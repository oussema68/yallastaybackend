# Yallastay  -  Django Architecture

Yallastay is an apartment-finding platform **for students and new arrival workers** in Dubai. Students and workers browse and rent; landlords and **realtors** list properties. Verification via university account and UAE ID.

---

## Realtors  -  Posting Houses

Realtors (real estate agents/brokers) are a separate role that connects to the platform to list properties.

### Realtor Flow

1. **Sign up**  -  Realtor registers with email, phone, agency details.
2. **Verification**  -  Submit UAE ID + brokerage license / RERA registration (Dubai).
3. **Approval**  -  Admin approves verified realtors.
4. **Post listings**  -  Realtor creates listings; can post on behalf of property owner.
5. **Manage**  -  View, edit, pause listings; respond to viewings and messages.

### Realtor vs Landlord

| | Landlord | Realtor |
|--|----------|---------|
| Lists | Own properties | Any properties (own or client's) |
| Verification | UAE ID (+ optional docs) | UAE ID + brokerage/RERA license |
| Profile | LandlordProfile | RealtorProfile |
| Can represent | Self only | Multiple owners/clients |

### Listing Owner

- Each `Listing` has a **listed_by** (User)  -  the account that created it (landlord or realtor).
- Optionally add **property_owner** FK  -  when a realtor posts on behalf of a client, link to the owner’s contact info (or external reference).

### Owners Without Ejari / Papers

Owners who don't have Ejari (Dubai's tenancy contract registration) or the necessary documents (title deed, NOC, etc.) cannot list directly. They can **choose one of Yallastay's verified realtors or brokers** (RERA-licensed in UAE) to list the property on their behalf.

| Step | Description |
|------|-------------|
| 1 | Owner registers and indicates they want assisted listing (no Ejari/papers) |
| 2 | Owner browses and selects a platform realtor or broker |
| 3 | Realtor handles Ejari, documents, and listing on behalf of the owner |
| 4 | Listing appears with realtor as `listed_by`; `property_owner` links to owner |

**Later stages:** A complete in-platform system will handle this end-to-end  -  onboarding owners without papers, document collection, realtor matching, Ejari and paperwork flow, all managed through the platform.

---

## Access Levels  -  Students & Workers (Non-UAE ID vs Verified)

Access for **students and workers** depends on UAE ID verification status.

| Action | Non-UAE ID | UAE ID Verified |
|--------|------------|-----------------|
| View apartments | ✓ | ✓ |
| Add to interested list | ✓ | ✓ |
| Check roommates | ✗ | ✓ |
| Rent / reserve apartment | ✗ | ✓ |
| Request viewing | ✗ | ✓ |
| Message landlord/realtor | ✗ | ✓ |

**Non-UAE ID students/workers** can browse listings and save them to an interested list (favorites). Full booking, roommate search, viewings, and messaging require UAE ID verification.

---

## Lifestyle Services

Students and workers can subscribe to lifestyle plans that bundle cleaning, internet, maintenance, furniture, and gym access. Available in 3 tiers:

### Essential  -  For the basics

| Service | Details |
|---------|---------|
| Cleaning | Bi-weekly (2×/month) |
| Internet | Setup coordination |
| Maintenance | 2 requests/month |

### Comfort  -  Most popular

| Service | Details |
|---------|---------|
| Cleaning | Weekly |
| Internet | Setup + support |
| Maintenance | Unlimited coordination |
| Furniture | 20% rental discount |
| Gym | Partner access |

### Complete  -  Everything included

| Service | Details |
|---------|---------|
| Cleaning | Twice weekly |
| Internet | Premium setup & support |
| Maintenance | Priority (same-day) |
| Furniture | Basic pack included |
| Gym | Premium membership |
| Support | Dedicated support |

Plans are linked to a **Reservation**; students/workers choose a tier when booking or after move-in. Billing via payments app.

---

## Outbound SMS & transactional email  -  dedicated app(s)

Today, the **`notifications`** app holds **in-app** rows only (`Notification`, `NotificationPreference`)  -  bell icon, read state, channel *preferences*. It does **not** persist **carrier** SMS or **ESP** email sends. For OTP, booking alerts, receipts, and verification mail, you need an **audit trail** (status, provider ids, errors, retries) and **inbound webhooks** from Twilio, SendGrid, SES, etc.

### Why not add SMS/email models to `notifications`?

| Concern | In-app `Notification` | Outbound SMS / email |
|--------|------------------------|----------------------|
| **Purpose** | User-visible feed in the product | Delivery to phone/inbox + compliance trail |
| **Lifecycle** | Created + read | Queued → sent → delivered/failed + **webhooks** |
| **Failure modes** | Rare | Rate limits, bounces, invalid numbers  -  ops-heavy |
| **Dependencies** | Simple CRUD | Provider SDKs, signing secrets, **idempotency** |

