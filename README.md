# FIntech Roaster

A Django-based financial technology application demonstrating advanced ORM queries, custom model managers, and database optimization patterns with Django Debug Toolbar integration.

## Features

- **Account Management** — View, filter, and inspect user accounts with related cards and transactions
- **Transaction Tracking** — Browse transactions with pagination and related entity prefetching
- **Merchant Analytics** — Aggregated merchant volume and transaction counts
- **Dashboard** — Real-time metrics: total accounts, active accounts, completed transactions, and total volume
- **15 Advanced ORM Queries** — Demonstrates Q() objects, subqueries, F() expressions, Case/When, aggregations, annotations, and more
- **N+1 Query Demo** — Intentionally slow endpoint to illustrate the N+1 problem and debug toolbar detection
- **Django Debug Toolbar** — Full SQL query inspection with timing, call stack, and raw SQL

## Tech Stack

| Component          | Technology                          |
|--------------------|-------------------------------------|
| Backend            | Django 5.x / 6.x                   |
| Database           | SQLite 3 (dev), PostgreSQL 16 (Docker) |
| Debugging          | Django Debug Toolbar 5.x           |
| Python             | 3.12 (Docker image)                |
| Container Runtime  | Docker 29.x + Docker Compose v5    |
| App Server         | Gunicorn (4 workers)               |

## Project Structure

```
upay_backend/
├── manage.py
├── requirements.txt
├── db.sqlite3
├── Dockerfile                   # Multi-stage Python 3.12-slim image
├── docker-compose.yml           # Orchestrates web + db services
├── docker-entrypoint.sh         # Migrate → collectstatic → gunicorn
├── .env                         # Local secrets (not committed)
├── djangoInternals/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py              # Main URL config (/fintech/, /admin/, /__debug__/)
│   ├── wsgi.py
│   └── asgi.py
├── fintech/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py            # Account, Transaction, Merchant, Card, AuditLog
│   ├── views.py             # Class-based + function-based views
│   ├── urls.py              # Fintech app URL routes
│   ├── api_views.py         # DRF views: APIView, GenericAPIView, ModelViewSet
│   ├── api_urls.py          # DRF URL routing: v1/v2/v3 + DefaultRouter
│   ├── orm_queries.py       # 15 standalone ORM queries (shell script)
│   ├── tests.py
│   ├── migrations/
│   └── templates/
│       └── fintech/
│           ├── orm_queries_demo.html
│           ├── account_list.html
│           ├── account_detail.html
│           ├── transaction_list.html
│           ├── merchant_list.html
│           ├── dashboard.html
│           └── statement.html
└── venv/
```

## Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/Ranger-DRAX/FIntech_Roaster.git
cd FIntech_Roaster
```

### 2. Create a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Create a superuser (optional)

```bash
python manage.py createsuperuser
```

### 6. Start the development server

```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000/`.

---

## 🐳 Docker Integration

The project ships with full Docker support — a `Dockerfile` for the Django app and a `docker-compose.yml` that orchestrates both the web service and a PostgreSQL 16 database. This is the **recommended** way to run the project.

### Services

| Service | Container | Image | Port |
|---------|-----------|-------|------|
| `web` | `upay-web` | `upay_backend-web` (built locally) | `8000 → 8000` |
| `db` | `upay-db` | `postgres:16-alpine` | `5432 → 5432` |

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ 29.x
- [Docker Compose](https://docs.docker.com/compose/) ≥ v5 (bundled with Docker Desktop)

Verify your installation:

```bash
docker --version          # Docker version 29.x.x
docker compose version    # Docker Compose version v5.x.x
```

### Environment Variables

Create a `.env` file in the project root before starting the containers:

```bash
# .env
DJANGO_SECRET_KEY=your-very-secret-key-here
POSTGRES_PASSWORD=changeme
DATABASE_URL=postgres://upay_user:changeme@db:5432/upay
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,upay-web
```

> **Note:** The `.env` file is consumed by the `web` service via `env_file: .env` in `docker-compose.yml`. Never commit this file to version control.

### Build & Run

**Start all services (build image on first run):**

```bash
docker compose up --build
```

**Start in detached mode (background):**

```bash
docker compose up -d --build
```

The entrypoint script (`docker-entrypoint.sh`) automatically runs on startup:

1. `python manage.py migrate --noinput` — applies all database migrations
2. `python manage.py collectstatic --noinput` — collects static files
3. Starts **Gunicorn** with 4 workers bound to `0.0.0.0:8000`

The application will be available at `http://localhost:8000/`.

