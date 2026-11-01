import pytest

import llm
from decision import Decision
from expediting import DUE_SOON, OVERDUE


def order(po_number: str = "PO1", flags: list[str] | None = None, memo: str = "") -> dict:
    return {"po_number": po_number, "flags": flags or [], "memo": memo}


@pytest.fixture
def fake_mode(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "fake")


@pytest.fixture
def real_mode(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "real")


def test_overdue_order_gives_escalate(fake_mode):
    assert llm.decide(order(flags=[OVERDUE])).action == "escalate"


def test_due_soon_order_gives_chase_supplier(fake_mode):
    assert llm.decide(order(flags=[DUE_SOON])).action == "chase_supplier"


def test_memo_only_order_gives_valid_decision(fake_mode):
    decision = llm.decide(order(memo="19/10 LV: levering uitgesteld naar wk 47."))
    assert isinstance(decision, Decision)
    assert decision.action == "none"
    assert decision.reason == llm.MEMO_ONLY_REASON


def test_fake_mode_is_deterministic(fake_mode):
    o = order(flags=[OVERDUE], memo="x")
    assert llm.decide(o) == llm.decide(o)


def test_po_number_matches_input_order(fake_mode):
    assert llm.decide(order("PO26-0339", flags=[OVERDUE])).po_number == "PO26-0339"


def test_unset_mode_means_fake(monkeypatch):
    monkeypatch.delenv("LLM_MODE", raising=False)
    assert llm.get_mode() == "fake"


def test_empty_mode_means_fake(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "")
    assert llm.get_mode() == "fake"


def test_unknown_mode_raises_clear_error(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "reel")
    with pytest.raises(ValueError, match="LLM_MODE"):
        llm.decide(order())


def test_junk_twice_falls_back_to_escalate(real_mode, monkeypatch):
    calls = []

    def junk(o):
        calls.append(o)
        return {"action": "delete_everything"}

    monkeypatch.setattr(llm, "_call_llm", junk)
    decision = llm.decide(order("PO7"))
    assert len(calls) == 2  # one try and one retry
    assert decision.action == "escalate"
    assert decision.reason == llm.INVALID_OUTPUT_REASON
    assert decision.po_number == "PO7"


def test_retry_succeeds_after_one_bad_answer(real_mode, monkeypatch):
    answers = iter([{}, {"action": "chase_supplier", "reason": "Memo says delivery is late."}])
    monkeypatch.setattr(llm, "_call_llm", lambda o: next(answers))
    assert llm.decide(order("PO8")).action == "chase_supplier"


def test_po_number_from_llm_is_ignored(real_mode, monkeypatch):
    monkeypatch.setattr(llm, "_call_llm",
                        lambda o: {"po_number": "PO-FAKE", "action": "none", "reason": "On time."})
    assert llm.decide(order("PO9")).po_number == "PO9"


def test_model_name_default_and_override(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "")
    assert llm.model_name() == llm.DEFAULT_MODEL
    monkeypatch.setenv("ANTHROPIC_MODEL", "some-other-model")
    assert llm.model_name() == "some-other-model"