Mixing the two bloats **`notifications`**, blurs admin UX, and encourages circular imports when many apps (`accounts`, `bookings`, `payments`, …) need to “send” something.

**Conclusion:** It is **more viable** to introduce **separate Django apps** for outbound SMS and email, and keep **`notifications`** strictly for **in-app** messaging.

### Implemented layout  -  **`sms`** + **`emails`** (two apps)

The repo uses **two apps** for easier scaling and clearer failure domains:

| App | Models | Entry points | Webhooks |
|-----|--------|--------------|----------|
| **`sms`** | `SmsMessage` | `sms.services.send_sms()` | `POST /api/sms/webhooks/twilio/status/`  -  Twilio status callback (`TWILIO_WEBHOOK_INSECURE_OK` for local dev only; production: request signature validation). |
| **`emails`** | `EmailMessage` | `emails.services.send_transactional_email()` | `POST /api/emails/webhooks/sendgrid/events/`  -  SendGrid-style JSON events (`SENDGRID_WEBHOOK_INSECURE_OK` or `X-Webhook-Secret` + `SENDGRID_WEBHOOK_SECRET`). |

- **Admin:** Both models registered for audit.
- **Dependencies:** `pip install twilio` when sending real SMS; email uses Django’s **`EMAIL_BACKEND`** / **`DEFAULT_FROM_EMAIL`** (see `settings/base.py`).
- **Alternative:** A single **`communications`** app would merge these modules  -  tradeoff: one `INSTALLED_APPS` line vs. larger app.

### Integration pattern

1. **Other apps** call **`sms.services.send_sms`** / **`emails.services.send_transactional_email`**  -  they **do not** import Twilio or raw SMTP in scattered `views.py`.
2. **Optional:** After a successful send, create an **in-app** `Notification` row for parity (user sees bell + got SMS)  -  two records, two concerns.
3. **Billing alignment:** Priced work (see project bill) is **models + services + webhooks + admin**; **per-SMS / per-email provider fees** stay on the **client’s** accounts.

---

## Analytics for Realtors

Realtors (and optionally landlords) get aggregated insights about **students and workers**  -  demographics, study/work locations, popular areas  -  to inform listing strategy and targeting.

### What Realtors See (Aggregated Only)

| Metric | Source | Example |
|--------|--------|---------|
| Student vs worker split | `UserProfile.role`, `UniversityVerification` | e.g. 65% students, 35% workers |
| Study locations | `UniversityVerification.university` | e.g. UAEU, Zayed, Heriot-Watt |
| Work locations | `UserProfile.work_area` (FK to Area) | e.g. DIFC, Internet City, Media City |
| Popular areas | `Favorite`, `ViewingRequest`, `Reservation` | Most saved / viewed / booked areas |
| Price preferences | `Favorite` + `Listing.price` | Typical budget ranges |

**Data is aggregated and anonymized**  -  no individual student or worker names, emails, or IDs visible.

### Access Control

- **Who**: Realtors (and optionally landlords for their own listings)
- **How**: Permission class `IsRealtor` or `IsRealtorOrLandlord` on analytics endpoints
- **What**: Aggregated counts/percentages only  -  never row-level tenant data

### Example Endpoints

```
GET /api/analytics/renter-demographics/
→ { "students": 62, "workers": 38, "by_university": {...}, "by_work_area": {...} }

GET /api/analytics/popular-areas/
→ { "areas": [{"name": "Dubai Marina", "saves": 120, "viewings": 45}, ...] }

GET /api/analytics/my-listings-insights/
→ Realtor's own listings: views, saves, viewing requests by area/renter type
```

### Privacy

- Aggregate only; avoid data that can identify individuals
- Align with UAE data protection and platform privacy policy
- Consider opt-out for users who decline analytics use

---

## Incremental Build Guide

Start small and add features in phases. Each phase should be working end-to-end before moving on.

### Phase 0  -  Project Setup

1. Create a virtual environment and install Django.
2. Create the Django project (e.g. `yallastay`).
3. Configure `settings.py` (database, `INSTALLED_APPS`, timezone, etc.).
4. Create a `.env` file for secrets (DB, keys) and use `python-decouple` or `django-environ`.
5. Add a basic `urls.py` and confirm the dev server runs.

---

### Phase 1  -  Core + Accounts + Listings (MVP)

**Goal:** Students and workers can browse; landlords/realtors can list. Auth for all roles.

1. **`core` app**
   - Create the app.
   - Add `Area` model (Dubai areas for filters).
   - Add `University` model (name, domain)  -  seed with common UAE universities.
   - Register in `INSTALLED_APPS`.

