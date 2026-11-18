# Local API contract (draft)

This is a design contract, not an implemented API. Version the interface independently (initial namespace: `/v1`).

## Transport and authorization

- Default transport: Unix-domain socket only; no TCP listener by default.
- Socket ownership and mode must restrict access to the CardManager service and explicitly authorized client service account(s).
- Authenticate clients using OS peer credentials in addition to filesystem permissions.
- Do not accept arbitrary file paths, shell commands, module paths, or caller-selected PKCS#11 object handles.
- Apply request size limits, timeouts, rate limits and operation IDs.

## Read-only discovery

### `GET /v1/status`

Returns service health, supported interface version and adapter readiness. Must not include secrets or personal certificate fields.

### `GET /v1/readers`

Returns reader identifiers, display names and presence status. Stable identifiers should be opaque and avoid leaking hardware serials unless explicitly required by an administrator.

### `GET /v1/cards`

Returns detected card/provider profile identifiers and high-level capabilities. Do not return PIN state, PIN values, CAN values, private-key material or unnecessary personal certificate fields.

### `GET /v1/cards/{card_id}/certificates`

Returns minimal certificate metadata needed by an authorized signing client: certificate fingerprint, issuer/subject only where necessary, validity interval, key usage, certificate policies and supported signing mechanisms. Personal identity details should be redacted by default.

## Cryptographic operation interface

The exact operation shape must be finalized with the PDFSigning project before implementation. The intended capability is a bounded request to sign a digest or a precisely specified mechanism input using a selected card key.

The API must:
- bind the operation to a server-resolved card, certificate and key;
- allow only mechanisms declared by the selected adapter;
- validate digest length and mechanism parameters;
- require user presence / PIN-pad interaction where the card requires it;
- return only the signature bytes, selected certificate chain references and a non-sensitive operation result;
- never accept or return private-key material;
- never accept PIN/CAN in request bodies, query strings or headers;
- prevent callers from selecting arbitrary object IDs without server-side policy checks.

No generic arbitrary PKCS#11 passthrough endpoint will be exposed.

## Errors

Use stable machine-readable error codes (examples): `READER_NOT_FOUND`, `CARD_NOT_PRESENT`, `PROVIDER_UNSUPPORTED`, `CERTIFICATE_AMBIGUOUS`, `MECHANISM_UNSUPPORTED`, `USER_CANCELLED`, `PIN_REQUIRED_AT_READER`, `CARD_LOCKED`, `TRUST_MATERIAL_INVALID`, `OPERATION_TIMEOUT`.

Error messages and logs must not disclose PIN/CAN, private data, full certificate dumps or low-level secrets.

## QES boundary

The cryptographic API reports what key/certificate and mechanism were used. It does not independently assert that the resulting PDF is a QES. PDFSigning and a dedicated validation/trust-policy layer must assess the PDF signature, certificate status, qualified status and applicable trusted-list evidence.
