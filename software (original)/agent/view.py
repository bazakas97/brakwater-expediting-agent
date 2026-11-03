"""Exact helpers for the page: sorting, stacking, counting, file age. Plain code, no Streamlit or Plotly."""
import html
import math
import textwrap
from datetime import date, datetime, timedelta

from expediting import DUE_SOON_DAYS

ACTIONS = ["escalate", "chase_supplier", "book_in", "wait", "none"]  # most urgent first
LABELS = {"escalate": "escalate", "chase_supplier": "chase", "book_in": "book in", "wait": "wait", "none": "none"}
STALE_AFTER_HOURS = 24
HOVER_WIDTH = 60
MARKER_SIZE_PX = 13
DOT_SPACE_PX = MARKER_SIZE_PX + 3  # a dot and a little air around it
ASSUMED_WIDTH_PX = 800  # a safe guess for the width of the chart


def sort_orders(orders: list[dict]) -> list[dict]:
    """escalate first, then chase_supplier, then none; by delivery date inside each group."""
    return sorted(orders, key=lambda o: (ACTIONS.index(o["action"]), o["delivery_date"], o["po_number"]))


def count_actions(orders: list[dict]) -> dict[str, int]:
    counts = {action: 0 for action in ACTIONS}
    for order in orders:
        counts[order["action"]] += 1
    return counts


def summary_line(orders: list[dict]) -> str:
    counts = count_actions(orders)
    parts = ", ".join(f"{counts[action]} {LABELS[action]}" for action in ACTIONS)
    return f"{len(orders)} open orders: {parts}"


def stack_levels(orders: list[dict], min_gap_days: int) -> list[dict]:
    """Copies of the orders with a "level" (1, 2, 3...), the height of the dot in the timeline.
    Two dots less than min_gap_days apart never share a level, so none hides another.
    The most urgent actions are placed first, so they get the lowest levels."""
    dates_on_level: dict[int, list[date]] = {}
    stacked = []
    for order in sorted(orders, key=lambda o: (ACTIONS.index(o["action"]), o["delivery_date"], o["po_number"])):
        day = date.fromisoformat(order["delivery_date"])
        level = 1
        while any(abs((day - other).days) < min_gap_days for other in dates_on_level.get(level, [])):
            level += 1
        dates_on_level.setdefault(level, []).append(day)
        stacked.append({**order, "level": level})
    return stacked


def min_gap_days(orders: list[dict], today: date) -> int:
    """How many days two dots must be apart to not touch. Depends on how many days the axis
    shows and on an ASSUMED chart width (the real width of the browser window is not known)."""
    low, high = x_range(orders, today)
    days_on_axis = (date.fromisoformat(high) - date.fromisoformat(low)).days
    return max(1, math.ceil(DOT_SPACE_PX * days_on_axis / ASSUMED_WIDTH_PX))


def due_soon_end(today: date) -> date:
    return today + timedelta(days=DUE_SOON_DAYS)


def x_range(orders: list[dict], today: date) -> list[str]:
    """Date range for the timeline axis: all orders plus both vertical lines, with a little margin."""
    dates = [date.fromisoformat(o["delivery_date"]) for o in orders] + [today, due_soon_end(today)]
    return [(min(dates) - timedelta(days=3)).isoformat(), (max(dates) + timedelta(days=3)).isoformat()]


def _wrapped(text: str) -> str:
    return "<br>".join(html.escape(line) for line in textwrap.wrap(text, HOVER_WIDTH))


def hover_text(order: dict, review_status: str | None = None) -> str:
    """The hover box of one dot. Text from the ERP is escaped, only our own <b> and <br> are HTML."""
    flags = ", ".join(order["flags"]) or "none"
    lines = [
        f"<b>{html.escape(order['po_number'])}</b> · {html.escape(order['supplier_name'])}",
        f"Delivery: {order['delivery_date']}",
        f"Flags: {html.escape(flags)}",
        f"Action: {order['action']}",
    ]
    if review_status:
        lines.append(f"Review: {review_status}")
    lines += [
        f"Reason: {_wrapped(order['reason'])}",
        f"Memo: {_wrapped(order['memo']) or '(none)'}",
    ]
    return "<br>".join(lines)


FIELD_LABELS = {"confirmed_delivery_date": "Confirmed delivery date", "order_confirmation_received": "Order confirmation received"}


def _show_value(value) -> str:
    if value is None:
        return "(empty)"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def describe_proposal(proposal: dict) -> str:
    """One line for a buyer, e.g. 'Confirmed delivery date: 2026-10-31 -> 2026-11-27'."""
    label = FIELD_LABELS[proposal["field"]]
    return f"{label}: {_show_value(proposal['current_value'])} -> {_show_value(proposal['proposed_value'])}"


RECIPIENT_KINDS = {"supplier": "supplier", "project_manager": "project manager",
                   "head_of_purchasing": "head of purchasing"}


def describe_recipient(draft: dict) -> str:
    """Who gets the draft, e.g. 'Petra Lange <vertrieb@marinetec-hydraulik.example> (supplier, German)'."""
    return f"{draft['name']} <{draft['email']}> ({RECIPIENT_KINDS[draft['kind']]}, {draft['language']})"


def describe_age(built_at: str, now: datetime) -> str:
    """How old the file is, e.g. "12 min ago". Both times must have a time zone."""
    seconds = int((now - datetime.fromisoformat(built_at)).total_seconds())
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} h ago"
    return f"{hours // 24} days ago"


def is_stale(built_at: str, now: datetime) -> bool:
    return now - datetime.fromisoformat(built_at) >= timedelta(hours=STALE_AFTER_HOURS)
