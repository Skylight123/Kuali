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
        result = self._client.read_holding_registers(address, count, slave=self._unit)
        if result.isError():
            raise ConnectionError(f"Modbus read error @ {address:#06x}")
        return result.registers

    def _write(self, address: int, value: int) -> None:
        self._client.write_register(address, value, slave=self._unit)

    # ------------------------------------------------------------------
    def read_cooker(self, cooker_id: int) -> CookerState:
        base = R.C1_TEMP_PV if cooker_id == 1 else R.C2_TEMP_PV
        regs = self._read(base, count=7)
        return CookerState(
            id=cooker_id,
            temp_current=regs[0] / 10.0,
            temp_setpoint=regs[1] / 10.0,
            mode=CookerMode(list(CookerMode)[regs[2]].value),
            batch=BatchState(list(BatchState)[regs[3]].value),
            progress=regs[4],
            runtime_s=regs[5],
            fault_code=regs[6],
        )

    def read_conveyor(self, conveyor_id: int) -> ConveyorStatus:
        bases = {1: R.CV1_STATE, 2: R.CV2_STATE, 3: R.CV3_STATE}
        regs = self._read(bases[conveyor_id], count=4)
        return ConveyorStatus(
            id=conveyor_id,
            state=list(ConveyorState)[regs[0]],
            speed_pct=regs[1],
            load_pct=regs[2],
            fault_code=regs[3],
        )

    def read_all(self) -> dict:
        return {
            "cookers": [
                vars(self.read_cooker(1)),
                vars(self.read_cooker(2)),
            ],
            "conveyors": [
                vars(self.read_conveyor(i)) for i in range(1, 4)
            ],
        }

    def write_register(self, address: int, value: int) -> None:
        self._write(address, value)

    def close(self) -> None:
        self._client.close()
