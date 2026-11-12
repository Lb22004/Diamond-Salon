-- =====================================================================
-- Diamond Salón — Accounting System
-- Reference PostgreSQL schema (PostgreSQL 16+)
--
-- NOTE: Django migrations are the SOURCE OF TRUTH for the real schema.
-- This file documents the target design (tables, constraints, triggers,
-- views) so every team member implements the same model. Table names
-- follow Django's "<app_label>_<model>" convention.
-- Triggers/views below should be added to Django via migrations.RunSQL.
-- =====================================================================

-- ---------------------------------------------------------------------
-- CORE (owner: P1 Platform)
-- ---------------------------------------------------------------------
CREATE TABLE core_company (
    id                   smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1),  -- single tenant
    legal_name           varchar(150) NOT NULL,
    trade_name           varchar(150) NOT NULL,
    nit                  varchar(17)  NOT NULL,
    nrc                  varchar(10)  NOT NULL,
    economic_activity    varchar(150),
    address              text,
    iva_rate             numeric(5,4) NOT NULL DEFAULT 0.1300 CHECK (iva_rate >= 0 AND iva_rate < 1),
    currency             char(3)      NOT NULL DEFAULT 'USD',
    allow_negative_stock boolean      NOT NULL DEFAULT false,
    updated_at           timestamptz  NOT NULL DEFAULT now()
);

-- Custom Django user (AUTH_USER_MODEL = 'core.User')
CREATE TABLE core_user (
    id           bigserial PRIMARY KEY,
    username     varchar(150) NOT NULL UNIQUE,
    password     varchar(128) NOT NULL,
    first_name   varchar(150) NOT NULL DEFAULT '',
    last_name    varchar(150) NOT NULL DEFAULT '',
    email        varchar(254) NOT NULL DEFAULT '',
    role         varchar(20)  NOT NULL DEFAULT 'READONLY'
                 CHECK (role IN ('ADMIN','ACCOUNTANT','AUDITOR','PURCHASING','CASHIER','READONLY')),
    is_active    boolean      NOT NULL DEFAULT true,
    is_staff     boolean      NOT NULL DEFAULT false,
    is_superuser boolean      NOT NULL DEFAULT false,
    last_login   timestamptz,
    date_joined  timestamptz  NOT NULL DEFAULT now()
);

CREATE TABLE core_employee (               -- stylists / manicurists (e.g. "Estilista Roberto G.")
    id         bigserial PRIMARY KEY,
    full_name  varchar(150) NOT NULL,
    position   varchar(20)  NOT NULL CHECK (position IN ('STYLIST','MANICURIST','RECEPTION','OTHER')),
    is_active  boolean      NOT NULL DEFAULT true
);

CREATE TABLE core_fiscal_year (
    id         bigserial PRIMARY KEY,
    year       smallint NOT NULL UNIQUE,
    start_date date     NOT NULL,
    end_date   date     NOT NULL,
    status     varchar(10) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','CLOSED')),
    CHECK (end_date > start_date)
);

CREATE TABLE core_accounting_period (
    id             bigserial PRIMARY KEY,
    fiscal_year_id bigint   NOT NULL REFERENCES core_fiscal_year(id) ON DELETE RESTRICT,
    year           smallint NOT NULL,
    month          smallint NOT NULL CHECK (month BETWEEN 1 AND 12),
    start_date     date     NOT NULL,
    end_date       date     NOT NULL,
    status         varchar(10) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','CLOSED')),
    is_active      boolean NOT NULL DEFAULT false,
    is_hidden      boolean NOT NULL DEFAULT false,
    closed_at      timestamptz,
    closed_by_id   bigint REFERENCES core_user(id) ON DELETE RESTRICT,
    UNIQUE (year, month),
    CHECK (end_date >= start_date),
    CHECK (status = 'OPEN' OR closed_at IS NOT NULL),
    CONSTRAINT ck_core_period_active_not_hidden CHECK (NOT (is_active AND is_hidden))
);

