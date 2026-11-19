"""Safe metadata models for PKCS#11 private-key discovery."""

from dataclasses import dataclass
from enum import StrEnum


class PrivateKeyVisibility(StrEnum):
    """Visibility state of private-key objects in an unauthenticated session."""

    NOT_VISIBLE = "not_visible"
    CANDIDATE_FOUND = "candidate_found"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class Pkcs11PrivateKeyInfo:
    """Non-secret metadata of a visible PKCS#11 private-key object."""

    object_id: bytes
    label: str
    key_type: str


@dataclass(frozen=True, slots=True)
class Pkcs11PrivateKeyDiscovery:
    """Result of unauthenticated private-key object discovery."""

    visibility: PrivateKeyVisibility
    keys: tuple[Pkcs11PrivateKeyInfo, ...]
