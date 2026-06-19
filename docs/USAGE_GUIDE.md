# Yallastay  -  Frontend & Backend Usage Guide

End-to-end guide to run, connect, and verify the Yallastay platform (frontend + backend).

**Public demo (Railway):** variable checklist and **`VITE_API_URL`** build instructions are in **`DEMO_PRESENTATION.md`** → *Deploy on Railway*.

---

## 1. Quick Start

### Backend (API)

```powershell
cd C:\Users\USER\Desktop\yallastay_backend\yallastay
.\..\venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py seed_core
python manage.py seed_lifestyle
python manage.py seed_demo
python manage.py runserver
```

**API base:** `http://localhost:8000`

### Frontend (React)

```powershell
cd C:\Users\USER\Desktop\yallastay
npm install
npm run dev
```

**App URL:** `http://localhost:3000` (or the port Vite shows)

**Presentation demo:** see **`DEMO_PRESENTATION.md`** in this repo (accounts, listings, reservation, suggested script).

### Connect Frontend → Backend

The frontend must point to the backend API:

- **If using Vite proxy:** Set `proxy` in `vite.config.js` to `http://localhost:8000`
- **If using env:** Set `VITE_API_URL=http://localhost:8000` in `.env` (or similar)

Check `vite.config.js` or the frontend `BackendConfig` page for the configured API URL.

---

## 2. Verification Checklist

Use this flow to confirm everything works.

### Step 1: API Root

1. Open `http://localhost:8000/` in a browser.
2. You should see: `{"message":"Yallastay API","status":"ok"}`

### Step 2: Core Data

1. Visit `http://localhost:8000/api/areas/`  -  should return Dubai areas (e.g. Dubai Marina, JLT).
2. Visit `http://localhost:8000/api/universities/`  -  should return universities.

If empty, run:
```bash
python manage.py seed_core
```

### Step 3: Register & Login (Frontend)

1. Open the frontend (e.g. `http://localhost:3000`, or the port Vite prints).
2. Go to **Sign Up** (`/signup`).
3. Register as **Student** (or Landlord/Realtor) with email + password.
4. You should be redirected after successful registration.
5. Go to **Login** (`/login`) and sign in.
6. You should see your profile/dashboard.

### Step 4: Browse Listings (Frontend)

1. From **Home** or **Search** (`/search`), browse listings.
2. If no listings: create one via **Add Property** (`/add-property`) as landlord/realtor, or run a seed if you have one.
3. Open a listing detail (`/property/:id`)  -  page loads without errors.

### Step 5: Favorites (Frontend)

1. While logged in, open a listing.
2. Use the **Add to Favorites** button (heart icon or similar).
3. Go to **Dashboard** or **Favorites**  -  your favorited listing appears.
4. Remove from favorites  -  it disappears.

### Step 6: Reservations (Frontend)

1. Go to **Reservations** or **My Reservations** in the dashboard.
2. Page loads (may show empty list)  -  no 500 error.
3. If you see “no such table: bookings_reservation”, run:
   ```bash
   python manage.py makemigrations bookings
   python manage.py migrate bookings
   ```

### Step 7: Lifestyle Plans (Frontend)

1. Go to **Services** (`/services`)  -  plans (Essential, Comfort, Complete) appear.
2. If empty or 500: run:
   ```bash
   python manage.py makemigrations lifestyle_services
   python manage.py migrate lifestyle_services
   python manage.py seed_lifestyle
   ```

**Subscribing (renter, paid pipeline):** the backend does **not** activate a subscription until payment succeeds.

1. The renter must have **UAE ID verification approved** (same gate as before).
2. They need a **reservation** on that listing (`confirmed` or `pending`).
3. **POST** `POST /api/lifestyle-subscriptions/` with JSON: `plan_id`, `reservation_id`, `start_date`, optional `end_date` (defaults to reservation end).
4. The response combines **checkout fields** with a `subscription` object:
   - `status` is `pending_payment` until paid.
   - `checkout_url`, `transaction_id`, `provider`, etc. (same shape as `POST /api/payments/initiate/`).
