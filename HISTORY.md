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


---

## [2026-11-08] Person 2 (P2 · Núcleo Contable: Catálogo de Cuentas, Libro Diario & Motor de Partidas)

**Owner:** Person 2 (P2 — Accounting Core Lead: Catálogo & Diario)  
**Scope:** Complete full-stack implementation of P2 deliverables across Sprints 0, 1, 2, and 3 per [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md), [docs/SRS.md](docs/SRS.md), and [docs/database/DB_DESIGN.md](docs/database/DB_DESIGN.md).

---

### 1. Backend Changes (`backend/apps/accounting/` & `backend/config/urls.py`)

#### 1.1 Database Models & Constraints (`backend/apps/accounting/models.py`)
Implemented all `accounting_*` tables matching `docs/database/schema.sql`:
- **`Account` (`accounting_account`)**:
  - Hierarchical NIIF PYMES account model (`code` numeric unique, `name`, self-FK `parent` `PROTECT`, `level` `1..6`, `account_type`, `nature`, `classification`, `accepts_entries`, `inventory_type` ∈ `VITRINA`/`CABINA`, `niif_reference`, `debit_rule`, `credit_rule`, `is_active`).
  - Enforced `ix_account_parent`, `ix_account_code_prefix`, `level BETWEEN 1 AND 6`, and `(level = 1) = (parent_id IS NULL)`.
- **`AccountMapping` (`accounting_account_mapping`)**:
  - Configurable business-event to account mapping (`key` PK, `account` FK `PROTECT`, `description`) enforcing `RN-12` (zero hard-coded account codes in Python).
- **`JournalEntry` (`accounting_journal_entry`)**:
  - Double-entry header (`period` FK `PROTECT`, sequential `entry_number` per period assigned on post, `entry_date`, `description`, `entry_type`, `source_app`, `source_id`, `status` ∈ `DRAFT`/`POSTED`/`REVERSED`, `reversal_of` `OneToOneField` `PROTECT`, `total_debit`, `total_credit`, `created_by`, `posted_by`, `posted_at`, `created_at`).
  - Enforced `UNIQUE(period, entry_number)`, `ix_entry_date`, `ix_entry_source`, `ck_accounting_entry_posted_meta`, and `ck_accounting_entry_balanced` (`total_debit = total_credit > 0` when not `DRAFT`).
- **`JournalEntryLine` (`accounting_journal_entry_line`)**:
  - Individual debit/credit lines (`entry` FK `CASCADE`, `line_no`, `account` FK `PROTECT`, `description`, `debit`, `credit`) with `UNIQUE(entry, line_no)`, `ix_line_account`, non-negative check, and XOR check `(debit > 0) <> (credit > 0)`.
- **`PeriodBalance` (`accounting_period_balance`)**:
  - Account balance snapshot per closed period (`UNIQUE(account, period)`) ready for P3's monthly closing service.

#### 1.2 Migration, NIIF PYMES Seed & PostgreSQL Triggers (`backend/apps/accounting/migrations/0001_initial_and_seed.py`)
- Created all `accounting_*` tables, constraints, and indexes.
- Installed PostgreSQL immutability triggers (`fn_journal_entry_guard` / `trg_journal_entry_guard` and `fn_journal_line_guard` / `trg_journal_line_guard` from `docs/database/schema.sql`).
- Seeded all 45 NIIF PYMES accounts (Classes 1–5) from `docs/database/seed.sql` enriched with NIIF references and dynamic debit/credit rules.
- Seeded all 17 `AccountMapping` keys (`CASH`, `BANK`, `ACCOUNTS_RECEIVABLE`, `INVENTORY_VITRINA`, `INVENTORY_CABINA`, `IVA_CREDIT`, `IVA_PERCEIVED`, `ACCOUNTS_PAYABLE`, `IVA_DEBIT`, `IVA_PAYABLE`, `COST_OF_SALES`, `SERVICE_SUPPLY_COST`, `INVENTORY_SHORTAGE`, `INVENTORY_SURPLUS`, `INCOME_SERVICES`, `INCOME_PRODUCTS`, `RETAINED_EARNINGS`).
- Seeded 7 balanced November 2026 journal entries matching the SRS/mock-up scenario (Opening entry, Vitrina CCF purchase, Cabina CCF purchase, Service FCF sale, Product FCF sale + cost of sales, Cabina supply consumption, Supplier payment).

