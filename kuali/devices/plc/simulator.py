"""Fake PLC gateway — dipakai saat development tanpa hardware."""
from __future__ import annotations

import math
import time

from domain.models import CookerState, ConveyorStatus
from domain.models.cooker import CookerMode, BatchState
from domain.models.conveyor import ConveyorState
from domain.ports import IPlcGateway


class SimulatorGateway(IPlcGateway):
    """Generates realistic-looking plant state without any real hardware."""

    def read_cooker(self, cooker_id: int) -> CookerState:
        t = time.time()
        offset = cooker_id * 10
        temp = 200 + 25 * math.sin((t + offset) / 8)
        progress = int((t * 3 + offset) % 100)
        return CookerState(
            id=cooker_id,
            mode=CookerMode.COOKING,
            temp_current=round(temp, 1),
            temp_setpoint=225.0,
            batch=BatchState.COOKING,
            progress=progress,
            runtime_s=int(t + offset) % 120,
        )

    def read_conveyor(self, conveyor_id: int) -> ConveyorStatus:
        t = time.time()
        speed = 60 + 20 * math.sin((t + conveyor_id * 5) / 6)
        return ConveyorStatus(
            id=conveyor_id,
            state=ConveyorState.RUNNING,
            speed_pct=int(speed),
            load_pct=int(40 + 20 * math.sin((t + conveyor_id * 3) / 4)),
        )

    def read_all(self) -> dict:
        return {
            "cookers": [vars(self.read_cooker(i)) for i in range(1, 3)],
            "conveyors": [vars(self.read_conveyor(i)) for i in range(1, 4)],
        }

    def write_register(self, address: int, value: int) -> None:
        pass  # no-op in simulator

    def close(self) -> None:
        pass
