# Generated for Diamond Salón — P2 Accounting Core Models, Triggers & NIIF PYMES Seed
from datetime import date, datetime, timezone
from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import F, Q


PG_TRIGGERS_SQL = """
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

DROP TRIGGER IF EXISTS trg_journal_entry_guard ON accounting_journal_entry;
CREATE TRIGGER trg_journal_entry_guard
    BEFORE INSERT OR UPDATE OR DELETE ON accounting_journal_entry
    FOR EACH ROW EXECUTE FUNCTION fn_journal_entry_guard();

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

DROP TRIGGER IF EXISTS trg_journal_line_guard ON accounting_journal_entry_line;
CREATE TRIGGER trg_journal_line_guard
    BEFORE INSERT OR UPDATE OR DELETE ON accounting_journal_entry_line
    FOR EACH ROW EXECUTE FUNCTION fn_journal_line_guard();
"""


SEED_ACCOUNTS = [
    # (code, name, parent_code, level, type, nature, classification, leaf, inv, niif, debit_rule, credit_rule)
    ("1", "ACTIVO", None, 1, "ASSET", "DEBIT", "Clase", False, None, "NIIF PYMES Secc. 2.15(a)", "Incrementos de recursos económicos controlados por el salón.", "Disminuciones o bajas de activos."),
    ("11", "Activo corriente", "1", 2, "ASSET", "DEBIT", "Grupo", False, None, "NIIF PYMES Secc. 4.5", "Entradas de efectivo, cuentas por cobrar e inventarios realizables en 12 meses.", "Salidas o realización de activos corrientes."),
    ("1101", "Efectivo y equivalentes", "11", 3, "ASSET", "DEBIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 7", "Ingresos de efectivo en caja o depósitos bancarios.", "Pagos en efectivo, transferencias y cheques emitidos."),
    ("110101", "Caja general", "1101", 4, "ASSET", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 7.2", "Se carga por cobros en efectivo de servicios (cabina), ventas retail (vitrina) y aportes iniciales.", "Se abona por pagos a proveedores en efectivo, remesas a bancos y gastos menores."),
    ("110102", "Bancos", "1101", 4, "ASSET", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 7.2", "Se carga por cobros con tarjeta POS, transferencias recibidas y depósitos de caja.", "Se abona por transferencias a proveedores, cheques e impuestos pagados."),
    ("1103", "Cuentas por cobrar", "11", 3, "ASSET", "DEBIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 11", "Derechos de cobro originados por ventas al crédito.", "Cobros parciales o totales recibidos de clientes."),
    ("110301", "Clientes", "1103", 4, "ASSET", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 11.13", "Se carga por facturación FCF/CCF emitida al crédito a clientes del salón.", "Se abona cuando el cliente liquida total o parcialmente su saldo."),
    ("1105", "Inventarios", "11", 3, "ASSET", "DEBIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 13", "Entradas de mercadería para reventa e insumos profesionales al costo promedio.", "Salidas por costo de venta, consumo de cabina o ajustes por faltantes."),
    ("110501", "Mercadería para la venta (vitrina)", "1105", 4, "ASSET", "DEBIT", "Subcuenta retail", True, "VITRINA", "NIIF PYMES Secc. 13.18", "Se carga por compras de productos comerciales para reventa (Vitrina) y ajustes positivos.", "Se abona al costo promedio ponderado por cada producto vendido en mostrador o por merma."),
    ("110502", "Insumos para servicios (cabina)", "1105", 4, "ASSET", "DEBIT", "Subcuenta operativa", True, "CABINA", "NIIF PYMES Secc. 13.18", "Se carga por compras de tintes, tratamientos y químicos destinados a las estaciones de servicio.", "Se abona al costo promedio cuando los estilistas consumen insumos en cabina."),
    ("1106", "IVA crédito fiscal", "11", 3, "ASSET", "DEBIT", "Cuenta mayor", False, None, "Ley de IVA Art. 57", "IVA 13% soportado en Comprobantes de Crédito Fiscal (CCF) de compras.", "Liquidación mensual contra el IVA débito fiscal."),
    ("110601", "IVA crédito fiscal - compras locales", "1106", 4, "ASSET", "DEBIT", "Crédito fiscal", True, None, "Ley de IVA Art. 65", "Se carga por el 13% de IVA respaldado con CCF en compras de vitrina, cabina y gastos del giro.", "Se abona al cierre mensual en la partida de liquidación contra la cuenta 2107."),
    ("110602", "IVA percibido / retenido a favor", "1106", 4, "ASSET", "DEBIT", "Crédito fiscal", True, None, "Código Tributario Art. 162", "Se carga por el 1% de IVA retenido por grandes contribuyentes o percibido por proveedores.", "Se abona al acreditarse en la declaración mensual de IVA."),
    ("12", "Activo no corriente", "1", 2, "ASSET", "DEBIT", "Grupo", False, None, "NIIF PYMES Secc. 17", "Adquisición de bienes de uso duradero del salón.", "Bajas o disposición de activos fijos."),
    ("1201", "Propiedad, planta y equipo", "12", 3, "ASSET", "DEBIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 17", "Inversión en mobiliario, sillones hidráulicos, secadores y equipo de estética.", "Retiro o venta de mobiliario y equipo."),
    ("120101", "Mobiliario y equipo de salón", "1201", 4, "ASSET", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 17.10", "Se carga al costo de adquisición de sillones, lavacabezas, vitrinas y equipos de estación.", "Se abona por baja o venta del equipo."),
    ("2", "PASIVO", None, 1, "LIABILITY", "CREDIT", "Clase", False, None, "NIIF PYMES Secc. 2.15(b)", "Pagos o extinción de obligaciones presentes.", "Nacimiento de obligaciones con proveedores y el fisco."),
    ("21", "Pasivo corriente", "2", 2, "LIABILITY", "CREDIT", "Grupo", False, None, "NIIF PYMES Secc. 4.7", "Amortización de deudas de corto plazo.", "Deudas comerciales e impuestos exigibles en menos de 12 meses."),
    ("2101", "Proveedores", "21", 3, "LIABILITY", "CREDIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 11", "Pagos parciales o totales a casas distribuidoras.", "Compras al crédito de productos de vitrina e insumos de cabina."),
    ("210101", "Proveedores locales", "2101", 4, "LIABILITY", "CREDIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 11.13", "Se carga por abonos o cancelaciones de facturas a proveedores (efectivo o transferencia).", "Se abona por el total de compras al crédito documentadas con CCF o factura."),
    ("2107", "IVA débito fiscal", "21", 3, "LIABILITY", "CREDIT", "Obligación fiscal", True, None, "Ley de IVA Art. 54", "Se carga al cierre del período mensual en la liquidación contra el IVA crédito fiscal (110601).", "Se abona por el 13% de IVA trasladado en ventas de servicios y productos (FCF y CCF)."),
    ("2108", "Impuestos por pagar", "21", 3, "LIABILITY", "CREDIT", "Obligación fiscal", False, None, "Código Tributario", "Entero de impuestos en colecturía o banca.", "Determinación de cuota tributaria neta a pagar al Ministerio de Hacienda."),
    ("210801", "IVA por pagar", "2108", 4, "LIABILITY", "CREDIT", "Obligación fiscal", True, None, "Ley de IVA Art. 94", "Se carga cuando se efectúa el pago de la declaración F-07 a Hacienda.", "Se abona en el cierre mensual por el excedente de IVA débito sobre IVA crédito."),
    ("3", "PATRIMONIO", None, 1, "EQUITY", "CREDIT", "Clase", False, None, "NIIF PYMES Secc. 2.15(c)", "Reducciones de patrimonio o pérdidas acumuladas.", "Aportes de socios y utilidades generadas."),
    ("31", "Capital contable", "3", 2, "EQUITY", "CREDIT", "Grupo", False, None, "NIIF PYMES Secc. 22", "Disminuciones de capital o distribución de resultados.", "Capital aportado y resultados acumulados del atelier."),
    ("3101", "Capital social", "31", 3, "EQUITY", "CREDIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 22", "Reducciones legales de capital social.", "Suscripción y pago de capital social."),
    ("310101", "Capital social pagado", "3101", 4, "EQUITY", "CREDIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 22.7", "Se carga únicamente por disminuciones formales de capital social.", "Se abona en la partida de apertura por el aporte inicial de los propietarios de Diamond Salón."),
    ("3105", "Resultados", "31", 3, "EQUITY", "CREDIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 5", "Pérdidas del ejercicio o capitalización.", "Utilidades netas obtenidas al cierre del ejercicio."),
    ("310501", "Utilidad (pérdida) del ejercicio", "3105", 4, "EQUITY", "CREDIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 5.4", "Se carga al cierre anual si los costos y gastos superan los ingresos.", "Se abona al cierre anual por la utilidad neta trasladada desde cuentas de resultado."),
    ("4", "COSTOS Y GASTOS", None, 1, "COST", "DEBIT", "Clase", False, None, "NIIF PYMES Secc. 2.23(b)", "Reconocimiento de costos de venta, consumo de cabina y gastos operativos.", "Liquidación anual contra resultados del ejercicio."),
    ("41", "Costos", "4", 2, "COST", "DEBIT", "Grupo", False, None, "NIIF PYMES Secc. 13.20", "Costo directo de mercadería vendida e insumos aplicados en servicios.", "Reversiones por anulación o cierre de ejercicio."),
    ("4101", "Costo de venta de productos", "41", 3, "COST", "DEBIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 13.20", "Descargo de inventario vitrina al momento de la venta.", "Reversión por anulación de factura de venta."),
    ("410101", "Costo de venta - vitrina", "4101", 4, "COST", "DEBIT", "Costo retail", True, "VITRINA", "NIIF PYMES Secc. 13.20", "Se carga automáticamente al costo promedio ponderado cuando se vende un producto de vitrina.", "Se abona por reversión de venta anulada o al cierre anual."),
    ("4102", "Costo de servicios atelier", "41", 3, "COST", "DEBIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 13.20", "Insumos profesionales consumidos en estaciones de trabajo.", "Reversión de consumo o cierre anual."),
    ("410201", "Insumos consumidos en cabina", "4102", 4, "COST", "DEBIT", "Costo operativo", True, "CABINA", "NIIF PYMES Secc. 13.20", "Se carga cuando se registra consumo de tintes, champú de galón o químicos desde 110502.", "Se abona por reversión o al cierre anual contra resultados."),
    ("42", "Gastos de operación", "4", 2, "EXPENSE", "DEBIT", "Grupo", False, None, "NIIF PYMES Secc. 2.42", "Gastos administrativos, servicios básicos y ajustes por faltantes.", "Cierre anual contra la cuenta 310501."),
    ("4201", "Gastos de administración", "42", 3, "EXPENSE", "DEBIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 2.42", "Gastos generales de funcionamiento y mermas de inventario.", "Reversión o cierre anual."),
    ("420101", "Gastos generales", "4201", 4, "EXPENSE", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 2.42", "Se carga por servicios básicos, papelería, limpieza y mantenimiento del local.", "Se abona al cierre anual contra resultados."),
    ("420102", "Faltantes de inventario", "4201", 4, "EXPENSE", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 13.20", "Se carga por ajustes negativos de stock (daño, vencimiento o diferencia en conteo físico).", "Se abona al cierre anual."),
    ("5", "INGRESOS", None, 1, "INCOME", "CREDIT", "Clase", False, None, "NIIF PYMES Secc. 23", "Anulaciones de ventas o cierre anual contra resultados.", "Devengo de ingresos por servicios de salón y venta retail (sin IVA)."),
    ("51", "Ingresos ordinarios", "5", 2, "INCOME", "CREDIT", "Grupo", False, None, "NIIF PYMES Secc. 23.3", "Reversiones de facturas anuladas.", "Facturación del giro principal del salón (cabina y vitrina)."),
    ("5101", "Ingresos por servicios de belleza", "51", 3, "INCOME", "CREDIT", "Rentas ordinarias", True, "CABINA", "NIIF PYMES Secc. 23.14", "Se carga por anulación de factura de servicio o al cierre anual.", "Se abona por el valor neto gravado (sin IVA) de cortes, tintes, manicure y tratamientos en cabina."),
    ("5102", "Ingresos por venta de productos", "51", 3, "INCOME", "CREDIT", "Rentas comerciales", True, "VITRINA", "NIIF PYMES Secc. 23.10", "Se carga por devolución/anulación de venta retail o cierre anual.", "Se abona por el valor neto gravado (sin IVA) de productos de vitrina vendidos al público."),
    ("52", "Otros ingresos", "5", 2, "INCOME", "CREDIT", "Grupo", False, None, "NIIF PYMES Secc. 2.25(a)", "Cierre anual.", "Ingresos no ordinarios y sobrantes de conteo físico."),
    ("5201", "Sobrantes de inventario", "52", 3, "INCOME", "CREDIT", "Otros ingresos", True, None, "NIIF PYMES Secc. 2.25(a)", "Se carga al cierre anual.", "Se abona por ajustes positivos derivados de recuentos físicos de inventario."),
]

SEED_MAPPINGS = [
    ("CASH", "110101", "Cobros y pagos en efectivo"),
    ("BANK", "110102", "Cobros con tarjeta / transferencias"),
    ("ACCOUNTS_RECEIVABLE", "110301", "Ventas al crédito"),
    ("INVENTORY_VITRINA", "110501", "Inventario de mercadería para la venta"),
    ("INVENTORY_CABINA", "110502", "Inventario de insumos de servicio"),
    ("IVA_CREDIT", "110601", "IVA crédito fiscal en compras"),
    ("IVA_PERCEIVED", "110602", "IVA percibido/retenido a favor"),
    ("ACCOUNTS_PAYABLE", "210101", "Compras al crédito"),
    ("IVA_DEBIT", "2107", "IVA débito fiscal en ventas"),
    ("IVA_PAYABLE", "210801", "Liquidación mensual de IVA"),
    ("COST_OF_SALES", "410101", "Costo de productos vendidos (vitrina)"),
    ("SERVICE_SUPPLY_COST", "410201", "Consumo de insumos de cabina"),
    ("INVENTORY_SHORTAGE", "420102", "Ajustes negativos de inventario"),
    ("INVENTORY_SURPLUS", "5201", "Ajustes positivos de inventario"),
    ("INCOME_SERVICES", "5101", "Ventas de servicios (cabina)"),
    ("INCOME_PRODUCTS", "5102", "Ventas de productos (vitrina)"),
    ("RETAINED_EARNINGS", "310501", "Cierre anual de resultados"),
]


def seed_accounting_data(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(PG_TRIGGERS_SQL)

    Account = apps.get_model("accounting", "Account")
    AccountMapping = apps.get_model("accounting", "AccountMapping")
    JournalEntry = apps.get_model("accounting", "JournalEntry")
    JournalEntryLine = apps.get_model("accounting", "JournalEntryLine")
    AccountingPeriod = apps.get_model("core", "AccountingPeriod")
    User = apps.get_model("core", "User")

    # 1. Insert accounts level by level (1..4) so parent_id always exists
    code_to_account = {}
    for lvl in (1, 2, 3, 4):
        for (
            code,
            name,
            parent_code,
            level,
            acc_type,
            nature,
            classification,
            leaf,
            inv_type,
            niif_ref,
            debit_rule,
            credit_rule,
        ) in SEED_ACCOUNTS:
            if level != lvl:
                continue
            parent_obj = code_to_account.get(parent_code) if parent_code else None
            acc, _ = Account.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "parent": parent_obj,
                    "level": level,
                    "account_type": acc_type,
                    "nature": nature,
                    "classification": classification,
                    "accepts_entries": leaf,
                    "inventory_type": inv_type,
                    "niif_reference": niif_ref,
                    "debit_rule": debit_rule,
                    "credit_rule": credit_rule,
                    "is_active": True,
                },
            )
            code_to_account[code] = acc

    # 2. Insert configurable account mappings (seed.sql)
    for key, code, description in SEED_MAPPINGS:
        AccountMapping.objects.update_or_create(
            key=key,
            defaults={
                "account": code_to_account[code],
                "description": description,
            },
        )

    # 3. Seed balanced November 2026 journal entries matching the SRS / mock-ups
    nov_period = AccountingPeriod.objects.filter(year=2026, month=11).first()
    creator = User.objects.filter(username="contador").first() or User.objects.first()
    if not nov_period or not creator or JournalEntry.objects.filter(period=nov_period).exists():
        return

    sample_entries = [
        (
            1,
            date(2026, 11, 1),
            "Partida de apertura de saldos iniciales — Noviembre 2026",
            "OPENING",
            None,
            None,
            [
                ("110101", "Efectivo inicial en Caja General", Decimal("1850.00"), Decimal("0.00")),
                ("110102", "Saldo inicial en cuenta bancaria operativa", Decimal("3400.00"), Decimal("0.00")),
                ("110501", "Inventario inicial mercadería vitrina (costo promedio)", Decimal("746.50"), Decimal("0.00")),
                ("110502", "Inventario inicial insumos cabina (costo promedio)", Decimal("480.00"), Decimal("0.00")),
                ("120101", "Mobiliario y equipo de estación Diamond Salón", Decimal("4523.50"), Decimal("0.00")),
                ("310101", "Capital social pagado — Apertura Atelier", Decimal("0.00"), Decimal("11000.00")),
            ],
        ),
        (
            2,
            date(2026, 11, 3),
            "Compra CCF-4521 Distribuidora Cosmética S.A. · Mercadería para Vitrina al crédito",
            "PURCHASE",
            "purchases.purchase",
            1,
            [
                ("110501", "Ingreso de champús y mascarillas retail a Vitrina", Decimal("150.00"), Decimal("0.00")),
                ("110601", "IVA crédito fiscal 13% s/ CCF-4521", Decimal("19.50"), Decimal("0.00")),
                ("210101", "Cuenta por pagar a Distribuidora Cosmética S.A.", Decimal("0.00"), Decimal("169.50")),
            ],
        ),
        (
            3,
            date(2026, 11, 4),
            "Compra CCF-4522 Insumos Pro S.A. · Tintes y peróxidos para Cabina al crédito",
            "PURCHASE",
            "purchases.purchase",
            2,
            [
                ("110502", "Ingreso de insumos técnicos a Cabina 1 y 2", Decimal("90.00"), Decimal("0.00")),
                ("110601", "IVA crédito fiscal 13% s/ CCF-4522", Decimal("11.70"), Decimal("0.00")),
                ("210101", "Cuenta por pagar a Insumos Pro S.A.", Decimal("0.00"), Decimal("101.70")),
            ],
        ),
        (
            4,
            date(2026, 11, 5),
            "Venta FCF-0012 · Servicio de corte, hidratación y estilizado en Cabina (Efectivo)",
            "SALE",
            "sales.sale",
            1,
            [
                ("110101", "Cobro en efectivo FCF-0012", Decimal("25.00"), Decimal("0.00")),
                ("5101", "Ingreso neto por servicio de belleza en cabina", Decimal("0.00"), Decimal("22.12")),
                ("2107", "IVA débito fiscal 13% incluido en FCF-0012", Decimal("0.00"), Decimal("2.88")),
            ],
        ),
        (
            5,
            date(2026, 11, 6),
            "Venta FCF-0013 · Champú nutritivo 300ml (Vitrina) + descargo al costo promedio",
            "SALE",
            "sales.sale",
            2,
            [
                ("110101", "Cobro en efectivo FCF-0013", Decimal("12.00"), Decimal("0.00")),
                ("5102", "Ingreso neto por venta de producto retail", Decimal("0.00"), Decimal("10.62")),
                ("2107", "IVA débito fiscal 13% incluido en FCF-0013", Decimal("0.00"), Decimal("1.38")),
                ("410101", "Costo de venta a promedio ponderado (1 u. x $7.00)", Decimal("7.00"), Decimal("0.00")),
                ("110501", "Descargo de inventario vitrina FCF-0013", Decimal("0.00"), Decimal("7.00")),
            ],
        ),
        (
            6,
            date(2026, 11, 7),
            "Consumo diario de insumos en Cabina 1 · Estilista Roberto G.",
            "INVENTORY",
            "inventory.consumption",
            1,
            [
                ("410201", "Aplicación de tinte y oxidante en servicios del día", Decimal("18.50"), Decimal("0.00")),
                ("110502", "Salida de insumos de Cabina 1 por consumo", Decimal("0.00"), Decimal("18.50")),
            ],
        ),
        (
            7,
            date(2026, 11, 8),
            "Pago a proveedor Insumos Pro S.A. · Cancelación CCF-4522 en efectivo",
            "PAYMENT",
            "purchases.supplierpayment",
            1,
            [
                ("210101", "Liquidación de saldo CCF-4522 Insumos Pro S.A.", Decimal("101.70"), Decimal("0.00")),
                ("110101", "Egreso de Caja General por pago a proveedor", Decimal("0.00"), Decimal("101.70")),
            ],
        ),
    ]

    now_ts = datetime(2026, 11, 8, 18, 0, 0, tzinfo=timezone.utc)
    for entry_no, entry_date, desc, entry_type, src_app, src_id, lines in sample_entries:
        # Step 1: Create as DRAFT (required by trg_journal_entry_guard)
        entry = JournalEntry.objects.create(
            period=nov_period,
            entry_number=None,
            entry_date=entry_date,
            description=desc,
            entry_type=entry_type,
            source_app=src_app,
            source_id=src_id,
            status="DRAFT",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("0.00"),
            created_by=creator,
        )
        total_d = Decimal("0.00")
        total_c = Decimal("0.00")
        for idx, (acc_code, line_desc, d_amt, c_amt) in enumerate(lines, start=1):
            JournalEntryLine.objects.create(
                entry=entry,
                line_no=idx,
                account=code_to_account[acc_code],
                description=line_desc,
                debit=d_amt,
                credit=c_amt,
            )
            total_d += d_amt
            total_c += c_amt

        # Step 2: Transition DRAFT -> POSTED
        entry.entry_number = entry_no
        entry.status = "POSTED"
        entry.total_debit = total_d
        entry.total_credit = total_c
        entry.posted_by = creator
        entry.posted_at = now_ts
        entry.save()


def unseed_accounting_data(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("core", "0002_core_domain_and_seed"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Account",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "code",
                    models.CharField(
                        max_length=20,
                        unique=True,
                        validators=[
                            django.core.validators.RegexValidator(
                                "^[0-9]+$",
                                "El código contable debe contener únicamente dígitos.",
                            )
                        ],
                    ),
                ),
                ("name", models.CharField(max_length=150)),
                ("level", models.SmallIntegerField()),
                (
                    "account_type",
                    models.CharField(
                        choices=[
                            ("ASSET", "Activo"),
                            ("LIABILITY", "Pasivo"),
                            ("EQUITY", "Patrimonio"),
                            ("COST", "Costo"),
                            ("EXPENSE", "Gasto"),
                            ("INCOME", "Ingreso"),
                            ("CLOSING", "Cierre"),
                        ],
                        max_length=10,
                    ),
                ),
                (
                    "nature",
                    models.CharField(
                        choices=[("DEBIT", "Deudora"), ("CREDIT", "Acreedora")],
                        max_length=6,
                    ),
                ),
                ("classification", models.CharField(blank=True, default="", max_length=40)),
                ("accepts_entries", models.BooleanField(default=False)),
                (
                    "inventory_type",
                    models.CharField(
                        blank=True,
                        choices=[("VITRINA", "Vitrina (Venta)"), ("CABINA", "Cabina (Servicio)")],
                        max_length=10,
                        null=True,
                    ),
                ),
                ("niif_reference", models.CharField(blank=True, default="", max_length=60)),
                ("debit_rule", models.TextField(blank=True, default="")),
                ("credit_rule", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="children",
                        to="accounting.account",
                    ),
                ),
            ],
            options={
                "db_table": "accounting_account",
                "ordering": ["code"],
            },
        ),
        migrations.CreateModel(
            name="AccountMapping",
            fields=[
                ("key", models.CharField(max_length=40, primary_key=True, serialize=False)),
                ("description", models.CharField(max_length=200)),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="mappings",
                        to="accounting.account",
                    ),
                ),
            ],
            options={
                "db_table": "accounting_account_mapping",
                "ordering": ["key"],
            },
        ),
        migrations.CreateModel(
            name="JournalEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("entry_number", models.IntegerField(blank=True, null=True)),
                ("entry_date", models.DateField()),
                ("description", models.TextField()),
                (
                    "entry_type",
                    models.CharField(
                        choices=[
                            ("OPENING", "Apertura"),
                            ("MANUAL", "Manual"),
                            ("SALE", "Venta"),
                            ("PURCHASE", "Compra"),
                            ("PAYMENT", "Pago"),
                            ("INVENTORY", "Inventario"),
                            ("ADJUSTMENT", "Ajuste"),
                            ("CLOSING", "Cierre"),
                            ("REVERSAL", "Reversión"),
                        ],
                        default="MANUAL",
                        max_length=12,
                    ),
                ),
                ("source_app", models.CharField(blank=True, max_length=40, null=True)),
                ("source_id", models.BigIntegerField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Borrador"),
                            ("POSTED", "Mayorizada"),
                            ("REVERSED", "Revertida"),
                        ],
                        default="DRAFT",
                        max_length=10,
                    ),
                ),
                ("total_debit", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("total_credit", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("posted_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_journal_entries",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "period",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="journal_entries",
                        to="core.accountingperiod",
                    ),
                ),
                (
                    "posted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="posted_journal_entries",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reversal_of",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reversed_by",
                        to="accounting.journalentry",
                    ),
                ),
            ],
            options={
                "db_table": "accounting_journal_entry",
                "ordering": ["entry_date", "entry_number", "id"],
            },
        ),
        migrations.CreateModel(
            name="JournalEntryLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("line_no", models.SmallIntegerField()),
                ("description", models.CharField(blank=True, default="", max_length=255)),
                ("debit", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("credit", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="journal_lines",
                        to="accounting.account",
                    ),
                ),
                (
                    "entry",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lines",
                        to="accounting.journalentry",
                    ),
                ),
            ],
            options={
                "db_table": "accounting_journal_entry_line",
                "ordering": ["line_no", "id"],
            },
        ),
        migrations.CreateModel(
            name="PeriodBalance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("opening_balance", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("debit_total", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("credit_total", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("closing_balance", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="period_balances",
                        to="accounting.account",
                    ),
                ),
                (
                    "period",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="account_balances",
                        to="core.accountingperiod",
                    ),
                ),
            ],
            options={
                "db_table": "accounting_period_balance",
            },
        ),
        # Indexes & Constraints
        migrations.AddIndex(
            model_name="account",
            index=models.Index(fields=["parent"], name="ix_account_parent"),
        ),
        migrations.AddIndex(
            model_name="account",
            index=models.Index(fields=["code"], name="ix_account_code_prefix"),
        ),
        migrations.AddConstraint(
            model_name="account",
            constraint=models.CheckConstraint(
                condition=Q(level__gte=1, level__lte=6),
                name="ck_accounting_account_level",
            ),
        ),
        migrations.AddConstraint(
            model_name="account",
            constraint=models.CheckConstraint(
                condition=Q(
                    account_type__in=["ASSET", "LIABILITY", "EQUITY", "COST", "EXPENSE", "INCOME", "CLOSING"]
                ),
                name="ck_accounting_account_type",
            ),
        ),
        migrations.AddConstraint(
            model_name="account",
            constraint=models.CheckConstraint(
                condition=Q(nature__in=["DEBIT", "CREDIT"]),
                name="ck_accounting_account_nature",
            ),
        ),
        migrations.AddConstraint(
            model_name="account",
            constraint=models.CheckConstraint(
                condition=Q(inventory_type__isnull=True) | Q(inventory_type__in=["VITRINA", "CABINA"]),
                name="ck_accounting_account_inv_type",
            ),
        ),
        migrations.AddConstraint(
            model_name="account",
            constraint=models.CheckConstraint(
                condition=(Q(level=1) & Q(parent__isnull=True))
                | (Q(level__gt=1) & Q(parent__isnull=False)),
                name="ck_accounting_account_root_parent",
            ),
        ),
        migrations.AddIndex(
            model_name="journalentry",
            index=models.Index(fields=["entry_date", "entry_number"], name="ix_entry_date"),
        ),
        migrations.AddIndex(
            model_name="journalentry",
            index=models.Index(fields=["source_app", "source_id"], name="ix_entry_source"),
        ),
        migrations.AddConstraint(
            model_name="journalentry",
            constraint=models.UniqueConstraint(
                fields=("period", "entry_number"),
                name="uq_accounting_entry_period_number",
            ),
        ),
        migrations.AddConstraint(
            model_name="journalentry",
            constraint=models.CheckConstraint(
                condition=Q(
                    entry_type__in=[
                        "OPENING",
                        "MANUAL",
                        "SALE",
                        "PURCHASE",
                        "PAYMENT",
                        "INVENTORY",
                        "ADJUSTMENT",
                        "CLOSING",
                        "REVERSAL",
                    ]
                ),
                name="ck_accounting_entry_type",
            ),
        ),
        migrations.AddConstraint(
            model_name="journalentry",
            constraint=models.CheckConstraint(
                condition=Q(status__in=["DRAFT", "POSTED", "REVERSED"]),
                name="ck_accounting_entry_status",
            ),
        ),
        migrations.AddConstraint(
            model_name="journalentry",
            constraint=models.CheckConstraint(
                condition=Q(status="DRAFT")
                | (Q(entry_number__isnull=False) & Q(posted_at__isnull=False)),
                name="ck_accounting_entry_posted_meta",
            ),
        ),
        migrations.AddConstraint(
            model_name="journalentry",
            constraint=models.CheckConstraint(
                condition=Q(status="DRAFT")
                | (Q(total_debit=F("total_credit")) & Q(total_debit__gt=Decimal("0.00"))),
                name="ck_accounting_entry_balanced",
            ),
        ),
        migrations.AddIndex(
            model_name="journalentryline",
            index=models.Index(fields=["account"], name="ix_line_account"),
        ),
        migrations.AddConstraint(
            model_name="journalentryline",
            constraint=models.UniqueConstraint(
                fields=("entry", "line_no"),
                name="uq_accounting_entry_line_no",
            ),
        ),
        migrations.AddConstraint(
            model_name="journalentryline",
            constraint=models.CheckConstraint(
                condition=Q(debit__gte=Decimal("0.00")) & Q(credit__gte=Decimal("0.00")),
                name="ck_accounting_line_non_negative",
            ),
        ),
        migrations.AddConstraint(
            model_name="journalentryline",
            constraint=models.CheckConstraint(
                condition=(Q(debit__gt=Decimal("0.00")) & Q(credit=Decimal("0.00")))
                | (Q(credit__gt=Decimal("0.00")) & Q(debit=Decimal("0.00"))),
                name="ck_accounting_line_xor_debit_credit",
            ),
        ),
        migrations.AddConstraint(
            model_name="periodbalance",
            constraint=models.UniqueConstraint(
                fields=("account", "period"),
                name="uq_accounting_period_balance",
            ),
        ),
        migrations.RunPython(seed_accounting_data, unseed_accounting_data),
    ]
