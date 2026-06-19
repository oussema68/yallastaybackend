# Yallastay - Detailed bill & delivery breakdown

| | |
|---|---|
| **Distribution** | **Confidential - commercial / technical scope.** NDA or executed engagement only. |

**Companion to:** [`bill-template.md`](./bill-template.md) - the **contract** uses **§4** (scope: **§4.1** backend through **§4.5** docs, **§4.6** grand total + optional add-ons, **§4.7** support, **§4.8** scaling), then **§5-§6** totals & payment, **§7-§9** assumptions / acceptance / signatures, and **Appendices A-B** (API prefixes + web routes). This file is the **technical** breakdown (models, endpoints, pages).

This document describes **models, behaviour, endpoints, and screens** for the full product (backend, web, mobile). Use it for **scope clarity**, **change orders**, and **client handover**. Status labels below are **technical** (what exists in repo vs gaps), not billing phases.

---

## Structure mirror (`BILL_TEMPLATE` §4)

| `BILL_TEMPLATE` | This document |
|-----------------|---------------|
| **§4.1** Backend API (subtotal **381,700**) | **Part A** (+ A.15a/b + **esign** + **cross-cutting** rows in template) |
| **§4.2** Web app React (subtotal **74,500**) | **Part B** |
| **§4.3** Mobile iOS + Android (subtotal **175,000**) | **Part E** |
| **§4.4** Deployment & wiring (subtotal **44,000**) | **Part D** |
| **§4.5** Documentation (**8,500**) | **Part C** |
| **§4.6** Grand total **683,700** + optional **Extra DR 35,000** | **Summary totals** + Ongoing table |
| **§4.7** Monthly support **9,500** / mo | **Ongoing** |
| **§4.8** Client metered spend + optional scaling **22,000** | A.6, A.15a/b, A.1b notes; Ongoing |

---

## How to read this doc

| Column / term | Meaning |
|---------------|---------|
| **In repo** | Implemented as described (or noted if partial) |
| **Partial** | Works but missing polish, extra fields, or integration (noted inline) |
| **Planned / gap** | Mobile or feature not yet in repo - still in overall scope where noted |

