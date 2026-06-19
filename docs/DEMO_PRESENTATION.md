# Demo presentation checklist

Use this for **live demos** of **Yallastay** (backend + React frontend).  
Repos: `yallastay_backend` (Django) and sibling **`yallastay`** (Vite on port **3000** locally). **Gap analysis & “what’s still weak”:** [`DEMO_GAP_REVIEW.md`](DEMO_GAP_REVIEW.md).

## Deploy on Railway (generated `*.up.railway.app` domains)

Use **two** Railway services (or one API + static host): **Django API** and **static SPA** from `npm run build`.

### Railway service layout

| Service | Root / artifact | Notes |
|---------|-----------------|--------|
| **API** | Repo folder **`yallastay`** (contains `manage.py`) | **[`Procfile`](yallastay/Procfile)** defines **`web`** (**`gunicorn`**). **[`railway.toml`](yallastay/railway.toml)** defines **`releaseCommand`** (`migrate` + `collectstatic`). Dependency: **`gunicorn`** in [`requirements.txt`](requirements.txt). |
| **SPA** | Frontend **`dist/`** after production build | Build must set **`VITE_API_URL`** (see below). Use env + **`npm ci && npm run build`** (no wrapper scripts). |

### Copy-paste environment (replace hostnames)

**API: Variables**

```bash
DJANGO_ENV=production
SECRET_KEY=<paste-strong-secret>
ALLOWED_HOSTS=your-api-xxxx.up.railway.app
FRONTEND_URL=https://your-spa-xxxx.up.railway.app
CORS_ALLOWED_ORIGINS=https://your-spa-xxxx.up.railway.app
PAYMENT_PROVIDER=stub
```

Add **`DATABASE_URL`** / use Railway’s Postgres plugin (**`DATABASE_PRIVATE_URL`** is also supported). Optional explicit public API base:

```bash
BACKEND_URL=https://your-api-xxxx.up.railway.app
```

If **`BACKEND_URL`** is omitted, production builds it from the **first** **`ALLOWED_HOSTS`** entry; that entry must match the browser-facing API hostname.

**SPA (build-time only)** (Railway static **build** env, or local before upload):

```bash
VITE_API_URL=https://your-api-xxxx.up.railway.app/api
```

Then:

```bash
npm ci && npm run build
```

Windows (PowerShell), from the frontend repo root:

```powershell
$env:VITE_API_URL = "https://your-api-xxxx.up.railway.app/api"
npm ci; npm run build
```

**Failure modes:** SPA built with **`VITE_API_URL=/api`** on split hosts → requests hit the wrong origin (404). **`CORS_ALLOWED_ORIGINS`** missing the SPA → browser blocks API calls. **`ALLOWED_HOSTS`** mismatch → Django **DisallowedHost**.

### How Django picks “production”

`yallastay/settings/__init__.py` loads **`prod`** when **`DJANGO_ENV=prod`** / **`production`**, **or** when Railway injects **`RAILWAY_ENVIRONMENT_*`**, **or** when **`DATABASE_URL` / `DATABASE_PRIVATE_URL`** is set (typical Postgres plugin).

Production **requires**:

| Variable | Notes |
|----------|--------|
| **`FRONTEND_URL`** | Full origin your browser opens for the React app, e.g. `https://frontend-xxxx.up.railway.app`. Used for password-reset links, Stripe returns, etc. (`prod.py` errors if missing.) |
| **`ALLOWED_HOSTS`** | Hostnames **only**, comma-separated: `backend-xxxx.up.railway.app` (your API Railway hostname). |
| **`CORS_ALLOWED_ORIGINS`** | Same-origin browser rule: must include the SPA URL, e.g. `https://frontend-xxxx.up.railway.app`. **`http://localhost:3000` alone is not enough** for the live site. |
| **`DATABASE_URL`** or **`DATABASE_PRIVATE_URL`** | Railway Postgres (required by `prod.py`). |
| **`SECRET_KEY`** | Strong random secret. |

Optional:

| Variable | Notes |
|----------|--------|
| **`BACKEND_URL`** | Public API base `https://backend-xxxx.up.railway.app`. If omitted, prod builds it from the **first** `ALLOWED_HOSTS` entry (must match your public Railway URL). |

Production SPA build steps are under **SPA (build-time only)** above (absolute **`VITE_API_URL`** + **`npm run build`**). Deploy **`dist/`** to static hosting.

### First deploy on Postgres

Release phase (**`migrate`** + **`collectstatic`**) is set in [`yallastay/railway.toml`](yallastay/railway.toml); the running server uses **`web`** from [`yallastay/Procfile`](yallastay/Procfile). Seed demo data **once** from Railway **shell** / one-off job with working directory **`yallastay`** (same folder as `manage.py`):