5. **Stripe:** redirect the browser to `checkout_url`, then Stripe sends the customer to your configured success URL; the backend webhook marks the payment completed and sets the subscription to `active`.
6. **Local stub (`PAYMENT_PROVIDER=stub`):** open or simulate `checkout_url`, then **POST** `POST /api/payments/webhook/stub/` with body `{ "transaction_id": "<transaction_id from step 4>" }` while **logged in as the payer** (JWT), or with header **`X-Stub-Webhook-Secret`** if the API has **`STUB_WEBHOOK_SECRET`** set, to simulate paid. The subscription becomes `active`.
7. **GET** `GET /api/lifestyle-subscriptions/` (or the detail URL) and show `status: active` and `latest_payment` before treating the user as subscribed.

Direct `POST /api/payments/initiate/` with `payment_type: "lifestyle"` also requires a `reservation_id` and creates a standalone lifestyle payment (link a subscription via the lifestyle checkout flow above for the normal renter path).

### Step 8: Backend Config Page (Frontend)

1. Go to **Backend Config** (`/backend`).
2. You should see API status and endpoint checks.
3. Use this page to verify the frontend can reach the backend.

### Step 9: Staff verification console (optional)

For **trusted Yallastay staff** who review broker/owner documents:

1. In **Django Admin**, set **`UserProfile.can_verify_documents`** for their user (or use **`is_staff`** / superuser). See **`docs/operations/staff-verification-console.md`** for the full model.
2. Sign in on the **same SPA origin** you use for the app (JWT lives in `localStorage` per origin; `staff.localhost` and `localhost` do not share a session).
3. Open the **staff verification app** (`yallastay_staff`, default **http://localhost:3001**) or use **Verify team** in the main app header when **`VITE_STAFF_APP_URL`** is set (new tab; sign in on the staff origin).
4. Demo account after **`seed_demo`:** `demo.verify@present.yallastay` / `DemoPresent2026!`.

API: **`GET /api/staff/verification/queue/`**, **`POST /api/staff/verification/realtors/<user_id>/decision/`**, **`POST /api/staff/verification/landlords/<user_id>/decision/`** (JWT). Curl matrix: **`MANUAL_TESTING.md`** → *Staff verification*.

---

## 3. Frontend Pages Reference

| Page | Path | Purpose |
|------|------|---------|
| Home | `/` | Hero, search, featured listings |
| Search | `/search` | Filter and browse listings |
| Property | `/property/:id` | Listing detail, favorite, contact |
| Login | `/login` | Sign in |
| Signup | `/signup` | Register (student, landlord, realtor) |
| Verify | `/verify` | UAE ID / university verification |
| Dashboard | `/dashboard` | User dashboard, favorites, reservations |
| Realtor Dashboard | `/realtor-dashboard` | My listings (realtors) |
| Services | `/services` | Lifestyle plans |
| Add Property | `/add-property` | Create listing (landlord/realtor) |
| For Partners | `/for-partners` | Landlord/realtor info |
| Backend Config | `/backend` | API status, connectivity check |
| Staff verification | `yallastay_staff` app (e.g. **http://localhost:3001**) | Queue: approve/reject brokers and owners (verification staff only); JWT on staff origin |

---

## 4. Backend API Quick Reference

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /` | No | API root |
| `POST /api/auth/register/` | No | Register |
| `POST /api/auth/login/` | No | Login |
| `GET /api/auth/me/` | Yes | Current user |
| `GET /api/areas/` | No | List areas |
| `GET /api/universities/` | No | List universities |
| `GET /api/listings/` | No | List listings |
| `GET /api/listings/:id/` | No | Listing detail |
| `POST /api/listings/` | Yes | Create listing |
| `GET /api/favorites/` | Yes | List favorites |
| `POST /api/favorites/` | Yes | Add favorite |
| `GET /api/reservations/` | Yes | List reservations |
| `GET /api/lifestyle-plans/` | Yes | List lifestyle plans |
| `GET /api/lifestyle-subscriptions/` | Yes | List subscriptions (includes `latest_payment`, `status`) |
| `POST /api/lifestyle-subscriptions/` | Yes | Start checkout: pending subscription + payment + checkout payload |
| `POST /api/payments/initiate/` | Yes | Start payment (rent, deposit, fee, lifestyle; lifestyle needs `reservation_id`) |
| `POST /api/payments/webhook/stub/` | JWT (payment owner) or shared secret header | Dev: mark stub payment completed (`transaction_id`) |
| `POST /api/payments/webhook/stripe/` | No | Stripe webhook (production) |
| `GET /api/viewings/` | Yes | List viewing requests |
| `GET /api/staff/verification/queue/` | Yes (verification staff) | Pending realtors/landlords + document checklist |
| `POST /api/staff/verification/realtors/<user_id>/decision/` | Yes (verification staff) | Body: `{"action":"approve"}` or `{"action":"reject","message":"..."}` |
| `POST /api/staff/verification/landlords/<user_id>/decision/` | Yes (verification staff) | Same body shape as realtor decision |

Full API details: see `MANUAL_TESTING.md`.

---

## 5. Common Issues

### “no such table: X”

Run migrations for the app that owns the table:

```bash
cd yallastay
python manage.py makemigrations <app_name>
python manage.py migrate
```

Examples: `bookings`, `lifestyle_services`, `listings`, etc.

### Frontend can’t reach backend (CORS / network)

- Ensure backend is running on `http://localhost:8000`.
- Check `vite.config.js` proxy or `VITE_API_URL`.
- Backend has `CORS_ALLOW_ALL_ORIGINS = True` in dev.

### Login redirect or token issues

- Clear cookies for `localhost`.
- Re-register if sessions were created with an old `SECRET_KEY`.
- Ensure `SECRET_KEY` is at least 32 characters.

### Empty areas/universities

```bash
python manage.py seed_core
```

### Empty lifestyle plans

```bash
python manage.py seed_lifestyle
```

### 401 on protected endpoints

- Ensure you’re sending `Authorization: Bearer <access_token>`.
- Frontend should store and send the token from login/register.

---

## 6. Run Tests

```bash
cd yallastay
python manage.py test
```

Run specific apps:

```bash
python manage.py test core accounts listings bookings lifestyle_services
```

---

## 7. Paths Reference

| What | Path |
|------|------|
| Backend project | `yallastay_backend/` |
| Django project (manage.py) | `yallastay_backend/yallastay/` |
| Frontend project | `yallastay/` (sibling to backend) |
| .env | `yallastay_backend/yallastay/.env` |
| Commands reference | `yallastay_backend/docs/COMMANDS.md` |
| Manual API testing | `yallastay_backend/docs/MANUAL_TESTING.md` |
| Staff verification console (ops) | `yallastay_backend/docs/operations/staff-verification-console.md` |

---

## 8. Suggested Full Verification Flow

1. Start backend → `python manage.py runserver`
2. Start frontend → `npm run dev`
3. Open frontend in browser
4. Register (student)
5. Login
6. Browse listings on Home and Search
7. Open a listing, add to favorites
8. Open Dashboard, confirm favorites
9. Open Reservations, confirm no 500
10. Open Services, confirm plans load
11. (Optional) With a reservation + approved UAE ID, subscribe via API: `POST /api/lifestyle-subscriptions/`, then complete payment (stub webhook or Stripe)
12. Open Backend Config, confirm API OK
13. (Optional) Register as landlord, add a listing, search for it

If all steps pass, frontend and backend are working together correctly.
