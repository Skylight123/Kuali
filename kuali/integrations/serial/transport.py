"""Modbus RTU serial transport adapter.

Adapter ini sengaja membungkus pymodbus agar detail koneksi RTU serial
tidak tersebar ke layer PLC gateway. Konfigurasi nilainya diambil dari
settings.py oleh caller, lalu diteruskan ke class ini.
"""
from __future__ import annotations

import logging
import threading
from typing import Iterable

logger = logging.getLogger(__name__)
serial_lock = threading.RLock()

try:
    from pymodbus.client import ModbusSerialClient as ModbusClient
except ImportError:
    ModbusClient = None  # type: ignore


class SerialTransport:
    """Modbus RTU transport using pymodbus SerialClient."""

    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 9600,
        timeout: float = 5,
        parity: str = "N",
        stopbits: int = 1,
        bytesize: int = 8,
    ):
        if ModbusClient is None:
            raise ImportError("pymodbus tidak terinstall. Jalankan: pip install pymodbus pyserial")

        self._client = ModbusClient(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            parity=parity,
            stopbits=stopbits,
            bytesize=bytesize,
        )
        logger.info("Modbus RTU serial configured on %s @ %d baud", port, baudrate)

    def connect(self) -> bool:
        return bool(self._client.connect())

    def close(self) -> None:
        self._client.close()

    def read_coils(self, address: int, *, count: int = 1, slave: int = 1):
        return self._client.read_coils(address, count=count, slave=slave)

    def read_discrete_inputs(self, address: int, *, count: int = 1, slave: int = 1):
        return self._client.read_discrete_inputs(address, count=count, slave=slave)

    def read_holding_registers(self, address: int, *, count: int = 1, slave: int = 1):
        return self._client.read_holding_registers(address, count=count, slave=slave)

    def read_input_registers(self, address: int, *, count: int = 1, slave: int = 1):
        return self._client.read_input_registers(address, count=count, slave=slave)

    def write_coil(self, address: int, value: bool, *, slave: int = 1):
        return self._client.write_coil(address, bool(value), slave=slave)

    def write_register(self, address: int, value: int, *, slave: int = 1):
        return self._client.write_register(address, int(value), slave=slave)

    def write_coils(self, address: int, values: Iterable[bool], *, slave: int = 1):
        return self._client.write_coils(address, [bool(value) for value in values], slave=slave)

    def write_registers(self, address: int, values: Iterable[int], *, slave: int = 1):
        return self._client.write_registers(address, [int(value) for value in values], slave=slave)
