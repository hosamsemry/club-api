# Club Management API Documentation

## Overview

This project is a Django REST Framework API for a social club management system.

Main business areas:

- Products and inventory
- Event reservations
- Gate tickets
- Sales and reporting
- Audit logs and dashboard summary

Base API prefix:

```text
/api/
```

Authentication:

- JWT access token: `Authorization: Bearer <access_token>`
- Obtain token: `POST /api/token/`
- Refresh token: `POST /api/token/refresh/`

Default behavior:

- Most endpoints require authentication
- Most list endpoints are paginated
- Data is tenant-scoped by the authenticated user's `club`

Role model used by the API:

- `owner`
- `manager`
- `cashier`
- `staff`

## Authentication

### Register Club and Owner

`POST /api/accounts/register/`

Creates a new club and its first owner user.

Request body:

```json
{
  "club_name": "Cairo Club",
  "email": "owner@example.com",
  "password": "secret123",
  "username": "owner"
}
```

Response:

```json
{
  "refresh": "<jwt-refresh-token>",
  "access": "<jwt-access-token>"
}
```

### Obtain JWT Token

`POST /api/token/`

Request body:

```json
{
  "email": "owner@example.com",
  "password": "secret123"
}
```

### Refresh JWT Token

`POST /api/token/refresh/`

Request body:

```json
{
  "refresh": "<jwt-refresh-token>"
}
```

## Core

### Dashboard

`GET /api/core/dashboard/`

Allowed roles:

- `owner`
- `manager`

Returns a high-level club dashboard summary.

Response shape:

```json
{
  "total_products": 24,
  "low_stock_alert_count": 3,
  "today_reservations_count": 4,
  "pending_reservations_count": 2,
  "today_ticket_sales_count": 18,
  "today_ticket_revenue": "3600.00",
  "today_checked_in_tickets_count": 11,
  "recent_activity": [
    {
      "action": "sale_created",
      "user_email": "manager@example.com",
      "created_at": "2026-03-21T10:15:00Z"
    }
  ]
}
```

### Audit Logs

`GET /api/core/audit-logs/`

Allowed roles:

- `owner`
- `manager`

Supported query params:

- `action`
- `user`
- `start_date`
- `end_date`
- `search`

Example:

```text
/api/core/audit-logs/?action=sale_created&start_date=2026-03-01&end_date=2026-03-21
```

## Inventory

### Categories

Base path:

```text
/api/inventory/categories/
```

Allowed roles:

- `owner`
- `manager`
- `cashier`

Supported methods:

- `GET`
- `POST`
- `PUT`
- `PATCH`
- `DELETE`

Fields:

- `name`
- `description`

Example request:

```json
{
  "name": "Drinks",
  "description": "Soft drinks and water"
}
```

### Products

Base path:

```text
/api/inventory/products/
```

Allowed roles:

- `owner`
- `manager`
- `cashier`

Supported query params:

- `category`
- `is_active`
- `search`

Fields:

- `name`
- `category`
- `sku`
- `cost_price`
- `selling_price`
- `stock_quantity`
- `is_active`
- `low_stock_threshold`

Example request:

```json
{
  "name": "Water",
  "category": 1,
  "sku": "WATER-1",
  "cost_price": "5.00",
  "selling_price": "10.00",
  "stock_quantity": 50,
  "is_active": true,
  "low_stock_threshold": 10
}
```

### Stock Movements

Base path:

```text
/api/inventory/stock-movements/
```

Allowed roles:

- `owner`
- `manager`
- `cashier`

Supported methods:

- `GET`
- `POST`

Update is not allowed.

Fields:

- `product`
- `movement_type`: `restock`, `sale`, `adjustment`, `refund`
- `quantity`
- `direction`: `in` or `out` for `adjustment` only
- `note`

Example restock:

```json
{
  "product": 1,
  "movement_type": "restock",
  "quantity": 20,
  "note": "Supplier delivery"
}
```

Example adjustment:

```json
{
  "product": 1,
  "movement_type": "adjustment",
  "quantity": 2,
  "direction": "out",
  "note": "Damaged items"
}
```

### Low Stock Alerts

`GET /api/inventory/low-stock-alerts/`

Allowed roles:

- `owner`
- `manager`

Supported query params:

- `is_active`
- `product`

Read-only endpoint.

## Sales

Base path:

```text
/api/sales/
```

Allowed roles:

- `owner`
- `manager`
- `cashier`

Supported methods:

- `GET`
- `POST`

### Create Sale

`POST /api/sales/`

Request body:

```json
{
  "items": [
    {
      "product_id": 1,
      "quantity": 2
    },
    {
      "product_id": 2,
      "quantity": 1,
      "unit_price": "18.00"
    }
  ],
  "note": "Front desk sale"
}
```

Notes:

- `unit_price` override is optional
- only `owner` and `manager` can override default pricing

### Refund Sale

`POST /api/sales/{id}/refund/`

Allowed roles:

- `owner`
- `manager`

Request body:

```json
{
  "note": "Customer refund"
}
```

### Daily Summary

`GET /api/sales/daily-summary/`

Optional query params:

- `date=YYYY-MM-DD`

### Daily Profit

`GET /api/sales/daily-profit/`

Allowed roles:

- `owner`
- `manager`

Optional query params:

- `date=YYYY-MM-DD`

### Top Products

`GET /api/sales/top-products/`

Allowed roles:

- `owner`
- `manager`

Optional query params:

- `date=YYYY-MM-DD`

## Events Reservations

### Occasion Types

Base path:

```text
/api/events/occasion-types/
```

Allowed roles:

- `owner`
- `manager`

Supported query params:

- `is_active`
- `search`

Delete is not allowed.

Fields:

- `name`
- `is_active`

### Reservations

Base path:

```text
/api/events/reservations/
```

Allowed roles:

- `owner`
- `manager`

Supported query params come from reservation filters plus:

- ordering
- search

Core fields:

- `occasion_type`
- `guest_name`
- `guest_phone`
- `starts_at`
- `ends_at`
- `guest_count`
- `total_amount`
- `notes`

Example create request:

```json
{
  "occasion_type": 1,
  "guest_name": "Sara Ahmed",
  "guest_phone": "01000000000",
  "starts_at": "2026-03-25T18:00:00Z",
  "ends_at": "2026-03-25T23:00:00Z",
  "guest_count": 120,
  "total_amount": "5000.00",
  "notes": "Family booking"
}
```

### Record Reservation Payment

`POST /api/events/reservations/{id}/record-payment/`

Request body:

```json
{
  "amount": "1500.00",
  "note": "Advance payment"
}
```

### Cancel Reservation

`POST /api/events/reservations/{id}/cancel/`

Request body:

```json
{
  "refund_amount": "500.00",
  "note": "Customer cancelled"
}
```

Delete is not allowed.

## Gate Tickets

### Ticket Types

Base path:

```text
/api/tickets/types/
```

Allowed roles:

- `owner`
- `manager`

Fields:

- `name`
- `price`
- `is_active`
- `display_order`

Delete is not allowed.

### Entry Days

Base path:

```text
/api/tickets/days/
```

Allowed roles:

- `owner`
- `manager`

Fields:

- `visit_date`
- `daily_capacity`
- `is_open`

Delete is not allowed.

### Ticket Sales

Base path:

```text
/api/tickets/sales/
```

Allowed roles:

- `owner`
- `manager`
- `cashier`
- `staff`

Supported methods:

- `GET`
- `POST`

Update and delete are not allowed.

Example create request:

```json
{
  "buyer_name": "Ahmed Ali",
  "buyer_phone": "01012345678",
  "visit_date": "2026-03-22",
  "notes": "Family group",
  "items": [
    {
      "ticket_type": 1,
      "quantity": 2
    },
    {
      "ticket_type": 2,
      "quantity": 1
    }
  ]
}
```

### Ticket Sales Daily Summary

`GET /api/tickets/sales/daily-summary/`

Optional query params:

- `date=YYYY-MM-DD`

### Tickets

Base path:

```text
/api/tickets/items/
```

Allowed roles:

- `owner`
- `manager`
- `cashier`
- `staff`

Read-only except for action endpoints below.

### Check In Ticket

`POST /api/tickets/items/{id}/check-in/`

Request body:

```json
{}
```

### Check In Ticket By Code

`POST /api/tickets/items/check-in-by-code/`

Request body:

```json
{
  "code": "ABCD1234EFGH"
}
```

### Void Ticket

`POST /api/tickets/items/{id}/void/`

Request body:

```json
{
  "note": "Customer request"
}
```

Create, update, and delete are not allowed on individual tickets.

## Reporting

Base path:

```text
/api/reporting/daily/
```

Allowed roles:

- `owner`
- `manager`

Read-only endpoint with action routes.

Supported query params:

- `report_date`
- `start_date`
- `end_date`

### Export CSV

`GET /api/reporting/daily/{id}/export/csv/`

Downloads the CSV export for the selected report. If no CSV exists yet, one is generated first.

### Regenerate Report

`POST /api/reporting/daily/{id}/regenerate/`

Schedules asynchronous regeneration through Celery.

Response example:

```json
{
  "detail": "Report regeneration scheduled.",
  "task_id": "<celery-task-id>"
}
```

### Revenue Calculator

`GET /api/reporting/revenue/`

Calculate revenue for one or more categories over an inclusive date range.

Allowed roles: `owner`, `manager`

**Query Parameters:**

| Parameter    | Type     | Required | Description                                                    |
| ------------ | -------- | -------- | -------------------------------------------------------------- |
| `start_date` | date     | Yes      | Start of the range (inclusive), e.g. `2026-03-01`              |
| `end_date`   | date     | Yes      | End of the range (inclusive), must be >= `start_date`          |
| `fields`     | string[] | Yes      | One or more of: `tickets`, `products`, `events` (repeated key) |

**Example request:**

```text
GET /api/reporting/revenue/?start_date=2026-03-01&end_date=2026-03-15&fields=products&fields=tickets
```

**Response example:**

```json
{
  "start_date": "2026-03-01",
  "end_date": "2026-03-15",
  "products": "1250.00",
  "tickets": "3400.00",
  "total_revenue": "4650.00"
}
```

Only selected fields appear in the response. `total_revenue` is always present and equals the sum of all selected category amounts.

**Revenue definitions:**

- **Products** – net completed product sales minus refunds that occurred in the window.
- **Tickets** – issued (non-voided) gate ticket sales created in the window.
- **Events** – `paid_amount` from non-cancelled venue reservations whose `starts_at` falls in the window.

## Common Notes

### Pagination

List endpoints use page-number pagination by default.

Typical shape:

```json
{
  "count": 20,
  "next": "http://localhost:8000/api/...",
  "previous": null,
  "results": []
}
```

### Filtering, Searching, and Ordering

Several endpoints support:

- DRF search via `?search=...`
- ordering via `?ordering=...`
- django-filter query params defined by the relevant viewset

### Error Format

Validation and permission errors return standard DRF-style JSON responses, typically:

```json
{
  "detail": "Error message"
}
```

or field-level validation:

```json
{
  "field_name": [
    "Validation error message"
  ]
}
```
