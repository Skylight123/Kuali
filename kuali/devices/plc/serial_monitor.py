from __future__ import annotations

import threading
from datetime import datetime

from django.conf import settings
from django.utils import timezone

from . import registers as R


_LOCK = threading.RLock()
_STATE = {
    "enabled": False,
    "status": "disabled",
    "mode": "",
    "endpoint": "",
    "slave_id": None,
    "last_error": "",
    "last_connected_at": None,
    "last_checked_at": None,
    "auto_connect": True,
    "auto_disconnect": False,
}


def _iso(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _endpoint() -> str:
    mode = getattr(settings, "MODBUS_MODE", "simulator")
    if mode == "tcp":
        return f"{getattr(settings, 'PLC_TCP_HOST', '')}:{getattr(settings, 'PLC_TCP_PORT', '')}"
    if mode == "simulator" or not getattr(settings, "PLC_ENABLED", False):
        return "simulator"
    return getattr(settings, "SERIAL_PORT", "")


def configure() -> None:
    with _LOCK:
        enabled = bool(getattr(settings, "PLC_ENABLED", False))
        mode = getattr(settings, "MODBUS_MODE", "simulator")
        _STATE["enabled"] = enabled
        _STATE["mode"] = mode
        _STATE["endpoint"] = _endpoint()
        _STATE["slave_id"] = R.default_slave_id()
        _STATE["auto_connect"] = bool(getattr(settings, "MODBUS_AUTO_CONNECT", True))
        _STATE["auto_disconnect"] = bool(getattr(settings, "MODBUS_AUTO_DISCONNECT", False))
        if not enabled or mode == "simulator":
            _STATE["status"] = "simulator"
            _STATE["last_error"] = ""
        elif _STATE["status"] in {"disabled", "simulator"}:
            _STATE["status"] = "disconnected"


def set_connecting() -> None:
    with _LOCK:
        configure()
        if _STATE["enabled"] and _STATE["mode"] != "simulator":
            _STATE["status"] = "connecting"
            _STATE["last_error"] = ""
            _STATE["last_checked_at"] = timezone.now()


def set_connected() -> None:
    with _LOCK:
        configure()
        _STATE["status"] = "connected"
        _STATE["last_error"] = ""
        now = timezone.now()
        _STATE["last_connected_at"] = now
        _STATE["last_checked_at"] = now


def set_failed(error: str) -> None:
    with _LOCK:
        configure()
        if _STATE["enabled"] and _STATE["mode"] != "simulator":
            _STATE["status"] = "failed"
            _STATE["last_error"] = str(error)
            _STATE["last_checked_at"] = timezone.now()


def set_disconnected(reason: str = "") -> None:
    with _LOCK:
        configure()
        if _STATE["enabled"] and _STATE["mode"] != "simulator":
            _STATE["status"] = "disconnected"
            _STATE["last_error"] = reason
            _STATE["last_checked_at"] = timezone.now()


def snapshot() -> dict:
    with _LOCK:
        configure()
        return {key: _iso(value) for key, value in _STATE.items()}
