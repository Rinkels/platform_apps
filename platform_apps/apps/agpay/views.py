import json

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import AgPayMerchant, Order, Product
from .services.stripe_checkout import StripeNotConfigured, create_cart_for_variant, create_checkout_session
from .services.webhooks import process_stripe_event


def dashboard(request):
    merchants = AgPayMerchant.objects.filter(is_active=True).order_by("display_name")
    return render(request, "agpay/dashboard.html", {"merchants": merchants})


def product_detail(request, merchant_slug: str, product_slug: str):
    product = get_object_or_404(
        Product.objects.select_related("merchant").prefetch_related("variants"),
        merchant__slug=merchant_slug,
        merchant__is_active=True,
        slug=product_slug,
        is_active=True,
    )
    variants = product.variants.filter(is_active=True).order_by("sort_order", "name")
    return render(request, "agpay/product_detail.html", {"product": product, "variants": variants})


@require_POST
def product_checkout(request, merchant_slug: str, product_slug: str):
    product = get_object_or_404(
        Product.objects.select_related("merchant").prefetch_related("variants"),
        merchant__slug=merchant_slug,
        merchant__is_active=True,
        slug=product_slug,
        is_active=True,
    )
    variant_id = request.POST.get("variant_id")
    variant = get_object_or_404(product.variants.filter(is_active=True), id=variant_id)
    quantity = int(request.POST.get("quantity") or "1")
    buyer_email = (request.POST.get("buyer_email") or "").strip()

    cart = create_cart_for_variant(variant, quantity=quantity, buyer_email=buyer_email)
    try:
        _order, session = create_checkout_session(request, cart)
    except StripeNotConfigured as exc:
        messages.error(request, str(exc))
        return redirect(product.get_absolute_url())

    return redirect(session.url)


def checkout_success(request, order_id: int):
    order = get_object_or_404(Order.objects.select_related("merchant"), id=order_id)
    return render(request, "agpay/checkout_success.html", {"order": order})


def checkout_cancel(request, order_id: int):
    order = get_object_or_404(Order.objects.select_related("merchant"), id=order_id)
    return render(request, "agpay/checkout_cancel.html", {"order": order})


@csrf_exempt
@require_POST
def stripe_webhook(request):
    webhook_secret = getattr(settings, "AGPAY_STRIPE_WEBHOOK_SECRET", "") or getattr(
        settings, "STRIPE_WEBHOOK_SECRET", ""
    )

    if webhook_secret:
        try:
            import stripe

            payload = stripe.Webhook.construct_event(
                payload=request.body,
                sig_header=request.META.get("HTTP_STRIPE_SIGNATURE", ""),
                secret=webhook_secret,
            )
        except Exception as exc:  # noqa: BLE001
            return HttpResponseBadRequest(f"Invalid Stripe webhook: {exc}")
    else:
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON")

    process_stripe_event(payload)
    return HttpResponse("ok")
