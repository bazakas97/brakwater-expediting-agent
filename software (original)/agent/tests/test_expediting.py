from datetime import date, timedelta

from expediting import DUE_SOON, NO_CONFIRMATION, OVERDUE, flag_order

TODAY = date(2026, 3, 2)


def order(requested_days: int, confirmed_days: int | None = None, confirmed: bool = True) -> dict:
    return {
        "requested_delivery_date": (TODAY + timedelta(days=requested_days)).isoformat(),
        "confirmed_delivery_date": (TODAY + timedelta(days=confirmed_days)).isoformat()
        if confirmed_days is not None else None,
        "order_confirmation_received": confirmed,
    }


def test_overdue():
    assert flag_order(order(-1), TODAY) == [OVERDUE]


def test_due_in_five_days():
    assert flag_order(order(5), TODAY) == [DUE_SOON]


def test_not_due_yet():
    assert flag_order(order(30), TODAY) == []


def test_confirmed_date_wins_over_requested_date():
    assert flag_order(order(-3, confirmed_days=40), TODAY) == []


def test_missing_confirmation():
    assert flag_order(order(40, confirmed=False), TODAY) == [NO_CONFIRMATION]
