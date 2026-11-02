"""Run the triage, then decide() on the first 5 orders that go to the LLM.

Usage (fake mode, no network, no key):
    LLM_MODE=fake python run_decide.py
"""
from datetime import date

from context import build_lookups, context_for
from keelson_client import KeelsonClient
from llm import decide, get_mode
from triage import split_orders

HOW_MANY = 5


def main() -> None:
    client = KeelsonClient()
    today = date.fromisoformat(client.business_date())
    for_llm, _ = split_orders(client.get_open_purchase_orders(), today)
    contact_policies, delivery_dates = build_lookups(client.get_suppliers(), client.get_projects())  # once per run

    print(f"LLM mode: {get_mode()}. Deciding {HOW_MANY} of {len(for_llm)} orders.\n")
    for order in for_llm[:HOW_MANY]:
        d = decide(order, today, context_for(order, contact_policies, delivery_dates))
        print(f"{d.po_number}  {d.action:<15} {d.reason}")


if __name__ == "__main__":
    main()