CREATE TABLE core_audit_log (
    id          bigserial PRIMARY KEY,
    user_id     bigint REFERENCES core_user(id) ON DELETE SET NULL,
    action      varchar(20)  NOT NULL CHECK (action IN ('CREATE','UPDATE','DELETE','POST','REVERSE','VOID','CLOSE','REOPEN','LOGIN','EXPORT')),
    table_name  varchar(80)  NOT NULL,
    record_id   bigint,
    before_data jsonb,
    after_data  jsonb,
    ip_address  inet,
    created_at  timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_table_record ON core_audit_log (table_name, record_id);
CREATE INDEX ix_audit_created ON core_audit_log (created_at);

-- ---------------------------------------------------------------------
-- ACCOUNTING (owner: P2 Accounting Core; ledger/closing views: P3)
-- ---------------------------------------------------------------------
CREATE TABLE accounting_account (
    id              bigserial PRIMARY KEY,
    code            varchar(20)  NOT NULL UNIQUE CHECK (code ~ '^[0-9]+$'),
    name            varchar(150) NOT NULL,
    parent_id       bigint REFERENCES accounting_account(id) ON DELETE RESTRICT,
    level           smallint     NOT NULL CHECK (level BETWEEN 1 AND 6),  -- 1 Clase, 2 Grupo, 3 Cuenta mayor, 4 Subcuenta...
    account_type    varchar(10)  NOT NULL
                    CHECK (account_type IN ('ASSET','LIABILITY','EQUITY','COST','EXPENSE','INCOME','CLOSING')),
    nature          varchar(6)   NOT NULL CHECK (nature IN ('DEBIT','CREDIT')),
    classification  varchar(40),            -- display label: 'Subcuenta Retail', 'Obligación Fiscal'...
    accepts_entries boolean      NOT NULL DEFAULT false,  -- only leaf (analytic) accounts take movements
    inventory_type  varchar(10)  CHECK (inventory_type IN ('VITRINA','CABINA')),
    niif_reference  varchar(60),            -- e.g. 'NIIF PYMES Secc. 13'
    debit_rule      text,                   -- "se carga cuando..."
    credit_rule     text,                   -- "se abona cuando..."
    is_active       boolean      NOT NULL DEFAULT true,
    created_at      timestamptz  NOT NULL DEFAULT now(),
    updated_at      timestamptz  NOT NULL DEFAULT now(),
    CHECK ((level = 1) = (parent_id IS NULL))
);
CREATE INDEX ix_account_parent ON accounting_account (parent_id);
CREATE INDEX ix_account_code_prefix ON accounting_account (code varchar_pattern_ops);

-- Configurable posting rules: business events -> accounts (no hard-coded codes in Python)
CREATE TABLE accounting_account_mapping (
    key         varchar(40) PRIMARY KEY,
    account_id  bigint NOT NULL REFERENCES accounting_account(id) ON DELETE RESTRICT,
    description varchar(200) NOT NULL
);

CREATE TABLE accounting_journal_entry (       -- "Partida" (Libro diario)
    id             bigserial PRIMARY KEY,
    period_id      bigint NOT NULL REFERENCES core_accounting_period(id) ON DELETE RESTRICT,
    entry_number   integer,                   -- assigned when posted, sequential per period ("Part. N.º 5")
    entry_date     date   NOT NULL,
    description    text   NOT NULL,
    entry_type     varchar(12) NOT NULL
                   CHECK (entry_type IN ('OPENING','MANUAL','SALE','PURCHASE','PAYMENT','INVENTORY','ADJUSTMENT','CLOSING','REVERSAL')),
    source_app     varchar(40),               -- e.g. 'sales.sale', 'purchases.purchase'
    source_id      bigint,
    status         varchar(10) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','POSTED','REVERSED')),
    reversal_of_id bigint UNIQUE REFERENCES accounting_journal_entry(id) ON DELETE RESTRICT,
    total_debit    numeric(14,2) NOT NULL DEFAULT 0,
    total_credit   numeric(14,2) NOT NULL DEFAULT 0,
    created_by_id  bigint NOT NULL REFERENCES core_user(id) ON DELETE RESTRICT,
    posted_by_id   bigint REFERENCES core_user(id) ON DELETE RESTRICT,
    posted_at      timestamptz,
    created_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (period_id, entry_number),
    CHECK (status = 'DRAFT' OR (entry_number IS NOT NULL AND posted_at IS NOT NULL)),
    CHECK (status = 'DRAFT' OR (total_debit = total_credit AND total_debit > 0))
);
CREATE INDEX ix_entry_date ON accounting_journal_entry (entry_date, entry_number);
CREATE INDEX ix_entry_source ON accounting_journal_entry (source_app, source_id);

CREATE TABLE accounting_journal_entry_line (  -- "Movimiento" (Debe / Haber)
    id          bigserial PRIMARY KEY,
    entry_id    bigint   NOT NULL REFERENCES accounting_journal_entry(id) ON DELETE CASCADE,
    line_no     smallint NOT NULL,
    account_id  bigint   NOT NULL REFERENCES accounting_account(id) ON DELETE RESTRICT,
    description varchar(255),
    debit       numeric(14,2) NOT NULL DEFAULT 0,
    credit      numeric(14,2) NOT NULL DEFAULT 0,
    UNIQUE (entry_id, line_no),
    CHECK (debit >= 0 AND credit >= 0),
    CHECK ((debit > 0) <> (credit > 0))       -- exactly one side per line
);
CREATE INDEX ix_line_account ON accounting_journal_entry_line (account_id);

-- Snapshot of balances per account and period, written when a period is closed.
CREATE TABLE accounting_period_balance (
    id              bigserial PRIMARY KEY,
    account_id      bigint NOT NULL REFERENCES accounting_account(id) ON DELETE RESTRICT,
    period_id       bigint NOT NULL REFERENCES core_accounting_period(id) ON DELETE RESTRICT,
    opening_balance numeric(14,2) NOT NULL DEFAULT 0,
    debit_total     numeric(14,2) NOT NULL DEFAULT 0,
    credit_total    numeric(14,2) NOT NULL DEFAULT 0,
    closing_balance numeric(14,2) NOT NULL DEFAULT 0,
    UNIQUE (account_id, period_id)
);

-- ---------------------------------------------------------------------
-- INVENTORY (owner: P5 Inventory & Purchases)
-- ---------------------------------------------------------------------
CREATE TABLE inventory_category (
    id             bigserial PRIMARY KEY,
    name           varchar(80) NOT NULL,
    inventory_type varchar(10) NOT NULL CHECK (inventory_type IN ('VITRINA','CABINA')),
    UNIQUE (name, inventory_type)
);

CREATE TABLE inventory_location (            -- Vitrina, Cabina 1, Cabina 2, General...
    id            bigserial PRIMARY KEY,
    code          varchar(20) NOT NULL UNIQUE,
    name          varchar(80) NOT NULL,
    location_type varchar(10) NOT NULL CHECK (location_type IN ('VITRINA','CABINA','WAREHOUSE')),
    is_active     boolean     NOT NULL DEFAULT true
);

CREATE TABLE purchases_supplier (            -- defined here because products reference it
    id                 bigserial PRIMARY KEY,
    name               varchar(150) NOT NULL,
    trade_name         varchar(150),
    nit                varchar(17)  NOT NULL UNIQUE,
    nrc                varchar(10),
    taxpayer_category  varchar(10)  NOT NULL DEFAULT 'MEDIUM'
                       CHECK (taxpayer_category IN ('SMALL','MEDIUM','LARGE','EXCLUDED')),  -- LARGE = gran contribuyente
    brands_description varchar(200),         -- "L'Oréal, Kérastase"
    contact_name       varchar(120),
    phone              varchar(30),
    email              varchar(254),
    address            text,
    is_active          boolean NOT NULL DEFAULT true,
    created_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE inventory_product (
    id                  bigserial PRIMARY KEY,
    sku                 varchar(30)  NOT NULL UNIQUE,
    barcode             varchar(50)  UNIQUE,
    name                varchar(150) NOT NULL,
    brand               varchar(80),
    presentation        varchar(80),            -- "300ml", "Garrafa 1000ml"
    category_id         bigint REFERENCES inventory_category(id) ON DELETE SET NULL,
    inventory_type      varchar(10)  NOT NULL CHECK (inventory_type IN ('VITRINA','CABINA')),
    unit_of_measure     varchar(10)  NOT NULL DEFAULT 'UNIT'
                        CHECK (unit_of_measure IN ('UNIT','LITER','MILLILITER','GRAM','KILOGRAM','PACKAGE')),
    account_id          bigint       NOT NULL REFERENCES accounting_account(id) ON DELETE RESTRICT, -- 110501 / 110502
    sale_price          numeric(12,2) CHECK (sale_price >= 0),  -- PVP incl. IVA (vitrina only)
    average_cost        numeric(14,4) NOT NULL DEFAULT 0 CHECK (average_cost >= 0),
    min_stock           numeric(12,3) NOT NULL DEFAULT 0 CHECK (min_stock >= 0),
    default_supplier_id bigint REFERENCES purchases_supplier(id) ON DELETE SET NULL,
    is_active           boolean NOT NULL DEFAULT true,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),
    CHECK (inventory_type = 'CABINA' OR sale_price IS NOT NULL),  -- vitrina products must have a PVP
    CHECK (inventory_type = 'VITRINA' OR sale_price IS NULL)      -- cabina supplies are never sold
);

CREATE TABLE inventory_stock (               -- current quantity per product & location (cache maintained by InventoryService)
    product_id  bigint NOT NULL REFERENCES inventory_product(id) ON DELETE RESTRICT,
    location_id bigint NOT NULL REFERENCES inventory_location(id) ON DELETE RESTRICT,
    quantity    numeric(12,3) NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    PRIMARY KEY (product_id, location_id)
);

CREATE TABLE inventory_adjustment (          -- header for physical-count adjustments ("Ajuste de stock")
    id               bigserial PRIMARY KEY,
    adjustment_date  date NOT NULL,
    reason           varchar(20) NOT NULL CHECK (reason IN ('PHYSICAL_COUNT','DAMAGE','EXPIRED','THEFT','OTHER')),
    notes            text,
    journal_entry_id bigint REFERENCES accounting_journal_entry(id) ON DELETE RESTRICT,
    created_by_id    bigint NOT NULL REFERENCES core_user(id) ON DELETE RESTRICT,
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE inventory_consumption (         -- cabina supplies used in services
    id               bigserial PRIMARY KEY,
    consumption_date date NOT NULL,
    location_id      bigint NOT NULL REFERENCES inventory_location(id) ON DELETE RESTRICT,
    employee_id      bigint REFERENCES core_employee(id) ON DELETE SET NULL,
    sale_id          bigint,                 -- FK to sales_sale added below (optional link to the service sold)
    notes            text,
    journal_entry_id bigint REFERENCES accounting_journal_entry(id) ON DELETE RESTRICT,
    created_by_id    bigint NOT NULL REFERENCES core_user(id) ON DELETE RESTRICT,
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE inventory_movement (            -- Kardex: every stock change, immutable
    id               bigserial PRIMARY KEY,
    product_id       bigint NOT NULL REFERENCES inventory_product(id) ON DELETE RESTRICT,
    location_id      bigint NOT NULL REFERENCES inventory_location(id) ON DELETE RESTRICT,
    movement_date    date   NOT NULL,
    movement_type    varchar(15) NOT NULL
                     CHECK (movement_type IN ('OPENING','PURCHASE','SALE','CONSUMPTION','ADJUSTMENT_IN','ADJUSTMENT_OUT',
                                              'TRANSFER_IN','TRANSFER_OUT','RETURN_IN','RETURN_OUT')),
    direction        smallint NOT NULL CHECK (direction IN (1,-1)),
    quantity         numeric(12,3) NOT NULL CHECK (quantity > 0),
    unit_cost        numeric(14,4) NOT NULL CHECK (unit_cost >= 0),
    total_cost       numeric(14,2) NOT NULL CHECK (total_cost >= 0),
    balance_quantity numeric(12,3) NOT NULL,  -- product stock after movement (all locations)
    balance_avg_cost numeric(14,4) NOT NULL,  -- weighted average cost after movement
    source_app       varchar(40),             -- 'purchases.purchase', 'sales.sale', 'inventory.adjustment', ...
    source_id        bigint,
    journal_entry_id bigint REFERENCES accounting_journal_entry(id) ON DELETE RESTRICT,
    notes            varchar(255),
    created_by_id    bigint NOT NULL REFERENCES core_user(id) ON DELETE RESTRICT,
    created_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_movement_product_date ON inventory_movement (product_id, movement_date, id);
CREATE INDEX ix_movement_source ON inventory_movement (source_app, source_id);

-- ---------------------------------------------------------------------
-- SALES (owner: P4 Sales & Services)
-- ---------------------------------------------------------------------
CREATE TABLE sales_customer (
    id                bigserial PRIMARY KEY,
    name              varchar(150) NOT NULL,
    customer_type     varchar(15)  NOT NULL CHECK (customer_type IN ('FINAL_CONSUMER','TAXPAYER')),
    document_type     varchar(10)  CHECK (document_type IN ('DUI','NIT','PASSPORT','OTHER')),
    document_number   varchar(20),
    nrc               varchar(10),
    economic_activity varchar(150),
    is_large_taxpayer boolean NOT NULL DEFAULT false,   -- gran contribuyente -> withholds 1% IVA
    email             varchar(254),
    phone             varchar(30),
    address           text,
    is_generic        boolean NOT NULL DEFAULT false,   -- "Consumidor final"
    is_active         boolean NOT NULL DEFAULT true,
    created_at        timestamptz NOT NULL DEFAULT now(),
    CHECK (customer_type <> 'TAXPAYER' OR (nrc IS NOT NULL AND document_number IS NOT NULL))
);
CREATE UNIQUE INDEX ux_customer_document ON sales_customer (document_type, document_number) WHERE document_number IS NOT NULL;

CREATE TABLE sales_service (                  -- beauty services catalog
    id                bigserial PRIMARY KEY,
    code              varchar(20)  NOT NULL UNIQUE,
    name              varchar(150) NOT NULL,
    category          varchar(20)  NOT NULL CHECK (category IN ('HAIRCUT','STYLING','COLOR','TREATMENT','NAILS','OTHER')),
    price             numeric(12,2) NOT NULL CHECK (price >= 0),  -- incl. IVA
    income_account_id bigint NOT NULL REFERENCES accounting_account(id) ON DELETE RESTRICT,  -- 5101
    is_active         boolean NOT NULL DEFAULT true
);

CREATE TABLE sales_service_supply (           -- optional "recipe": supplies consumed per service
    id         bigserial PRIMARY KEY,
    service_id bigint NOT NULL REFERENCES sales_service(id) ON DELETE CASCADE,
    product_id bigint NOT NULL REFERENCES inventory_product(id) ON DELETE RESTRICT,
    quantity   numeric(12,3) NOT NULL CHECK (quantity > 0),
    UNIQUE (service_id, product_id)
);

CREATE TABLE sales_document_series (          -- authorized correlatives (FCF-0012...)
    id              bigserial PRIMARY KEY,
    doc_type        varchar(3)  NOT NULL CHECK (doc_type IN ('FCF','CCF','NC','ND')),
    prefix          varchar(10) NOT NULL,
    resolution      varchar(60),
    authorized_from integer NOT NULL CHECK (authorized_from > 0),
    authorized_to   integer NOT NULL,
    next_number     integer NOT NULL,
    valid_from      date    NOT NULL,
    is_active       boolean NOT NULL DEFAULT true,
    CHECK (authorized_to >= authorized_from),
    CHECK (next_number BETWEEN authorized_from AND authorized_to + 1)
);
CREATE UNIQUE INDEX ux_series_active ON sales_document_series (doc_type) WHERE is_active;

CREATE TABLE sales_sale (
    id                 bigserial PRIMARY KEY,
    series_id          bigint NOT NULL REFERENCES sales_document_series(id) ON DELETE RESTRICT,
    doc_type           varchar(3)  NOT NULL CHECK (doc_type IN ('FCF','CCF','NC','ND')),
    doc_number         varchar(20) NOT NULL,
    sale_date          date   NOT NULL,
    period_id          bigint NOT NULL REFERENCES core_accounting_period(id) ON DELETE RESTRICT,
    customer_id        bigint NOT NULL REFERENCES sales_customer(id) ON DELETE RESTRICT,
    employee_id        bigint REFERENCES core_employee(id) ON DELETE SET NULL,
    payment_method     varchar(10) NOT NULL CHECK (payment_method IN ('CASH','CARD','TRANSFER','CREDIT')),
    taxable_amount     numeric(14,2) NOT NULL DEFAULT 0 CHECK (taxable_amount >= 0),  -- base gravada
    exempt_amount      numeric(14,2) NOT NULL DEFAULT 0 CHECK (exempt_amount >= 0),
    non_subject_amount numeric(14,2) NOT NULL DEFAULT 0 CHECK (non_subject_amount >= 0),
    iva_amount         numeric(14,2) NOT NULL DEFAULT 0 CHECK (iva_amount >= 0),       -- IVA débito fiscal
    iva_withheld       numeric(14,2) NOT NULL DEFAULT 0 CHECK (iva_withheld >= 0),     -- 1% retention by large taxpayer
    total              numeric(14,2) NOT NULL CHECK (total >= 0),
    status             varchar(10) NOT NULL DEFAULT 'ISSUED' CHECK (status IN ('ISSUED','VOIDED')),
    void_reason        varchar(255),
    voided_at          timestamptz,
    related_sale_id    bigint REFERENCES sales_sale(id) ON DELETE RESTRICT,  -- for NC / ND
    journal_entry_id   bigint REFERENCES accounting_journal_entry(id) ON DELETE RESTRICT,
    notes              text,
    created_by_id      bigint NOT NULL REFERENCES core_user(id) ON DELETE RESTRICT,
    created_at         timestamptz NOT NULL DEFAULT now(),
    UNIQUE (doc_type, doc_number),
    CHECK (total = taxable_amount + exempt_amount + non_subject_amount + iva_amount - iva_withheld),
    CHECK (status = 'ISSUED' OR (void_reason IS NOT NULL AND voided_at IS NOT NULL)),
    CHECK (doc_type IN ('FCF','CCF') OR related_sale_id IS NOT NULL)
);
CREATE INDEX ix_sale_date ON sales_sale (sale_date);
CREATE INDEX ix_sale_period ON sales_sale (period_id, doc_type);

CREATE TABLE sales_sale_line (
    id             bigserial PRIMARY KEY,
    sale_id        bigint   NOT NULL REFERENCES sales_sale(id) ON DELETE CASCADE,
    line_no        smallint NOT NULL,
    line_type      varchar(10) NOT NULL CHECK (line_type IN ('SERVICE','PRODUCT')),  -- CABINA vs VITRINA badge
    service_id     bigint REFERENCES sales_service(id) ON DELETE RESTRICT,
    product_id     bigint REFERENCES inventory_product(id) ON DELETE RESTRICT,
    description    varchar(255) NOT NULL,
    quantity       numeric(12,3) NOT NULL CHECK (quantity > 0),
    unit_price     numeric(12,2) NOT NULL CHECK (unit_price >= 0),  -- incl. IVA
    discount       numeric(12,2) NOT NULL DEFAULT 0 CHECK (discount >= 0),
    taxable_amount numeric(14,2) NOT NULL CHECK (taxable_amount >= 0),
    iva_amount     numeric(14,2) NOT NULL CHECK (iva_amount >= 0),
    total          numeric(14,2) NOT NULL CHECK (total >= 0),
    unit_cost      numeric(14,4),             -- weighted avg cost at sale time (products only)
    UNIQUE (sale_id, line_no),
    CHECK ((line_type = 'SERVICE' AND service_id IS NOT NULL AND product_id IS NULL)
        OR (line_type = 'PRODUCT' AND product_id IS NOT NULL AND service_id IS NULL)),
    CHECK (total = taxable_amount + iva_amount)
);

ALTER TABLE inventory_consumption
    ADD CONSTRAINT fk_consumption_sale FOREIGN KEY (sale_id) REFERENCES sales_sale(id) ON DELETE SET NULL;

-- ---------------------------------------------------------------------
-- PURCHASES (owner: P5 Inventory & Purchases)
-- ---------------------------------------------------------------------
CREATE TABLE purchases_purchase (
    id                 bigserial PRIMARY KEY,
    supplier_id        bigint NOT NULL REFERENCES purchases_supplier(id) ON DELETE RESTRICT,
    doc_type           varchar(16) NOT NULL
                       CHECK (doc_type IN ('CCF','INVOICE','NC','ND','IMPORT','EXCLUDED_SUBJECT')),
    doc_number         varchar(30) NOT NULL,
    doc_date           date   NOT NULL,
    period_id          bigint NOT NULL REFERENCES core_accounting_period(id) ON DELETE RESTRICT,
    destination        varchar(10) NOT NULL CHECK (destination IN ('VITRINA','CABINA','MIXED','EXPENSE')),
    taxable_amount     numeric(14,2) NOT NULL DEFAULT 0 CHECK (taxable_amount >= 0),
    exempt_amount      numeric(14,2) NOT NULL DEFAULT 0 CHECK (exempt_amount >= 0),
    iva_credit         numeric(14,2) NOT NULL DEFAULT 0 CHECK (iva_credit >= 0),     -- IVA crédito fiscal
    iva_perceived      numeric(14,2) NOT NULL DEFAULT 0 CHECK (iva_perceived >= 0),  -- 1% perception (large supplier)
    total              numeric(14,2) NOT NULL CHECK (total >= 0),
    payment_condition  varchar(6)  NOT NULL CHECK (payment_condition IN ('CASH','CREDIT')),
    due_date           date,
    amount_paid        numeric(14,2) NOT NULL DEFAULT 0 CHECK (amount_paid >= 0),
    payment_status     varchar(8)  NOT NULL DEFAULT 'PENDING' CHECK (payment_status IN ('PENDING','PARTIAL','PAID')),
    status             varchar(10) NOT NULL DEFAULT 'REGISTERED' CHECK (status IN ('REGISTERED','VOIDED')),
    void_reason        varchar(255),
    journal_entry_id   bigint REFERENCES accounting_journal_entry(id) ON DELETE RESTRICT,
    notes              text,
    created_by_id      bigint NOT NULL REFERENCES core_user(id) ON DELETE RESTRICT,
    created_at         timestamptz NOT NULL DEFAULT now(),
    UNIQUE (supplier_id, doc_type, doc_number),
    CHECK (total = taxable_amount + exempt_amount + iva_credit + iva_perceived),
    CHECK (amount_paid <= total),
    CHECK (payment_condition = 'CASH' OR due_date IS NOT NULL)
);
CREATE INDEX ix_purchase_date ON purchases_purchase (doc_date);
CREATE INDEX ix_purchase_period ON purchases_purchase (period_id);

CREATE TABLE purchases_purchase_line (
    id                 bigserial PRIMARY KEY,
    purchase_id        bigint   NOT NULL REFERENCES purchases_purchase(id) ON DELETE CASCADE,
    line_no            smallint NOT NULL,
    product_id         bigint REFERENCES inventory_product(id) ON DELETE RESTRICT,
    expense_account_id bigint REFERENCES accounting_account(id) ON DELETE RESTRICT,  -- non-inventory purchases
    location_id        bigint REFERENCES inventory_location(id) ON DELETE RESTRICT,  -- where stock enters
    description        varchar(255) NOT NULL,
    quantity           numeric(12,3) NOT NULL CHECK (quantity > 0),
    unit_cost          numeric(14,4) NOT NULL CHECK (unit_cost >= 0),  -- excl. IVA
    taxable_amount     numeric(14,2) NOT NULL CHECK (taxable_amount >= 0),
    iva_amount         numeric(14,2) NOT NULL CHECK (iva_amount >= 0),
    UNIQUE (purchase_id, line_no),
    CHECK ((product_id IS NOT NULL) <> (expense_account_id IS NOT NULL)),
    CHECK (product_id IS NULL OR location_id IS NOT NULL)
);

CREATE TABLE purchases_supplier_payment (
    id               bigserial PRIMARY KEY,
    purchase_id      bigint NOT NULL REFERENCES purchases_purchase(id) ON DELETE RESTRICT,
    payment_date     date   NOT NULL,
    amount           numeric(14,2) NOT NULL CHECK (amount > 0),
    payment_method   varchar(10) NOT NULL CHECK (payment_method IN ('CASH','TRANSFER','CHECK','CARD')),
    reference        varchar(60),             -- "Recibo provisional N.º 8820"
    cash_account_id  bigint NOT NULL REFERENCES accounting_account(id) ON DELETE RESTRICT,  -- 110101 / 110102
    journal_entry_id bigint REFERENCES accounting_journal_entry(id) ON DELETE RESTRICT,
    created_by_id    bigint NOT NULL REFERENCES core_user(id) ON DELETE RESTRICT,
    created_at       timestamptz NOT NULL DEFAULT now()
);

-- =====================================================================
-- INTEGRITY TRIGGERS (defense in depth — services also validate)
-- =====================================================================

-- 1) Entries are always created as DRAFT; posted entries are immutable
--    except POSTED -> REVERSED; only drafts can be deleted.
CREATE OR REPLACE FUNCTION fn_journal_entry_guard() RETURNS trigger AS $$
DECLARE
    v_debit  numeric(14,2);
    v_credit numeric(14,2);
    v_period_status varchar(10);
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.status <> 'DRAFT' THEN
            RAISE EXCEPTION 'Journal entries must be created as DRAFT';
        END IF;
        RETURN NEW;
    END IF;

    IF TG_OP = 'DELETE' THEN
        IF OLD.status <> 'DRAFT' THEN
            RAISE EXCEPTION 'Posted journal entry % cannot be deleted; reverse it instead', OLD.id;
        END IF;
        RETURN OLD;
    END IF;

    -- UPDATE
    IF OLD.status = 'REVERSED' THEN
        RAISE EXCEPTION 'Reversed journal entry % is immutable', OLD.id;
    END IF;
    IF OLD.status = 'POSTED' THEN
        IF NEW.status <> 'REVERSED'
           OR (to_jsonb(NEW) - 'status') <> (to_jsonb(OLD) - 'status') THEN
            RAISE EXCEPTION 'Posted journal entry % is immutable (only POSTED -> REVERSED allowed)', OLD.id;
        END IF;
        RETURN NEW;
    END IF;

    -- DRAFT -> POSTED: validate double entry and open period
    IF NEW.status = 'POSTED' THEN
        SELECT status INTO v_period_status FROM core_accounting_period WHERE id = NEW.period_id;
        IF v_period_status <> 'OPEN' THEN
            RAISE EXCEPTION 'Accounting period % is closed', NEW.period_id;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM core_accounting_period p
                       WHERE p.id = NEW.period_id AND NEW.entry_date BETWEEN p.start_date AND p.end_date) THEN
            RAISE EXCEPTION 'Entry date % is outside its accounting period', NEW.entry_date;
        END IF;
        SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0)
          INTO v_debit, v_credit
          FROM accounting_journal_entry_line WHERE entry_id = NEW.id;
        IF v_debit <> v_credit OR v_debit = 0
           OR (SELECT COUNT(*) FROM accounting_journal_entry_line WHERE entry_id = NEW.id) < 2 THEN
            RAISE EXCEPTION 'Unbalanced entry %: debit % <> credit %', NEW.id, v_debit, v_credit;
        END IF;
        NEW.total_debit  := v_debit;
        NEW.total_credit := v_credit;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_journal_entry_guard
    BEFORE INSERT OR UPDATE OR DELETE ON accounting_journal_entry
    FOR EACH ROW EXECUTE FUNCTION fn_journal_entry_guard();

-- 2) Lines can only change while the entry is DRAFT, and only on leaf, active accounts.
CREATE OR REPLACE FUNCTION fn_journal_line_guard() RETURNS trigger AS $$
DECLARE
    v_entry_id bigint := COALESCE(NEW.entry_id, OLD.entry_id);
    v_status   varchar(10);
