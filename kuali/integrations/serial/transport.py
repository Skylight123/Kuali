"""Low-level serial transport untuk Modbus RTU (RS-485).

Biasanya tidak dipakai langsung — ModbusGateway pakai pymodbus
yang sudah handle framing. File ini untuk kebutuhan raw serial
(mis. firmware debug, non-Modbus protocol).

Requires: pip install pyserial
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    import serial
except ImportError:
    serial = None  # type: ignore


class SerialTransport:
    """Raw RS-485 / serial byte transport."""

    def __init__(self, port: str = "/dev/ttyUSB0", baudrate: int = 9600,
                 timeout: float = 0.5):
        if serial is None:
            raise ImportError("pyserial tidak terinstall. Jalankan: pip install pyserial")

        self._ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
        )
        logger.info("Serial port %s terbuka @ %d baud", port, baudrate)

    def send(self, data: bytes) -> None:
        self._ser.write(data)

    def receive(self, length: int) -> bytes:
        return self._ser.read(length)

    def flush(self) -> None:
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()

    def close(self) -> None:
        if self._ser.is_open:
            self._ser.close()
