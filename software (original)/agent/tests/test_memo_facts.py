from datetime import date

import pytest

import memo_facts
from memo_facts import MemoFacts, build_memo_message, check_quote, extract_facts

TODAY = date(2026, 11, 3)


def order(memo: str) -> dict:
    return {"po_number": "PO1", "memo": memo}


@pytest.fixture
def fake_mode(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "fake")


@pytest.fixture
def real_mode(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "real")


# --- the facts model ---

def test_facts_with_nothing_stated_are_valid_without_a_quote():
    MemoFacts(confirmation="not_mentioned", delivery_kind="none")


@pytest.mark.parametrize("fields", [
    {"delivery_kind": "date", "day": 21},                 # no month
    {"delivery_kind": "date", "day": 32, "month": 1},     # no such day
    {"delivery_kind": "date", "day": 1, "month": 13},     # no such month
    {"delivery_kind": "week"},                            # no week number
    {"delivery_kind": "week", "week": 0},
    {"delivery_kind": "week", "week": 54},
])
def test_incomplete_or_impossible_delivery_facts_are_invalid(fields):
    with pytest.raises(ValueError):
        MemoFacts(confirmation="not_mentioned", quote="memo text", **fields)


def test_a_stated_fact_needs_a_quote():
    with pytest.raises(ValueError, match="quote"):
        MemoFacts(confirmation="yes", delivery_kind="none", quote="  ")


def test_the_quote_must_be_in_the_memo_ignoring_line_breaks_and_spaces():
    memo = "24/10 YA: OB ontvangen per mail,\nnog niet ingevoerd."
    facts = MemoFacts(confirmation="yes", delivery_kind="none", quote="OB ontvangen per mail, nog niet ingevoerd.")
    check_quote(facts, memo)
    invented = MemoFacts(confirmation="yes", delivery_kind="none", quote="OB is binnen")
    with pytest.raises(ValueError, match="quote is not in the memo"):
        check_quote(invented, memo)


# --- fake mode: simple patterns on the memos of the sandbox ---

def test_fake_reads_a_delivery_week():
    facts = extract_facts(order("21/10 LV: tel. Erik (Aluprofiel): levering uitgesteld naar wk 48, extrusie loopt achter."), TODAY)
    assert (facts.delivery_kind, facts.week, facts.confirmation) == ("week", 48, "not_mentioned")


def test_fake_reads_confirmation_and_date_together_and_ignores_the_date_of_the_note():
    facts = extract_facts(order("24/10 YA: OB ontvangen per mail, nog niet ingevoerd. Levering 21/11 volgens OB."), TODAY)
    assert facts.confirmation == "yes"
    assert (facts.delivery_kind, facts.day, facts.month) == ("date", 21, 11)  # not 24/10, the note date


def test_fake_takes_the_new_date_not_the_old_one():
    facts = extract_facts(order("30/09 LV: OB ontvangen, levering 19/11 i.p.v. 29/10."), TODAY)
    assert (facts.day, facts.month) == (19, 11)


def test_fake_reads_a_missing_confirmation_with_a_german_week():
    facts = extract_facts(order("27/10 LV: AB fehlt noch, Liefertermin KW 46 telefonisch zugesagt (Hr. Weber)."), TODAY)
    assert (facts.confirmation, facts.delivery_kind, facts.week) == ("no", "week", 46)


def test_fake_reads_nothing_from_a_routine_memo_or_a_price_memo():
    for memo in ["Leverancier levert in twee delen.", "Prijs volgens raamafspraak 2026.",
                 '30/10 LV: mail ontvangen: "we need a surcharge of 8%"', "21/10 YA: LT 6-8 wks per supplier, ETA tbc. OC not received yet."]:
        facts = extract_facts(order(memo), TODAY)
        assert facts.delivery_kind == "none", memo
        assert facts.confirmation in ("not_mentioned", "no"), memo


def test_fake_newest_line_wins():
    facts = extract_facts(order("22/10 LV: levering wk 44\n27/10 LV: levering uitgesteld naar wk 46"), TODAY)
    assert facts.week == 46
    assert facts.quote == "27/10 LV: levering uitgesteld naar wk 46"


def test_fake_quote_is_always_text_from_the_memo():
    memo = "24/10 YA: OB ontvangen per mail, nog niet ingevoerd. Levering 21/11 volgens OB."
    check_quote(extract_facts(order(memo), TODAY), memo)


def test_unset_or_empty_mode_means_fake(monkeypatch):
    monkeypatch.delenv("LLM_MODE", raising=False)
    assert extract_facts(order("levering wk 48"), TODAY).week == 48
    monkeypatch.setenv("LLM_MODE", "")
    assert extract_facts(order("levering wk 48"), TODAY).week == 48


# --- real mode, with the model call mocked (no network) ---

GOOD = {"confirmation": "no", "delivery_kind": "week", "week": 46, "quote": "AB fehlt noch, Liefertermin KW 46"}
MEMO = "27/10 LV: AB fehlt noch, Liefertermin KW 46 telefonisch zugesagt (Hr. Weber)."


def test_real_mode_returns_valid_facts(real_mode, monkeypatch):
    monkeypatch.setattr(memo_facts, "_call_memo_llm", lambda memo, today, error=None: GOOD)
    assert extract_facts(order(MEMO), TODAY).week == 46


def test_real_mode_invalid_twice_gives_none_after_exactly_one_retry(real_mode, monkeypatch):
    calls = []
    monkeypatch.setattr(memo_facts, "_call_memo_llm", lambda memo, today, error=None: calls.append(error) or {"x": 1})
    assert extract_facts(order(MEMO), TODAY) is None
    assert len(calls) == 2 and calls[0] is None and calls[1]


def test_real_mode_an_invented_quote_is_rejected_and_the_retry_says_why(real_mode, monkeypatch):
    answers = iter([{**GOOD, "quote": "OB is binnen gekomen"}, GOOD])
    errors = []

    def call(memo, today, error=None):
        errors.append(error)
        return next(answers)

    monkeypatch.setattr(memo_facts, "_call_memo_llm", call)
    assert extract_facts(order(MEMO), TODAY).quote == GOOD["quote"]
    assert errors[0] is None
    assert "quote is not in the memo" in errors[1]


# --- the message and the prompt ---

def test_message_has_the_memo_and_today_and_the_error_on_a_retry():
    plain = build_memo_message("levering wk 48", TODAY)
    assert "levering wk 48" in plain and "2026-11-03" in plain and "rejected" not in plain
    assert "week 99" in build_memo_message("x", TODAY, error="week 99 is not valid")


def test_prompt_warns_about_the_date_at_the_start_of_a_memo_line_and_names_iso_weeks():
    assert "start of a memo line" in memo_facts.SYSTEM_PROMPT
    assert "ISO week" in memo_facts.SYSTEM_PROMPT and "KW" in memo_facts.SYSTEM_PROMPT
