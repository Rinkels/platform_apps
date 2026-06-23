from django.utils import timezone

from platform_apps.apps.agpay.models import Order, StripeWebhookEvent


def process_stripe_event(event_payload: dict) -> StripeWebhookEvent:
    event_id = event_payload.get("id", "")
    event_type = event_payload.get("type", "")
    event, _ = StripeWebhookEvent.objects.get_or_create(
        event_id=event_id,
        defaults={"event_type": event_type, "payload": event_payload},
    )
    if event.status == StripeWebhookEvent.STATUS_PROCESSED:
        return event

    try:
        data_object = (event_payload.get("data") or {}).get("object") or {}
        if event_type == "checkout.session.completed":
            _mark_checkout_session_paid(data_object)
        event.status = StripeWebhookEvent.STATUS_PROCESSED
        event.processed_at = timezone.now()
        event.error = ""
        event.save(update_fields=["status", "processed_at", "error"])
    except Exception as exc:  # noqa: BLE001
        event.status = StripeWebhookEvent.STATUS_FAILED
        event.error = str(exc)
        event.save(update_fields=["status", "error"])
        raise
    return event


def _mark_checkout_session_paid(session: dict) -> None:
    session_id = session.get("id", "")
    order = Order.objects.filter(stripe_checkout_session_id=session_id).first()
    if not order:
        metadata = session.get("metadata") or {}
        order_id = metadata.get("agpay_order_id")
        if order_id:
            order = Order.objects.filter(id=order_id).first()
    if not order:
        return

    order.status = Order.STATUS_PAID
    order.buyer_email = order.buyer_email or session.get("customer_email", "")
    order.stripe_payment_intent_id = session.get("payment_intent", "") or order.stripe_payment_intent_id
    order.paid_at = timezone.now()
    order.save(update_fields=["status", "buyer_email", "stripe_payment_intent_id", "paid_at", "updated_at"])

    if order.cart_id:
        order.cart.status = order.cart.STATUS_ORDERED
        order.cart.save(update_fields=["status", "updated_at"])
