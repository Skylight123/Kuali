"""WebSocket consumer — menerima koneksi browser dan forward state PLC."""
from __future__ import annotations

import json

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from devices.plc.poller import CHANNEL_GROUP


class HmiConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self) -> None:
        # Hanya user yang sudah login yang boleh connect
        if not self.scope["user"].is_authenticated:
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(CHANNEL_GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, code: int) -> None:
        await self.channel_layer.group_discard(CHANNEL_GROUP, self.channel_name)

    # Pesan dari browser -> write command ke PLC.
    async def receive_json(self, content: dict, **kwargs) -> None:
        write = content.get("write") or {}
        try:
            address = int(write.get("address"))
            value = int(write.get("value"))
        except (TypeError, ValueError):
            await self.send_json({"error": "Invalid write payload"})
            return

        from devices.plc import connection as plc_connection
        plc_connection.with_gateway(lambda gateway: gateway.write_command(address, value))
        await self.send_json({"write_ack": {"address": address, "value": value}})

    # Handler untuk pesan dari poller via Channel Layer
    async def plc_update(self, event: dict) -> None:
        await self.send_json(event["data"])
