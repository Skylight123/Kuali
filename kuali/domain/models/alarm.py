from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AlarmLevel(str, Enum):
    INFO = "info"
    WARN = "warn"
    FAULT = "fault"


@dataclass
class Alarm:
    code: int
    level: AlarmLevel
    message: str
    source: str                      # e.g. "cooker_1", "conveyor_2"
    ts: datetime = field(default_factory=datetime.now)
    acked: bool = False
