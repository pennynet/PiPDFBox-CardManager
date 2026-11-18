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

This branch establishes the initial architecture, domain models and provider-adapter contracts. It includes an initial read-only D-TRUST metadata adapter, optional PC/SC reader discovery and automated unit tests.

It does not yet include production signing operations, a local service/API endpoint, trust-anchor downloader, reader event monitoring or Debian/systemd installer. These will be added in reviewed increments.

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

## Verified hardware reference

A separate Raspberry Pi OS reference installation has been documented for the REINER SCT cyberJack RFID standard and D-TRUST Card 5.1 Standard. USB/PC/SC/OpenSC/PKCS#11 discovery and RSA-3072 mechanisms were observed on ARM64. The operator also reports a successful PDF signing and validation test using the archived pyHanko-based environment.

See [the reference installation record](docs/reference-dtrust-cyberjack-pios-2026-11-18.md) for observed package versions, commands, scope and limitations. This reference does not imply that the current installation has been validated or that the CardManager backend/API is production-ready.