```bash
python manage.py bootstrap_demo
```

If migrations already ran in release and you only need seeds:

```bash
python manage.py bootstrap_demo --skip-migrate
```

From a full clone (repo root **`yallastay_backend`**):

```bash
cd yallastay && python manage.py bootstrap_demo
```

Re-running seeds may hit unique constraints; use a **fresh Postgres volume** if you need a clean slate.

### Pre-investor smoke (public API)

Run ~15 minutes before the meeting; treat failures as blockers.

**Option A (CI):** Add repository variable **`SMOKE_API_BASE`** = `https://your-api-xxxx.up.railway.app` (no trailing slash). Pushes and PRs then run **`.github/workflows/ci.yml`** checks against that URL when the variable is set.

**Option B (manual, Unix shell):**

```bash
BASE=https://your-api-xxxx.up.railway.app
curl -fsS "$BASE/api/areas/" >/dev/null && curl -fsS "$BASE/api/universities/" >/dev/null && echo OK
```

**Option C (manual, PowerShell):**

```powershell
$B = "https://your-api-xxxx.up.railway.app"
Invoke-WebRequest -Uri "$B/api/areas/" -UseBasicParsing | Out-Null
Invoke-WebRequest -Uri "$B/api/universities/" -UseBasicParsing | Out-Null
Write-Host OK
```

Then in the browser: open the SPA → Backend/connectivity (**`/api/areas/`**) → login **tenant** → **`[Demo]`** listing → **stub payment** → simulate paid.

### Investor demo: frozen presenter checklist

Use **only** flows you verified in the smoke run immediately beforehand.

- **Payments:** **`PAYMENT_PROVIDER=stub`** only; use in-app stub completion. Do **not** switch to Stripe unless keys and return URLs are tested.
- **Accounts:** all rows in **Demo accounts** below share **`DemoPresent2026!`** (`demo.tenant@…`, `demo.landlord@…`, `demo.team@…`, `demo.verify@…`, `demo.realtor@…`, `demo.realtor-pending@…`, `demo.owner-pending@…`).
- **Avoid:** password reset, magic-link email, or any flow that needs **SMTP** unless it is configured and tested.
- **Warm-up:** load SPA and log in once ~10 minutes before investors (Railway cold start).

### Demo-specific notes online

- **`PAYMENT_PROVIDER=stub`** works if users can reach **`POST /api/payments/webhook/stub/`** (same API origin as checkout) while **logged in as the payer** or with **`X-Stub-Webhook-Secret`** when configured; fine for internal demos.
- **Uploaded media** on Railway’s ephemeral disk **can disappear on redeploy** unless you configure **S3 / compatible storage** (`USE_S3_MEDIA` in `.env.example`).
- **HTTPS**: prod forces HTTPS on `FRONTEND_URL` / `BACKEND_URL` normalization.

---

## Before you present (local)

1. **Backend env:** From `yallastay/` (folder with `manage.py`), copy `.env.example` → `.env`, set at least `SECRET_KEY`. For demos use **`PAYMENT_PROVIDER=stub`** (default in `.env.example`).
2. **Frontend env:** In `yallastay/`, copy `.env.example` → `.env`. Keep **`VITE_API_URL=/api`** so the Vite dev proxy hits Django on **:8000**.
3. **Two terminals**
   - Backend: migrate, seed, runserver (commands below).
   - Frontend: `npm install` once, then `npm run dev` → open **http://localhost:3000**.

## One-shot backend setup

From **`yallastay_backend`** (activate your venv first if you use `venv/`):

```powershell
.\venv\Scripts\Activate.ps1   # optional
cd yallastay
python manage.py bootstrap_demo
python manage.py runserver
```

Same idea on macOS/Linux: `cd yallastay && python manage.py bootstrap_demo && python manage.py runserver`.

(`bootstrap_demo` runs **`migrate`** plus **`seed_core`**, **`seed_lifestyle`**, **`seed_demo`**; use **`--skip-migrate`** only if you already migrated.)

## Frontend

```powershell
cd C:\Users\USER\Desktop\yallastay
npm install
npm run dev
```

App: **http://localhost:3000** · API (direct): **http://localhost:8000**

## Demo accounts (`seed_demo`)

