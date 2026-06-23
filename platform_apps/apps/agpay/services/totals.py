from decimal import Decimal


def compute_platform_fee(amount: Decimal, fee_bps: int) -> Decimal:
    return (amount * Decimal(fee_bps or 0) / Decimal("10000")).quantize(Decimal("0.01"))


def compute_line_subtotal(unit_amount: Decimal, quantity: int) -> Decimal:
    return (unit_amount or Decimal("0.00")) * Decimal(quantity or 0)
