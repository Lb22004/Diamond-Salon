# Change History — Diamond Salón · Atelier Contable

## [2026-11-08] Person 1 (P1 · Platform, Auth, Períodos, UI Kit & Panel)

**Owner:** Person 1 (P1 — Platform, Auth, UI Kit & Dashboard Lead)  
**Scope:** Complete full-stack implementation of P1 deliverables across Sprints 0, 1, 2, and 3 per [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md), [docs/SRS.md](docs/SRS.md), and [docs/database/DB_DESIGN.md](docs/database/DB_DESIGN.md).

---

### 1. Backend Changes (`backend/apps/core/` & `backend/config/`)

#### 1.1 Database Models & Constraints (`backend/apps/core/models.py`)
Implemented all `core_*` tables matching `docs/database/schema.sql`:
- **`User` (`core_user`)**:
  - Added database `CheckConstraint` (`ck_core_user_role`) validating `role` ∈ `('ADMIN', 'ACCOUNTANT', 'AUDITOR', 'PURCHASING', 'CASHIER', 'READONLY')`.
  - Added `role_label` and `full_display_name` convenience properties.
- **`Company` (`core_company`)**:
  - Single-tenant company table enforced by `CheckConstraint(condition=Q(id=1), name="ck_core_company_singleton")` and `CheckConstraint` on `iva_rate` (`0 <= iva_rate < 1`).
  - Added `Company.get_solo()` helper returning the singleton configuration (`Diamond Salón, S.A. de C.V.`, IVA `0.1300`, currency `USD`).
- **`Employee` (`core_employee`)**:
  - Salon stylists, manicurists, reception, and support staff (`STYLIST`, `MANICURIST`, `RECEPTION`, `OTHER`) with DB check constraint.
- **`FiscalYear` (`core_fiscal_year`)**:
  - Fiscal year container (`year` unique, `start_date`, `end_date`, `status` ∈ `OPEN`/`CLOSED`, check `end_date > start_date`).
- **`AccountingPeriod` (`core_accounting_period`)**:
  - Monthly accounting periods (`fiscal_year` `PROTECT`, `year`, `month` `1..12`, `start_date`, `end_date`, `status` ∈ `OPEN`/`CLOSED`, `is_active`, `closed_at`, `closed_by` `PROTECT`).
  - Enforced `UniqueConstraint(fields=["year", "month"])`, month range check, date order check, and `status = 'OPEN' OR closed_at IS NOT NULL`.
- **`AuditLog` (`core_audit_log`)**:
  - Append-only audit trail (`CREATE`, `UPDATE`, `DELETE`, `POST`, `REVERSE`, `VOID`, `CLOSE`, `REOPEN`, `LOGIN`, `EXPORT`) storing `user`, `action`, `table_name`, `record_id`, `before_data` (JSON), `after_data` (JSON), `ip_address`, and `created_at` with indexes `ix_audit_table_record` and `ix_audit_created`.

#### 1.2 Database Migration & Initial Seed (`backend/apps/core/migrations/0002_core_domain_and_seed.py`)
- Created schema for `Company`, `Employee`, `FiscalYear`, `AccountingPeriod`, and `AuditLog`, plus all constraints and indexes.
- Ported the `core` seed data from `docs/database/seed.sql`:
  - Singleton `Company` (`Diamond Salón, S.A. de C.V.` / `Diamond Salón Atelier`, NIT `0614-000000-000-0`, IVA `13%`).
  - `system` user + 6 role-based demo accounts (`admin`, `contador`, `auditor`, `compras`, `cajero`, `lectura`, password: `diamond2026`).
  - `FiscalYear` `2026` and all 12 monthly `AccountingPeriod` rows for 2026, with **Noviembre 2026** marked `is_active=True`.
  - Sample salon stylists/staff (`Roberto G.`, `Andrea M.`, `Sofía L.`, `Valeria R.`).

#### 1.3 Cross-Module Domain Services (`backend/apps/core/services/`)
- **`backend/apps/core/exceptions.py`**:
  - Defined `ClosedPeriodError` raised when attempting to post or mutate records in a closed period.
