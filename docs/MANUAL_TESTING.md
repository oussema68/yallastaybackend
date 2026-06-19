# Yallastay Backend  -  Manual Testing Guide

Use this guide to manually test each app's API. Run the server (`python manage.py runserver`) and use a client like Postman, Insomnia, curl, or Thunder Client.

**Base URL:** `http://localhost:8000` (or your server)

> **Full-stack verification:** For connecting frontend and backend and walking through the app, see **USAGE_GUIDE.md**.

---

## Prerequisites

1. **Seed core data:** `python manage.py seed_core` (creates areas and universities)
2. **Seed lifestyle plans:** `python manage.py seed_lifestyle` (creates Essential, Comfort, Complete plans)
3. **Create a superuser** (optional, for admin/staff tests): `python manage.py createsuperuser`
4. **Auth:** Most endpoints require JWT. Use the token from register/login as `Authorization: Bearer <token>`
5. **Realtors:** For analytics, realtor must be approved (`is_approved=True`) in admin

---

## API Root

| Test | Method | URL | Auth | Expected |
|------|--------|-----|------|----------|
| Root | GET | `/` | No | 200, `{"message":"Yallastay API","status":"ok"}` |

---

## 1. Core

**Endpoints:** `/api/areas/`, `/api/universities/`

| Test | Method | URL | Auth | Expected |
|------|--------|-----|------|----------|
| List areas | GET | `/api/areas/` | No | 200, list of areas (e.g. Dubai Marina, JLT) |
| Retrieve area | GET | `/api/areas/1/` | No | 200, single area |
| Retrieve nonexistent area | GET | `/api/areas/99999/` | No | 404 |
| List universities | GET | `/api/universities/` | No | 200, list of universities |

**Note:** Run `seed_core` first if lists are empty.

---

## 2. Accounts (Auth & Verification)

### Auth

| Test | Method | URL | Body | Auth | Expected |
|------|--------|-----|------|------|----------|
| Register (student) | POST | `/api/auth/register/` | `{"email":"test@example.com","password":"TestPass123!","role":"student"}` | No | 201, token + user |
| Register (landlord) | POST | `/api/auth/register/` | `{"email":"landlord@example.com","password":"TestPass123!","role":"landlord"}` | No | 201, LandlordProfile created |
| Register (realtor) | POST | `/api/auth/register/` | `{"email":"realtor@example.com","password":"TestPass123!","role":"realtor"}` | No | 201, RealtorProfile created |
| Register short password | POST | `/api/auth/register/` | `{"email":"x@x.com","password":"short","role":"student"}` | No | 400 |
| Register duplicate email | POST | `/api/auth/register/` | Same email twice | No | 400 |
| Login | POST | `/api/auth/login/` | `{"email":"test@example.com","password":"TestPass123!"}` | No | 200, token + refresh |
| Login wrong password | POST | `/api/auth/login/` | `{"email":"test@example.com","password":"Wrong!"}` | No | 401 |
| Refresh token | POST | `/api/auth/refresh/` | `{"refresh":"<refresh_token>"}` | No | 200, new access token |
| Logout | POST | `/api/auth/logout/` | `{"refresh":"<refresh_token>"}` | No | 200 |
| Me | GET | `/api/auth/me/` |  -  | Yes | 200, user + profile |
| Me (no auth) | GET | `/api/auth/me/` |  -  | No | 401 |
| Update profile | PATCH | `/api/auth/me/` | `{"phone":"+971501234567","bio":"Student"}` | Yes | 200 |

### Verification

| Test | Method | URL | Body | Auth | Expected |
|------|--------|-----|------|------|----------|
| UAE ID submit | POST | `/api/verification/uae-id/` | `{"emirates_id":"784-1234-1234567-1"}` (multipart: + document file) | Yes | 200/201 |
| UAE ID invalid format | POST | `/api/verification/uae-id/` | `{"emirates_id":"123"}` | Yes | 400 |
| University submit | POST | `/api/verification/university/` | `{"email":"student@uaeu.ac.ae","university_id":1,"student_id":"123"}` | Yes | 200/201 |
| University wrong domain | POST | `/api/verification/university/` | `{"email":"student@gmail.com","university_id":1}` | Yes | 400 |
| Verification status | GET | `/api/verification/status/` |  -  | Yes | 200, uae_id_verified, university_verified |