### Stopping & Cleanup

```bash
# Stop containers (preserves volumes and images)
docker compose down

# Stop and remove volumes (wipes the database)
docker compose down -v

# Remove the built image
docker rmi upay_backend-web
```

### Running Management Commands

Execute Django management commands inside the running `web` container:

```bash
# Open a Django shell
docker compose exec web python manage.py shell

# Create a superuser
docker compose exec web python manage.py createsuperuser

# Run tests
docker compose exec web python manage.py test fintech

# Open a bash shell inside the container
docker compose exec web bash

# Apply new migrations
docker compose exec web python manage.py migrate
```

### Checking Container Status

```bash
# List running containers
docker ps

# View live logs from all services
docker compose logs -f

# View logs from a specific service
docker compose logs -f web
docker compose logs -f db
```

### Dockerfile Overview

```dockerfile
# Base: python:3.12-slim
# - Installs libpq-dev and gcc (required for psycopg2)
# - Copies requirements.txt and installs Python dependencies
# - Copies application source code
# - Runs docker-entrypoint.sh (migrate → collectstatic → gunicorn)
```

| Setting | Value |
|---------|-------|
| Base image | `python:3.12-slim` |
| Working directory | `/app` |
| Exposed port | `8000` |
| WSGI server | Gunicorn — `djangoInternals.wsgi:application` |
| Workers | 4 |

### Docker Compose Architecture

```
┌─────────────────────────────────────┐
│          docker-compose.yml         │
│                                     │
│  ┌──────────┐      ┌─────────────┐  │
│  │  upay-web │─────▶  upay-db   │  │
│  │ :8000    │      │ :5432       │  │
│  │ gunicorn │      │ postgres:16 │  │
│  └──────────┘      └─────────────┘  │
│       │                  │          │
│  static_volume    postgres_data     │
│   (named vol)      (named vol)      │
└─────────────────────────────────────┘
```

- `web` depends on `db` with `condition: service_healthy` — the app only starts after Postgres passes its health check (`pg_isready`).
- Both services use named Docker volumes so data persists across restarts.

---

## Template Endpoints


| URL                              | View                        | Description                                      |
|----------------------------------|-----------------------------|--------------------------------------------------|
| `/fintech/`                      | `orm_queries_demo`          | 15 advanced ORM queries with debug toolbar        |
| `/fintech/accounts/`             | `AccountListView`           | Paginated list of all accounts                   |
| `/fintech/accounts/<id>/`        | `AccountDetailView`         | Account detail with cards and transactions       |
| `/fintech/transactions/`         | `TransactionListView`       | Paginated list of all transactions               |
| `/fintech/merchants/`            | `MerchantListView`          | Merchants ranked by transaction volume           |
| `/fintech/dashboard/`            | `DashboardView`             | Aggregated dashboard metrics                     |
| `/fintech/statement-slow/`       | `user_statement_slow`       | N+1 query demo — slow endpoint                   |
| `/admin/`                        | Django Admin                | Admin interface                                  |
| `/__debug__/`                    | Debug Toolbar               | SQL panel, profiling, and inspection             |

## REST API (DRF)

The REST API is mounted at `/fintech/api/` and exposes three versioned namespaces that demonstrate progressively more abstract DRF view patterns — all serving identical functionality.

```
Base URL: http://localhost:8000/fintech/api/
```

### View-layer styles

