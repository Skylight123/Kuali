"""Background async loop: baca PLC → broadcast ke Channel Layer."""
from __future__ import annotations

import asyncio
import logging

from channels.layers import get_channel_layer

from domain.ports import IPlcGateway

logger = logging.getLogger(__name__)

CHANNEL_GROUP = "hmi_dashboard"


async def plc_poll_loop(gateway: IPlcGateway, interval_ms: int = 500) -> None:
    """
    Jalankan sebagai background task di ASGI lifespan atau management command.
    Broadcast state PLC ke semua WebSocket client yang join group 'hmi_dashboard'.
    """
    layer = get_channel_layer()
    logger.info("PLC poller started (interval=%dms)", interval_ms)

    while True:
        try:
            state = gateway.read_all()
            from integrations.mqtt import broker_monitor
            from services.robot_queue_service import reconcile_plc_state
            state = reconcile_plc_state(state)
            state["broker_status"] = broker_monitor.snapshot()
            await layer.group_send(
                CHANNEL_GROUP,
                {"type": "plc.update", "data": state},
            )
        except Exception as exc:
            logger.error("Poller error: %s", exc)

        await asyncio.sleep(interval_ms / 1000)
