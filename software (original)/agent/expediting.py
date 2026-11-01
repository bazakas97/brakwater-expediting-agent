"""Rules used by the open orders export to decide which orders need attention."""
from datetime import date, timedelta

DUE_SOON_DAYS = 14

NO_CONFIRMATION = "NO_CONFIRMATION"
DUE_SOON = "DUE_WITHIN_14_DAYS"
OVERDUE = "OVERDUE"


def effective_delivery_date(po: dict) -> date:
    """The confirmed delivery date if the supplier confirmed one, otherwise the requested date."""
    value = po.get("confirmed_delivery_date") or po["requested_delivery_date"]
    return date.fromisoformat(value)


def is_overdue(po: dict, today: date) -> bool:
    return effective_delivery_date(po) < today


def is_due_soon(po: dict, today: date) -> bool:
    delivery = effective_delivery_date(po)
    return today <= delivery <= today + timedelta(days=DUE_SOON_DAYS)


def missing_confirmation(po: dict) -> bool:
    return not po["order_confirmation_received"]


def flag_order(po: dict, today: date) -> list[str]:
    flags = []
    if missing_confirmation(po):
        flags.append(NO_CONFIRMATION)
    if is_due_soon(po, today):
        flags.append(DUE_SOON)
    if is_overdue(po, today):
        flags.append(OVERDUE)
    return flags
