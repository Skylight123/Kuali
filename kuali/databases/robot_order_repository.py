from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from hmi.models import RobotOrder, RobotOrderTask


ORDER_STATUS_RECEIVED = RobotOrder.STATUS_RECEIVED
ORDER_STATUS_PROCESSING = RobotOrder.STATUS_PROCESSING
ORDER_STATUS_DONE = RobotOrder.STATUS_DONE
ORDER_STATUS_ERROR = RobotOrder.STATUS_ERROR

TASK_STATUS_RECEIVED = RobotOrderTask.STATUS_RECEIVED
TASK_STATUS_PROCESSING = RobotOrderTask.STATUS_PROCESSING
TASK_STATUS_DONE = RobotOrderTask.STATUS_DONE
TASK_STATUS_ERROR = RobotOrderTask.STATUS_ERROR

OPEN_TASK_STATUSES = (RobotOrderTask.STATUS_RECEIVED, RobotOrderTask.STATUS_PROCESSING)


def atomic():
    return transaction.atomic()


def get_or_create_order(order_id: str, raw_payload: dict):
    return RobotOrder.objects.get_or_create(
        order_id=order_id,
        defaults={
            "raw_payload": raw_payload,
            "aggregate_status": RobotOrder.STATUS_RECEIVED,
        },
    )


def get_order_by_order_id(order_id: str) -> RobotOrder:
    return RobotOrder.objects.get(order_id=order_id)


def order_has_tasks(order: RobotOrder) -> bool:
    return order.tasks.exists()


def mark_order_done(order: RobotOrder, raw_payload: dict | None = None, now=None) -> RobotOrder:
    now = now or timezone.now()
    if raw_payload is not None:
        order.raw_payload = raw_payload
    order.aggregate_status = RobotOrder.STATUS_DONE
    order.error_message = ""
    order.completed_at = now
    order.save(update_fields=["raw_payload", "aggregate_status", "completed_at", "updated_at", "error_message"])
    return order


def mark_order_error_with_tasks(order: RobotOrder, raw_payload: dict, cooking_units, error_message: str, now=None) -> RobotOrder:
    now = now or timezone.now()
    order.raw_payload = raw_payload
    order.aggregate_status = RobotOrder.STATUS_ERROR
    order.error_message = error_message
    order.completed_at = now
    order.save(update_fields=["raw_payload", "aggregate_status", "error_message", "completed_at", "updated_at"])

    for idx, item in enumerate(cooking_units, start=1):
        RobotOrderTask.objects.create(
            order=order,
            menu=item.menu,
            option=item.option,
            qty_index=idx,
            status=RobotOrderTask.STATUS_ERROR,
            error_message=error_message,
            completed_at=now,
        )
    return order


def create_received_tasks(order: RobotOrder, raw_payload: dict, cooking_units) -> RobotOrder:
    order.raw_payload = raw_payload
    order.aggregate_status = RobotOrder.STATUS_RECEIVED
    order.error_message = ""
    order.completed_at = None
    order.save(update_fields=["raw_payload", "aggregate_status", "updated_at", "error_message", "completed_at"])

    for idx, item in enumerate(cooking_units, start=1):
        RobotOrderTask.objects.create(
            order=order,
            menu=item.menu,
            option=item.option,
            qty_index=idx,
            status=RobotOrderTask.STATUS_RECEIVED,
        )
    return order


def processing_tasks() -> list[RobotOrderTask]:
    return list(RobotOrderTask.objects.select_related("order").filter(status=RobotOrderTask.STATUS_PROCESSING))


def open_tasks() -> list[RobotOrderTask]:
    return list(RobotOrderTask.objects.select_related("order").filter(status__in=OPEN_TASK_STATUSES))


def waiting_tasks(limit: int) -> list[RobotOrderTask]:
    return list(
        RobotOrderTask.objects.select_related("order")
        .filter(status=RobotOrderTask.STATUS_RECEIVED)
        .order_by("created_at", "id")[:limit]
    )


def orders_by_ids(order_ids):
    return RobotOrder.objects.filter(id__in=order_ids)


def mark_task_processing(task: RobotOrderTask, stirrer: int, now=None) -> RobotOrderTask:
    now = now or timezone.now()
    task.status = RobotOrderTask.STATUS_PROCESSING
    task.assigned_stirrer = stirrer
    task.started_at = now
    task.error_message = ""
    task.save(update_fields=["status", "assigned_stirrer", "started_at", "error_message", "updated_at"])
    return task


