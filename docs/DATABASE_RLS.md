# PostgreSQL Row Level Security (RLS) - scope and role

| | |
|---|---|
| **Audience** | Technical stakeholders, security reviewers, DBAs |
| **Distribution** | **Client-facing** - suitable for technical due diligence under NDA. |
| **Disclaimer** | Describes intended database controls; **not** a substitute for application security review or legal compliance on its own. |

---

## Complementary controls (what RLS does not replace)

RLS is **PostgreSQL row access control** tied to `app.request_user_id`. It helps **limit which rows** a DB session can see or change **when policies apply**.

| Risk | How it is addressed |
|------|---------------------|
| **XSS (cross-site scripting)** | Browser-side; use sanitization, safe rendering, **CSP** (see [`SECURITY_CHECKLIST.md`](./SECURITY_CHECKLIST.md), [`security/defense-layers.md`](./security/defense-layers.md)). |
| **SQL injection** | Use the **ORM** and parameterized queries. |
| **Authorization on non-RLS tables** | **Application layer** - DRF permissions and object checks; **IDOR** reviews for tables without RLS. |
| **Business logic** | Enforced in application code. |

**Summary:** **Django/DRF** is the **primary** authorization layer; **RLS** is **defense in depth** on covered tables. See [`security/defense-layers.md`](./security/defense-layers.md).

---

## Current state

- **Local / default dev:** SQLite - RLS is **not** applied (migration is a no-op).
- **Production (PostgreSQL):** RLS is **enabled** on selected tables (see migration `core.0002_postgresql_row_level_security`). Policies use the session variable `app.request_user_id`, set each HTTP request by `PostgresRLSContextMiddleware`.

## How it works

1. **Middleware** (`core.middleware.postgres_rls.PostgresRLSContextMiddleware`) runs after `AuthenticationMiddleware`. For PostgreSQL it wraps the request in `transaction.atomic()` and runs `SET LOCAL app.request_user_id = '<user pk>'` (empty string when anonymous).
2. **Helper functions** in PostgreSQL (created by migration):
   - `app.request_user_id()` - parses the session variable to `bigint` or `NULL`.
   - `app.request_user_is_staff()` - true when the current setting’s user is staff (for Django admin / moderation).
3. **`FORCE ROW LEVEL SECURITY`** is used so policies apply even when the DB user owns the tables.
4. **Staff bypass:** Policies include `app.request_user_is_staff()` so Django admin sessions can read/write rows for support (controlled operational access).

## Tables covered

RLS is **not** on every table. Intentionally **excluded** (application-layer enforcement):

- **`accounts_user`** and other auth/session tables - admin and login flows.
- **`payments_payment`** and related payment rows - Stripe/webhook paths and idempotency; **API** enforces access.
- **`messaging_*`** - participant rules; **API** enforces access.
- **`esign_*`** - magic-link / token flows; **API** enforces access.

**Included:** `listings_listing`, `listings_favorite`, `bookings_reservation`, `bookings_viewingrequest`, `notifications_notification`, `reports_report`, `reviews_review`, `reviews_reviewresponse`, `roommates_roommateprofile`, `roommates_roommateinterest`.

## Operations & webhooks

- **Stripe / payment webhooks** call `set_request_user_id_for_rls(payment.user_id)` before saving the payment or running hooks so ORM access to **reservations/listings** inside hooks remains consistent with RLS policies.

## Operational override (emergency only)

Environment variable **`POSTGRES_RLS_ENABLED=false`** skips setting `app.request_user_id` in middleware. Use only for **break-glass** recovery; prefer fixing application paths or policies for normal operations.

## Inspect policies (PostgreSQL only)

```bash
python manage.py rls_status
```

## Deploying PostgreSQL from scratch

Run migrations as usual; `core.0002_postgresql_row_level_security` creates policies on PostgreSQL only.

If you already ran an **older** `0002` revision on a Postgres database before staff bypass was added, create a follow-up migration or re-apply policy SQL manually - do not delete applied migrations from history.

## Summary

| Layer | Role |
|--------|------|
| Django / DRF | Primary authorization - **required** |
| PostgreSQL RLS | Defense in depth on listed tables |
| SQLite (dev) | RLS migration skipped |

---

## Related docs

- [`SECURITY_CHECKLIST.md`](./SECURITY_CHECKLIST.md) - Security and privacy controls overview  
- [`security/defense-layers.md`](./security/defense-layers.md) - Layered defenses  
- [`security/auth-hardening-idor-rls.md`](./security/auth-hardening-idor-rls.md) - Auth rate limits, account flows, **IDOR review** for non-RLS routes  
- [`client/README.md`](./client/README.md) - Client document package index  
