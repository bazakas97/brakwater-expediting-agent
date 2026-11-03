"""The page. It reads data/decisions.json and shows what a buyer must review.

Approve / Reject is saved to data/reviews.json by reviews.py: that is the ONLY thing this page writes.
It never calls the LLM, the ERP or email. Streamlit runs this whole script again on every click,
so all exact logic lives in view.py and reviews.py, which have tests.

Run:  docker compose up app     then open http://localhost:8501
"""
import json
from datetime import date, datetime, timezone
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from reviews import (APPROVED, REJECTED, describe_review, latest_by_po, load_reviews, make_review, orders_to_review,
                     progress, save_review, statuses)
from view import (ACTIONS, MARKER_SIZE_PX, describe_age, describe_proposal, describe_recipient, due_soon_end, hover_text, is_stale, min_gap_days,
                  sort_orders, stack_levels, summary_line, x_range)

DATA_PATH = Path(__file__).parent / "data" / "decisions.json"

# Colors: red and orange are the status steps of the dataviz palette, blue and aqua come from the
# categorical palette, and "none" is a darker neutral grey that recedes. Color is never the only
# signal: every action has its own shape and a legend entry (the validator asks for this, because
# aqua and orange are hard to tell apart with some forms of color blindness).
STYLE = {
    "escalate": {"label": "escalate", "color": "#d03b3b", "symbol": "diamond"},
    "chase_supplier": {"label": "chase supplier", "color": "#ec835a", "symbol": "square"},
    "book_in": {"label": "book in", "color": "#2a78d6", "symbol": "triangle-up"},
    "wait": {"label": "wait", "color": "#1baf7a", "symbol": "cross"},
    "none": {"label": "none", "color": "#767571", "symbol": "circle"},
}


def timeline(orders: list[dict], today: date, status_by_po: dict[str, str]) -> go.Figure:
    """One dot per order. A hollow dot is an order with a valid review (the shape stays the same)."""
    stacked = stack_levels(orders, min_gap_days(orders, today))
    reviewed = {po for po, status in status_by_po.items() if status in (APPROVED, REJECTED)}
    fig = go.Figure()
    for action in ACTIONS:
        dots = [o for o in stacked if o["action"] == action]
        style = STYLE[action]
        for is_reviewed in (False, True):
            part = [o for o in dots if (o["po_number"] in reviewed) == is_reviewed]
            fig.add_trace(go.Scatter(
                x=[o["delivery_date"] for o in part],
                y=[o["level"] for o in part],
                mode="markers",
                name=f"{style['label']} ({len(dots)})",
                legendgroup=action,
                showlegend=not is_reviewed,  # one legend entry per action
                marker={"size": MARKER_SIZE_PX, "color": style["color"],
                        "symbol": style["symbol"] + ("-open" if is_reviewed else ""),
                        "line": {"width": 2 if is_reviewed else 0, "color": style["color"]}},
                text=[hover_text(o, status_by_po.get(o["po_number"])) for o in part],
                hovertemplate="%{text}<extra></extra>",
            ))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="hollow = reviewed", hoverinfo="skip",
                             marker={"size": MARKER_SIZE_PX, "color": "#8a8985", "symbol": "circle-open",
                                     "line": {"width": 2, "color": "#8a8985"}}))
    # Each label sits on the OUTSIDE of its line (today to the left, today + 14 days to the right),
    # above the plot, so the two labels can never overlap, even in a narrow window.
    for day, label, side in [(today, "today", "right"), (due_soon_end(today), "today + 14 days", "left")]:
        fig.add_shape(type="line", x0=day.isoformat(), x1=day.isoformat(), y0=0, y1=1, yref="paper",
                      line={"dash": "dash", "width": 1.5, "color": "#8a8985"})
        fig.add_annotation(x=day.isoformat(), y=1, yref="paper", text=label, showarrow=False,
                           yanchor="bottom", xanchor=side, xshift=-4 if side == "right" else 4)
    top_level = max(o["level"] for o in stacked)
    fig.update_xaxes(type="date", range=x_range(orders, today), title="Effective delivery date")
    fig.update_yaxes(visible=False, range=[0.4, top_level + 0.8])
    fig.update_layout(height=max(280, 140 + 38 * top_level), margin={"t": 30, "b": 10, "l": 10, "r": 10},
                      legend={"orientation": "h", "yanchor": "top", "y": -0.25}, hovermode="closest")
    return fig