#### 1.3 Posting Engine & Exceptions (`backend/apps/accounting/exceptions.py`, `backend/apps/accounting/services/posting.py`)
Implemented the exact cross-module service contracts specified in `DB_DESIGN.md §6`:
- `LineDTO`: Transfer object supporting account instance, ID, mapping key, or numeric code.
- `get_account(key_or_identifier) -> Account`: Resolves accounts from `AccountMapping` or code/ID.
- `create_draft_entry(...)`, `update_draft_entry(...)`, `delete_draft_entry(...)`: Draft lifecycle operations enforcing `RN-02`, `RN-03`, and `RN-04`.
- `post_draft_entry(entry, *, user) -> JournalEntry`: Validates ≥ 2 lines, `Σ Debe == Σ Haber > 0` (`UnbalancedEntryError("La partida no está cuadrada (diferencia $X.XX)")`), open period (`ClosedPeriodError`), active leaf accounts (`InvalidAccountError`), assigns the next sequential `entry_number` in the period with `select_for_update()`, transitions `DRAFT -> POSTED`, and logs `POST` in `AuditLog`.
- `post_entry(...) -> JournalEntry`: Atomic two-step (`DRAFT` creation + `POSTED` transition) contract used by Sales (P4), Inventory/Purchases (P5), and Period Close (P3).
- `reverse_entry(entry, *, reason, user, reversal_date=None) -> JournalEntry`: Creates and posts a mirror-image `REVERSAL` entry (`reversal_of=entry`), marks the original `REVERSED`, and logs `REVERSE` in `AuditLog` (`RN-02`, `RF-DIA-04`).

#### 1.4 REST API Endpoints (`backend/apps/accounting/serializers.py`, `views.py`, `urls.py`, `admin.py`)
Mounted under `/api/v1/`:
- `GET/POST/PATCH/DELETE /api/v1/accounts/` (`?tree=1`, `?account_type=`, `?accepts_entries=`, `?search=`, `?period=`):
  - Computes leaf movements and rolls up balances to parent accounts by code prefix (`DB_DESIGN.md §5`), returns class filter counts (`RF-CAT-07`) and `"Estado del plan: BALANCEADO"` verification (`RF-CAT-12`).
  - Enforces cumulative decimal coding (`RF-CAT-02`), blocks child creation under accounts with movements (`RF-CAT-04`), locks `code`/`nature`/`parent` once an account has movements (`RF-CAT-05`), and soft-deactivates accounts with zero balance (`RF-CAT-06`).
- `GET/PATCH /api/v1/account-mappings/`: Lists and updates configurable event mappings (`RF-CAT-11`).
- `GET/POST/PUT/DELETE /api/v1/journal-entries/`, `GET /api/v1/journal-entries/summary/`, `POST /api/v1/journal-entries/{id}/post/`, `POST /api/v1/journal-entries/{id}/reverse/`: Full Libro Diario and manual journal entry workflow (`RF-DIA-01..07`).

---

### 2. Frontend Changes (`frontend/src/modules/accounting/` & `frontend/src/styles/main.css`)

- **`frontend/src/modules/accounting/views/CatalogoCuentasView.vue` (Vista 1 · Catálogo de cuentas)**:
  - Hierarchical tree table with collapsible parent rows, indentation by level, `VITRINA`/`CABINA` regime badges (`RF-CAT-09`), NIIF reference tags, nature badges, and rolled-up period balances.
  - Instant search + class filter chips with live counts (`Todos`, `1 · Activos`, `2 · Pasivos`, `3 · Patrimonio`, `4 · Costos / Gastos`, `5 · Ingresos`, `RF-CAT-07`).
  - `(i) Reglas` modal (`RF-CAT-08`) displaying total cargos, abonos, current balance, `"¿Cuándo se CARGA (Debe)?"`, `"¿Cuándo se ABONA (Haber)?"`, and a 1-click button to open the account in **Libro Mayor**.
  - `+ Nueva cuenta` / `Editar` modal (`RF-CAT-03`, `RF-CAT-05`) with automatic parent code/level/nature inheritance and field locks when movements exist.
  - `⚙ Mapeo de Partidas` modal (`RF-CAT-11`) for editing `AccountMapping` entries.
