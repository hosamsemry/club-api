# Club Management API

A multi-tenant REST API for managing social clubs — covering inventory, point-of-sale, event reservations, gate ticketing, and automated reporting.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Django 6.0 / Django REST Framework 3.16 |
| Database | PostgreSQL (via psycopg2) |
| Auth | JWT (Simple JWT) |
| Task Queue | Celery 5.6 + Redis |
| Filtering | django-filter |
| CORS | django-cors-headers |

## Project Structure

```
api/
├── management/          # Django project settings, ASGI/WSGI, Celery app, root URLs
├── accounts/            # User model, registration, JWT login, club user CRUD
├── clubs/               # Club model, TenantBaseModel base class
├── core/                # AuditLog, Dashboard, permissions, exception handler, middleware
├── events/              # OccasionType, VenueReservation, payments, cancellations
├── inventory/           # Product, Category, StockMovement, LowStockAlert
├── sales/               # Sale, SaleItem, price overrides, refunds, daily analytics
├── tickets/             # GateTicketType, GateEntryDay, GateTicketSale, check-in/void
├── reporting/           # DailyClubReport, CSV export, revenue calculator, Celery tasks
└── media/reports/       # Generated report CSV files
```

## Multi-Tenancy

All business data is scoped to a **Club**. Every model inherits from `TenantBaseModel` which includes a `club` foreign key. The `TenantModelViewSet` base class automatically filters querysets by `request.user.club` and stamps new records with the correct club.

## Roles

| Role | Scope |
|------|-------|
| `owner` | Full access — dashboard, users, reports, refunds, price overrides |
| `manager` | Same as owner except cannot create other owners |
| `cashier` | Sales, inventory, ticket sales |
| `staff` | Ticket sales and check-in only |

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL
- Redis (for Celery)

### Installation

```bash
# Clone and enter the project
cd api

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env   # then edit with your DB and Redis credentials

# Run migrations
python manage.py migrate

# Create a superuser (for admin access)
python manage.py createsuperuser

# Start the development server
python manage.py runserver
```

### Celery (background tasks)

```bash
# Worker
celery -A management worker -l info

# Beat scheduler (for daily report generation)
celery -A management beat -l info
```

## Docker

The backend repo includes its own `docker-compose.yml` for the API, PostgreSQL, Redis, Celery worker, and Celery Beat.

### Included Services

- `backend`: Django API on `http://localhost:8000`
- `postgres`: PostgreSQL 15 for the app database
- `redis`: Redis 7 for cache and Celery broker/backend
- `celery-worker`: background task worker
- `celery-beat`: periodic task scheduler

### First-Time Setup

From the `api/` folder:

```bash
cp .env.docker.example .env.docker
```

Update `.env.docker` before sharing the setup outside local development, especially:

- `SECRET_KEY`
- `POSTGRES_PASSWORD`

### Start

From the `api/` folder:

```bash
docker compose up --build
```

The backend container runs Django migrations automatically on startup.

### Stop

From the `api/` folder:

```bash
docker compose down
```

### Notes

- This compose file creates the shared Docker network `club-network`.
- The frontend compose file in the sibling `club/` folder joins that existing network, so start the backend stack first.
- Backend media files are mounted from `api/media`, and collected static files are mounted from `api/staticfiles`.
- Celery worker and beat use the same image and environment file as the backend service.

## API Endpoints

Base URL: `/api/`

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/accounts/register/` | Register a new club + owner |
| POST | `/api/token/` | Obtain JWT token pair |
| POST | `/api/token/refresh/` | Refresh access token |

### Accounts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/accounts/users/` | List club users |
| POST | `/api/accounts/users/` | Create club user |
| GET | `/api/accounts/users/{id}/` | Retrieve user |
| PATCH | `/api/accounts/users/{id}/` | Update user role/status |

### Core

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/core/dashboard/` | Club dashboard summary |
| GET | `/api/core/audit-logs/` | Filterable audit log |

### Inventory

| Method | Endpoint | Description |
|--------|----------|-------------|
| CRUD | `/api/inventory/categories/` | Product categories |
| CRUD | `/api/inventory/products/` | Products |
| GET/POST | `/api/inventory/stock-movements/` | Stock movements (restock, adjustment, refund) |
| GET | `/api/inventory/low-stock-alerts/` | Active low-stock alerts |

### Sales

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/sales/` | List / create sales |
| POST | `/api/sales/{id}/refund/` | Refund a completed sale |
| GET | `/api/sales/daily-summary/` | Daily sales summary |
| GET | `/api/sales/daily-profit/` | Daily profit breakdown |
| GET | `/api/sales/top-products/` | Top-selling products |

### Events

| Method | Endpoint | Description |
|--------|----------|-------------|
| CRUD | `/api/events/occasion-types/` | Occasion types (no delete) |
| CRUD | `/api/events/reservations/` | Venue reservations |
| POST | `/api/events/reservations/{id}/record-payment/` | Record payment |
| POST | `/api/events/reservations/{id}/cancel/` | Cancel with optional refund |

### Tickets

| Method | Endpoint | Description |
|--------|----------|-------------|
| CRUD | `/api/tickets/types/` | Ticket types (no delete) |
| CRUD | `/api/tickets/days/` | Entry days (no delete) |
| GET/POST | `/api/tickets/sales/` | Ticket sales |
| GET | `/api/tickets/sales/daily-summary/` | Daily ticket summary |
| GET | `/api/tickets/items/` | Individual tickets |
| POST | `/api/tickets/items/{id}/check-in/` | Check in by ID |
| POST | `/api/tickets/items/check-in-by-code/` | Check in by code |
| POST | `/api/tickets/items/{id}/void/` | Void a ticket |

### Reporting

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/reporting/daily/` | Daily club reports |
| GET | `/api/reporting/daily/{id}/export/csv/` | Download CSV export |
| POST | `/api/reporting/daily/{id}/regenerate/` | Regenerate via Celery |
| GET | `/api/reporting/revenue/` | Revenue calculator by category |

## Error Format

All errors return a consistent envelope:

```json
{
  "success": false,
  "message": "Validation error",
  "errors": {
    "field_name": ["Error message"]
  }
}
```

## Pagination

List endpoints return paginated responses:

```json
{
  "count": 42,
  "next": "http://localhost:8000/api/...?page=2",
  "previous": null,
  "results": []
}
```

## License

All rights reserved.
