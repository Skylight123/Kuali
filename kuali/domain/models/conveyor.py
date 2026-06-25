from dataclasses import dataclass
from enum import Enum


class ConveyorState(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    FAULT = "fault"


@dataclass
class ConveyorStatus:
    id: int                          # 1, 2, or 3
    state: ConveyorState = ConveyorState.STOPPED
    speed_pct: int = 0               # 0–100 %
    load_pct: int = 0                # belt load estimate
    fault_code: int = 0
