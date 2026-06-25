from __future__ import annotations

from dataclasses import dataclass


DRINK_PREFIXES = ("es_", "teh", "kopi", "jus", "air_")


@dataclass(frozen=True)
class IncomingOrderItem:
    menu: str
    option: int
    qty: int

    @property
    def needs_cooking_robot(self) -> bool:
        token = self.menu.lower().strip()
        return bool(token) and not token.startswith(DRINK_PREFIXES)


@dataclass(frozen=True)
class IncomingOrder:
    order_id: str
    items: tuple[IncomingOrderItem, ...]

    @classmethod
    def from_payload(cls, payload: dict) -> "IncomingOrder":
        order_id = str(payload.get("order_id") or "").strip()
        if not order_id:
            raise ValueError("order_id wajib diisi")

        items = []
        for raw in payload.get("items") or []:
            menu = str(raw.get("menu") or "").strip().lower()
            if not menu:
                continue
            option = int(raw.get("option") or 0)
            qty = max(0, int(raw.get("qty") or 0))
            if qty:
                items.append(IncomingOrderItem(menu=menu, option=option, qty=qty))

        if not items:
            raise ValueError("items order kosong")
        return cls(order_id=order_id, items=tuple(items))

    def expand_cooking_units(self) -> list[IncomingOrderItem]:
        units: list[IncomingOrderItem] = []
        for item in self.items:
            if not item.needs_cooking_robot:
                continue
            for _ in range(item.qty):
                units.append(IncomingOrderItem(menu=item.menu, option=item.option, qty=1))
        return units