- **`frontend/src/modules/accounting/views/LibroDiarioView.vue` (Vista 5 · Libro diario)**:
  - 4 KPI cards (`Partidas Mayorizadas`, `Borradores en Preparación`, `Total Cargos (Debe)`, `Total Abonos (Haber)` with `"Sumas iguales"` badge).
  - Filter toolbar (`SearchInput`, `DateRangePicker`, `Origen`, `Estado`, and `Cuenta analítica`).
  - Chronological journal entry cards displaying `Partida N.º X`, date, origin & status badges, click-through link to source document (`RF-DIA-06`), reversal tags, line items with links to `/libro-mayor`, entry subtotals, and period grand totals (`RF-DIA-01`).
  - `+ Nueva partida manual` modal (`RF-DIA-02`, `RF-DIA-03`) with dynamic N-line editor, live difference calculator, **Guardar Borrador (`DRAFT`)**, and **Mayorizar Partida (`POSTED`)**.
  - Audited **Revertir partida** confirmation dialog with mandatory reason (`RF-DIA-04`).

---

### 3. Tests & Verification
- **`backend/apps/accounting/tests/test_accounting.py`**:
  - Verified 45 NIIF PYMES accounts, 17 `AccountMapping` keys, and 7 initial November 2026 journal entries.
  - Verified `post_entry()` sequential numbering and `UnbalancedEntryError` (`"La partida no está cuadrada (diferencia $1.00)"`).
  - Verified `InvalidAccountError` on parent accounts (`RN-04`) and `ClosedPeriodError` on closed periods (`"El período 10/2026 está cerrado"`).
  - Verified `reverse_entry()` mirror-image creation, `REVERSED` status transition, and double-reversal prevention.
  - Verified `/api/v1/accounts/?tree=1` hierarchy rules (`RF-CAT-04`, `RF-CAT-05`) and `/api/v1/journal-entries/` draft/post/reverse API workflow (`13 passed` total across `core` + `accounting`).


---

## [2026-11-08] Person 3 (P3 · Libro Mayor, Balance de Comprobación, Cierre Mensual & Exportes)

**Owner:** Person 3 (P3 — Reporting, Closing & Exports Lead)  
**Scope:** Complete full-stack implementation of P3 deliverables across Sprints 0, 1, 2, and 3 per [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md), [docs/SRS.md](docs/SRS.md), and [docs/database/DB_DESIGN.md](docs/database/DB_DESIGN.md).

---

### 1. Backend Changes (`backend/apps/reports/` & `backend/config/urls.py`)

#### 1.1 Reporting SQL Views Migration (`backend/apps/reports/migrations/0001_reporting_sql_views.py`)
Installed the 3 database reporting views defined in `docs/database/schema.sql`:
- `accounting_v_journal_book`: Chronological journal lines view with entry metadata and period reference.
- `accounting_v_general_ledger`: Windowed running-balance (`SUM(...) OVER (PARTITION BY account_id ORDER BY entry_date, entry_number, line_no)`) view respecting account nature (`DEBIT` vs `CREDIT`).
- `accounting_v_trial_balance`: Period-grouped debit/credit movement totals and net balances per leaf account.

#### 1.2 General Ledger, Trial Balance & NIIF Financial Statements (`backend/apps/reports/services/ledger.py`)
- **`get_account_ledger(account_identifier, period, date_from, date_to)` (`RF-MAY-01..08`)**:
  - Resolves leaf or grouping account (prefix rollup) and calculates `opening_balance` strictly prior to `date_from`, `effective_initial_balance` (handling initial `OPENING` entries), chronological movements with running `resulting_balance`, `debit_total`, `credit_total`, `closing_balance`, `variation_pct`, and `operational_inflow`.
  - Verifies period-wide trial balance equality (`trial_balance_ok`).
- **`get_simultaneous_summary(cutoff_date)` (`RF-MAY-08`)**:
  - Returns live majorized summary cards for key salon accounts (`110101`, `110102`, `110501`, `110502`, `110601`, `2107`, `210101`, `5101`, `5102`).
- **`get_trial_balance(period)` (`RF-MAY-10`)**:
  - Computes 8-column Balance de Comprobación de Sumas y Saldos (`opening_balance`, `debit_total`, `credit_total`, `closing_debit`, `closing_credit`) and verifies `Σ Debe = Σ Haber`.
