from datetime import date, datetime, timedelta, timezone

import pytest

from decision import ACTIONS as DECISION_ACTIONS
from view import (ACTIONS, LABELS, count_actions, describe_age, describe_proposal, describe_recipient, due_soon_end, hover_text, is_stale, min_gap_days, sort_orders,
                  stack_levels, summary_line, x_range)

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


def order(po: str, action: str = "none", delivery_date: str = "2026-11-10", **extra) -> dict:
    return {"po_number": po, "supplier_name": "Acme", "action": action, "delivery_date": delivery_date,
            "flags": [], "memo": "", "reason": "r", **extra}


def test_sort_puts_escalate_first_then_chase_then_none():
    orders = [order("A", "none"), order("B", "chase_supplier"), order("C", "escalate")]
    assert [o["po_number"] for o in sort_orders(orders)] == ["C", "B", "A"]


def test_sort_uses_delivery_date_inside_a_group():
    orders = [order("A", "escalate", "2026-12-01"), order("B", "escalate", "2026-11-05")]
    assert [o["po_number"] for o in sort_orders(orders)] == ["B", "A"]


def test_sort_with_unknown_action_fails_loudly():
    with pytest.raises(ValueError):
        sort_orders([order("A", "delete_everything")])


def test_count_and_summary_line():
    orders = [order("A", "escalate"), order("B", "chase_supplier"), order("C", "chase_supplier"), order("D"),
              order("E", "book_in"), order("F", "wait"), order("G", "wait")]
    assert count_actions(orders) == {"escalate": 1, "chase_supplier": 2, "book_in": 1, "wait": 2, "none": 1}
    assert summary_line(orders) == "7 open orders: 1 escalate, 2 chase, 1 book in, 2 wait, 1 none"


def test_sort_orders_all_five_actions_most_urgent_first():
    actions = ["none", "wait", "book_in", "chase_supplier", "escalate"]
    orders = [order(a, a) for a in actions]
    assert [o["action"] for o in sort_orders(orders)] == ["escalate", "chase_supplier", "book_in", "wait", "none"]


def test_view_and_decision_know_the_same_actions():
    assert set(ACTIONS) == set(DECISION_ACTIONS)
    assert set(LABELS) == set(ACTIONS)


def levels(orders: list[dict], gap: int) -> dict[str, int]:
    return {o["po_number"]: o["level"] for o in stack_levels(orders, gap)}


def test_orders_on_the_same_date_get_different_levels_most_urgent_lowest():
    orders = [order("A", "none"), order("B", "escalate"), order("C", "chase_supplier")]
    assert levels(orders, gap=3) == {"B": 1, "C": 2, "A": 3}


def test_dots_closer_than_the_gap_get_different_levels():
    orders = [order("A", delivery_date="2026-11-10"), order("B", delivery_date="2026-11-11"),
              order("C", delivery_date="2026-11-12")]
    result = levels(orders, gap=3)
    assert len(set(result.values())) == 3  # 1 and 2 days apart: all three on their own level


def test_dots_exactly_the_gap_apart_may_share_a_level():
    orders = [order("A", delivery_date="2026-11-10"), order("B", delivery_date="2026-11-13")]
    assert levels(orders, gap=3) == {"A": 1, "B": 1}


def test_far_apart_dots_all_stay_on_level_one():
    orders = [order("A", delivery_date="2026-11-01"), order("B", delivery_date="2026-12-01")]
    assert levels(orders, gap=3) == {"A": 1, "B": 1}


def test_most_urgent_stays_at_the_bottom_even_with_a_later_date():
    orders = [order("CHASE", "chase_supplier", "2026-11-04"), order("ESC", "escalate", "2026-11-05")]
    assert levels(orders, gap=3) == {"ESC": 1, "CHASE": 2}


def test_gap_of_one_day_only_separates_the_same_date():
    orders = [order("A", delivery_date="2026-11-10"), order("B", delivery_date="2026-11-11"),
              order("C", delivery_date="2026-11-11")]
    assert levels(orders, gap=1) == {"A": 1, "B": 1, "C": 2}


