import json
from datetime import date, datetime, timezone

from build_decisions import build_records, to_record, write_decisions
from decision import Decision


def order(po: str, confirmed: str | None = None, **extra) -> dict:
    return {"po_number": po, "supplier_name": "Acme", "project": "BB-2604",
            "requested_delivery_date": "2026-11-10", "confirmed_delivery_date": confirmed,
            "flags": ["DUE_WITHIN_14_DAYS"], "memo": "a memo", **extra}


def triage_none(po: str) -> dict:
    return order(po, flags=[], memo="", action="none", reason="On time, confirmed, no notes")


def decide_escalate(o: dict) -> Decision:
    return Decision(po_number=o["po_number"], action="escalate", reason="because")


def test_record_has_all_the_fields_the_page_needs():
    record = to_record(order("PO1"), "chase_supplier", "routine", "llm")
    assert record == {
        "po_number": "PO1", "supplier_name": "Acme", "project": "BB-2604", "delivery_date": "2026-11-10",
        "flags": ["DUE_WITHIN_14_DAYS"], "memo": "a memo", "action": "chase_supplier", "reason": "routine",
        "source": "llm",
    }


def test_record_uses_the_confirmed_date_when_there_is_one():
    assert to_record(order("PO1", confirmed="2026-12-24"), "none", "r", "llm")["delivery_date"] == "2026-12-24"


def test_every_order_is_in_the_result_exactly_once_with_the_right_source():
    records = build_records([order("PO2"), order("PO1")], [triage_none("PO3")], decide_escalate)
    assert [r["po_number"] for r in records] == ["PO1", "PO2", "PO3"]  # sorted by PO
    assert {r["po_number"]: r["source"] for r in records} == {"PO1": "llm", "PO2": "llm", "PO3": "triage"}


def test_triage_orders_keep_the_action_and_reason_from_the_triage():
    record = build_records([], [triage_none("PO3")], decide_escalate)[0]
    assert (record["action"], record["reason"]) == ("none", "On time, confirmed, no notes")


def test_llm_orders_get_the_action_from_decide():
    assert build_records([order("PO1")], [], decide_escalate)[0]["action"] == "escalate"


def test_write_decisions_writes_the_file_with_build_time_date_and_mode(tmp_path):
    path = tmp_path / "data" / "decisions.json"
    now = datetime(2026, 11, 3, 12, 5, 30, tzinfo=timezone.utc)
    write_decisions([to_record(order("PO1"), "none", "r", "llm")], date(2026, 11, 3), "fake", path, now)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["built_at"] == "2026-11-03T12:05:30+00:00"
    assert data["business_date"] == "2026-11-03"
    assert data["llm_mode"] == "fake"
    assert len(data["orders"]) == 1


def test_write_decisions_replaces_the_old_file_and_leaves_no_temp_file(tmp_path):
    path = tmp_path / "decisions.json"
    write_decisions([], date(2026, 11, 3), "fake", path)
    write_decisions([to_record(order("PO1"), "none", "r", "llm")], date(2026, 11, 4), "real", path)
    assert json.loads(path.read_text(encoding="utf-8"))["llm_mode"] == "real"
    assert [p.name for p in tmp_path.iterdir()] == ["decisions.json"]
