from datetime import date

import pytest

import email_drafts
from email_drafts import MAX_BODY_WORDS, Draft, build_draft_message, check_draft, draft_facts, write_draft
from recipients import ESCALATION_TO_PM, PM_CONTACTS_SUPPLIER, REMINDER_TO_SUPPLIER

TODAY = date(2026, 11, 3)
ORDER = {"po_number": "PO26-0334", "description": "Wheelhouse windows set", "supplier_name": "Seaglass Windows Ltd",
         "project": "BB-2604", "requested_delivery_date": "2026-11-11", "confirmed_delivery_date": "2026-11-11",
         "order_confirmation_received": True, "flags": ["DUE_WITHIN_14_DAYS"], "memo": "8% surcharge asked"}


def recipient(purpose: str = REMINDER_TO_SUPPLIER, language: str = "English", kind: str = "supplier") -> dict:
    return {"kind": kind, "purpose": purpose, "name": "Tom Reeves", "email": "tom@example", "language": language, "note": None}


def facts(rec: dict | None = None) -> dict:
    return draft_facts(ORDER, rec or recipient(), "Price change, needs a decision", "2027-01-02")


@pytest.fixture
def fake_mode(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "fake")


@pytest.fixture
def real_mode(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "real")


# --- the facts: nothing internal goes to a supplier ---

def test_a_supplier_gets_no_project_customer_or_internal_reason():
    f = facts(recipient(kind="supplier"))
    assert "project" not in f and "customer_delivery_date" not in f and "why_it_needs_attention" not in f
    assert f["po_number"] == "PO26-0334"


def test_a_colleague_gets_the_project_the_customer_date_and_the_reason():
    f = facts(recipient(ESCALATION_TO_PM, "Dutch", "project_manager"))
    assert (f["project"], f["customer_delivery_date"]) == ("BB-2604", "2027-01-02")
    assert f["why_it_needs_attention"] == "Price change, needs a decision"


def test_the_amount_is_never_part_of_the_facts():
    assert "amount" not in facts() and "amount" not in facts(recipient(ESCALATION_TO_PM, "Dutch", "project_manager"))


# --- the Draft model and the code checks ---

def test_a_body_of_exactly_the_maximum_is_valid_and_one_more_word_is_not():
    Draft(subject="s", body=" ".join(["word"] * MAX_BODY_WORDS))
    with pytest.raises(ValueError, match=f"body has {MAX_BODY_WORDS + 1} words, max is {MAX_BODY_WORDS}"):
        Draft(subject="s", body=" ".join(["word"] * (MAX_BODY_WORDS + 1)))


def test_the_po_number_and_the_senders_name_are_required():
    check_draft(Draft(subject="Reminder PO26-0334", body="Dear Tom,\n\nKind regards,\nLinda Verhoeven"), "PO26-0334", "Linda Verhoeven")
    with pytest.raises(ValueError, match="PO number"):
        check_draft(Draft(subject="Reminder", body="Dear Tom, Linda Verhoeven"), "PO26-0334", "Linda Verhoeven")
    with pytest.raises(ValueError, match="sender"):
        check_draft(Draft(subject="Reminder PO26-0334", body="Dear Tom,\n\nBest wishes"), "PO26-0334", "Linda Verhoeven")


# --- fake mode: templates in the language of the recipient ---

@pytest.mark.parametrize("language, greeting", [("English", "Dear Tom Reeves"), ("Dutch", "Geachte Tom Reeves"),
                                                ("German", "Sehr geehrte(r) Tom Reeves")])
def test_fake_reminder_is_in_the_suppliers_language_with_the_po_and_the_signature(fake_mode, language, greeting):
    rec = recipient(language=language)
    draft = write_draft(ORDER, rec, "Linda Verhoeven", "r", facts(rec), TODAY)
    assert draft.body.startswith(greeting)
    assert "PO26-0334" in draft.subject and draft.body.endswith("Linda Verhoeven")
    check_draft(draft, "PO26-0334", "Linda Verhoeven")