2. **`accounts` app**
   - Create the app.
   - Create custom `User` model (extend `AbstractUser`, use email as `USERNAME_FIELD`).
   - Add `UserProfile` (phone, role: student/worker/landlord/**realtor**, FK to `User`).
   - Add `LandlordProfile` and `RealtorProfile` (agency name, license number)  -  create on registration based on role.
   - Set `AUTH_USER_MODEL` in settings.
   - Add basic auth endpoints (register, login, logout)  -  separate flows for student/worker vs landlord vs realtor. Landlords indicate if they need assisted listing (no Ejari/papers).
   - Skip verification for now; add it in Phase 2.

3. **`listings` app**
   - Create the app.
   - Add `Listing` model (title, description, price, bedrooms, bathrooms, area, type, status, **listed_by** FK  -  landlord or realtor; optional **property_owner** for realtor-posted client properties).
   - Add `ListingImage` (image, order, listing FK).
   - Add `Location` (area FK, address, building) or embed key fields in `Listing` for simplicity.
   - Add CRUD endpoints for listings (create/edit: landlord/realtor only; list/detail: **all users including non-verified**).
   - Add simple list/detail views with basic filters (price, area, bedrooms).
   - Add `Favorite` / interested list early so non-UAE ID users can save listings.

**Deliverable:** Students and workers browse and add to interested list. Landlords/realtors create listings.

---

### Phase 2  -  Verification + Bookings

**Goal:** Students and workers verify identity; verified users can request viewings and make reservations.

1. **`accounts`  -  verification**
   - Add `UAEIDVerification` (user FK, hashed_id, document, status, verified_at).
   - Add `UniversityVerification` (user FK, email, university FK, status, verified_at).
   - Add verification endpoints and admin approval flow.
   - **Realtors**: Add `RealtorVerification` or extend `RealtorProfile` with brokerage_license, rera_number, license_document; admin approves before realtor can post.

2. **`bookings` app**
   - Create the app.
   - Add `ViewingRequest` (listing, student/worker, requested_datetime, status).
   - Add `Reservation` (listing, student/worker, start_date, end_date, status, deposit_amount).
   - Add endpoints: request viewing, confirm/reject, create reservation.
   - Add `LeaseAgreement` later if you need document storage.
   - **Require UAE ID verification** for all booking actions; return 403 if user not verified.

**Deliverable:** Students and workers verify → request viewing → create reservation.

---

### Phase 3  -  Reviews

**Goal:** Verified users can rate each other.

1. **`reviews` app**
   - Create the app.
   - Add `Review` (reviewer, reviewee, listing optional, rating, comment).
   - Add `ReviewResponse` for landlord replies.
   - Add endpoints: create review, list reviews for user/listing.
   - **Require UAE ID verification** to leave reviews.

**Deliverable:** Rate users (verified only). *(Favorites/interested list added in Phase 1.)*

---

### Phase 4  -  Payments + Messaging

**Goal:** Handle rent/deposits and in-app communication.

1. **`payments` app**
   - Create the app.
   - Add `Payment` (user, amount, type, status, transaction_id).
   - Add `RentSchedule` and `Deposit` linked to `Reservation`.
   - Integrate a payment provider (e.g. Stripe, PayTabs).
   - Add webhooks for payment status.

2. **`messaging` app**
   - Create the app.
   - Add `Conversation` (listing, participants M2M).
   - Add `Message` (conversation, sender, content, read_at).
   - Add endpoints: list conversations, send message, mark read.
   - Optionally add WebSockets for real-time chat.
   - **Require UAE ID verification** for messaging; non-verified users cannot initiate or reply.

**Deliverable:** Students/workers pay rent; chat with landlord/realtor.

---

### Phase 5  -  Lifestyle Services + Notifications + SMS & Email apps + Polish

**Goal:** Students/workers subscribe to **in-app** lifestyle plans; **in-app** notifications fire from domain events; **SMS** and **email** are logged and sent via **`sms`** and **`emails`** apps; product hardening before analytics.

**Prerequisites (from earlier phases):** `payments` (even if stub) for lifestyle charges; `bookings` / `Reservation` if subscriptions tie to a lease.

---

1. **`lifestyle_services` app**

| Task | Detail |
|------|--------|
| Models | `LifestylePlan`, `LifestyleService` (plan FK, type, details), `LifestyleSubscription` (link `Reservation`, `User`, plan, dates, **status**). |
| Seed | Management command (or migration data) for **Essential / Comfort / Complete** tiers and line items  -  matches product copy in this doc. |
| API | List plans (+ nested services), create/update/list **subscriptions**; filters as needed. |
| Permissions | **Subscribe / pay** paths: **`IsAuthenticated`** + **`IsUAEIDVerified`** (same product rule as bookings/messaging). |
| Payments | Create or attach **`Payment`** rows with `payment_type` = lifestyle; hand off to **Stripe** (or agreed gateway) when Phase 4 checkout is real. |
| Signals | On subscription status change (e.g. active / cancelled), optionally enqueue **Notification** + transactional **email** via **`emails.services.send_transactional_email`**. |

---

2. **`notifications` app** (in-app only)

| Task | Detail |
|------|--------|
| Models | Already sketched: `Notification`, `NotificationPreference`  -  ensure **indexes** on `(user, read, created_at)` for feed performance. |
| API | List, mark read, **preferences** GET/PATCH  -  align with web/mobile clients. |
| Triggers | **Wire signals** (or explicit service calls) from **`bookings`** (viewing confirmed), **`messaging`** (new message), **`payments`** (paid/failed), **`lifestyle_services`** (subscription update). Keep payloads small (title/body + type). |
| Rules | **Do not** store SMS/email bodies here  -  see **`sms`** / **`emails`**. Optional: create an in-app row **after** a successful outbound send so the bell matches reality. |

---

3. **`sms`** and **`emails`** apps (see **Outbound SMS & transactional email**  -  **implemented** in repo)

| Task | Detail |
|------|--------|
| Package | **`sms`** and **`emails`** in **`INSTALLED_APPS`**; URLs **`/api/sms/webhooks/...`**, **`/api/emails/webhooks/...`**  -  **no JWT** on webhooks; keep provider callbacks out of authenticated API namespaces. |
| Models | **`sms.SmsMessage`**, **`emails.EmailMessage`**: recipient, template key or body, provider id, **status**, error, retry count, optional **`user`** FK, timestamps. |
| Send path | **`sms.services.send_sms`**, **`emails.services.send_transactional_email`**; wire from **`accounts`** (verification, password reset), **`bookings`** (reminders), **`payments`** (receipts)  -  **no** direct Twilio imports outside **`sms`**. |
| Async | **Celery** (or Django **background tasks**) for send + retry; configure broker in settings for prod. |
| Webhooks | Twilio **status** POST; SendGrid-style **events** JSON  -  dev flags **`TWILIO_WEBHOOK_INSECURE_OK`**, **`SENDGRID_WEBHOOK_INSECURE_OK`** (never in production). |
| Admin | Both models registered; filter by **failed** / **skipped** sends. |
| Env | `TWILIO_*`, `EMAIL_BACKEND`, **`DEFAULT_FROM_EMAIL`**, webhook secrets  -  see **`MANUAL_TESTING.md`** §9a. |

---

4. **Polish (cross-cutting)**

| Task | Detail |
|------|--------|
| Listings | Optional: **`Amenity`**, **`Availability`** if product needs richer search  -  or defer if out of scope. |
| Search | Consistent **pagination** (`page`, `page_size`) on list endpoints; align **`ListingFilter`** with frontend query params. |
| API | Harden **throttling** on auth-sensitive routes if not already; consistent **error** shape for clients. |
| Quality | Expand **tests** for new signals/webhooks; update **`MANUAL_TESTING.md`**, **`USAGE_GUIDE`**, **`FRONTEND_BACKEND_MAPPING.md`**. |
| Deploy | Env checklist for **`sms`** / **`emails`** + notification triggers on staging before prod. |

**Not in Phase 5:** **`reports`** moderation app  -  covered in **Phase 7** unless you pull it forward.

**Deliverable:** Users can subscribe to lifestyle tiers in-product with correct **gating**; **in-app** notifications fire from key events; **SMS/email** are **auditable** and **sent** through **`sms`** / **`emails`**; staging-ready polish.

---

### Phase 6  -  Analytics for Realtors

**Goal:** Realtors see aggregated student & worker demographics and popular areas.

1. **`analytics` app**
   - Create the app.
   - Add `work_area` FK to `UserProfile` (Area where worker works).
   - Build endpoints: `renter-demographics`, `popular-areas`, `my-listings-insights`.
   - Aggregate from `UserProfile`, `UniversityVerification`, `Favorite`, `ViewingRequest`, `Reservation`, `Listing`.
   - **Require `IsRealtor` or `IsRealtorOrLandlord`** permission on all analytics views.
   - Optional: cache aggregated results for performance.

**Deliverable:** Realtors view student vs worker split, universities, work areas, and popular locations.

---

### Phase 7  -  Reports

**Goal:** Users can report listings or users for moderation.

1. **`reports` app**
   - Add `Report` (reporter, reported_listing or reported_user, reason, status).
   - Endpoints: submit report, list reports (admin).
   - Moderation workflow.

**Deliverable:** Report listings or users.

---

### Phase 8  -  Roommates

**Goal:** Roommate matching or viewing for shared accommodations.

1. **`roommates` app**
   - Add models for roommate profiles, preferences, matching.
   - **Require UAE ID verification** for roommate features.
   - Endpoints: create profile, search roommates, express interest.

**Deliverable:** Roommate matching and viewing.

---

### Phase 9  -  Documents

**Goal:** Centralized document storage for IDs, contracts, lease agreements.

1. **`documents` app**
   - Add `Document` (user, type, file, related_object FK generic).
   - Link to UAEIDVerification, LeaseAgreement, etc.
   - Endpoints: upload, list, retrieve.

**Deliverable:** Centralized document storage.

---

### Phase 10+  -  Assisted Listing

**Goal:** Full system for owners without Ejari/papers.

1. **`assisted_listing` app**
   - Complete onboarding, document collection, realtor matching.
   - Owner selects from platform realtors; Ejari and paperwork flow.
   - Models: `RealtorAssignment` (owner, realtor, property, status).

**Deliverable:** End-to-end assisted listing.

---

### Summary  -  Build Order

| Phase | Apps | Focus |
|-------|------|-------|
| 0 |  -  | Project setup |
| 1 | core, accounts, listings (+ Favorite) | MVP: auth + listings + interested list |
| 2 | accounts (verification), bookings | Verification + viewings/reservations |
| 3 | reviews | Social (reviews; favorites in Phase 1) |
| 4 | payments, messaging | Money + chat |
| 5 | lifestyle_services, notifications, **sms**, **emails**, polish | Lifestyle + in-app alerts + **logged** SMS/email + refinement |
| 6 | analytics | Realtor demographics & popular areas |
| 7 | reports | Report listings or users |
| 8 | roommates | Roommate matching (UAE ID required) |
| 9 | documents | Centralized document storage |
| 10+ | assisted_listing | Owners without Ejari/papers: realtor matching |

---

## APIs Overview

### Initial / MVP APIs (Phase 1-4)

#### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register (student/worker, landlord, realtor) |
| POST | `/api/auth/login/` | Login (email + password) |
| POST | `/api/auth/logout/` | Logout |
| POST | `/api/auth/refresh/` | Refresh JWT (if used) |
| GET | `/api/auth/me/` | Current user + profile |

#### Core (reference data)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/areas/` | List Dubai areas |
| GET | `/api/universities/` | List universities (for verification) |

#### Listings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/listings/` | List listings (filter: price, area, bedrooms) |
| GET | `/api/listings/{id}/` | Listing detail |
| POST | `/api/listings/` | Create listing (landlord/realtor) |
| PATCH | `/api/listings/{id}/` | Update listing |
| DELETE | `/api/listings/{id}/` | Delete listing |

#### Favorites / Interested list
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/favorites/` | List user's favorites |
| POST | `/api/favorites/` | Add listing to favorites |
| DELETE | `/api/favorites/{id}/` | Remove from favorites |

#### Verification
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/verification/uae-id/` | Submit UAE ID + document |
| POST | `/api/verification/university/` | Submit university email |
| GET | `/api/verification/status/` | Get verification status |

#### Bookings
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/viewings/` | Request viewing (UAE ID required) |
| GET | `/api/viewings/` | List viewings (tenant or landlord/realtor) |
| PATCH | `/api/viewings/{id}/` | Confirm/reject viewing |
| POST | `/api/reservations/` | Create reservation |
| GET | `/api/reservations/` | List reservations |

#### Reviews
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/reviews/` | Create review |
| GET | `/api/reviews/` | List reviews (by user or listing) |

#### Payments
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/payments/initiate/` | Initiate payment (rent, deposit, lifestyle) |
| GET | `/api/payments/` | List payments |
| POST | `/api/payments/webhook/` | Payment provider webhook |

#### Messaging
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/conversations/` | List conversations |
| POST | `/api/conversations/` | Start conversation (on listing) |
| GET | `/api/conversations/{id}/messages/` | List messages |
| POST | `/api/conversations/{id}/messages/` | Send message |

#### Lifestyle services (Phase 5)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/lifestyle-plans/` | List Essential/Comfort/Complete plans |
| POST | `/api/lifestyle-subscriptions/` | Subscribe to plan (linked to reservation) |
| GET | `/api/lifestyle-subscriptions/` | List user subscriptions |
| PATCH | `/api/lifestyle-subscriptions/{id}/` | Update/cancel subscription |

#### Notifications (Phase 5)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/notifications/` | List notifications |
| PATCH | `/api/notifications/{id}/read/` | Mark as read |
| GET | `/api/notifications/preferences/` | Get preferences |
| PATCH | `/api/notifications/preferences/` | Update preferences |

#### Analytics (Phase 6, realtors only)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics/renter-demographics/` | Student vs worker, universities, work areas |
| GET | `/api/analytics/popular-areas/` | Most saved/viewed/booked areas |
| GET | `/api/analytics/my-listings-insights/` | Realtor's own listing metrics |

#### Reports (Phase 7)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/reports/submit/` | Submit report (listing or user) |
| GET | `/api/reports/` | List reports (own; staff: all) |
| GET | `/api/reports/{id}/` | Report detail |
| PATCH | `/api/reports/{id}/` | Update status, admin_notes (staff only) |

#### Roommates (Phase 8, UAE ID required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/roommates/profile/` | Get own roommate profile |
| POST | `/api/roommates/profile/` | Create profile |
| PUT/PATCH | `/api/roommates/profile/` | Update profile |
| GET | `/api/roommates/search/` | Search roommates (?area=, ?budget_max=) |
| POST | `/api/roommates/interest/` | Express interest |
| GET | `/api/roommates/interests/` | List sent and received interests |
| PATCH | `/api/roommates/interests/{id}/` | Accept/decline (recipient only) |

#### Documents (Phase 9)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/documents/` | List current user's documents |
| POST | `/api/documents/` | Upload document (document_type, file; optional content_type_id, object_id) |
| GET | `/api/documents/{id}/` | Retrieve single document |

**Document types:** `uae_id`, `university`, `lease_agreement`, `realtor_license`, `passport`, `other`. Optional `content_type_id` and `object_id` link to related objects (e.g. UAEIDVerification, LeaseAgreement).

---

## API Placements (Codebase Reference)

*Where each API lives in the project. Use this when adding or extending endpoints.*

| Route prefix | App | URL module | Views module | Serializers |
|--------------|-----|------------|--------------|-------------|
| `/api/auth/` | `accounts` | `accounts/urls.py` | `accounts/views.py` | `accounts/serializers.py` |
| `/api/verification/` | `accounts` | `accounts/verification_urls.py` | `accounts/verification_views.py` | `accounts/serializers.py` (UAEIDVerificationSerializer, UniversityVerificationSerializer) |
| `/api/viewings/`, `/api/reservations/` | `bookings` | `bookings/urls.py` | `bookings/views.py` | `bookings/serializers.py` |
| `/api/areas/`, `/api/universities/` | `core` | `core/urls.py` | `core/views.py` | `core/serializers.py` |
| `/api/listings/`, `/api/favorites/` | `listings` | `listings/urls.py` | `listings/views.py` | `listings/serializers.py` |
| `/api/reviews/` | `reviews` *(Phase 3)* | `reviews/urls.py` | `reviews/views.py` | `reviews/serializers.py` |
| `/api/payments/` | `payments` *(Phase 4)* | `payments/urls.py` | `payments/views.py` | `payments/serializers.py` |
| `/api/conversations/` | `messaging` *(Phase 4)* | `messaging/urls.py` | `messaging/views.py` | `messaging/serializers.py` |
| `/api/lifestyle-plans/`, `/api/lifestyle-subscriptions/` | `lifestyle_services` *(Phase 5)* | `lifestyle_services/urls.py` | `lifestyle_services/views.py` | `lifestyle_services/serializers.py` |
| `/api/notifications/` | `notifications` *(Phase 5)* | `notifications/urls.py` | `notifications/views.py` | `notifications/serializers.py` |
| `/api/analytics/` | `analytics` *(Phase 6)* | `analytics/urls.py` | `analytics/views.py` | `analytics/serializers.py` |
| `/api/reports/` | `reports` *(Phase 7)* | `reports/urls.py` | `reports/views.py` | `reports/serializers.py` |
| `/api/roommates/` | `roommates` *(Phase 8)* | `roommates/urls.py` | `roommates/views.py` | `roommates/serializers.py` |
| `/api/documents/` | `documents` *(Phase 9)* | `documents/urls.py` | `documents/views.py` | `documents/serializers.py` |
| `/api/realtors/`, `/api/assisted-listing/` | `assisted_listing` *(Phase 10+)* | `assisted_listing/urls.py` | `assisted_listing/views.py` | `assisted_listing/serializers.py` |

**Wiring in main URL config** (`yallastay/urls.py`):
```python
path('api/auth/', include('accounts.urls')),
path('api/verification/', include('accounts.verification_urls')),
path('api/', include('bookings.urls')),
path('api/', include('core.urls')),
path('api/', include('listings.urls')),
# Add new: path('api/<prefix>/', include('<app>.urls')),
```

**Adding a new verification-type endpoint** (e.g. future `POST /api/verification/passport/`):
1. Add serializer in `accounts/serializers.py`
2. Add view in `accounts/verification_views.py`
3. Add path in `accounts/verification_urls.py`

**Adding a new API group** (e.g. new app):
1. Create app: `python manage.py startapp <app_name>`
2. Add to `INSTALLED_APPS` in `yallastay/settings/base.py`
3. Create `views.py`, `serializers.py`, `urls.py` in the app
4. Include in `yallastay/urls.py`: `path('api/<prefix>/', include('<app>.urls'))`

---

### External Integrations  -  Used From the Beginning

*Platform realtors handle Ejari and RERA manually  -  no Ejari API or RERA API integration.*

| API / Service | Purpose | Phase |
|---------------|---------|-------|
| **Stripe** or **PayTabs** | Payments, subscriptions, webhooks | 4 |
| **Email** (SendGrid, AWS SES) | Verification emails, notifications | 2+ |
| **File storage** (S3, etc.) | Documents, listing images | 1+ |
| **SMS** (Twilio, etc.) | OTP, alerts | Optional |
| **Push notifications** (Firebase, etc.) | Mobile push | 5 |
| **Cleaning partner** | Schedule, manage cleaning | 5 |
| **Internet provider** | Setup requests, status | 5 |
| **Furniture rental** | Discounts, basic pack | 5 |
| **Gym partner** | Access, premium membership | 5 |
| **UAE ID / Identity** (gov API) | Automated Emirates ID verification |

---

### Not Integrated  -  Handled by Platform Realtors

| Item | Reason |
|------|--------|
| **Ejari API** | Platform realtors register tenancy contracts and handle Ejari manually |
| **RERA API** | Platform realtors are RERA-licensed; verification done via document upload, not API |

---

### Platform APIs (Phase 7+)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/realtors/` | List platform realtors (for owners without papers) |
| POST | `/api/assisted-listing/` | Owner requests assisted listing, selects realtor |
| GET | `/api/assisted-listing/` | List assisted listing requests / assignments |

---

## Recommended Django Apps

| App | Purpose |
|-----|---------|
| **`accounts`** | User profiles, authentication, verification (UAE ID, university) |
| **`listings`** | Apartments, rooms, shared spaces |
| **`bookings`** | Viewings, reservations, lease agreements |
| **`reviews`** | Ratings and reviews for students, workers, landlords, realtors |
| **`payments`** | Rent, deposits, fees |
| **`lifestyle_services`** | Cleaning, internet, maintenance, furniture, gym  -  Essential / Comfort / Complete plans |
| **`messaging`** | In-app messaging between users |
| **`notifications`** | Alerts, emails, push notifications |
| **`analytics`** | Aggregated student & worker demographics for realtors (split, universities, work areas, popular locations) |
| **`core`** | Shared utilities, base models, config |
| **`reports`** *(Phase 7)* | Report listings or users |
| **`roommates`** *(Phase 8)* | Roommate matching; UAE ID required |
| **`documents`** *(Phase 9)* | Centralized document storage (IDs, contracts) |
| **`assisted_listing`** *(Phase 10+)* | Owners without Ejari/papers; realtor matching |

---

## Models by App

### 1. `accounts`

| Model | Purpose |
|-------|---------|
| `User` | Extend Django's AbstractUser (email as username, role, etc.) |
| `UserProfile` | Phone, avatar, bio, preferences, role (**student**/worker/landlord/**realtor**), **work_area** FK to Area (where worker works) |
| `UniversityVerification` | University email, institution, student ID, status, verified_at |
| `UAEIDVerification` | Emirates ID number (hashed), document upload, status, verified_at |
| `LandlordProfile` | Company name, license, bank details; **needs_assisted_listing** bool (owner without Ejari/papers; will select platform realtor) |
| `RealtorProfile` | Agency name, brokerage license number, RERA registration, license document, bank details, verified_at |

### 2. `listings`

| Model | Purpose |
|-------|---------|
| `Listing` | Title, description, price, currency (AED), type (apartment/room/shared), address, area (sqft), bedrooms, bathrooms, amenities (JSON or M2M), status (active/paused/closed), **listed_by** FK (User  -  landlord or realtor), **property_owner** FK optional (when realtor posts for client) |
| `ListingImage` | Image, order, listing FK |
| `Favorite` / `InterestedListing` | User FK, listing FK  -  **available to all users** (incl. non-UAE ID) |
| `Amenity` | Name (WiFi, AC, gym, etc.)  -  optional lookup table |
| `Location` | City, area, district, building name, coordinates (for map search) |
| `Availability` | Start date, end date, listing FK (for short-term) |

### 3. `bookings`

| Model | Purpose |
|-------|---------|
| `ViewingRequest` | Listing, student/worker (User FK), requested_datetime, status (pending/confirmed/rejected), notes |
| `Reservation` | Listing, student/worker (User FK), start_date, end_date, status, deposit_amount |
| `LeaseAgreement` | Reservation FK, document URL, signed_at, terms |

### 4. `reviews`

| Model | Purpose |
|-------|---------|
| `Review` | Reviewer, reviewee (User), listing (optional), rating (1-5), comment, created_at |
| `ReviewResponse` | Review FK, response text, landlord reply |

### 5. `payments`

| Model | Purpose |
|-------|---------|
| `Payment` | User, amount, currency, type (rent/deposit/fee/lifestyle), status, payment_method, transaction_id |
| `RentSchedule` | Reservation FK, due_date, amount, status (pending/paid/overdue) |
| `Deposit` | Reservation FK, amount, status (held/refunded/deducted) |

### 5b. `lifestyle_services`

| Model | Purpose |
|-------|---------|
| `LifestylePlan` | Name (Essential/Comfort/Complete), price, tier (1/2/3) |
| `LifestyleService` | Plan FK, service_type (cleaning/internet/maintenance/furniture/gym/support), details (JSON or text) |
| `LifestyleSubscription` | Reservation FK, plan FK, user FK, start_date, end_date, status, billed via Payment |

### 6. `messaging`

| Model | Purpose |
|-------|---------|
| `Conversation` | Listing FK, participants (M2M to User), created_at |
| `Message` | Conversation FK, sender, content, read_at, created_at |

### 7. `notifications`

| Model | Purpose |
|-------|---------|
| `Notification` | User FK, type (booking/viewing/message/etc.), title, body, read, created_at |
| `NotificationPreference` | User FK, channel (email/push), notification_type, enabled |

### 8. `core`

| Model | Purpose |
|-------|---------|
| `University` | Name, domain (e.g. `@uaeu.ac.ae`), country |
| `Area` | Dubai areas (e.g. Dubai Marina, JLT, Academic City) for filters |

### 9. `reports`

| Model | Purpose |
|-------|---------|
| `Report` | Reporter, reported_listing or reported_user, reason, status (pending/reviewed/resolved/dismissed), admin_notes |

### 10. `roommates`

| Model | Purpose |
|-------|---------|
| `RoommateProfile` | User (1:1), bio, budget_min/max, preferred_areas (M2M), move_in_date, lifestyle_preferences, is_looking |
| `RoommateInterest` | from_user, to_user, message, status (pending/accepted/declined) |

### 11. `documents`

| Model | Purpose |
|-------|---------|
| `Document` | User FK, document_type (uae_id/university/lease_agreement/realtor_license/passport/other), file, content_type + object_id (generic FK to related object), created_at |

### 12. `analytics`

| Note | Purpose |
|------|---------|
| No storage models | Analytics are computed from `UserProfile`, `UniversityVerification`, `Favorite`, `ViewingRequest`, `Reservation`, `Listing` |
| Optional: `AnalyticsCache` | Cache aggregated results (e.g. daily) for performance |

---

## Verification Flow

1. **UAE ID**: User uploads Emirates ID; backend validates format and stores hashed ID; admin or automated checks approve/reject.
2. **University**: User enters university email; system sends verification link; optional integration with university domains for auto-verification.
3. **Realtors**: UAE ID + brokerage license / RERA registration; admin approves before realtor can post listings.

---

## Entity Relationships

```
User (accounts)
  ├── UserProfile (1:1)
  ├── UniversityVerification (1:1, optional)
  ├── UAEIDVerification (1:1)
  ├── LandlordProfile (1:1, optional)
  └── RealtorProfile (1:1, optional)

Listing (listings)
  ├── listed_by → User (landlord or realtor)
  ├── property_owner → User optional (when realtor posts for client)
  ├── has Location
  ├── has ListingImages
  └── has Amenities (M2M)

Reservation (bookings)
  ├── Listing
  ├── User (student or worker)
  ├── LeaseAgreement
  └── LifestyleSubscription (optional)

LifestyleSubscription (lifestyle_services)
  ├── Reservation FK
  ├── LifestylePlan FK
  └── User FK
```

---

## Later Phases (7-10+)

These phases are defined above in the Incremental Build Guide:

| Phase | App | Notes |
|-------|-----|-------|
| 7 | `reports` | Report listings or users |
| 8 | `roommates` | Roommate matching; **UAE ID required** |
| 9 | `documents` | Centralized document storage (IDs, contracts) |
| 10+ | `assisted_listing` | Owners without Ejari/papers; realtor matching |

**Note:** Favorites (interested list) is implemented in Phase 1 as part of the `listings` app.
