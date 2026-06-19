# Invoice / Statement of Work - Yallastay SaaS

| | |
|---|---|
| **Distribution** | **Confidential - commercial.** Share only under **signed NDA** or as part of a **quote / SOW**. Redact placeholders before informal sharing. |

> **Deep technical breakdown** (models, endpoints, pages): **[bill-detailed.md](./bill-detailed.md)**.

---

## 1. Document header

| Field | Value |
|-------|--------|
| **Invoice / Quote #** | `[INV-YYYY-NNN]` |
| **Issue date** | `[DD Month YYYY]` |
| **Due date** | `[DD Month YYYY]` |
| **Currency** | `[e.g. AED]` |
| **Project** | Yallastay - rental & lifestyle SaaS (Dubai); API consumed by **web, iOS, Android** |

---

## 2. Parties

**Vendor**  
`[Company legal name]`  
`[Address line 1]` · `[City, Country]`  
`[Email]` · `[Phone]`  
`[Tax ID / company number]`

**Client**  
`[Client company name]`  
`[Address line 1]` · `[City, Country]`  
`[Email]` · `[Phone]`  
`[Tax ID - if applicable]`

---

## 3. What you’re buying (overview)

One **Django REST API** plus **web**, **iOS**, and **Android** clients on the same contract. Same JWT and `/api/...` surface everywhere.

**Product rules (core scope):** **Lifestyle services** are **managed end-to-end in the app** (plans, subscriptions, flows). Most journeys stay **gated on UAE ID verification** - **live UAE ID API** integration and **Stripe** checkout are **included** in this quote, not optional add-ons.

**Rental & lease flow (as implemented):** **Reservations** → deposit/rent via **Stripe Checkout** (or **stub** in dev) → **webhooks** complete payments and drive follow-up (team message, **lease signing** via magic links). **E-sign** records signatures in order; when a lease is **fully signed**, the **listing** is marked **leased** and **public search / home** hide that unit while owners and related parties retain access. **Verification** UX reflects **pending / rejected / approved** from the API (not only “submit once”).

**Backend surface (repos):** **16** Django apps under `INSTALLED_APPS` - `core`, `accounts`, `listings`, `bookings`, `reviews`, `payments`, `messaging`, `lifestyle_services`, `notifications`, `analytics`, `reports`, `roommates`, `documents`, **`sms`**, **`emails`**, **`esign`**. **Cross-cutting:** payment **hooks** (team chat, e-sign session, payer receipt), **SendGrid** + **Twilio** inbound webhooks, **JWT** + blacklist refresh, **throttling** / **django-filter**, **WhiteNoise** static.

| Layer | Role |
|-------|------|
| **Backend** | Business logic, data, admin, integrations hooks |
| **Web** | React app (`yallastay`) |
| **iOS / Android** | Native or cross-platform apps consuming the same API |
| **Ops** | Railway (or similar): deploy, DB, SSL, env, external services wiring |
| **Docs** | Runbooks, API mapping, testing notes (repo) |

---

## 4. Scope & pricing (short)

*Amounts use the same **currency** as §1 (figures below use **AED**).*

### 4.1 Backend API

