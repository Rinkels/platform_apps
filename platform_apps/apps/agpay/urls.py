from django.urls import path

from . import views

app_name = "agpay"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("m/<slug:merchant_slug>/products/<slug:product_slug>/", views.product_detail, name="product_detail"),
    path("m/<slug:merchant_slug>/products/<slug:product_slug>/checkout/", views.product_checkout, name="product_checkout"),
    path("checkout/success/<int:order_id>/", views.checkout_success, name="checkout_success"),
    path("checkout/cancel/<int:order_id>/", views.checkout_cancel, name="checkout_cancel"),
    path("webhooks/stripe/", views.stripe_webhook, name="stripe_webhook"),
]
