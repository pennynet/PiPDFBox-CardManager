# Development checkpoint — D-TRUST signing-certificate discovery

Last updated: 2026-11-18

This document is the hand-off record for continuing work in a later chat. It records verified observations separately from implementation status.

## Repository and branches

- Repository: `pennynet/PiPDFBox-CardManager`
- Architecture baseline: `main` (includes the reference installation record)
- PKCS#11 token discovery: `feature/dtrust-pkcs11-discovery`, tracked by PR #3
- Current work: `feature/dtrust-signing-certificate-discovery`, based on the PKCS#11 discovery branch
- Current pull request: to be opened after this checkpoint is committed

Do not merge implementation branches into `main` until reviewed and hardware-tested.

## Hardware observations reported from the Raspberry Pi

On the known-good Raspberry Pi OS ARM64 installation:

- Reader: REINER SCT cyberJack RFID standard, USB ID `0c4b:0500`
- Card: D-TRUST Card 5.1 Standard
- OpenSC module: `/usr/lib/aarch64-linux-gnu/opensc-pkcs11.so`
- `opensc-tool -l` detected the cyberJack and an inserted card.
- `pkcs11-tool --list-slots` showed two tokens:
  - D-TRUST Signature-PIN token
  - D-TRUST Authentication-PIN token
- Both tokens reported login required, protected authentication path, token initialized and user PIN initialized.
- The user reports a prior successful PDF signing and validation on a separate archived installation. This is not evidence that the current CardManager implements production signing.

Sensitive token serial numbers and PKCS#11 URIs are intentionally omitted.

## Verified tests

The user reported:
- 30 tests passed on the initial PKCS#11 discovery branch.
- After normalizing PKCS#11 flag enum names, 31 tests passed on the Raspberry Pi.

These results apply to the earlier branch and its tests. The certificate-discovery changes in the current branch have not yet been run by the user on the Raspberry Pi.

## Current implementation in this branch

- `Pkcs11Module.list_tokens()` reads public token metadata and does not expose serial numbers.
- PKCS#11 flags are normalized to readable enum names.
- `Pkcs11Module.list_signing_certificates()` is being introduced as a read-only discovery method.
- It selects exactly one token whose label identifies `(Signature-PIN)` and whose manufacturer begins with `D-TRUST`.
- It opens only that token, using `token.open(rw=False)` with no PIN argument.
- It searches only certificate objects and parses X.509 certificate values.
- It returns SHA-256 fingerprint, issuer common name, validity timestamps and public-key algorithm/size for certificates with digital-signature or content-commitment key usage.
- It does not return subject names or raw certificate bytes.
- It does not open the Authentication-PIN token, enumerate private-key objects, perform login, request PINs or sign.
- The optional `pkcs11` extra now includes `cryptography` for X.509 parsing.

## Important scope and caveats

- Certificate discovery is not certificate-chain validation or trust validation.
- A certificate with digital-signature key usage is not, by itself, proof of qualified electronic signature status.
- The current token selection relies on the observed D-TRUST token label/manufacturer metadata. Keep it fail-closed if missing or ambiguous.
- Real-card certificate enumeration must be tested on the Raspberry Pi before this work is considered complete.
- The test suite uses generated test certificates and fake PKCS#11 token/session objects; it does not substitute for the hardware test.
- Do not add PIN collection, login, private-key reads, signing, or Authentication-PIN access to this milestone.

## Next steps

1. On the Pi, fetch this branch and reinstall the updated optional dependencies:
   ```bash
   git fetch origin
   git checkout feature/dtrust-signing-certificate-discovery
   git pull origin feature/dtrust-signing-certificate-discovery
   pip install -e ".[pkcs11,dev]"
   python -m pytest -v
   ```
2. If all tests pass, run the read-only real-card certificate discovery snippet provided in the PR description / hand-off conversation.
3. Review certificate count and issuer/key metadata only. Do not publish personal subject data, raw certificate data, token serials or PKCS#11 URIs in logs.
4. Record hardware results here, then review PR before merging.
5. Later milestones: map certificate IDs to public key objects safely, discover per-key signing mechanisms, then separately design protected-path signing and PDF/PAdES integration.

## How to resume in a new chat

Start from this repository and read this document first. Then inspect the open pull requests and the branch `feature/dtrust-signing-certificate-discovery`. The user’s Pi checkout has previously been at:

`/home/pi/cardmanager-test/PiPDFBox-CardManager`

The virtual environment is `.venv`. Do not assume the current Pi checkout has the latest branch until `git status` and `git branch --show-current` are checked.

## Latest Pi test feedback (2026-11-18)

The user ran the new branch on the Raspberry Pi: 34 tests collected, 33 passed and one failed. The failing test was `test_loader_errors_are_wrapped_without_leaking_low_level_text`; implementation correctly wrapped the loader error with the message `PKCS#11 module could not be loaded`, while the older assertion expected `token discovery failed`. During review, the chained original exception was also identified as a possible way for low-level device details to appear in tracebacks. The branch was updated to suppress that exception chain (`raise ... from None`) and the test now checks the actual stable message and that `__cause__` is absent. These latest fixes are committed but have not yet been rerun by the user.
