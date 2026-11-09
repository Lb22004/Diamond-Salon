from datetime import date, datetime, timezone
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from apps.accounting.models import Account, AccountMapping, JournalEntry, JournalEntryLine
from apps.core.models import AccountingPeriod, Company, Employee, PeriodStatus, User
from apps.inventory.models import (
    Adjustment,
    Category,
    Consumption,
    InventoryMovement,
    Location,
    Product,
    Stock,
)
from apps.purchases.models import Purchase, PurchaseLine, Supplier, SupplierPayment
from apps.sales.models import Customer, DocumentSeries, Sale, SaleLine, Service


SEED_ACCOUNTS = [
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


class Command(BaseCommand):
    help = "Seeds comprehensive mock data conforming to official Catálogo de Cuentas (Table 1 NIIF PYMES)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset existing transactions and re-populate fresh November 2026 data.",
        )

    def handle(self, *args, **options):
        reset = options.get("reset", False)
        self.stdout.write(self.style.MIGRATE_HEADING("=== SEEDING DIAMOND SALÓN MOCK DATA ==="))

        with transaction.atomic():
            # 1. Accounts & Hierarchy
            self.stdout.write("1. Verifying and updating 82 official accounts...")
            code_to_acc = {}
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
                    parent_obj = code_to_acc.get(parent_code) if parent_code else None
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
                    code_to_acc[code] = acc

            self.stdout.write(self.style.SUCCESS(f"   [OK] {len(code_to_acc)} accounts loaded."))

            # 2. Account Mappings
            self.stdout.write("2. Updating account mappings...")
            for key, code, desc in SEED_MAPPINGS:
                AccountMapping.objects.update_or_create(
                    key=key,
                    defaults={"account": code_to_acc[code], "description": desc},
                )
            self.stdout.write(self.style.SUCCESS(f"   [OK] {len(SEED_MAPPINGS)} mappings verified."))

            # 3. Company
            company, _ = Company.objects.update_or_create(
                pk=1,
                defaults={
                    "legal_name": "Diamond Salón Atelier S.A. de C.V.",
                    "trade_name": "Diamond Salón — Atelier Contable",
                    "nrc": "305921-8",
                    "nit": "0614-280320-103-1",
                    "activity_code": "96020",
                    "activity_description": "Servicios de peluquería y otros tratamientos de belleza",
                    "address": "Avenida Masferrer Norte #425, Colonia Escalón, San Salvador",
                    "phone": "2288-9900",
                    "email": "contacto@diamondsalon.sv",
                    "taxpayer_category": "MEDIUM",
                    "general_iva_rate": Decimal("0.1300"),
                    "income_tax_rate": Decimal("0.3000"),
                    "large_taxpayer_retention_rate": Decimal("0.0100"),
                    "freelance_renta_retention_rate": Decimal("0.1000"),
                    "currency_code": "USD",
                    "currency_symbol": "$",
                },
            )

            # 4. Users & Employees
            self.stdout.write("3. Verifying users and stylists...")
            users_info = [
                ("admin", "Admin123!*", "Maira", "Gómez", "admin@diamondsalon.sv", User.Role.ADMIN),
                ("contador", "Contador123!*", "Jose Roberto", "Auditor", "contador@diamondsalon.sv", User.Role.ACCOUNTANT),
                ("compras", "Compras123!*", "Víctor", "Flores", "compras@diamondsalon.sv", User.Role.PURCHASING),
                ("estilista", "Estilista123!*", "Ferdinand", "Silva", "estilista@diamondsalon.sv", User.Role.CASHIER),
            ]
            user_map = {}
            for uname, pwd, fname, lname, email, role in users_info:
                u, created = User.objects.get_or_create(
                    username=uname,
                    defaults={"first_name": fname, "last_name": lname, "email": email, "role": role},
                )
                u.first_name = fname
                u.last_name = lname
                u.email = email
                u.role = role
                u.is_active = True
                u.is_staff = role in (User.Role.ADMIN, User.Role.ACCOUNTANT)
                u.is_superuser = role == User.Role.ADMIN
                u.set_password(pwd)
                u.save()
                user_map[uname] = u

            emp_stylist, _ = Employee.objects.update_or_create(
                full_name="Ferdinand Silva",
                defaults={
                    "position": Employee.Position.STYLIST,
                    "is_active": True,
                },
            )
            emp_victor, _ = Employee.objects.update_or_create(
                full_name="Víctor Flores",
                defaults={
                    "position": Employee.Position.OTHER,
                    "is_active": True,
                },
            )

            # 5. Periods (2026)
            self.stdout.write("4. Configuring fiscal periods 2026...")
            nov_period = None
            for m in range(1, 13):
                p_status = PeriodStatus.CLOSED if m < 11 else PeriodStatus.OPEN
                p_active = m == 11
                p_start = date(2026, m, 1)
                p_end = (
                    date(2026, 11, 30)
                    if m == 11
                    else date(2026, 12, 31)
                    if m == 12
                    else date(2026, m + 1, 1).replace(day=1) - date.resolution
                )
                p_closed_at = datetime(2026, m, 28, 18, 0, tzinfo=timezone.utc) if p_status == PeriodStatus.CLOSED else None
                p_closed_by = user_map["admin"] if p_status == PeriodStatus.CLOSED else None
                p, _ = AccountingPeriod.objects.update_or_create(
                    year=2026,
                    month=m,
                    defaults={
                        "name": f"{['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'][m-1]} 2026",
                        "start_date": p_start,
                        "end_date": p_end,
                        "status": p_status,
                        "is_active": p_active,
                        "closed_at": p_closed_at,
                        "closed_by": p_closed_by,
                    },
                )
                if m == 11:
                    nov_period = p

            # 6. Document Series
            DocumentSeries.objects.update_or_create(
                doc_type="FCF",
                defaults={"prefix": "FCF-", "next_number": 16, "resolution": "RES-DGII-2026-00142", "authorized_from": 1, "authorized_to": 9999, "is_active": True, "valid_from": date(2026, 1, 1)},
            )
            DocumentSeries.objects.update_or_create(
                doc_type="CCF",
                defaults={"prefix": "CCF-", "next_number": 2, "resolution": "RES-DGII-2026-00143", "authorized_from": 1, "authorized_to": 9999, "is_active": True, "valid_from": date(2026, 1, 1)},
            )
            DocumentSeries.objects.update_or_create(
                doc_type="NC",
                defaults={"prefix": "NC-", "next_number": 1, "resolution": "RES-DGII-2026-00144", "authorized_from": 1, "authorized_to": 999, "is_active": True, "valid_from": date(2026, 1, 1)},
            )

            # 7. Locations
            loc_vit, _ = Location.objects.update_or_create(code="VIT", defaults={"name": "Vitrina", "location_type": "VITRINA", "is_active": True})
            loc_cab1, _ = Location.objects.update_or_create(code="CAB1", defaults={"name": "Cabina 1", "location_type": "CABINA", "is_active": True})
            loc_cab2, _ = Location.objects.update_or_create(code="CAB2", defaults={"name": "Cabina 2", "location_type": "CABINA", "is_active": True})
            loc_gen, _ = Location.objects.update_or_create(code="GEN", defaults={"name": "General", "location_type": "WAREHOUSE", "is_active": True})

            # 8. Categories
            cat_hair_vit, _ = Category.objects.get_or_create(name="Cuidado Capilar Retail", inventory_type="VITRINA")
            cat_nails_vit, _ = Category.objects.get_or_create(name="Cosmética & Esmaltes", inventory_type="VITRINA")
            cat_color_cab, _ = Category.objects.get_or_create(name="Colorimetría & Químicos", inventory_type="CABINA")
            cat_supply_cab, _ = Category.objects.get_or_create(name="Insumos Descartables & Solventes", inventory_type="CABINA")

            # 9. Suppliers
            sup_bella, _ = Supplier.objects.update_or_create(
                nit="0614-120415-102-8",
                defaults={
                    "name": "Distribuidora Bella",
                    "trade_name": "Distribuidora Cosmética S.A. de C.V.",
                    "nrc": "240812-4",
                    "taxpayer_category": "LARGE",
                    "brands_description": "L'Oréal, Kérastase",
                    "contact_name": "Claudia Solís",
                    "phone": "2264-8800",
                    "email": "facturacion@distribuidorabella.com.sv",
                    "address": "Zona Industrial Santa Elena, Antiguo Cuscatlán",
                    "is_active": True,
                },
            )
            sup_insumos, _ = Supplier.objects.update_or_create(
                nit="0614-190818-105-1",
                defaults={
                    "name": "Insumos Pro",
                    "trade_name": "Insumos Pro S.A. de C.V.",
                    "nrc": "261904-8",
                    "taxpayer_category": "MEDIUM",
                    "brands_description": "Químicos & Decolorantes",
                    "contact_name": "Héctor Méndez",
                    "phone": "2243-5190",
                    "email": "ventas@insumospro.com.sv",
                    "address": "Colonia Escalón, San Salvador",
                    "is_active": True,
                },
            )
            sup_color, _ = Supplier.objects.update_or_create(
                nit="0614-251120-109-3",
                defaults={
                    "name": "Color & Style",
                    "trade_name": "Color & Style Atelier S.A. de C.V.",
                    "nrc": "289103-1",
                    "taxpayer_category": "MEDIUM",
                    "brands_description": "Tintes Orgánicos",
                    "contact_name": "Valeria Rivas",
                    "phone": "2298-3412",
                    "email": "pedidos@colorandstyle.com.sv",
                    "address": "Boulevard del Hipódromo, San Benito",
                    "is_active": True,
                },
            )

            # 10. Customers
            cust_final, _ = Customer.objects.update_or_create(
                name="Consumidor final",
                defaults={"customer_type": Customer.CustomerType.FINAL_CONSUMER, "is_generic": True, "is_active": True},
            )
            cust_ana, _ = Customer.objects.update_or_create(
                name="Ana Mejía",
                defaults={
                    "customer_type": Customer.CustomerType.FINAL_CONSUMER,
                    "document_type": Customer.DocumentType.DUI,
                    "document_number": "02458190-3",
                    "phone": "7102-3344",
                    "email": "ana.mejia@gmail.com",
                    "is_active": True,
                },
            )
            cust_rosa, _ = Customer.objects.update_or_create(
                name="Rosa Flores",
                defaults={
                    "customer_type": Customer.CustomerType.FINAL_CONSUMER,
                    "document_type": Customer.DocumentType.DUI,
                    "document_number": "01893201-7",
                    "phone": "7245-8899",
                    "email": "rosa.flores@yahoo.com",
                    "is_active": True,
                },
            )
            cust_eventos, _ = Customer.objects.update_or_create(
                name="Eventos & Moda S.A. de C.V.",
                defaults={
                    "customer_type": Customer.CustomerType.TAXPAYER,
                    "document_type": Customer.DocumentType.NIT,
                    "document_number": "0614-110515-101-9",
                    "nrc": "194028-2",
                    "economic_activity": "Agencias de modelaje y organización de eventos",
                    "is_large_taxpayer": True,
                    "phone": "2255-7788",
                    "email": "contabilidad@eventosymoda.com.sv",
                    "address": "Calle La Mascota #310, San Salvador",
                    "is_active": True,
                },
            )

            # 11. Products (4 Vitrina, 4 Cabina)
            prod_vit_1, _ = Product.objects.update_or_create(
                sku="VIT-001",
                defaults={
                    "barcode": "750100110001",
                    "name": "Champú nutritivo 300ml",
                    "brand": "L'Oréal Professionnel Serie Expert",
                    "presentation": "300ml",
                    "category": cat_hair_vit,
                    "inventory_type": "VITRINA",
                    "unit_of_measure": "UNIDAD",
                    "average_cost": Decimal("7.0000"),
                    "sale_price": Decimal("12.00"),
                    "min_stock": Decimal("5.000"),
                    "account": code_to_acc["110401"],
                    "is_active": True,
                },
            )
            prod_vit_2, _ = Product.objects.update_or_create(
                sku="VIT-002",
                defaults={
                    "barcode": "750100110002",
                    "name": "Mascarilla reconstructiva 250ml",
                    "brand": "Kérastase Resistance 250ml",
                    "presentation": "250ml",
                    "category": cat_hair_vit,
                    "inventory_type": "VITRINA",
                    "unit_of_measure": "UNIDAD",
                    "average_cost": Decimal("24.0000"),
                    "sale_price": Decimal("22.00"),
                    "min_stock": Decimal("5.000"),
                    "account": code_to_acc["110401"],
                    "is_active": True,
                },
            )
            prod_vit_3, _ = Product.objects.update_or_create(
                sku="VIT-003",
                defaults={
                    "barcode": "750100110003",
                    "name": "Sérum de brillo 100ml",
                    "brand": "Moroccanoil Treatment 100ml",
                    "presentation": "100ml",
                    "category": cat_hair_vit,
                    "inventory_type": "VITRINA",
                    "unit_of_measure": "UNIDAD",
                    "average_cost": Decimal("10.5000"),
                    "sale_price": Decimal("18.00"),
                    "min_stock": Decimal("8.000"),  # Alerta crítico
                    "account": code_to_acc["110401"],
                    "is_active": True,
                },
            )
            prod_vit_4, _ = Product.objects.update_or_create(
                sku="VIT-004",
                defaults={
                    "barcode": "750100110004",
                    "name": "Esmalte profesional OPI",
                    "brand": "OPI Nail Lacquer Palette Atelier",
                    "presentation": "Frasco 15ml",
                    "category": cat_nails_vit,
                    "inventory_type": "VITRINA",
                    "unit_of_measure": "UNIDAD",
                    "average_cost": Decimal("17.0400"),
                    "sale_price": Decimal("6.50"),
                    "min_stock": Decimal("10.000"),
                    "account": code_to_acc["110401"],
                    "is_active": True,
                },
            )

            # Cabina products
            prod_cab_1, _ = Product.objects.update_or_create(
                sku="CAB-001",
                defaults={
                    "barcode": "750100220001",
                    "name": "Tinte / colorante Majirel",
                    "brand": "Majirel Tubos 50ml (Gama Castaños)",
                    "presentation": "Tubo 50ml",
                    "category": cat_color_cab,
                    "inventory_type": "CABINA",
                    "unit_of_measure": "UNIDAD",
                    "average_cost": Decimal("15.0000"),
                    "sale_price": None,
                    "min_stock": Decimal("10.000"),
                    "account": code_to_acc["110402"],
                    "is_active": True,
                },
            )
            prod_cab_2, _ = Product.objects.update_or_create(
                sku="CAB-002",
                defaults={
                    "barcode": "750100220002",
                    "name": "Acondicionador sellador pH",
                    "brand": "pH Acidifying Rinse Garrafa 1000ml",
                    "presentation": "Garrafa 1L",
                    "category": cat_color_cab,
                    "inventory_type": "CABINA",
                    "unit_of_measure": "UNIDAD",
                    "average_cost": Decimal("45.0000"),
                    "sale_price": None,
                    "min_stock": Decimal("6.000"),  # Alerta crítico
                    "account": code_to_acc["110402"],
                    "is_active": True,
                },
            )
            prod_cab_3, _ = Product.objects.update_or_create(
                sku="CAB-003",
                defaults={
                    "barcode": "750100220003",
                    "name": "Acetona pura solvente técnico",
                    "brand": "Solvente grado técnico para remoción",
                    "presentation": "Litro",
                    "category": cat_supply_cab,
                    "inventory_type": "CABINA",
                    "unit_of_measure": "LITRO",
                    "average_cost": Decimal("24.5000"),
                    "sale_price": None,
                    "min_stock": Decimal("3.000"),
                    "account": code_to_acc["110402"],
                    "is_active": True,
                },
            )
            prod_cab_4, _ = Product.objects.update_or_create(
                sku="CAB-004",
                defaults={
                    "barcode": "750100220004",
                    "name": "Algodón / insumos descartables",
                    "brand": "Paquetes desmaquillantes prensados",
                    "presentation": "Paquete 100u",
                    "category": cat_supply_cab,
                    "inventory_type": "CABINA",
                    "unit_of_measure": "UNIDAD",
                    "average_cost": Decimal("3.1167"),
                    "sale_price": None,
                    "min_stock": Decimal("10.000"),
                    "account": code_to_acc["110402"],
                    "is_active": True,
                },
            )

            # 12. Services
            srv_1, _ = Service.objects.update_or_create(
                code="SRV-001",
                defaults={"name": "Servicio: corte y peinado", "category": "STYLING", "price": Decimal("25.00"), "income_account": code_to_acc["510101"], "is_active": True},
            )
            srv_2, _ = Service.objects.update_or_create(
                code="SRV-002",
                defaults={"name": "Servicio: manicura + esmaltado", "category": "NAILS", "price": Decimal("15.00"), "income_account": code_to_acc["510102"], "is_active": True},
            )
            srv_3, _ = Service.objects.update_or_create(
                code="SRV-003",
                defaults={"name": "Balayage & Colorimetría Couture", "category": "COLOR", "price": Decimal("85.00"), "income_account": code_to_acc["510101"], "is_active": True},
            )
            srv_4, _ = Service.objects.update_or_create(
                code="SRV-004",
                defaults={"name": "Ritual Keratina & Hidratación Profunda", "category": "TREATMENT", "price": Decimal("45.00"), "income_account": code_to_acc["510101"], "is_active": True},
            )
            srv_5, _ = Service.objects.update_or_create(
                code="SRV-005",
                defaults={"name": "Peinado de Gala & Maquillaje Editorial", "category": "STYLING", "price": Decimal("60.00"), "income_account": code_to_acc["510103"], "is_active": True},
            )

            # 13. Stocks (Exact Vista 2 quantities: 42 Vitrina items, 26 Cabina items)
            Stock.objects.update_or_create(product=prod_vit_1, location=loc_vit, defaults={"quantity": Decimal("18.000")})
            Stock.objects.update_or_create(product=prod_vit_2, location=loc_vit, defaults={"quantity": Decimal("11.000")})
            Stock.objects.update_or_create(product=prod_vit_3, location=loc_vit, defaults={"quantity": Decimal("7.000")})
            Stock.objects.update_or_create(product=prod_vit_4, location=loc_vit, defaults={"quantity": Decimal("25.000")})

            Stock.objects.update_or_create(product=prod_cab_1, location=loc_cab1, defaults={"quantity": Decimal("9.000")})
            Stock.objects.update_or_create(product=prod_cab_2, location=loc_cab2, defaults={"quantity": Decimal("5.000")})
            Stock.objects.update_or_create(product=prod_cab_3, location=loc_gen, defaults={"quantity": Decimal("4.000")})
            Stock.objects.update_or_create(product=prod_cab_4, location=loc_gen, defaults={"quantity": Decimal("30.000")})

            self.stdout.write(self.style.SUCCESS("   [OK] Products, stock, and services initialized."))

            # 14. Transactions for November 2026
            # If reset or no journal entries, create the complete verified set
            if reset:
                self.stdout.write("   Cleaning old November 2026 transactions for clean reset...")
                SaleLine.objects.filter(sale__period=nov_period).delete()
                Sale.objects.filter(period=nov_period).delete()
                SupplierPayment.objects.filter(purchase__period=nov_period).delete()
                PurchaseLine.objects.filter(purchase__period=nov_period).delete()
                Purchase.objects.filter(period=nov_period).delete()
                Consumption.objects.filter(consumption_date__year=2026, consumption_date__month=11).delete()
                Adjustment.objects.filter(adjustment_date__year=2026, adjustment_date__month=11).delete()
                with connection.cursor() as cursor:
                    if connection.vendor == "postgresql":
                        cursor.execute("ALTER TABLE inventory_movement DISABLE TRIGGER ALL;")
                        cursor.execute("DELETE FROM inventory_movement WHERE EXTRACT(YEAR FROM movement_date) = 2026 AND EXTRACT(MONTH FROM movement_date) = 11;")
                        cursor.execute("ALTER TABLE inventory_movement ENABLE TRIGGER ALL;")

                        cursor.execute("ALTER TABLE accounting_journal_entry_line DISABLE TRIGGER ALL;")
                        cursor.execute("ALTER TABLE accounting_journal_entry DISABLE TRIGGER ALL;")
                        cursor.execute("DELETE FROM accounting_journal_entry_line WHERE entry_id IN (SELECT id FROM accounting_journal_entry WHERE period_id = %s);", [nov_period.id])
                        cursor.execute("DELETE FROM accounting_journal_entry WHERE period_id = %s;", [nov_period.id])
                        cursor.execute("ALTER TABLE accounting_journal_entry_line ENABLE TRIGGER ALL;")
                        cursor.execute("ALTER TABLE accounting_journal_entry ENABLE TRIGGER ALL;")
                    else:
                        InventoryMovement.objects.filter(movement_date__year=2026, movement_date__month=11).delete()
                        JournalEntryLine.objects.filter(entry__period=nov_period).delete()
                        JournalEntry.objects.filter(period=nov_period).delete()

            creator = user_map["contador"]

            if not JournalEntry.objects.filter(period=nov_period).exists():
                self.stdout.write("5. Posting balanced November 2026 operations...")

                entries_data = [
                    # 1. Apertura
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
                            ("110401", "Inventario inicial mercadería vitrina (costo promedio)", Decimal("756.00"), Decimal("0.00")),
                            ("110402", "Inventario inicial insumos cabina (costo promedio)", Decimal("480.00"), Decimal("0.00")),
                            ("120101", "Mobiliario y equipo de estación Diamond Salón", Decimal("4514.00"), Decimal("0.00")),
                            ("310101", "Capital social — Apertura Atelier", Decimal("0.00"), Decimal("11000.00")),
                        ],
                    ),
                    # 2. Compra CCF-4521 Bella
                    (
                        2,
                        date(2026, 11, 1),
                        "Compra CCF-4521 Distribuidora Bella · Mercadería para Vitrina al crédito",
                        "PURCHASE",
                        "purchases.purchase",
                        1,
                        [
                            ("110401", "Ingreso de champús y mascarillas retail a Vitrina", Decimal("150.00"), Decimal("0.00")),
                            ("110301", "IVA crédito fiscal 13% s/ CCF-4521", Decimal("19.50"), Decimal("0.00")),
                            ("210101", "Cuenta por pagar a Distribuidora Bella", Decimal("0.00"), Decimal("169.50")),
                        ],
                    ),
                    # 3. Compra CCF-4522 Insumos Pro
                    (
                        3,
                        date(2026, 11, 1),
                        "Compra CCF-4522 Insumos Pro · Tintes y peróxidos para Cabina al crédito",
                        "PURCHASE",
                        "purchases.purchase",
                        2,
                        [
                            ("110402", "Ingreso de insumos técnicos a Cabina 1 y 2", Decimal("90.00"), Decimal("0.00")),
                            ("110301", "IVA crédito fiscal 13% s/ CCF-4522", Decimal("11.70"), Decimal("0.00")),
                            ("210101", "Cuenta por pagar a Insumos Pro", Decimal("0.00"), Decimal("101.70")),
                        ],
                    ),
                    # 4. Compra CCF-4530 Color & Style
                    (
                        4,
                        date(2026, 11, 3),
                        "Compra CCF-4530 Color & Style · Tintes orgánicos para Cabina al crédito",
                        "PURCHASE",
                        "purchases.purchase",
                        3,
                        [
                            ("110402", "Ingreso de tintes orgánicos a Cabina", Decimal("60.00"), Decimal("0.00")),
                            ("110301", "IVA crédito fiscal 13% s/ CCF-4530", Decimal("7.80"), Decimal("0.00")),
                            ("210101", "Cuenta por pagar a Color & Style", Decimal("0.00"), Decimal("67.80")),
                        ],
                    ),
                    # 5. Venta FCF-0012 Ana Mejía
                    (
                        5,
                        date(2026, 11, 2),
                        "Venta FCF-0012 · Servicio de corte y peinado en Cabina (Efectivo)",
                        "SALE",
                        "sales.sale",
                        1,
                        [
                            ("110101", "Cobro en efectivo FCF-0012", Decimal("25.00"), Decimal("0.00")),
                            ("510101", "Ingreso neto por servicio de peluquería en cabina", Decimal("0.00"), Decimal("22.12")),
                            ("210201", "IVA débito fiscal 13% incluido en FCF-0012", Decimal("0.00"), Decimal("2.88")),
                        ],
                    ),
                    # 6. Venta FCF-0013 Consumidor Final
                    (
                        6,
                        date(2026, 11, 3),
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
                    # 7. Venta FCF-0014 Rosa Flores
                    (
                        7,
                        date(2026, 11, 4),
                        "Venta FCF-0014 · Servicio manicura + esmaltado en Cabina (Efectivo)",
                        "SALE",
                        "sales.sale",
                        3,
                        [
                            ("110101", "Cobro en efectivo FCF-0014", Decimal("15.00"), Decimal("0.00")),
                            ("510102", "Ingreso neto por servicio de manos y pies", Decimal("0.00"), Decimal("13.27")),
                            ("210201", "IVA débito fiscal 13% incluido en FCF-0014", Decimal("0.00"), Decimal("1.73")),
                        ],
                    ),
                    # 8. Venta FCF-0015 Consumidor Final
                    (
                        8,
                        date(2026, 11, 5),
                        "Venta FCF-0015 · Sérum de brillo 100ml (Vitrina) + descargo al costo promedio",
                        "SALE",
                        "sales.sale",
                        4,
                        [
                            ("110101", "Cobro en efectivo FCF-0015", Decimal("18.00"), Decimal("0.00")),
                            ("510201", "Ingreso neto por venta de producto cosmético", Decimal("0.00"), Decimal("15.93")),
                            ("210201", "IVA débito fiscal 13% incluido en FCF-0015", Decimal("0.00"), Decimal("2.07")),
                            ("410101", "Costo de venta a promedio ponderado (1 u. x $9.50)", Decimal("9.50"), Decimal("0.00")),
                            ("110401", "Descargo de inventario vitrina FCF-0015", Decimal("0.00"), Decimal("9.50")),
                        ],
                    ),
                    # 9. Consumo diario de insumos Cabina
                    (
                        9,
                        date(2026, 11, 7),
                        "Consumo diario de insumos en Cabina 1 · Estilista Ferdinand S.",
                        "INVENTORY",
                        "inventory.consumption",
                        1,
                        [
                            ("410201", "Aplicación de tinte y oxidante en servicios del período", Decimal("78.50"), Decimal("0.00")),
                            ("110402", "Salida de insumos de Cabina por consumo técnico", Decimal("0.00"), Decimal("78.50")),
                        ],
                    ),
                    # 10. Pago a proveedor Insumos Pro CCF-4522
                    (
                        10,
                        date(2026, 11, 8),
                        "Pago a proveedor Insumos Pro · Cancelación CCF-4522 en efectivo",
                        "PAYMENT",
                        "purchases.supplierpayment",
                        1,
                        [
                            ("210101", "Liquidación de saldo CCF-4522 Insumos Pro", Decimal("101.70"), Decimal("0.00")),
                            ("110101", "Egreso de Caja General por pago a proveedor", Decimal("0.00"), Decimal("101.70")),
                        ],
                    ),
                ]

                now_ts = datetime(2026, 11, 8, 18, 0, 0, tzinfo=timezone.utc)
                jentry_map = {}
                for entry_no, entry_date, desc, entry_type, src_app, src_id, lines in entries_data:
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
                            account=code_to_acc[acc_code],
                            description=line_desc,
                            debit=d_amt,
                            credit=c_amt,
                        )
                        total_d += d_amt
                        total_c += c_amt

                    entry.entry_number = entry_no
                    entry.status = "POSTED"
                    entry.total_debit = total_d
                    entry.total_credit = total_c
                    entry.posted_by = creator
                    entry.posted_at = now_ts
                    entry.save()
                    jentry_map[entry_no] = entry

                # Series for Sales
                series_fcf, _ = DocumentSeries.objects.get_or_create(
                    doc_type="FCF",
                    defaults={
                        "prefix": "FCF-",
                        "resolution": "RES-2026-001",
                        "authorized_from": 1,
                        "authorized_to": 9999,
                        "next_number": 16,
                        "valid_from": date(2026, 1, 1),
                        "is_active": True,
                    },
                )
                series_ccf, _ = DocumentSeries.objects.get_or_create(
                    doc_type="CCF",
                    defaults={
                        "prefix": "CCF-",
                        "resolution": "RES-2026-002",
                        "authorized_from": 1,
                        "authorized_to": 9999,
                        "next_number": 1,
                        "valid_from": date(2026, 1, 1),
                        "is_active": True,
                    },
                )

                # Link Purchases to their JournalEntries
                p1, _ = Purchase.objects.update_or_create(
                    supplier=sup_bella,
                    doc_type="CCF",
                    doc_number="CCF-4521",
                    defaults={
                        "destination": "VITRINA",
                        "doc_date": date(2026, 11, 1),
                        "period": nov_period,
                        "payment_condition": "CREDIT",
                        "due_date": date(2026, 11, 30),
                        "amount_paid": Decimal("0.00"),
                        "payment_status": "PENDING",
                        "taxable_amount": Decimal("150.00"),
                        "exempt_amount": Decimal("0.00"),
                        "iva_credit": Decimal("19.50"),
                        "iva_perceived": Decimal("0.00"),
                        "total": Decimal("169.50"),
                        "status": "REGISTERED",
                        "journal_entry": jentry_map.get(2),
                        "created_by": user_map["compras"],
                    },
                )
                PurchaseLine.objects.update_or_create(
                    purchase=p1,
                    line_no=1,
                    defaults={
                        "product": prod_vit_1,
                        "location": loc_vit,
                        "description": "Champú nutritivo 300ml - Lote retail L'Oréal",
                        "quantity": Decimal("10.000"),
                        "unit_cost": Decimal("7.0000"),
                        "taxable_amount": Decimal("70.00"),
                        "iva_amount": Decimal("9.10"),
                    },
                )
                PurchaseLine.objects.update_or_create(
                    purchase=p1,
                    line_no=2,
                    defaults={
                        "product": prod_vit_2,
                        "location": loc_vit,
                        "description": "Mascarilla reconstructiva 250ml - Kérastase",
                        "quantity": Decimal("7.272"),
                        "unit_cost": Decimal("11.0000"),
                        "taxable_amount": Decimal("80.00"),
                        "iva_amount": Decimal("10.40"),
                    },
                )

                p2, _ = Purchase.objects.update_or_create(
                    supplier=sup_insumos,
                    doc_type="CCF",
                    doc_number="CCF-4522",
                    defaults={
                        "destination": "CABINA",
                        "doc_date": date(2026, 11, 1),
                        "period": nov_period,
                        "payment_condition": "CREDIT",
                        "due_date": date(2026, 11, 8),
                        "amount_paid": Decimal("101.70"),
                        "payment_status": "PAID",
                        "taxable_amount": Decimal("90.00"),
                        "exempt_amount": Decimal("0.00"),
                        "iva_credit": Decimal("11.70"),
                        "iva_perceived": Decimal("0.00"),
                        "total": Decimal("101.70"),
                        "status": "REGISTERED",
                        "journal_entry": jentry_map.get(3),
                        "created_by": user_map["compras"],
                    },
                )
                PurchaseLine.objects.update_or_create(
                    purchase=p2,
                    line_no=1,
                    defaults={
                        "product": prod_cab_1,
                        "location": loc_cab1,
                        "description": "Tinte Majirel Tubos 50ml (Insumos técnicos)",
                        "quantity": Decimal("9.000"),
                        "unit_cost": Decimal("10.0000"),
                        "taxable_amount": Decimal("90.00"),
                        "iva_amount": Decimal("11.70"),
                    },
                )

                p3, _ = Purchase.objects.update_or_create(
                    supplier=sup_color,
                    doc_type="CCF",
                    doc_number="CCF-4530",
                    defaults={
                        "destination": "CABINA",
                        "doc_date": date(2026, 11, 3),
                        "period": nov_period,
                        "payment_condition": "CREDIT",
                        "due_date": date(2026, 11, 30),
                        "amount_paid": Decimal("0.00"),
                        "payment_status": "PENDING",
                        "taxable_amount": Decimal("60.00"),
                        "exempt_amount": Decimal("0.00"),
                        "iva_credit": Decimal("7.80"),
                        "iva_perceived": Decimal("0.00"),
                        "total": Decimal("67.80"),
                        "status": "REGISTERED",
                        "journal_entry": jentry_map.get(4),
                        "created_by": user_map["compras"],
                    },
                )
                PurchaseLine.objects.update_or_create(
                    purchase=p3,
                    line_no=1,
                    defaults={
                        "product": prod_cab_1,
                        "location": loc_cab1,
                        "description": "Tintes Orgánicos Color & Style (Insumos cabina)",
                        "quantity": Decimal("4.000"),
                        "unit_cost": Decimal("15.0000"),
                        "taxable_amount": Decimal("60.00"),
                        "iva_amount": Decimal("7.80"),
                    },
                )

                SupplierPayment.objects.update_or_create(
                    purchase=p2,
                    payment_date=date(2026, 11, 8),
                    defaults={
                        "amount": Decimal("101.70"),
                        "payment_method": "CASH",
                        "reference": "Cancelación contado CCF-4522",
                        "cash_account": code_to_acc["110101"],
                        "journal_entry": jentry_map.get(10),
                        "created_by": user_map["compras"],
                    },
                )

                # Link Sales to their JournalEntries
                s1, _ = Sale.objects.update_or_create(
                    doc_type="FCF",
                    doc_number="FCF-0012",
                    defaults={
                        "series": series_fcf,
                        "sale_date": date(2026, 11, 2),
                        "period": nov_period,
                        "customer": cust_ana,
                        "employee": emp_stylist,
                        "payment_method": "CASH",
                        "taxable_amount": Decimal("22.12"),
                        "exempt_amount": Decimal("0.00"),
                        "non_subject_amount": Decimal("0.00"),
                        "iva_amount": Decimal("2.88"),
                        "iva_withheld": Decimal("0.00"),
                        "total": Decimal("25.00"),
                        "status": "ISSUED",
                        "journal_entry": jentry_map.get(5),
                        "created_by": user_map["estilista"],
                    },
                )
                SaleLine.objects.update_or_create(
                    sale=s1,
                    line_no=1,
                    defaults={
                        "line_type": "SERVICE",
                        "service": srv_1,
                        "description": "Servicio: corte y peinado",
                        "quantity": Decimal("1.000"),
                        "unit_price": Decimal("25.00"),
                        "discount": Decimal("0.00"),
                        "taxable_amount": Decimal("22.12"),
                        "iva_amount": Decimal("2.88"),
                        "total": Decimal("25.00"),
                    },
                )

                s2, _ = Sale.objects.update_or_create(
                    doc_type="FCF",
                    doc_number="FCF-0013",
                    defaults={
                        "series": series_fcf,
                        "sale_date": date(2026, 11, 3),
                        "period": nov_period,
                        "customer": cust_final,
                        "employee": emp_stylist,
                        "payment_method": "CASH",
                        "taxable_amount": Decimal("10.62"),
                        "exempt_amount": Decimal("0.00"),
                        "non_subject_amount": Decimal("0.00"),
                        "iva_amount": Decimal("1.38"),
                        "iva_withheld": Decimal("0.00"),
                        "total": Decimal("12.00"),
                        "status": "ISSUED",
                        "journal_entry": jentry_map.get(6),
                        "created_by": user_map["estilista"],
                    },
                )
                SaleLine.objects.update_or_create(
                    sale=s2,
                    line_no=1,
                    defaults={
                        "line_type": "PRODUCT",
                        "product_id": prod_vit_1.id,
                        "description": "Venta: champú nutritivo 300ml",
                        "quantity": Decimal("1.000"),
                        "unit_price": Decimal("12.00"),
                        "discount": Decimal("0.00"),
                        "taxable_amount": Decimal("10.62"),
                        "iva_amount": Decimal("1.38"),
                        "total": Decimal("12.00"),
                        "unit_cost": Decimal("7.0000"),
                    },
                )

                s3, _ = Sale.objects.update_or_create(
                    doc_type="FCF",
                    doc_number="FCF-0014",
                    defaults={
                        "series": series_fcf,
                        "sale_date": date(2026, 11, 4),
                        "period": nov_period,
                        "customer": cust_rosa,
                        "employee": emp_stylist,
                        "payment_method": "CASH",
                        "taxable_amount": Decimal("13.27"),
                        "exempt_amount": Decimal("0.00"),
                        "non_subject_amount": Decimal("0.00"),
                        "iva_amount": Decimal("1.73"),
                        "iva_withheld": Decimal("0.00"),
                        "total": Decimal("15.00"),
                        "status": "ISSUED",
                        "journal_entry": jentry_map.get(7),
                        "created_by": user_map["estilista"],
                    },
                )
                SaleLine.objects.update_or_create(
                    sale=s3,
                    line_no=1,
                    defaults={
                        "line_type": "SERVICE",
                        "service": srv_2,
                        "description": "Servicio: manicura + esmaltado",
                        "quantity": Decimal("1.000"),
                        "unit_price": Decimal("15.00"),
                        "discount": Decimal("0.00"),
                        "taxable_amount": Decimal("13.27"),
                        "iva_amount": Decimal("1.73"),
                        "total": Decimal("15.00"),
                    },
                )

                s4, _ = Sale.objects.update_or_create(
                    doc_type="FCF",
                    doc_number="FCF-0015",
                    defaults={
                        "series": series_fcf,
                        "sale_date": date(2026, 11, 5),
                        "period": nov_period,
                        "customer": cust_final,
                        "employee": emp_stylist,
                        "payment_method": "CASH",
                        "taxable_amount": Decimal("15.93"),
                        "exempt_amount": Decimal("0.00"),
                        "non_subject_amount": Decimal("0.00"),
                        "iva_amount": Decimal("2.07"),
                        "iva_withheld": Decimal("0.00"),
                        "total": Decimal("18.00"),
                        "status": "ISSUED",
                        "journal_entry": jentry_map.get(8),
                        "created_by": user_map["estilista"],
                    },
                )
                SaleLine.objects.update_or_create(
                    sale=s4,
                    line_no=1,
                    defaults={
                        "line_type": "PRODUCT",
                        "product_id": prod_vit_3.id,
                        "description": "Venta: sérum de brillo 100ml",
                        "quantity": Decimal("1.000"),
                        "unit_price": Decimal("18.00"),
                        "discount": Decimal("0.00"),
                        "taxable_amount": Decimal("15.93"),
                        "iva_amount": Decimal("2.07"),
                        "total": Decimal("18.00"),
                        "unit_cost": Decimal("9.5000"),
                    },
                )

                Consumption.objects.update_or_create(
                    consumption_date=date(2026, 11, 7),
                    location=loc_cab1,
                    defaults={
                        "employee": emp_stylist,
                        "notes": "Consumo de tinte y oxidante en estaciones de belleza",
                        "journal_entry": jentry_map.get(9),
                        "created_by": user_map["estilista"],
                    },
                )

                self.stdout.write(self.style.SUCCESS("   [OK] 10 balanced journal entries and linked records created."))

            # 15. Check final Trial Balance
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(l.debit),0), COALESCE(SUM(l.credit),0)
                    FROM accounting_journal_entry_line l
                    JOIN accounting_journal_entry e ON e.id = l.entry_id
                    WHERE e.period_id = %s AND e.status = 'POSTED'
                    """,
                    [nov_period.id],
                )
                deb_sum, cred_sum = cursor.fetchone()
                diff = abs(Decimal(str(deb_sum)) - Decimal(str(cred_sum)))
                if diff == 0:
                    self.stdout.write(self.style.SUCCESS(f"=== TRIAL BALANCE SQUARE: Total Debe ${deb_sum} = Total Haber ${cred_sum} (Diff: $0.00) ==="))
                else:
                    self.stdout.write(self.style.ERROR(f"!!! TRIAL BALANCE OUT OF BALANCE: Debe ${deb_sum} <> Haber ${cred_sum} (Diff: ${diff}) !!!"))

        self.stdout.write(self.style.SUCCESS("=== MOCK DATA SEEDING COMPLETE ==="))