def review_card(order: dict, status: str, review: dict | None, built_at: str) -> None:
    style = STYLE[order["action"]]
    with st.container(border=True):
        st.markdown(f"**{order['po_number']}** · {order['supplier_name']} · delivery {order['delivery_date']} · "
                    f"**{style['label'].upper()}**")
        st.text(f"Flags: {', '.join(order['flags']) or 'none'}")
        st.text(f"Memo: {order['memo'] or '(none)'}")
        st.text(f"Reason: {order['reason']}")
        proposals = order.get("erp_proposals", [])  # older files have none
        for proposal in proposals:
            st.markdown(f"**Proposed ERP update:** {describe_proposal(proposal)}")
            details = " ".join(part for part in [proposal["note"], f"Memo: \"{proposal['evidence']}\""] if part)
            st.caption(details)
        if proposals:
            st.caption("Enter this in the ERP by hand. This system never writes to the ERP.")
        draft = order.get("draft_email")  # older files have none
        if draft:
            with st.expander("Draft email"):
                st.markdown(f"**To:** {describe_recipient(draft)}")
                if draft["note"]:
                    st.caption(draft["note"])
                if draft["problem"]:
                    st.warning(draft["problem"])
                else:
                    st.markdown(f"**Subject:** {draft['subject']}")
                    st.code(draft["body"], language=None, wrap_lines=True)  # the code box has a copy button
                    st.caption("Copy it into your own email and change what you like. This system never sends email.")
        st.caption(describe_review(status, review))
        with st.form(key=f"review_{order['po_number']}", clear_on_submit=True, border=False):
            comment = st.text_input("Comment (optional)", key=f"comment_{order['po_number']}")
            approve_column, reject_column, _ = st.columns([1, 1, 4])
            approve = approve_column.form_submit_button("Approve", type="primary")
            reject = reject_column.form_submit_button("Reject")
        if approve or reject:
            save_review(make_review(order, "approved" if approve else "rejected", comment, built_at))
            st.rerun()


def table_rows(orders: list[dict]) -> list[dict]:
    return [{
        "Action": STYLE[o["action"]]["label"],
        "PO": o["po_number"],
        "Supplier": o["supplier_name"],
        "Project": o["project"],
        "Delivery": o["delivery_date"],
        "Flags": ", ".join(o["flags"]),
        "Reason": o["reason"],
        "Memo": o["memo"],
        "Source": o["source"],
    } for o in sort_orders(orders)]


def main() -> None:
    st.set_page_config(page_title="Brakwater open orders", layout="wide")
    st.title("Open orders")

    if not DATA_PATH.exists():
        st.error("No data/decisions.json yet. Build it first: "
                 "docker compose run --rm agent python build_decisions.py")
        st.stop()
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    orders = data["orders"]
    built_at = data["built_at"]
    today = date.fromisoformat(data["business_date"])
    now = datetime.now(timezone.utc)

    st.caption(f"Data built {built_at.replace('T', ' ')} ({describe_age(built_at, now)}) · "
               f"business date {today} · LLM mode: {data['llm_mode']}")
    if is_stale(built_at, now):
        st.warning("This data is more than 24 hours old. Build it again: "
                   "docker compose run --rm agent python build_decisions.py")
    if data["llm_mode"] == "fake":
        st.info("Fake mode: the actions come from simple rules, not from the LLM.")

    to_review = orders_to_review(orders)
    reviews = load_reviews()
    status_by_po = statuses(to_review, reviews, built_at)
    done, total = progress(to_review, status_by_po)

    st.subheader(summary_line(orders))
    st.progress(done / total if total else 1.0, text=f"Reviewed {done} of {total}")
    st.plotly_chart(timeline(orders, today, status_by_po))

    st.header(f"To review ({total})")
    latest = latest_by_po(reviews)
    for order in to_review:
        review_card(order, status_by_po[order["po_number"]], latest.get(order["po_number"]), built_at)

    no_action = [o for o in orders if o["action"] == "none"]
    with st.expander(f"No action needed ({len(no_action)})"):
        st.dataframe(table_rows(no_action), hide_index=True)


main()
