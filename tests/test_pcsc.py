import pytest

from cardmanager.domain import ReaderState
from cardmanager.readers.pcsc import PcscBackend, PcscError


class FakeConnection:
    def __init__(self, atr=None, no_card=False):
        self.atr = atr
        self.no_card = no_card
        self.disconnected = False

    def connect(self):
        if self.no_card:
            from smartcard.Exceptions import NoCardException
            raise NoCardException("No card inserted", -1)

    def getATR(self):
        return self.atr

    def disconnect(self):
        self.disconnected = True


class FakeReader:
    def __init__(self, name, connection):
        self.name = name
        self.connection = connection

    def __str__(self):
        return self.name

    def createConnection(self):
        return self.connection


def test_detects_inserted_card_and_atr():
    connection = FakeConnection([0x3B, 0x01, 0x02])
    reader = FakeReader("Example Reader", connection)

    result = PcscBackend(reader_provider=lambda: [reader]).list_readers()

    assert len(result) == 1
    assert result[0].card_present is True
    assert result[0].atr == "3b:01:02"
    assert result[0].reader.state is ReaderState.AVAILABLE
    assert connection.disconnected is True


def test_detects_reader_without_card():
    connection = FakeConnection(no_card=True)
    reader = FakeReader("Example Reader", connection)

    result = PcscBackend(reader_provider=lambda: [reader]).list_readers()

    assert len(result) == 1
    assert result[0].card_present is False
    assert result[0].atr is None
    assert connection.disconnected is True


def test_reader_display_name_does_not_expose_serial():
    connection = FakeConnection([0x3B, 0x01])
    reader = FakeReader(
        "REINER SCT cyberJack RFID standard (ExampleSerial123)",
        connection,
    )

    result = PcscBackend(reader_provider=lambda: [reader]).list_readers()

    assert result[0].reader.display_name == "REINER SCT cyberJack RFID standard"
    assert "ExampleSerial123" not in result[0].reader.display_name


def test_reader_display_name_removes_pcsc_suffix():
    name = "REINER SCT cyberJack RFID standard (ExampleSerial123) 00 00"
    result = PcscBackend._display_name(name)

    assert result == "REINER SCT cyberJack RFID standard"
    assert "ExampleSerial123" not in result


def test_reader_id_is_independent_of_serial_number():
    reader_names = [
        "REINER SCT cyberJack RFID standard (SerialA123) 00 00",
        "REINER SCT cyberJack RFID standard (SerialB456) 00 00",
    ]

    readers = [
        FakeReader(name, FakeConnection([0x3B, 0x01]))
        for name in reader_names
    ]

    result = PcscBackend(
        reader_provider=lambda: readers
    ).list_readers()

    assert len(result) == 2
    assert result[0].reader.display_name == result[1].reader.display_name
    assert result[0].reader.reader_id == result[1].reader.reader_id


def test_connection_creation_failure_raises_pcsc_error():
    class BrokenReader:
        def __str__(self):
            return "Example Reader"

        def createConnection(self):
            raise RuntimeError("Connection creation failed")

    reader = BrokenReader()

    backend = PcscBackend(reader_provider=lambda: [reader])

    with pytest.raises(
        PcscError,
        match="PC/SC card detection failed",
    ):
        backend.list_readers()


def test_disconnect_failure_does_not_hide_detected_card(caplog):
    class BrokenDisconnectConnection(FakeConnection):
        def disconnect(self):
            from smartcard.Exceptions import CardConnectionException

            raise CardConnectionException("Disconnect failed")

    connection = BrokenDisconnectConnection([0x3B, 0x01])
    reader = FakeReader("Example Reader", connection)

    result = PcscBackend(
        reader_provider=lambda: [reader]
    ).list_readers()

    assert len(result) == 1
    assert result[0].card_present is True
    assert result[0].atr == "3b:01"
    assert "PC/SC connection could not be disconnected" in caplog.text
    assert "3b:01" not in caplog.text
