from datetime import date

import pytest

import llm
from context import NO_CUSTOMER_DATE
from decision import MAX_REASON_WORDS, Decision
from expediting import DUE_SOON, OVERDUE

TODAY = date(2026, 11, 2)
CONTEXT = {"contact_policy": "Standard", "customer_delivery_date": "2027-01-01"}


def order(po_number: str = "PO1", flags: list[str] | None = None, memo: str = "") -> dict:
    return {"po_number": po_number, "flags": flags or [], "memo": memo}


def words(n: int) -> str:
    return " ".join(["word"] * n)


@pytest.fixture
def fake_mode(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "fake")


@pytest.fixture
def real_mode(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "real")


# --- fake mode ---

def test_overdue_order_gives_escalate(fake_mode):
    assert llm.decide(order(flags=[OVERDUE]), TODAY, CONTEXT).action == "escalate"


def test_due_soon_order_gives_chase_supplier(fake_mode):
    assert llm.decide(order(flags=[DUE_SOON]), TODAY, CONTEXT).action == "chase_supplier"


def test_memo_only_order_gives_valid_decision(fake_mode):
    decision = llm.decide(order(memo="19/10 LV: levering uitgesteld naar wk 47."), TODAY, CONTEXT)
    assert isinstance(decision, Decision)
    assert decision.action == "none"
    assert decision.reason == llm.MEMO_ONLY_REASON


def test_fake_mode_is_deterministic(fake_mode):
    o = order(flags=[OVERDUE], memo="x")
    assert llm.decide(o, TODAY, CONTEXT) == llm.decide(o, TODAY, CONTEXT)


def test_po_number_matches_input_order(fake_mode):
    assert llm.decide(order("PO26-0339", flags=[OVERDUE]), TODAY, CONTEXT).po_number == "PO26-0339"


# --- mode switch ---

def test_unset_mode_means_fake(monkeypatch):
    monkeypatch.delenv("LLM_MODE", raising=False)
    assert llm.get_mode() == "fake"


def test_empty_mode_means_fake(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "")
    assert llm.get_mode() == "fake"


def test_unknown_mode_raises_clear_error(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "reel")
    with pytest.raises(ValueError, match="LLM_MODE"):
        llm.decide(order(), TODAY, CONTEXT)


# --- real mode, with the model call mocked (no network) ---

def test_junk_twice_falls_back_to_escalate(real_mode, monkeypatch):
    calls = []

    def junk(o, today, context, error=None):
        calls.append(o)
        return {"action": "delete_everything"}

    monkeypatch.setattr(llm, "_call_llm", junk)
    decision = llm.decide(order("PO7"), TODAY, CONTEXT)
    assert len(calls) == 2  # one try and one retry
    assert decision.action == "escalate"
    assert decision.reason == llm.INVALID_OUTPUT_REASON
    assert decision.po_number == "PO7"


def test_retry_succeeds_after_one_bad_answer(real_mode, monkeypatch):
    answers = iter([{}, {"action": "chase_supplier", "reason": "Memo says delivery is late."}])
    monkeypatch.setattr(llm, "_call_llm", lambda o, today, context, error=None: next(answers))
    assert llm.decide(order("PO8"), TODAY, CONTEXT).action == "chase_supplier"


def test_po_number_from_llm_is_ignored(real_mode, monkeypatch):
    monkeypatch.setattr(llm, "_call_llm", lambda o, today, context, error=None:
                        {"po_number": "PO-FAKE", "action": "none", "reason": "On time."})
    assert llm.decide(order("PO9"), TODAY, CONTEXT).po_number == "PO9"


def test_too_long_reason_is_retried_with_the_reason_why(real_mode, monkeypatch):
    errors_seen = []
    answers = iter([
        {"action": "none", "reason": words(MAX_REASON_WORDS + 1)},
        {"action": "none", "reason": "Delivered Friday, not booked in."},
    ])

    def call(o, today, context, error=None):
        errors_seen.append(error)
        return next(answers)

    monkeypatch.setattr(llm, "_call_llm", call)
    decision = llm.decide(order("PO10"), TODAY, CONTEXT)
    assert errors_seen[0] is None  # first call has no error
    assert "21 words" in errors_seen[1] and "max is 20" in errors_seen[1]
    assert decision.reason == "Delivered Friday, not booked in."


def test_too_long_reason_twice_falls_back_and_is_not_truncated(real_mode, monkeypatch):
    monkeypatch.setattr(llm, "_call_llm", lambda o, today, context, error=None:
                        {"action": "none", "reason": words(MAX_REASON_WORDS + 5)})
    decision = llm.decide(order("PO11"), TODAY, CONTEXT)
    assert decision.action == "escalate"
    assert decision.reason == llm.INVALID_OUTPUT_REASON


# --- the Decision model ---

def test_reason_of_exactly_max_words_is_valid():
    Decision(po_number="PO1", action="none", reason=words(MAX_REASON_WORDS))


def test_reason_over_max_words_is_invalid():
    with pytest.raises(ValueError, match="reason has 21 words, max is 20"):
        Decision(po_number="PO1", action="none", reason=words(MAX_REASON_WORDS + 1))


# --- the message the model sees ---

def test_message_contains_today_and_context():
    message = llm.build_user_message(order(memo="wk 47"), TODAY, CONTEXT)
    assert "2026-11-02" in message
    assert "Standard" in message and "2027-01-01" in message
    assert "wk 47" in message
    assert "rejected" not in message


def test_message_for_stock_order_says_there_is_no_customer_date():
    stock_context = {"contact_policy": "Standard", "customer_delivery_date": NO_CUSTOMER_DATE}
    assert "none (stock order)" in llm.build_user_message(order(), TODAY, stock_context)


def test_retry_message_contains_the_error():
    message = llm.build_user_message(order(), TODAY, CONTEXT, error="reason has 27 words, max is 20")
    assert "reason has 27 words, max is 20" in message


# --- model name ---

def test_model_name_default_and_override(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "")
    assert llm.model_name() == llm.DEFAULT_MODEL
    monkeypatch.setenv("ANTHROPIC_MODEL", "some-other-model")
    assert llm.model_name() == "some-other-model"
