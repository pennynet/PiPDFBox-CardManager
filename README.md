# PiPDFBox CardManager

Independent smart-card, reader and cryptographic-key management service for PiPDFBox and other applications.

**Status:** architecture/bootstrap stage. No production signing API is implemented yet.

## Purpose

CardManager isolates hardware- and provider-specific concerns from PDF processing. It is independently installable and does not require PiPDFBox.

- Discover and report smart-card readers and inserted cards.
- Load provider-specific PKCS#11 or vendor-middleware adapters.
- Expose certificate metadata and signing capabilities without exporting private keys.
- Acquire and verify provider trust material with recorded provenance.
- Provide a narrowly scoped local interface to authorized clients.

PDF parsing, PAdES assembly and PDF-level validation belong to the separate **PiPDFBox-PDFSigning** project.

## Design principles

1. Provider-neutral core; D-TRUST is the first integration, not a hard-coded dependency.
2. Private keys never leave the card or cryptographic provider.
3. PINs and CANs are never stored, logged, or sent through the PiPDFBox web UI.
4. Trust anchors are obtained from documented official sources and checked against independently maintained fingerprints before activation.
5. Reader access is least-privilege and isolated from PHP-FPM.
6. Local IPC is authenticated and restricted; prefer a Unix-domain socket with filesystem permissions.
7. A card's cryptographic capabilities do not, by themselves, establish QES status.
8. Provider adapters are explicit and testable; unsupported cards fail closed.

## Repository layout

- `cardmanager/` — provider-neutral service and domain interfaces.
- `cardmanager/providers/` — provider adapters and profiles.
- `cardmanager/readers/` — PC/SC and reader discovery.
- `cardmanager/certificates/` — trust-material acquisition and verification.
- `cardmanager/api/` — local service interface.
- `docs/` — architecture, security and API contracts.
- `tests/` — unit and integration tests.
- `packaging/` — future Debian/systemd installation assets.

## Development status

The initial branch establishes documentation and package boundaries only. Hardware integration, service endpoints, installer and provider profiles will be added in reviewed increments.

Initial development target: Python 3.13 on Debian 13 / Raspberry Pi OS Trixie. Hardware and provider compatibility will be declared per adapter, not assumed globally.

## Development

Create a virtual environment and install development dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Install optional PC/SC and PKCS#11 support only when needed:

```bash
pip install -e ".[pcsc,pkcs11]"
```
