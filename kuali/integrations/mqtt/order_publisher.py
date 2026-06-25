from __future__ import annotations

import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None  # type: ignore


class MqttOrderStatusPublisher:
    def __init__(self):
        if mqtt is None:
            raise ImportError("paho-mqtt tidak terinstall. Jalankan: pip install paho-mqtt")
        self._root = getattr(settings, "MQTT_TOPIC_ROOT", "kuali").strip("/")
        self._device = getattr(settings, "MQTT_ORDER_STATUS_DEVICE", "kuali").strip("/")

    def publish_status(self, order_id: str, status: str, message: str = "") -> None:
        payload = {"order_id": order_id, "status": status}
        if message:
            payload["message"] = message
        topic = f"order/status/{self._device}"
        full_topic = f"{self._root}/{topic}" if self._root else topic

        client = mqtt.Client(client_id=f"{settings.MQTT_CLIENT_ID}-pub")
        if settings.MQTT_USERNAME:
            client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
        client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, keepalive=30)
        client.publish(full_topic, json.dumps(payload), qos=1, retain=False)
        client.disconnect()
        logger.info("MQTT publish %s %s", full_topic, payload)
