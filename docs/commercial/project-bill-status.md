# YallaStay - whole-project bill & delivery status

| | |
|---|---|
| **Distribution** | **Confidential - commercial.** Internal and **signed** client engagements; **not** a general marketing handout. |

This document is the **commercial bill** aligned with **[`bill-template.md`](./bill-template.md)** (§4.1-§4.6) and **[`bill-detailed.md`](./bill-detailed.md)** (technical line items), with an explicit **Finished / Partial / Not started** column so stakeholders can see what is done vs. outstanding.

**Amounts** below match the template **§4.6** (one-time build, excl. VAT). Status reflects **this repository** (backend + in-repo web) as of the last doc update; **native mobile** is priced in the bill but **not present in this repo**.

| Layer (§4.6) | Amount (AED) | Overall status |
|--------------|-------------:|----------------|
| Backend (§4.1) | 381,700 | **Mostly delivered** - see Part A; gaps: UAE ID live API, some hardening, optional scaling |
| Web (§4.2) | 74,500 | **Mostly delivered** - see Part B; ongoing polish |
| iOS + Android (§4.3) | 175,000 | **Not started** (separate codebase / engagement) |
| Deployment & wiring (§4.4) | 44,000 | **Partial** - env-specific; client/production setup varies |
| Documentation (§4.5) | 8,500 | **Largely delivered** - see Part C |
| **Total (excl. tax)** | **683,700** | |

*Recurring §4.7 support and optional §4.8 scaling are **not** included in the table above.*

---

## Legend

| Status | Meaning |
|--------|---------|
| **Finished** | Implemented and usable in-repo for the described scope; may still need production config or minor fixes. |
| **Partial** | Core exists; missing features, integration, hardening, or production-only steps called out in notes. |
| **Not started** | Not in this repo or not begun; priced in the bill but not delivered here. |

---

## Part A - Backend API (§4.1, 381,700 AED)

| Block | Amount | Status | Notes |
|-------|-------:|--------|--------|
| **A.1** Authentication & user management | 28,000 | **Partial** | JWT, register/login, profiles, `me`, verification models, admin. **Password reset** end-to-end may need verification in your environment. |
| **A.1b** UAE ID verification (live API) | 18,000 | **Not started** | Main **MVP gap**: stub/placeholder path; live UAE ID API integration not completed ([`../product/mvp-gap-analysis.md`](../product/mvp-gap-analysis.md)). |
| **A.2** Core platform | 22,000 | **Finished** | Health, settings, enums, locations. |
| **A.3** Property listings | 38,000 | **Finished** | CRUD, search, filters, media, map, landlord dashboard alignment. |
| **A.4** Bookings & reservations | 42,000 | **Finished** | Flows, calendar, landlord actions; ties to payments where implemented. |
| **A.5** Reviews & ratings | 18,000 | **Finished** | |
| **A.6** Payments & billing (Stripe) | 45,000 | **Partial** | Stripe Checkout + webhooks implemented; **stub webhook** must **not** be exposed in production ([`../payments/stripe-setup.md`](../payments/stripe-setup.md)). Refunds/admin UX may be partial. |
| **A.7** Messaging | 32,000 | **Finished** | Threads, WebSocket consumer, REST. |
| **A.8** Lifestyle & subscriptions | 28,000 | **Partial** | API + models; full in-app subscription + pay journey may need more work. |
| **A.9** Notifications | 24,000 | **Partial** | In-app + models; **push (FCM)** not fully delivered ([`../product/mvp-gap-analysis.md`](../product/mvp-gap-analysis.md)). |
| **A.10** Analytics & reporting | 22,000 | **Finished** | Landlord/property metrics APIs. |
| **A.11** Reports & exports | 18,000 | **Finished** | |
| **A.12** Roommate matching | 26,000 | **Finished** | |
| **A.13** Document management | 24,000 | **Partial** | Upload/list/delete; **private signed URLs** for production file access called out as gap ([`../product/mvp-gap-analysis.md`](../product/mvp-gap-analysis.md)). |
| **E-sign & lease contracts** (priced with Part A) | 28,000 | **Partial** | In-app **stub** PDF signing + audit + consent + multi-slot flow; **DocuSign-class** provider not integrated. |
| **A.14** Project shell & cross-cutting | 20,000 | **Partial** | Django split settings, CORS, throttling, structured logging, Sentry hook, security checklist doc. **HSTS**, **media upload hardening**, **dependency audit** still called out as gaps. |
| **A.15a** SMS integration | 8,000 | **Finished** | `communications` app; Twilio-capable; production SMS = client keys. |
| **A.15b** Email (SendGrid/SES) | 8,000 | **Finished** | Same pattern; production = client keys. |

