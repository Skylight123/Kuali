"""Production Modbus gateway — requires pymodbus + pyserial.

Config diambil dari settings.py (bersumber dari .env):
    PLC_MODE        : 'rtu' | 'tcp'
    SERIAL_PORT     : e.g. '/dev/ttyUSB0'
    SERIAL_BAUDRATE : e.g. 9600
    SERIAL_UNIT     : Modbus slave/unit ID
    PLC_TCP_HOST    : IP PLC (mode tcp)
    PLC_TCP_PORT    : port TCP (default 502)
"""
from __future__ import annotations

from django.conf import settings

from domain.models import CookerState, ConveyorStatus
from domain.models.cooker import CookerMode, BatchState
from domain.models.conveyor import ConveyorState
from domain.ports import IPlcGateway
from . import registers as R

try:
    from pymodbus.client import ModbusSerialClient, ModbusTcpClient
except ImportError:
    ModbusSerialClient = ModbusTcpClient = None  # type: ignore


class ModbusGateway(IPlcGateway):

    def __init__(self):
        if ModbusSerialClient is None:
            raise ImportError("pymodbus tidak terinstall. Jalankan: pip install pymodbus pyserial")

        self._unit = settings.SERIAL_UNIT

        if settings.PLC_MODE == "tcp":
            self._client = ModbusTcpClient(settings.PLC_TCP_HOST, port=settings.PLC_TCP_PORT)
        else:
            self._client = ModbusSerialClient(
                port=settings.SERIAL_PORT,
                baudrate=settings.SERIAL_BAUDRATE,
                stopbits=1,
                bytesize=8,
                parity="N",
            )
        self._client.connect()

    # ------------------------------------------------------------------
    def _read(self, address: int, count: int = 1) -> list[int]:
        result = self._client.read_holding_registers(address, count=count, slave=self._unit)
        if result.isError():
            raise ConnectionError(f"Modbus read error @ {address:#06x}")
        return result.registers

    def _write(self, address: int, value: int) -> None:
        self._client.write_register(address, value, slave=self._unit)

    # ------------------------------------------------------------------
    def read_cooker(self, cooker_id: int) -> CookerState:
        raise NotImplementedError("Kuali HMI uses read_all() register snapshots for cooker state")

    def read_conveyor(self, conveyor_id: int) -> ConveyorStatus:
        raise NotImplementedError("Kuali HMI uses read_all() register snapshots for conveyor state")

    def read_all(self) -> dict:
        start = min(R.ALL_ADDRS)
        end = max(R.ALL_ADDRS)
        values = self._read(start, count=end - start + 1)
        registers = {
            address: values[address - start]
            for address in R.ALL_ADDRS
        }
        return {"registers": registers}

    def write_register(self, address: int, value: int) -> None:
        self._write(address, value)

    def close(self) -> None:
        self._client.close()
