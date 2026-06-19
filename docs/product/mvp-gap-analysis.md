# Yallastay - MVP gap analysis (backend + frontend)

| | |
|---|---|
| **Distribution** | **Internal - engineering.** Do **not** send verbatim to clients; use [`../client/README.md`](../client/README.md) for client-safe documents. |

This document compares **what exists today** in the **backend** (`yallastay_backend` / Django under `yallastay/`) and **frontend** (sibling repo `yallastay`, Vite + React) against a **credible first production MVP** for a UAE-oriented rental marketplace: listings, bookings, payments, messaging, documents, and lease e-signing.

It is **not** a commitment to build every item - use it to prioritize. **Prioritized production/contract gaps:** [`production-readiness-gaps.md`](./production-readiness-gaps.md). **How to collect proof for diligence or security reviews:** [`../diligence/evidence-preparation.md`](../diligence/evidence-preparation.md). Security & privacy overview: [`../SECURITY_CHECKLIST.md`](../SECURITY_CHECKLIST.md); platform workflows: [`../platform/vision-and-implementation.md`](../platform/vision-and-implementation.md).

---

## 1. What is already in decent shape

| Area | Notes |
|------|--------|
| **Core API** | Django REST Framework, JWT (SimpleJWT + blacklist app), role/verification checks on sensitive routes (`accounts`, `listings`, `bookings`, etc.). |
| **Data model** | Listings, reservations, payments, messaging, notifications, documents, roommates, analytics hooks, e-sign sessions + audit events. |
| **Payments** | Stub + **Stripe Checkout**; webhook signature verification for Stripe; hooks for post-payment messaging and **lease signing session** creation. |
| **E-sign (stub)** | Magic-link signing, PDF upload, multi-slot signatures, UAE consent + audit trail, signed PDF rebuild - **not** a commercial e-sign provider. |
| **PostgreSQL RLS** | Optional row-level security for a subset of tables (see [`../DATABASE_RLS.md`](../DATABASE_RLS.md)) - complement to app-level permissions. |
| **Global API throttling** | DRF `AnonRateThrottle` / `UserRateThrottle` configured in settings. |
| **Frontend surface** | Major routes: search, property, auth, dashboard, realtor tools, payments success/cancel, **SignLease**, messages, notifications, documents, roommates, etc. |
| **Tests** | Substantial backend `tests/` and frontend Vitest units; Playwright present (screenshot-oriented). |

---

## 2. Feature gaps (product MVP)

### 2.1 End-to-end journey

- **Single happy path polish:** Search → shortlist → book/viewing → reservation → pay → lease PDF → both sign → **clear “what happens next”** (Ejari, handover) is only partially reflected in copy/emails, not a guided checklist in-app.
- **Ejari / DLD:** `dld_metadata` and vision docs point to future automation - **no** integrated government flow for MVP; treat as **manual + education** unless scope expands.
- **Bank transfer / non-card rent:** Documented as out of scope in platform docs - **no** unified in-app flow.

### 2.2 Auth & accounts

- **Password reset / forgot password:** Backend may use token generators (`accounts/tokens.py`); **frontend route and full UX** should be verified end-to-end (many MVPs ship without this - high support cost).
- **Email verification:** Verify page exists; ensure **all** registration paths and **resend** limits align with security expectations (see checklist §9).
- **Centralized route protection:** Frontend relies on **per-page** `localStorage` token checks and axios 401 redirect - **no** unified `ProtectedRoute` / auth context → inconsistent deep-link behavior and brief flashes of protected content.

### 2.3 Listings & search

- **Moderation:** Admin exists; product-level **report listing**, **appeals**, and **automated abuse** workflows may be minimal or missing for MVP scale.
- **Availability & calendar:** Depends on implementation - often **manual** for MVP; real-time sync with external calendars is usually **post-MVP**.

### 2.4 Bookings & payments

- **Refunds / disputes / receipts:** Stripe backend can record payment method labels; **in-app refund UI**, **dispute handling**, and **downloadable invoice** may be incomplete vs user expectations.
- **Payment provider:** `PAYMENT_PROVIDER=stub` must **never** be used for real money; production runbook must enforce **Stripe** (or chosen PSP) only.

### 2.5 E-sign

- **Legal weight:** Current flow = **drawn PNG + PDF + audit DB** - fine for **internal MVP**; **UAE counsel** may require **TDRA-trusted** or **DocuSign-class** provider for some use cases.
- **Magic link = possession of secret URL** - not liveness or government ID at signing time; **identity story** for disputes is “account + email + audit,” not qualified signature.

### 2.6 Messaging & notifications

- Core APIs exist; MVP gaps are often **push on mobile web**, **email digests**, and **SLA** for support - optional for first launch.

### 2.7 Documents & media storage

- Upload/storage models exist; **private file access** (see §3) is the main MVP risk, not “feature missing” but **access model** must be correct.
- **Object storage (S3):** Default dev uses **local `media/`**; production should set **`AWS_STORAGE_BUCKET_NAME`** (and related env) so **new uploads** go to **S3**; DB rows store **paths/keys only**, never file blobs in PostgreSQL. See [`../operations/media-storage-s3.md`](../operations/media-storage-s3.md). **Gap:** legacy rows that still point at **`/media/...` on disk** need a **migration plan** (copy to bucket + path update) if you previously ran on local files only.

---

## 3. Security gaps (pre-launch priority)