| Role | Email | Password |
|------|--------|----------|
| Landlord (staff-approved) | `demo.landlord@present.yallastay` | `DemoPresent2026!` |
| Tenant (UAE approved) | `demo.tenant@present.yallastay` | `DemoPresent2026!` |
| Lifestyle team (Services overview table) | `demo.team@present.yallastay` | `DemoPresent2026!` |
| Verification console (brokers & owners) | `demo.verify@present.yallastay` | `DemoPresent2026!` |
| Realtor (approved; broker-listed **[Demo]** listing) | `demo.realtor@present.yallastay` | `DemoPresent2026!` |
| Realtor (pending — appears in staff queue) | `demo.realtor-pending@present.yallastay` | `DemoPresent2026!` |
| Owner (pending — appears in staff queue) | `demo.owner-pending@present.yallastay` | `DemoPresent2026!` |

Open the **staff verification** app (**`yallastay_staff`**, default **http://localhost:3001**) and sign in there (JWT is per origin). In the main marketplace, set **`VITE_STAFF_APP_URL=http://localhost:3001`** so **Verify team** appears for eligible users. **Operations runbook:** [`operations/staff-verification-console.md`](operations/staff-verification-console.md).

Listings are titled **`[Demo] …`** (including **`[Demo] Marina · broker-listed studio`** by the approved realtor). The tenant has a **confirmed** reservation on the primary Marina **[Demo]** listing for **lifestyle** and **rent / lease e-sign** demos. **`seed_demo`** also creates a **Messages** thread on that listing (landlord → tenant).

## Suggested flow (12–18 min)

1. **Guest:** Home, Search, open a **[Demo]** listing (landlord or broker-listed).
2. **Login as tenant:** Dashboard, **Messages** (seeded thread on the Marina demo listing), **Verify** (already approved in seed).
3. **Services** (`/services`): Plans; subscribe with **stub checkout** → complete payment in **Stub payment** modal → subscription **active** → **Configure your benefits** (gym / cleaning window). Ensure `seed_lifestyle` ran so partner gyms exist.
4. **Login as landlord:** My listings / add property (optional). Three seeded **[Demo]** listings exist (two landlord, one broker).
5. **Login as `demo.realtor` (optional):** Realtor dashboard / listings — shows **staff-approved** broker path and Trakheesi-style field on the broker **[Demo]** listing.
6. **Login as demo.team:** Services page **team** block: all subscriptions overview (read-only).
7. **Staff app (`yallastay_staff`, e.g. localhost:3001):** sign in as **`demo.verify`** — queue includes **at least** `demo.realtor-pending@…` and `demo.owner-pending@…` (document checklist; approve/reject same as Django Admin). **Tip:** if you **approve** them during a rehearsal, run **`bootstrap_demo`** again (or re-run **`seed_demo`**) before the next demo to restore pending rows.
8. **Optional — Rent (stub) → lease e-sign (2–3 min):** As **tenant**, open **Reservations** / payments for the **confirmed** Marina reservation → start **rent** checkout (**stub**) → complete payment (in-app stub UI while logged in, or `POST /api/payments/webhook/stub/` with `transaction_id` plus JWT or **`X-Stub-Webhook-Secret`** if the API enforces it). Then open **lease signing** from the dashboard / notification link, or follow magic-link URLs from **`GET /api/esign/sessions/`** (renter signs first; see [`esign/setup.md`](esign/setup.md)). Automated API proof: `python manage.py test core.tests.test_happy_path_chain`. Full manual ticks: [`operations/happy-path-e2e-checklist.md`](operations/happy-path-e2e-checklist.md).
9. **Backend sanity:** `/backend` page or `GET http://localhost:8000/` → `{"status":"ok"}`.

## Payments (stub)

With **`PAYMENT_PROVIDER=stub`**, after checkout starts, use the app’s **stub payment** UI (same session as checkout) or POST:

`POST /api/payments/webhook/stub/` with `{ "transaction_id": "<from checkout response>" }` and **JWT** (payment owner) or **`X-Stub-Webhook-Secret`** when **`STUB_WEBHOOK_SECRET`** is set on the API.

## Fresh database

If you need a clean slate: delete `db.sqlite3` (if using SQLite), then **`python manage.py bootstrap_demo`** again.

## Optional polish

- **Demo gaps & what’s still weak:** [`DEMO_GAP_REVIEW.md`](DEMO_GAP_REVIEW.md)
- **Screen recording / Playwright shots** as a fallback if live Railway lags: [`SCREENSHOTS_PLAYWRIGHT.md`](SCREENSHOTS_PLAYWRIGHT.md)
- Full usage & troubleshooting: **`USAGE_GUIDE.md`**
- Deployed API smoke in CI: set repo variable **`SMOKE_API_BASE`** → **`.github/workflows/ci.yml`**
- Local or Railway demo DB: **`python manage.py bootstrap_demo`** from **`yallastay/`** (see sections above)

### Note on console email output

The first time `seed_demo` approves the demo tenant’s UAE record, Django may print an **approval email** to the console (dev backend). That’s normal.