| Block | What’s included (short) | Amount |
|-------|-------------------------|--------|
| **Auth & verification** | Users, roles, **JWT** + refresh/blacklist, university flows; **public profile** for trust in threads | 32,000 |
| **UAE ID (live API) & gated access** | Official **UAE ID** integration, verification state, **gate** lifestyle and core flows until verified | 45,000 |
| **Reference data** | Areas, universities | 7,200 |
| **Listings** | Properties, images (multipart, cap), favorites, search filters; **interested users** (lister-only); **`leased`** visibility rules for public vs parties | 32,000 |
| **Bookings** | Viewings, reservations, **`POST /listings/<id>/rent/`**, reservation state | 16,800 |
| **E-sign & lease contracts** | Dedicated **`esign`** app: `LeaseSigningSession`, per-party tokens, sign order, preview/sign APIs, signals → **`leased`** + notifications; orchestration from **payment completion** | 28,000 |
| **Cross-cutting integrations** | **SendGrid** event webhook (`/api/emails/...`), **Twilio** SMS status webhook (`/api/sms/...`); **`GET .../public-profile/`**; **verify-email resend**; **Yallastay Team** user + payment-triggered messaging; notification types **payment** / **esign** / **contract**; REST **throttling** & filters | 14,000 |
| **Reviews** | Reviews + responses | 13,500 |
| **Payments & Stripe** | **Stripe** Checkout (`mode=payment`) or **stub**: initiate, redirects, **`checkout.session.completed`** webhook, **`payment_method`** labels (e.g. card brand, **Apple Pay / Google Pay** via Stripe), payment records, reconciliation (API + mobile paths); **bank transfer** not part of the current Checkout flow | 38,000 |
| **Messaging** | Conversations, messages, read state | 24,500 |
| **Lifestyle** | **In-app** lifestyle plans, services, subscriptions - managed inside the product | 15,200 |
| **Notifications** | In-app notifications + **per-channel preferences**; types include **payment**, **esign**, **contract**, booking, viewing, etc. | 12,600 |
| **Analytics** | Realtor demographics, popular areas, listing insights | 15,800 |
| **Reports** | User reports for moderation | 9,800 |
| **Roommates** | Profiles, search, interests | 18,900 |
| **Documents** | Upload/list documents | 13,400 |
| **SMS sent** | **Sent-SMS** model(s): delivery status, retries, idempotency hooks, admin visibility, **Twilio** provider + **status callback** webhook | 12,000 |
| **Email sent** | **Sent-email** model(s): templates, queue, status, admin visibility, **SendGrid** (or similar) + **event** webhook for delivery metrics | 12,000 |
| **Project** | Admin, settings, CORS, migrations, **pytest** coverage across apps, API root | 22,000 |
| | **Subtotal** | **381,700** |

### 4.2 Web app (React)

| Block | What’s included (short) | Amount |
|-------|-------------------------|--------|
| **Shell** | Vite, routes, Tailwind, layout, motion | 6,500 |
| **API client** | Axios, token, **16** API groups (incl. **payments**, **esign**), `publicApiUrl` for unauthenticated sign preview, 401 handling | 10,000 |
| **UI** | Header, footer, property cards | 7,500 |
| **Auth & verify** | Login, signup, verify; **verification status** in UI (pending / rejected / approved), nav **Verified** when approved | 8,500 |
| **Discovery** | Home, search, property, add listing; **leased** listings excluded from public catalog; property **reservation-aware** CTAs (manage / view dashboard, hide rent & viewing when appropriate) | 12,500 |
| **Dashboards** | User + realtor + analytics; realtor **reservations** section where applicable | 10,000 |
| **Engagement** | Messages, notifications, roommates, documents | 12,500 |
| **Other** | Services, partners (e.g. **list property** → `/add-property` when logged in), backend health page; **payment success/cancel** routes; **lease sign** page (`/sign/lease/:token`); **LeaseContractsSection**, **RentalReservationsSection**, **StubPaymentModal**, `paymentCheckout` util; **Vitest** tests (e.g. sign page) | 7,000 |
| | **Subtotal** | **74,500** |

### 4.3 Mobile - iOS & Android

| Block | What’s included (short) | Amount |
|-------|-------------------------|--------|
| **iOS** | App shell, networking, auth, listings, dashboards, engagement, App Store release | 88,500 |
| **Android** | Same for Android stack + Play release | 86,500 |
| | **Subtotal** | **175,000** |

*Alternative:* one **React Native / Flutter** codebase for both stores often costs less than two native lines but more messy debugging and testing

### 4.4 Deployment & external wiring (Railway-style)

| Block | What’s included (short) | Amount |
|-------|-------------------------|--------|
| **Host & DB** | Git deploy, Django build, PostgreSQL URL, health checks | 18,800 |
| **SSL & domain** | HTTPS, custom domain, CORS/security env | 6,700 |
| **Web build** | Static front + `VITE_API_URL` | 4,500 |
| **Integrations** | Env wiring for **Stripe**, **SendGrid/SES**, **SMS** provider, keys & secrets (usage bills remain client-paid) | 14,000 |
| | **Subtotal** | **44,000** |

*Recurring hosting usage is billed by the provider.*

