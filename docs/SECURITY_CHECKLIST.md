# Security and privacy - controls overview (Yallastay)

| | |
|---|---|
| **Audience** | Clients, partners, auditors, and external reviewers |
| **Distribution** | **Client-facing** - suitable to share under NDA; remove any environment-specific values before sending. |
| **Disclaimer** | Describes **intended** technical and operational practices. This is **not** a certification, penetration-test report, or legal warranty. Commitments in **contracts** prevail. |

---

## Executive summary

Yallastay is built as a **Django REST API** with a **React** web client, **JWT** authentication, and **role-based** access for tenants, property owners, and realtors. Production deployments use **HTTPS**, **restricted CORS**, **secrets in environment variables**, and **Stripe** for card payments with **signed webhooks**. User input is **sanitized** for plain-text; rich HTML rendering uses **safe patterns** on the frontend. **PostgreSQL Row Level Security** adds **defense in depth** on selected tables; see [`DATABASE_RLS.md`](./DATABASE_RLS.md) and [`security/defense-layers.md`](./security/defense-layers.md).

---

## 1. Controls implemented (baseline)

| Area | Practice |
|------|----------|
| **Transport & cookies** | HTTPS redirect, secure cookies, proxy-aware TLS settings in production. |
| **CORS** | Explicit allowed origins in production (not open wildcard). |
| **Authentication** | JWT access/refresh tokens; role checks on sensitive flows (UAE ID verification, listings, bookings, etc.). |
| **Payments** | Stripe Checkout; webhook requests verified with **`Stripe-Signature`**. Production uses live keys and webhook secrets from environment only. |
| **Input & output** | Plain-text sanitization on the backend; frontend uses safe rendering (React defaults) and sanitizer helpers where HTML is required. |
| **Database** | Django ORM for parameterized queries; RLS on selected PostgreSQL tables for row-level isolation. |
| **Administration** | Django admin protected by authentication; staff access follows least-privilege operational practice. |

---

## 2. Layered defenses (XSS, authorization, SQLi, RLS)

Cross-site scripting (**XSS**), **authorization**, and **SQL injection** are addressed at **different layers**. **RLS** protects **row access in PostgreSQL** for covered tables; it does **not** replace application-level permissions or browser-side protections. See [`security/defense-layers.md`](./security/defense-layers.md) for a concise matrix (XSS, IDOR, CSP, CSRF, webhooks).

---

## 3. Ongoing security hardening (typical roadmap)

| Theme | Direction |
|-------|-----------|
| **Session & tokens** | Short-lived access tokens, refresh rotation + blacklist; optional **Content-Security-Policy** on the static app; **httpOnly** cookies evaluated if auth architecture evolves. |
| **Abuse prevention** | Rate limits on authentication and verification; optional WAF or stricter limits at the edge. |
| **Transport hardening** | **HSTS** once HTTPS endpoints are stable. |
| **Private documents** | Signed URLs or authenticated download paths for ID and lease documents in production object storage. |
| **CSRF** | JSON APIs use JWT; **Django admin** and any session forms use CSRF protection as provided by Django. |
| **Secrets** | Rotation of Stripe, database, JWT signing keys, and webhook secrets on any incident; no secrets in source control. |
| **Dependencies** | Regular dependency updates and vulnerability monitoring (e.g. `pip audit`, automated PRs). |
| **Authorization reviews** | Periodic review of **object access by ID** (IDOR), especially for tables **not** covered by RLS; **messaging**, **payments**, and **e-sign** flows rely on application-layer checks. See [`security/auth-hardening-idor-rls.md`](./security/auth-hardening-idor-rls.md). |
| **Partner / B2B (server-to-server)** | Prefer **OAuth 2.0 client credentials** (token endpoint, scoped bearer access tokens, per-partner clients, rotation)-not a single long-lived shared API key without lifecycle policy. See [`platform/partner-api-authentication.md`](./platform/partner-api-authentication.md). |
| **Verification flows** | Rate-limited verification, password reset, and OTP; single-use, time-limited tokens. |
| **HTTP headers (frontend)** | CSP, frame-ancestors / X-Frame-Options, Referrer-Policy - typically configured at CDN or static host. |

---

## 4. Production deployment expectations

| Topic | Expectation |
|-------|-------------|
| **Configuration** | `ALLOWED_HOSTS`, CORS, and secrets set only via environment or secret manager. |
| **Payments** | Production uses **Stripe** with live credentials; **non-production** payment simulation endpoints are **not** exposed on public production URLs. |
| **Monitoring** | Error tracking and alerting appropriate to production (e.g. 5xx rates, payment webhook failures). |

---

## 5. Related documents

| Document | Purpose |
|----------|---------|
| [`security/defense-layers.md`](./security/defense-layers.md) | Layered model: XSS, RLS, IDOR, CSP, webhooks. |
| [`DATABASE_RLS.md`](./DATABASE_RLS.md) | PostgreSQL RLS scope and operations. |
| [`client/README.md`](./client/README.md) | Which files to send to clients and what to keep internal. |
| [`operations/happy-path-e2e-checklist.md`](./operations/happy-path-e2e-checklist.md) | Release happy path (manual checklist + backend chain test). |
| [`operations/monitoring-and-backups.md`](./operations/monitoring-and-backups.md) | Sentry, uptime probes, 5xx/webhook alerts, backup restore drill. |

**Internal engineering backlog** (detailed gaps, pre-launch checklists) - maintain separately if you need a raw ticket list; the documents above are the **client-safe** overview.