def mark_order_processing(order: RobotOrder) -> RobotOrder:
    order.aggregate_status = RobotOrder.STATUS_PROCESSING
    order.error_message = ""
    order.save(update_fields=["aggregate_status", "error_message", "updated_at"])
    return order


def mark_task_error_and_order_error(task: RobotOrderTask, error_message: str, now=None) -> RobotOrderTask:
    now = now or timezone.now()
    task.status = RobotOrderTask.STATUS_ERROR
    task.error_message = error_message
    task.completed_at = now
    task.save(update_fields=["status", "error_message", "completed_at", "updated_at"])

    order = task.order
    order.aggregate_status = RobotOrder.STATUS_ERROR
    order.error_message = error_message
    order.completed_at = now
    order.save(update_fields=["aggregate_status", "error_message", "completed_at", "updated_at"])
    return task


def mark_open_tasks_error(error_message: str, now=None) -> list[tuple[str, str, str]]:
    now = now or timezone.now()
    events = []
    seen_orders: set[int] = set()
    for task in open_tasks():
        task.status = RobotOrderTask.STATUS_ERROR
        task.error_message = error_message
        task.completed_at = now
        task.save(update_fields=["status", "error_message", "completed_at", "updated_at"])

        order = task.order
        if order.id in seen_orders:
            continue
        order.aggregate_status = RobotOrder.STATUS_ERROR
        order.error_message = error_message
        order.completed_at = now
        order.save(update_fields=["aggregate_status", "error_message", "completed_at", "updated_at"])
        events.append((order.order_id, RobotOrder.STATUS_ERROR, error_message))
        seen_orders.add(order.id)
    return events


def mark_task_seen_on(task: RobotOrderTask) -> RobotOrderTask:
    task.plc_seen_on = True
    task.save(update_fields=["plc_seen_on", "updated_at"])
    return task


def mark_task_done(task: RobotOrderTask, now=None) -> RobotOrderTask:
    now = now or timezone.now()
    task.status = RobotOrderTask.STATUS_DONE
    task.completed_at = now
    task.save(update_fields=["status", "completed_at", "updated_at"])
    return task


def refresh_order_status(order: RobotOrder, now=None):
    now = now or timezone.now()
    statuses = list(order.tasks.values_list("status", flat=True))
    if not statuses:
        return None

    if any(status == RobotOrderTask.STATUS_ERROR for status in statuses):
        order.aggregate_status = RobotOrder.STATUS_ERROR
        order.completed_at = now
        order.save(update_fields=["aggregate_status", "completed_at", "updated_at"])
        return order.order_id, RobotOrder.STATUS_ERROR, order.error_message

    if all(status == RobotOrderTask.STATUS_DONE for status in statuses):
        order.aggregate_status = RobotOrder.STATUS_DONE
        order.completed_at = now
        order.save(update_fields=["aggregate_status", "completed_at", "updated_at"])
        return order.order_id, RobotOrder.STATUS_DONE, ""

    if any(status == RobotOrderTask.STATUS_PROCESSING for status in statuses):
        order.aggregate_status = RobotOrder.STATUS_PROCESSING
        order.save(update_fields=["aggregate_status", "updated_at"])
        return order.order_id, RobotOrder.STATUS_PROCESSING, ""

    order.aggregate_status = RobotOrder.STATUS_RECEIVED
    order.save(update_fields=["aggregate_status", "updated_at"])
    return order.order_id, RobotOrder.STATUS_RECEIVED, ""


def queue_snapshot(limit: int = 60) -> dict:
    tasks = (
        RobotOrderTask.objects.select_related("order")
        .exclude(status=RobotOrderTask.STATUS_DONE)
        .order_by("created_at", "id")[:limit]
    )
    rows = [
        {
            "id": task.id,
            "order_name": task.order.order_id,
            "menu": task.menu,
            "option": task.option,
            "status": task.display_status,
            "raw_status": task.status,
            "assigned_stirrer": task.assigned_stirrer,
            "error_message": task.error_message,
        }
        for task in tasks
    ]
    return {
        "rows": rows,
        "summary": {
            "received": RobotOrderTask.objects.filter(status=RobotOrderTask.STATUS_RECEIVED).count(),
            "processing": RobotOrderTask.objects.filter(status=RobotOrderTask.STATUS_PROCESSING).count(),
            "error": RobotOrderTask.objects.filter(status=RobotOrderTask.STATUS_ERROR).count(),
        },
    }
