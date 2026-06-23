from decimal import Decimal
import os

from django.conf import settings
from django.urls import reverse

from platform_apps.apps.agpay.models import Cart, CartItem, Order, OrderItem, ProductVariant
from platform_apps.apps.agpay.services.totals import compute_line_subtotal, compute_platform_fee


class StripeNotConfigured(RuntimeError):
    pass


def _stripe_client():
    try:
        import stripe
    except ImportError as exc:
        raise StripeNotConfigured("The 'stripe' package is not installed.") from exc

    api_key = (
        getattr(settings, "AGPAY_STRIPE_SECRET_KEY", "")
        or getattr(settings, "STRIPE_SECRET_KEY", "")
        or os.environ.get("AGPAY_STRIPE_SECRET_KEY", "")
        or os.environ.get("STRIPE_SECRET_KEY", "")
    )
    if not api_key:
        raise StripeNotConfigured("AGPAY_STRIPE_SECRET_KEY or STRIPE_SECRET_KEY is not configured.")
    stripe.api_key = api_key
    return stripe


def _absolute_url(request, path_name, *args):
    return request.build_absolute_uri(reverse(path_name, args=args))


def create_cart_for_variant(variant: ProductVariant, *, quantity: int = 1, buyer_email: str = "") -> Cart:
    merchant = variant.product.merchant
    cart = Cart.objects.create(merchant=merchant, buyer_email=buyer_email)
    CartItem.objects.create(
        cart=cart,
        variant=variant,
        label=variant.name,
        quantity=max(1, int(quantity or 1)),
        unit_amount=variant.unit_amount,
        currency=variant.currency,
        metadata={"product_id": variant.product_id},
    )
    return cart


def create_order_from_cart(cart: Cart) -> Order:
    items = list(cart.items.select_related("variant", "variant__product"))
    subtotal = sum((item.line_subtotal() for item in items), Decimal("0.00"))
    fee = compute_platform_fee(subtotal, cart.merchant.platform_fee_bps)
    currency = items[0].currency if items else cart.merchant.default_currency

    order = Order.objects.create(
        merchant=cart.merchant,
        cart=cart,
        buyer_email=cart.buyer_email,
        buyer_name=cart.buyer_name,
        currency=currency,
        subtotal_amount=subtotal,
        platform_fee_amount=fee,
        total_amount=subtotal,
        metadata={"cart_id": cart.id},
    )
    for item in items:
        OrderItem.objects.create(
            order=order,
            variant=item.variant,
            label=item.label,
            quantity=item.quantity,
            unit_amount=item.unit_amount,
            currency=item.currency,
            metadata=item.metadata,
        )
    cart.status = Cart.STATUS_CHECKOUT
    cart.save(update_fields=["status", "updated_at"])
    return order


def create_checkout_session(request, cart: Cart) -> tuple[Order, object]:
    stripe = _stripe_client()
    order = create_order_from_cart(cart)

    success_url = cart.merchant.success_url or _absolute_url(request, "agpay:checkout_success", order.id)
    cancel_url = cart.merchant.cancel_url or _absolute_url(request, "agpay:checkout_cancel", order.id)

    line_items = []
    for item in cart.items.select_related("variant", "variant__product"):
        line_items.append(
            {
                "price_data": {
                    "currency": item.currency.lower(),
                    "unit_amount": int(item.unit_amount * 100),
                    "product_data": {
                        "name": item.label,
                        "description": item.variant.product.description[:500],
                    },
                },
                "quantity": item.quantity,
            }
        )

    kwargs = {
        "mode": "payment",
        "line_items": line_items,
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": str(order.id),
        "customer_email": cart.buyer_email or None,
        "metadata": {
            "agpay_order_id": str(order.id),
            "agpay_merchant": cart.merchant.slug,
        },
    }

    if cart.merchant.stripe_account_id:
        kwargs["payment_intent_data"] = {
            "application_fee_amount": int(order.platform_fee_amount * 100),
            "transfer_data": {"destination": cart.merchant.stripe_account_id},
        }

    session = stripe.checkout.Session.create(**kwargs)
    order.stripe_checkout_session_id = session.id
    order.save(update_fields=["stripe_checkout_session_id", "updated_at"])
    return order, session
