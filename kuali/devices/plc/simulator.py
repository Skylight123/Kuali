"""Fake PLC gateway — dipakai saat development tanpa hardware.

Mengembalikan format { "registers": { addr: value } } yang
sama persis dengan yang dikirim WebSocket ke frontend.
"""
from __future__ import annotations

import math
import time

from domain.ports import IPlcGateway
from . import registers as R


class SimulatorGateway(IPlcGateway):

    def read_all(self) -> dict:
        t = time.time()

        # Stirrer menyala bergantian setiap 8 detik
        stir1 = 1 if math.sin(t / 8) > 0 else 0
        stir2 = 1 if math.sin(t / 8 + math.pi) > 0 else 0

        # Conveyor menyala berurutan (simulasi metered feed)
        conveyors = {
            R.CONVEYOR_1: 1 if math.sin(t / 5)       > 0.3 else 0,
            R.CONVEYOR_2: 1 if math.sin(t / 5 + 1)   > 0.3 else 0,
            R.CONVEYOR_3: 1 if math.sin(t / 5 + 2)   > 0.3 else 0,
            R.CONVEYOR_4: 1 if math.sin(t / 5 + 3)   > 0.3 else 0,
            R.CONVEYOR_5: 1 if math.sin(t / 5 + 4)   > 0.3 else 0,
            R.CONVEYOR_6: 1 if math.sin(t / 5 + 5)   > 0.3 else 0,
        }

        return {
            "registers": {
                R.STIRRER_1: stir1,
                R.STIRRER_2: stir2,
                **conveyors,
                R.CMD_11: 1,
            }
        }

    def read_cooker(self, cooker_id: int):
        raise NotImplementedError("Simulator uses read_all() with register format")

    def read_conveyor(self, conveyor_id: int):
        raise NotImplementedError("Simulator uses read_all() with register format")

    def write_register(self, address: int, value: int) -> None:
        pass

    def close(self) -> None:
        pass
