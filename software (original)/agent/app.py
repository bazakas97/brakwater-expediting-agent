"""The page. It ONLY reads data/decisions.json and draws it.

Streamlit runs this whole script again on every click, so it must never call the LLM or the API.
All exact logic (sorting, stacking, counting) lives in view.py, which has tests.

Run:  docker compose up app     then open http://localhost:8501
"""
import json
from datetime import date, datetime, timezone
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from view import (ACTIONS, MARKER_SIZE_PX, describe_age, due_soon_end, hover_text, is_stale, min_gap_days,
                  sort_orders, stack_levels, summary_line, x_range)

DATA_PATH = Path(__file__).parent / "data" / "decisions.json"

# Colors: the status steps of the dataviz palette (red, orange) and a neutral grey for "none".
# Color is not the only signal: every action also has its own shape and a legend entry.
STYLE = {
    "escalate": {"label": "escalate", "color": "#d03b3b", "symbol": "diamond"},
    "chase_supplier": {"label": "chase supplier", "color": "#ec835a", "symbol": "square"},
    "none": {"label": "none", "color": "#8a8985", "symbol": "circle"},
}


def timeline(orders: list[dict], today: date) -> go.Figure:
    stacked = stack_levels(orders, min_gap_days(orders, today))
    fig = go.Figure()
    for action in ACTIONS:
        dots = [o for o in stacked if o["action"] == action]
        fig.add_trace(go.Scatter(
            x=[o["delivery_date"] for o in dots],
            y=[o["level"] for o in dots],
            mode="markers",
            name=f"{STYLE[action]['label']} ({len(dots)})",
            marker={"size": MARKER_SIZE_PX, "color": STYLE[action]["color"], "symbol": STYLE[action]["symbol"]},
            text=[hover_text(o) for o in dots],
            hovertemplate="%{text}<extra></extra>",
        ))
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
    today = date.fromisoformat(data["business_date"])
    now = datetime.now(timezone.utc)

    st.caption(f"Data built {data['built_at'].replace('T', ' ')} ({describe_age(data['built_at'], now)}) · "
               f"business date {today} · LLM mode: {data['llm_mode']}")
    if is_stale(data["built_at"], now):
        st.warning("This data is more than 24 hours old. Build it again: "
                   "docker compose run --rm agent python build_decisions.py")
    if data["llm_mode"] == "fake":
        st.info("Fake mode: the actions come from simple rules, not from the LLM.")

    st.subheader(summary_line(orders))
    st.plotly_chart(timeline(orders, today))
    st.dataframe(table_rows(orders), hide_index=True)


main()
