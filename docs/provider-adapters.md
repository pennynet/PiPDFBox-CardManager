# Provider adapters

Provider adapters isolate card-vendor and middleware differences from the CardManager core.

## Contract

Implement ProviderAdapter from cardmanager.providers.base:

- provider_id: stable lowercase identifier.
- list_readers(): readers handled by this adapter.
- list_cards(): supported cards currently detected.
- list_certificates(card_id): safe certificate metadata for one card.
- signing_mechanisms(card_id, certificate_id): mechanisms available for that key.

The initial contract is deliberately read-only. A later, separately reviewed change will define the cryptographic operation/session interface, including cancellation, PIN-pad behavior, timeouts and transient credential handling. Do not add PIN/CAN arguments to discovery methods.

## Registry

Adapters are registered explicitly with ProviderRegistry. Duplicate identifiers and unknown provider lookups fail with typed exceptions. There is no implicit module loading or arbitrary PKCS#11 module path supplied by an API client.

## Adapter implementation rules

1. Return the shared immutable domain types; do not leak vendor objects into the core.
2. Use opaque service-local IDs for readers, cards and certificates.
3. Do not log APDUs, PIN/CAN, private-key handles or full personal certificate data.
4. Declare only mechanisms actually supported by the selected key and middleware.
5. Fail closed on ambiguous certificates, unsupported cards or middleware errors.
6. Keep provider trust-material URLs and independently verified fingerprints in reviewed provider profiles, not in caller input.
7. Hardware access and PKCS#11 session management remain inside the adapter/service boundary.

## First integration

D-TRUST will be the first concrete adapter. It must be implemented against the contract and tested with mocked PC/SC/PKCS#11 objects before connecting real hardware. No D-TRUST-specific behavior is present in the provider-neutral core.
