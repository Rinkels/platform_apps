from .totals import compute_totals

def build_snapshot(quote):
    lines = quote.lines.select_related("catalog_item").all().order_by("sort_order", "id")
    totals = compute_totals(lines)

    return {
        "quote": {
            "id": quote.id,
            "title": quote.title,
            "status": quote.status,
            "currency": quote.currency,
            "created_at": quote.created_at.isoformat() if quote.created_at else None,
            "sent_at": quote.sent_at.isoformat() if quote.sent_at else None,
            "accepted_at": quote.accepted_at.isoformat() if quote.accepted_at else None,
        },
        "company": {
            "content_type": str(quote.company_content_type) if quote.company_content_type else None,
            "object_id": quote.company_object_id,
            "display": str(quote.company) if quote.company else None,
        },
        "lines": [
            {
                "id": ln.id,
                "parent_id": ln.parent_id,
                "label": ln.label,
                "description": ln.description,
                "cost_type": ln.cost_type,
                "quantity": str(ln.quantity),
                "unit_price": str(ln.unit_price),
                "subtotal": str(ln.line_subtotal()),
                "is_selected": ln.is_selected,
                "is_required": ln.is_required,
                "rule_context": ln.rule_context,
            }
            for ln in lines
        ],
        "totals": {
            k: {kk: str(vv) for kk, vv in v.items()} for k, v in totals.items()
        }
    }
