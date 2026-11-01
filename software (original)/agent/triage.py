"""Decide which open orders need the LLM and which need no action.

An order goes to the LLM if it has at least one flag (see expediting.flag_order)
or a non-empty memo. Everything else gets the action "none" straight from code.

Pure function: no API calls, no LLM calls.
"""
from datetime import date

from expediting import flag_order

NO_ACTION_REASON = "On time, confirmed, no notes"


def split_orders(orders: list[dict], today: date) -> tuple[list[dict], list[dict]]:
    """Split orders into (for_llm, no_action). Every order ends up in exactly one list."""
    for_llm = []
    no_action = []
    for po in orders:
        flags = flag_order(po, today)
        has_memo = bool(po.get("memo", "").strip())
        if flags or has_memo:
            for_llm.append({**po, "flags": flags})
        else:
            no_action.append({**po, "flags": flags, "action": "none", "reason": NO_ACTION_REASON})
    return for_llm, no_action
