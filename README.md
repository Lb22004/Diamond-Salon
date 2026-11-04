# Diamond Salón · Atelier Contable

Accounting and mixed-inventory web application for **Diamond Salón** (El Salvador), built with **Vue 3 (Vite)**, **Django 5 + Django REST Framework**, and **PostgreSQL 17**, fully containerized with **Docker Compose**.

## Documentation

| Document | Description |
|---|---|
| [docs/SRS.md](docs/SRS.md) | Software Requirements Specification (functional requirements per view, business rules, automatic posting matrix, NFRs, and mock-up discrepancy log). |
| [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | 5-person work division (vertical slices + view ownership), 4-sprint roadmap, service contracts, and Git workflow. |
| [docs/database/DB_DESIGN.md](docs/database/DB_DESIGN.md) | PostgreSQL database architecture, ER diagram, table dictionary, triggers, and key queries. |
| [docs/database/schema.sql](docs/database/schema.sql) | Reference PostgreSQL 17 DDL (tables, CHECK constraints, immutability triggers, and reporting views). |
| [docs/database/seed.sql](docs/database/seed.sql) | Base NIIF PYMES chart of accounts for Diamond Salón, posting-engine mappings, locations, and document series. |

## Quick Start (Docker)

```bash
# 1. Optional: copy environment defaults
cp .env.example .env

# 2. Build and start PostgreSQL, Django API, and Vue dev server
docker compose up --build
```

Once running:
- **Vue 3 Frontend:** http://localhost:5173
- **Django API Healthcheck:** http://localhost:8000/api/health/
- **Django Admin:** http://localhost:8000/admin/
- **PostgreSQL:** `localhost:5432` (db: `diamond_salon`, user: `diamond`, password: `diamond`)
- **pgAdmin (optional):** `docker compose --profile tools up -d` -> http://localhost:5050

### Useful Commands

```bash
# Create & apply Django migrations inside the backend container
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate

# Create an admin user
docker compose exec backend python manage.py createsuperuser

# Run backend tests
docker compose exec backend pytest
```

## Project Structure

```text
Diamond-Salon/
├── docker-compose.yml          # Orchestrates db (Postgres 17), backend (Django 5), frontend (Vue 3)
├── .env.example                # Environment variables template
├── docs/
│   ├── SRS.md                  # Full Software Requirements Specification
│   ├── IMPLEMENTATION_PLAN.md  # 5-developer division & sprint plan
│   └── database/
│       ├── DB_DESIGN.md        # ER diagram & table dictionary
│       ├── schema.sql          # Reference PostgreSQL DDL + triggers + views
│       └── seed.sql            # NIIF PYMES chart of accounts & account mappings
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── manage.py
│   ├── config/                 # Django settings, root URLs, WSGI
│   └── apps/
│       ├── core/               # P1: Custom User, roles, periods, company, audit
│       ├── accounting/         # P2: Chart of accounts, journal entries, posting engine
│       ├── reports/            # P3: General ledger, trial balance, period close, exports
│       ├── sales/              # P4: Customers, services, FCF/CCF sales book
│       ├── inventory/          # P5: Mixed inventory (Vitrina/Cabina), Kardex, adjustments
│       └── purchases/          # P5: Suppliers, CCF purchases book, supplier payments
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js          # Proxies /api -> http://backend:8000
    └── src/
        ├── api/http.js         # Axios client with JWT interceptor
        ├── router/index.js     # Routes for all 7 sidebar views
        └── modules/            # Mirrors backend ownership (dashboard, accounting, reports, sales, inventory, purchases)
```