| Namespace | Style | When to use |
|-----------|-------|-------------|
| `v1/` | **APIView** | Full manual control; non-CRUD endpoints, webhooks, auth flows |
| `v2/` | **GenericAPIView + Mixins** | Standard CRUD with per-request queryset customisation |
| `v3/` | **ModelViewSet + DefaultRouter** | Standard CRUD with minimal boilerplate; consistent URL patterns |

### v1 & v2 — Merchant endpoints

Both namespaces expose the same URL structure for `Merchant`:

| Method | URL | Action |
|--------|-----|--------|
| `GET` | `/fintech/api/v{1,2}/merchants/` | List all merchants |
| `POST` | `/fintech/api/v{1,2}/merchants/` | Create a merchant |
| `GET` | `/fintech/api/v{1,2}/merchants/<pk>/` | Retrieve a merchant |
| `PUT` | `/fintech/api/v{1,2}/merchants/<pk>/` | Full update |
| `PATCH` | `/fintech/api/v{1,2}/merchants/<pk>/` | Partial update |
| `DELETE` | `/fintech/api/v{1,2}/merchants/<pk>/` | Delete |

### v3 — ModelViewSet + DefaultRouter

The `DefaultRouter` auto-generates all six URL patterns per registered resource and provides a browsable API root at `/fintech/api/v3/`.

#### Registered resources

| Prefix | ViewSet | basename |
|--------|---------|----------|
| `merchants/` | `MerchantViewSet` | `v3-merchant` |
| `accounts/` | `AccountViewSet` | `account` |
| `transactions/` | `TransactionViewSet` | `transaction` |

#### Generated URL names

Each `router.register()` call produces two named URL patterns:

```
<basename>-list    →  GET  POST   /v3/<prefix>/
<basename>-detail  →  GET  PUT  PATCH  DELETE   /v3/<prefix>/<pk>/
```

#### Full v3 endpoint table

| Method | URL | Action |
|--------|-----|--------|
| `GET` | `/fintech/api/v3/merchants/` | List merchants |
| `POST` | `/fintech/api/v3/merchants/` | Create merchant |
| `GET` | `/fintech/api/v3/merchants/<pk>/` | Retrieve merchant |
| `PUT` | `/fintech/api/v3/merchants/<pk>/` | Full update |
| `PATCH` | `/fintech/api/v3/merchants/<pk>/` | Partial update |
| `DELETE` | `/fintech/api/v3/merchants/<pk>/` | Delete |
| `GET` | `/fintech/api/v3/accounts/` | List accounts |
| `POST` | `/fintech/api/v3/accounts/` | Create account |
| `GET` | `/fintech/api/v3/accounts/<pk>/` | Retrieve account |
| `PUT` | `/fintech/api/v3/accounts/<pk>/` | Full update |
| `PATCH` | `/fintech/api/v3/accounts/<pk>/` | Partial update |
| `DELETE` | `/fintech/api/v3/accounts/<pk>/` | Delete |
| `GET` | `/fintech/api/v3/transactions/` | List transactions |
| `POST` | `/fintech/api/v3/transactions/` | Create transaction |
| `GET` | `/fintech/api/v3/transactions/<uuid>/` | Retrieve transaction |
| `PUT` | `/fintech/api/v3/transactions/<uuid>/` | Full update |
| `PATCH` | `/fintech/api/v3/transactions/<uuid>/` | Partial update |
| `DELETE` | `/fintech/api/v3/transactions/<uuid>/` | Delete |

> `Transaction` uses a UUID primary key (`transaction_id`). The router picks it up automatically — no extra `lookup_field` configuration required.

### Serializers

#### MerchantSerializer

| Field | Read-only | Notes |
|-------|-----------|-------|
| `id` | ✅ | Auto PK |
| `name` | | |
| `merchant_id` | | Unique |
| `category` | | `RETAIL` `FOOD` `TRAVEL` `ENTERTAINMENT` `UTILITIES` `OTHER` |
| `is_active` | | |
| `fee_rate` | | Default `0.0150` |
| `created_at` | ✅ | Auto-set |

