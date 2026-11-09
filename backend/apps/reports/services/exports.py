from datetime import date
from decimal import Decimal
from io import BytesIO

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from django.db import connection
from django.utils import timezone

from apps.accounting.models import Account, JournalEntry
from apps.core.models import AccountingPeriod, AuditLog, Company, User
from apps.core.services.audit import log_audit
from apps.core.services.periods import get_active_period
from apps.reports.services.ledger import (
    get_account_ledger,
    get_financial_statements,
    get_trial_balance,
)


def _fmt_money(val: str | Decimal | float | int | None) -> str:
    if val is None or val == "":
        return "$0.00"
    d = Decimal(str(val))
    sign = "-" if d < 0 else ""
    return f"{sign}${abs(d):,.2f}"


def _build_book_dataset(
    book: str,
    *,
    period: AccountingPeriod | None = None,
    account: str | int | None = None,
    date_from: str | date | None = None,
    date_to: str | date | None = None,
) -> dict:
    resolved_period = period or get_active_period()
    period_label = resolved_period.label if resolved_period else "Noviembre 2026"
    start_d = resolved_period.start_date if resolved_period else date(2026, 11, 1)
    end_d = resolved_period.end_date if resolved_period else date(2026, 11, 30)

    b = book.lower().strip()

    if b in ("chart", "accounts", "catalogo"):
        accounts = Account.objects.filter(is_active=True).order_by("code")
        headers = ["Código", "Nombre de Cuenta", "Nivel", "Tipo", "Naturaleza", "Inventario", "Operativa"]
        rows = []
        for a in accounts:
            rows.append([
                a.code,
                a.name,
                str(a.level),
                a.get_account_type_display(),
                a.get_nature_display(),
                a.get_inventory_type_display(),
                "Sí" if a.accepts_entries else "Agrupadora",
            ])
        return {
            "title": "CATÁLOGO OFICIAL DE CUENTAS (NIIF PARA LAS PYMES)",
            "subtitle": f"Período de referencia: {period_label} · Total cuentas: {len(rows)}",
            "filename_stem": f"catalogo_cuentas_{resolved_period.code if resolved_period else '2026-11'}",
            "headers": headers,
            "rows": rows,
            "totals": ["TOTAL", f"{len(rows)} cuentas", "", "", "", "", ""],
            "money_cols": [],
        }

    if b in ("journal", "diario", "libro-diario"):
        entries = (
            JournalEntry.objects.filter(
                period=resolved_period,
                status__in=[JournalEntry.EntryStatus.POSTED, JournalEntry.EntryStatus.REVERSED],
            )
            .prefetch_related("lines__account")
            .order_by("entry_date", "entry_number", "id")
            if resolved_period
            else JournalEntry.objects.prefetch_related("lines__account").order_by("entry_date", "id")
        )
        headers = ["Partida", "Fecha", "Tipo", "Código", "Cuenta / Concepto", "Debe (USD)", "Haber (USD)"]
        rows = []
        tot_d = Decimal("0.00")
        tot_c = Decimal("0.00")
        for e in entries:
            ref = f"#{e.entry_number}" if e.entry_number else f"Borr.{e.id}"
            for line in e.lines.all():
                tot_d += line.debit
                tot_c += line.credit
                rows.append([
                    ref,
                    e.entry_date.isoformat(),
                    e.get_entry_type_display(),
                    line.account.code,
                    f"{line.account.name} — {line.description or e.description}",
                    f"{line.debit:.2f}",
                    f"{line.credit:.2f}",
                ])
        return {
            "title": "LIBRO DIARIO GENERAL",
            "subtitle": f"Período contable: {period_label} ({start_d.isoformat()} al {end_d.isoformat()})",
            "filename_stem": f"libro_diario_{resolved_period.code if resolved_period else '2026-11'}",
            "headers": headers,
            "rows": rows,
            "totals": ["", "", "", "", "SUMAS IGUALES DEL PERÍODO", f"{tot_d:.2f}", f"{tot_c:.2f}"],
            "money_cols": [5, 6],
        }

    if b in ("ledger", "mayor", "libro-mayor"):
        data = get_account_ledger(
            account_identifier=account,
            period=resolved_period,
            date_from=date_from,
            date_to=date_to,
        )
        acc_info = data["account"]
        kpis = data["kpis"]
        headers = ["Fecha", "Ref. Diario", "Tipo", "Concepto Contable", "Cargo / Debe", "Abono / Haber", "Saldo Acumulado"]
        rows = [
            [
                data["date_from"],
                "SALDO INIC.",
                "Apertura",
                "Saldo inicial anterior al rango consultado",
                "0.00",
                "0.00",
                kpis["opening_balance"],
            ]
        ]
        for m in data["movements"]:
            rows.append([
                m["entry_date"],
                m["entry_ref"],
                m["entry_type_label"],
                m["concept"],
                m["debit"],
                m["credit"],
                m["resulting_balance"],
            ])
        return {
            "title": f"LIBRO MAYOR ANALÍTICO — CUENTA {acc_info['code']} {acc_info['name'].upper()}",
            "subtitle": (
                f"Período: {period_label} · Naturaleza: {acc_info['nature_label']} · "
                f"Del {data['date_from']} al {data['date_to']}"
            ),
            "filename_stem": f"libro_mayor_{acc_info['code']}_{resolved_period.code if resolved_period else '2026-11'}",
            "headers": headers,
            "rows": rows,
            "totals": [
                "",
                "",
                "",
                "TOTALES Y SALDO DE CIERRE",
                kpis["debit_total"],
                kpis["credit_total"],
                kpis["closing_balance"],
            ],
            "money_cols": [4, 5, 6],
        }

    if b in ("trial-balance", "balance-comprobacion", "balance"):
        tb = get_trial_balance(period=resolved_period)
        headers = [
            "Código",
            "Nombre de Cuenta",
            "Naturaleza",
            "Saldo Inicial",
            "Cargos (Debe)",
            "Abonos (Haber)",
            "Saldo Deudor",
            "Saldo Acreedor",
        ]
        rows = []
        for r in tb["rows"]:
            rows.append([
                r["code"],
                r["name"],
                r["nature_label"],
                r["opening_balance"],
                r["debit_total"],
                r["credit_total"],
                r["closing_debit"],
                r["closing_credit"],
            ])
        t = tb["totals"]
        return {
            "title": "BALANCE DE COMPROBACIÓN DE SUMAS Y SALDOS",
            "subtitle": f"Período contable: {period_label} · Sumas iguales verificadas: {'OK' if t['is_balanced'] else 'DESCUADRADO'}",
            "filename_stem": f"balance_comprobacion_{resolved_period.code if resolved_period else '2026-11'}",
            "headers": headers,
            "rows": rows,
            "totals": [
                "",
                "SUMAS IGUALES",
                "",
                "0.00",
                t["debit_total"],
                t["credit_total"],
                t["closing_debit"],
                t["closing_credit"],
            ],
            "money_cols": [3, 4, 5, 6, 7],
        }

    if b in ("financial-statements", "estados-financieros", "niif"):
        fs = get_financial_statements(period=resolved_period)
        inc = fs["income_statement"]
        bs = fs["balance_sheet"]
        headers = ["Sección / Estado", "Código", "Rubro / Cuenta Contable", "Importe (USD)"]
        rows = []
        for item in inc["incomes"]:
            rows.append(["Estado de Resultados · Ingresos", item["code"], item["name"], item["balance"]])
        for item in inc["costs"]:
            rows.append(["Estado de Resultados · Costos", item["code"], item["name"], item["balance"]])
        rows.append(["Estado de Resultados · Subtotal", "", "UTILIDAD BRUTA", inc["gross_profit"]])
        for item in inc["expenses"]:
            rows.append(["Estado de Resultados · Gastos", item["code"], item["name"], item["balance"]])
        rows.append(["Estado de Resultados · Neto", "", "UTILIDAD / RESULTADO DEL EJERCICIO", inc["net_income"]])
        for item in bs["assets"]:
            rows.append(["Balance General · Activos", item["code"], item["name"], item["balance"]])
        rows.append(["Balance General · Total Activos", "", "TOTAL ACTIVOS", bs["total_assets"]])
        for item in bs["liabilities"]:
            rows.append(["Balance General · Pasivos", item["code"], item["name"], item["balance"]])
        for item in bs["equity"]:
            rows.append(["Balance General · Patrimonio", item["code"], item["name"], item["balance"]])
        rows.append(["Balance General · Resultado", "320102", "Resultado del Ejercicio Actual", bs["current_period_result"]])
        return {
            "title": "ESTADOS FINANCIEROS NIIF PARA LAS PYMES (RESULTADOS Y SITUACIÓN FINANCIERA)",
            "subtitle": f"Período contable: {period_label} · Ecuación Patrimonial (A = P + C): {'OK' if bs['is_balanced'] else 'REVISAR'}",
            "filename_stem": f"estados_financieros_{resolved_period.code if resolved_period else '2026-11'}",
            "headers": headers,
            "rows": rows,
            "totals": ["ECUACIÓN PATRIMONIAL", "", "TOTAL PASIVO + PATRIMONIO", bs["total_liabilities_and_equity"]],
            "money_cols": [3],
        }

    if b in ("sales", "sales-fcf", "sales-ccf", "ventas", "libro-ventas"):
        tables = set(connection.introspection.table_names())
        headers = ["Fecha", "Tipo Doc.", "Correlativo", "Cliente", "NRC", "Gravado", "IVA Débito (13%)", "Total"]
        rows = []
        tot_sub = Decimal("0.00")
        tot_iva = Decimal("0.00")
        tot_all = Decimal("0.00")
        if "sales_sale" in tables and resolved_period:
            doc_filter = ""
            if b == "sales-fcf":
                doc_filter = " AND s.doc_type = 'FCF'"
            elif b == "sales-ccf":
                doc_filter = " AND s.doc_type = 'CCF'"
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT s.issue_date, s.doc_type, s.doc_number, c.name, COALESCE(c.nrc, '—'),
                           s.subtotal, s.iva_amount, s.total
                    FROM sales_sale s
                    JOIN sales_customer c ON c.id = s.customer_id
                    WHERE s.period_id = %s AND s.status = 'ISSUED'{doc_filter}
                    ORDER BY s.issue_date, s.id
                    """,
                    [resolved_period.pk],
                )
                for r in cursor.fetchall():
                    sub = Decimal(str(r[5] or 0))
                    iva = Decimal(str(r[6] or 0))
                    tot = Decimal(str(r[7] or 0))
                    tot_sub += sub
                    tot_iva += iva
                    tot_all += tot
                    rows.append([
                        str(r[0]),
                        str(r[1]),
                        str(r[2]),
                        str(r[3]),
                        str(r[4]),
                        f"{sub:.2f}",
                        f"{iva:.2f}",
                        f"{tot:.2f}",
                    ])
        return {
            "title": "LIBRO DE VENTAS E INGRESOS (IVA DÉBITO FISCAL)",
            "subtitle": f"Período tributario: {period_label}",
            "filename_stem": f"libro_ventas_{resolved_period.code if resolved_period else '2026-11'}",
            "headers": headers,
            "rows": rows,
            "totals": ["", "", "", "TOTALES DEL PERÍODO", "", f"{tot_sub:.2f}", f"{tot_iva:.2f}", f"{tot_all:.2f}"],
            "money_cols": [5, 6, 7],
        }

    if b in ("purchases", "compras", "libro-compras"):
        tables = set(connection.introspection.table_names())
        headers = ["Fecha", "CCF N.º", "Proveedor", "NRC", "Destino", "Compra Gravada", "IVA Crédito (13%)", "Total"]
        rows = []
        tot_sub = Decimal("0.00")
        tot_iva = Decimal("0.00")
        tot_all = Decimal("0.00")
        if "purchases_purchase" in tables and resolved_period:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT p.issue_date, p.doc_number, s.name, s.nrc, p.destination,
                           p.subtotal, p.iva_amount, p.total
                    FROM purchases_purchase p
                    JOIN purchases_supplier s ON s.id = p.supplier_id
                    WHERE p.period_id = %s AND p.status = 'REGISTERED'
                    ORDER BY p.issue_date, p.id
                    """,
                    [resolved_period.pk],
                )
                for r in cursor.fetchall():
                    sub = Decimal(str(r[5] or 0))
                    iva = Decimal(str(r[6] or 0))
                    tot = Decimal(str(r[7] or 0))
                    tot_sub += sub
                    tot_iva += iva
                    tot_all += tot
                    rows.append([
                        str(r[0]),
                        str(r[1]),
                        str(r[2]),
                        str(r[3]),
                        str(r[4]),
                        f"{sub:.2f}",
                        f"{iva:.2f}",
                        f"{tot:.2f}",
                    ])
        return {
            "title": "LIBRO DE COMPRAS Y CRÉDITO FISCAL IVA",
            "subtitle": f"Período tributario: {period_label}",
            "filename_stem": f"libro_compras_{resolved_period.code if resolved_period else '2026-11'}",
            "headers": headers,
            "rows": rows,
            "totals": ["", "", "", "", "TOTALES DEL PERÍODO", f"{tot_sub:.2f}", f"{tot_iva:.2f}", f"{tot_all:.2f}"],
            "money_cols": [5, 6, 7],
        }

    # Default fallback to trial balance
    return _build_book_dataset("trial-balance", period=resolved_period)


