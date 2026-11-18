from datetime import UTC, datetime

import pytest

from cardmanager.domain import (
    Card,
    CardState,
    Certificate,
    CertificateRole,
    Reader,
    ReaderState,
    SigningMechanism,
)


def test_reader_model_accepts_available_reader():
    reader = Reader("reader-1", "Smart-card reader", ReaderState.AVAILABLE)
    assert reader.reader_id == "reader-1"
    assert reader.state is ReaderState.AVAILABLE


def test_card_model_is_provider_neutral():
    card = Card(
        card_id="card-1",
        reader_id="reader-1",
        provider_id="example-provider",
        card_type="example-card",
        display_name="Smart card",
        state=CardState.PRESENT,
    )
    assert card.provider_id == "example-provider"
    assert card.state is CardState.PRESENT


def test_signing_mechanism_requires_positive_key_size():
    with pytest.raises(ValueError, match="positive"):
        SigningMechanism("sha256", "rsa-pkcs", "RSA", 0)


def test_certificate_requires_timezone_aware_validity():
    with pytest.raises(ValueError, match="timezone-aware"):
        Certificate(
            "cert-1", "card-1", CertificateRole.SIGNING, None,
            datetime(2026, 1, 1), datetime(2027, 1, 1),
            "RSA", 3072,
        )


def test_certificate_validity_order_is_checked():
    now = datetime.now(UTC)
    with pytest.raises(ValueError, match="later"):
        Certificate(
            "cert-1", "card-1", CertificateRole.SIGNING, None,
            now, now, "RSA", 3072,
        )


def test_domain_objects_are_immutable():
    reader = Reader("reader-1", "Smart-card reader", ReaderState.BUSY)
    with pytest.raises(AttributeError):
        reader.display_name = "Changed"
