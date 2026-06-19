# Stripe (AED / Checkout) - operator checklist

| | |
|---|---|
| **Audience** | Technical operators, integrators, client IT |
| **Distribution** | **Client-facing** - share **variable names only**; never paste live secret values into email. |
| **Disclaimer** | Configuration guidance; Stripe’s terms and your acquiring relationship apply. |

Yallastay uses **Stripe Checkout** (`mode=payment`) and completes orders on **`checkout.session.completed`**. After payment, the backend stores a short **`payment_method`** label (e.g. `google_pay`, `apple_pay`, `card_visa`) from the PaymentIntent.

## Environment (Django)

| Variable | Purpose |
|----------|---------|
| `PAYMENT_PROVIDER=stripe` | Use **Stripe** in production (non-production environments may use separate test configuration) |
| `STRIPE_SECRET_KEY` | Server key - required for Checkout + webhook PaymentIntent retrieve |
| `STRIPE_PUBLISHABLE_KEY` | Returned to clients if needed (optional for hosted Checkout redirect) |
| `STRIPE_WEBHOOK_SECRET` | Signing secret for `/api/payments/webhook/stripe/` |
| `FRONTEND_URL` | Success/cancel URLs for Checkout (e.g. `https://app.yallastay.com`) |

## Stripe Dashboard

1. **Account & region** - Ensure **United Arab Emirates** (or your settlement country) and **AED** where applicable.
2. **Payment methods** - Enable **Cards**. Enable **Apple Pay** and **Google Pay** under Wallets if you want wallets on Checkout (availability depends on currency, account, and customer device).
3. **Apple Pay** - Register and verify your **production domain** (and staging if used): *Settings → Payment methods → Apple Pay*.
4. **Webhooks** - Add endpoint: `{BACKEND_URL}/api/payments/webhook/stripe/`, subscribe to **`checkout.session.completed`** (and keep the signing secret in `STRIPE_WEBHOOK_SECRET`).
5. **Test mode** - Use test keys and [test cards](https://docs.stripe.com/testing); wallets can be exercised on supported devices.

## Bank transfer

**Not** enabled by this Checkout integration. Adding bank rails (e.g. regional transfer, ACH, SEPA) requires a separate product choice and Stripe configuration.

## Support

`payment_method` on `Payment` is populated from the completed session when Stripe returns a PaymentIntent; if retrieval fails, status still updates but `payment_method` may stay empty.