- **`backend/apps/core/services/periods.py`**:
  - `get_open_period(entry_date) -> AccountingPeriod`: Implements the cross-module contract from `DB_DESIGN.md §6` and `SRS RN-03` (raises `ClosedPeriodError("El período MM/YYYY está cerrado")` when closed).
  - `get_active_period() -> AccountingPeriod | None`: Returns the active working period (`RF-CIE-01`).
  - `activate_period(period, *, user)`: Switches the active working period and logs to `AuditLog`.
  - `generate_fiscal_year_periods(year, *, user)`: Generates a `FiscalYear` and its 12 monthly `AccountingPeriod` rows.
  - `reopen_period(period, *, user, reason)`: Allows `ADMIN` to reopen the most recently closed period with a mandatory audit reason (`RF-CIE-05`).
- **`backend/apps/core/services/audit.py` & `backend/apps/core/middleware.py`**:
  - `log_audit(...)` and `serialize_instance(...)` for append-only audit logging (`RF-SEG-03`, `RNF-05`).
  - `AuditMiddleware`: Captures request user and client IP in contextvars and automatically records fallback audit entries for mutating `/api/` calls.

#### 1.4 RBAC Permissions & REST API Endpoints
- **`backend/apps/core/permissions.py`**:
  - Implemented `IsAdminRole`, `IsAdminOrReadOnly`, `IsAccountantOrAdmin`, `IsPurchasingOrAdmin`, `IsCashierOrAdmin`, `CanViewAuditLog`, and `ROLE_PERMISSIONS_MATRIX` (`SRS §2.3`, `RF-SEG-02`).
- **`backend/apps/core/serializers.py`, `views.py`, `urls.py`, `admin.py`**:
  - `POST /api/auth/token/` & `POST /api/v1/auth/token/`: JWT login returning `{ access, refresh, user }` and recording a `LOGIN` audit log (`RF-SEG-01`).
  - `POST /api/auth/token/refresh/` & `POST /api/v1/auth/token/refresh/`: JWT token refresh.
  - `GET /api/v1/auth/me/`: Current user profile, permissions matrix, company info, and active period.
  - `GET/POST/PATCH/DELETE /api/v1/users/`: User & role administration (`ADMIN` only, `RF-SEG-04`).
  - `GET/PUT/PATCH /api/v1/company/`: Single-tenant company settings (`RF-SEG-05`).
  - `GET/POST/PATCH /api/v1/employees/`: Salon employees catalog.
  - `GET /api/v1/fiscal-years/` & `GET /api/v1/periods/`: Period listing, `GET /api/v1/periods/active/`, `POST /api/v1/periods/generate-year/`, `POST /api/v1/periods/{id}/activate/`, `POST /api/v1/periods/{id}/reopen/`.
  - `GET /api/v1/audit-log/`: Filterable, searchable append-only audit trail (`ADMIN`, `AUDITOR`, `ACCOUNTANT`).
  - `GET /api/v1/dashboard/summary/?period=<id>`: Live KPI aggregation for the Panel (`RF-PAN-01`) with introspection guards so it works both before and after P2/P4/P5 tables are migrated.
  - `GET /api/v1/search/?q=<term>`: Global search (`Ctrl+K`, `RF-GEN-02`) across views, accounts, journal entries, and sales/purchase documents.
  - `GET /api/v1/notifications/`: Notification bell alerts (`RF-GEN-05`) for prior open periods, critical stock, and draft entries.
- **`backend/config/settings.py` & `backend/config/urls.py`**:
  - Wired `AuditMiddleware` and `/api/v1/` core routes.
  - Added optional `USE_SQLITE` environment toggle for running pytest locally when Docker is offline while keeping PostgreSQL 17 as the default engine.

---

### 2. Frontend Changes (`frontend/src/`)

#### 2.1 HTTP Client, Formatters & Pinia Stores
- **`frontend/src/api/http.js`**: Added response interceptor that automatically refreshes expired access tokens via `/api/auth/token/refresh/` and redirects to `/login` when unauthenticated.
- **`frontend/src/utils/formatters.js`**:
  - `formatMoney(value)`: Formats decimal strings into `$#,##0.00` using integer string arithmetic (zero floating-point drift, `RF-GEN-04`, `RNF-03`).
  - `formatDateShort(value)` (`dd/mm/yy`), `formatDateLong(value)` (`dd/mm/yyyy`), and `formatDateTime(value)`.