def test_no_two_dots_on_one_level_are_closer_than_the_gap():
    actions = ["none", "chase_supplier", "escalate"]
    orders = [order(f"P{i}", actions[i % 3], f"2026-11-{1 + (i * 7) % 25:02d}") for i in range(40)]
    for gap in (1, 2, 3, 5):
        stacked = stack_levels(orders, gap)
        for a in stacked:
            for b in stacked:
                if a is not b and a["level"] == b["level"]:
                    days = abs((date.fromisoformat(a["delivery_date"]) - date.fromisoformat(b["delivery_date"])).days)
                    assert days >= gap, (gap, a["po_number"], b["po_number"])


def test_stacking_loses_no_order_and_does_not_change_the_input():
    orders = [order("A"), order("B"), order("C", delivery_date="2026-12-01")]
    stacked = stack_levels(orders, 3)
    assert sorted(o["po_number"] for o in stacked) == ["A", "B", "C"]
    assert all("level" not in o for o in orders)


def test_min_gap_days_grows_with_the_days_shown_on_the_axis():
    today = date(2026, 11, 3)
    narrow = [order("A", delivery_date="2026-11-05"), order("B", delivery_date="2026-11-20")]
    wide = [order("A", delivery_date="2026-10-20"), order("B", delivery_date="2027-01-30")]
    assert min_gap_days(narrow, today) == 1   # 23 days on the axis: every day has room for a dot
    assert min_gap_days(wide, today) == 3     # 108 days on the axis: 3 days per dot


def test_due_soon_end_is_today_plus_14_days():
    assert due_soon_end(date(2026, 11, 3)) == date(2026, 11, 17)


def test_x_range_includes_the_14_day_line_even_when_all_orders_are_earlier():
    low, high = x_range([order("A", delivery_date="2026-10-20")], date(2026, 11, 3))
    assert low == "2026-10-17"          # earliest order minus 3 days
    assert high == "2026-11-20"         # today + 14 days plus 3 days


def test_hover_text_has_the_main_facts():
    text = hover_text(order("PO26-1", "escalate", flags=["OVERDUE"], memo="late", reason="Price change"))
    for part in ["PO26-1", "Acme", "2026-11-10", "OVERDUE", "escalate", "Price change", "late"]:
        assert part in text


def test_hover_text_escapes_html_from_the_erp():
    text = hover_text(order("PO26-1", memo='<script>x</script> & "q"'))
    assert "<script>" not in text
    assert "&lt;script&gt;" in text


def test_hover_text_shows_the_review_status_only_when_given():
    assert "Review: approved" in hover_text(order("PO26-1"), "approved")
    assert "Review:" not in hover_text(order("PO26-1"))


def test_hover_text_for_empty_memo():
    assert "Memo: (none)" in hover_text(order("PO26-1"))


def test_describe_age():
    def ago(**kw):
        return describe_age((NOW - timedelta(**kw)).isoformat(), NOW)
    assert ago(seconds=10) == "just now"
    assert ago(minutes=12) == "12 min ago"
    assert ago(hours=3, minutes=5) == "3 h ago"
    assert ago(days=2, hours=1) == "2 days ago"


def test_is_stale_after_24_hours():
    assert not is_stale((NOW - timedelta(hours=23, minutes=59)).isoformat(), NOW)
    assert is_stale((NOW - timedelta(hours=24)).isoformat(), NOW)


def test_describe_proposal_for_a_date_a_missing_date_and_a_confirmation():
    date_change = {"field": "confirmed_delivery_date", "current_value": "2026-10-31", "proposed_value": "2026-11-27"}
    assert describe_proposal(date_change) == "Confirmed delivery date: 2026-10-31 -> 2026-11-27"
    from_empty = {**date_change, "current_value": None}
    assert describe_proposal(from_empty) == "Confirmed delivery date: (empty) -> 2026-11-27"
    confirmation = {"field": "order_confirmation_received", "current_value": False, "proposed_value": True}
    assert describe_proposal(confirmation) == "Order confirmation received: no -> yes"


def test_describe_recipient_shows_name_address_kind_and_language():
    supplier = {"name": "Petra Lange", "email": "vertrieb@marinetec.example", "kind": "supplier", "language": "German"}
    assert describe_recipient(supplier) == "Petra Lange <vertrieb@marinetec.example> (supplier, German)"
    manager = {"name": "Sanne de Wit", "email": "sanne@brakwater.example", "kind": "project_manager", "language": "Dutch"}
    assert describe_recipient(manager) == "Sanne de Wit <sanne@brakwater.example> (project manager, Dutch)"
