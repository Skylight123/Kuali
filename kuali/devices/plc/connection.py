from __future__ import annotations

import logging
from typing import Callable, TypeVar

from django.conf import settings

from integrations.serial.transport import serial_lock
from . import serial_monitor
from .factory import build_plc_gateway

logger = logging.getLogger(__name__)
T = TypeVar("T")

_gateway = None


def _auto_disconnect() -> bool:
    return bool(getattr(settings, "MODBUS_AUTO_DISCONNECT", False))


def _uses_real_plc() -> bool:
    return bool(getattr(settings, "PLC_ENABLED", False)) and getattr(settings, "MODBUS_MODE", "simulator") != "simulator"


def _close_current_locked(reason: str = "") -> None:
    global _gateway
    if _gateway is not None:
        try:
            _gateway.close()
        finally:
            _gateway = None
    if _uses_real_plc():
        serial_monitor.set_disconnected(reason)


def with_gateway(action: Callable[[object], T], *, force_new: bool = False) -> T:
    """Run a PLC action under the same serial lock used by scanner-style code."""
    global _gateway
    with serial_lock:
        if force_new:
            _close_current_locked("manual reconnect")

        close_after = _auto_disconnect()
        gateway = None
        if close_after:
            gateway = build_plc_gateway()
        else:
            if _gateway is None:
                _gateway = build_plc_gateway()
            gateway = _gateway

        try:
            return action(gateway)
        finally:
            if close_after:
                gateway.close()
                if _uses_real_plc():
                    serial_monitor.set_disconnected("auto disconnect")


def reconnect(test_read: bool = True) -> dict:
    def _probe(gateway):
        snapshot = gateway.read_all() if test_read else {}
        return {
            "ok": True,
            "snapshot": snapshot,
            "serial_status": serial_monitor.snapshot(),
        }

    return with_gateway(_probe, force_new=True)


def disconnect(reason: str = "manual disconnect") -> dict:
    with serial_lock:
        _close_current_locked(reason)
        return {"ok": True, "serial_status": serial_monitor.snapshot()}
