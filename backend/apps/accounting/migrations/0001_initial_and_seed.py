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
    # 1 ACTIVO
    ("1", "ACTIVO", None, 1, "ASSET", "DEBIT", "Clase", False, None, "NIIF PYMES Secc. 2.15(a)", "Incrementos de recursos económicos controlados por el salón.", "Disminuciones o bajas de activos."),
    ("11", "ACTIVO CORRIENTE", "1", 2, "ASSET", "DEBIT", "Grupo", False, None, "NIIF PYMES Secc. 4.5", "Entradas de efectivo, derechos de cobro e inventarios realizables en 12 meses.", "Salidas o realización de activos corrientes."),
    ("1101", "Efectivo y equivalentes al efectivo", "11", 3, "ASSET", "DEBIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 7", "Ingresos de efectivo en caja o depósitos bancarios.", "Pagos en efectivo, transferencias y cheques emitidos."),
    ("110101", "Caja general", "1101", 4, "ASSET", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 7.2", "Cobros en efectivo de servicios y ventas retail.", "Pagos menores en efectivo y remesas a bancos."),
    ("110102", "Caja chica", "1101", 4, "ASSET", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 7.2", "Fondo fijo para gastos menores y reposición.", "Liquidación o reducción del fondo fijo."),
    ("110103", "Bancos cuenta corriente", "1101", 4, "ASSET", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 7.2", "Cobros POS con tarjeta, transferencias y depósitos.", "Transferencias a proveedores, cheques y pagos de servicios."),
    ("110104", "Bancos cuenta de ahorro", "1101", 4, "ASSET", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 7.2", "Depósitos e intereses ganados.", "Retiros y traslados a cuenta corriente."),
    ("1102", "Cuentas y documentos por cobrar", "11", 3, "ASSET", "DEBIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 11", "Derechos de cobro exigibles a clientes y deudores.", "Recuperación de saldos o castigo de deudas incobrables."),
    ("110201", "Clientes", "1102", 4, "ASSET", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 11.13", "Ventas de servicios o productos al crédito documentadas con FCF/CCF.", "Abonos y cancelaciones de clientes."),
    ("110202", "Deudores diversos", "1102", 4, "ASSET", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 11.13", "Préstamos a empleados y anticipos varios no comerciales.", "Cobros o descuentos de deudores."),
    ("110203", "Estimación para cuentas incobrables (-)", "1102", 4, "ASSET", "CREDIT", "Cuenta de valuación", True, None, "NIIF PYMES Secc. 11.21", "Cancelación o castigo definitivo de cuentas incobrables.", "Dotación o provisión por deterioro de cartera de clientes."),
    ("1103", "IVA crédito fiscal", "11", 3, "ASSET", "DEBIT", "Cuenta mayor", False, None, "Ley de IVA Art. 57", "IVA 13% soportado en comprobantes de crédito fiscal de compras.", "Liquidación mensual contra IVA débito o remanente."),
    ("110301", "IVA crédito fiscal por compras", "1103", 4, "ASSET", "DEBIT", "Subcuenta analítica", True, None, "Ley de IVA Art. 65", "IVA 13% en CCF por compras de mercadería, insumos y gastos.", "Acreditación y liquidación en partida de cierre mensual."),
    ("1104", "Inventarios", "11", 3, "ASSET", "DEBIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 13", "Entradas de mercadería e insumos al costo promedio ponderado.", "Salidas por costo de venta, consumo en cabina o ajustes."),
    ("110401", "Inventario de mercadería para la venta (vitrina)", "1104", 4, "ASSET", "DEBIT", "Subcuenta retail", True, "VITRINA", "NIIF PYMES Secc. 13.18", "Compras de productos comerciales para reventa y ajustes positivos.", "Costo promedio por venta retail en mostrador o mermas."),
    ("110402", "Inventario de insumos para servicios (cabina)", "1104", 4, "ASSET", "DEBIT", "Subcuenta operativa", True, "CABINA", "NIIF PYMES Secc. 13.18", "Compras de tintes, químicos y tratamientos para estaciones.", "Consumo de insumos en cabina por estilistas al costo promedio."),
    ("1105", "Pagos anticipados", "11", 3, "ASSET", "DEBIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 18", "Pagos por servicios o bienes que se recibirán en el futuro.", "Amortización o devengo del gasto pagado por anticipado."),
    ("110501", "Anticipo a proveedores", "1105", 4, "ASSET", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 18.2", "Anticipos entregados a proveedores por compras futuras.", "Liquidación al recibir la mercadería o insumos con CCF."),
    ("110502", "Seguros pagados por anticipado", "1105", 4, "ASSET", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 18.2", "Pago de primas de seguro de instalaciones y equipo.", "Devengo mensual de la cobertura de seguro contra gastos."),
    ("12", "ACTIVO NO CORRIENTE", "1", 2, "ASSET", "DEBIT", "Grupo", False, None, "NIIF PYMES Secc. 17", "Bienes duraderos y tangibles destinados al funcionamiento del salón.", "Bajas, enajenación o retiro de activos fijos."),
    ("1201", "Propiedad, planta y equipo", "12", 3, "ASSET", "DEBIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 17", "Adquisición de mobiliario, secadores, computadoras y equipo de salón.", "Disposición, venta o retiro por obsolescencia."),
    ("120101", "Mobiliario y equipo de salón", "1201", 4, "ASSET", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 17.10", "Sillones hidráulicos, lavacabezas, tocadores y equipo de belleza.", "Baja o descarte de mobiliario de salón."),
    ("120102", "Equipo de cómputo", "1201", 4, "ASSET", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 17.10", "Computadoras, puntos de venta (POS), tablets e impresoras térmicas.", "Baja por obsolescencia tecnológica."),
    ("120103", "Mobiliario y equipo de oficina", "1201", 4, "ASSET", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 17.10", "Escritorios de recepción, sillas de espera, archivadores.", "Retiro de equipo de oficina."),
    ("120104", "Depreciación acumulada (-)", "1201", 4, "ASSET", "CREDIT", "Cuenta de valuación", True, None, "NIIF PYMES Secc. 17.16", "Descargo por venta o retiro del activo fijo.", "Depreciación mensual por desgaste sistemático de los bienes."),
    ("1202", "Activos intangibles", "12", 3, "ASSET", "DEBIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 18", "Licencias de software y programas de gestión contable.", "Amortización acumulada o baja de intangibles."),
    ("120201", "Programas informáticos (software)", "1202", 4, "ASSET", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 18.4", "Software de gestión Diamond Salón, licencias ERP.", "Amortización o descarte de programas informáticos."),

    # 2 PASIVO
    ("2", "PASIVO", None, 1, "LIABILITY", "CREDIT", "Clase", False, None, "NIIF PYMES Secc. 2.15(b)", "Cancelaciones, pagos y amortizaciones de deudas.", "Nacimiento de obligaciones contractuales, laborales y tributarias."),
    ("21", "PASIVO CORRIENTE", "2", 2, "LIABILITY", "CREDIT", "Grupo", False, None, "NIIF PYMES Secc. 4.7", "Liquidación de pasivos exigibles dentro de 12 meses.", "Obligaciones comerciales, laborales y fiscales a corto plazo."),
    ("2101", "Cuentas y documentos por pagar", "21", 3, "LIABILITY", "CREDIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 11", "Pagos a distribuidores y acreedores del salón.", "Obligaciones contraídas por compras de bienes y servicios al crédito."),
    ("210101", "Proveedores", "2101", 4, "LIABILITY", "CREDIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 11.13", "Abonos y cancelaciones de compras con CCF al crédito.", "Compras a crédito de productos de vitrina e insumos de cabina."),
    ("210102", "Acreedores diversos", "2101", 4, "LIABILITY", "CREDIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 11.13", "Pagos de deudas no comerciales.", "Obligaciones varias distintas a proveedores de inventario."),
    ("2102", "IVA débito fiscal", "21", 3, "LIABILITY", "CREDIT", "Cuenta mayor", False, None, "Ley de IVA Art. 54", "Liquidación mensual de IVA contra crédito fiscal en cierre de período.", "IVA 13% trasladado en facturas FCF y CCF de servicios y productos."),
    ("210201", "IVA débito fiscal por ventas", "2102", 4, "LIABILITY", "CREDIT", "Subcuenta analítica", True, None, "Ley de IVA Art. 54", "Compensación mensual en partida de cierre contra cuenta 110301.", "IVA 13% facturado en ventas retail y servicios de belleza."),
    ("2103", "Impuestos por pagar", "21", 3, "LIABILITY", "CREDIT", "Cuenta mayor", False, None, "Código Tributario", "Pago en ventanilla bancaria o colecturía de mandamientos del fisco.", "Determinación de cuota neta mensual o anual a enterar."),
    ("210301", "IVA por pagar", "2103", 4, "LIABILITY", "CREDIT", "Subcuenta analítica", True, None, "Ley de IVA Art. 94", "Pago de la declaración F-07 en colecturía de Hacienda.", "IVA débito excedente sobre el crédito fiscal liquidado al cierre de mes."),
    ("210302", "Pago a cuenta (anticipo ISR)", "2103", 4, "LIABILITY", "CREDIT", "Subcuenta analítica", True, None, "Ley de ISR Art. 151", "Pago mensual de anticipo 1.75% sobre ingresos brutos.", "Provisión mensual del pago a cuenta sobre ingresos."),
    ("210303", "Impuesto sobre la renta por pagar", "2103", 4, "LIABILITY", "CREDIT", "Subcuenta analítica", True, None, "Ley de ISR Art. 37", "Pago anual de la declaración F-11 de renta.", "Determinación del ISR anual sobre la renta imponible neta."),
    ("2104", "Beneficios a empleados por pagar", "21", 3, "LIABILITY", "CREDIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 28", "Pago de planillas, aguinaldos y transferencias previsionales.", "Devengo de salarios y retenciones laborales."),
    ("210401", "Sueldos y salarios por pagar", "2104", 4, "LIABILITY", "CREDIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 28.3", "Pago quincenal o mensual a estilistas y personal.", "Devengo del pasivo laboral por sueldos del período."),
    ("210402", "ISSS por pagar", "2104", 4, "LIABILITY", "CREDIT", "Subcuenta analítica", True, None, "Ley del Seguro Social", "Pago de planilla mensual al Instituto Salvadoreño del Seguro Social.", "Retención del 3% laboral más cuota patronal del 7.5%."),
    ("210403", "AFP por pagar", "2104", 4, "LIABILITY", "CREDIT", "Subcuenta analítica", True, None, "Ley SAP El Salvador", "Pago de cotizaciones a Administradoras de Fondos de Pensiones.", "Retención laboral 7.25% más cuota patronal 8.75%."),
    ("22", "PASIVO NO CORRIENTE", "2", 2, "LIABILITY", "CREDIT", "Grupo", False, None, "NIIF PYMES Secc. 4.7", "Amortización de préstamos bancarios de largo plazo.", "Obligaciones financieras pagaderas a más de un año."),
    ("2201", "Préstamos bancarios a largo plazo", "22", 3, "LIABILITY", "CREDIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 11", "Amortización a capital de deudas financieras.", "Contratación de créditos bancarios con vencimiento mayor a 12 meses."),
    ("220101", "Préstamos bancarios", "2201", 4, "LIABILITY", "CREDIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 11.13", "Pagos periódicos al capital del préstamo bancario.", "Desembolso de financiamiento bancario a largo plazo."),

    # 3 PATRIMONIO
    ("3", "PATRIMONIO", None, 1, "EQUITY", "CREDIT", "Clase", False, None, "NIIF PYMES Secc. 2.15(c)", "Disminuciones de capital, retiro de utilidades o pérdidas del ejercicio.", "Aportaciones de dueños/socios y acumulación de resultados favorables."),
    ("31", "CAPITAL", "3", 2, "EQUITY", "CREDIT", "Grupo", False, None, "NIIF PYMES Secc. 22", "Disminución de capital o pérdidas acumuladas.", "Fondos aportados y resultados generados por el salón."),
    ("3101", "Capital social", "31", 3, "EQUITY", "CREDIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 22", "Reducciones de capital social aprobadas.", "Aportes iniciales y posteriores de los propietarios."),
    ("310101", "Capital social", "3101", 4, "EQUITY", "CREDIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 22.7", "Disminución formal del capital social.", "Aporte de capital pagado al inicio de operaciones de Diamond Salón."),
    ("3102", "Resultados", "31", 3, "EQUITY", "CREDIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 5", "Distribución de dividendos y absorción de pérdidas.", "Utilidades del período y utilidades de ejercicios previos."),
    ("310201", "Utilidad del ejercicio", "3102", 4, "EQUITY", "CREDIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 5.4", "Traslado a utilidades acumuladas en período posterior.", "Utilidad neta generada en el cierre contable del ejercicio."),
    ("310202", "Utilidades acumuladas", "3102", 4, "EQUITY", "CREDIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 5.4", "Pago de dividendos o reinversión en el salón.", "Traslado de utilidades netas de ejercicios anteriores."),
    ("310203", "Pérdidas acumuladas (-)", "3102", 4, "EQUITY", "DEBIT", "Cuenta de valuación", True, None, "NIIF PYMES Secc. 5.4", "Absorción de pérdidas del ejercicio con resultados acumulados.", "Amortización o absorción con futuras utilidades."),

    # 4 COSTOS Y GASTOS
    ("4", "COSTOS Y GASTOS", None, 1, "COST", "DEBIT", "Clase", False, None, "NIIF PYMES Secc. 2.23(b)", "Costos y gastos incurridos en la operación y comercialización.", "Liquidación al cierre anual contra cuentas de resultado."),
    ("41", "COSTOS", "4", 2, "COST", "DEBIT", "Grupo", False, None, "NIIF PYMES Secc. 13.20", "Costo directo de ventas y consumo de insumos en cabina.", "Cierre anual contra pérdidas y ganancias."),
    ("4101", "Costo de venta", "41", 3, "COST", "DEBIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 13.20", "Costo de mercadería comercial vendida.", "Reversión por anulación de ventas o cierre anual."),
    ("410101", "Costo de venta de productos (vitrina)", "4101", 4, "COST", "DEBIT", "Costo retail", True, "VITRINA", "NIIF PYMES Secc. 13.20", "Costo promedio ponderado de productos retail descargados de vitrina.", "Reversión de venta o cierre contable del ejercicio."),
    ("4102", "Costo de servicios", "41", 3, "COST", "DEBIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 13.20", "Insumos profesionales utilizados en atenciones de belleza.", "Reversiones o liquidación al cierre anual."),
    ("410201", "Consumo de insumos en servicios (cabina)", "4102", 4, "COST", "DEBIT", "Costo operativo", True, "CABINA", "NIIF PYMES Secc. 13.20", "Insumos (tintes, oxidantes, champú técnico) consumidos en cabina.", "Liquidación al cierre del período fiscal."),
    ("42", "GASTOS", "4", 2, "EXPENSE", "DEBIT", "Grupo", False, None, "NIIF PYMES Secc. 2.42", "Gastos operativos administrativos, de venta y de financiamiento.", "Cancelación de saldos al cierre del ejercicio económico."),
    ("4201", "Gastos de administración", "42", 3, "EXPENSE", "DEBIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 2.42", "Gastos de dirección, alquiler, servicios públicos y suministros.", "Liquidación anual de cuentas de resultados."),
    ("420101", "Sueldos y salarios", "4201", 4, "EXPENSE", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 28", "Remuneraciones devengadas por personal administrativo y operativo.", "Cierre anual contra cuenta de resultados."),
    ("420102", "Agua, energía eléctrica y teléfono", "4201", 4, "EXPENSE", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 2.42", "Consumo de energía de secadores, agua del salón y telecomunicaciones.", "Cierre anual."),
    ("420103", "Alquiler del local", "4201", 4, "EXPENSE", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 20", "Arrendamiento mensual de las instalaciones del atelier.", "Cierre anual."),
    ("420104", "Depreciaciones", "4201", 4, "EXPENSE", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 17", "Gasto por desgaste mensual de equipo de salón y computación.", "Cierre anual."),
    ("420105", "Papelería y útiles", "4201", 4, "EXPENSE", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 2.42", "Papelería, útiles de oficina y mermas menores.", "Cierre anual."),
    ("4202", "Gastos de venta", "42", 3, "EXPENSE", "DEBIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 2.42", "Erogaciones vinculadas directamente a la comercialización.", "Cierre anual de resultados."),
    ("420201", "Publicidad y promoción", "4202", 4, "EXPENSE", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 2.42", "Campañas en redes sociales, folletos y promociones del salón.", "Cierre anual."),
    ("420202", "Comisiones sobre ventas", "4202", 4, "EXPENSE", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 28", "Comisiones variables pagadas a estilistas por ventas o servicios.", "Cierre anual."),
    ("4203", "Gastos financieros", "42", 3, "EXPENSE", "DEBIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 25", "Costos por uso de financiamiento y servicios del sistema bancario.", "Cierre anual."),
    ("420301", "Intereses bancarios", "4203", 4, "EXPENSE", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 25.1", "Intereses causados por préstamos bancarios.", "Cierre anual."),
    ("420302", "Comisiones bancarias", "4203", 4, "EXPENSE", "DEBIT", "Subcuenta analítica", True, None, "NIIF PYMES Secc. 25.1", "Comisiones de manejo de cuenta y transferencias del sistema.", "Cierre anual."),

    # 5 INGRESOS
    ("5", "INGRESOS", None, 1, "INCOME", "CREDIT", "Clase", False, None, "NIIF PYMES Secc. 23", "Cancelaciones o notas de crédito que anulen ventas.", "Ingresos devengados por servicios profesionales y venta de productos."),
    ("51", "INGRESOS DE OPERACIÓN", "5", 2, "INCOME", "CREDIT", "Grupo", False, None, "NIIF PYMES Secc. 23.3", "Notas de crédito y reversiones.", "Facturación ordinaria del giro del salón."),
    ("5101", "Ingresos por servicios de belleza", "51", 3, "INCOME", "CREDIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 23.14", "Reversión por servicios anulados.", "Ventas netas de servicios de peluquería, manos y pies, maquillaje."),
    ("510101", "Servicios de peluquería y estilismo", "5101", 4, "INCOME", "CREDIT", "Rentas ordinarias", True, "CABINA", "NIIF PYMES Secc. 23.14", "Anulación de servicios de cabello o corte.", "Ingreso neto gravado de cortes, tintes, peinados e hidrataciones."),
    ("510102", "Servicios de manos y pies", "5101", 4, "INCOME", "CREDIT", "Rentas ordinarias", True, "CABINA", "NIIF PYMES Secc. 23.14", "Anulación de servicios de uñas.", "Ingreso neto gravado de manicura, pedicura spa, esmaltado y parafina."),
    ("510103", "Maquillaje profesional", "5101", 4, "INCOME", "CREDIT", "Rentas ordinarias", True, "CABINA", "NIIF PYMES Secc. 23.14", "Anulación de servicios de maquillaje.", "Ingreso neto gravado de maquillaje para novias, eventos y pasarela."),
    ("5102", "Ingresos por venta de productos", "51", 3, "INCOME", "CREDIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 23.10", "Devoluciones o anulación de ventas retail.", "Ingreso neto por venta directa en mostrador."),
    ("510201", "Venta de productos cosméticos", "5102", 4, "INCOME", "CREDIT", "Rentas comerciales", True, "VITRINA", "NIIF PYMES Secc. 23.10", "Reversión por devolución de productos vitrina.", "Venta de champús, sérums, mascarillas y esmaltes al público."),
    ("5103", "Otros ingresos", "51", 3, "INCOME", "CREDIT", "Cuenta mayor", False, None, "NIIF PYMES Secc. 2.25(a)", "Cierre anual.", "Ingresos no ordinarios o complementarios del negocio."),
    ("510301", "Ingresos varios", "5103", 4, "INCOME", "CREDIT", "Otros ingresos", True, None, "NIIF PYMES Secc. 2.25(a)", "Cierre anual.", "Sobrantes justificados en recuentos físicos y otros ingresos diversos."),
]

SEED_MAPPINGS = [
    ("CASH", "110101", "Cobros y pagos en efectivo"),
    ("BANK", "110103", "Cobros con tarjeta / transferencias (Cta Cte)"),
    ("ACCOUNTS_RECEIVABLE", "110201", "Ventas al crédito"),
    ("INVENTORY_VITRINA", "110401", "Inventario de mercadería para la venta"),
    ("INVENTORY_CABINA", "110402", "Inventario de insumos para servicios"),
    ("IVA_CREDIT", "110301", "IVA crédito fiscal en compras"),
    ("IVA_PERCEIVED", "110301", "IVA percibido / retención a favor"),
    ("ACCOUNTS_PAYABLE", "210101", "Compras al crédito"),
    ("IVA_DEBIT", "210201", "IVA débito fiscal en ventas"),
    ("IVA_PAYABLE", "210301", "Liquidación mensual de IVA"),
    ("COST_OF_SALES", "410101", "Costo de venta de productos (vitrina)"),
    ("SERVICE_SUPPLY_COST", "410201", "Consumo de insumos en servicios (cabina)"),
    ("INVENTORY_SHORTAGE", "420105", "Ajustes negativos / mermas de inventario"),
    ("INVENTORY_SURPLUS", "510301", "Ajustes positivos de inventario"),
    ("INCOME_SERVICES", "510101", "Ventas de servicios de peluquería"),
    ("INCOME_PRODUCTS", "510201", "Ventas de productos cosméticos"),
    ("RETAINED_EARNINGS", "310202", "Cierre anual de resultados"),
]


def seed_accounting_data(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(PG_TRIGGERS_SQL, params=None)

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
                ("110103", "Saldo inicial en Bancos cuenta corriente", Decimal("3400.00"), Decimal("0.00")),
                ("110401", "Inventario inicial mercadería vitrina (costo promedio)", Decimal("746.50"), Decimal("0.00")),
                ("110402", "Inventario inicial insumos cabina (costo promedio)", Decimal("480.00"), Decimal("0.00")),
                ("120101", "Mobiliario y equipo de estación Diamond Salón", Decimal("4523.50"), Decimal("0.00")),
                ("310101", "Capital social — Apertura Atelier", Decimal("0.00"), Decimal("11000.00")),
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
                ("110401", "Ingreso de champús y mascarillas retail a Vitrina", Decimal("150.00"), Decimal("0.00")),
                ("110301", "IVA crédito fiscal 13% s/ CCF-4521", Decimal("19.50"), Decimal("0.00")),
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
                ("110402", "Ingreso de insumos técnicos a Cabina 1 y 2", Decimal("90.00"), Decimal("0.00")),
                ("110301", "IVA crédito fiscal 13% s/ CCF-4522", Decimal("11.70"), Decimal("0.00")),
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
                ("510101", "Ingreso neto por servicio de peluquería en cabina", Decimal("0.00"), Decimal("22.12")),
                ("210201", "IVA débito fiscal 13% incluido en FCF-0012", Decimal("0.00"), Decimal("2.88")),
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
                ("510201", "Ingreso neto por venta de producto cosmético", Decimal("0.00"), Decimal("10.62")),
                ("210201", "IVA débito fiscal 13% incluido en FCF-0013", Decimal("0.00"), Decimal("1.38")),
                ("410101", "Costo de venta a promedio ponderado (1 u. x $7.00)", Decimal("7.00"), Decimal("0.00")),
                ("110401", "Descargo de inventario vitrina FCF-0013", Decimal("0.00"), Decimal("7.00")),
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
                ("110402", "Salida de insumos de Cabina 1 por consumo", Decimal("0.00"), Decimal("18.50")),
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