- **`get_financial_statements(period)` (`RF-REP-02`, `RF-REP-03`)**:
  - Computes **Estado de Resultados Integral** (`Ingresos`, `Costos Directos / Cabina`, `Utilidad Bruta`, `Gastos Operativos`, `Utilidad Neta`) and **Balance General / Estado de Situación Financiera** (`Activos`, `Pasivos`, `Patrimonio + Resultado del Ejercicio Actual`, verifying `Activo = Pasivo + Patrimonio`).

#### 1.3 Monthly Closing & IVA Liquidation Service (`backend/apps/reports/services/closing.py`)
- **`get_close_preview(period)` (`RF-CIE-02`, `RF-CIE-03`)**:
  - Evaluates the 4 pre-close checklist rules: (1) zero `DRAFT` journal entries in the period, (2) Trial Balance squared (`Σ Debe = Σ Haber`), (3) 100% of issued sales and registered purchases posted to the journal, and (4) inventory Kárdex valuation reconciled with accounts `110501` (Vitrina) and `110502` (Cabina) (`RN-13`).
  - Computes the monthly IVA liquidation preview comparing `2107 IVA Débito Fiscal` vs `110601 IVA Crédito Fiscal` and proposes the `CLOSING` journal entry lines (`2108 IVA por Pagar` or credit remainder).
- **`close_period(period, *, user, post_iva_liquidation=True)` (`RF-CIE-03`, `RF-CIE-04`)**:
  - Atomically locks the `AccountingPeriod` row, posts the `CLOSING` IVA liquidation entry via P2's `PostingService.post_entry()`, snapshots all leaf account balances into `accounting_period_balance` (`PeriodBalance`), transitions the period to `CLOSED`, advances the active period if applicable, and logs `AuditLog.Action.CLOSE`.

#### 1.4 Official PDF & Excel Export Engine (`backend/apps/reports/services/exports.py`)
- **`export_book(book, fmt, period, account, date_from, date_to, user)` (`RF-REP-01..04`, `RN-15`)**:
  - Generates institutional PDF (`reportlab`) and formatted Excel (`openpyxl`) workbooks for `chart`, `journal`, `ledger`, `trial-balance`, `financial-statements`, `sales` (`sales-fcf`, `sales-ccf`), and `purchases`.
  - Includes legal header (`Company.legal_name`, `trade_name`, `nit`, `nrc`, active period, emission timestamp, and column totals) and records an `AuditLog.Action.EXPORT` entry on every download.

#### 1.5 REST API Endpoints (`backend/apps/reports/views.py`, `urls.py`, `backend/config/urls.py`)
Mounted under `/api/v1/` and `/api/v1/reports/`:
- `GET /api/v1/ledger/`
- `GET /api/v1/trial-balance/`
- `GET /api/v1/financial-statements/`
- `GET/POST /api/v1/periods/<int:pk>/close/`
- `GET /api/v1/exports/<str:book>/?format=pdf|xlsx` (with custom `IgnoreClientContentNegotiation` so DRF does not intercept `?format=pdf|xlsx`).

---

### 2. Frontend Changes (`frontend/src/modules/reports/`)

- **`frontend/src/modules/reports/components/PeriodCloseModal.vue` (`RF-CIE-01..05`)**:
  - Interactive modal displaying period status, the 4 pre-close validation checks (`OK` / `BLOQUEANTE`), the 4 IVA liquidation summary cards (`2107 IVA Débito`, `110601 IVA Crédito`, `2108 IVA por Pagar`, `Remanente Crédito`), the proposed closing entry preview table, **Confirmar Cierre Mensual**, and Admin-only **Reabrir Período** with mandatory audit reason.
- **`frontend/src/modules/reports/views/LibroMayorView.vue` (Vista 6 · Libro Mayor, Balance y Estados Financieros)**:
  - **Tab 1 — Libro Mayor Analítico (`RF-MAY-01..09`)**:
    - Account selector dropdown, `DateRangePicker`, and 9 quick-access account chips.
    - Selected account banner with code badge, classification, nature badge, inventory regime badge, and `"✓ Sumas iguales verificadas: OK"` indicator.
    - 4 KPI cards (`Apertura / Base Inicial`, `Total Cargos (Debe)`, `Total Abonos (Haber)`, `Saldo de Cierre Actual` with variation %).
    - Chronological movements table with sticky `SALDO INIC.` row, click-through links to `/diario?entry=<id>`, running `resulting_balance`, and `SUMAS Y SALDO DE CIERRE` footer.
    - SVG Donut chart (`Evolución de la Cuenta`) comparing initial balance, operational inflows, and outflows.
    - Clickable **Resumen Mayorizado Simultáneo** grid of key salon accounts.
  - **Tab 2 — Balance de Comprobación (`RF-MAY-10`)**:
    - 9-column trial balance table with click-through to inspect any account's analytical ledger and verified `SUMAS IGUALES` footer.
  - **Tab 3 — Estados Financieros NIIF (`RF-REP-02`, `RF-REP-03`)**:
    - Side-by-side **Estado de Resultados Integral** and **Estado de Situación Financiera (Balance General)** with `Activo = Pasivo + Patrimonio` verification badge.

