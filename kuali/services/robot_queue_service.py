from __future__ import annotations

import logging
from typing import Protocol

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.utils import timezone

from databases import robot_order_repository as orders
from devices.plc import registers as R
from devices.plc import connection as plc_connection
from devices.plc.poller import CHANNEL_GROUP
from domain.models.robot_order import IncomingOrder
from hmi.models import RobotOrder

logger = logging.getLogger(__name__)


class OrderStatusPublisher(Protocol):
    def publish_status(self, order_id: str, status: str, message: str = "") -> None:
        ...


class NoopOrderStatusPublisher:
    def publish_status(self, order_id: str, status: str, message: str = "") -> None:
        logger.info("Robot order status %s -> %s %s", order_id, status, message)


def _default_publisher() -> OrderStatusPublisher:
    if not getattr(settings, "MQTT_ENABLED", False):
        return NoopOrderStatusPublisher()
    from integrations.mqtt.order_publisher import MqttOrderStatusPublisher
    return MqttOrderStatusPublisher()


def _registers(snapshot: dict | None) -> dict[int, int]:
    if not snapshot:
        return {}
    return {int(k): int(v) for k, v in (snapshot.get("registers") or {}).items()}


def _plc_snapshot(plc_gateway=None) -> dict:
    if plc_gateway is not None:
        return plc_gateway.read_all()
    return plc_connection.with_gateway(lambda gateway: gateway.read_all())


def _plc_is_on(registers: dict[int, int]) -> bool:
    return registers.get(R.CMD_11) == 1


def _available_stirrers(registers: dict[int, int]) -> list[int]:
    available = []
    if registers.get(R.STIRRER_1) == 0:
        available.append(1)
    if registers.get(R.STIRRER_2) == 0:
        available.append(2)
    return available


def _active_register_for_stirrer(stirrer_id: int) -> int:
    return R.STIRRER_1 if stirrer_id == 1 else R.STIRRER_2


def _command_address_for_stirrer(stirrer_id: int) -> int:
    return R.CMD_9 if stirrer_id == 1 else R.CMD_10


def _send_stirrer_command(stirrer_id: int, value: int, plc_gateway=None) -> None:
    address = _command_address_for_stirrer(stirrer_id)
    if plc_gateway is not None:
        plc_gateway.write_command(address, value)
        return
    plc_connection.with_gateway(lambda gateway: gateway.write_command(address, value))


def _plc_off_message() -> str:
    return "PLC tidak ON pada cmd_11"


def receive_order(payload: dict, plc_gateway=None, publisher: OrderStatusPublisher | None = None) -> RobotOrder:
    incoming = IncomingOrder.from_payload(payload)
    publisher = publisher or _default_publisher()
    snapshot = _plc_snapshot(plc_gateway)
    registers = _registers(snapshot)
    cooking_units = incoming.expand_cooking_units()

    with orders.atomic():
        order, created = orders.get_or_create_order(incoming.order_id, payload)
        if not created and orders.order_has_tasks(order):
            return order

        if not cooking_units:
            order = orders.mark_order_done(order, raw_payload=payload)
            publisher.publish_status(order.order_id, orders.ORDER_STATUS_DONE)
            broadcast_queue_snapshot()
            return order

        if not _plc_is_on(registers):
            message = _plc_off_message()
            order = orders.mark_order_error_with_tasks(order, payload, cooking_units, message)
            publisher.publish_status(order.order_id, orders.ORDER_STATUS_ERROR, message)
            broadcast_queue_snapshot()
            return order

        orders.create_received_tasks(order, payload, cooking_units)

    publisher.publish_status(incoming.order_id, orders.ORDER_STATUS_RECEIVED)
    dispatch_waiting_tasks(snapshot=snapshot, publisher=publisher, plc_gateway=plc_gateway)
    broadcast_queue_snapshot()
    return orders.get_order_by_order_id(incoming.order_id)


def dispatch_waiting_tasks(
    snapshot: dict | None = None,
    publisher: OrderStatusPublisher | None = None,
    plc_gateway=None,
) -> None:
    publisher = publisher or _default_publisher()
    if snapshot is None:
        snapshot = _plc_snapshot()
    registers = _registers(snapshot)
    if not _plc_is_on(registers):
        return

    ready = _available_stirrers(registers)
    if not ready:
        return

    touched_orders: set[int] = set()
    assigned_tasks: list[tuple[int, int]] = []
    with orders.atomic():
        occupied = {task.assigned_stirrer for task in orders.processing_tasks() if task.assigned_stirrer}
        free = [stirrer for stirrer in ready if stirrer not in occupied]
        if not free:
            return

        now = timezone.now()
        for task, stirrer in zip(orders.waiting_tasks(len(free)), free):
            task = orders.mark_task_processing(task, stirrer, now=now)
            assigned_tasks.append((task.id, stirrer))
            if task.order.aggregate_status != orders.ORDER_STATUS_PROCESSING:
                orders.mark_order_processing(task.order)
            touched_orders.add(task.order.id)

    failed_order_ids: set[int] = set()
    write_errors: list[tuple[str, str, str]] = []
    for task_id, stirrer in assigned_tasks:
        try:
            _send_stirrer_command(stirrer, 1, plc_gateway=plc_gateway)
        except Exception as exc:
            message = f"Gagal kirim command PLC stirrer {stirrer}: {exc}"
            logger.exception(message)
            with orders.atomic():
                task = orders.task_by_id(task_id)
                orders.mark_task_error_and_order_error(task, message)
                failed_order_ids.add(task.order.id)
                write_errors.append((task.order.order_id, orders.ORDER_STATUS_ERROR, message))

    for order in orders.orders_by_ids(touched_orders - failed_order_ids):
        publisher.publish_status(order.order_id, orders.ORDER_STATUS_PROCESSING)
    for order_id, status, message in write_errors:
        publisher.publish_status(order_id, status, message)
    if touched_orders:
        broadcast_queue_snapshot()


def reconcile_plc_state(snapshot: dict, publisher: OrderStatusPublisher | None = None, plc_gateway=None) -> dict:
    publisher = publisher or _default_publisher()
    registers = _registers(snapshot)
    now = timezone.now()
    publish: list[tuple[str, str, str]] = []

    if not _plc_is_on(registers):
        with orders.atomic():
            publish.extend(orders.mark_open_tasks_error(_plc_off_message(), now=now))
    else:
        with orders.atomic():
            for task in orders.processing_tasks():
                if not task.assigned_stirrer:
                    continue
                active_value = registers.get(_active_register_for_stirrer(task.assigned_stirrer))

                if active_value == 1 and not task.plc_seen_on:
                    orders.mark_task_seen_on(task)
                    continue

                if task.plc_seen_on and active_value == 0:
                    orders.mark_task_done(task, now=now)
                    event = orders.refresh_order_status(task.order, now=now)
                    if event:
                        publish.append(event)

        dispatch_waiting_tasks(snapshot=snapshot, publisher=publisher, plc_gateway=plc_gateway)

    for order_id, status, message in publish:
        publisher.publish_status(order_id, status, message)
    snapshot["robot_queue"] = queue_snapshot()
    return snapshot


def queue_snapshot(limit: int = 60) -> dict:
    return orders.queue_snapshot(limit=limit)


def broadcast_queue_snapshot(data: dict | None = None) -> None:
    layer = get_channel_layer()
    if not layer:
        return
    async_to_sync(layer.group_send)(
        CHANNEL_GROUP,
        {"type": "plc.update", "data": {"robot_queue": data or queue_snapshot()}},
    )
