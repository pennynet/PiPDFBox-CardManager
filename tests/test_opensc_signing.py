import asyncio

import pytest
from asn1crypto import x509 as asn1_x509
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from cardmanager.signing.opensc import (
    OpenSCPdfSigner,
    OpenSCPdfSigningError,
    _OpenSCExternalSigner,
)


def make_certificate():
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test CA")])
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=30))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.DER)


def test_signer_rejects_relative_module_path():
    with pytest.raises(ValueError, match="absolute path"):
        OpenSCPdfSigner("opensc.so", make_certificate())


def test_signer_rejects_invalid_certificate():
    with pytest.raises(ValueError, match="invalid RSA"):
        OpenSCPdfSigner("/opensc.so", b"not a certificate")


def test_signer_rejects_empty_key_id():
    with pytest.raises(ValueError, match="key_id"):
        OpenSCPdfSigner("/opensc.so", make_certificate(), key_id=b"")


def test_dry_run_returns_rsa_sized_placeholder():
    cert = asn1_x509.Certificate.load(make_certificate())
    signer = _OpenSCExternalSigner(
        cert, 384, "/opensc.so", "/pkcs11-tool", 1, b"\x02"
    )
    result = asyncio.run(signer.async_sign_raw(b"data", "sha256", dry_run=True))
    assert result == b"\x00" * 384


def test_external_signer_rejects_unsupported_digest():
    cert = asn1_x509.Certificate.load(make_certificate())
    signer = _OpenSCExternalSigner(
        cert, 384, "/opensc.so", "/pkcs11-tool", 1, b"\x02"
    )
    with pytest.raises(OpenSCPdfSigningError, match="SHA-256"):
        asyncio.run(signer.async_sign_raw(b"data", "sha384"))


def test_sign_pdf_does_not_overwrite_existing_output(tmp_path):
    cert = make_certificate()
    source = tmp_path / "input.pdf"
    output = tmp_path / "signed.pdf"
    source.write_bytes(b"%PDF-test")
    output.write_bytes(b"keep this file")

    signer = OpenSCPdfSigner("/opensc.so", cert)
    with pytest.raises(FileExistsError):
        signer.sign_pdf(source, output)

    assert output.read_bytes() == b"keep this file"
