# Domain model

The first implementation increment defines immutable metadata objects only.

## Objects

- **Reader** identifies a reader within the running service and reports its state.
- **Card** describes card presence and a provider-neutral card profile. It contains no cardholder identity.
- **Certificate** reports purpose and validity metadata without exposing subject names or raw certificate bytes.
- **SigningMechanism** describes an available cryptographic mechanism and key characteristics.

## Security boundaries

- Identifiers are opaque and service-local; clients must not treat them as permanent hardware identities.
- PINs, CANs, private keys, key handles, APDUs and raw certificate contents are not domain-model fields.
- A supported signing mechanism is not evidence that a signature is qualified.
- Certificate-chain trust, revocation status and QES qualification are separate assessments and are intentionally not inferred by these models.
- Provider-specific details belong in adapters, not in these shared types.

## Validation

Models are immutable dataclasses. Required identifiers and display labels must be non-empty. Certificate validity timestamps must be timezone-aware and ordered. Key sizes must be positive.
