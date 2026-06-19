# Frontend-Backend Mapping & Methodology

Reference for keeping frontend and backend in sync.

---

## Project Completion: ~55%

| Area | Status | Notes |
|------|--------|-------|
| **Backend** (apps, models, API, admin) | ✓ Complete | All apps wired, migrations applied |
| **Frontend** (pages, API client, routes) | ✓ Complete | All pages wired to backend |
| **Domain** | ✗ Incomplete | Custom domain not configured |
| **UAE ID API** | ✗ Incomplete | No gov/identity API integration; manual admin approval only |
| **Hosting / Railway** | ✗ Incomplete | Not deployed |
| **Email sending** | Partial | **`emails`** app: `EmailMessage` + `send_transactional_email()` + SendGrid-style webhook  -  wire from flows (verification, receipts) |
| **SMS sending** | Partial | **`sms`** app: `SmsMessage` + `send_sms()` + Twilio webhook  -  wire from OTP/alerts; needs `pip install twilio` + env for live sends |
| **Payments** | ✗ Incomplete | No gateway (PayTabs/Stripe) integration |

---

## 1. API Client (`src/api/client.js`)

Every backend API should have a corresponding client method. When adding a new backend endpoint:

1. Add the method to the appropriate export in `client.js`
2. Use the client (not raw `fetch`) in frontend components for consistency and interceptors

| Backend App   | API Client Export | Endpoints Covered |
|---------------|-------------------|-------------------|
| accounts      | `auth`            | register, login, me, logout |
| accounts      | `verification`    | uaeId, university, status |
| core          | `core`            | areas, universities |
| listings      | `listings`        | list, get, create, update, delete |
| listings      | `favorites`       | list, add, remove |
| bookings      | `bookings`        | requestViewing, listViewings, updateViewing, createReservation, listReservations |
| reviews       | `reviews`         | create, list |
| lifestyle_services | `lifestyle` | plans, subscribe, subscriptions |
| messaging     | `messaging`       | listConversations, createConversation, listMessages, sendMessage, markMessageRead, markConversationRead |
| notifications | `notifications`   | list, markRead, getPreferences, updatePreferences |
| reports       | `reports`         | submit, list, get |
| roommates     | `roommates`       | getProfile, createProfile, updateProfile, search, expressInterest, listInterests, updateInterest |
| documents     | `documents`       | list, upload, get |
| analytics     | `analytics`       | renterDemographics, popularAreas, myListingsInsights |
| payments      | (not in client)   | initiate, webhook  -  payment gateway integration |
| sms           | (server-only)     | Webhooks are provider → backend; no browser client |
| emails        | (server-only)     | Webhooks are provider → backend; no browser client |

---

## 2. Pages & Backend Coverage

| Page              | Backend Used | Status |
|-------------------|--------------|--------|
| Home              | listings, core (areas) | ✓ Areas in search form; listings from API |
| Search            | listings, core | ✓ Filters by area_slug, type |
| Property          | listings, favorites, bookings, messaging, reports | ✓ Favorite, request viewing, message landlord, report listing |
| Login/Signup      | auth         | ✓ |
| Verify            | verification | ✓ UAE ID, university |
| Dashboard         | auth, favorites, bookings, messaging, notifications | ✓ Viewings, reservations, links to Messages/Notifications/Documents/Roommates |
| RealtorDashboard  | listings, analytics | ✓ My listings + insights |
| Services          | lifestyle    | ✓ Plans from API |
| AddProperty       | listings, core | ✓ Areas from API, create listing |
| Messages          | messaging    | ✓ List conversations, send messages |
| Notifications     | notifications | ✓ List, mark read |
| Roommates         | roommates, core | ✓ Profile, search, express interest, sent/received interests |
| Documents         | documents    | ✓ List user's documents, link to Verify |
| ForPartners       |  -             | Static |
| BackendConfig     |  -             | API status check |

---

## 3. Not Yet Wired / Partial (Future Work)

| Backend      | Frontend Status | Notes |
|--------------|-----------------|-------|
| **Reports**  | ✓ Property page | Report listing modal. No standalone Reports page (admin-only list). |
| **Documents**| ✓ Documents page | List + view. Verify page file upload does not yet use documents.upload() for persistence. |
| **Payments** | Not wired       | Payments require gateway (e.g. PayTabs). Frontend would need initiate → redirect. |
| **Verify (University)** | Partial | Backend expects university_id, student_id; frontend only sends email. May need university selector. |

---

## 4. What Was Forgotten (Lessons Learned)

When connecting apps and models to the frontend, these gaps are easy to miss:

1. **Reports**  -  Backend had submit endpoint; frontend had no Report button. **Fix:** Add Report modal on Property page.
2. **Roommates**  -  Full backend (profile, search, interests); wired at **`/roommates`** (profile CRUD, search filters, interests, express interest / accept / decline). Demo tenant gets a seeded profile via **`seed_demo`**.
3. **Documents**  -  Backend lists/upload; Verify page had file input but no document list. **Fix:** Add Documents page + link from Dashboard.
4. **Navigation**  -  New pages need routes in `App.jsx` and links in Header or Dashboard.
5. **API client**  -  Always add/use methods in `client.js`; avoid raw `fetch` for consistency (auth, 401 handling).
6. **Verify (University)**  -  Backend expects `university_id`, optionally `student_id`; frontend only sent `email`. Verify serializer may accept email and resolve university; check backend.
7. **Payments**  -  Gateway integration is separate; requires initiate → redirect flow.

### Checklist When Adding a Backend App

- [x] Model + migration + admin
- [x] URLs included in main `urls.py`
- [x] API client method in `client.js`
- [x] Frontend page or component that uses it
- [x] Route in `App.jsx`
- [x] Navigation link (Header, Dashboard, or contextual)

---

## 5. Correct Methodology for New Features

### When adding a backend model/endpoint

1. **Migrations:** Run `makemigrations <app>` and `migrate`
2. **Admin:** Register model in `admin.py` if it should be editable in admin
3. **URLs:** Add route in app `urls.py`; include app in main `urls.py` if new app
4. **API client:** Add method to `src/api/client.js`
5. **Frontend page/component:** Use the client method; add route in `App.jsx` if new page
6. **Navigation:** Add link in Header, Dashboard, or relevant page

### When adding a frontend feature

1. **Check backend:** Ensure the endpoint exists; add if not
2. **API client:** Add or use existing client method
3. **Use client:** Prefer `api` client over raw `fetch` (auth headers, 401 handling)
4. **Handle errors:** Show `e.response?.data?.detail` or field errors

### Query param alignment

- Listings filter: `area_slug`, `type`, `min_price`, `max_price` (match `ListingFilter`)
- Areas from `/api/areas/`  -  use `id` for create, `slug` for filter
- Search form: pass `area_slug` to align with backend

---

## 6. Checklist for Full-Stack Feature

- [x] Backend model + migration
- [x] Backend serializer + view + URL
- [x] Backend admin registration (if needed)
- [x] API client method
- [x] Frontend page or component
- [x] Route (if new page)
- [x] Navigation link
- [x] Error handling and loading states
