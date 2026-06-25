from __future__ import annotations

from django.conf import settings

from .modbus_gateway import ModbusGateway
from .simulator import SimulatorGateway


def build_plc_gateway():
    if not getattr(settings, "PLC_ENABLED", False) or settings.MODBUS_MODE == "simulator":
        return SimulatorGateway()
    return ModbusGateway()
