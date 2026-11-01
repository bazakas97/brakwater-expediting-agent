from datetime import date, timedelta

from triage import NO_ACTION_REASON, split_orders

TODAY = date(2026, 3, 2)


def order(po_number: str, requested_days: int, memo: str = "", confirmed: bool = True) -> dict:
    return {
        "po_number": po_number,
        "requested_delivery_date": (TODAY + timedelta(days=requested_days)).isoformat(),
        "confirmed_delivery_date": None,
        "order_confirmation_received": confirmed,
        "memo": memo,
    }


def po_numbers(orders: list[dict]) -> list[str]:
    return [o["po_number"] for o in orders]


def test_flagged_order_without_memo_goes_to_llm():
    for_llm, no_action = split_orders([order("PO1", requested_days=-1)], TODAY)
    assert po_numbers(for_llm) == ["PO1"]
    assert no_action == []


def test_unflagged_order_with_memo_goes_to_llm():
    # On time and confirmed, but the delay is only written in the memo.
    late_in_memo = order("PO2", requested_days=60, memo="19/10 LV: levering uitgesteld naar wk 47.")
    for_llm, no_action = split_orders([late_in_memo], TODAY)
    assert po_numbers(for_llm) == ["PO2"]
    assert no_action == []


def test_unflagged_order_without_memo_gets_action_none():
    for_llm, no_action = split_orders([order("PO3", requested_days=60)], TODAY)
    assert for_llm == []
    assert po_numbers(no_action) == ["PO3"]
    assert no_action[0]["action"] == "none"
    assert no_action[0]["reason"] == NO_ACTION_REASON


def test_memo_with_only_spaces_counts_as_empty():
    for_llm, no_action = split_orders([order("PO4", requested_days=60, memo="  \n ")], TODAY)
    assert for_llm == []
    assert po_numbers(no_action) == ["PO4"]


def test_every_order_ends_up_in_exactly_one_list():
    orders = [
        order("PO1", requested_days=-1),
        order("PO2", requested_days=60, memo="note"),
        order("PO3", requested_days=60),
        order("PO4", requested_days=5, memo="note"),
        order("PO5", requested_days=60, confirmed=False),
        order("PO6", requested_days=60),
    ]
    for_llm, no_action = split_orders(orders, TODAY)
    all_out = po_numbers(for_llm) + po_numbers(no_action)
    assert sorted(all_out) == sorted(po_numbers(orders))
    assert len(all_out) == len(set(all_out))