**Repos:** Backend `yallastay_backend/yallastay/` · Web `C:\Users\USER\Desktop\yallastay\`

---

## Product rules (aligned with `BILL_TEMPLATE` §3)

| Rule | Implication |
|------|-------------|
| **Lifestyle in-app** | **Lifestyle services** are **managed end-to-end in the app** (plans, subscriptions, flows) - same wording as §3. |
| **UAE ID + Stripe in core quote** | Most journeys are **gated on UAE ID verification**; **live UAE ID API** integration and **Stripe** checkout are **included** in the priced build - **not** optional add-ons (see §4.6 optional table: only **Extra DR** remains optional). |
| **Metered spend (`BILL_TEMPLATE` §4.8)** | **Integration work** for Stripe, SMS, email, UAE ID API is in **§4.1**; **money paid to providers** (hosting, per-SMS, per-email, MDR, API usage, egress, maps) stays on **the client’s accounts** - see §4.8 in the template. |

### Access matrix (students & workers - from product rules)

| Action | Without UAE ID | UAE ID verified |
|--------|----------------|-----------------|
| Browse listings, search | Yes | Yes |
| Favorites / interested list | Yes | Yes |
| Request viewing | No | Yes |
| Messaging landlord/realtor | No | Yes |
| Reservations / rent flow | No | Yes |
| Roommates (search / match) | No | Yes |

*Landlords/realtors follow separate verification flows (UAE ID + brokerage/RERA where applicable).*

---

# Part A - Backend (Django REST API)

## A.1 `accounts` - **Auth & verification** (`BILL_TEMPLATE` **32,000**)

**Purpose:** Identity, roles, and KYC-style verification for the UAE market - **without** the live external ID API layer (that is **A.1b**).

### Models - what each stores

| Model | Purpose |
|-------|---------|
| **User** | Email-as-username, password hash, Django auth flags; extends `AbstractUser`. |
| **UserProfile** | Role (student / worker / landlord / realtor), phone, bio, optional `work_area` for workers. |
| **LandlordProfile** | Extra fields for landlords listing properties. |
| **RealtorProfile** | Agency / license metadata; approval flag for posting listings. |
| **UAEIDVerification** | Emirates ID submission (hash + optional document); admin approval workflow. |
| **UniversityVerification** | Student email + university FK + student ID; domain checks vs `University`. |

### Views & behaviour - what each does

| View | HTTP | What it does |
|------|------|--------------|
| **RegisterView** | POST `/api/auth/register/` | Creates user + profile by role; returns JWT access + refresh + user payload. |
| **LoginView** | POST `/api/auth/login/` | JWT pair; serializer adds `token` alias for frontend compatibility. |
| **LogoutView** | POST `/api/auth/logout/` | Blacklists refresh token (Simple JWT blacklist). |
| **MeView** | GET/PUT/PATCH `/api/auth/me/` | Current user + profile; PATCH updates name/phone/bio/work area. |
| **UAEIDVerificationView** | POST `/api/verification/uae-id/` | Multipart: Emirates ID + optional file; pending until admin approves. |
| **UniversityVerificationView** | POST `/api/verification/university/` | Validates email domain vs university; stores pending verification. |
| **VerificationStatusView** | GET `/api/verification/status/` | Returns flags for UAE + university verification state. |

**Also:** `POST /api/auth/refresh/` (Simple JWT) for token refresh.

### Permission hooks (typical)

- Viewsets across **bookings**, **messaging**, **reviews**, **roommates** use **`IsUAEIDVerified`** (or equivalent) where product rules require a verified user.
- **403** with a clear message when a gated action is attempted without verification.

---

## A.1b UAE ID (live API) & gated access - **45,000** (`BILL_TEMPLATE` **§4.1** row)

**Purpose:** Move from **manual/admin** UAE ID checks to **programmatic** verification where the official or licensed **UAE identity API** supports it - so **gating** (lifestyle checkout, booking, chat, roommates) is enforceable **without** relying on slow manual review for every user.

### What this scope includes (engineering)

| Area | Detail |
|------|--------|
| **Integration** | Provider-agnostic **service layer**: client id/secret in env, token exchange if required, **callback** or **polling** flow per provider docs. |
| **State machine** | Map `UAEIDVerification` (or successor fields) to **verified / failed / retry**; **sync** with `VerificationStatusView` payload so web/mobile can branch UI. |
| **Gating** | Central helper or permission: **“is identity verified for product actions?”** - reused by **lifestyle subscription**, **payments initiate**, **viewings**, **messages**, **roommates**. |
| **Audit** | Minimal **audit** fields (who verified, when, correlation id from provider) for support and compliance. |
| **Failure handling** | User-visible errors, **rate limits**, **idempotent** retries where the API allows. |

### What stays outside this line item

| Item | Owner |
|------|--------|
| **Provider fees** per API call | **Client** |
| **Legal / DPA** with identity vendor | **Client** |
| **Manual fallback** (admin queue) | Can remain for edge cases; priced under ops, not duplicate API work. |

### Gaps (repo vs contract)

- **In repo:** `UAEIDVerification` + admin approval; **no** live gov API in code yet - this line item is the **implementation budget** for that layer.
- **Web:** align **Verify** tab with **university_id** + optional **student_id** where backend expects them.

---

## A.2 `core` - **7,200 AED**

**Purpose:** Reference data for Dubai areas and universities (filters, verification).

| Model | Purpose |
|-------|---------|
| **Area** | Name + slug (e.g. Dubai Marina) - used in listings and search. |
| **University** | Name + email domain for student verification. |

### Endpoints - what each does

| Pattern | What it does |
|---------|--------------|
| `GET /api/areas/` | List areas (read-only). |
| `GET /api/areas/<id>/` | Area detail. |
| `GET /api/universities/` | List universities. |
| `GET /api/universities/<id>/` | University detail. |

**Delivered:** Seeded via `seed_core` management command.

---

## A.3 `listings` - **32,000 AED**

**Purpose:** Property catalogue, images, and renter “interested list” (favorites).

### Models

| Model | Purpose |
|-------|---------|
| **Listing** | Title, description, price, type (room/studio/apartment), bedrooms/bathrooms, area FK, `listed_by`, status (active/paused/closed). |
| **ListingImage** | Ordered images per listing. |
| **Favorite** | User ↔ listing saved list. |

### Views & rules

| Component | What it does |
|-----------|--------------|
| **ListingViewSet** | List/detail with **filters** (area_slug, price, type, search, ordering); **public read**; create/update/delete for landlord/realtor; `?mine=1` for own listings. |
| **FavoriteViewSet** | Authenticated: list/add/remove favorites. |

**Permissions:** Browse without login; write operations require correct role + ownership rules.

---

## A.4 `bookings` - **16,800 AED**

**Purpose:** Viewing requests and reservations (rental pipeline).

| Model | Purpose |
|-------|---------|
| **ViewingRequest** | Tenant requests a slot; linked listing; status workflow. |
| **Reservation** | Booking / reservation record linked to listing and parties. |

### Endpoints

| Path | What it does |
|------|--------------|
| `GET/POST /api/viewings/` | List/create viewing requests (**UAE ID verified** for create where enforced). |
| `GET/PATCH /api/viewings/<id>/` | Detail + update status (landlord/realtor side). |
| `GET/POST /api/reservations/` | List/create reservations. |
| `GET/PATCH/DELETE /api/reservations/<id>/` | Detail and updates. |

---

## A.5 `reviews` - **13,500 AED**

| Model | Purpose |
|-------|---------|
| **Review** | Rating + comment; reviewer, reviewee, optional listing. |
| **ReviewResponse** | Owner/reviewee reply to a review. |

### Endpoints

| Path | What it does |
|------|--------------|
| `GET/POST /api/reviews/` | List (filters) / create (**UAE ID** required for create). |
| `GET/PATCH/DELETE /api/reviews/<id>/` | Detail + mutate. |
| `POST /api/reviews/<id>/response/` | Add response to review. |

---

## A.6 `payments` - **Payments & Stripe** - **38,000** (`BILL_TEMPLATE` **§4.1**)

| Model | Purpose |
|-------|---------|
| **Payment** | Records payment intent / status (gateway integration point). |
| **RentSchedule** | Scheduled rent instalments. |
| **Deposit** | Deposit tracking. |

### Endpoints

| Path | What it does |
|------|--------------|
| `GET /api/payments/` | User’s payments. |
| `POST /api/payments/initiate/` | Start payment (provider-specific). |
| `POST /api/payments/webhook/` | **AllowAny** - gateway callbacks. |

### Stripe scope (what “38,000” covers)

| Topic | Detail |
|-------|--------|
| **Checkout** | **Stripe Checkout** or **Payment Element** session creation from **initiate**; line items for rent, deposit, **lifestyle** charges as separate `Payment` types. |
| **Success / cancel URLs** | Web + deep links for mobile (return to app via universal link / intent). |
| **Webhooks** | **Signed** webhook handler (Stripe signing secret in env): `payment_intent.succeeded`, `payment_intent.failed`, `charge.refunded` - **idempotent** updates to `Payment` rows. |
| **Metadata** | `user_id`, `reservation_id` / `subscription_id` in Stripe metadata for reconciliation. |
| **Secrets** | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, publishable key for frontends - **never** in repo. |

**Repo status:** `payments/views.py` may still contain **stub** responses - the priced work is **replacing stubs** with real Stripe calls and **hardening** webhooks.

**PayTabs** (or other UAE acquirer) can be substituted **if agreed in writing**; same budget assumes **one** primary gateway unless you change order.

---

## A.7 `messaging` - **24,500 AED**

| Model | Purpose |
|-------|---------|
| **Conversation** | Tied to listing; participants (M2M users). |
| **Message** | Sender, content, timestamps; read state. |

### Endpoints

| Path | What it does |
|------|--------------|
| `GET/POST /api/conversations/` | List / start conversation by listing. |
| `GET /api/conversations/<id>/` | Conversation detail. |
| `GET/POST .../messages/` | List/send messages (**UAE ID** for messaging where enforced). |
| `POST .../messages/<msg_id>/read/` | Mark message read. |
| `POST .../mark-read/` | Mark whole thread read. |

---

## A.8 `lifestyle_services` - **Lifestyle** (in-app) - **15,200 AED** (`BILL_TEMPLATE` **§4.1**)

| Model | Purpose |
|-------|---------|
| **LifestylePlan** | Tier (Essential / Comfort / Complete), price. |
| **LifestyleService** | Line items under a plan (cleaning, internet, etc.). |
| **LifestyleSubscription** | User subscription to a plan (often tied to reservation). |

### Endpoints

| Path | What it does |
|------|--------------|
| `GET /api/lifestyle-plans/` | List plans + nested services. |
| `GET/POST /api/lifestyle-subscriptions/` | List/create subscription. |
| `GET/PATCH /api/lifestyle-subscriptions/<id>/` | Detail/update. |

### In-app lifecycle (product requirement)

| Step | Behaviour |
|------|-----------|
| **Discovery** | Authenticated user browses **plans** (`GET /api/lifestyle-plans/`); UI shows **Essential / Comfort / Complete** with bundled services (see `ARCHITECTURE.md` tier copy). |
| **Subscribe** | **POST** subscription ties to **user** and often **`Reservation`** (move-in flow); **status** field drives active/paused/cancelled. |
| **Pay** | **Lifestyle** charges are billed via **`payments`** (Stripe) with `Payment` type distinguishing rent vs lifestyle vs deposit. |
| **Gate** | **UAE ID verified** users only for **subscription** and **payment** paths that match product rules (align with `IsUAEIDVerified` on booking/messaging). |

**Admin:** Seed `LifestylePlan` + `LifestyleService` rows; adjust prices without code deploy when possible.

---

## A.9 `notifications` - **12,600 AED**

| Model | Purpose |
|-------|---------|
| **Notification** | In-app notification (title, body, read flag, type). |
| **NotificationPreference** | Per-channel or per-type toggles. |

### Endpoints

| Path | What it does |
|------|--------------|
| `GET /api/notifications/` | List for current user. |
| `PATCH /api/notifications/<id>/read/` | Mark read. |
| `GET/PATCH /api/notifications/preferences/` | Get/update preferences. |

### Relation to `notifications` vs **A.15a / A.15b**

| Concern | Where it lives |
|---------|----------------|
| **In-app feed** (bell icon) | `Notification` model + list endpoints. |
| **Transactional email/SMS** | **A.15b** / **A.15a** - logged sends; may **also** create a `Notification` row for parity. |

**Push (FCM/APNs)** - not in scope until mobile contracts add it (see Part D).

---

## A.10 `analytics` - **15,800 AED**

**Purpose:** Aggregated insights for **realtors** (and similar roles) - no PII export in aggregates.

| Endpoint | What it does |
|----------|--------------|
| `GET /api/analytics/renter-demographics/` | Student vs worker splits, universities, work areas (aggregated). |
| `GET /api/analytics/popular-areas/` | Saves / viewings / bookings by area. |
| `GET /api/analytics/my-listings-insights/` | Metrics for listings owned by the realtor. |

**Permission:** Realtor (or landlord where implemented).

---

## A.11 `reports` - **9,800 AED**

| Model | Purpose |
|-------|---------|
| **Report** | User-reported listing or user; reason; status for moderation. |

### Endpoints

| Path | What it does |
|------|--------------|
| `POST /api/reports/submit/` | Create report (listing **or** user, not both). |
| `GET /api/reports/` | Own reports; staff see all. |
| `GET/PATCH /api/reports/<id>/` | Detail; staff update status/notes. |

---

## A.12 `roommates` - **18,900 AED**

**Purpose:** Student/worker roommate matching (UAE ID + role checks).

| Model | Purpose |
|-------|---------|
| **RoommateProfile** | Bio, budget, preferred areas, move-in, lifestyle text, `is_looking`. |
| **RoommateInterest** | Interest between users; pending/accepted/declined. |

### Endpoints

| Path | What it does |
|------|--------------|
| `GET/POST/PATCH /api/roommates/profile/` | CRUD own profile. |
| `GET /api/roommates/search/` | Filter by area slug, budget (excludes self). |
| `POST /api/roommates/interest/` | Express interest. |
| `GET /api/roommates/interests/` | Sent + received lists. |
| `PATCH /api/roommates/interests/<id>/` | Accept/decline. |

---

## A.13 `documents` - **13,400 AED**

| Model | Purpose |
|-------|---------|
| **Document** | User file uploads with type (UAE ID, lease, etc.); optional generic FK. |

### Endpoints

| Path | What it does |
|------|--------------|
| `GET/POST /api/documents/` | List / multipart upload. |
| `GET /api/documents/<id>/` | Retrieve metadata (file URL). |

---

## A.14 Project shell - **22,000 AED**

| Item | What was done |
|------|----------------|
| **Settings** | `base`, `dev`, `prod`; JWT; CORS; PostgreSQL in prod via `dj_database_url`. |
| **URLs** | Single `/api/` tree; `admin/`; media in DEBUG. |
| **Migrations** | All apps migrated. |
| **Admin** | Models registered for operational use. |
| **Tests** | Unit/view tests across apps (as in repo). |
| **CORS / JWT** | Frontend dev proxy and production origins configurable. |

### Env vars (non-exhaustive - production)

| Variable | Used for |
|----------|----------|
| `DATABASE_URL` | Postgres (Railway) |
| `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` | Django core |
| `CORS_ALLOWED_ORIGINS` | Web app origin |
| `STRIPE_*` | Payments (see A.6) |
| `TWILIO_*` / SMS provider | A.15a |
| `SENDGRID_*` / `AWS_SES_*` | A.15b |

---

## A.15a SMS sent - **12,000** (`BILL_TEMPLATE` §4.1) - Django app **`sms`**

**Purpose:** Every **outbound SMS** (OTP, alerts, booking reminders) should be **observable** in the database - not “fire and forget” only.

**Repo:** App **`sms`** - model **`SmsMessage`**, **`sms.services.send_sms()`**, webhook **`POST /api/sms/webhooks/twilio/status/`** (see `ARCHITECTURE.md`, `MANUAL_TESTING.md` §9a).

### Intended implementation (scope)

| Piece | Behaviour |
|-------|-----------|
| **Model(s)** | **`SmsMessage`**: `to_number`, `body`, `template_key`, `provider_message_id`, `status`, `error_message`, `retry_count`, optional `user` FK. |
| **Service** | **`send_sms()`** - Twilio when env set; else **skipped** row; `pip install twilio` for real sends. |
| **Webhooks** | Twilio status POST; **`TWILIO_WEBHOOK_INSECURE_OK`** for local dev only. |
| **Admin** | List/filter by status. |
| **Idempotency** | Avoid duplicate provider sends in higher layers (tasks). |

**Provider usage:** **client-paid**; this fee is **models + plumbing + admin**.

---

## A.15b Email sent - **12,000** (`BILL_TEMPLATE` §4.1) - Django app **`emails`**

**Purpose:** Transactional email (verification, receipts, password reset) with **delivery tracking** and **template** discipline.

**Repo:** App **`emails`** - model **`EmailMessage`**, **`emails.services.send_transactional_email()`**, webhook **`POST /api/emails/webhooks/sendgrid/events/`**.

### Intended implementation (scope)

| Piece | Behaviour |
|-------|-----------|
| **Model(s)** | **`EmailMessage`**: `to_email`, `subject`, `body_text` / `body_html`, `template_key`, `provider_message_id`, `status`, etc. |
| **Queue** | **Celery** optional; sync send via Django **email** backend today. |
| **Templates** | Django templates or ESP template ids; **i18n** hook if needed later. |
| **Bounces** | SendGrid-style **events** webhook; optional **`X-Webhook-Secret`** + **`SENDGRID_WEBHOOK_SECRET`**. |

**Provider usage:** **client-paid**; this fee is **models + queue + admin + templates**.

---

# Part B - React web (`yallastay`) - **74,500 AED** total (`BILL_TEMPLATE` **§4.2**)

**Stack:** Vite, React 18, React Router 6, Tailwind, Framer Motion, Axios.

### §4.2 line mapping (amounts must sum to **74,500**)

| `BILL_TEMPLATE` §4.2 block | Amount | This doc |
|----------------------------|--------|------------|
| Shell | 6,500 | B.1 |
| API client | 10,000 | B.2 |
| UI | 7,500 | B.3 |
| Auth & verify | 8,500 | B.4 (Auth & verify) |
| Discovery | 12,500 | B.4 (Listings & discovery) |
| Dashboards | 10,000 | B.4 (Dashboards) |
| Engagement | 12,500 | B.4 (Engagement) |
| Other | 7,000 | B.4 (Misc) |

## B.1 Shell & tooling - **6,500 AED**

| File / area | What was done |
|-------------|----------------|
| `main.jsx` | React root, `BrowserRouter`. |
| `App.jsx` | All feature routes nested under `Layout` (home, auth, property, dashboards, payments, lease sign, etc.). |
| `vite.config.js` | Dev server; **proxy `/api` → backend** (e.g. port 8000). |
| Tailwind / PostCSS | Global styling, `btn`, `card`, theme colours. |

## B.2 API client - **10,000 AED**

| Module | What it does |
|--------|--------------|
| `api` instance | Base URL `VITE_API_URL` or `/api`; JSON default. |
| Interceptors | Attach `Bearer` from `localStorage`; on **401** clear token + redirect `/login`. |
| Named exports | `auth`, `verification`, `core`, `listings`, `favorites`, `bookings`, `reviews`, `lifestyle`, `messaging`, `notifications`, `reports`, `roommates`, `documents`, `analytics`, **`payments`**, **`esign`** - mirror backend routes. |
| `publicApiUrl` | Absolute URL for **unauthenticated** e-sign preview (`GET /api/esign/sign/<token>/`). |

## B.3 Layout & shared UI - **7,500 AED**

| Component | What was done |
|-----------|----------------|
| **Layout.jsx** | Outlet + Framer Motion page transitions. |
| **Header.jsx** | Nav links (Find Homes, Services, Roommates, List Property, Backend); auth-aware (Dashboard, Verify, Logout, realtor link). |
| **Footer.jsx** | Site footer. |
| **PropertyCard.jsx** | Listing card: image, title, area, price, beds/baths. |

## B.4 Pages - **by group**

### Auth & verify - **8,500 AED**

| Page | What was done |
|------|----------------|
| **Login** | Email/password → token stored → redirect. |
| **Signup** | Register with role; redirects for login. |
| **Verify** | Tabs: UAE ID (multipart), university email; **partial** vs backend if `university_id` missing. |

**UX alignment with contract**

- When **live UAE ID API** lands (A.1b), **Verify** should show **provider-driven** steps (redirect or iframe) **without** duplicating manual upload where the API replaces it - **copy** and **error states** must match **VerificationStatusView**.
- **Gated** routes (e.g. **Messages**, **Roommates**, **viewing** on Property) should redirect to **Verify** or show **modal** when `verification.status` shows UAE ID not verified.

### Listings & discovery - **12,500 AED**

| Page | What was done |
|------|----------------|
| **Home** | Featured/search entry; areas from API where implemented. |
| **Search** | Listings list; filters `area_slug`, type; uses `PropertyCard`. |
| **Property** | Detail; **favorite**, **request viewing**, **message landlord**, **report listing** modals; uses `first_image`, area name, beds/baths. |
| **AddProperty** | Create listing; **area** from API; landlord/realtor. |

### Dashboards - **10,000 AED**

| Page | What was done |
|------|----------------|
| **Dashboard** | Me + favorites + viewings + reservations + links to Messages, Notifications, Documents, Roommates (role). |
| **RealtorDashboard** | Own listings + **analytics** (`myListingsInsights` / similar). |

### Engagement - **12,500 AED**

| Page | What was done |
|------|----------------|
| **Messages** | Conversation list + thread + send. |
| **Notifications** | List + mark read. |
| **Roommates** | Profile CRUD, search, express interest, accept/decline (student/worker). |
| **Documents** | List user documents + link to Verify. |

### Misc - **7,000 AED**

| Page / component | What was done |
|------------------|----------------|
| **Services** | Lifestyle plans from API + fallback cards. |
| **ForPartners** | Marketing; **list property** CTA routes logged-in realtors to **`/add-property`**. |
| **BackendConfig** | API health / connectivity check; distinct keys per method/path. |
| **PaymentSuccess** / **PaymentCancel** | Stripe return URLs. |
| **SignLease** | Magic-link lease signing UI; uses `esign.previewSign` + public fetch. |
| **LeaseContractsSection** / **RentalReservationsSection** | Dashboard / realtor lease & reservation UI. |
| **StubPaymentModal** / `paymentCheckout` | Stub vs Stripe initiate flow. |
| **Vitest** | Unit tests (e.g. `SignLease` route). |

**Services** - must stay **in-app** for the contract: user sees **tiers**, **nested services**, path to **subscribe** (after UAE ID), and **payment** handoff when Stripe is wired (see A.6 + A.8).

---

# Part C - Documentation - **8,500 AED** (`BILL_TEMPLATE` **§4.5**)

Matches template line **“Repo docs”**: API mapping, commands, usage, manual testing.

| Asset | What it contains |
|-------|------------------|
| **FRONTEND_BACKEND_MAPPING.md** | API client ↔ pages; gaps; methodology checklist. |
| **backend_documentation.md** / **frontend_documentation.md** | Overview, routes, env. |
| **USAGE_GUIDE.md** | Run backend + frontend, verification steps. |
| **COMMANDS.md** | migrate, seed, test commands. |
| **MANUAL_TESTING.md** | API manual test matrix. |
| **ARCHITECTURE.md** | Product and technical architecture. |

---

# Part D - Deployment & external wiring - **44,000** (`BILL_TEMPLATE` **§4.4**)

**Stack:** Railway (or equivalent), **Git** deploy, **PostgreSQL** plugin, **HTTPS** custom domain.

| `BILL_TEMPLATE` §4.4 block | Amount | What it covers (engineering) |
|----------------------------|--------|------------------------------|
| **Host & DB** | **18,800** | Connect repo to Railway; **build** Django (Procfile / `nixpacks` / Dockerfile); **DATABASE_URL**; health check; **release** for migrations. |
| **SSL & domain** | **6,700** | TLS cert, **CORS** + `ALLOWED_HOSTS`; **HSTS** optional. |
| **Web build** | **4,500** | Vite/React **static** deploy; **`VITE_API_URL`** → prod API; asset caching. |
| **Integrations** | **14,000** | Env wiring for **Stripe**, **SendGrid/SES**, **SMS** provider, secrets (usage bills **client-paid** per §4.8). Webhooks registered in Stripe dashboard (public HTTPS). **S3** or compatible for media if used. |
| **Subtotal** | **44,000** | Matches `BILL_TEMPLATE` §4.4 |

*Template note:* recurring hosting usage is billed by the provider.

**Client responsibility:** Railway **invoice**, domain **registrar**, **Stripe/SMS/email** provider **bills** - vendor configures **env**, not your credit card unless agreed.

---

# Part E - iOS & Android - **175,000** (`BILL_TEMPLATE` **§4.3**)

| `BILL_TEMPLATE` §4.3 block | Amount | Notes |
|----------------------------|--------|--------|
| **iOS** | **88,500** | App shell, networking, auth, listings, dashboards, engagement, App Store release |
| **Android** | **86,500** | Same scope on Android stack + Play release |
| | **175,000** | |

*Template footnote:* one **React Native / Flutter** codebase for both stores can cost less than two native tracks but mixes debugging/testing trade-offs.

For each **workstream**, **planned** work means:

| Stream | Would deliver |
|--------|----------------|
| **Shell** | Single app per platform; **dev/staging/prod** API base URLs; navigation graph matching web IA. |
| **Networking** | JWT secure storage (Keychain / EncryptedSharedPreferences), refresh, **401** → login, **multipart** for UAE ID + uploads. |
| **Auth & verify** | Parity with Login/Signup/Verify; **UAE ID** flow must support **live API** (A.1b) + deep links back from Stripe. |
| **Listings** | Home, search, PDP, favorites, viewing, chat entry, report. |
| **Dashboards** | Renter + realtor + analytics. |
| **Engagement** | Messages, notifications, roommates, documents. |
| **Services / lifestyle** | **In-app** plan browsing + subscription + payment entry points (same as web product rules). |
| **Store** | TestFlight / Play internal testing → production listing; **screenshots**, **privacy**, **UAE**-appropriate copy. |

**Not included until contracted:** push notifications (FCM/APNs), offline-first, app-specific analytics SDKs.

---

## Summary totals (aligned with BILL_TEMPLATE)

| Scope | Amount (same unit as template) |
|-------|--------------------------------|
| Backend | 381,700 |
| React web | 74,500 |
| iOS + Android | 175,000 |
| Deployment & external wiring | 44,000 |
| Documentation | 8,500 |
| **Grand total** | **683,700** *(see `bill-template.md` §4.6)* |

### Full mapping: `BILL_TEMPLATE` §4.1 ↔ Part A (subtotal **381,700**)

Order matches the **template table** (amounts identical). **E-sign** and **cross-cutting integrations** are priced as their own §4.1 rows (see `esign` app + webhooks / public profile / team messaging).

| §4.1 row | AED | This doc |
|----------|-----|----------|
| Auth & verification | 32,000 | A.1 |
| UAE ID (live API) & gated access | 45,000 | A.1b |
| Reference data | 7,200 | A.2 `core` |
| Listings | 32,000 | A.3 |
| Bookings | 16,800 | A.4 |
| E-sign & lease contracts | 28,000 | `esign` app (see also A.4 flow) |
| Cross-cutting integrations | 14,000 | `sms`/`emails` webhooks, `accounts` public-profile & verify-email, team user + hooks |
| Reviews | 13,500 | A.5 |
| Payments & Stripe | 38,000 | A.6 |
| Messaging | 24,500 | A.7 |
| Lifestyle | 15,200 | A.8 |
| Notifications | 12,600 | A.9 |
| Analytics | 15,800 | A.10 |
| Reports | 9,800 | A.11 |
| Roommates | 18,900 | A.12 |
| Documents | 13,400 | A.13 |
| SMS sent | 12,000 | A.15a |
| Email sent | 12,000 | A.15b |
| Project | 22,000 | A.14 |

*Note:* In Part A, **A.14** and **A.15a/b** appear **after** A.13 in this file; the **billing rows** match §4.1 including **E-sign** and **cross-cutting** as separate line items.

### `BILL_TEMPLATE` §5-§6 (commercial cross-check)

| Topic | Value |
|-------|--------|
| **§5** One-time build | **683,700** |
| **§5** Monthly support (§4.7) | **9,500** / month |
| **§5** Third-party usage | **Client** - §4.8 |
| **§5** Scaling engineering (optional) | **22,000** |
| **§5** Optional Extra DR | **35,000** - §4.6 optional table |
| **§6** Payment schedule (build only) | **40% / 30% / 30%** → **273,480** / **205,110** / **205,110** |

Full legal wording stays in **`bill-template.md`** (assumptions §7, acceptance §8, signatures §9).

### API & routes index

Backend URL prefixes are listed in **`BILL_TEMPLATE` Appendix A**; React routes in **Appendix B** (same paths as Part B).

### Ongoing (not in 683,700)

| Item | Where in template |
|------|-------------------|
| Monthly support **9,500 AED** | §4.7 |
| Scaling engineering **22,000 AED** (optional) | §4.8 |
| Extra DR **35,000 AED** (optional) | §4.6 optional table - **only** optional line; UAE ID, Stripe, SMS/email models, lifestyle are **in §4.1** |

---

*End of detailed bill*