### 4.5 Documentation

| Block | What’s included (short) | Amount |
|-------|-------------------------|--------|
| **Repo docs** | API mapping, commands, usage, manual testing; **[`../platform/vision-and-implementation.md`](../platform/vision-and-implementation.md)**, **[`../payments/stripe-setup.md`](../payments/stripe-setup.md)** (webhooks, CLI, wallets) | 8,500 |

### 4.6 Grand total (full stack)

| Layer | Amount |
|-------|--------|
| Backend | 381,700 |
| Web | 74,500 |
| iOS + Android | 175,000 |
| Deployment & external wiring | 44,000 |
| Documentation | 8,500 |
| **Total (excl. tax)** | **683,700** |

#### Optional add-ons (quoted separately)

**UAE ID live API**, **Stripe**, **SMS/email sent models**, and **lifestyle-in-app** flows are **already in §4.1** - not listed here. Remaining optional work is **infrastructure resilience** only. Scope and price are **fixed in a change order** before work starts. *Not* the same as recurring **§4.7** or the optional **§4.8** scaling package (**22,000 AED**).

| Add-on | What it typically covers | **Indicative (AED, excl. VAT)** |
|--------|--------------------------|--------------------------------|
| **Extra DR** | Secondary region or cold-standby, backup/restore drills, RPO/RTO agreed, runbooks | **35,000** |

---

### 4.7 Monthly support & maintenance

*Separate from the one-time build in §4.6. Billed **monthly** in **AED**; first month starts after go-live.*

*Recommended for this product (full-stack rental / lifestyle SaaS in production): a single **operations & maintenance** retainer - enough hours for real incidents, deploy support, and a monthly health pass, without under-serving a multi-app system.*

| | |
|--|--|
| **Coverage** | **~18 hrs/month** - incident triage, bug fixes in **existing** agreed scope, deploy / env / DNS support, security patch coordination, monthly sanity check (logs, disk, backups) |
| **Response** | **Next business day** for production-impacting issues (UAE business hours) |
| **Monthly (AED, excl. VAT)** | **9,500** |

**Out of scope:** new features, redesigns, large refactors, or work inside third-party systems beyond configuration - **change order** or **time & materials** as agreed.

*Unused hours **expire monthly** unless roll-over is agreed in writing.*

---

### 4.8 Scaling & additional capacity

**Client responsibility (metered / subscription bills):** **Integration work** for **Stripe**, **SMS**, **email**, and **UAE ID API** is **included in §4.1**. The **money you pay providers** - hosting, **per-SMS**, **per-email**, **payment MDR**, **UAE ID / API usage fees**, egress, maps - still goes on **the client’s accounts** and is **not** part of this fixed build price.

**Vendor (optional, fixed - order when needed):** **Engineering** to **design and implement** scaling - **caching**, **queues**, **background workers**, **DB tuning**, **read-replica strategy** (as applicable to your stack).

| | |
|--|--|
| **Deliverable** | Technical design + implementation pass for the above; handover notes for ops |
| **One-time fee (AED, excl. VAT)** | **22,000** |
| **When billed** | On **order** (separate from §4.6 milestones); not included in §4.7 |

*Third-party hosting/DB **usage** stays **client-paid** (see above). This fee is **vendor labour** only.*

---

## 5. Totals & tax note

| | Amount |
|--|--------|
| **Grand total (excl. tax)** - one-time build (§4.6) | **683,700** |
| **Monthly support** (recommended - §4.7) | **9,500 AED** / month |
| **Third-party usage** (hosting, per-SMS/email, MDR, API metered fees) | **Client** - see §4.8 |
| **Scaling engineering** (optional, one-time - §4.8) | **22,000 AED** |
| **Optional add-on** (extra DR - if ordered) | **35,000 AED** - see §4.6 |

*Taxes / withholding: **not included** - apply per your jurisdiction (VAT may apply in UAE if applicable).*

---

## 6. Payment schedule (40% / 30% / 30%)

Applies to the **one-time build** total (§4.6) only. **Monthly support** (§4.7) is billed monthly if subscribed. The **optional scaling engineering** package (§4.8, **22,000 AED**) is invoiced **when ordered**. **40%** due at contract / kickoff.

