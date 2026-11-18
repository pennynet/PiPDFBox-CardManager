"""Safe, read-only PKCS#11 token discovery.

This module deliberately does not open authenticated sessions, request PINs,
enumerate private-key objects or perform cryptographic operations.
"""
from __future__ import annotations

from dataclasses import dataclass
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


class Pkcs11Module:
    """Load one configured PKCS#11 module and enumerate public token metadata."""

    def __init__(
        self,
        module_path: str,
        library_loader: Callable[[str], object] | None = None,
    ) -> None:
        if not isinstance(module_path, str) or not module_path.strip():
            raise ValueError("module_path must be a non-empty path")
        self._module_path = module_path
        self._library_loader = library_loader

    def list_tokens(self) -> tuple[Pkcs11TokenInfo, ...]:
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
            library = loader(self._module_path)
            tokens: Iterable[object] = library.get_tokens()
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
            # Do not include low-level exception text: some middleware errors
            # may contain device or token identifiers.
            raise Pkcs11Error("PKCS#11 token discovery failed") from exc


def _safe_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalise_flags(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    try:
        values = tuple(value)  # PKCS#11 flag sets are iterable
    except TypeError:
        values = (value,)
    return tuple(sorted({str(item).lower() for item in values}))
