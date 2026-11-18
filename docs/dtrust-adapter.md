# D-TRUST adapter (initial)

The first D-TRUST adapter implements read-only reader/card/certificate/mechanism discovery. It is intentionally separate from the generic provider registry and has no direct dependency on PC/SC or PKCS#11 libraries.

## Backend boundary

The service composition layer injects a narrow backend that supplies reader state, ATR/presence, safe certificate metadata and mechanisms. This lets unit tests use a deterministic mock and keeps vendor middleware details out of the provider-neutral core.

The adapter uses the observed ATR from the initial hardware investigation as a default matching hint. ATR matching is configurable and must not be treated as a unique cryptographic identity or the sole production validation of a card. Production identification should combine supported card profile data and middleware evidence.

## Identifiers and privacy

- Card IDs are service-local and derived from the reader ID.
- Certificate IDs are SHA-256 fingerprints.
- Token serials, cardholder subject names, PIN/CAN values and private-key material are not exposed by this adapter.
- Certificate object IDs remain internal to the backend and are resolved server-side before capability lookup.

## Current limitations

- Read-only discovery only; no signing operation or PIN handling.
- No concrete PC/SC or PKCS#11 backend is included.
- No provider trust-anchor download or fingerprint pinning is implemented here.
- No OCSP/CRL or QES assessment is performed.
- Hardware behavior must be verified on the target Raspberry Pi after mocked tests pass.

These limitations are deliberate; this module is not yet suitable for production use.
