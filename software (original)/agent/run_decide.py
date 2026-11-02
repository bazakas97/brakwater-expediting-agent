"""Run the triage, then decide() on some of the orders that go to the LLM.

Usage (fake mode, no network, no key):
    LLM_MODE=fake python run_decide.py                      first 5 orders
    LLM_MODE=fake python run_decide.py --limit 10           first 10 orders
    LLM_MODE=fake python run_decide.py --po PO26-0334 PO26-0351
"""
import argparse
from datetime import date

from context import build_lookups, context_for
from keelson_client import KeelsonClient
from llm import decide, get_mode
from triage import split_orders

DEFAULT_LIMIT = 5


def positive_int(text: str) -> int:
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("must be 1 or more")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--po", nargs="+", metavar="PO", help="decide only these PO numbers")
    parser.add_argument("--limit", type=positive_int, help=f"max orders to decide (default {DEFAULT_LIMIT} without --po)")
    return parser.parse_args()


def choose_orders(for_llm: list[dict], no_action: list[dict], po_numbers: list[str] | None,
                  limit: int | None) -> list[dict]:
    if not po_numbers:
        return for_llm[:limit or DEFAULT_LIMIT]
    by_po = {o["po_number"]: o for o in for_llm}
    skipped_by_triage = {o["po_number"] for o in no_action}
    chosen = []
    for po in po_numbers:
        if po in by_po:
            chosen.append(by_po[po])
        elif po in skipped_by_triage:
            print(f"{po}: triage gave 'none', no LLM needed")
        else:
            print(f"{po}: not found in open orders")
    return chosen[:limit]


def main() -> None:
    args = parse_args()
    client = KeelsonClient()
    today = date.fromisoformat(client.business_date())
    for_llm, no_action = split_orders(client.get_open_purchase_orders(), today)
    contact_policies, delivery_dates = build_lookups(client.get_suppliers(), client.get_projects())  # once per run

    orders = choose_orders(for_llm, no_action, args.po, args.limit)
    print(f"LLM mode: {get_mode()}. Deciding {len(orders)} of {len(for_llm)} orders.\n")
    for order in orders:
        d = decide(order, today, context_for(order, contact_policies, delivery_dates))
        print(f"{d.po_number}  {d.action:<15} {d.reason}")


if __name__ == "__main__":
    main()