def test_fake_escalation_is_in_dutch_and_includes_the_reason(fake_mode):
    rec = recipient(ESCALATION_TO_PM, "Dutch", "project_manager")
    draft = write_draft(ORDER, rec, "Linda Verhoeven", "Price change, needs a decision", facts(rec), TODAY)
    assert draft.subject.startswith("Escalatie") and "Price change, needs a decision" in draft.body


def test_fake_pm_contact_mail_says_the_supplier_is_not_written_to_directly(fake_mode):
    rec = recipient(PM_CONTACTS_SUPPLIER, "English", "project_manager")
    draft = write_draft(ORDER, rec, "Linda Verhoeven", "r", facts(rec), TODAY)
    assert "do not write to Seaglass Windows Ltd directly" in draft.body


def test_fake_falls_back_to_english_for_an_unknown_language(fake_mode):
    rec = recipient(language="Danish")
    assert write_draft(ORDER, rec, "Linda Verhoeven", "r", facts(rec), TODAY).subject == "Reminder PO26-0334"


def test_fake_uses_the_confirmed_date_else_the_requested_date(fake_mode):
    rec = recipient()
    order = {**ORDER, "confirmed_delivery_date": None, "requested_delivery_date": "2026-12-01"}
    assert "2026-12-01" in write_draft(order, rec, "Linda Verhoeven", "r", draft_facts(order, rec, "r", "x"), TODAY).body


# --- real mode, with the model call mocked (no network) ---

GOOD = {"subject": "Reminder PO26-0334", "body": "Dear Tom,\n\nPlease confirm PO26-0334.\n\nKind regards,\nLinda Verhoeven"}


def test_real_mode_returns_a_valid_draft(real_mode, monkeypatch):
    monkeypatch.setattr(email_drafts, "_call_draft_llm", lambda rec, sender, today, f, error=None: GOOD)
    assert write_draft(ORDER, recipient(), "Linda Verhoeven", "r", facts(), TODAY).subject == "Reminder PO26-0334"


def test_real_mode_a_draft_without_the_po_number_is_retried_with_the_reason(real_mode, monkeypatch):
    answers = iter([{"subject": "Reminder", "body": "Dear Tom, Linda Verhoeven"}, GOOD])
    errors = []

    def call(rec, sender, today, f, error=None):
        errors.append(error)
        return next(answers)

    monkeypatch.setattr(email_drafts, "_call_draft_llm", call)
    assert write_draft(ORDER, recipient(), "Linda Verhoeven", "r", facts(), TODAY) is not None
    assert errors[0] is None and "PO number" in errors[1]


def test_real_mode_invalid_twice_gives_none_after_exactly_one_retry(real_mode, monkeypatch):
    calls = []
    monkeypatch.setattr(email_drafts, "_call_draft_llm", lambda rec, sender, today, f, error=None: calls.append(error) or {})
    assert write_draft(ORDER, recipient(), "Linda Verhoeven", "r", facts(), TODAY) is None
    assert len(calls) == 2


# --- the message and the prompt ---

def test_message_has_purpose_recipient_language_sender_and_the_facts():
    message = build_draft_message(recipient(language="German"), "Linda Verhoeven", TODAY, facts())
    for part in ["reminder_to_supplier", "Tom Reeves", "German", "Linda Verhoeven", "2026-11-03", "PO26-0334"]:
        assert part in message
    assert "rejected" not in message
    assert "word count" in build_draft_message(recipient(), "L", TODAY, facts(), error="word count too high")


def test_prompt_demands_the_recipients_language_no_invented_facts_and_nothing_internal_to_suppliers():
    for part in ["recipient's language", "never invent", "never mention internal matters", "120 words",
                 "reminder_to_supplier", "escalation_to_pm", "pm_contact_supplier"]:
        assert part in email_drafts.SYSTEM_PROMPT
