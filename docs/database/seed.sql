-- =====================================================================
-- Diamond Salón — reference seed data (run after schema.sql)
-- In Django, port this to a data migration or `manage.py loaddata`.
-- =====================================================================

INSERT INTO core_company (legal_name, trade_name, nit, nrc, economic_activity, iva_rate)
VALUES ('Diamond Salón, S.A. de C.V.', 'Diamond Salón Atelier', '0614-000000-000-0', '000000-0',
        'Peluquería y otros tratamientos de belleza', 0.1300);

INSERT INTO core_user (username, password, first_name, last_name, role, is_staff, is_superuser)
VALUES ('system', '!', 'Sistema', '', 'ADMIN', false, false);

INSERT INTO core_fiscal_year (year, start_date, end_date) VALUES (2026, '2026-01-01', '2026-12-31');
INSERT INTO core_accounting_period (fiscal_year_id, year, month, start_date, end_date)
SELECT fy.id, 2026, m, make_date(2026, m, 1), (make_date(2026, m, 1) + interval '1 month - 1 day')::date
FROM core_fiscal_year fy, generate_series(1, 12) AS m
WHERE fy.year = 2026;

-- ---------------------------------------------------------------------
-- Proposed chart of accounts (Salvadoran structure: 1 Activo, 2 Pasivo,
-- 3 Patrimonio, 4 Costos y gastos, 5 Ingresos). Codes used in the
-- mock-ups (110101, 110501, 110502, 2107, 5101, 5102) are preserved.
-- level: 1 Clase · 2 Grupo · 3 Cuenta mayor · 4 Subcuenta
-- ---------------------------------------------------------------------
CREATE TEMP TABLE seed_account (
    code text, name text, parent text, level int, type text, nature text,
    classification text, leaf boolean, inv text
);
INSERT INTO seed_account VALUES
 ('1',      'ACTIVO',                                  NULL,   1, 'ASSET',     'DEBIT',  'Clase',               false, NULL),
 ('11',     'Activo corriente',                        '1',    2, 'ASSET',     'DEBIT',  'Grupo',               false, NULL),
 ('1101',   'Efectivo y equivalentes',                 '11',   3, 'ASSET',     'DEBIT',  'Cuenta mayor',        false, NULL),
 ('110101', 'Caja general',                            '1101', 4, 'ASSET',     'DEBIT',  'Subcuenta analítica', true,  NULL),
 ('110102', 'Bancos',                                  '1101', 4, 'ASSET',     'DEBIT',  'Subcuenta analítica', true,  NULL),
 ('1103',   'Cuentas por cobrar',                      '11',   3, 'ASSET',     'DEBIT',  'Cuenta mayor',        false, NULL),
 ('110301', 'Clientes',                                '1103', 4, 'ASSET',     'DEBIT',  'Subcuenta analítica', true,  NULL),
 ('1105',   'Inventarios',                             '11',   3, 'ASSET',     'DEBIT',  'Cuenta mayor',        false, NULL),
 ('110501', 'Mercadería para la venta (vitrina)',      '1105', 4, 'ASSET',     'DEBIT',  'Subcuenta retail',    true,  'VITRINA'),
 ('110502', 'Insumos para servicios (cabina)',         '1105', 4, 'ASSET',     'DEBIT',  'Subcuenta operativa', true,  'CABINA'),
 ('1106',   'IVA crédito fiscal',                      '11',   3, 'ASSET',     'DEBIT',  'Cuenta mayor',        false, NULL),
 ('110601', 'IVA crédito fiscal - compras locales',    '1106', 4, 'ASSET',     'DEBIT',  'Crédito fiscal',      true,  NULL),
 ('110602', 'IVA percibido / retenido a favor',        '1106', 4, 'ASSET',     'DEBIT',  'Crédito fiscal',      true,  NULL),
 ('12',     'Activo no corriente',                     '1',    2, 'ASSET',     'DEBIT',  'Grupo',               false, NULL),
 ('1201',   'Propiedad, planta y equipo',              '12',   3, 'ASSET',     'DEBIT',  'Cuenta mayor',        false, NULL),
 ('120101', 'Mobiliario y equipo de salón',            '1201', 4, 'ASSET',     'DEBIT',  'Subcuenta analítica', true,  NULL),
 ('2',      'PASIVO',                                  NULL,   1, 'LIABILITY', 'CREDIT', 'Clase',               false, NULL),
 ('21',     'Pasivo corriente',                        '2',    2, 'LIABILITY', 'CREDIT', 'Grupo',               false, NULL),
 ('2101',   'Proveedores',                             '21',   3, 'LIABILITY', 'CREDIT', 'Cuenta mayor',        false, NULL),
 ('210101', 'Proveedores locales',                     '2101', 4, 'LIABILITY', 'CREDIT', 'Subcuenta analítica', true,  NULL),
 ('2107',   'IVA débito fiscal',                       '21',   3, 'LIABILITY', 'CREDIT', 'Obligación fiscal',   true,  NULL),
 ('2108',   'Impuestos por pagar',                     '21',   3, 'LIABILITY', 'CREDIT', 'Obligación fiscal',   false, NULL),
 ('210801', 'IVA por pagar',                           '2108', 4, 'LIABILITY', 'CREDIT', 'Obligación fiscal',   true,  NULL),
 ('3',      'PATRIMONIO',                              NULL,   1, 'EQUITY',    'CREDIT', 'Clase',               false, NULL),
 ('31',     'Capital contable',                        '3',    2, 'EQUITY',    'CREDIT', 'Grupo',               false, NULL),
 ('3101',   'Capital social',                          '31',   3, 'EQUITY',    'CREDIT', 'Cuenta mayor',        false, NULL),
 ('310101', 'Capital social pagado',                   '3101', 4, 'EQUITY',    'CREDIT', 'Subcuenta analítica', true,  NULL),
 ('3105',   'Resultados',                              '31',   3, 'EQUITY',    'CREDIT', 'Cuenta mayor',        false, NULL),
 ('310501', 'Utilidad (pérdida) del ejercicio',        '3105', 4, 'EQUITY',    'CREDIT', 'Subcuenta analítica', true,  NULL),
 ('4',      'COSTOS Y GASTOS',                         NULL,   1, 'COST',      'DEBIT',  'Clase',               false, NULL),
 ('41',     'Costos',                                  '4',    2, 'COST',      'DEBIT',  'Grupo',               false, NULL),
 ('4101',   'Costo de venta de productos',             '41',   3, 'COST',      'DEBIT',  'Cuenta mayor',        false, NULL),
 ('410101', 'Costo de venta - vitrina',                '4101', 4, 'COST',      'DEBIT',  'Costo retail',        true,  'VITRINA'),
 ('4102',   'Costo de servicios atelier',              '41',   3, 'COST',      'DEBIT',  'Cuenta mayor',        false, NULL),
 ('410201', 'Insumos consumidos en cabina',            '4102', 4, 'COST',      'DEBIT',  'Costo operativo',     true,  'CABINA'),
 ('42',     'Gastos de operación',                     '4',    2, 'EXPENSE',   'DEBIT',  'Grupo',               false, NULL),
 ('4201',   'Gastos de administración',                '42',   3, 'EXPENSE',   'DEBIT',  'Cuenta mayor',        false, NULL),
 ('420101', 'Gastos generales',                        '4201', 4, 'EXPENSE',   'DEBIT',  'Subcuenta analítica', true,  NULL),
 ('420102', 'Faltantes de inventario',                 '4201', 4, 'EXPENSE',   'DEBIT',  'Subcuenta analítica', true,  NULL),
 ('5',      'INGRESOS',                                NULL,   1, 'INCOME',    'CREDIT', 'Clase',               false, NULL),
 ('51',     'Ingresos ordinarios',                     '5',    2, 'INCOME',    'CREDIT', 'Grupo',               false, NULL),
 ('5101',   'Ingresos por servicios de belleza',       '51',   3, 'INCOME',    'CREDIT', 'Rentas ordinarias',   true,  NULL),
 ('5102',   'Ingresos por venta de productos',         '51',   3, 'INCOME',    'CREDIT', 'Rentas comerciales',  true,  NULL),
 ('52',     'Otros ingresos',                          '5',    2, 'INCOME',    'CREDIT', 'Grupo',               false, NULL),
 ('5201',   'Sobrantes de inventario',                 '52',   3, 'INCOME',    'CREDIT', 'Otros ingresos',      true,  NULL);

