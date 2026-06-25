from __future__ import annotations

import json
import logging
import sys
import threading
import time

from django.conf import settings

from integrations.mqtt import broker_monitor
from services import robot_queue_service

logger = logging.getLogger(__name__)

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None  # type: ignore

_listener_thread: threading.Thread | None = None
_client = None
_client_lock = threading.RLock()

_SKIP_COMMANDS = {"check", "migrate", "makemigrations", "showmigrations", "test", "shell", "collectstatic", "createsuperuser"}


def should_start_listener() -> bool:
    return bool(getattr(settings, "MQTT_ENABLED", False)) and not any(cmd in sys.argv for cmd in _SKIP_COMMANDS)


def _full_topic(relative_topic: str) -> str:
    root = getattr(settings, "MQTT_TOPIC_ROOT", "kuali").strip("/")
    relative = relative_topic.strip("/")
    return f"{root}/{relative}" if root else relative


def start_order_listener() -> None:
    global _listener_thread
    topic = _full_topic(getattr(settings, "MQTT_ORDER_COMMAND_TOPIC", "order/cmd/#"))
    broker_monitor.configure(topic=topic)
    if _listener_thread and _listener_thread.is_alive():
        return
    if not should_start_listener():
        return
    if mqtt is None:
        broker_monitor.set_failed("paho-mqtt tidak terinstall")
        logger.warning("MQTT listener tidak start: paho-mqtt tidak terinstall")
        return

    _listener_thread = threading.Thread(target=_run_forever, name="kuali-mqtt-order-listener", daemon=True)
    _listener_thread.start()


def request_reconnect() -> dict:
    broker_monitor.request_reconnect()
    with _client_lock:
        client = _client
    if client is not None:
        try:
            client.disconnect()
        except Exception as exc:
            broker_monitor.set_failed(f"disconnect before reconnect failed: {exc}")
    start_order_listener()
    return broker_monitor.snapshot()


def _run_forever() -> None:
    while should_start_listener():
        try:
            _run_once()
        except Exception as exc:
            broker_monitor.set_failed(str(exc))
            logger.exception("MQTT order listener crash, retry 5s")
            time.sleep(5)
        else:
            time.sleep(1)


def _reason_is_success(reason) -> bool:
    try:
        return int(reason) == 0
    except (TypeError, ValueError):
        return str(reason).lower() in {"0", "success", "normal disconnection"}


def _reason_label(reason) -> str:
    return str(reason) if reason is not None else "unknown"


def _run_once() -> None:
    global _client
    topic = _full_topic(getattr(settings, "MQTT_ORDER_COMMAND_TOPIC", "order/cmd/#"))
    broker_monitor.set_connecting(topic=topic)

    client = mqtt.Client(client_id=f"{settings.MQTT_CLIENT_ID}-orders")
    with _client_lock:
        _client = client

    if settings.MQTT_USERNAME:
        client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

    def on_connect(client, userdata, *args):
        reason = args[1] if len(args) >= 2 else (args[0] if args else 0)
        if _reason_is_success(reason):
            client.subscribe(topic, qos=1)
            broker_monitor.set_connected(topic=topic)
            logger.info("MQTT order listener subscribed %s", topic)
        else:
            broker_monitor.set_failed(f"connect rc={_reason_label(reason)}")
            logger.error("MQTT order listener connect failed rc=%s", reason)

    def on_disconnect(client, userdata, *args):
        reason = args[1] if len(args) >= 2 else (args[0] if args else "disconnected")
        if _reason_is_success(reason):
            broker_monitor.set_disconnected("disconnect")
        else:
            broker_monitor.set_failed(f"disconnect rc={_reason_label(reason)}")

    def on_message(client, userdata, message):
        broker_monitor.record_message(message.topic, message.payload)
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            robot_queue_service.receive_order(payload)
        except Exception:
            logger.exception("Gagal proses MQTT order dari %s", message.topic)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:
        client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, keepalive=60)
        client.loop_forever()
    finally:
        with _client_lock:
            if _client is client:
                _client = None
        try:
            client.disconnect()
        except Exception:
            pass