### Staff verification (brokers & owners)

Requires **`UserProfile.can_verify_documents=True`** (set in Django Admin) **or** Django **`is_staff`** / **`is_superuser`**.

After **`python manage.py bootstrap_demo`**, **`GET /api/staff/verification/queue/`** as **`demo.verify@present.yallastay`** (password in **`DEMO_PRESENTATION.md`**) should include **`demo.realtor-pending@…`** under **`realtors`** and **`demo.owner-pending@…`** under **`landlords`** (use returned **`user_id`** in decision URLs, not `1`).

| Test | Method | URL | Body | Auth | Expected |
|------|--------|-----|------|------|----------|
| Queue | GET | `/api/staff/verification/queue/` |  -  | Yes (verification staff) | 200, `realtors` + `landlords` with `checklist` |
| Queue (normal tenant) | GET | `/api/staff/verification/queue/` |  -  | Yes (tenant) | 403 |
| Approve broker | POST | `/api/staff/verification/realtors/1/decision/` | `{"action":"approve"}` | Yes (verification staff) | 200 |
| Reject broker | POST | `/api/staff/verification/realtors/1/decision/` | `{"action":"reject","message":"..."}` | Yes (verification staff) | 200 + in-app notification |
| Approve owner | POST | `/api/staff/verification/landlords/1/decision/` | `{"action":"approve"}` | Yes (verification staff) | 200 |

---

| Test | Method | URL | Auth | Notes |
|------|--------|-----|------|-------|
| List listings | GET | `/api/listings/` | No | 200 |
| Filter listings | GET | `/api/listings/?min_price=3000&max_price=8000&area=1` | No | 200 |
| Search listings | GET | `/api/listings/?search=Marina` | No | 200 |
| Order listings | GET | `/api/listings/?ordering=price` or `?ordering=-created_at` | No | 200 |
| Retrieve listing | GET | `/api/listings/1/` | No | 200 |
| Retrieve nonexistent | GET | `/api/listings/99999/` | No | 404 |
| Create listing (landlord) | POST | `/api/listings/` | Yes (landlord) | `{"title":"New Apt","description":"Nice","price":5000,"type":"apartment","area":1}` |
| Create listing (unapproved realtor) | POST | `/api/listings/` | Yes (realtor, not approved) | 403 |
| Update listing (owner) | PATCH | `/api/listings/1/` | Yes | `{"price":5500}` |
| Update listing (non-owner) | PATCH | `/api/listings/1/` | Yes | 403 |
| Delete listing | DELETE | `/api/listings/1/` | Yes (owner) | 204 |
| List own listings | GET | `/api/listings/?mine=1` | Yes (landlord/realtor) | 200 |
| Add favorite | POST | `/api/favorites/` | Yes | `{"listing":1}` |
| List favorites | GET | `/api/favorites/` | Yes | 200 |
| Remove favorite | DELETE | `/api/favorites/1/` | Yes | 204 |

**Listing types:** `room`, `studio`, `apartment`

---

## 4. Bookings

**Requires UAE ID verification** for POST viewings and reservations.

| Test | Method | URL | Auth | Notes |
|------|--------|-----|------|-------|
| List viewings (tenant) | GET | `/api/viewings/` | Yes | Own requests only |
| List viewings (landlord) | GET | `/api/viewings/` | Yes | For their listings |
| Viewing detail | GET | `/api/viewings/1/` | Yes | 200 |
| Request viewing (no UAE ID) | POST | `/api/viewings/` | Yes | 403 |
| Request viewing | POST | `/api/viewings/` | Yes (UAE ID) | `{"listing_id":1,"requested_datetime":"2025-03-15T10:00:00Z","notes":"..."}` |
| Confirm viewing | PATCH | `/api/viewings/1/` | Yes (landlord) | `{"status":"confirmed"}` |
| Reject viewing | PATCH | `/api/viewings/1/` | Yes (landlord) | `{"status":"rejected"}` |
| Tenant confirm viewing | PATCH | `/api/viewings/1/` | Yes (tenant) | 403 |
| List reservations | GET | `/api/reservations/` | Yes | 200 |
| Create reservation (no UAE ID) | POST | `/api/reservations/` | Yes | 403 |
| Create reservation | POST | `/api/reservations/` | Yes (UAE ID) | `{"listing_id":1,"start_date":"2025-04-01","end_date":"2025-10-01"}` |
| Reservation detail | GET | `/api/reservations/1/` | Yes | 200 |
| Move-in (renter, confirmed) | PATCH | `/api/reservations/1/move-in/` | Yes (renter on booking) | `{"keys_received":true,"platform_feedback":"..."}` |
| Move-in (pending booking) | PATCH | `/api/reservations/1/move-in/` | Yes (renter) | 400 |
| Move-in (lister) | PATCH | `/api/reservations/1/move-in/` | Yes (lister) | 404 |

