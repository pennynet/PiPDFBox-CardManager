# Development checkpoint — D-TRUST signing-certificate discovery

Last updated: 2026-11-18

This document is the hand-off record for continuing work in a later chat. It records verified observations separately from implementation status.

## Repository and branches

- Repository: `pennynet/PiPDFBox-CardManager`
- Architecture baseline: `main` (includes the reference installation record)
- PKCS#11 token discovery: `feature/dtrust-pkcs11-discovery`, tracked by PR #3
- Current work: `feature/dtrust-signing-certificate-discovery`, based on the PKCS#11 discovery branch
- Current pull request: PR #4 (draft): https://github.com/pennynet/PiPDFBox-CardManager/pull/4

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
- On 2026-11-18, after the exception-chain suppression fix, all 34 tests passed on the Raspberry Pi (`python -m pytest -v`, 34 passed in 0.36s).

## Current implementation in this branch

- `Pkcs11Module.list_tokens()` reads public token metadata and does not expose serial numbers.
- PKCS#11 flags are normalized to readable enum names.
- `Pkcs11Module.list_signing_certificates()` provides read-only certificate discovery.
- It selects exactly one token whose label identifies `(Signature-PIN)` and whose manufacturer begins with `D-TRUST`.
- It opens only that token, using `token.open(rw=False)` with no PIN argument.
- It searches only certificate objects and parses X.509 certificate values.
- It returns SHA-256 fingerprint, issuer common name, validity timestamps and public-key algorithm/size for certificates with digital-signature or content-commitment key usage.
- It does not return subject names or raw certificate bytes.
- It does not open the Authentication-PIN token, enumerate private-key objects, perform login, request PINs or sign.
- The optional `pkcs11` extra includes `cryptography` for X.509 parsing.

## Real-card certificate discovery — verified on Raspberry Pi (2026-11-18)

The user successfully ran `Pkcs11Module.list_signing_certificates()` against the real REINER SCT cyberJack RFID standard and D-TRUST Card 5.1 Standard using the OpenSC PKCS#11 module.

Observed result:
- Exactly one signing certificate was returned.
- Issuer common name: `D-TRUST CA 3-21-1 2021`
- Validity: 2025-07-08 04:43:35 UTC through 2028-07-18 04:43:35 UTC
- Public key: RSA, 3072 bits
- SHA-256 fingerprint was returned and checked in the live session; it is intentionally not repeated in this persistent checkpoint.

The test was executed without supplying a PIN. The implementation path is read-only and is designed to open only the Signature-PIN token. No Authentication-PIN token access, login, private-key enumeration or signing was part of this test.

This verifies real-card certificate discovery, not certificate-chain validation, trust status, qualified-signature status or actual signing.

## Important scope and caveats

- Certificate discovery is not certificate-chain validation or trust validation.
- A certificate with digital-signature key usage is not, by itself, proof of qualified electronic signature status.
- The current token selection relies on the observed D-TRUST token label/manufacturer metadata. Keep it fail-closed if missing or ambiguous.
- The real-card read-only certificate enumeration has now been tested successfully on the Raspberry Pi.
- The test suite uses generated test certificates and fake PKCS#11 token/session objects; it does not substitute for the successful hardware test above.
- Do not add PIN collection, login, private-key reads, signing, or Authentication-PIN access to this milestone.

## Next steps

1. Review PR #4 and keep it separate from `main` until the implementation is reviewed.
2. Consider whether certificates without a KeyUsage extension should be handled differently; make any change only with test coverage and card evidence.
3. Next technical milestone: safely associate the discovered certificate with its corresponding public-key object and inspect supported signing mechanisms without logging in or signing.
4. Later milestones: separately design protected-path signing and PDF/PAdES integration. Do not assume certificate discovery proves these work.

## How to resume in a new chat

Start from this repository and read this document first. Then inspect PR #3, PR #4 and the branch `feature/dtrust-signing-certificate-discovery`. The user's Pi checkout has previously been at:

`/home/pi/cardmanager-test/PiPDFBox-CardManager`

The virtual environment is `.venv`. Do not assume the current Pi checkout has the latest branch until `git status` and `git branch --show-current` are checked.

## Latest Pi test feedback (2026-11-18)

The user initially ran the new branch on the Raspberry Pi: 34 tests collected, 33 passed and one failed. The failing test was `test_loader_errors_are_wrapped_without_leaking_low_level_text`; implementation correctly wrapped the loader error with the message `PKCS#11 module could not be loaded`, while the older assertion expected `token discovery failed`. During review, the chained original exception was also identified as a possible way for low-level device details to appear in tracebacks. The branch was updated to suppress that exception chain (`raise ... from None`) and the test now checks the stable message and that `__cause__` is absent. The user reran the suite successfully: 34 passed in 0.36s.
