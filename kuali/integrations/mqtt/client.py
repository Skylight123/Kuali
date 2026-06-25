"""MQTT broker client — publish plant state ke broker (Mosquitto, HiveMQ, dll).

Requires: pip install paho-mqtt
Config diambil dari settings.py (bersumber dari .env):
    MQTT_ENABLED, MQTT_BROKER, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD,
    MQTT_CLIENT_ID, MQTT_TOPIC_ROOT
"""
from __future__ import annotations

import json
import logging

from django.conf import settings

from domain.ports import IBroker

logger = logging.getLogger(__name__)

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None  # type: ignore


class MqttBroker(IBroker):

    def __init__(self):
        if mqtt is None:
            raise ImportError("paho-mqtt tidak terinstall. Jalankan: pip install paho-mqtt")

        self._root = getattr(settings, "MQTT_TOPIC_ROOT", "kuali")
        self._client = mqtt.Client(client_id=settings.MQTT_CLIENT_ID)

        if settings.MQTT_USERNAME:
            self._client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

        self._client.on_disconnect = self._on_disconnect
        self._client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, keepalive=60)
        self._client.loop_start()
        logger.info("MQTT connected to %s:%d", settings.MQTT_BROKER, settings.MQTT_PORT)

    def _on_disconnect(self, client, userdata, rc):
        logger.warning("MQTT disconnected (rc=%d), auto-reconnect...", rc)

    def publish(self, topic: str, payload: dict) -> None:
        full_topic = f"{self._root}/{topic}" if self._root else topic
        self._client.publish(full_topic, json.dumps(payload), qos=0, retain=False)

    def close(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