Aligned with [`../SECURITY_CHECKLIST.md`](../SECURITY_CHECKLIST.md):

| Item | Risk | MVP note |
|------|------|----------|
| **Stub payment webhook** (`AllowAny`, transaction id) | Critical if exposed publicly | **Disable or firewall** in production; use Stripe webhooks only. |
| **JWT in `localStorage`** | XSS → token theft | Short-lived access + refresh blacklist helps; **CSP** on frontend, sanitize user HTML; consider **httpOnly cookie** auth later. |
| **CORS** | `base.py` allows all origins by default | **Prod** uses explicit origins - ensure **dev** doesn’t accidentally deploy with open CORS. |
| **HSTS** | Missing `SECURE_HSTS_*` | Add after HTTPS stable (checklist §3). |
| **Private media** | `/media/` in DEBUG; local disk in dev | Prod must use **private bucket** + **signed URLs** (or authenticated proxy) for sensitive docs; not public `/media/` for ID/lease. **Configurable:** `django-storages` S3 when `AWS_STORAGE_BUCKET_NAME` is set; see [`../operations/media-storage-s3.md`](../operations/media-storage-s3.md). |
| **Auth endpoint throttling** | Global throttles only | Tighten **login/register/reset** (ScopedRateThrottle or edge/WAF). |
| **IDOR** | RLS doesn’t cover all apps | Periodic review of **object access by id** (`messaging`, `payments`, `esign`, etc.). |
| **Django admin** | `/admin/` | Strong passwords, 2FA for staff, IP allowlist if possible. |
| **Frontend security headers** | CSP, frame-ancestors, Referrer-Policy | Usually **CDN / static host** - track as launch item. |

---

## 4. Frontend-specific gaps

| Topic | Gap |
|-------|-----|
| **Auth consistency** | Login uses raw `fetch` to `/api/auth/login/` while other calls use **axios** - base URL / proxy edge cases; unify on one client. |
| **Error handling** | No **React error boundary**; API errors handled **per page** - consider global toast + normalized error type. |
| **Token refresh** | Rely on SimpleJWT refresh flow in client - verify **silent refresh** and **multi-tab** behavior (header uses `storage` events - partial). |
| **E2E** | Playwright is **screenshot-heavy**; add **critical path** tests: login → pay → sign (even smoke). |
| **Accessibility & i18n** | Not evidenced as systematic - MVP often ships **English-first** with a11y backlog. |

---

## 5. Backend / ops gaps

| Topic | Gap |
|-------|-----|
| **Root README** | Use **[`README.md`](../../README.md)** at repo root; detailed docs live under **`docs/`**. |
| **CI/CD** | Not verified in this analysis - ensure **tests + migrate + collectstatic** (if used) on each deploy. |
| **Observability** | Structured logging, error tracking (**Sentry** or similar), uptime checks - **assumed** to be configured per environment; confirm for MVP. |
| **Backups & DR** | Database and **object storage** (S3 versioning/lifecycle) for media; **operations**, not app code. See [`../operations/monitoring-and-backups.md`](../operations/monitoring-and-backups.md). |
| **Settings selection** | `settings/__init__.py` infers **prod** from env (e.g. `DATABASE_URL`) - confirm **staging** doesn’t accidentally use prod-like settings unintentionally. |

---

## 6. Compliance & legal (non-technical)

- **UAE rental / broker regulations:** Product and copy should be reviewed by **local counsel** (not covered by code review).
- **Privacy / PDPL:** Privacy policy, data retention, and **subprocessors** (Stripe, email, hosting) - document and link in-app.
- **Terms of use** for landlords, renters, and realtors - **legal** deliverable, not only engineering.

---

## 7. Suggested MVP “definition of done” (engineering)

**Must-have before real users and money**

1. Production settings: **HTTPS**, **secrets in env**, **CORS/ALLOWED_HOSTS** locked, **Stripe live** + webhook secret, **stub webhook unreachable** from internet.  
2. **Private documents** access model decided and implemented; **user uploads** on **S3** (or equivalent) in prod; **not** relying on container-local `media/` for new files ([`../operations/media-storage-s3.md`](../operations/media-storage-s3.md)).  
3. **HSTS** (when HTTPS stable), rate limits on **auth** endpoints reviewed.  
4. **Password reset** + **email verification** flows tested end-to-end on production-like env.  
5. **Smoke E2E** or manual runbook: register → listing → book → pay → sign → download PDF.  
6. **Monitoring** + alert on 5xx and payment webhook failures.

**Nice-to-have first sprint after launch**

- CSP / security headers on frontend host.  
- Stricter throttles and WAF rules.  
- httpOnly cookie auth **or** hardened SPA token strategy.  
- Commercial e-sign **when** legal/commercial requires it.

---

## 8. Document maintenance

- **Owner:** Engineering + product.  
- **Update when:** Major flows ship (payments, e-sign, documents), or security review completes.  
- **Related:** [`../platform/vision-and-implementation.md`](../platform/vision-and-implementation.md), [`../SECURITY_CHECKLIST.md`](../SECURITY_CHECKLIST.md), [`../operations/media-storage-s3.md`](../operations/media-storage-s3.md), [`../payments/stripe-setup.md`](../payments/stripe-setup.md), [`../esign/pdf-signing-agreement.md`](../esign/pdf-signing-agreement.md).

---

*Generated as a structured gap review; adjust priorities to match your launch geography, funding, and legal advice.*
