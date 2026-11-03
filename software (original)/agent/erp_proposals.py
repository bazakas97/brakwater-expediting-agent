"""Proposed ERP updates, from the facts the LLM read in a memo. Plain, exact code: no LLM here.

The LLM only says WHAT the memo states (a confirmation was received, a delivery week or date is
named). This file turns that into dates, compares it with what the ERP says now, and drops
everything the ERP already has. A proposal is only a suggestion: a buyer enters it in the ERP by
hand. Nothing here writes to the ERP.

Two fields only: confirmed_delivery_date and order_confirmation_received.
"""
from datetime import date

from memo_facts import MemoFacts

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _nearest(candidates: list[date | None], today: date) -> date | None:
    """The candidate closest to today (on a tie, the one in the future). None if there is none.

    A week or a day without a year is read as the year that puts it nearest to today:
    "wk 44" said in the first days of November is last week (this year, so late), while
    "KW 2" said in December is January of next year."""
    valid = [c for c in candidates if c is not None]
    if not valid:
        return None
    return min(valid, key=lambda c: (abs((c - today).days), c < today))


def _day_or_none(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:  # for example 29 February in a year that has none
        return None


def _friday_or_none(year: int, week: int) -> date | None:
    try:
        return date.fromisocalendar(year, week, 5)  # ISO weeks; KW in German memos is ISO as well
    except ValueError:  # not every year has an ISO week 53
        return None


def _short(day: date) -> str:
    return f"{day.day} {MONTHS[day.month - 1]}"


def resolve_delivery(facts: MemoFacts, today: date) -> tuple[date, str | None] | None:
    """The delivery date a memo names, and a note for the buyer. None if the memo names no date.

    A week gives the FRIDAY of that ISO week (the field needs one day, the memo gives none; the
    note says so). A date or week that ends up before today is kept, with a note that it is late."""
    years = [today.year - 1, today.year, today.year + 1]
    if facts.delivery_kind == "date":
        chosen = _nearest([_day_or_none(y, facts.month, facts.day) for y in years], today)
        note = None
    elif facts.delivery_kind == "week":
        chosen = _nearest([_friday_or_none(y, facts.week) for y in years], today)
        if chosen is None:
            return None
        monday = date.fromordinal(chosen.toordinal() - 4)
        note = (f"Week {facts.week}: Mon {_short(monday)} - Fri {_short(chosen)}. "
                f"The memo gives no day, check.")
    else:
        return None
    if chosen is None:
        return None
    if chosen < today:
        past = "This date is already in the past: the delivery is late."
        note = f"{note} {past}" if note else past
    return chosen, note


def _proposal(field: str, current, proposed, evidence: str, note: str | None) -> dict:
    return {"field": field, "current_value": current, "proposed_value": proposed,
            "evidence": evidence, "note": note}


def build_proposals(order: dict, facts: MemoFacts, today: date) -> list[dict]:
    """What the memo says that the ERP does not say yet. An empty list if the ERP is up to date."""
    proposals = []
    if facts.confirmation == "yes" and not order["order_confirmation_received"]:
        proposals.append(_proposal("order_confirmation_received", False, True, facts.quote, None))
    resolved = resolve_delivery(facts, today)
    if resolved:
        new_date, note = resolved
        current = order["confirmed_delivery_date"]
        if new_date.isoformat() != current:
            proposals.append(_proposal("confirmed_delivery_date", current, new_date.isoformat(), facts.quote, note))
    return proposals