BEGIN
    SELECT status INTO v_status FROM accounting_journal_entry WHERE id = v_entry_id;
    IF v_status IS NOT NULL AND v_status <> 'DRAFT' THEN
        RAISE EXCEPTION 'Lines of posted entry % cannot be modified', v_entry_id;
    END IF;
    IF TG_OP IN ('INSERT','UPDATE') THEN
        IF NOT EXISTS (SELECT 1 FROM accounting_account
                       WHERE id = NEW.account_id AND accepts_entries AND is_active) THEN
            RAISE EXCEPTION 'Account % does not accept entries (not a leaf or inactive)', NEW.account_id;
        END IF;
        RETURN NEW;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_journal_line_guard
    BEFORE INSERT OR UPDATE OR DELETE ON accounting_journal_entry_line
    FOR EACH ROW EXECUTE FUNCTION fn_journal_line_guard();

-- 3) Inventory movements are append-only (corrections = new movements).
CREATE OR REPLACE FUNCTION fn_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_inventory_movement_append_only
    BEFORE UPDATE OR DELETE ON inventory_movement
    FOR EACH ROW EXECUTE FUNCTION fn_append_only();

-- =====================================================================
-- REPORTING VIEWS (owner: P3 Ledger & Reports)
-- =====================================================================

-- Libro diario: posted entries with their lines in chronological order
CREATE VIEW accounting_v_journal_book AS
SELECT e.id AS entry_id, e.entry_number, e.entry_date, e.period_id, e.entry_type, e.status,
       e.description AS entry_description, l.line_no, a.code AS account_code, a.name AS account_name,
       l.description AS line_description, l.debit, l.credit