- **`frontend/src/stores/auth.js`**: Pinia store managing JWT tokens, current user profile, role getters (`isAdmin`, `isAccountant`, `canViewAudit`), and route access checks.
- **`frontend/src/stores/period.js`**: Pinia store managing accounting periods, active period selector (`Noviembre 2026`), period activation, fiscal year generation, and period reopening.

#### 2.2 Shared UI Component Kit (`frontend/src/components/ui/`)
Built all shared UI components defined in `SRS §7.1`:
- `AppShell.vue` — Sidebar navigation (7 core views + RBAC admin links + "Cierre periódico" status widget), top header with `PeriodPicker`, `Ctrl+K` global search button, notification bell dropdown, and user/role indicator (`RF-GEN-01`).
- `KpiCard.vue` — Metric card with wine, gold, ink, and danger tones.
- `DataTable.vue` — Sortable, paginated table with custom cell slots and sticky period totals footer (`"Sumas iguales comprobadas"`, `RF-GEN-03`).
- `MoneyCell.vue` — Tabular-numeral currency cell (`$#,##0.00`).
- `Badge.vue` — Semantic pills (`VITRINA`, `CABINA`, `OPEN`, `CLOSED`, `POSTED`, `DRAFT`, `REVERSED`, user roles).
- `PeriodPicker.vue` — Active period selector dropdown ("Período: Noviembre 2026").
- `DateRangePicker.vue` — Date range filter (`Desde` / `Hasta`) with `dd/mm/yyyy` preview.
- `SearchInput.vue` — Debounced search input with clear button.
- `ExportButton.vue` — Reusable PDF / Excel export dropdown compatible with `/api/v1/exports/{book}/`.
- `FormModal.vue` & `ConfirmDialog.vue` — Accessible modals for forms and audited confirmations (with mandatory reason field).
- `GlobalSearchModal.vue` — `Ctrl/⌘+K` command palette (`RF-GEN-02`).
- `index.js` — Barrel export for all shared UI components.

#### 2.3 P1 Views, Router & Styling
- **`frontend/src/modules/dashboard/views/LoginView.vue` (`/login`)**: Authentication screen with role quick-fill chips for testing all 6 roles.
- **`frontend/src/modules/dashboard/views/PanelView.vue` (`/panel`)**: Executive Dashboard (`RF-PAN-01`) with 4 primary KPIs, Cabina vs Vitrina summary panels, critical stock alerts, platform health card, and latest journal entries table.
- **`frontend/src/modules/dashboard/views/UsersView.vue` (`/usuarios`)**: Admin user and role management view (`RF-SEG-04`).
- **`frontend/src/modules/dashboard/views/CompanySettingsView.vue` (`/configuracion`)**: Multi-tab configuration view for Company settings (`RF-SEG-05`), Accounting Periods (`RF-CIE-01`, `RF-CIE-05`), Salon Employees, and the immutable `AuditLog` explorer (`RF-SEG-03`).
- **`frontend/src/router/index.js` & `frontend/src/App.vue`**: Wired routes and authentication/RBAC navigation guards.
- **`frontend/src/styles/main.css`**: Complete Diamond Salón visual design system (`--wine: #6b1a24`, `--gold: #8a6a1f`, `--ink: #1f1f1f`, `--paper: #faf8f4`).

---

### 3. Tests & Verification
- **`backend/apps/core/tests/test_core.py`**:
  - Verified seed data (`Company` singleton `id=1`, `FiscalYear` 2026, 12 `AccountingPeriod` rows, November 2026 active).
  - Verified `get_open_period()` and `ClosedPeriodError` (`"El período 10/2026 está cerrado"`).
  - Verified `reopen_period()` RBAC, mandatory reason, and `REOPEN` audit trail.
  - Verified JWT login (`POST /api/v1/auth/token/`) and `LOGIN` audit entry.
  - Verified RBAC permissions across `ADMIN`, `AUDITOR`, and `CASHIER` roles on `/api/v1/users/`, `/api/v1/company/`, and `/api/v1/audit-log/`.
  - Verified `/api/v1/dashboard/summary/`, `/api/v1/search/`, and `/api/v1/notifications/`.
