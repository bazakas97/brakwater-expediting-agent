from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_single_purchase_order():
    response = client.get("/api/v1/purchase-orders/PO26-0301")
    assert response.status_code == 200
    assert response.json()["supplier_id"] == "S02"


def test_unknown_purchase_order_returns_404():
    assert client.get("/api/v1/purchase-orders/PO99-0000").status_code == 404


def test_open_only_returns_only_open_statuses():
    items = client.get("/api/v1/purchase-orders", params={"open_only": True}).json()["items"]
    assert items
    assert {o["status"] for o in items} <= {"Open", "Partially received"}


def test_filter_on_supplier():
    items = client.get("/api/v1/purchase-orders", params={"supplier_id": "S05"}).json()["items"]
    assert items
    assert all(o["supplier_id"] == "S05" for o in items)


def test_second_page_returns_other_orders():
    first = client.get("/api/v1/purchase-orders", params={"page": 1, "page_size": 10}).json()["items"]
    second = client.get("/api/v1/purchase-orders", params={"page": 2, "page_size": 10}).json()["items"]
    assert len(second) == 10
    assert {o["po_number"] for o in first}.isdisjoint({o["po_number"] for o in second})


def test_suppliers_have_language():
    items = client.get("/api/v1/suppliers").json()["items"]
    assert len(items) > 0
    assert all("language" in s for s in items)
