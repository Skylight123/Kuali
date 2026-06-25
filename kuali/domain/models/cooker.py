from dataclasses import dataclass, field
from enum import Enum


class CookerMode(str, Enum):
    IDLE = "idle"
    HEATING = "heating"
    COOKING = "cooking"
    FAULT = "fault"


class BatchState(str, Enum):
    EMPTY = "empty"
    LOADING = "loading"
    COOKING = "cooking"
    DONE = "done"


@dataclass
class CookerState:
    id: int                          # 1 or 2
    mode: CookerMode = CookerMode.IDLE
    temp_current: float = 0.0        # °C, from PLC register
    temp_setpoint: float = 225.0     # °C
    batch: BatchState = BatchState.EMPTY
    progress: int = 0                # 0–100 %
    runtime_s: int = 0               # seconds in current batch
    fault_code: int = 0              # 0 = no fault

    @property
    def is_running(self) -> bool:
        return self.mode in (CookerMode.HEATING, CookerMode.COOKING)
