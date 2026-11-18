"""Provider adapters and provider-neutral card metadata."""

from cardmanager.domain import Card, CardState, Certificate, CertificateRole, SigningMechanism
from cardmanager.providers.base import (
    DuplicateProviderError, ProviderAdapter, ProviderError,
    ProviderNotFoundError, ProviderRegistry,
)
from cardmanager.providers.dtrust import DTrustAdapter

__all__ = [
    "Card", "CardState", "Certificate", "CertificateRole", "SigningMechanism",
    "DuplicateProviderError", "ProviderAdapter", "ProviderError",
    "ProviderNotFoundError", "ProviderRegistry", "DTrustAdapter",
]
