from __future__ import annotations

import json
import logging
import sys
import threading
import time

from django.conf import settings

from services import robot_queue_service

logger = logging.getLogger(__name__)

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None  # type: ignore

_listener_thread: threading.Thread | None = None

_SKIP_COMMANDS = {"check", "migrate", "makemigrations", "showmigrations", "test", "shell", "collectstatic", "createsuperuser"}


def should_start_listener() -> bool:
    return bool(getattr(settings, "MQTT_ENABLED", False)) and not any(cmd in sys.argv for cmd in _SKIP_COMMANDS)


def _full_topic(relative_topic: str) -> str:
    root = getattr(settings, "MQTT_TOPIC_ROOT", "kuali").strip("/")
    relative = relative_topic.strip("/")
    return f"{root}/{relative}" if root else relative


def start_order_listener() -> None:
    global _listener_thread
    if _listener_thread and _listener_thread.is_alive():
        return
    if not should_start_listener():
        return
    if mqtt is None:
        logger.warning("MQTT listener tidak start: paho-mqtt tidak terinstall")
        return

    _listener_thread = threading.Thread(target=_run_forever, name="kuali-mqtt-order-listener", daemon=True)
    _listener_thread.start()


def _run_forever() -> None:
    while True:
        try:
            _run_once()
        except Exception:
            logger.exception("MQTT order listener crash, retry 5s")
            time.sleep(5)


def _run_once() -> None:
    topic = _full_topic(getattr(settings, "MQTT_ORDER_COMMAND_TOPIC", "order/cmd/#"))
    client = mqtt.Client(client_id=f"{settings.MQTT_CLIENT_ID}-orders")
    if settings.MQTT_USERNAME:
        client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(topic, qos=1)
            logger.info("MQTT order listener subscribed %s", topic)
        else:
            logger.error("MQTT order listener connect failed rc=%s", rc)

    def on_message(client, userdata, message):
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            robot_queue_service.receive_order(payload)
        except Exception:
            logger.exception("Gagal proses MQTT order dari %s", message.topic)

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, keepalive=60)
    client.loop_forever()
