"""Extra facts the LLM gets next to the order: the supplier's contact policy and the customer date.

Plain lookups, no LLM. Build them once per run, then ask for each order.
"""

NO_CUSTOMER_DATE = "none (stock order)"


def build_lookups(suppliers: list[dict], projects: list[dict]) -> tuple[dict, dict]:
    """Returns (contact_policy by supplier_id, customer_delivery_date by project)."""
    contact_policies = {s["supplier_id"]: s["contact_policy"] for s in suppliers}
    delivery_dates = {p["project"]: p.get("customer_delivery_date") for p in projects}
    return contact_policies, delivery_dates


def context_for(order: dict, contact_policies: dict, delivery_dates: dict) -> dict:
    """The context for one order. An unknown supplier or project raises KeyError on purpose."""
    return {
        "contact_policy": contact_policies[order["supplier_id"]],
        "customer_delivery_date": delivery_dates[order["project"]] or NO_CUSTOMER_DATE,
    }
