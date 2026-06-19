# Auth hardening, IDOR review, and RLS boundaries

| | |
|---|---|
| **Audience** | Engineers, security reviewers |
| **Purpose** | Document stricter rate limits on auth endpoints, how account flows work in staging/production, and where **RLS does not apply** so **IDOR** reviews stay explicit. |

---

## Auth endpoint rate limits (DRF `ScopedRateThrottle`)

Login, register, refresh, password reset, verify-email, and resend-verification views set **`throttle_classes = [ScopedRateThrottle]`** only (they do **not** use the project default `AnonRateThrottle` + `UserRateThrottle`). Other API routes still use the global defaults in `REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"]`.

| Scope | Default (non-test) | Env override |
|-------|-------------------|--------------|
| `auth_login` | 5/minute | `API_THROTTLE_AUTH_LOGIN` |
| `auth_register` | 5/minute | `API_THROTTLE_AUTH_REGISTER` |
| `auth_refresh` | 30/minute | `API_THROTTLE_AUTH_REFRESH` |
| `auth_password_reset` | 5/hour | `API_THROTTLE_AUTH_PASSWORD_RESET` |
| `auth_password_reset_confirm` | 10/minute | `API_THROTTLE_AUTH_PASSWORD_RESET_CONFIRM` |
| `auth_verify_email` | 60/minute | `API_THROTTLE_AUTH_VERIFY_EMAIL` |
| `auth_resend_verification` | 5/hour | `API_THROTTLE_AUTH_RESEND_VERIFICATION` |

Tests use very high caps unless overridden. Tune per environment via env vars.

**Automated 429 check:** `accounts.tests.test_auth_throttles.AuthLoginThrottleBurstTests` asserts that the third failed login in a row returns HTTP **429** when `auth_login` is temporarily set to **`2/minute`**. It patches `rest_framework.throttling.SimpleRateThrottle.THROTTLE_RATES` for that run only, because DRF binds that mapping at import time; `override_settings(REST_FRAMEWORK=…)` alone does not change the live throttle dict on the class.

---

## Password reset API

| Method | Path | Notes |
|--------|------|--------|
| POST | `/api/auth/password-reset/` | Body: `{ "email": "..." }`. **Always** returns the same `detail` message (does not reveal whether the email is registered). |
| POST | `/api/auth/password-reset/confirm/` | Body: `{ "uid", "token", "new_password" }` (same `uid`/`token` as in the email link). |

Email links use **`FRONTEND_URL`** (see below). The backend does not host the reset form; the SPA reads `uid` and `token` from the query string and POSTs to confirm.

---

## Email verification and staging / production-like checks

1. **`DEFAULT_FROM_EMAIL`** (and real SMTP or provider) must be set so messages are delivered, not only queued.
2. **`FRONTEND_URL`**: used for password reset links (`/reset-password?uid=...&token=...`) and for email verification redirect success (`/?email_verified=1`).
3. **`BACKEND_URL`**: used for API links in the verification email (`/api/auth/verify-email/?uid=...&token=...`).

**Suggested staging checklist**

- [ ] Register → receive `email_verification` → open link → profile shows `is_email_verified`.
- [ ] Forgot password → receive `password_reset` → SPA `/reset-password` submits confirm → login with new password.
- [ ] Resend verification (authenticated) respects `auth_resend_verification` throttle.

---

## IDOR / RLS: routes and tables **without** RLS

PostgreSQL RLS is **defense in depth** on a subset of tables. It does **not** replace application authorization. See [`../DATABASE_RLS.md`](../DATABASE_RLS.md) for which tables have policies.

**Non-RLS areas (application-level authorization required; review for IDOR)**

| Area | Why RLS may not apply | Review focus |
|------|------------------------|--------------|
| `accounts_user` / auth | Login, sessions, admin | Object ownership on `/api/auth/me/`, profile updates, public profile by `pk`. |
| `documents_document` | Document uploads | **Owner checks** on list/detail/delete; future private storage must not rely on public `/media/` URLs. |
| `payments_*` | Webhooks, Stripe | Idempotency, user on payment row, webhook authenticity. |
| `messaging_*` | Threads | Participant membership on every message/thread access. |
| `esign_*` | Magic links / tokens | Token scope, session ownership, lease party checks. |

**Actionable review:** For each endpoint touching these tables, confirm **permission classes**, **queryset scoping**, and **get_object_or_404** patterns so users cannot read or mutate another user’s rows by ID.

---

## Related

- [`../SECURITY_CHECKLIST.md`](../SECURITY_CHECKLIST.md)
- [`../DATABASE_RLS.md`](../DATABASE_RLS.md)
- [`defense-layers.md`](./defense-layers.md)
