"""Build data/decisions.json: one line for every open order, read later by the page (app.py).

Runs the triage, asks decide() for each order that goes to the LLM (so it respects LLM_MODE),
and adds the orders the triage already settled with action "none".

Usage (fake mode, no network, no key):
    LLM_MODE=fake python build_decisions.py
"""
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

from context import build_lookups, context_for
from erp_proposals import build_proposals
from expediting import effective_delivery_date
from keelson_client import KeelsonClient
from llm import decide, get_mode
from memo_facts import extract_facts
from triage import split_orders

DATA_PATH = Path(__file__).parent / "data" / "decisions.json"


def to_record(order: dict, action: str, reason: str, source: str, erp_proposals: list[dict] | None = None) -> dict:
    """One line of the file. source is "llm" (decide() answered) or "triage" (code said none).
    erp_proposals are the ERP updates a buyer could enter by hand (see erp_proposals.py)."""
    return {
        "po_number": order["po_number"],
        "supplier_name": order["supplier_name"],
        "project": order["project"],
        "delivery_date": effective_delivery_date(order).isoformat(),
        "flags": order["flags"],
        "memo": order["memo"],
        "action": action,
        "reason": reason,
        "source": source,
        "erp_proposals": erp_proposals or [],
    }


def build_records(for_llm: list[dict], no_action: list[dict], decide_one, proposals_for=lambda order: []) -> list[dict]:
    """decide_one(order) -> Decision, proposals_for(order) -> list of ERP proposals.
    Every order of both lists ends up in the result once."""
    records = []
    for order in for_llm:
        decision = decide_one(order)
        records.append(to_record(order, decision.action, decision.reason, "llm", proposals_for(order)))
    for order in no_action:
        records.append(to_record(order, order["action"], order["reason"], "triage"))
    return sorted(records, key=lambda r: r["po_number"])


def write_decisions(records: list[dict], business_date: date, llm_mode: str,
                    path: Path = DATA_PATH, now: datetime | None = None) -> None:
    """Write the file in one go: the page never sees a half-written file."""
    now = now or datetime.now(timezone.utc)
    payload = {
        "built_at": now.isoformat(timespec="seconds"),
        "business_date": business_date.isoformat(),
        "llm_mode": llm_mode,
        "orders": records,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temp_path, path)


def main() -> None:
    client = KeelsonClient()
    today = date.fromisoformat(client.business_date())
    for_llm, no_action = split_orders(client.get_open_purchase_orders(), today)
    contact_policies, delivery_dates = build_lookups(client.get_suppliers(), client.get_projects())  # once per run

    def decide_one(order: dict):
        return decide(order, today, context_for(order, contact_policies, delivery_dates))

    unreadable = []  # memos whose facts the LLM could not give in a valid form

    def proposals_for(order: dict) -> list[dict]:
        if not order["memo"].strip():
            return []
        facts = extract_facts(order, today)
        if facts is None:
            unreadable.append(order["po_number"])
            return []
        return build_proposals(order, facts, today)

    print(f"LLM mode: {get_mode()}. {len(for_llm)} orders go to decide(), {len(no_action)} are settled by the triage.")
    records = build_records(for_llm, no_action, decide_one, proposals_for)
    write_decisions(records, today, get_mode())
    with_proposals = [r for r in records if r["erp_proposals"]]
    print(f"Wrote {len(records)} orders to {DATA_PATH}")
    print(f"ERP proposals: {sum(len(r['erp_proposals']) for r in with_proposals)} for {len(with_proposals)} orders")
    if unreadable:
        print(f"Memo facts could not be read for: {', '.join(unreadable)} (no ERP proposal for these)")


if __name__ == "__main__":
    main()
