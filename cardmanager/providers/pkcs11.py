"""Safe, read-only PKCS#11 token and signing-certificate discovery.

Only the D-TRUST Signature-PIN token is opened. The Authentication-PIN token
is deliberately ignored. Sessions are read-only and unauthenticated; no PIN,
private-key object, or signing operation is used.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable


class Pkcs11Error(RuntimeError):
    """Raised when a PKCS#11 module cannot be loaded or queried."""


@dataclass(frozen=True, slots=True)
class Pkcs11TokenInfo:
    """Non-secret token metadata; serial numbers are intentionally excluded."""

    label: str
    manufacturer_id: str
    model: str
    flags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Pkcs11SigningCertificate:
    """Public metadata for a signing certificate; raw DER and subject are omitted."""

    fingerprint_sha256: str
    issuer_display_name: str
    not_before: datetime
    not_after: datetime
    public_key_algorithm: str
    public_key_size_bits: int


class Pkcs11Module:
    """Load one configured PKCS#11 module and enumerate public metadata."""

    def __init__(
        self,
        module_path: str,
        library_loader: Callable[[str], object] | None = None,
    ) -> None:
        if not isinstance(module_path, str) or not module_path.strip():
            raise ValueError("module_path must be a non-empty path")
        self._module_path = module_path
        self._library_loader = library_loader

    def _load_library(self):
        loader = self._library_loader
        if loader is None:
            try:
                import pkcs11
            except ImportError as exc:
                raise Pkcs11Error(
                    "PKCS#11 support requires the optional 'pkcs11' extra"
                ) from exc
            loader = pkcs11.lib
        try:
            return loader(self._module_path)
        except Exception as exc:
            raise Pkcs11Error("PKCS#11 module could not be loaded") from None

    def list_tokens(self) -> tuple[Pkcs11TokenInfo, ...]:
        try:
            tokens: Iterable[object] = self._load_library().get_tokens()
            return tuple(
                Pkcs11TokenInfo(
                    label=_safe_text(getattr(token, "label", "")),
                    manufacturer_id=_safe_text(getattr(token, "manufacturer_id", "")),
                    model=_safe_text(getattr(token, "model", "")),
                    flags=_normalise_flags(getattr(token, "flags", ())),
                )
                for token in tokens
            )
        except Pkcs11Error:
            raise
        except Exception as exc:
            raise Pkcs11Error("PKCS#11 token discovery failed") from exc

    def list_signing_certificates(self) -> tuple[Pkcs11SigningCertificate, ...]:
        """Read signing certificates from the D-TRUST Signature-PIN token only.

        The method opens an unauthenticated, read-only PKCS#11 session. It
        never enumerates private keys, logs in, requests a PIN, or accesses the
        Authentication-PIN token.
        """
        try:
            from pkcs11 import Attribute, ObjectClass
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import (
                dsa, ec, ed25519, ed448, rsa,
            )
            from cryptography.x509.oid import NameOID

            tokens = tuple(self._load_library().get_tokens())
            signature_tokens = [
                token for token in tokens
                if "(signature-pin)" in _safe_text(getattr(token, "label", "")).lower()
                and _safe_text(getattr(token, "manufacturer_id", "")).lower().startswith("d-trust")
            ]
            if len(signature_tokens) != 1:
                raise Pkcs11Error(
                    "exactly one D-TRUST Signature-PIN token must be present"
                )

            discovered = []
            token = signature_tokens[0]
            with token.open(rw=False) as session:
                objects = session.get_objects({
                    Attribute.CLASS: ObjectClass.CERTIFICATE,
                })
                for obj in objects:
                    der = obj[Attribute.VALUE]
                    certificate = x509.load_der_x509_certificate(bytes(der))
                    try:
                        usage = certificate.extensions.get_extension_for_class(
                            x509.KeyUsage
                        ).value
                    except x509.ExtensionNotFound:
                        continue
                    if not (usage.digital_signature or usage.content_commitment):
                        continue

                    public_key = certificate.public_key()
                    if isinstance(public_key, rsa.RSAPublicKey):
                        algorithm, key_size = "RSA", public_key.key_size
                    elif isinstance(public_key, ec.EllipticCurvePublicKey):
                        algorithm, key_size = "EC", public_key.key_size
                    elif isinstance(public_key, dsa.DSAPublicKey):
                        algorithm, key_size = "DSA", public_key.key_size
                    elif isinstance(public_key, ed25519.Ed25519PublicKey):
                        algorithm, key_size = "ED25519", 256
                    elif isinstance(public_key, ed448.Ed448PublicKey):
                        algorithm, key_size = "ED448", 456
                    else:
                        continue

                    common_names = certificate.issuer.get_attributes_for_oid(
                        NameOID.COMMON_NAME
                    )
                    issuer = common_names[0].value if common_names else "Unknown issuer"
                    discovered.append(Pkcs11SigningCertificate(
                        fingerprint_sha256=certificate.fingerprint(hashes.SHA256()).hex(),
                        issuer_display_name=issuer,
                        not_before=certificate.not_valid_before_utc,
                        not_after=certificate.not_valid_after_utc,
                        public_key_algorithm=algorithm,
                        public_key_size_bits=key_size,
                    ))
            return tuple(discovered)
        except Pkcs11Error:
            raise
        except Exception as exc:
            raise Pkcs11Error(
                "D-TRUST signing-certificate discovery failed"
            ) from exc


def _safe_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalise_flags(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    try:
        values = tuple(value)
    except TypeError:
        values = (value,)
    names = {
        str(getattr(item, "name", None) or item).lower()
        for item in values
    }
    return tuple(sorted(names))
