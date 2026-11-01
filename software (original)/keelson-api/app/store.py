"""Read only data store backed by the JSON files in app/data."""
import json
from pathlib import Path

from .dates import shift_date, shift_memo

DATA_DIR = Path(__file__).parent / "data"

PO_DATE_FIELDS = ("order_date", "requested_delivery_date", "confirmed_delivery_date", "last_modified")


def _load(name: str) -> list[dict]:
    return json.loads((DATA_DIR / f"{name}.json").read_text(encoding="utf-8"))


_SUPPLIERS = _load("suppliers")
_EMPLOYEES = _load("employees")
_PROJECTS = _load("projects")
_PURCHASE_ORDERS = _load("purchase_orders")


def _shift_order(po: dict) -> dict:
    result = dict(po)
    for field in PO_DATE_FIELDS:
        result[field] = shift_date(po[field])
    result["memo"] = shift_memo(po["memo"])
    return result


def purchase_orders() -> list[dict]:
    return [_shift_order(po) for po in _PURCHASE_ORDERS]


def suppliers() -> list[dict]:
    return [dict(s) for s in _SUPPLIERS]


def employees() -> list[dict]:
    return [dict(e) for e in _EMPLOYEES]


def projects() -> list[dict]:
    return [{**p, "customer_delivery_date": shift_date(p["customer_delivery_date"])} for p in _PROJECTS]
