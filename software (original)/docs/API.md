# Keelson ERP API (sandbox)

Read only REST API for purchase orders, suppliers, employees and projects of Brakwater Boats B.V.

**Base URL:** `http://localhost:8000` (from the agent container: `http://keelson-api:8000`)
**Format:** JSON
**Authentication:** none in the sandbox

The OpenAPI specification is available at `/openapi.json`.

## Business date

The sandbox uses today as business date. All dates in the data, including dates mentioned in memo texts, are relative to it. `GET /health` returns the business date the API uses.

## Endpoints

### `GET /health`

```json
{ "status": "ok", "business_date": "2026-10-12" }
```

### `GET /api/v1/purchase-orders`

List of purchase orders, sorted by `po_number`, paginated.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `open_only` | boolean | `false` | Only orders with status `Open` or `Partially received` |
| `status` | string, repeatable | | Filter on one or more statuses, for example `?status=Open&status=Closed` |
| `supplier_id` | string | | Filter on supplier, for example `S05` |
| `project` | string | | Filter on project, for example `BB-2604` or `STOCK` |
| `page` | integer | `1` | Page number, starting at 1 |
| `page_size` | integer | `50` | Orders per page, maximum 100 |

Response:

```json
{
  "items": [ { "...purchase order..." } ],
  "page": 1,
  "page_size": 50,
  "total": 60
}
```

`total` is the total number of orders matching the filters, over all pages.

### `GET /api/v1/purchase-orders/{po_number}`

A single purchase order. Returns `404` if it does not exist.

```json
{
  "po_number": "PO26-0336",
  "supplier_id": "S01",
  "supplier_name": "Aluprofiel Zeeland B.V.",
  "project": "BB-2604",
  "buyer": "LV",
  "description": "Aluminium plate 5083 H111, 6 mm",
  "amount": 8987.88,
  "currency": "EUR",
  "order_date": "2026-08-24",
  "requested_delivery_date": "2026-10-02",
  "confirmed_delivery_date": "2026-10-02",
  "order_confirmation_received": true,
  "status": "Open",
  "memo": "",
  "last_modified": "2026-08-27"
}
```

| Field | Description |
|---|---|
| `buyer` | Initials of the responsible buyer, see `/api/v1/employees` |
| `requested_delivery_date` | Delivery date Brakwater asked for on the order |
| `confirmed_delivery_date` | Delivery date from the supplier's order confirmation, `null` if none received |
| `order_confirmation_received` | Whether an order confirmation is registered in the ERP |
| `status` | `Open`, `Partially received`, `Received`, `Closed` or `Cancelled` |
| `memo` | Free text notes by buyers and project managers, newest line last |

### `GET /api/v1/suppliers` and `GET /api/v1/suppliers/{supplier_id}`

```json
{
  "supplier_id": "S02",
  "name": "Marinetec Hydraulik GmbH",
  "country": "DE",
  "language": "German",
  "contact_person": "Petra Lange",
  "email": "vertrieb@marinetec-hydraulik.example",
  "phone": "+49 40 000 202",
  "category": "Steering and hydraulics",
  "contact_policy": "Standard"
}
```

`contact_policy` is `Standard` or `Via project manager`.

### `GET /api/v1/employees`

Buyers and project managers, with `employee_id`, `name`, `initials`, `role` and `email`.

### `GET /api/v1/projects`

Projects with `project`, `description`, `project_manager_id` and `customer_delivery_date`.
