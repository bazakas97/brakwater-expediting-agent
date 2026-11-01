"""Run the triage on the real open orders from the API and print the two groups.

Usage:
    python run_triage.py
"""
from datetime import date

from keelson_client import KeelsonClient
from triage import split_orders


def main() -> None:
    client = KeelsonClient()
    today = date.fromisoformat(client.business_date())
    orders = client.get_open_purchase_orders()
    for_llm, no_action = split_orders(orders, today)

    print(f"Business date: {today}. Open orders: {len(orders)}\n")
    print(f"For the LLM: {len(for_llm)}")
    print("  " + ", ".join(o["po_number"] for o in for_llm))
    print(f"\nAction 'none': {len(no_action)}")
    print("  " + ", ".join(o["po_number"] for o in no_action))


if __name__ == "__main__":
    main()