---

## 5. Reviews

**Requires UAE ID verification** for creating reviews.

| Test | Method | URL | Auth | Notes |
|------|--------|-----|------|-------|
| List reviews | GET | `/api/reviews/` | Yes | 200 |
| Filter by user | GET | `/api/reviews/?user=1` | Yes | 200 |
| Filter by listing | GET | `/api/reviews/?listing=1` | Yes | 200 |
| Review detail | GET | `/api/reviews/1/` | Yes | 200 |
| Create review (no UAE ID) | POST | `/api/reviews/` | Yes | 403 |
| Create review | POST | `/api/reviews/` | Yes (UAE ID) | `{"reviewee_id":1,"listing_id":1,"rating":5,"comment":"Great!"}` |
| Create review self | POST | `/api/reviews/` | Yes | `{"reviewee_id":<self>}` → 400 |
| Create review invalid rating | POST | `/api/reviews/` | Yes | `{"rating":10}` → 400 |
| Add response (reviewee) | POST | `/api/reviews/1/response/` | Yes (reviewee) | `{"response_text":"Thanks!"}` |
| Add response (non-reviewee) | POST | `/api/reviews/1/response/` | Yes | 403 |
| Add response (already exists) | POST | `/api/reviews/1/response/` | Yes | 400 |

**Rating:** 1-5

---

## 6. Payments

| Test | Method | URL | Auth | Notes |
|------|--------|-----|------|-------|
| List payments | GET | `/api/payments/` | Yes | 200 |
| Initiate payment (fee) | POST | `/api/payments/initiate/` | Yes | `{"amount":5000,"payment_type":"fee","currency":"AED"}` |
| Initiate payment (rent, needs reservation) | POST | `/api/payments/initiate/` | Yes | `{"amount":5000,"payment_type":"rent","reservation_id":1}` |
| Webhook | POST | `/api/payments/webhook/` | No | `{"transaction_id":"ys_xxx"}`  -  marks payment completed |

**Payment types:** `rent`, `deposit`, `fee`, `lifestyle`  -  rent/deposit require `reservation_id`

---

## 7. Messaging

**Requires UAE ID verification** for creating conversations and sending messages.

| Test | Method | URL | Auth | Notes |
|------|--------|-----|------|-------|
| List conversations | GET | `/api/conversations/` | Yes | 200 |
| Create conversation (no UAE ID) | POST | `/api/conversations/` | Yes | 403 |
| Create conversation | POST | `/api/conversations/` | Yes (UAE ID) | `{"listing_id":1}` |
| Conversation detail | GET | `/api/conversations/1/` | Yes | 200 (must be participant) |
| List messages | GET | `/api/conversations/1/messages/` | Yes | 200 |
| Send message | POST | `/api/conversations/1/messages/` | Yes (UAE ID) | `{"content":"Hello!"}` |
| Mark message read | POST | `/api/conversations/1/messages/1/read/` | Yes | 200 |
| Mark conversation read | POST | `/api/conversations/1/mark-read/` | Yes | 200 |

---

## 8. Lifestyle Services

| Test | Method | URL | Auth | Notes |
|------|--------|-----|------|-------|
| List plans | GET | `/api/lifestyle-plans/` | Yes | 200 |
| List subscriptions | GET | `/api/lifestyle-subscriptions/` | Yes | 200 |
| Subscribe | POST | `/api/lifestyle-subscriptions/` | Yes | `{"plan_id":1,"reservation_id":1,"start_date":"2025-04-01"}`  -  reservation must be yours |
| Subscription detail | GET | `/api/lifestyle-subscriptions/1/` | Yes | 200 |
| Cancel subscription | PATCH | `/api/lifestyle-subscriptions/1/` | Yes | `{"status":"cancelled"}` |

