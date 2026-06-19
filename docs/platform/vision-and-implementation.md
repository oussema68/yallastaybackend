# Yallastay - Platform Vision, Workflows & Runbooks

| | |
|---|---|
| **Audience** | Engineers, technical partners, client IT |
| **Distribution** | **Client-facing** - may be shared under NDA; **redact** internal repo paths or credentials if exporting. |
| **Disclaimer** | Describes implementation intent; not a fixed product warranty unless agreed in contract. |

*See also [`../README.md`](../README.md) (documentation index) and [`../client/README.md`](../client/README.md) (client package).*

This document summarizes product direction, implemented features, **local vs production** setup, and **end-to-end workflows** for backend and frontend. It is a living reference for engineers and stakeholders.

**Repositories**
- **Backend:** `yallastay_backend` → Django project under `yallastay/`
- **Frontend:** `yallastay` (Vite + React) - sibling folder; many UI routes call `/api` on the same origin or via `VITE_API_URL`

---

## Table of contents

1. [Messaging & conversations](#1-messaging--conversations)  
2. [Public profiles](#2-public-profiles-userid)  
3. [Payments - stub vs Stripe](#3-payments--stub-vs-stripe)  
4. [Product vision - Airbnb-like automation](#4-product-vision--airbnb-like-automation-roadmap)  
5. [Signing platform & QR](#5-signing-platform--qr-recommended-pattern)  
6. [Local development (testing)](#6-local-development-testing)  
7. [Production](#7-production)  
8. [Backend workflows (API order)](#8-backend-workflows-api-order)  
9. [Frontend workflows (user journeys)](#9-frontend-workflows-user-journeys)  
10. [Environment variables reference](#10-environment-variables-reference)  
11. [Misc fixes](#11-misc-fixes)  

---

## 1. Messaging & conversations

### Problems solved
- **Sender alignment:** Compare `message.sender` to the current user’s id from `GET /auth/me/`, not only `sender_email === 'You'`.
- **Labels:** **First name** (or `"You"` for self), not email.
- **Listing context:** Chats tied to the property (`listing_detail`, `other_user`).

### Backend (`messaging`)
- **`ConversationSerializer`:** `listing_detail`, `other_user` (`id`, `first_name`, `role`).
- **`GET /api/conversations/<id>/messages/`** returns `{ "messages": [...], "conversation": { ... } }`.
- **`MessageSerializer`:** `sender_first_name`, `sender_is_yallastay_team` for system messages.
- **`_conversation_queryset()`** for efficient prefetch.

### Frontend
- **`Messages.jsx`**, **`Header.jsx`**: listing strip, links to `/property/:id` and `/user/:id`, team message styling.
- **`listMessages`:** supports legacy array or `{ messages, conversation }`.

---

## 2. Public profiles (`/user/:id`)

- **`GET /api/auth/users/<id>/public-profile/`** (JWT): reviews, verification, `realtor_public`, optional **`contract_context`** for listers with a relationship.
- **Yallastay Team** system user → **404** on public profile.
- **Frontend:** `UserProfile.jsx`, `auth.publicProfile(id)`.

---

## 3. Payments - stub vs Stripe

| Setting | Purpose |
|---------|---------|
| `PAYMENT_PROVIDER` | `stub` (default) or `stripe` |
| `STRIPE_SECRET_KEY` | Required when `stripe` |
| `STRIPE_WEBHOOK_SECRET` | Verifies `POST .../webhook/stripe/` |
| `STRIPE_PUBLISHABLE_KEY` | Optional; returned on initiate |
| `FRONTEND_URL` | Stripe Checkout `success_url` / `cancel_url` base |

### Webhooks
| URL | Use |
|-----|-----|
| `POST /api/payments/webhook/` | Stub (alias) |
| `POST /api/payments/webhook/stub/` | Dev — `{ "transaction_id": "..." }` + JWT (payer) or `X-Stub-Webhook-Secret` |
| `POST /api/payments/webhook/stripe/` | Stripe - raw body + `Stripe-Signature` |

### After payment (first time a row becomes `completed`)
Handled by `payments/hooks.py` → `on_payment_first_completed` (stub + Stripe webhooks):

1. **Yallastay Team** message in the listing thread when rent/deposit + reservation (`Payment.team_message_sent_at`).
2. **E-sign (stub):** one `LeaseSigningSession` per reservation - emails + in-app notifications (`esign` + `contract` types) with magic links `FRONTEND_URL/sign/lease/<token>/`.
3. **Payer receipt:** transactional email (`payment_receipt`) + in-app notification (`payment`).

### Stripe Checkout & billing metadata
- **`checkout.session.completed`** webhook completes the `Payment` row; **`payment_method`** stores a short label (e.g. `google_pay`, `apple_pay`, `card_visa`) resolved from the session’s PaymentIntent when available.
- **Wallets:** enable Apple Pay / Google Pay in the Stripe Dashboard; no separate frontend change beyond normal Checkout.
- **Bank transfer:** not part of the current Checkout flow; treat as out of scope until a dedicated flow exists.
- **Runbook:** see [`../payments/stripe-setup.md`](../payments/stripe-setup.md) for webhook URLs, CLI forwarding, and test checklist.

### Frontend
- `payments.initiate`, `payments.stubWebhook`, `initiatePayment()`, `StubPaymentModal`, Property + Dashboard deposit flows, `/payment/success`, `/payment/cancel`.
- **Lease signing:** `SignLease.jsx` route `sign/lease/:token`, `api` `esign.listSessions` / `getSession`, public `POST /api/esign/sign/<token>/`.

### Code
- `messaging/team_user.py`, `messaging/payment_messages.py`, `payments/stripe_service.py`, `payments/hooks.py`, `esign/` (models, `services`, views).

---

## 4. Product vision - Airbnb-like automation (roadmap)

- Single journey: search → book → pay → contract → sign → status in-app.
- Pipelines: **webhooks** (Stripe; e-sign later).
- Phases: Stripe → realtor contract orchestration → e-sign → Ejari/DLD tracking (`dld_metadata`, `external_reference`).
- **In-app + mobile:** one API; responsive web first; native apps later.

---

## 5. Signing platform & QR

**Implemented (dev):** `esign` app - `LeaseSigningSession` with per-party tokens. **Order:** renter signs first; landlord/realtor cannot sign until `renter_signed_at` is set (`renter_must_sign_first` on early lister POST). **`GET /api/esign/sign/<token>/`** = preview (no auth); **`POST /api/esign/sign/<token>/`** = record signature. Completion writes `reservation.dld_metadata.lease_signed_at`. Frontend: **Dashboard** + **My listings** show **Lease agreements & signatures** with steps and **Open signing page** when it’s your turn.

**Listings:** when a lease is **fully signed**, `Listing.leased` is set `True`. Public **`GET /api/listings/`** excludes leased properties; **`?mine=1`** (landlord/realtor) still returns them. **`GET /api/listings/<id>/`** is allowed for anonymous/unrelated users only if `leased=False`; renters with a **reservation** on that listing and the **lister** can still open the detail.

Replace `sign_with_token` internals + add vendor webhooks when connecting DocuSign / Dropbox Sign.

**Recommended for production**
- E-sign SaaS + webhooks; store `provider_metadata` envelope ids.
- **QR on desktop** → same signing URL on **phone** for clearer signatures.
- Bind URL/token to the correct signer; handle expiry; typed signature where needed.

---

## 6. Local development (testing)

### Prerequisites
- Python 3.x, Node.js (for Vite).
- **Backend:** from `yallastay_backend/yallastay/` (folder with `manage.py`): `pip install -r ../requirements.txt`
- **Frontend:** sibling **Vite** repo named `yallastay` on Desktop (`../yallastay` next to `yallastay_backend`); **not** the Django package folder inside this backend repo: `npm install`

### Backend - run
```bash
cd yallastay_backend/yallastay
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```
- API root: `http://localhost:8000/` (JSON `{"message":"Yallastay API",...}`)
- Admin: `http://localhost:8000/admin/` (create superuser if needed)
- **Media in dev:** `DEBUG` serves `/media/` for uploads (listing images, avatars).

### Frontend - run
From **`yallastay_backend`** repo root (same level as `requirements.txt`):

```bash
cd ../yallastay
npm run dev
```
- Default **Vite port is `3000`** (`vite.config.js`).
- **Proxy:** `/api` and `/media` → `http://localhost:8000` - so the browser uses **`http://localhost:3000`** and **no CORS** issues for `/api/*`.

### Frontend - unit tests (Vitest)
- **Source:** `src/` only; **tests:** `tests/unit/**/*.{test,spec}.{js,jsx}` only (no `*.test.*` under `src/`).
- **Setup:** `tests/setup/vitest.setup.js` (test-only; not imported by the app).
- **Imports:** `@/` → `src/` (see `vite.config.js` `resolve.alias`).
From **`yallastay_backend`** repo root:

```bash
cd ../yallastay
npm test
npm run test:watch
```
- **E2E (Playwright):** `npm run test:e2e` - specs live under `e2e/` (separate from Vitest).

### Frontend API base
- **`VITE_API_URL` unset:** axios uses **`/api`** (same origin as Vite → proxy to Django). **Recommended for local.**
- **`VITE_API_URL=http://localhost:8000/api`:** direct to Django (ensure CORS if origin differs).

### JWT in local testing
1. `POST /api/auth/register/` or `POST /api/auth/login/`
2. Store **`token`** (access) in `localStorage` - frontend client does this on login.
3. Use **Bearer** on protected routes (client attaches automatically).

### Payment - **stub** (default, no Stripe account)
1. Set **`PAYMENT_PROVIDER=stub`** or omit (default).
2. **`FRONTEND_URL`:** use the URL users actually open - for Vite dev that is typically **`http://localhost:3000`** (not 5173 unless you change Vite port).

   Set in backend `.env` (loaded from `yallastay/.env` or parent):
   ```env
   FRONTEND_URL=http://localhost:3000
   PAYMENT_PROVIDER=stub
   ```

3. Flow:
   - Create reservation (e.g. rent from property page with deposit).
   - `POST /api/payments/initiate/` with `reservation_id`, `payment_type`, `amount`, `currency`.
   - UI shows **StubPaymentModal** → **Simulate payment completed** → calls `POST /api/payments/webhook/stub/` with `transaction_id`.
   - For **realtor message**: payment must be **`rent`** or **`deposit`** and linked to **`reservation`**.

4. **Manual curl (stub webhook):** use **`Authorization: Bearer <access_token>`** for the payment owner, or **`X-Stub-Webhook-Secret`** when **`STUB_WEBHOOK_SECRET`** is set on the API.
   ```bash
   curl -X POST http://localhost:8000/api/payments/webhook/stub/ \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <access_token>" \
     -d '{"transaction_id": "ys_xxxxxxxx"}'
   ```

### Payment - **Stripe test mode** (local)
1. Install Stripe CLI; login; get **test** API keys from Dashboard.
2. Backend `.env`:
   ```env
   PAYMENT_PROVIDER=stripe
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...   # from `stripe listen`
   STRIPE_PUBLISHABLE_KEY=pk_test_...
   FRONTEND_URL=http://localhost:3000
   ```
3. Forward webhooks to local Django:
   ```bash
   stripe listen --forward-to localhost:8000/api/payments/webhook/stripe/
   ```
   Use the **`whsec_`** secret the CLI prints as `STRIPE_WEBHOOK_SECRET`.

4. Initiate payment from UI → redirect to Stripe Checkout → pay with **test card** `4242 4242 4242 4242` → redirect to `/payment/success` on your frontend.

### Emails (local)
- Default: **console** backend - emails print to the terminal, not sent.

### Useful local URLs (frontend routes)
| Path | Page |
|------|------|
| `/` | Home |
| `/search` | Listings |
| `/property/:id` | Listing detail, rent, message, favorites |
| `/messages` | Conversations |
| `/user/:id` | Public profile |
| `/dashboard` | Account, reservations, deposit pay |
| `/payment/success` | Stripe return (success) |
| `/payment/cancel` | Stripe return (cancel) |
| `/login`, `/signup`, `/verify` | Auth |
| `/backend` | API connectivity checklist (lists main endpoints) |

---

## 7. Production

### Principles
- **`DEBUG=False`**, **`SECRET_KEY`** from env, **`ALLOWED_HOSTS`** set.
- **HTTPS** everywhere (TLS termination at load balancer or reverse proxy).
- **Database:** PostgreSQL (or managed DB) - not SQLite for production traffic.
- **`FRONTEND_URL`** = public SPA origin (e.g. `https://app.yallastay.com`).
- **`BACKEND_URL`** = public API origin (e.g. `https://api.yallastay.com`) for links in emails and Stripe redirects if you use absolute API URLs.

### Stripe (live)
- **`PAYMENT_PROVIDER=stripe`**
- **`STRIPE_SECRET_KEY=sk_live_...`**, **`STRIPE_PUBLISHABLE_KEY=pk_live_...`**
- **Webhook endpoint (HTTPS):**  
  `https://<your-api-domain>/api/payments/webhook/stripe/`  
  - Event: **`checkout.session.completed`** (server also checks `payment_status == paid`).
- **Dashboard:** add the exact URL; use **signing secret** from Dashboard as `STRIPE_WEBHOOK_SECRET` (production endpoint, not CLI).

### CORS
- Replace blanket `CORS_ALLOW_ALL_ORIGINS` with **explicit allowed origins** (your frontend origin only) in production settings.

### Frontend build
From **`yallastay_backend`** repo root:

```bash
cd ../yallastay
npm run build
```
- Set **`VITE_API_URL=https://<api-domain>/api`** (or relative `/api` if SPA and API share the same host behind nginx).

### Static/media
- Run **`collectstatic`**; serve static via WhiteNoise or CDN.
- **User uploads** (`MEDIA_ROOT`): S3-compatible storage or persistent volume - not only local disk on ephemeral servers.

### Team system user
- **`YALLASTAY_TEAM_USER_EMAIL`:** use a dedicated internal address that **never** appears on the public registration form.

### Monitoring
- Log Stripe webhook failures; alert on 5xx on payment routes.

---

## 8. Backend workflows (API order)

### Auth
1. `POST /api/auth/register/` or `POST /api/auth/login/` → JWT `access` (+ refresh if used).
2. `GET /api/auth/me/` → user + profile + role.

### Verification (renters)
- `GET /api/verification/status/`
- UAE ID / university flows per `accounts` + `verification` URLs (see project `urls.py`).

### Listings
- `GET /api/listings/`, `GET /api/listings/<id>/`
- Create/update listing (lister/realtor) per permissions.

### Rental request (reservation)
1. Renter must satisfy app rules (e.g. UAE ID verified - enforced in views).
2. `POST /api/listings/<listing_id>/rent/` with `start_date`, `end_date`, optional `deposit_amount`, `notes`.
3. Response: **`Reservation`** JSON including **`id`**.

### Payments
1. `POST /api/payments/initiate/`  
   Body example:  
   `{ "payment_type": "deposit", "amount": "5000.00", "currency": "AED", "reservation_id": <pk> }`  
   - **`rent`** / **`deposit`** require **`reservation_id`**.
2. **Stub:** complete via `POST /api/payments/webhook/stub/` with `transaction_id` (JWT as payer or shared secret header when configured).  
   **Stripe:** Checkout completes → `POST .../webhook/stripe/` from Stripe.
3. On first **completed** for rent/deposit with reservation → **team message** in messaging thread.

### Messaging
1. `POST /api/conversations/` with `listing_id` (UAE ID rules apply).
2. `GET /api/conversations/` - list with `listing_detail`, `other_user`.
3. `GET /api/conversations/<id>/messages/` - `{ messages, conversation }`.
4. `POST /api/conversations/<id>/messages/` - send (UAE ID rules apply).

### Public profile
- `GET /api/auth/users/<id>/public-profile/`

### Reviews
- `GET /api/reviews/?user=<id>` (reviewee filter) - see `reviews` app.

*(Other apps: favorites, viewings, documents, notifications, roommates - see `yallastay/urls.py` and `BackendConfig.jsx` in frontend for paths.)*

---

## 9. Frontend workflows (user journeys)

### Renter (typical)
1. **Sign up / log in** → token stored.
2. **Verify** (UAE ID, etc.) via `/verify` until actions unlock. The nav shows **Verified** when the backend reports **approved**; **Verify** and **Profile** reflect **pending / rejected / approved** (not only “submit once”).
3. **Search** / **Home** - **leased** listings are hidden from public catalog; **Property** for a leased unit is only reachable for parties with a reservation or the lister (see §5).
4. **Property** - if the current user **already has a reservation** on this listing (pending, confirmed, or leased): primary CTAs shift to **Manage rental** / **View rental on dashboard**; **Rent** is hidden; **Request viewing** is hidden when the reservation is **leased**; the rent modal closes when a reservation appears after refresh or navigation.
5. After request with **deposit amount** → **Proceed to payment** (stub modal or Stripe redirect).
6. **Dashboard** → **Reservations** → **Pay deposit** (amount + same payment flow).
7. **Messages** - thread shows listing card + counterparty link to **`/user/:id`**.
8. **Payment success** - `/payment/success` after Stripe; stub uses modal instead.

### Realtor / landlord
1. Listings (dashboard / add property), manage inquiries.
2. **Messages** with renters; **public profile** of renter when linked from thread.
3. After renter **pays** (stub or Stripe), **Yallastay Team** message appears in the **same listing thread** with next-step copy.
4. **Realtor dashboard** includes a **Reservations** section for rental-related activity on their listings.

### Partners / marketing (`For partners`)
- Logged-in **realtors** (and similar roles) who tap **List your property** go to **`/add-property`**, not the signup funnel.

### Dev / QA quick checks
- Stub payment end-to-end without Stripe.
- Stripe test mode with CLI webhook forwarding; confirm **`payment_method`** on `Payment` after `checkout.session.completed`.
- Toggle only **`PAYMENT_PROVIDER`** and keys between stub and Stripe without changing frontend code paths (UI branches on `provider` in response).

---

## 10. Environment variables reference

### Backend (common)

| Variable | Local (typical) | Production (typical) |
|----------|------------------|----------------------|
| `SECRET_KEY` | Dev default if unset | **Required**, strong random |
| `DJANGO_ENV` | - | `production` to enforce strict settings |
| `DEBUG` | `True` | **`False`** |
| `ALLOWED_HOSTS` | Empty / dev | **Comma-separated hosts** |
| `FRONTEND_URL` | `http://localhost:3000` | `https://your-app-domain` |
| `BACKEND_URL` | `http://localhost:8000` | `https://your-api-domain` |
| `PAYMENT_PROVIDER` | `stub` or `stripe` | `stripe` |
| `STRIPE_SECRET_KEY` | `sk_test_...` | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | From `stripe listen` | From Stripe Dashboard webhook |
| `STRIPE_PUBLISHABLE_KEY` | `pk_test_...` | `pk_live_...` |
| `YALLASTAY_TEAM_USER_EMAIL` | Default internal | Dedicated non-signup email |
| `EMAIL_BACKEND` | Console | SMTP / provider |
| `DATABASE_URL` | SQLite default | PostgreSQL URL if used |
| `TIME_ZONE` | `Asia/Dubai` | `Asia/Dubai` |

### Frontend

| Variable | Local | Production |
|----------|-------|------------|
| `VITE_API_URL` | Empty (use proxy `/api`) or `http://localhost:8000/api` | `https://api.yourdomain.com/api` |

---

## 11. Misc fixes

- **`bookings/serializers.py`:** Removed unused `timedelta` import (lease date validation uses `timezone.now().date()` and date arithmetic).
- **Backend config (dev):** `BackendConfig.jsx` uses distinct React keys for GET vs POST on the same e-sign path so the console does not warn about duplicate keys.
- **Public listings:** `leased` and completed lease-signing sessions exclude listings from anonymous search/home while preserving rows for owners and related parties.

---

## 12. Related repos

- **Backend:** `yallastay_backend` (this doc’s folder).
- **Frontend:** `yallastay` - keep payment return URLs and `FRONTEND_URL` aligned with the port users actually use (Vite defaults to **port 3000** in this project).

---

*Document covers: vision, messaging, profiles, payments (stub + Stripe, `payment_method`, Stripe runbook), team message, local vs production runbooks, backend API order, frontend journeys (verification states, reservation-aware property CTAs, partner links), env reference, signing/QR roadmap.*