-- insert level by level so parents exist
DO $$
DECLARE lvl int;
BEGIN
  FOR lvl IN 1..4 LOOP
    INSERT INTO accounting_account (code, name, parent_id, level, account_type, nature, classification, accepts_entries, inventory_type)
    SELECT s.code, s.name, p.id, s.level, s.type, s.nature, s.classification, s.leaf, s.inv
    FROM seed_account s LEFT JOIN accounting_account p ON p.code = s.parent
    WHERE s.level = lvl;
  END LOOP;
END $$;

-- ---------------------------------------------------------------------
-- Posting rules: event keys used by the PostingService
-- ---------------------------------------------------------------------
INSERT INTO accounting_account_mapping (key, account_id, description)
SELECT m.key, a.id, m.description
FROM (VALUES
  ('CASH',                 '110101', 'Cobros y pagos en efectivo'),
  ('BANK',                 '110102', 'Cobros con tarjeta / transferencias'),
  ('ACCOUNTS_RECEIVABLE',  '110301', 'Ventas al crédito'),
  ('INVENTORY_VITRINA',    '110501', 'Inventario de mercadería para la venta'),
  ('INVENTORY_CABINA',     '110502', 'Inventario de insumos de servicio'),
  ('IVA_CREDIT',           '110601', 'IVA crédito fiscal en compras'),
  ('IVA_PERCEIVED',        '110602', 'IVA percibido/retenido a favor'),
  ('ACCOUNTS_PAYABLE',     '210101', 'Compras al crédito'),
  ('IVA_DEBIT',            '2107',   'IVA débito fiscal en ventas'),
  ('IVA_PAYABLE',          '210801', 'Liquidación mensual de IVA'),
  ('COST_OF_SALES',        '410101', 'Costo de productos vendidos (vitrina)'),
  ('SERVICE_SUPPLY_COST',  '410201', 'Consumo de insumos de cabina'),
  ('INVENTORY_SHORTAGE',   '420102', 'Ajustes negativos de inventario'),
  ('INVENTORY_SURPLUS',    '5201',   'Ajustes positivos de inventario'),
  ('INCOME_SERVICES',      '5101',   'Ventas de servicios (cabina)'),
  ('INCOME_PRODUCTS',      '5102',   'Ventas de productos (vitrina)'),
  ('RETAINED_EARNINGS',    '310501', 'Cierre anual de resultados')
) AS m(key, code, description)
JOIN accounting_account a ON a.code = m.code;

INSERT INTO inventory_location (code, name, location_type) VALUES
  ('VIT',   'Vitrina',         'VITRINA'),
  ('CAB1',  'Cabina 1',        'CABINA'),
  ('CAB2',  'Cabina 2',        'CABINA'),
  ('GEN',   'Bodega general',  'WAREHOUSE');

INSERT INTO sales_customer (name, customer_type, is_generic) VALUES ('Consumidor final', 'FINAL_CONSUMER', true);

INSERT INTO sales_document_series (doc_type, prefix, authorized_from, authorized_to, next_number, valid_from) VALUES
  ('FCF', 'FCF-', 1, 9999, 12, '2026-01-01'),
  ('CCF', 'CCF-', 1, 9999, 1,  '2026-01-01');
