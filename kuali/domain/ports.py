from abc import ABC, abstractmethod
from .models import CookerState, ConveyorStatus, Alarm


class IPlcGateway(ABC):
    """Abstraction for reading/writing PLC registers.
    Implemented by ModbusGateway (production) or SimulatorGateway (dev).
    """

    @abstractmethod
    def read_all(self) -> dict:
        """Return full plant snapshot as a plain dict (JSON-serialisable)."""
        ...

    @abstractmethod
    def read_cooker(self, cooker_id: int) -> CookerState:
        ...

    @abstractmethod
    def read_conveyor(self, conveyor_id: int) -> ConveyorStatus:
        ...

    @abstractmethod
    def write_register(self, address: int, value: int) -> None:
        ...

    @abstractmethod
    def write_command(self, address: int, value: int) -> None:
        ...

    @abstractmethod
    def remote_read(self, function_code: int, address: int, quantity: int = 1) -> dict:
        ...

    @abstractmethod
    def remote_write(self, function_code: int, address: int, values) -> dict:
        ...

    @abstractmethod
    def close(self) -> None:
        ...


class IBroker(ABC):
    """Abstraction for publishing plant state to a message broker (MQTT, etc.)."""

    @abstractmethod
    def publish(self, topic: str, payload: dict) -> None:
        ...

    @abstractmethod
    def close(self) -> None:
        ...