---

### 3. Tests & Verification
- **`backend/apps/reports/tests/test_reports.py`**:
  - Verified `get_account_ledger` for `110101 Caja general` in Nov 2026 (`opening_balance=0.00`, `effective_initial_balance=1850.00`, `debit_total=1887.00`, `credit_total=101.70`, `closing_balance=1785.30`, 4 chronological movements).
  - Verified `get_trial_balance` and `get_financial_statements` equality (`is_balanced=True`).
  - Verified `get_close_preview` blocks closing when a `DRAFT` entry exists and turns green once resolved.
  - Verified `close_period` posts the `CLOSING` IVA liquidation entry, snapshots `PeriodBalance` rows (`110101` = `$1,785.30`, `2107` = `$0.00`), locks the period (`CLOSED`), and blocks subsequent postings (`ClosedPeriodError`).
  - Verified `/api/v1/exports/ledger/?format=pdf` and `/api/v1/exports/trial-balance/?format=xlsx` binary headers (`%PDF` and `PK`) and `EXPORT` audit logs (`18 passed` across all backend suites).


---

## [2026-11-09] Person 4 (P4 · Ventas, Servicios, Clientes & Facturación Fiscal — Vista 3: Libro de Ventas)

**Owner:** Person 4 (P4 — Sales, Services & Tax Billing Lead)  
**Scope:** Complete full-stack implementation of P4 deliverables across Sprints 0, 1, 2, and 3 per [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md), [docs/SRS.md](docs/SRS.md), and [docs/database/DB_DESIGN.md](docs/database/DB_DESIGN.md).

---

### 1. Backend Changes (`backend/apps/sales/` & `backend/config/urls.py`)

#### 1.1 Database Models & Constraints (`backend/apps/sales/models.py`)
Implemented all 5 `sales_*` tables matching `docs/database/schema.sql`:
- **`Customer` (`sales_customer`)**:
  - Supports `FINAL_CONSUMER` (`Consumidor final`) and `TAXPAYER` (`Contribuyente IVA`) with `document_type`, `document_number`, `nrc`, `economic_activity`, `is_large_taxpayer` (1% IVA retention trigger), and `is_generic`.
  - Enforces `ck_sales_customer_taxpayer_ids` (`customer_type <> 'TAXPAYER' OR (nrc IS NOT NULL AND document_number IS NOT NULL)`) and partial unique constraint `ux_customer_document` (`RF-VEN-04`).
- **`Service` (`sales_service`) & `ServiceSupply` (`sales_service_supply`)**:
  - Salon beauty service catalog (`code` unique, `name`, `category`, `price` incl. 13% IVA, `income_account` FK to `5101`) and optional Cabina supply recipes (`RF-INV-10`, `RF-VEN-13`).
- **`DocumentSeries` (`sales_document_series`)**:
  - Authorized fiscal correlative series (`doc_type` ∈ `FCF`/`CCF`/`NC`/`ND`, `prefix`, `resolution`, `authorized_from`, `authorized_to`, `next_number`, `valid_from`, `is_active`) with partial unique index `ux_series_active` (`RF-VEN-02`, `RN-09`).
- **`Sale` (`sales_sale`) & `SaleLine` (`sales_sale_line`)**:
  - Header (`series`, `doc_type`, `doc_number`, `sale_date`, `period`, `customer`, `employee`, `payment_method` ∈ `CASH`/`CARD`/`TRANSFER`/`CREDIT`, `taxable_amount`, `exempt_amount`, `non_subject_amount`, `iva_amount`, `iva_withheld`, `total`, `status` ∈ `ISSUED`/`VOIDED`, `void_reason`, `voided_at`, `related_sale`, `journal_entry`, `notes`, `created_by`).
  - Line items (`line_no`, `line_type` ∈ `SERVICE`/`PRODUCT` with `regime_badge` `CABINA`/`VITRINA`, `service`, `product_id`, `description`, `quantity`, `unit_price`, `discount`, `taxable_amount`, `iva_amount`, `total`, `unit_cost`).

