"""Open orders export.

Built last year by Brakwater's IT contractor. Linda runs it every Monday morning:
it lists all open purchase orders that need attention and writes them to a CSV
file, which she then works through by hand.

Usage:
    python export_open_orders.py
"""
import csv
from datetime import date
from pathlib import Path

from expediting import flag_order
from keelson_client import KeelsonClient

OUTPUT_DIR = Path(__file__).parent / "output"
COLUMNS = ["po_number", "supplier_name", "project", "buyer", "flags", "requested_delivery_date",
           "confirmed_delivery_date", "memo"]


def orders_needing_attention(client: KeelsonClient, today: date) -> list[dict]:
    result = []
    for po in client.get_open_purchase_orders():
        flags = flag_order(po, today)
        if flags:
            result.append({**po, "flags": ", ".join(flags)})
    return sorted(result, key=lambda o: (o["supplier_name"], o["po_number"]))


def main() -> None:
    client = KeelsonClient()
    today = date.fromisoformat(client.business_date())
    rows = orders_needing_attention(client, today)

    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"open_orders_{today.isoformat()}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    for row in rows:
        print(f"{row['po_number']}  {row['supplier_name']:<36} {row['flags']}")
    print(f"\n{len(rows)} orders need attention. Written to {path}")


if __name__ == "__main__":
    main()