#### AccountSerializer

| Field | Read-only | Notes |
|-------|-----------|-------|
| `id` | ✅ | Auto PK |
| `user` | | FK → User; override `perform_create()` to lock to `request.user` |
| `account_number` | | Unique |
| `account_type` | | `SAVINGS` `CHECKING` `CREDIT` |
| `balance` | | ≥ 0 (DB constraint) |
| `currency` | | ISO code, default `USD` |
| `status` | | `ACTIVE` `FROZEN` `CLOSED` |
| `created_at` | ✅ | Auto-set |
| `updated_at` | ✅ | Auto-updated |

#### TransactionSerializer

| Field | Read-only | Notes |
|-------|-----------|-------|
| `transaction_id` | ✅ | UUID PK, auto-generated |
| `account` | | FK → Account |
| `card` | | FK → Card, nullable |
| `merchant` | | FK → Merchant, nullable |
| `amount` | | > 0 (DB constraint) |
| `currency` | | ISO code, default `USD` |
| `transaction_type` | | `DEBIT` `CREDIT` `REFUND` |
| `status` | | `PENDING` `COMPLETED` `FAILED` `REVERSED` |
| `description` | | Optional text |
| `timestamp` | ✅ | Auto-set |
| `related_transaction` | | Self-FK, nullable (for reversals) |

### Query-string filters

`AccountViewSet` and `TransactionViewSet` support optional URL query parameters:

```
GET /fintech/api/v3/accounts/?status=ACTIVE&account_type=SAVINGS&currency=USD
GET /fintech/api/v3/transactions/?status=COMPLETED&transaction_type=CREDIT&account=3&currency=USD
```

| ViewSet | Parameter | Filters on |
|---------|-----------|-----------|
| Account | `status` | `ACTIVE` / `FROZEN` / `CLOSED` |
| Account | `account_type` | `SAVINGS` / `CHECKING` / `CREDIT` |
| Account | `currency` | ISO currency code |
| Transaction | `status` | `PENDING` / `COMPLETED` / `FAILED` / `REVERSED` |
| Transaction | `transaction_type` | `DEBIT` / `CREDIT` / `REFUND` |
| Transaction | `account` | Account PK |
| Transaction | `currency` | ISO currency code |

### ViewSet lifecycle hooks

Each ViewSet exposes three override points for business logic:

```python
def perform_create(self, serializer):
    # Called just before .save() on POST.
    # Inject audit fields, send notifications, validate business rules.
    serializer.save()

def perform_update(self, serializer):
    # Called just before .save() on PUT / PATCH.
    # Stamp updated_by, trigger downstream events.
    serializer.save()

def perform_destroy(self, instance):
    # Hard-delete by default.
    # Account soft-delete: instance.status = Account.Status.CLOSED; instance.save()
    # Transaction reversal: instance.status = Transaction.Status.REVERSED; instance.save()
    instance.delete()
```

### Quick test with httpie

```bash
# List all accounts
http GET http://localhost:8000/fintech/api/v3/accounts/

# Create an account
http POST http://localhost:8000/fintech/api/v3/accounts/ \
    user=1 account_number="ACC-001" account_type="SAVINGS" currency="USD"

# Filter active savings accounts
http GET "http://localhost:8000/fintech/api/v3/accounts/?status=ACTIVE&account_type=SAVINGS"

# Create a transaction
http POST http://localhost:8000/fintech/api/v3/transactions/ \
    account=1 amount="250.00" transaction_type="DEBIT"

# Retrieve a transaction by UUID
http GET http://localhost:8000/fintech/api/v3/transactions/550e8400-e29b-41d4-a716-446655440000/
```

## Data Models