FROM accounting_journal_entry e
JOIN accounting_journal_entry_line l ON l.entry_id = e.id
JOIN accounting_account a ON a.id = l.account_id
WHERE e.status IN ('POSTED','REVERSED');

-- Libro mayor: movements per account with running balance signed by nature
CREATE VIEW accounting_v_general_ledger AS
SELECT l.account_id, a.code AS account_code, a.name AS account_name, a.nature,
       e.id AS entry_id, e.entry_number, e.entry_date, e.period_id, e.entry_type,
       COALESCE(l.description, e.description) AS concept, l.debit, l.credit,
       SUM(CASE WHEN a.nature = 'DEBIT' THEN l.debit - l.credit ELSE l.credit - l.debit END)
           OVER (PARTITION BY l.account_id
                 ORDER BY e.entry_date, e.entry_number, l.line_no
                 ROWS UNBOUNDED PRECEDING) AS running_balance
FROM accounting_journal_entry_line l
JOIN accounting_journal_entry e ON e.id = l.entry_id
JOIN accounting_account a ON a.id = l.account_id
WHERE e.status IN ('POSTED','REVERSED');

-- Balance de comprobación per period (leaf accounts)
CREATE VIEW accounting_v_trial_balance AS
SELECT e.period_id, a.id AS account_id, a.code, a.name, a.nature,
       SUM(l.debit) AS debit_total, SUM(l.credit) AS credit_total,
       SUM(CASE WHEN a.nature = 'DEBIT' THEN l.debit - l.credit ELSE l.credit - l.debit END) AS net_movement
