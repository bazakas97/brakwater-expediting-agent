"""The picture itself: what the Plotly figure contains. Only drawing, but the legend once went wrong."""
from datetime import date

import app
from view import ACTIONS

TODAY = date(2026, 11, 3)


def order(po: str, action: str, delivery_date: str = "2026-11-10") -> dict:
    return {"po_number": po, "supplier_name": "Acme", "action": action, "delivery_date": delivery_date,
            "flags": [], "memo": "", "reason": "r"}


ORDERS = [order(f"P{i}", action, f"2026-11-{10 + i:02d}") for i, action in enumerate(ACTIONS)]


def legend_names(fig) -> list[str]:
    return [t.name for t in fig.data if t.showlegend is not False]


def test_every_action_is_in_the_legend_when_nothing_is_reviewed():
    names = legend_names(app.timeline(ORDERS, TODAY, {}))
    for action in ACTIONS:
        assert any(name.startswith(app.STYLE[action]["label"]) for name in names), action


def test_every_action_is_still_in_the_legend_when_all_its_dots_are_reviewed():
    # This is the bug in the first screenshot: escalate, chase and book in vanished from the legend.
    everything_reviewed = {o["po_number"]: "approved" for o in ORDERS if o["action"] != "none"}
    names = legend_names(app.timeline(ORDERS, TODAY, everything_reviewed))
    for action in ACTIONS:
        assert any(name.startswith(app.STYLE[action]["label"]) for name in names), action
    assert "hollow = reviewed" in names


def test_the_legend_counts_all_dots_of_an_action_reviewed_or_not():
    orders = ORDERS + [order("EXTRA", "escalate", "2026-12-01")]
    fig = app.timeline(orders, TODAY, {"EXTRA": "approved"})
    assert "escalate (2)" in legend_names(fig)


def test_the_dots_of_an_action_share_its_legend_group_so_one_click_hides_them_all():
    fig = app.timeline(ORDERS, TODAY, {ORDERS[0]["po_number"]: "approved"})
    for action in ACTIONS:
        group = [t for t in fig.data if t.legendgroup == action]
        assert len(group) == 3  # the legend entry, the dots without review, the dots with review


def test_reviewed_dots_are_hollow_and_the_others_are_filled():
    fig = app.timeline(ORDERS, TODAY, {ORDERS[0]["po_number"]: "rejected"})
    symbols = {t.marker.symbol for t in fig.data if t.x and t.x[0] is not None}
    assert "diamond-open" in symbols and "diamond" not in symbols  # the only escalate dot is reviewed
    assert "square" in symbols  # a chase dot without review stays filled


def test_an_outdated_review_does_not_make_a_dot_hollow():
    fig = app.timeline(ORDERS, TODAY, {ORDERS[0]["po_number"]: "outdated"})
    symbols = {t.marker.symbol for t in fig.data if t.x and t.x[0] is not None}
    assert "diamond" in symbols and "diamond-open" not in symbols