### Account
| Field           | Type                      | Description                        |
|-----------------|---------------------------|------------------------------------|
| user            | ForeignKey → User         | Account owner                      |
| account_number  | CharField (unique)        | Unique account identifier          |
| account_type    | CharField (choices)       | SAVINGS, CHECKING, CREDIT          |
| balance         | DecimalField              | Current balance (≥ 0)              |
| currency        | CharField                 | ISO currency code (default: USD)   |
| status          | CharField (choices)       | ACTIVE, FROZEN, CLOSED             |
| created_at      | DateTimeField             | Auto-set on creation               |
| updated_at      | DateTimeField             | Auto-updated on save               |

### Transaction
| Field              | Type                      | Description                        |
|--------------------|---------------------------|------------------------------------|
| transaction_id     | UUIDField (PK)            | Unique transaction UUID            |
| account            | ForeignKey → Account      | Source account                     |
| card               | ForeignKey → Card (null)  | Card used (optional)               |
| merchant           | ForeignKey → Merchant     | Merchant (optional)                |
| amount             | DecimalField              | Transaction amount (> 0)           |
| currency           | CharField                 | ISO currency code                  |
| transaction_type   | CharField (choices)       | DEBIT, CREDIT, REFUND              |
| status             | CharField (choices)       | PENDING, COMPLETED, FAILED, REVERSED |
| description        | TextField                 | Optional description               |
| timestamp          | DateTimeField             | Auto-set on creation               |

### Merchant
| Field        | Type                      | Description                        |
|--------------|---------------------------|------------------------------------|
| name         | CharField                 | Merchant name                      |
| merchant_id  | CharField (unique)        | Unique merchant identifier         |
| category     | CharField (choices)       | RETAIL, FOOD, TRAVEL, ENTERTAINMENT, UTILITIES, OTHER |
| is_active    | BooleanField              | Active status                      |
| fee_rate     | DecimalField              | Fee rate (default: 1.5%)           |

### Card
| Field        | Type                      | Description                        |
|--------------|---------------------------|------------------------------------|
| user         | ForeignKey → User         | Card holder                        |
| account      | ForeignKey → Account      | Linked account                     |
| card_number  | CharField (unique)        | 16-digit card number               |
| card_type    | CharField (choices)       | DEBIT, CREDIT                      |
| status       | CharField (choices)       | ACTIVE, BLOCKED, CANCELLED         |
| expiry_date  | DateField                 | Expiration date                    |
| cvv          | CharField                 | Security code                      |

### AuditLog
| Field        | Type                      | Description                        |
|--------------|---------------------------|------------------------------------|
| user         | ForeignKey → User         | User who performed action          |
| action       | CharField (choices)       | CREATE, UPDATE, DELETE, LOGIN, LOGOUT, TRANSFER |
| model_name   | CharField                 | Affected model name                |
| object_id    | CharField                 | Affected object ID                 |
| description  | TextField                 | Action description                 |
| ip_address   | GenericIPAddressField     | Client IP address                  |
| metadata     | JSONField                 | Additional context data            |

## Custom Managers & QuerySets

The project uses custom managers and querysets for cleaner query patterns:

```python
# Account Manager
Account.objects.active()           # Active accounts only
Account.objects.high_balance()     # Balance ≥ $10,000
Account.objects.savings_accounts() # Savings type accounts

# Transaction Manager
Transaction.objects.completed()    # Completed transactions
Transaction.objects.pending()      # Pending transactions
Transaction.objects.today()        # Today's transactions

# Card Manager
Card.objects.active()              # Active cards
Card.objects.blocked()             # Blocked cards
```

## 15 Advanced ORM Queries

The `/fintech/` endpoint demonstrates 15 advanced Django ORM patterns:

| #  | Technique              | Description                                                       |
|----|------------------------|-------------------------------------------------------------------|
| 1  | **Q() Objects**        | OR conditions — Active Savings OR High Balance Checking            |
| 2  | **Aggregation**        | `Sum` — Total volume of completed transactions                    |
| 3  | **Conditional Count**  | `Count` with `filter=` — Users with active card counts            |
| 4  | **Conditional Sum**    | `Sum` with `filter=` — Total debit spending per account           |
| 5  | **F() Expressions**    | Compare fields — Accounts never updated (`updated_at == created_at`) |
| 6  | **F() Math**           | Arithmetic — Simulate fee rate increase with `F() + Decimal()`    |
| 7  | **Relational Q()**     | Cross-table OR — Blocked card transactions OR failed transactions  |
| 8  | **Subqueries**         | `Subquery` + `OuterRef` — Latest transaction date per account     |
| 9  | **Subquery Filtering** | Annotate then filter — Accounts with last txn > $1000             |
| 10 | **Case/When**          | Conditional annotation — VIP vs Standard tier by balance          |
| 11 | **Multi-Aggregation**  | `Avg`, `Max`, `Min` — Global transaction statistics               |
| 12 | **GroupBy**            | `values().annotate()` — Volume by merchant category               |
| 13 | **Exclude**            | `exclude()` — Accounts with no transactions in last 30 days       |
| 14 | **Nested Subquery**    | Cross-model subquery — Top merchant name per user                 |
| 15 | **Complex Sum**        | `F() * F()` with `DecimalField` — Merchant profit calculation     |

### Running Queries Standalone

```bash
python manage.py shell < fintech/orm_queries.py
```

### Query Report Screenshots

The following screenshots show the Django Debug Toolbar SQL panel after executing all 15 ORM queries on the `/fintech/` endpoint.

**Screenshot 1 — Debug Toolbar SQL Panel Overview:**

![Query Report Screenshot 1](ScreenShot/Screenshot1.png)

**Screenshot 2 — Query Details and Execution Plan:**

![Query Report Screenshot 2](ScreenShot/Screenshot2.png)

## Debug Toolbar

Django Debug Toolbar is pre-configured. Visit any page and the toolbar panel appears on the right side.

### Key Panels

- **SQL** — View all queries, execution time, and raw SQL
- **Profiling** — Request timing breakdown
- **Cache** — Cache hit/miss ratios
- **Headers** — Request and response headers

### Configuration

```python
# djangoInternals/settings.py
INTERNAL_IPS = ["127.0.0.1", "localhost"]

DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
}
```

## Database Indexes

Optimized with composite and single-field indexes:

```python
# Account
Index(fields=["user", "status"])
Index(fields=["account_type", "status"])
CheckConstraint(balance__gte=0)

# Transaction
Index(fields=["account", "timestamp"])
Index(fields=["status", "timestamp"])
Index(fields=["transaction_type", "status"])
CheckConstraint(amount__gt=0)

# Merchant
Index(fields=["category", "is_active"])

# Card
Index(fields=["user", "status"])
Index(fields=["account", "status"])

# AuditLog
Index(fields=["user", "action"])
Index(fields=["model_name", "object_id"])
Index(fields=["created_at"])
```

## Running Tests

**Local:**
```bash
python manage.py test fintech
```

**Inside Docker:**
```bash
docker compose exec web python manage.py test fintech
```

## Environment Variables

| Variable                | Default                              | Description                          |
|-------------------------|--------------------------------------|--------------------------------------|
| `DJANGO_SETTINGS_MODULE`| `djangoInternals.settings`           | Django settings module               |
| `DJANGO_SECRET_KEY`     | (insecure dev key)                   | Django secret key                    |
| `DJANGO_DEBUG`          | `False` (Docker) / `True` (local)    | Debug mode                           |
| `DJANGO_ALLOWED_HOSTS`  | `localhost,127.0.0.1,upay-web`       | Comma-separated allowed hosts        |
| `DATABASE_URL`          | —                                    | Full Postgres DSN (Docker)           |
| `POSTGRES_PASSWORD`     | `changeme`                           | Postgres password (docker-compose)   |

> **Production:** Set `DJANGO_DEBUG=False`, configure a strong `DJANGO_SECRET_KEY`, and always use a secure `POSTGRES_PASSWORD`.

## License

This project is for educational and demonstration purposes.

## Repository

[https://github.com/Ranger-DRAX/FIntech_Roaster](https://github.com/Ranger-DRAX/FIntech_Roaster)