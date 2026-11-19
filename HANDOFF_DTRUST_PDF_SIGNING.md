# Handover – D-TRUST PDF signing integration

**Repository:** `pennynet/PiPDFBox-CardManager`  
**Working branch:** `feature/dtrust-signing-certificate-discovery`  
**Last completed commit:** `6f15e0c` – `Add OpenSC-backed PDF signing`  
**Status:** Feature branch pushed to GitHub. No merge to `main`; no changes to `main`.

## 1. Goal

Continue integrating the proven D-TRUST/OpenSC PDF signing path into the normal CardManager application flow. The next milestone is a CardManager service/API operation that accepts an input PDF and output path, discovers the usable signing certificate on the connected card, associates it with the correct private key, and signs only after an explicit user action.

## 2. Verified current state

- Raspberry Pi host: `offix`, Debian 13, ARM64, Python 3.13.5.
- Repository working copy used during implementation: `/home/pi/cardmanager-test/PiPDFBox-CardManager`.
- Python virtual environment: `.venv`.
- OpenSC version: 0.27.1.
- OpenSC PKCS#11 module: `/opt/opensc-0.27.1/lib/opensc-pkcs11.so`.
- OpenSC utility: `/opt/opensc-0.27.1/bin/pkcs11-tool`.
- pyHanko: 0.38.2.
- python-pkcs11: 0.10.1.
- D-TRUST signing certificate uses an RSA 3072-bit public key; resulting RSA signature is 384 bytes.
- The signing key has `CKA_ALWAYS_AUTHENTICATE=True`; the reader's protected authentication path is used.
- PKCS#11 certificate/key association observed during the test: key ID `02`, slot `1`.

### Completed verification

- Baseline suite before the signing addition: 48 tests passed.
- Current suite after the addition and async subprocess correction: **54 tests passed**.
- Ruff: **All checks passed**.
- `git diff --check`: clean before commit.
- Real card signing through the new `OpenSCPdfSigner` implementation succeeded.
- Output test PDF was created at `/home/pi/cardmanager-backups/dtrust-cardmanager-integrated-signed.pdf` (12,901 bytes at the time of the test).
- External RTR online validation reported: **“Das Dokument ist gültig signiert.”** Signature format was identified as PDF signature / Adobe PKCS#7.
- Local pyHanko validation found one signature and reported:
  - `intact = True`
  - `valid = True`
  - `trusted = False`
- The local trust result is **not** a cryptographic signature failure. pyHanko could not build the certificate path because the issuing CA `D-TRUST CA 3-21-1 2021` was not available in its validation context. The issuer/root chain still needs to be configured for local trust validation.
- The signed PDF and certificate test file are in the local backup directory, not in the repository.

## 3. Changes committed

Commit `6f15e0c` changed exactly three files:

1. `cardmanager/signing/opensc.py`
   - Adds `OpenSCPdfSigner` and `OpenSCPdfSigningError`.
   - Uses pyHanko's `ExternalSigner`.
   - Calls OpenSC `pkcs11-tool` asynchronously with `asyncio.create_subprocess_exec`.
   - Enforces SHA-256 / RSA PKCS#1 v1.5 signing and expected signature length.
   - Uses a 120-second timeout and terminates the child process on timeout.
   - Uses temporary files for the signed attributes and signature.
   - Refuses to overwrite an existing output PDF.
   - Requires absolute module/tool paths and validates the RSA signing certificate.
2. `tests/test_opensc_signing.py`
   - Six tests cover constructor validation, dry-run signature sizing, digest rejection, and output overwrite protection.
3. `pyproject.toml`
   - Adds optional extra: `pdf-signing = ["pyHanko>=0.38,<0.39", "cryptography>=42"]`.

The existing `cardmanager/providers/pkcs11.py` remains read-only and should stay read-only. Do not add private-key signing or authentication operations to that discovery provider.

## 4. Security constraints – must preserve

- Never ask for, store, pass on the command line, or log PIN or CAN values.
- Signature PIN entry must remain exclusively on the reader's protected PIN pad / protected authentication path.
- Do not access or use the card's Authentication-PIN token for this signature flow.
- Never export private keys.
- Never log certificate subject/person-identifying details, PIN prompts, raw token output, or sensitive PKCS#11 object labels.
- Do not sign automatically on card insertion. Require an explicit user action for every signing operation.
- Do not overwrite existing PDFs; preserve the original input.
- Do not upload user PDFs to online validation services automatically. Online checking is optional and requires explicit user consent plus privacy/retention review.
- Do not commit test PDFs, DER certificates, card dumps, logs, credentials, or backup files.