---

## 9. Notifications

| Test | Method | URL | Auth | Notes |
|------|--------|-----|------|-------|
| List notifications | GET | `/api/notifications/` | Yes | 200 |
| Mark read | PATCH | `/api/notifications/1/read/` | Yes | 200 |
| Get preferences | GET | `/api/notifications/preferences/` | Yes | 200 |
| Update preferences (single) | PATCH | `/api/notifications/preferences/` | Yes | `{"channel":"email","notification_type":"general","enabled":true}` |
| Update preferences (list) | PATCH | `/api/notifications/preferences/` | Yes | `[{"channel":"email",...}]` |

---

## 9a. SMS & Email (outbound  -  provider webhooks)

These routes are **server-to-server** (Twilio / SendGrid). They are **not** JWT-protected. In production, **always** verify signatures or a shared secret  -  never expose `TWILIO_WEBHOOK_INSECURE_OK` / `SENDGRID_WEBHOOK_INSECURE_OK` in production.

**Models & admin:** `sms.SmsMessage`, `emails.EmailMessage`  -  visible in Django admin for audit.

| Test | Method | URL | Auth | Expected |
|------|--------|-----|------|----------|
| Twilio status (dev) | POST | `/api/sms/webhooks/twilio/status/` | No (use env) | Set `TWILIO_WEBHOOK_INSECURE_OK=true` locally. Body: `MessageSid=<sid>&MessageStatus=delivered` (form). 200 if `SmsMessage.provider_message_id` matches. |
| Twilio status (reject) | POST | `/api/sms/webhooks/twilio/status/` | No | 403 if insecure flag off and request not verified |
| SendGrid events (dev) | POST | `/api/emails/webhooks/sendgrid/events/` | No | Set `SENDGRID_WEBHOOK_INSECURE_OK=true`. JSON body: `[{"event":"delivered","email":"user@example.com","sg_message_id":"<id>"}]`. 200 |
| SendGrid events (reject) | POST | `/api/emails/webhooks/sendgrid/events/` | No | 403 if `SENDGRID_WEBHOOK_SECRET` not matched via `X-Webhook-Secret` and insecure flag off |

**Sending from shell (creates DB rows):**

```bash
python manage.py shell
>>> from sms.services import send_sms
>>> send_sms("+971501234567", body="test")  # skipped if Twilio env not set
>>> from emails.services import send_transactional_email
>>> send_transactional_email("you@example.com", subject="Hi", body_text="Hello")
```

**Automated tests:** `python manage.py test sms emails`

---

## 10. Analytics

**Requires approved realtor** for renter-demographics and popular-areas. **Landlord or realtor** for my-listings-insights.

| Test | Method | URL | Auth | Notes |
|------|--------|-----|------|-------|
| Renter demographics (non-realtor) | GET | `/api/analytics/renter-demographics/` | Yes | 403 |
| Renter demographics | GET | `/api/analytics/renter-demographics/` | Yes (approved realtor) | 200 |
| Popular areas | GET | `/api/analytics/popular-areas/` | Yes (approved realtor) | 200 |
| My listings insights | GET | `/api/analytics/my-listings-insights/` | Yes (realtor/landlord) | 200 |

---

## 11. Reports

| Test | Method | URL | Auth | Notes |
|------|--------|-----|------|-------|
| Submit report (listing) | POST | `/api/reports/submit/` | Yes | `{"listing_id":1,"reason":"spam"}` |
| Submit report (user) | POST | `/api/reports/submit/` | Yes | `{"user_id":1,"reason":"harassment"}` |
| Submit both | POST | `/api/reports/submit/` | Yes | 400 |
| Submit neither | POST | `/api/reports/submit/` | Yes | 400 |
| List reports | GET | `/api/reports/` | Yes | Own reports; staff see all |
| Report detail (reporter) | GET | `/api/reports/1/` | Yes | 200 |
| Report detail (non-reporter) | GET | `/api/reports/1/` | Yes | 404 |
| Update status (staff) | PATCH | `/api/reports/1/` | Yes (staff) | `{"status":"resolved","admin_notes":"..."}` |
| Update status (non-staff) | PATCH | `/api/reports/1/` | Yes | 403 |

**Status values:** `pending`, `reviewed`, `resolved`, `dismissed`

