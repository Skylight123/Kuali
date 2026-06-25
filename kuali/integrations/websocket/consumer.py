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

    # Pesan dari browser → bisa dipakai untuk write command ke PLC nanti
    async def receive_json(self, content: dict, **kwargs) -> None:
        # TODO: route write commands (e.g. set setpoint, toggle cooker)
        pass

    # Handler untuk pesan dari poller via Channel Layer
    async def plc_update(self, event: dict) -> None:
        await self.send_json(event["data"])
