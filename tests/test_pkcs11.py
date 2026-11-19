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
