import pytest

from context import NO_CUSTOMER_DATE, build_lookups, context_for

SUPPLIERS = [
    {"supplier_id": "S01", "contact_policy": "Standard"},
    {"supplier_id": "S07", "contact_policy": "Via project manager"},
]
PROJECTS = [
    {"project": "BB-2604", "customer_delivery_date": "2027-01-01"},
    {"project": "STOCK", "customer_delivery_date": None},
]


def lookups():
    return build_lookups(SUPPLIERS, PROJECTS)


def test_context_has_contact_policy_and_customer_date():
    order = {"supplier_id": "S07", "project": "BB-2604"}
    assert context_for(order, *lookups()) == {
        "contact_policy": "Via project manager",
        "customer_delivery_date": "2027-01-01",
    }


def test_stock_order_gets_none_stock_order_instead_of_a_date():
    order = {"supplier_id": "S01", "project": "STOCK"}
    assert context_for(order, *lookups())["customer_delivery_date"] == NO_CUSTOMER_DATE
    assert NO_CUSTOMER_DATE == "none (stock order)"


def test_missing_date_key_is_treated_like_an_empty_date():
    _, dates = build_lookups(SUPPLIERS, [{"project": "STOCK"}])
    assert dates["STOCK"] is None


def test_unknown_supplier_raises_instead_of_guessing():
    with pytest.raises(KeyError):
        context_for({"supplier_id": "S99", "project": "BB-2604"}, *lookups())


def test_unknown_project_raises_instead_of_guessing():
    with pytest.raises(KeyError):
        context_for({"supplier_id": "S01", "project": "BB-9999"}, *lookups())
