from django.urls import path

from .views import (
    PaymentInitiateView,
    PaymentListView,
    PaymentWebhookStripeView,
    PaymentWebhookStubView,
)

urlpatterns = [
    path("payments/", PaymentListView.as_view(), name="payment-list"),
    path("payments/initiate/", PaymentInitiateView.as_view(), name="payment-initiate"),
    # Stub: no signature (local / QA manual testing). Same behavior as legacy URL.
    path("payments/webhook/", PaymentWebhookStubView.as_view(), name="payment-webhook"),
    path(
        "payments/webhook/stub/",
        PaymentWebhookStubView.as_view(),
        name="payment-webhook-stub",
    ),
    # Stripe: raw body + Stripe-Signature (configure this URL in Stripe Dashboard)
    path(
        "payments/webhook/stripe/",
        PaymentWebhookStripeView.as_view(),
        name="payment-webhook-stripe",
    ),
]