#### 1.2 Migration & Initial Seed (`backend/apps/sales/migrations/0001_initial_and_seed.py`)
- Created all `sales_*` tables, indexes, and constraints.
- Seeded generic `Consumidor final` customer, named final consumers (`Ana Mejía`, `Rosa Flores`), and 2 taxpayer customers (`Eventos Glamour, S.A. de C.V.` and `Corporación Hotelera Real, S.A. de C.V.` as Gran Contribuyente).
- Seeded authorized `DocumentSeries` for `FCF` (`FCF-0016` next), `CCF` (`CCF-0001` next), `NC`, and `ND`.
- Seeded 5 salon beauty services (`SRV-001` to `SRV-005`) linked to account `5101`.
- Seeded the 4 November 2026 sales from the visual specification (`FCF-0012` `Ana Mejía` `$25.00` Cabina, `FCF-0013` `Consumidor final` `$12.00` Vitrina, `FCF-0014` `Rosa Flores` `$15.00` Cabina, `FCF-0015` `Consumidor final` `$18.00` Vitrina → `$70.00` gross, `$61.94` taxable, `$8.06` IVA) with their corresponding posted `JournalEntry` rows.
- Also updated `backend/apps/accounting/migrations/0001_initial_and_seed.py` (`params=None` in `schema_editor.execute(PG_TRIGGERS_SQL, params=None)`) so `psycopg` v3 in PostgreSQL 17 does not treat `%` inside `RAISE EXCEPTION` PL/pgSQL strings as placeholders.

#### 1.3 Tax & Sales Services (`backend/apps/sales/services/tax.py`, `backend/apps/sales/services/sales.py`)
- **`split_iva(amount, *, price_includes_iva, rate)` (`DB_DESIGN.md §6`, `RN-06`, `RF-VEN-03`)**:
  - Exact `ROUND_HALF_UP` IVA breakdown for `FCF` (`price_includes_iva=True`: `taxable = round(amount / 1.13, 2)`, `iva = amount - taxable`) and `CCF` (`price_includes_iva=False`: `iva = round(taxable * 0.13, 2)`).
- **`compute_iva_withholding(taxable_amount, *, is_large_taxpayer, doc_type)` (`RF-VEN-03`)**:
  - Calculates 1% IVA withholding on `CCF`/`NC`/`ND` issued to large taxpayers.
- **`create_sale(...)` (`RF-VEN-01..05`, `RF-VEN-11`, `RN-09`, `RN-11`)**:
  - Validates open period (`get_open_period`), enforces `TAXPAYER` with `NRC` and `NIT/DUI` on `CCF`/`NC`/`ND`, locks `DocumentSeries` with `select_for_update()` to assign gapless correlative numbers, computes line and document totals, hooks into `StockService.register_movement()` when `apps.inventory` is present, and posts the balanced `JournalEntry` (`110101`/`110102`/`110301` + `110602` vs `5101`/`5102` + `2107`, plus Cost of Sales `410101` vs `110501` for Vitrina products) in a single atomic transaction.
- **`void_sale(sale, *, reason, user)` (`RF-VEN-10`)**:
  - Validates open period, reverses the sale's `JournalEntry` via `PostingService.reverse_entry()`, marks the sale `VOIDED`, and records `AuditLog.Action.VOID`.
- **`get_sales_book(...)` (`RF-VEN-06..09`, `RF-VEN-12`, `OI-6`, `OI-7`)**:
  - Computes the 4 KPI cards, the dual **Cabina (`5101`) vs. Vitrina (`5102`)** regime breakdown cards, the interactive sales list, the daily consolidated **Libro Legal Consumidor Final (FCF)**, and the detailed **Libro Legal Contribuyentes (CCF)**.

