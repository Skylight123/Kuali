from __future__ import annotations

import asyncio
import logging
import sys
import threading

from django.conf import settings

from .factory import build_plc_gateway
from .poller import plc_poll_loop

logger = logging.getLogger(__name__)

_thread: threading.Thread | None = None
_SKIP_COMMANDS = {"check", "migrate", "makemigrations", "showmigrations", "test", "shell", "collectstatic", "createsuperuser"}


def should_start_poller() -> bool:
    return not any(cmd in sys.argv for cmd in _SKIP_COMMANDS)


def start_plc_poller() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    if not should_start_poller():
        return
    _thread = threading.Thread(target=_run, name="kuali-plc-poller", daemon=True)
    _thread.start()


def _run() -> None:
    gateway = build_plc_gateway()
    interval = int(getattr(settings, "PLC_POLL_INTERVAL_MS", 500))
    try:
        asyncio.run(plc_poll_loop(gateway, interval_ms=interval))
    except Exception:
        logger.exception("PLC poller stopped")
    finally:
        gateway.close()
