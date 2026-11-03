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
from expediting import effective_delivery_date
from keelson_client import KeelsonClient
from llm import decide, get_mode
from triage import split_orders

DATA_PATH = Path(__file__).parent / "data" / "decisions.json"


def to_record(order: dict, action: str, reason: str, source: str) -> dict:
    """One line of the file. source is "llm" (decide() answered) or "triage" (code said none)."""
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
    }


def build_records(for_llm: list[dict], no_action: list[dict], decide_one) -> list[dict]:
    """decide_one(order) -> Decision. Every order of both lists ends up in the result once."""
    records = []
    for order in for_llm:
        decision = decide_one(order)
        records.append(to_record(order, decision.action, decision.reason, "llm"))
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

    print(f"LLM mode: {get_mode()}. {len(for_llm)} orders go to decide(), {len(no_action)} are settled by the triage.")
    records = build_records(for_llm, no_action, decide_one)
    write_decisions(records, today, get_mode())
    print(f"Wrote {len(records)} orders to {DATA_PATH}")


if __name__ == "__main__":
    main()
