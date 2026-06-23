from decimal import Decimal
from collections import defaultdict

def compute_totals(lines):
    """
    Returns totals by cost_type:
    { "one_time": {"subtotal":..., "tax":..., "total":...}, "per_month": {...} }
    """
    out = defaultdict(lambda: {"subtotal": Decimal("0.00"), "tax": Decimal("0.00"), "total": Decimal("0.00")})

    for ln in lines:
        if not ln.is_selected:
            continue
        sub = ln.line_subtotal()
        out[ln.cost_type]["subtotal"] += sub

        if ln.is_taxable and ln.tax_rate:
            out[ln.cost_type]["tax"] += (sub * ln.tax_rate)

    for k in out.keys():
        out[k]["total"] = out[k]["subtotal"] + out[k]["tax"]

    return out
