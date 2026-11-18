"""Provider-neutral domain models.

These objects deliberately contain metadata only. PINs, CANs, private-key
material, raw APDUs and personal certificate subject data do not belong here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ReaderState(StrEnum):
    AVAILABLE = "available"
    BUSY = "busy"
    UNAVAILABLE = "unavailable"


class CardState(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    UNKNOWN = "unknown"


class CertificateRole(StrEnum):
    SIGNING = "signing"
    AUTHENTICATION = "authentication"
    INTERMEDIATE_CA = "intermediate_ca"
    ROOT_CA = "root_ca"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class Reader:
    """A discovered reader; reader_id is an opaque, service-local identifier."""

    reader_id: str
    display_name: str
    state: ReaderState

    def __post_init__(self) -> None:
        _required(self.reader_id, "reader_id")
        _required(self.display_name, "display_name")


@dataclass(frozen=True, slots=True)
class Card:
    """A card presence/profile summary without cardholder identity or secrets."""

    card_id: str
    reader_id: str
    provider_id: str
    card_type: str
    display_name: str
    state: CardState

    def __post_init__(self) -> None:
        for field_name in ("card_id", "reader_id", "provider_id", "card_type", "display_name"):
            _required(getattr(self, field_name), field_name)


@dataclass(frozen=True, slots=True)
class SigningMechanism:
    """One cryptographic operation supported by a card/provider key."""

    algorithm: str
    mechanism: str
    key_algorithm: str
    key_size_bits: int

    def __post_init__(self) -> None:
        for field_name in ("algorithm", "mechanism", "key_algorithm"):
            _required(getattr(self, field_name), field_name)
        if self.key_size_bits <= 0:
            raise ValueError("key_size_bits must be positive")


@dataclass(frozen=True, slots=True)
class Certificate:
    """Safe certificate metadata; no subject name or raw certificate is exposed."""

    certificate_id: str
    card_id: str
    role: CertificateRole
    issuer_display_name: str | None
    not_before: datetime
    not_after: datetime
    public_key_algorithm: str
    public_key_size_bits: int

    def __post_init__(self) -> None:
        for field_name in ("certificate_id", "card_id", "public_key_algorithm"):
            _required(getattr(self, field_name), field_name)
        if self.not_before.tzinfo is None or self.not_after.tzinfo is None:
            raise ValueError("certificate validity timestamps must be timezone-aware")
        if self.not_after <= self.not_before:
            raise ValueError("not_after must be later than not_before")
        if self.public_key_size_bits <= 0:
            raise ValueError("public_key_size_bits must be positive")


def _required(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
