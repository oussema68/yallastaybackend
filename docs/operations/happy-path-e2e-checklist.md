# Happy path: register → listing → book → pay → sign → PDF

| | |
|---|---|
| **Audience** | QA, release managers, engineers |
| **Purpose** | One **proven** vertical slice before releases. Use this checklist on **staging** (production-like URLs, email, optional Stripe test mode). |

---

## Automated proof (backend)

The Django test **`core.tests.test_happy_path_chain.HappyPathChainTests.test_reservation_rent_pay_stub_opens_esign_and_contract_pdf`** exercises the API chain with **`PAYMENT_PROVIDER=stub`** (default in dev):

1. Tenant with approved UAE ID creates a **reservation** on an existing listing.  
2. **Initiate rent payment** with `reservation_id` → stub checkout + `transaction_id`.  
3. **POST** stub webhook (test client / JWT as payer, or **`X-Stub-Webhook-Secret`** when configured) → payment `completed` → **`after_rental_payment_completed`** creates **`LeaseSigningSession`**.  
4. With **`ESIGN_AUTO_GENERATE_CONTRACT_PDF=True`**, a **contract PDF** is attached; tenant **GET** `/api/esign/sessions/<id>/contract-pdf/` returns **`application/pdf`**.  
5. Tenant **GET** `/api/esign/sessions/` includes the session.

Run:

```bash
python manage.py test core.tests.test_happy_path_chain
```

**Register + create listing via API** are covered separately in **`accounts`** and **`listings`** tests; this chain starts from an existing listing to keep the test fast and stable.

---

## Manual / staging checklist (full product path)

Complete in order; tick each row. Use **staging** `FRONTEND_URL` / `BACKEND_URL` and real outbound email if validating delivery.

| Step | Action | Pass criteria |
|------|--------|----------------|
| 1 | **Register** landlord (or realtor) and **tenant** accounts; verify email if enforced | Both can log in; profile roles correct |
| 2 | **Landlord**: create listing (title deed / Trakheesi as required by role) | Listing visible in search / detail |
| 3 | **Tenant**: complete **UAE ID** verification if required for booking | Status approved in app |
| 4 | **Tenant**: **reserve** / rent flow for the listing | Reservation created (`pending` or per product rules) |
| 5 | **Landlord** (or workflow): confirm reservation if your flow requires it | Reservation eligible for payment |
| 6 | **Tenant**: **pay** (**stub**: complete stub checkout + call webhook **or** **Stripe test mode**: finish Checkout) | Payment `completed`; notifications / team message per `payments.hooks` |
| 7 | **E-sign**: landlord uploads lease PDF if not auto-generated; **place signature fields** if required | Session shows contract PDF |
| 8 | **Renter** then **lister** sign via magic links or dashboard | Session status advances per rules |
| 9 | **Download** signed PDF (dashboard or signed link) | File opens; bytes look like PDF |

---

## Playwright / visual E2E (optional)

Use Playwright (or Cypress) against **staging** to **record** the UI path and attach screenshots/video to the release ticket. Assertions should include:

- After login: dashboard loads.  
- Listing creation form submits without 5xx.  
- Checkout redirect (Stripe test) or stub confirmation page.  
- E-sign route loads (`/sign/lease/...` or your SPA route).

Playwright does **not** replace the **backend** chain test above; it adds **UI** confidence and **visual** regression signals.

---

## Stripe test mode (staging)

- Set **`PAYMENT_PROVIDER=stripe`**, **`STRIPE_*`** test keys, webhook URL **`{BACKEND_URL}/api/payments/webhook/stripe/`** in Stripe Dashboard.  
- See [`../payments/stripe-setup.md`](../payments/stripe-setup.md).

---

## Related

- [`monitoring-and-backups.md`](./monitoring-and-backups.md): uptime, errors, backups  
- [`../payments/stripe-setup.md`](../payments/stripe-setup.md)  
- [`../esign/setup.md`](../esign/setup.md)