#### 1.4 REST API Endpoints (`backend/apps/sales/serializers.py`, `views.py`, `urls.py`, `admin.py`)
Mounted under `/api/v1/` and `/api/v1/sales/`:
- `GET/POST/PATCH/DELETE /api/v1/customers/`
- `GET/POST/PATCH/DELETE /api/v1/services/`
- `GET/POST/PATCH /api/v1/document-series/`
- `GET/POST /api/v1/sales/` & `POST /api/v1/sales/<pk>/void/`
- `GET /api/v1/sales-book/`

---

### 2. Frontend Changes (`frontend/src/modules/sales/views/LibroVentasView.vue`, `frontend/src/styles/main.css`)

- **Vista 3 · Libro de Ventas (`LibroVentasView.vue`) — Aligned with Atelier Mock-up**:
  - **Top Amber Ribbon Banner (`.ds-vista-ribbon`)**: `🛡 VISTA 3 · LIBRO DE VENTAS · EJERCICIO FISCAL 2026` | `● RESPONSABLE: VÍCTOR FLORES | RÉGIMEN GENERAL IVA (13%)`.
  - **Editorial Header**: `SUBDIARIO FISCAL` pill + `Periodo contable 01/11 – 30/11`, serif `Libro de ventas` heading, `Descargar reporte mensual` (`ExportButton`), and wine `+ Registrar venta` CTA button.
  - **4 KPI Cards (`.ds-sales-kpi-grid`, `RF-VEN-08`, `OI-6`)**:
    1. `VENTAS BRUTAS TOTALES`: `$70.00` + gold pill `100% Total`
    2. `BASE IMPONIBLE GRAVADA`: `$61.94` + neutral pill `88.49%`
    3. `IVA DÉBITO FISCAL (13%)`: `$8.06` (wine text) + pink pill `Crédito por liquidar`
    4. `COMPROBANTES EMITIDOS`: `4 FCF` + gold pill `Secuencia Activa` (`FCF-0012 a FCF-0015`)
  - **Main White Card (`.ds-sales-main-card`)**:
    - Toolbar with `📅 RANGO: 01/11/26 - 05/11/26 ▾` toggle, segmented tabs (`Todos (4)`, `Servicio (2)`, `Venta de producto (2)`, `Libro FCF`, `Libro CCF`), `● Estado: Registrado y Mayorizado`, compact search `🔍 Filtrar por cliente o factura...`, and print button `🖨`.
    - Dark-header table (`.ds-dark-table`) with `FECHA` (`dd/mm/yy`), `DOCUMENTO` pill (`FCF-0012`), `CLIENTE` (bold or italic `Consumidor final`), `CONCEPTO` (`CABINA` gold tag / `VITRINA` pink tag + text), `GRAVADO ($)`, `IVA ($)` in wine, `TOTAL ($)` bold, and `✓✓ Totales del periodo (Sumas iguales comprobadas)` footer (`61.94 | 8.06 | 70.00`).
    - Explanatory Audit Note Bar (`.ds-audit-note-bar`) with `AUDITORÍA OK ●`.
  - **Bottom 2 Regime Summary Cards (`.ds-bottom-regime-grid`, `RF-VEN-09`)**:
    - `SERVICIOS EN SALÓN (CABINA)`: `$40.00 (57.1% del total)` · `2 registros · Corte & peinado, Manicura`.
    - `VENTA RETAIL DIRECTA (VITRINA)`: `$30.00 (42.9% del total)` · `2 registros · Champú nutritivo, Sérum de brillo`.
  - **Interactive Modals**: `+ Registrar Venta`, `Directorio de Clientes`, `Catálogo de Servicios`, `Detalle de Venta`, and `Anular Documento`.

---

### 3. Tests & Verification
- **`backend/apps/sales/tests/test_sales.py`**:
  - Verified `split_iva()` for `FCF` (`$25.00` → `$22.12 + $2.88`; `$12.00` → `$10.62 + $1.38`), `CCF` (`$100.00` → `$100.00 + $13.00`), and 1% large-taxpayer withholding (`$1.00`).
  - Verified seeded Nov 2026 sales book (`gross_sales = 70.00`, `taxable_base = 61.94`, `iva_debit = 8.06`, `cabina = 40.00`, `vitrina = 30.00`).
  - Verified `CCF` rejection for Final Consumer (`RF-VEN-04`), automatic double-entry + cost of sales posting (`110101`, `5101`, `5102`, `2107`, `410101`, `110501`), and `void_sale()` reversal (`22 passed` across all backend test suites).
