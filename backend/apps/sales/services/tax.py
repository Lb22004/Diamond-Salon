from decimal import Decimal, ROUND_HALF_UP

from apps.core.models import Company

TWOPLACES = Decimal("0.01")
DEFAULT_IVA_RATE = Decimal("0.13")
DEFAULT_RETENTION_RATE = Decimal("0.01")


def get_company_iva_rate() -> Decimal:
    """Return configured IVA rate from Company singleton (default 13% · RN-06)."""
    company = Company.objects.order_by("id").first()
    if company and company.iva_rate is not None:
        return Decimal(str(company.iva_rate))
    return DEFAULT_IVA_RATE


def split_iva(
    amount: Decimal | str | float | int,
    *,
    price_includes_iva: bool,
    rate: Decimal | None = None,
) -> tuple[Decimal, Decimal]:
    """Split a gross or net amount into (taxable_amount, iva_amount) rounded half-up (DB_DESIGN.md §6, RN-06).

    - When ``price_includes_iva=True`` (FCF):
      ``taxable = round(amount / (1 + rate), 2)`` and ``iva = amount - taxable``.
    - When ``price_includes_iva=False`` (CCF):
      ``taxable = round(amount, 2)`` and ``iva = round(taxable * rate, 2)``.
    """
    amt = Decimal(str(amount)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    iva_rate = Decimal(str(rate)) if rate is not None else get_company_iva_rate()

    if amt <= Decimal("0.00"):
        return Decimal("0.00"), Decimal("0.00")

    if price_includes_iva:
        taxable = (amt / (Decimal("1.00") + iva_rate)).quantize(
            TWOPLACES, rounding=ROUND_HALF_UP
        )
        iva = (amt - taxable).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        return taxable, iva

    taxable = amt
    iva = (taxable * iva_rate).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    return taxable, iva


def compute_iva_withholding(
    taxable_amount: Decimal | str,
    *,
    is_large_taxpayer: bool,
    doc_type: str,
    retention_rate: Decimal = DEFAULT_RETENTION_RATE,
) -> Decimal:
    """Compute 1% IVA retention when a large taxpayer is billed on a CCF (RF-VEN-03)."""
    if not is_large_taxpayer or doc_type not in ("CCF", "NC", "ND"):
        return Decimal("0.00")
    base = Decimal(str(taxable_amount)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    if base <= Decimal("0.00"):
        return Decimal("0.00")
    return (base * retention_rate).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
