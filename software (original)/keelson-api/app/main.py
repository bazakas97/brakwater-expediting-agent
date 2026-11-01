"""Keelson ERP API, sandbox edition.

Read only API for purchase orders, suppliers, employees and projects of
Brakwater Boats B.V. See docs/API.md for the full description.
"""
from fastapi import FastAPI, HTTPException, Query

from . import store
from .dates import business_today

OPEN_STATUSES = {"Open", "Partially received"}

app = FastAPI(
    title="Keelson ERP API (sandbox)",
    version="1.0",
    docs_url=None,
    redoc_url=None,
)


@app.get("/health")
def health():
    return {"status": "ok", "business_date": business_today().isoformat()}


@app.get("/api/v1/purchase-orders")
def list_purchase_orders(
    open_only: bool = Query(False, description="Only orders with status Open or Partially received"),
    status: list[str] | None = Query(None, description="Filter on one or more statuses"),
    supplier_id: str | None = None,
    project: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    orders = store.purchase_orders()
    if open_only:
        orders = [o for o in orders if o["status"] in OPEN_STATUSES]
    if status:
        orders = [o for o in orders if o["status"] in status]
    if supplier_id:
        orders = [o for o in orders if o["supplier_id"] == supplier_id]
    if project:
        orders = [o for o in orders if o["project"] == project]
    orders.sort(key=lambda o: o["po_number"])

    start = (page - 1) * page_size
    items = orders[start:start + page_size]
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": len(orders),
    }


@app.get("/api/v1/purchase-orders/{po_number}")
def get_purchase_order(po_number: str):
    for order in store.purchase_orders():
        if order["po_number"] == po_number:
            return order
    raise HTTPException(status_code=404, detail=f"Purchase order {po_number} not found")


@app.get("/api/v1/suppliers")
def list_suppliers():
    return {"items": store.suppliers()}


@app.get("/api/v1/suppliers/{supplier_id}")
def get_supplier(supplier_id: str):
    for supplier in store.suppliers():
        if supplier["supplier_id"] == supplier_id:
            return supplier
    raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")


@app.get("/api/v1/employees")
def list_employees():
    return {"items": store.employees()}


@app.get("/api/v1/projects")
def list_projects():
    return {"items": store.projects()}
