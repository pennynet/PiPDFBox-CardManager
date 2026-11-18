from datetime import UTC, datetime

import pytest

from cardmanager.domain import CertificateRole, ReaderState
from cardmanager.providers.base import ProviderError
from cardmanager.providers.dtrust import (
    BackendCertificate,
    BackendMechanism,
    BackendReader,
    DTrustAdapter,
)

NOW = datetime.now(UTC)
FINGERPRINT = "a" * 64


class MockBackend:
    def __init__(self):
        self.readers = (
            BackendReader(
                "reader-1", "Mock contactless reader", ReaderState.AVAILABLE,
                atr="3b:d2:18:00:81:31:fe:58:cb:01:16", token_present=True,
            ),
            BackendReader(
                "reader-2", "Other reader", ReaderState.AVAILABLE,
                atr="3b:00:00:00", token_present=True,
            ),
            BackendReader(
                "reader-3", "Empty reader", ReaderState.AVAILABLE,
                atr=None, token_present=False,
            ),
        )
        self.certificate = BackendCertificate(
            object_id="backend-object-7",
            fingerprint_sha256=FINGERPRINT,
            role=CertificateRole.SIGNING,
            issuer_display_name="Example issuing CA",
            not_before=NOW,
            not_after=NOW.replace(year=NOW.year + 1),
            public_key_algorithm="RSA",
            public_key_size_bits=3072,
        )
        self.requested_object_id = None

    def list_readers(self):
        return self.readers

    def list_certificates(self, reader_id):
        assert reader_id == "reader-1"
        return (self.certificate,)

    def signing_mechanisms(self, reader_id, certificate_object_id):
        self.requested_object_id = certificate_object_id
        return (BackendMechanism("sha256", "rsa-pkcs", "RSA", 3072),)


def test_adapter_lists_all_readers_but_only_matching_present_cards():
    adapter = DTrustAdapter(MockBackend())
    assert len(adapter.list_readers()) == 3
    cards = adapter.list_cards()
    assert len(cards) == 1
    assert cards[0].provider_id == "dtrust"
    assert cards[0].card_id == "dtrust:reader-1"


def test_adapter_maps_safe_certificate_metadata():
    adapter = DTrustAdapter(MockBackend())
    certs = adapter.list_certificates("dtrust:reader-1")
    assert len(certs) == 1
    assert certs[0].certificate_id == f"sha256:{FINGERPRINT}"
    assert certs[0].role is CertificateRole.SIGNING
    assert not hasattr(certs[0], "subject_name")


def test_adapter_resolves_certificate_before_listing_mechanisms():
    backend = MockBackend()
    adapter = DTrustAdapter(backend)
    mechanisms = adapter.signing_mechanisms("dtrust:reader-1", f"sha256:{FINGERPRINT}")
    assert mechanisms[0].mechanism == "rsa-pkcs"
    assert backend.requested_object_id == "backend-object-7"


def test_adapter_rejects_unknown_certificate_id():
    adapter = DTrustAdapter(MockBackend())
    with pytest.raises(ProviderError, match="missing or ambiguous"):
        adapter.signing_mechanisms("dtrust:reader-1", "sha256:" + "b" * 64)


def test_adapter_rejects_card_ids_from_other_providers():
    adapter = DTrustAdapter(MockBackend())
    with pytest.raises(ProviderError, match="does not belong"):
        adapter.list_certificates("other:reader-1")


def test_adapter_fails_closed_on_invalid_backend_fingerprint():
    backend = MockBackend()
    backend.certificate = BackendCertificate(
        object_id="bad", fingerprint_sha256="not-a-fingerprint",
        role=CertificateRole.SIGNING, issuer_display_name=None,
        not_before=NOW, not_after=NOW.replace(year=NOW.year + 1),
        public_key_algorithm="RSA", public_key_size_bits=3072,
    )
    adapter = DTrustAdapter(backend)
    with pytest.raises(ProviderError, match="invalid SHA-256"):
        adapter.list_certificates("dtrust:reader-1")


def test_adapter_does_not_expose_private_key_or_pin_methods():
    adapter = DTrustAdapter(MockBackend())
    assert not hasattr(adapter, "sign")
    assert not hasattr(adapter, "submit_pin")