def _render_pdf(company: Company | None, dataset: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(letter),
        leftMargin=0.45 * inch,
        rightMargin=0.45 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "AtelierTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1E1B18"),
        spaceAfter=2,
    )
    meta_style = ParagraphStyle(
        "AtelierMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#5C554E"),
        spaceAfter=8,
    )
    cell_style = ParagraphStyle(
        "AtelierCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#1E1B18"),
    )

    legal_name = company.legal_name if company else "DIAMOND SALON, S.A. DE C.V."
    trade_name = company.trade_name if company else "Diamond Salón · Atelier Contable"
    nit = company.nit if company else "0614-150524-101-8"
    nrc = company.nrc if company else "318450-9"
    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")

    elements = [
        Paragraph(f"{legal_name} ({trade_name})", title_style),
        Paragraph(
            f"<b>NIT:</b> {nit} &nbsp;&nbsp;|&nbsp;&nbsp; <b>NRC:</b> {nrc} "
            f"&nbsp;&nbsp;|&nbsp;&nbsp; <b>Moneda:</b> USD ($) &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Emitido:</b> {timestamp}",
            meta_style,
        ),
        Paragraph(f"<b>{dataset['title']}</b> — {dataset['subtitle']}", meta_style),
        Spacer(1, 4),
    ]

    money_cols = set(dataset.get("money_cols", []))
    table_data = [dataset["headers"]]

    for row in dataset["rows"]:
        formatted_row = []
        for idx, val in enumerate(row):
            if idx in money_cols:
                formatted_row.append(_fmt_money(val))
            else:
                text = str(val or "")
                if len(text) > 58:
                    formatted_row.append(Paragraph(text, cell_style))
                else:
                    formatted_row.append(text)
        table_data.append(formatted_row)

    totals_row = []
    for idx, val in enumerate(dataset["totals"]):
        if idx in money_cols and val != "":
            totals_row.append(_fmt_money(val))
        else:
            totals_row.append(str(val or ""))
    table_data.append(totals_row)

    tbl = Table(table_data, repeatRows=1)
    tbl_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E1B18")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#FAF6F0")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -2), 7.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#FAF6F0")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F1E9DC")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8CFC2")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for col_idx in money_cols:
        tbl_style.append(("ALIGN", (col_idx, 0), (col_idx, -1), "RIGHT"))

    tbl.setStyle(TableStyle(tbl_style))
    elements.append(tbl)
    doc.build(elements)
    return buf.getvalue()


