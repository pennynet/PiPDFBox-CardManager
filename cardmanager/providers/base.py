"""Contracts and registry for pluggable smart-card providers."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from cardmanager.domain import Card, Certificate, Reader, SigningMechanism


class ProviderError(RuntimeError):
    """Base error for provider discovery and metadata failures."""


class ProviderNotFoundError(ProviderError):
    """Raised when a requested provider is not registered."""


class DuplicateProviderError(ProviderError):
    """Raised when two adapters claim the same provider identifier."""


@runtime_checkable
class ProviderAdapter(Protocol):
    """Read-only discovery contract implemented by each provider adapter."""

    @property
    def provider_id(self) -> str:
        """Stable, lowercase identifier, e.g. dtrust."""

    def list_readers(self) -> tuple[Reader, ...]:
        """Return readers relevant to this adapter."""

    def list_cards(self) -> tuple[Card, ...]:
        """Return currently detected cards supported by this adapter."""

    def list_certificates(self, card_id: str) -> tuple[Certificate, ...]:
        """Return safe certificate metadata for one detected card."""

    def signing_mechanisms(self, card_id: str, certificate_id: str) -> tuple[SigningMechanism, ...]:
        """Return mechanisms allowed for the selected certificate/key."""


class ProviderRegistry:
    """Explicit registry; adapters are injected rather than auto-imported."""

    def __init__(self) -> None:
        self._adapters: dict[str, ProviderAdapter] = {}

    def register(self, adapter: ProviderAdapter) -> None:
        provider_id = adapter.provider_id
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("provider_id must be a non-empty string")
        if provider_id != provider_id.strip().lower():
            raise ValueError("provider_id must be lowercase without surrounding whitespace")
        if provider_id in self._adapters:
            raise DuplicateProviderError(f"provider already registered: {provider_id}")
        self._adapters[provider_id] = adapter

    def get(self, provider_id: str) -> ProviderAdapter:
        try:
            return self._adapters[provider_id]
        except KeyError as exc:
            raise ProviderNotFoundError(f"provider is not registered: {provider_id}") from exc

    def provider_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))
