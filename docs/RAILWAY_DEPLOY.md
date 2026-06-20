# Railway deploy checklist (backend + frontend)

Use this in order. Every signup/JWT error like `token_blacklist_outstandingtoken does not exist` means **migrations did not finish** on Postgres.

---

## Phase 0 — GitHub

1. Push **backend** (`yallastay_backend`) with latest:
   - `psycopg[binary]` in `requirements.txt`
   - `core/0002` RLS migration dependency fix
   - Register `on_commit` email fix
   - Resend SMTP settings in `base.py`
   - `railway.toml` + `Procfile` (repo root **or** `yallastay/` only — see Phase 1)
2. Push **frontend** (`yallastay`) with signup using `auth.register()` (not hardcoded `/api/...`).

---

## Phase 1 — Railway project

1. **New project** (or existing) + add **PostgreSQL** plugin.
2. **API service** — connect backend GitHub repo.

### Root directory (pick ONE — do not mix)

| Setting | Use which config |
|--------|-------------------|
| **Root Directory = `yallastay`** | `yallastay/Procfile`, `yallastay/railway.toml` |
| **Root Directory = empty (repo root)** | repo-root `Procfile`, repo-root `railway.toml` (`cd yallastay && ...`) |

3. Link Postgres to API service: **`DATABASE_URL`** (reference variable from Postgres service).

---

## Phase 2 — Backend environment variables

Replace hostnames with your real Railway domains.

```bash
DJANGO_ENV=production
SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_urlsafe(40))">

ALLOWED_HOSTS=yallastaybackend-production.up.railway.app
BACKEND_URL=https://yallastaybackend-production.up.railway.app
FRONTEND_URL=https://YOUR-FRONTEND.up.railway.app
CORS_ALLOWED_ORIGINS=https://YOUR-FRONTEND.up.railway.app

PAYMENT_PROVIDER=stub

# Resend (demo@yallastay.ae) — see RESEND_SETUP.md
DEFAULT_FROM_EMAIL=demo@yallastay.ae
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=resend
RESEND_API_KEY=re_your_key_here
```

`DATABASE_URL` comes from Postgres plugin (do not paste manually unless needed).

---

## Phase 3 — Deploy backend & verify release

1. **Deploy** API service.
2. Open deploy logs → find **Release** section. Must show:
   - `Applying ...` migrations (many apps)
   - `No migrations to apply` or all apps `[X]`
   - `X static files copied to .../staticfiles`
3. If Release is **missing** or **failed** → fix Root Directory (Phase 1), redeploy.

### Manual fix (do this now if signup still breaks)

Railway → API service → **Shell**:

```bash
# If root dir is repo root:
cd yallastay

python manage.py migrate --noinput
python manage.py migrate --check
python manage.py showmigrations
python manage.py collectstatic --noinput
```

**`showmigrations`**: every line must start with `[X]`. Any `[ ]` = still broken.

Apps that must be applied (includes JWT blacklist):

- `token_blacklist` (creates `token_blacklist_outstandingtoken` — required for signup JWT)
- `emails` (verification templates)
- `core` through `0002_postgresql_row_level_security`
- all other apps

If `migrate` errors on `core.0002` → pull latest backend (RLS dependency fix), run `migrate` again.

If DB is corrupted from half-applied migrations → Postgres service → **reset volume** (destroys data) → redeploy → `migrate` again.

---

## Phase 4 — Smoke test API

```powershell
$B = "https://yallastaybackend-production.up.railway.app"
Invoke-WebRequest -Uri "$B/api/areas/" -UseBasicParsing
```

Expect **200**. If **400 DisallowedHost** → fix `ALLOWED_HOSTS`.

---

## Phase 5 — Frontend service

1. Connect frontend GitHub repo.
2. **Build command:** `npm ci && npm run build`
3. **Start command:** `npx serve -s dist -l $PORT`
4. **Build variable (required):**

```bash
VITE_API_URL=https://yallastaybackend-production.up.railway.app/api
```

5. Generate public domain for SPA.
6. Update backend **`FRONTEND_URL`** and **`CORS_ALLOWED_ORIGINS`** to SPA URL → redeploy API.

---

## Phase 6 — End-to-end test

1. Open **frontend** URL (not API URL).
2. Sign up → expect **201** (not 405, not 500).
3. Check Resend dashboard for verification email from `demo@yallastay.ae`.
4. Log in, create listings manually (no `bootstrap_demo` required).
5. Optional: `python manage.py seed_core` in shell for area/university dropdowns only.

---

## Error → fix quick reference

| Error | Fix |
|-------|-----|
| `psycopg2 or psycopg module` | Push `requirements.txt` with `psycopg[binary]` |
| `DisallowedHost` | `ALLOWED_HOSTS` = API hostname only |
| CORS in browser | `CORS_ALLOWED_ORIGINS` = SPA URL |
| `405` on `/api/auth/register/` | Frontend `VITE_API_URL` = absolute API `/api` |
| `token_blacklist_outstandingtoken does not exist` | Run `migrate` until all `[X]` |
| `emails_emailtemplate does not exist` | Same — finish `emails` migrations |
| `No directory at .../staticfiles/` | Release/collectstatic never ran — Phase 1 + 3 |
| `transaction is aborted` | Push register `on_commit` fix + migrate |

---

## Optional

- **Resend domain:** verify `yallastay.ae`, sender `demo@yallastay.ae` — [`RESEND_SETUP.md`](RESEND_SETUP.md)
- **Demo presentation env block:** [`DEMO_PRESENTATION.md`](DEMO_PRESENTATION.md)