## 5. Architecture known so far

- `cardmanager/providers/pkcs11.py`: read-only PKCS#11 discovery; keep read-only.
- `cardmanager/providers/dtrust.py`: D-TRUST adapter; backend protocol currently focuses on discovery/mechanisms.
- `cardmanager/config.py`: current configuration has `CardManagerConfig` and `pkcs11.module_path`.
- `cardmanager/domain.py`: metadata-only domain model; avoid putting secrets or private-key material here.
- Existing tests include `test_config.py`, `test_domain.py`, `test_dtrust_adapter.py`, `test_pcsc.py`, `test_pkcs11.py`, `test_providers.py`, plus new `test_opensc_signing.py`.
- The existing PKCS#11 tests enforce that the discovery module has no signing methods.
- The new `cardmanager/signing/` directory currently contains `opensc.py`; it did not yet have an `__init__.py` at handover time.

Before implementation, inspect the actual current tree and service/API entry points. The project was not yet wired to invoke the new signer through its normal application flow.

## 6. Next roadmap

### Phase 1 – integrate signing into CardManager (next task)
1. Inspect the current repository tree, service layer, API layer, and provider interfaces.
2. Define a narrow signing service/use-case boundary; do not mix signing into the read-only discovery provider.
3. Obtain certificate DER from the selected public certificate object using read-only PKCS#11 access, matched to the selected certificate fingerprint/ID.
4. Resolve the signing key ID and slot from discovered card metadata rather than silently assuming fixed values. Keep a safe D-TRUST default only if the architecture requires it and document the assumption.
5. Add configuration for the OpenSC module and `pkcs11-tool` executable if appropriate; avoid hard-coded machine-specific paths in business logic.
6. Expose a method such as `sign_pdf(input_pdf, output_pdf, ...)` through the CardManager service/API.
7. Add unit tests with mocked process execution and provider discovery. Do not require a physical card for the normal unit suite.

### Phase 2 – user-facing flow
- Select source PDF and destination.
- Show detected reader/card and eligible signing certificate metadata.
- Require explicit confirmation before signing.
- Trigger protected PIN entry on the reader; no terminal PIN input.
- Report success/failure without leaking token output.
- Preserve original PDF and refuse accidental overwrite.

### Phase 3 – validation
- Integrate local pyHanko integrity/cryptographic validation.
- Configure D-TRUST intermediate/root certificates as a trust context, after verifying certificate fingerprints and issuer chain from official D-TRUST sources.
- Report integrity, cryptographic validity, and trust status as separate results.
- Consider optional online validation only after reviewing a supported service/API, data protection, retention, and explicit user consent.

### Phase 4 – hardening and release
- Test card removal, reader removal, timeout, cancellation, wrong/locked PIN, missing certificate/key, unsupported PDF, and existing output path.
- Verify no PIN/CAN or personal certificate data enters logs.
- Run full tests and Ruff on the Raspberry Pi.
- Update installation and operator documentation.
- Push changes to this feature branch and create a PR only when the user requests it.

## 7. Commands and workflow

Use one terminal command per assistant turn and wait for the user's output. Commands should start with `clear` and use the full repository path.

Repository:
```bash
cd /home/pi/cardmanager-test/PiPDFBox-CardManager
```

Check branch and working tree:
```bash
git status --short --branch
git branch --show-current
```

Run tests:
```bash
.venv/bin/python -m pytest -q
```

Run lint:
```bash
.venv/bin/ruff check cardmanager tests
```

Do not switch to `main`, merge, or push new work without explicit user approval. The previous push was explicitly authorized and completed for commit `6f15e0c`.

## 8. GitHub state

- Repository: https://github.com/pennynet/PiPDFBox-CardManager
- Branch: https://github.com/pennynet/PiPDFBox-CardManager/tree/feature/dtrust-signing-certificate-discovery
- Commit: https://github.com/pennynet/PiPDFBox-CardManager/commit/6f15e0c
- Last confirmed push output: `3820ea1..6f15e0c feature/dtrust-signing-certificate-discovery -> feature/dtrust-signing-certificate-discovery`.
- No PR was created and no merge was performed.

## 9. Immediate next action

Start with a read-only inspection of the current repository structure and service/API entry points. Do not modify files until the existing integration points are understood. Then implement Phase 1 in small, testable increments.
