from __future__ import annotations

import json
import threading
from collections import deque
from datetime import datetime

from django.conf import settings
from django.utils import timezone


_LOCK = threading.RLock()
_MESSAGES = deque(maxlen=30)
_STATE = {
    "enabled": False,
    "status": "disabled",
    "broker": "",
    "port": None,
    "topic": "",
    "last_error": "",
    "last_connected_at": None,
    "last_disconnected_at": None,
    "last_message_at": None,
    "reconnect_requested_at": None,
}


def _iso(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _public_state() -> dict:
    return {key: _iso(value) for key, value in _STATE.items()}


def configure(topic: str = "") -> None:
    with _LOCK:
        _STATE["enabled"] = bool(getattr(settings, "MQTT_ENABLED", False))
        _STATE["broker"] = getattr(settings, "MQTT_BROKER", "")
        _STATE["port"] = getattr(settings, "MQTT_PORT", None)
        _STATE["topic"] = topic
        if not _STATE["enabled"]:
            _STATE["status"] = "disabled"
            _STATE["last_error"] = "MQTT_ENABLED=False"
        elif _STATE["status"] == "disabled":
            _STATE["status"] = "disconnected"
            _STATE["last_error"] = ""


def set_connecting(topic: str = "") -> None:
    with _LOCK:
        configure(topic=topic)
        if _STATE["enabled"]:
            _STATE["status"] = "connecting"
            _STATE["last_error"] = ""


def set_connected(topic: str = "") -> None:
    with _LOCK:
        configure(topic=topic or _STATE.get("topic") or "")
        _STATE["status"] = "connected"
        _STATE["last_error"] = ""
        _STATE["last_connected_at"] = timezone.now()


def set_disconnected(reason: str = "") -> None:
    with _LOCK:
        configure(topic=_STATE.get("topic") or "")
        if _STATE["enabled"]:
            _STATE["status"] = "disconnected"
            _STATE["last_disconnected_at"] = timezone.now()
            if reason:
                _STATE["last_error"] = reason


def set_failed(error: str) -> None:
    with _LOCK:
        configure(topic=_STATE.get("topic") or "")
        if _STATE["enabled"]:
            _STATE["status"] = "failed"
            _STATE["last_error"] = str(error)
            _STATE["last_disconnected_at"] = timezone.now()


def request_reconnect() -> None:
    with _LOCK:
        configure(topic=_STATE.get("topic") or "")
        _STATE["reconnect_requested_at"] = timezone.now()
        if _STATE["enabled"]:
            _STATE["status"] = "connecting"
            _STATE["last_error"] = "reconnect requested"


def record_message(topic: str, payload: bytes | str) -> None:
    raw = payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else str(payload)
    parsed = None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None

    item = {
        "topic": topic,
        "payload": parsed if parsed is not None else raw,
        "raw": raw[:1200],
        "received_at": timezone.now().isoformat(),
    }
    with _LOCK:
        _STATE["last_message_at"] = timezone.now()
        _MESSAGES.appendleft(item)


def snapshot() -> dict:
    with _LOCK:
        configure(topic=_STATE.get("topic") or "")
        return {
            **_public_state(),
            "messages": list(_MESSAGES),
        }
