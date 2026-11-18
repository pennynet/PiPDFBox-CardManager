# Security model

## Sensitive material

- Private keys remain non-exportable in the card/provider.
- PIN and CAN are entered only through the supported reader/middleware interaction. They must never be written to configuration, command-line arguments, logs, environment variables, browser requests or persistent storage.
- Do not commit real card certificates containing personal identity data, card identifiers, serial numbers, PIN data, CAN data, logs or captured validation reports.
- Public certificates may still contain personal data. Test fixtures must be synthetic or explicitly sanitized.

## Process separation

- The CardManager service runs under a dedicated unprivileged account.
- PHP-FPM (for example, `www-data`) does not receive direct PC/SC or PKCS#11 access.
- Only the CardManager service account receives the minimum PC/SC authorization required.
- The local IPC endpoint is not exposed to the LAN and is protected by filesystem permissions and client authorization.
- The PDFSigning component receives only the cryptographic operation interface it needs.

## Trust anchors

A certificate downloaded over HTTPS is not trusted merely because the download succeeded. Its fingerprint or signed metadata must be independently anchored in the shipped, reviewed provider profile or another independently trusted source. Failed or ambiguous checks must stop activation.

Trust-anchor validation, certificate-path validation, revocation checking and QES assessment are separate checks and must be reported separately.

## Logging

Logs may contain operation IDs, provider/profile identifiers, non-sensitive status codes and timings. They must not contain PIN/CAN, private key material, full personal certificate fields, raw authentication exchanges or unredacted validation dumps.

## Threats to address before production

- unauthorized local client requesting a signature;
- malicious or compromised PDFSigning/PiPDFBox process;
- untrusted provider profile or substituted trust anchor;
- incorrect certificate/key selection on multi-certificate cards;
- PIN retry exhaustion or card lockout;
- reader removal during a signing operation;
- stale revocation/trust-list information;
- unsafe updates and rollback;
- denial of service through repeated signing requests.

This document is an initial design baseline, not a completed security audit.
