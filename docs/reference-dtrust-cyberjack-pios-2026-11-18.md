# D-TRUST / cyberJack reference installation

**Recorded:** 2026-11-18  
**Status:** Hardware and PKCS#11 discovery verified on a separate Raspberry Pi OS installation. PDF signing and validation were previously reported successful by the operator on that installation. This is a reference record, not a production compatibility guarantee.

## Hardware

- Reader: REINER SCT cyberJack RFID standard (dual interface)
- USB vendor/product ID observed: `0c4b:0500`
- Card: D-TRUST Card 5.1 Standard, version 1.2 (operator-provided identification)

The USB device was visible with `lsusb`. OpenSC reported the reader as:

```text
REINER SCT cyberJack RFID standard
```

The reader was reported with PIN-pad capability by `opensc-tool -l`.

## System packages observed

Architecture: `arm64`

| Package | Version |
| --- | --- |
| `libccid` | `1.6.2-1` |
| `libifd-cyberjack6` | `3.99.5final.sp17-0.1` |
| `libpcsclite-dev` | `2.3.3-1` |
| `libpcsclite1` | `2.3.3-1` |
| `pcscd` | `2.3.3-1` |
| `opensc` | `0.27.1-3` |
| `opensc-pkcs11` | `0.27.1-3` |

PKCS#11 module path observed:

```text
/usr/lib/aarch64-linux-gnu/opensc-pkcs11.so
```

The PC/SC daemon was socket-activated (`pcscd.service` inactive while `pcscd.socket` was active). This is not by itself an error.

The diagnostic command `pcsc_scan` was not installed in the reference environment. It is provided by the optional `pcsc-tools` package; its absence did not prevent OpenSC/PKCS#11 discovery.

## Card and certificate discovery

With the card inserted:

- `pkcs11-tool --list-slots` reported slot 0 with a present token.
- `pkcs11-tool --list-objects` showed certificate and public-key objects, including the signing certificate and CA certificates.
- The public key associated with the signing certificate was reported as RSA, 3072 bits.

Personal certificate fields, token serials and other identifying values are intentionally omitted from this document.

## Mechanisms observed

The PKCS#11 mechanism listing reported RSA key size 3072 bits and included:

- `RSA-PKCS` (sign/verify)
- `SHA256-RSA-PKCS` (sign/verify)
- `SHA384-RSA-PKCS` (sign/verify)
- `SHA512-RSA-PKCS` (sign/verify)
- `RSA-PKCS-PSS` (sign/verify)
- `SHA256-RSA-PKCS-PSS` (sign/verify)
- `SHA384-RSA-PKCS-PSS` (sign/verify)
- `SHA512-RSA-PKCS-PSS` (sign/verify)

This is capability discovery only. It does not establish which mechanism was selected by a particular PDF-signing operation.

## PDF signing reference

The archived test environment contains a Python signing script at `pades-test/scripts/sign_pdf.py` and D-TRUST configuration. The environment inventory identified pyHanko 0.38.1 and python-pkcs11 0.9.5, with OpenSC PKCS#11 as the card access path.

The operator reports that `Test.PDF` was successfully signed and validated on this separate installation. The precise signature profile, validation policy and revocation-checking status must be confirmed from the script and its sanitized output before being described as a production validation result.

## Architectural implications

The reference supports the following implementation direction:

- CardManager: PC/SC reader discovery, card/provider identification, PKCS#11 certificate and mechanism metadata, and tightly scoped private-key operations.
- PiPDFBox-PDFSigning: PDF parsing, PAdES construction and PDF-level validation (for example, using the already-tested pyHanko path).
- PiPDFBox: user interface and workflow.

Private keys remain on the card/provider. PIN/CAN values must not be placed in configuration, command-line arguments, logs, browser requests or persistent storage. PHP-FPM must not receive direct PC/SC or PKCS#11 access.

## Not yet established

This record does **not** establish:

- that the current/new PiOS installation has the same packages or configuration;
- the cyberJack firmware version;
- the exact D-TRUST middleware/card profile requirements for every card variant;
- the exact PAdES baseline level produced by the archived script;
- online OCSP/CRL checking, LTV status or qualified-signature (QES) status;
- production readiness of a CardManager PKCS#11 backend or service API.

## Reproduction commands

Run these on the reference Pi with the card inserted. Do not enter a PIN merely to perform discovery.

```bash
lsusb
opensc-tool -l
pkcs11-tool --module /usr/lib/aarch64-linux-gnu/opensc-pkcs11.so --list-slots
pkcs11-tool --module /usr/lib/aarch64-linux-gnu/opensc-pkcs11.so --list-objects
pkcs11-tool --module /usr/lib/aarch64-linux-gnu/opensc-pkcs11.so --list-mechanisms
```