def _render_xlsx(company: Company | None, dataset: dict) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte Contable"

    legal_name = company.legal_name if company else "DIAMOND SALON, S.A. DE C.V."
    trade_name = company.trade_name if company else "Diamond Salón · Atelier Contable"
    nit = company.nit if company else "0614-150524-101-8"
    nrc = company.nrc if company else "318450-9"

    title_font = Font(name="Calibri", size=13, bold=True, color="1E1B18")
    sub_font = Font(name="Calibri", size=10, italic=True, color="5C554E")
    header_font = Font(name="Calibri", size=10, bold=True, color="FAF6F0")
    header_fill = PatternFill(start_color="1E1B18", end_color="1E1B18", fill_type="solid")
    total_font = Font(name="Calibri", size=10, bold=True, color="1E1B18")
    total_fill = PatternFill(start_color="F1E9DC", end_color="F1E9DC", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin", color="D8CFC2"),
        right=Side(style="thin", color="D8CFC2"),
        top=Side(style="thin", color="D8CFC2"),
        bottom=Side(style="thin", color="D8CFC2"),
    )

    ws["A1"] = f"{legal_name} ({trade_name})"
    ws["A1"].font = title_font
    ws["A2"] = f"NIT: {nit}  |  NRC: {nrc}  |  Moneda: USD ($)"
    ws["A2"].font = sub_font
    ws["A3"] = f"{dataset['title']} — {dataset['subtitle']}"
    ws["A3"].font = Font(name="Calibri", size=10, bold=True, color="8B6F47")

    start_row = 5
    headers = dataset["headers"]
    money_cols = set(dataset.get("money_cols", []))

    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=start_row, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal="right" if (col_idx - 1) in money_cols else "left", vertical="center")

    current_row = start_row + 1
    for row_vals in dataset["rows"]:
        for col_idx, val in enumerate(row_vals, start=1):
            c = ws.cell(row=current_row, column=col_idx)
            if (col_idx - 1) in money_cols and val not in ("", None):
                c.value = float(Decimal(str(val)))
                c.number_format = "$#,##0.00;($#,##0.00);\"$0.00\""
                c.alignment = Alignment(horizontal="right")
            else:
                c.value = str(val or "")
            c.border = thin_border
        current_row += 1

    for col_idx, val in enumerate(dataset["totals"], start=1):
        c = ws.cell(row=current_row, column=col_idx)
        if (col_idx - 1) in money_cols and val not in ("", None):
            c.value = float(Decimal(str(val)))
            c.number_format = "$#,##0.00;($#,##0.00);\"$0.00\""
            c.alignment = Alignment(horizontal="right")
        else:
            c.value = str(val or "")
        c.font = total_font
        c.fill = total_fill
        c.border = thin_border

    for col_idx in range(1, len(headers) + 1):
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = 20 if (col_idx - 1) in money_cols else 24

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_book(
    *,
    book: str,
    fmt: str = "pdf",
    period: AccountingPeriod | None = None,
    account: str | int | None = None,
    date_from: str | date | None = None,
    date_to: str | date | None = None,
    user: User | None = None,
) -> tuple[bytes, str, str]:
    """Generate official PDF or XLSX report and log EXPORT audit trail (RF-REP-01..04, RN-15)."""
    resolved_period = period or get_active_period()
    company = Company.objects.order_by("id").first()
    dataset = _build_book_dataset(
        book,
        period=resolved_period,
        account=account,
        date_from=date_from,
        date_to=date_to,
    )

    clean_fmt = (fmt or "pdf").lower().strip()
    if clean_fmt in ("xlsx", "excel", "xls"):
        payload = _render_xlsx(company, dataset)
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{dataset['filename_stem']}.xlsx"
    else:
        payload = _render_pdf(company, dataset)
        content_type = "application/pdf"
        filename = f"{dataset['filename_stem']}.pdf"

    log_audit(
        action=AuditLog.Action.EXPORT,
        table_name=f"reports_{book}",
        record_id=resolved_period.pk if resolved_period else 0,
        after_data={
            "book": book,
            "format": clean_fmt,
            "filename": filename,
            "rows_exported": len(dataset["rows"]),
        },
        user=user,
    )
    return payload, content_type, filename
