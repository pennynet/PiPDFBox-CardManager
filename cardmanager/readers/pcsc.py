"""Provider-neutral PC/SC reader discovery.

Only reader metadata, card presence and ATR are exposed.
No APDUs, PINs, CANs, certificates or private keys are accessed.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass

from cardmanager.domain import Reader, ReaderState

logger = logging.getLogger(__name__)

class PcscError(RuntimeError):
    """Raised when PC/SC reader discovery fails."""


@dataclass(frozen=True, slots=True)
class PcscReaderInfo:
    reader: Reader
    card_present: bool
    atr: str | None


class PcscBackend:
    """Discover PC/SC readers and detect inserted cards."""

    def __init__(self, reader_provider=None) -> None:
        self._reader_provider = reader_provider

    def list_readers(self) -> tuple[PcscReaderInfo, ...]:
        try:
            from smartcard.Exceptions import (
                CardConnectionException,
                NoCardException,
            )
            from smartcard.System import readers as system_readers
        except ImportError as exc:
            raise PcscError(
                "PC/SC support requires the optional 'pcsc' extra"
            ) from exc

        if self._reader_provider is None:
            self._reader_provider = system_readers

        try:
            detected_readers = self._reader_provider()
        except Exception as exc:
            raise PcscError("PC/SC reader discovery failed") from exc

        results = []

        for pcsc_reader in detected_readers:
            name = str(pcsc_reader)
            display_name = self._display_name(name)
            reader_id = self._reader_id(display_name)

            reader = Reader(
                reader_id=reader_id,
                display_name=display_name,
                state=ReaderState.AVAILABLE,
            )

            connection = None

            try:
                connection = pcsc_reader.createConnection()
                connection.connect()
                atr_bytes = connection.getATR()
                atr = ":".join(f"{byte:02x}" for byte in atr_bytes)

                results.append(
                    PcscReaderInfo(
                        reader=reader,
                        card_present=True,
                        atr=atr,
                    )
                )

            except NoCardException:
                results.append(
                    PcscReaderInfo(
                        reader=reader,
                        card_present=False,
                        atr=None,
                    )
                )

            except Exception as exc:
                raise PcscError(
                    "PC/SC card detection failed"
                ) from exc

            finally:
                if connection is not None:
                    try:
                        connection.disconnect()
                    except CardConnectionException:
                        logger.warning("PC/SC connection could not be disconnected")

        return tuple(results)

    @staticmethod
    def _reader_id(name: str) -> str:
        digest = hashlib.sha256(name.encode("utf-8")).hexdigest()
        return f"pcsc:{digest[:16]}"

    @staticmethod
    def _display_name(name: str) -> str:
        # Reader serial numbers are not exposed in display metadata.
        clean_name = re.sub(r"\s+\([^)]*\)", "", name)
        clean_name = re.sub(r"\s+00\s+00$", "", clean_name)
        return clean_name.strip()

