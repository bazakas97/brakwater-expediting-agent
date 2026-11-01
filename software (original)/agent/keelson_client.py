"""Small client for the Keelson ERP API."""
import os

import httpx

DEFAULT_BASE_URL = os.getenv("KEELSON_API_URL", "http://localhost:8000")


class KeelsonClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, http: httpx.Client | None = None):
        self.http = http or httpx.Client(base_url=base_url, timeout=10)

    def _get(self, path: str, **params) -> dict:
        response = self.http.get(path, params=params)
        response.raise_for_status()
        return response.json()

    def get_open_purchase_orders(self, page_size: int = 50) -> list[dict]:
        """All open purchase orders (status Open or Partially received), all pages."""
        orders: list[dict] = []
        page = 1
        while True:
            data = self._get("/api/v1/purchase-orders", open_only=True, page=page, page_size=page_size)
            orders.extend(data["items"])
            if page * page_size >= data["total"]:
                break
            page += 1
        return orders

    def get_purchase_order(self, po_number: str) -> dict:
        return self._get(f"/api/v1/purchase-orders/{po_number}")

    def get_suppliers(self) -> list[dict]:
        return self._get("/api/v1/suppliers")["items"]

    def get_employees(self) -> list[dict]:
        return self._get("/api/v1/employees")["items"]

    def get_projects(self) -> list[dict]:
        return self._get("/api/v1/projects")["items"]

    def business_date(self) -> str:
        return self._get("/health")["business_date"]
