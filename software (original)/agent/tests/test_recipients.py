import pytest

from recipients import (ESCALATION_TO_PM, INTERNAL_LANGUAGE, PM_CONTACTS_SUPPLIER, REMINDER_TO_SUPPLIER, find_recipient,
                        sender_name)

SUPPLIERS = {
    "S02": {"name": "Marinetec Hydraulik GmbH", "contact_person": "Petra Lange", "email": "vertrieb@marinetec.example",
            "language": "German", "contact_policy": "Standard"},
    "S07": {"name": "Polarnav Electronics ApS", "contact_person": "Mette Friis", "email": "mette@polarnav.example",
            "language": "English", "contact_policy": "Via project manager"},
}
PROJECTS = {"BB-2604": {"project_manager_id": "E04"}, "STOCK": {"project_manager_id": None}}
EMPLOYEES = {
    "E01": {"name": "Mark Dekker", "email": "mark@brakwater.example", "role": "Head of Purchasing and Logistics", "initials": "MD"},
    "E02": {"name": "Linda Verhoeven", "email": "linda@brakwater.example", "role": "Buyer", "initials": "LV"},
    "E04": {"name": "Sanne de Wit", "email": "sanne@brakwater.example", "role": "Project manager", "initials": "SW"},
}


def order(supplier_id: str = "S02", project: str = "BB-2604") -> dict:
    return {"supplier_id": supplier_id, "project": project, "buyer": "LV"}


def recipient(action: str, **kw) -> dict | None:
    return find_recipient(order(**kw), action, SUPPLIERS, PROJECTS, EMPLOYEES)


def test_chase_goes_to_the_supplier_contact_in_the_suppliers_language():
    r = recipient("chase_supplier")
    assert (r["kind"], r["purpose"]) == ("supplier", REMINDER_TO_SUPPLIER)
    assert (r["name"], r["email"], r["language"]) == ("Petra Lange", "vertrieb@marinetec.example", "German")


def test_escalate_goes_to_the_project_manager_in_the_internal_language():
    r = recipient("escalate")
    assert (r["kind"], r["purpose"]) == ("project_manager", ESCALATION_TO_PM)
    assert (r["name"], r["email"], r["language"]) == ("Sanne de Wit", "sanne@brakwater.example", INTERNAL_LANGUAGE)


def test_a_via_project_manager_supplier_is_never_written_to_directly():
    r = recipient("chase_supplier", supplier_id="S07")
    assert r["kind"] == "project_manager"
    assert r["email"] == "sanne@brakwater.example"
    assert r["purpose"] == PM_CONTACTS_SUPPLIER
    assert "never email this supplier directly" in r["note"]


def test_escalating_an_order_of_a_via_project_manager_supplier_goes_to_the_project_manager():
    r = recipient("escalate", supplier_id="S07")
    assert (r["kind"], r["purpose"], r["email"]) == ("project_manager", ESCALATION_TO_PM, "sanne@brakwater.example")


def test_the_address_of_a_via_project_manager_supplier_is_never_a_recipient():
    for action in ["chase_supplier", "escalate"]:
        for project in ["BB-2604", "STOCK"]:
            assert recipient(action, supplier_id="S07", project=project)["email"] != SUPPLIERS["S07"]["email"]


def test_a_project_without_project_manager_goes_to_the_head_of_purchasing():
    r = recipient("escalate", project="STOCK")
    assert (r["kind"], r["name"]) == ("head_of_purchasing", "Mark Dekker")
    assert "no project manager" in r["note"]


def test_a_via_pm_supplier_on_a_stock_order_goes_to_the_head_of_purchasing_with_both_notes():
    r = recipient("chase_supplier", supplier_id="S07", project="STOCK")
    assert r["kind"] == "head_of_purchasing"
    assert "never email this supplier directly" in r["note"] and "no project manager" in r["note"]


@pytest.mark.parametrize("action", ["none", "wait", "book_in"])
def test_other_actions_need_no_email(action):
    assert recipient(action) is None


def test_unknown_supplier_or_project_fails_loudly():
    with pytest.raises(KeyError):
        recipient("chase_supplier", supplier_id="S99")
    with pytest.raises(KeyError):
        recipient("escalate", project="BB-9999")


def test_the_buyer_of_the_order_signs():
    assert sender_name(order(), {e["initials"]: e for e in EMPLOYEES.values()}) == "Linda Verhoeven"
