from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
from pathlib import Path

from django.conf import settings

from . import serial_monitor
from .poller import plc_poll_loop

logger = logging.getLogger(__name__)

_thread: threading.Thread | None = None
_SKIP_COMMANDS = {"check", "migrate", "makemigrations", "showmigrations", "test", "shell", "collectstatic", "createsuperuser"}
_SERVER_COMMANDS = {"daphne", "gunicorn", "uvicorn"}


def _argv_tokens() -> set[str]:
    return {Path(arg).name for arg in sys.argv if arg}


def _is_runserver_process(tokens: set[str]) -> bool:
    if "runserver" not in tokens:
        return False
    if os.environ.get("RUN_MAIN") == "true":
        return True
    return "--noreload" in tokens


def _is_server_process() -> bool:
    tokens = _argv_tokens()
    if tokens & _SKIP_COMMANDS:
        return False
    if _is_runserver_process(tokens):
        return True
    return bool(tokens & _SERVER_COMMANDS or os.environ.get("KUALI_START_BACKGROUND") == "1")


def should_start_poller() -> bool:
    if not bool(getattr(settings, "MODBUS_AUTO_CONNECT", True)):
        serial_monitor.set_disconnected("auto connect disabled")
        return False
    return _is_server_process()


def start_plc_poller() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    if not should_start_poller():
        return
    _thread = threading.Thread(target=_run, name="kuali-plc-poller", daemon=True)
    _thread.start()


def _run() -> None:
    interval = int(getattr(settings, "PLC_POLL_INTERVAL_MS", 500))
    try:
        asyncio.run(plc_poll_loop(interval_ms=interval))
    except Exception:
        logger.exception("PLC poller stopped")