**Part A summary:** The majority of modules are **Finished**. The main **Not started** item priced here is **A.1b (UAE ID live)**. **Partial** items: payments (prod webhook discipline), documents (signed URLs), notifications (push), lifestyle depth, e-sign (provider-grade), A.14 hardening.

---

## Part B - Web application (§4.2, 74,500 AED)

| Block | Amount | Status | Notes |
|-------|-------:|--------|--------|
| **B.1** Shell & routing | 6,500 | **Finished** | Layout, nav, theme, i18n. |
| **B.2** Marketing & public | 8,000 | **Finished** | Home, listings browse, listing detail, map, lifestyle marketing. |
| **B.3** Auth & onboarding | 9,000 | **Partial** | Login/register/forgot flows; align with backend reset behaviour. |
| **B.4** Tenant dashboard & flows | 14,000 | **Finished** | Bookings, favorites, reviews, roommate, lifestyle, profile, messages. |
| **B.5** Landlord dashboard | 12,000 | **Finished** | Listings, bookings, analytics, payments views. |
| **B.6** Messaging UI | 8,000 | **Finished** | |
| **B.7** Lifestyle UI | 6,500 | **Partial** | Depends on A.8 depth. |
| **B.8** Notifications UI | 5,000 | **Partial** | In-app list; push-dependent UX incomplete. |
| **B.9** Payments UI | 5,000 | **Partial** | Checkout/success/cancel + lease sign page; production Stripe config on client. |

**Part B summary:** **Mostly Finished**; **Partial** where tied to A.6, A.8, A.9, or auth edge cases.

---

## Part C - Documentation (§4.5, 8,500 AED)

| Block | Amount | Status | Notes |
|-------|-------:|--------|--------|
| Repo docs (API mapping, commands, testing, vision, Stripe) | 8,500 | **Finished** | [`README.md`](../README.md) index; [`../platform/vision-and-implementation.md`](../platform/vision-and-implementation.md); [`../payments/stripe-setup.md`](../payments/stripe-setup.md); product/gap docs. **[`FRONTEND_BACKEND_MAPPING.md`](../FRONTEND_BACKEND_MAPPING.md)** and **[`ARCHITECTURE.md`](../ARCHITECTURE.md)** live in **`docs/`** with the rest of the repo documentation. |

---

## Part D - Deployment & external wiring (§4.4, 44,000 AED)

| Block | Amount | Status | Notes |
|-------|-------:|--------|--------|
| Host & DB, SSL, web build, integrations env | 44,000 | **Partial** | **Not** fully automatic: Railway (or other) project, domain, secrets, and go-live are **per-environment**. Codebase supports 12-factor config; client completes hosting and DNS. |

---

## Part E - Mobile iOS & Android (§4.3, 175,000 AED)

| Block | Amount | Status | Notes |
|-------|-------:|--------|--------|
| **iOS** | 88,500 | **Not started** | Described in [`../product/mobile-roadmap.md`](../product/mobile-roadmap.md); **no app in this repo**. |
| **Android** | 86,500 | **Not started** | Same. |

---

## Optional / out of scope (reference)

| Item | In bill? | Status |
|------|----------|--------|
| §4.7 Monthly support (~9,500 AED/mo) | Priced separately | Not included unless contracted |
| §4.8 Scaling package (22,000 AED) | Optional add-on | Not started unless ordered |
| §4.6 optional **Extra DR** (~35,000 AED) | Optional | Not started unless ordered |
| PayTabs and additional PSPs (mentioned in gap analysis) | Not in §4.6 line items | **Not started** |

---

## Related documents

| Document | Role |
|----------|------|
| [`bill-template.md`](./bill-template.md) | Formal SOW / invoice structure and §4.6 totals |
| [`bill-detailed.md`](./bill-detailed.md) | File-level technical mapping per block |
| [`../product/mvp-gap-analysis.md`](../product/mvp-gap-analysis.md) | Engineering gaps vs. MVP |
| [`../product/mobile-roadmap.md`](../product/mobile-roadmap.md) | Future native mobile |

---

*This status bill should be updated when major milestones close (e.g. UAE ID live, mobile kickoff, production go-live).*
