"""Initial D-TRUST adapter.

This module contains no direct PC/SC or PKCS#11 dependency. A concrete
middleware backend is injected by the service composition layer.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from cardmanager.domain import (
    Card,
    CardState,
    Certificate,
    CertificateRole,
    Reader,
    ReaderState,
    SigningMechanism,
)
from cardmanager.providers.base import ProviderError

# Observed during the initial hardware investigation. Keep matching
# configurable: ATR alone is not a globally unique product identifier.
DEFAULT_DTRUST_ATRS = frozenset({"3b:d2:18:00:81:31:fe:58:cb:01:16"})


@dataclass(frozen=True, slots=True)
class BackendReader:
    reader_id: str
    display_name: str
    state: ReaderState
    atr: str | None = None
    token_present: bool = False


@dataclass(frozen=True, slots=True)
class BackendCertificate:
    object_id: str
    fingerprint_sha256: str
    role: CertificateRole
    issuer_display_name: str | None
    not_before: datetime
    not_after: datetime
    public_key_algorithm: str
    public_key_size_bits: int


@dataclass(frozen=True, slots=True)
class BackendMechanism:
    algorithm: str
    mechanism: str
    key_algorithm: str
    key_size_bits: int


class DTrustBackend:
    """Narrow backend protocol implemented by the PC/SC/PKCS#11 integration."""

    def list_readers(self) -> tuple[BackendReader, ...]:
        raise NotImplementedError

    def list_certificates(self, reader_id: str) -> tuple[BackendCertificate, ...]:
        raise NotImplementedError

    def signing_mechanisms(self, reader_id: str, certificate_object_id: str) -> tuple[BackendMechanism, ...]:
        raise NotImplementedError


class DTrustAdapter:
    """D-TRUST card discovery and safe metadata adapter."""

    provider_id = "dtrust"

    def __init__(
        self,
        backend: DTrustBackend,
        supported_atrs: frozenset[str] = DEFAULT_DTRUST_ATRS,
    ) -> None:
        self._backend = backend
        self._supported_atrs = frozenset(_normalise_atr(atr) for atr in supported_atrs)

    def list_readers(self) -> tuple[Reader, ...]:
        try:
            return tuple(
                Reader(item.reader_id, item.display_name, item.state)
                for item in self._backend.list_readers()
            )
        except Exception as exc:
            raise ProviderError("D-TRUST reader discovery failed") from exc

    def list_cards(self) -> tuple[Card, ...]:
        try:
            cards = []
            for item in self._backend.list_readers():
                if not item.token_present or not item.atr:
                    continue
                if _normalise_atr(item.atr) not in self._supported_atrs:
                    continue
                # Reader ID is service-local and opaque. Do not expose token serials.
                card_id = f"dtrust:{item.reader_id}"
                cards.append(Card(
                    card_id=card_id,
                    reader_id=item.reader_id,
                    provider_id=self.provider_id,
                    card_type="dtrust-card",
                    display_name="D-TRUST smart card",
                    state=CardState.PRESENT,
                ))
            return tuple(cards)
        except Exception as exc:
            raise ProviderError("D-TRUST card discovery failed") from exc

    def list_certificates(self, card_id: str) -> tuple[Certificate, ...]:
        reader_id = _reader_id_from_card_id(card_id)
        try:
            return tuple(
                Certificate(
                    certificate_id=_certificate_id(item.fingerprint_sha256),
                    card_id=card_id,
                    role=item.role,
                    issuer_display_name=item.issuer_display_name,
                    not_before=item.not_before,
                    not_after=item.not_after,
                    public_key_algorithm=item.public_key_algorithm,
                    public_key_size_bits=item.public_key_size_bits,
                )
                for item in self._backend.list_certificates(reader_id)
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError("D-TRUST certificate metadata lookup failed") from exc

    def signing_mechanisms(self, card_id: str, certificate_id: str) -> tuple[SigningMechanism, ...]:
        reader_id = _reader_id_from_card_id(card_id)
        # Resolve the opaque certificate ID to a backend object only after
        # matching it against the certificate list for this reader.
        try:
            certificates = self._backend.list_certificates(reader_id)
            matches = [
                item for item in certificates
                if _certificate_id(item.fingerprint_sha256) == certificate_id
            ]
            if len(matches) != 1:
                raise ProviderError("D-TRUST certificate selection is missing or ambiguous")
            mechanisms = self._backend.signing_mechanisms(reader_id, matches[0].object_id)
            return tuple(
                SigningMechanism(
                    item.algorithm, item.mechanism, item.key_algorithm, item.key_size_bits,
                )
                for item in mechanisms
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError("D-TRUST mechanism discovery failed") from exc


def _normalise_atr(value: str) -> str:
    return value.strip().lower().replace(":", "").replace(" ", "")


def _certificate_id(fingerprint: str) -> str:
    value = fingerprint.strip().lower().replace(":", "")
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ProviderError("backend returned an invalid SHA-256 certificate fingerprint")
    return f"sha256:{value}"


def _reader_id_from_card_id(card_id: str) -> str:
    prefix, separator, reader_id = card_id.partition(":")
    if prefix != "dtrust" or not separator or not reader_id:
        raise ProviderError("card identifier does not belong to the D-TRUST adapter")
    return reader_id
