# Architecture

## Responsibilities and boundaries

CardManager is an independently installable service and repository. It does not depend on PiPDFBox being installed.

### CardManager owns

- PC/SC reader discovery and card presence monitoring.
- Provider/card identification and adapter selection.
- PKCS#11 sessions and access to private-key operations.
- Certificate and public-key metadata associated with a card.
- Provider trust-material acquisition, provenance and fingerprint verification.
- A local, least-privilege interface for authorized clients.

### PiPDFBox-PDFSigning owns

- PDF parsing and modification.
- PAdES signature construction and PDF-level validation.
- Signature appearance, fields, reason/location and PDF workflow.

PDFSigning may request a cryptographic signing operation from CardManager. CardManager must never receive arbitrary filesystem paths or take responsibility for PDF parsing.

### PiPDFBox owns

- User interface and user workflow.
- Installation orchestration and feature availability.
- Authorization of users and jobs before requesting signing operations.

PHP-FPM must not receive direct PC/SC or PKCS#11 access.

## Runtime topology

The intended deployment is a dedicated unprivileged OS account and systemd service. Communication should use a Unix-domain socket with restrictive ownership/mode and a narrowly defined client group or peer-credential policy. Do not expose a network listener by default.

The web application submits a job to the PDFSigning component. PDFSigning requests a signing operation through the CardManager interface. PIN-pad interaction remains with the reader/card middleware; PIN/CAN values must not be collected by the browser or persisted by either service.

## Provider adapter contract

A provider adapter describes:

- supported reader/card identification patterns;
- PKCS#11 module or vendor middleware requirements;
- certificate selection rules (issuer, key usage, certificate policy and stable object identifiers; never assume labels are globally unique);
- supported mechanisms and key capabilities;
- PIN-pad / user-presence behavior;
- official certificate and trust-list sources;
- provider-specific operational limitations.

The core must not assume all cards use OpenSC, PKCS#11, RSA, a PIN pad, or the same certificate layout. Adapters must declare capabilities and fail closed when requirements are not met.

## Trust material lifecycle

1. Select the trust anchor(s) required for the detected certificate chain and intended validation policy.
2. Retrieve from a documented official provider or authoritative trust-list source over authenticated transport.
3. Verify the downloaded certificate against a fingerprint or signed metadata obtained independently of that download.
4. Validate certificate constraints, subject/issuer, validity and expected role before activation.
5. Store immutable provenance (source, retrieval time, fingerprint, validation result and profile version).
6. Refresh safely; never silently replace a trust anchor after a failed verification.

OCSP/CRL checking is distinct from trust-anchor verification. QES assessment additionally requires applicable qualified certificate/service status and trusted-list evidence; a mathematically valid signature or trusted chain alone is not a QES determination.

## Installation and upgrades

CardManager has its own installer/updater and can be installed or removed independently. PiPDFBox may offer an optional “Install card module” action. The CardManager installer must not modify PiPDFBox application files.

The installer should:
- install only required system packages;
- create a dedicated service account and protected configuration/state directories;
- install the service into a versioned virtual environment or package;
- create narrowly scoped PC/SC authorization;
- install a systemd unit and local socket;
- perform health checks before reporting ready;
- provide rollback and safe uninstall behavior.

No installer implementation is included in this bootstrap branch.

## Compatibility

Initial target: Debian 13 / Raspberry Pi OS Trixie, Python 3.13, PC/SC-Lite and OpenSC where supported. These are initial targets, not universal requirements for every provider.