| # | Milestone | % | Amount |
|---|-----------|---|--------|
| 1 | **Signed & kickoff** | **40%** | **273,480** |
| 2 | `[Mid project - API + web UAT]` | 30% | **205,110** |
| 3 | `[Final - mobile + deploy + docs accepted]` | 30% | **205,110** |
| | **Total** | **100%** | **683,700** |

### 6.1 How to pay

- **Method:** `[Bank transfer / Wise / card / platform]`  
- **Currency:** As per §1  
- **Invoices:** Per installment or combined - as agreed  
- **Ongoing:** Support (§4.7) and scaling (§4.8) - separate invoices per agreed cadence (e.g. monthly).  
- **Due:** First payment before or on kickoff; others within **`[X]` days** of invoice  
- **Late payment:** `[Optional]`

---

## 7. Assumptions & exclusions

- **Domain & DNS:** Client provides registrar access or delegates DNS for SSL/custom domain.  
- **API keys:** Email, SMS, payment keys are **client-owned**; vendor configures env.  
- **Store accounts:** Apple Developer & Google Play fees usually **client**.  
- **Provider usage:** Hosting, SMS, email, payment **MDR**, API usage, storage - **client’s account and responsibility** (see §4.8).  
- **Stripe:** Wallets (**Apple Pay / Google Pay**) are enabled in the **Stripe Dashboard**; **`payment_method`** on stored payments comes from Checkout completion. **Bank/wire transfer** as a first-class payment method is **out of scope** for the current Checkout-based flow unless agreed as a **change order**.  
- **Listings:** **Leased** (fully signed) units are **hidden from anonymous discovery**; data retained for dashboards and parties with a relationship.  
- **Change orders:** Anything outside §4 is quoted separately. **§4.7** (support) and **§4.8** (scaling work) - confirm in writing when subscribed.

---

## 8. Acceptance

1. `[Staging URL]` - smoke tests per `MANUAL_TESTING.md` / `USAGE_GUIDE.md`  
2. Client sign-off within `[X]` business days of delivery notice  

---

## 9. Signatures

**Vendor** - Name: _________________ Date: _________  

**Client** - Name: _________________ Date: _________  

---

## Appendix A - Backend API prefix index

| Prefix | App |
|--------|-----|
| `/api/auth/` | accounts |
| `/api/verification/` | accounts |
| `/api/areas/`, `/api/universities/` | core |
| `/api/listings/`, `/api/favorites/` | listings |
| `/api/viewings/`, `/api/reservations/` | bookings |
| `/api/reviews/` | reviews |
| `/api/payments/` | payments |
| `/api/esign/` | esign (lease signing sessions, sign by token) |
| `/api/conversations/` … | messaging |
| `/api/lifestyle-plans/`, `/api/lifestyle-subscriptions/` | lifestyle_services |
| `/api/notifications/` | notifications |
| `/api/analytics/` | analytics |
| `/api/reports/` | reports |
| `/api/roommates/` | roommates |
| `/api/documents/` | documents |
| `/api/sms/` | sms (e.g. Twilio status webhook) |
| `/api/emails/` | emails (e.g. SendGrid event webhook) |

## Appendix B - React app routes (`yallastay`)

**Project path:** `C:\Users\USER\Desktop\yallastay`

| Route | Page component |
|-------|------------------|
| `/` | Home |
| `/search` | Search |
| `/property/:id` | Property |
| `/login` | Login |
| `/signup` | Signup |
| `/verify` | Verify |
| `/profile` | Profile |
| `/user/:id` | UserProfile |
| `/dashboard` | Dashboard |
| `/realtor-dashboard` | RealtorDashboard |
| `/services` | Services |
| `/add-property` | AddProperty |
| `/edit-property/:id` | EditProperty |
| `/payment/success` | PaymentSuccess |
| `/payment/cancel` | PaymentCancel |
| `/sign/lease/:token` | SignLease |
| `/messages` | Messages |
| `/notifications` | Notifications |
| `/roommates` | Roommates |
| `/documents` | Documents |
| `/for-partners` | ForPartners |
| `/backend` | BackendConfig |

---

*End of document*
