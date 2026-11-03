from datetime import date

from erp_proposals import build_proposals, resolve_delivery
from memo_facts import MemoFacts

TODAY = date(2026, 11, 3)  # a Tuesday, in ISO week 45


def week(number: int) -> MemoFacts:
    return MemoFacts(confirmation="not_mentioned", delivery_kind="week", week=number, quote="memo text")


def day(d: int, m: int) -> MemoFacts:
    return MemoFacts(confirmation="not_mentioned", delivery_kind="date", day=d, month=m, quote="memo text")


def facts(confirmation: str = "not_mentioned", **delivery) -> MemoFacts:
    kind = "none" if not delivery else ("week" if "week" in delivery else "date")
    return MemoFacts(confirmation=confirmation, delivery_kind=kind, quote="the memo line", **delivery)


def erp(confirmed: str | None = "2026-10-31", received: bool = True) -> dict:
    return {"confirmed_delivery_date": confirmed, "order_confirmation_received": received}


# --- a week becomes the Friday of that ISO week ---

def test_week_48_in_2026_is_friday_27_november_2026():
    resolved_date, note = resolve_delivery(week(48), TODAY)
    assert resolved_date == date(2026, 11, 27)
    assert resolved_date.strftime("%A") == "Friday"
    assert "Week 48: Mon 23 Nov - Fri 27 Nov" in note
    assert "The memo gives no day, check" in note
    assert "past" not in note


def test_a_week_that_just_passed_stays_in_this_year_and_is_flagged_as_late():
    # Said as "wk 44" and it is now week 45: the supplier is late, so it is NOT moved to next year.
    resolved_date, note = resolve_delivery(week(44), TODAY)
    assert resolved_date == date(2026, 10, 30)
    assert "already in the past" in note


def test_a_week_long_gone_is_read_as_next_year():
    # "KW 2" said in December can only mean January of next year, not January of this year.
    resolved_date, note = resolve_delivery(week(2), date(2026, 12, 20))
    assert resolved_date == date(2027, 1, 15)
    assert "past" not in note


def test_the_current_week_is_not_flagged_as_late():
    resolved_date, note = resolve_delivery(week(45), TODAY)  # Friday 6 Nov, still ahead
    assert resolved_date == date(2026, 11, 6)
    assert "past" not in note


def test_week_53_does_not_crash_in_a_year_without_one():
    # 2027 has no ISO week 53; the only valid one nearby is week 53 of 2026 (Friday 1 Jan 2027).
    resolved_date, note = resolve_delivery(week(53), date(2027, 6, 1))
    assert resolved_date == date(2027, 1, 1)
    assert "already in the past" in note


# --- a day and month without a year ---

def test_a_day_and_month_in_the_near_future_use_this_year():
    assert resolve_delivery(day(21, 11), TODAY) == (date(2026, 11, 21), None)


def test_a_january_date_said_in_december_is_next_year():
    assert resolve_delivery(day(5, 1), date(2026, 12, 20)) == (date(2027, 1, 5), None)


def test_a_date_that_does_not_exist_gives_nothing():
    assert resolve_delivery(day(29, 2), date(2026, 12, 1)) is None  # none of 2025, 2026, 2027 is a leap year


def test_a_date_before_today_is_kept_and_flagged():
    resolved_date, note = resolve_delivery(day(28, 10), TODAY)
    assert resolved_date == date(2026, 10, 28)
    assert "already in the past" in note


def test_no_delivery_in_the_memo_gives_nothing():
    assert resolve_delivery(facts(), TODAY) is None


# --- proposals: what the memo says and the ERP does not say yet ---

def test_a_new_delivery_week_gives_a_proposal_with_current_and_proposed_value():
    [proposal] = build_proposals(erp("2026-10-31"), week(48), TODAY)
    assert proposal["field"] == "confirmed_delivery_date"
    assert proposal["current_value"] == "2026-10-31"
    assert proposal["proposed_value"] == "2026-11-27"
    assert proposal["evidence"] == "memo text"
    assert "Week 48" in proposal["note"]


def test_no_proposal_when_the_erp_already_has_that_date():
    assert build_proposals(erp("2026-11-21"), day(21, 11), TODAY) == []


def test_an_empty_erp_date_gets_a_proposal():
    [proposal] = build_proposals(erp(None), day(21, 11), TODAY)
    assert (proposal["current_value"], proposal["proposed_value"]) == (None, "2026-11-21")


def test_confirmation_received_in_the_memo_but_not_in_the_erp_gives_a_proposal():
    [proposal] = build_proposals(erp(received=False), facts("yes"), TODAY)
    assert proposal["field"] == "order_confirmation_received"
    assert (proposal["current_value"], proposal["proposed_value"]) == (False, True)


def test_no_proposal_when_the_erp_already_has_the_confirmation():
    assert build_proposals(erp(received=True), facts("yes"), TODAY) == []


def test_a_missing_confirmation_never_gives_a_proposal():
    assert build_proposals(erp(received=False), facts("no", week=46), TODAY)[0]["field"] == "confirmed_delivery_date"
    assert [p["field"] for p in build_proposals(erp(received=False), facts("no"), TODAY)] == []


def test_confirmation_and_date_together_give_two_proposals_confirmation_first():
    proposals = build_proposals(erp(None, received=False), facts("yes", day=21, month=11), TODAY)
    assert [p["field"] for p in proposals] == ["order_confirmation_received", "confirmed_delivery_date"]


def test_nothing_in_the_memo_gives_no_proposals():
    assert build_proposals(erp(), facts(), TODAY) == []
