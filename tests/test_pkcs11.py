from dataclasses import dataclass
from enum import IntEnum

import pytest

from cardmanager.providers.pkcs11 import Pkcs11Error, Pkcs11Module


@dataclass
class FakeToken:
    label: str = "D-TRUST Signature Token"
    manufacturer_id: str = "Example Manufacturer"
    model: str = "Card Model"
    flags: tuple[str, ...] = ("TOKEN_INITIALIZED", "LOGIN_REQUIRED")


class FakeLibrary:
    def __init__(self, tokens):
        self._tokens = tokens

    def get_tokens(self):
        return iter(self._tokens)


def test_lists_safe_token_metadata_without_serial_number():
    module = Pkcs11Module(
        "/usr/lib/example-pkcs11.so",
        library_loader=lambda path: FakeLibrary([FakeToken()]),
    )

    tokens = module.list_tokens()

    assert len(tokens) == 1
    assert tokens[0].label == "D-TRUST Signature Token"
    assert tokens[0].manufacturer_id == "Example Manufacturer"
    assert tokens[0].model == "Card Model"
    assert tokens[0].flags == ("login_required", "token_initialized")
    assert not hasattr(tokens[0], "serial_number")


def test_empty_module_returns_empty_tuple():
    module = Pkcs11Module(
        "/usr/lib/example-pkcs11.so",
        library_loader=lambda path: FakeLibrary([]),
    )

    assert module.list_tokens() == ()


def test_invalid_module_path_is_rejected():
    with pytest.raises(ValueError, match="module_path"):
        Pkcs11Module(" ")


def test_loader_errors_are_wrapped_without_leaking_low_level_text():
    def broken_loader(path):
        raise RuntimeError("device serial SECRET-123")

    module = Pkcs11Module("/usr/lib/example-pkcs11.so", library_loader=broken_loader)

    with pytest.raises(Pkcs11Error, match="token discovery failed") as error:
        module.list_tokens()

    assert "SECRET-123" not in str(error.value)


def test_token_enumeration_does_not_require_session_or_pin():
    token = FakeToken()
    module = Pkcs11Module(
        "/usr/lib/example-pkcs11.so",
        library_loader=lambda path: FakeLibrary([token]),
    )

    result = module.list_tokens()

    assert result[0].label == token.label
    assert not hasattr(module, "open_session")
    assert not hasattr(module, "sign")


class FakeTokenFlag(IntEnum):
    LOGIN_REQUIRED = 4
    TOKEN_INITIALIZED = 1024


def test_integer_enum_flags_are_reported_by_name():
    module = Pkcs11Module(
        "/usr/lib/example-pkcs11.so",
        library_loader=lambda path: FakeLibrary([
            FakeToken(flags=(FakeTokenFlag.TOKEN_INITIALIZED, FakeTokenFlag.LOGIN_REQUIRED))
        ]),
    )

    tokens = module.list_tokens()

    assert tokens[0].flags == ("login_required", "token_initialized")


from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from pkcs11 import Attribute, ObjectClass

from cardmanager.providers.pkcs11 import Pkcs11Error


class FakeCertificateObject:
    def __init__(self, der):
        self.der = der

    def __getitem__(self, attribute):
        assert attribute is Attribute.VALUE
        return self.der


class FakeSession:
    def __init__(self, objects):
        self.objects = objects

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get_objects(self, query):
        assert query == {Attribute.CLASS: ObjectClass.CERTIFICATE}
        return iter(self.objects)


class FakePkcs11Token:
    def __init__(self, label, manufacturer_id, objects=()):
        self.label = label
        self.manufacturer_id = manufacturer_id
        self.objects = objects
        self.opened = False

    def open(self, rw=False):
        assert rw is False
        self.opened = True
        return FakeSession(self.objects)


class FakePkcs11Library:
    def __init__(self, tokens):
        self.tokens = tokens

    def get_tokens(self):
        return iter(self.tokens)


def make_signing_certificate_der():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "D-TRUST Test CA")])
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Do not expose subject")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=365))
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=True,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(private_key, hashes.SHA256())
    )
    return certificate.public_bytes(serialization.Encoding.DER)


def test_reads_signing_certificate_from_signature_token_only():
    signature = FakePkcs11Token(
        "D-TRUST Card (Signature-PIN)",
        "D-TRUST GmbH (C)",
        [FakeCertificateObject(make_signing_certificate_der())],
    )
    authentication = FakePkcs11Token(
        "D-TRUST Card (Authentication-PIN)",
        "D-TRUST GmbH (C)",
    )
    module = Pkcs11Module(
        "/usr/lib/example-pkcs11.so",
        library_loader=lambda path: FakePkcs11Library([signature, authentication]),
    )

    certificates = module.list_signing_certificates()

    assert len(certificates) == 1
    assert certificates[0].issuer_display_name == "D-TRUST Test CA"
    assert certificates[0].public_key_algorithm == "RSA"
    assert certificates[0].public_key_size_bits == 2048
    assert certificates[0].fingerprint_sha256
    assert certificates[0].not_before.tzinfo is not None
    assert certificates[0].not_after.tzinfo is not None
    assert not hasattr(certificates[0], "subject_name")
    assert signature.opened is True
    assert authentication.opened is False


def test_signing_certificate_discovery_fails_closed_without_signature_token():
    authentication = FakePkcs11Token(
        "D-TRUST Card (Authentication-PIN)",
        "D-TRUST GmbH (C)",
    )
    module = Pkcs11Module(
        "/usr/lib/example-pkcs11.so",
        library_loader=lambda path: FakePkcs11Library([authentication]),
    )

    with pytest.raises(Pkcs11Error, match="Signature-PIN token"):
        module.list_signing_certificates()

    assert authentication.opened is False


def test_signing_certificate_discovery_does_not_open_ambiguous_signature_tokens():
    first = FakePkcs11Token("D-TRUST (Signature-PIN)", "D-TRUST GmbH")
    second = FakePkcs11Token("D-TRUST (Signature-PIN)", "D-TRUST GmbH")
    module = Pkcs11Module(
        "/usr/lib/example-pkcs11.so",
        library_loader=lambda path: FakePkcs11Library([first, second]),
    )

    with pytest.raises(Pkcs11Error, match="exactly one"):
        module.list_signing_certificates()

    assert first.opened is False
    assert second.opened is False