FROM accounting_journal_entry_line l
JOIN accounting_journal_entry e ON e.id = l.entry_id
JOIN accounting_account a ON a.id = l.account_id
WHERE e.status IN ('POSTED','REVERSED')
GROUP BY e.period_id, a.id, a.code, a.name, a.nature;

-- Libro de ventas (both consumidor final and contribuyentes; filter by doc_type)
CREATE VIEW sales_v_sales_book AS
SELECT s.id AS sale_id, s.sale_date, s.period_id, s.doc_type, s.doc_number,
       c.name AS customer_name, c.nrc AS customer_nrc, c.document_number AS customer_document,
       CASE WHEN bool_and(sl.line_type = 'SERVICE') THEN 'SERVICE'
            WHEN bool_and(sl.line_type = 'PRODUCT') THEN 'PRODUCT' ELSE 'MIXED' END AS sale_category,
       string_agg(sl.description, ', ' ORDER BY sl.line_no) AS concept,
       s.taxable_amount, s.exempt_amount, s.non_subject_amount, s.iva_amount, s.iva_withheld, s.total, s.status
FROM sales_sale s
JOIN sales_customer c ON c.id = s.customer_id
JOIN sales_sale_line sl ON sl.sale_id = s.id
GROUP BY s.id, c.id;

-- Libro de compras
CREATE VIEW purchases_v_purchase_book AS
SELECT p.id AS purchase_id, p.doc_date, p.period_id, p.doc_type, p.doc_number,
       sp.name AS supplier_name, sp.nrc AS supplier_nrc, sp.nit AS supplier_nit, p.destination,
       p.taxable_amount, p.exempt_amount, p.iva_credit, p.iva_perceived, p.total, p.payment_status, p.status
FROM purchases_purchase p
JOIN purchases_supplier sp ON sp.id = p.supplier_id;
