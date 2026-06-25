"""Fake PLC gateway - dipakai saat development tanpa hardware.

Mengembalikan format { "registers": { addr: value } } yang
sama persis dengan yang dikirim WebSocket ke frontend.
"""
from __future__ import annotations

import math
import time

from domain.ports import IPlcGateway
from . import registers as R
from . import serial_monitor


class SimulatorGateway(IPlcGateway):
    _holding_values: dict[int, int] = {R.CMD_9: 0, R.CMD_10: 0}
    _coil_values: dict[int, int] = {R.CMD_9: 0, R.CMD_10: 0}

    def __init__(self):
        serial_monitor.configure()

    def _snapshot_registers(self) -> dict[int, int]:
        t = time.time()

        stir1 = 1 if math.sin(t / 8) > 0 else 0
        stir2 = 1 if math.sin(t / 8 + math.pi) > 0 else 0

        conveyors = {
            R.CONVEYOR_1: 1 if math.sin(t / 5)       > 0.3 else 0,
            R.CONVEYOR_2: 1 if math.sin(t / 5 + 1)   > 0.3 else 0,
            R.CONVEYOR_3: 1 if math.sin(t / 5 + 2)   > 0.3 else 0,
            R.CONVEYOR_4: 1 if math.sin(t / 5 + 3)   > 0.3 else 0,
            R.CONVEYOR_5: 1 if math.sin(t / 5 + 4)   > 0.3 else 0,
            R.CONVEYOR_6: 1 if math.sin(t / 5 + 5)   > 0.3 else 0,
        }
        registers = {
            R.STIRRER_1: stir1,
            R.STIRRER_2: stir2,
            **conveyors,
            R.CMD_11: 1,
        }
        registers.update(self._holding_values)
        return registers

    def read_all(self) -> dict:
        return {"registers": self._snapshot_registers(), "serial_status": serial_monitor.snapshot()}

    def read_cooker(self, cooker_id: int):
        raise NotImplementedError("Simulator uses read_all() with register format")

    def read_conveyor(self, conveyor_id: int):
        raise NotImplementedError("Simulator uses read_all() with register format")

    def remote_read(self, function_code: int, address: int, quantity: int = 1) -> dict:
        function_code = int(function_code)
        address = int(address)
        quantity = max(1, int(quantity or 1))
        R.validate_remote_access(function_code, address, quantity)

        if function_code in (R.READ_COIL, R.READ_DISCRETE_INPUT):
            values = [int(self._coil_values.get(addr, 0)) for addr in range(address, address + quantity)]
        elif function_code in (R.READ_HOLDING, R.READ_INPUT):
            snapshot = self._snapshot_registers()
            values = [int(snapshot.get(addr, 0)) for addr in range(address, address + quantity)]
        else:
            raise ValueError("Function code bukan operasi read")

        return {
            "function_code": function_code,
            "address": address,
            "quantity": quantity,
            "values": values,
            "serial_status": serial_monitor.snapshot(),
        }

    def remote_write(self, function_code: int, address: int, values) -> dict:
        function_code = int(function_code)
        address = int(address)
        if not isinstance(values, list):
            values = [values]
        values = [int(value) for value in values]
        R.validate_remote_access(function_code, address, len(values))

        if function_code in (R.WRITE_SINGLE_COIL, R.WRITE_MULTIPLE_COIL):
            for offset, value in enumerate(values):
                self._coil_values[address + offset] = 1 if value else 0
        elif function_code in (R.WRITE_SINGLE_REGISTER, R.WRITE_MULTIPLE_REGISTER):
            for offset, value in enumerate(values):
                self._holding_values[address + offset] = int(value)
        else:
            raise ValueError("Function code bukan operasi write")

        return {
            "function_code": function_code,
            "address": address,
            "quantity": len(values),
            "values": values,
            "serial_status": serial_monitor.snapshot(),
        }

    def write_register(self, address: int, value: int) -> None:
        R.validate_remote_access(R.WRITE_SINGLE_REGISTER, address, 1)
        self._holding_values[int(address)] = int(value)

    def write_command(self, address: int, value: int) -> None:
        R.validate_remote_access(R.WRITE_SINGLE_COIL, address, 1)
        self._coil_values[int(address)] = 1 if int(value) else 0

    def close(self) -> None:
        pass