---

## 12. Roommates (UAE ID required for create/update/search)

**Students and workers only.** Landlords get 403 on roommate endpoints.

| Test | Method | URL | Auth | Notes |
|------|--------|-----|------|-------|
| Get profile (none) | GET | `/api/roommates/profile/` | Yes | 200, body `null` |
| Get profile | GET | `/api/roommates/profile/` | Yes | 200 |
| Create profile (no UAE ID) | POST | `/api/roommates/profile/` | Yes | 403 |
| Create profile | POST | `/api/roommates/profile/` | Yes (UAE ID) | `{"bio":"...","budget_min":2000,"budget_max":4000,"preferred_area_ids":[1]}` |
| Update profile | PATCH | `/api/roommates/profile/` | Yes | `{"bio":"Updated"}` |
| Landlord access | GET | `/api/roommates/profile/` | Yes (landlord) | 403 |
| Search | GET | `/api/roommates/search/?area=dubai-marina&budget_max=5000&budget_min=2000&move_in_before=2026-12-31` | Yes (UAE ID) | `area` = slug **or** numeric area id |
| Express interest | POST | `/api/roommates/interest/` | Yes | `{"to_user_id":1,"message":"Hi!"}`  -  target must be looking |
| List interests | GET | `/api/roommates/interests/` | Yes | 200 |
| Accept interest | PATCH | `/api/roommates/interests/1/` | Yes (recipient) | `{"status":"accepted"}` |
| Decline interest | PATCH | `/api/roommates/interests/1/` | Yes (recipient) | `{"status":"declined"}` |

---

## 13. Documents

| Test | Method | URL | Auth | Notes |
|------|--------|-----|------|-------|
| List documents | GET | `/api/documents/` | Yes | 200 |
| Upload document | POST | `/api/documents/` | Yes | Multipart: `document_type`, `file` |
| Upload invalid type | POST | `/api/documents/` | Yes | 400 |
| Upload content_type without object_id | POST | `/api/documents/` | Yes | 400 (must provide both or neither) |
| Retrieve own document | GET | `/api/documents/1/` | Yes | 200 |
| Retrieve other's document | GET | `/api/documents/1/` | Yes | 404 |

**Document types:** `uae_id`, `university`, `lease_agreement`, `realtor_license`, `passport`, `other`

**Example upload (curl):**
```bash
curl -X POST http://localhost:8000/api/documents/ \
  -H "Authorization: Bearer <token>" \
  -F "document_type=uae_id" \
  -F "file=@/path/to/id.pdf"
```

---

## Management Commands

| Command | Description |
|--------|-------------|
| `python manage.py seed_core` | Seeds Area and University with Dubai data |
| `python manage.py seed_lifestyle` | Seeds LifestylePlan and LifestyleService |

---

## Error / Edge Case Checklist

- [ ] 401 on protected endpoints without token
- [ ] 403 when permission denied (UAE ID, realtor, ownership)
- [ ] 404 for nonexistent or unauthorized resources
- [ ] 400 for validation errors (short password, wrong domain, both/neither in reports)
- [ ] Non-owner cannot update/delete listing
- [ ] Non-reporter cannot see report detail
- [ ] Tenant cannot confirm viewing
- [ ] Landlord cannot use roommate features
- [ ] Cannot review self
- [ ] Cannot add second review response

---

## Quick Test Flow

1. Register → login → get token
2. `GET /`  -  api root
3. `GET /api/areas/`  -  verify core data
4. Create landlord user, create listing
5. Add listing to favorites as student
6. Submit UAE ID verification
7. Request viewing
8. Landlord confirm/reject viewing
9. Create reservation
10. Submit university verification
11. Leave review, add response
12. Start conversation, send message, mark read
13. Upload document
14. Create lifestyle subscription, cancel
15. Initiate payment, webhook
16. (As approved realtor) Check analytics
17. Submit report, staff update status
18. Create roommate profile, search, express interest, accept
19. Check notifications, update preferences
20. (Optional) `send_sms` / `send_transactional_email` in Django shell  -  see §9a

---

## Run Automated Tests

```bash
python manage.py test
```

Or per app:
```bash
python manage.py test core accounts listings bookings reviews payments messaging lifestyle_services notifications sms emails analytics reports roommates documents yallastay
```
