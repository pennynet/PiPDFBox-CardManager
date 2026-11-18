from datetime import datetime, timezone

import pytest

from cardmanager.domain import (
    Card, CardState, Certificate, CertificateRole, Reader, ReaderState, SigningMechanism,
)
from cardmanager.providers.base import (
    DuplicateProviderError, ProviderNotFoundError, ProviderRegistry,
)


class FakeProvider:
    provider_id = "example"

    def list_readers(self):
        return (Reader("reader-1", "Test reader", ReaderState.AVAILABLE),)

    def list_cards(self):
        return (Card("card-1", "reader-1", self.provider_id, "test-card", "Test card", CardState.PRESENT),)

    def list_certificates(self, card_id):
        assert card_id == "card-1"
        now = datetime.now(timezone.utc)
        return (Certificate(
            "cert-1", card_id, CertificateRole.SIGNING, "Example CA",
            now, now.replace(year=now.year + 1), "RSA", 3072,
        ),)

    def signing_mechanisms(self, card_id, certificate_id):
        assert (card_id, certificate_id) == ("card-1", "cert-1")
        return (SigningMechanism("sha256", "rsa-pkcs", "RSA", 3072),)


def test_registry_registers_and_resolves_adapter():
    registry = ProviderRegistry()
    adapter = FakeProvider()
    registry.register(adapter)
    assert registry.get("example") is adapter
    assert registry.provider_ids() == ("example",)


def test_registry_rejects_duplicate_provider_ids():
    registry = ProviderRegistry()
    registry.register(FakeProvider())
    with pytest.raises(DuplicateProviderError):
        registry.register(FakeProvider())


def test_registry_rejects_unknown_provider():
    with pytest.raises(ProviderNotFoundError):
        ProviderRegistry().get("missing")


def test_adapter_contract_exposes_provider_neutral_metadata():
    adapter = FakeProvider()
    assert adapter.list_readers()[0].reader_id == "reader-1"
    assert adapter.list_cards()[0].provider_id == "example"
    assert adapter.list_certificates("card-1")[0].role is CertificateRole.SIGNING
    assert adapter.signing_mechanisms("card-1", "cert-1")[0].mechanism == "rsa-pkcs"


def test_registry_requires_normalized_provider_id():
    class BadProvider(FakeProvider):
        provider_id = "Example "
    with pytest.raises(ValueError, match="lowercase"):
        ProviderRegistry().register(BadProvider())
