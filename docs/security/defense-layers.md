# Security architecture - layered defenses (XSS, authorization, RLS, and related controls)

| | |
|---|---|
| **Audience** | Clients, partners, security reviewers, and engineering |
| **Distribution** | **Client-facing** - suitable to share under NDA. |
| **Disclaimer** | Describes intended design; **not** a certification or penetration-test result. |

This document explains how **browser**, **application**, and **database** layers work together. It complements [`../SECURITY_CHECKLIST.md`](../SECURITY_CHECKLIST.md) and [`../DATABASE_RLS.md`](../DATABASE_RLS.md).

---

## 1. Layered model (who does what)

| Concern | Primary defense in this stack | RLS helps? | Notes |
|--------|--------------------------------|------------|--------|
| **Cross-site scripting (XSS)** | Sanitize **on write** (backend), safe rendering **on read** (frontend: avoid raw HTML; use a sanitizer when HTML is required); **CSP** on the static host | **No** - RLS is database row access, not browser execution | Token theft via XSS is mitigated with short-lived tokens, CSP, and secure token handling. |
| **SQL injection** | Django ORM / parameterized queries; avoid raw SQL with untrusted input | **No** (policies are not the main SQLi control) | Review any ad-hoc raw SQL. |
| **Insecure direct object reference (IDOR)** | DRF permissions, querysets scoped to `request.user`; review “fetch by id” on all apps | **Partially** - only on **RLS-enabled** tables (see [`DATABASE_RLS.md`](../DATABASE_RLS.md)) | **`messaging_*`, `payments_*`, `esign_*`** are **not** RLS-covered; application layer is mandatory. |
| **Broken access control** | Same as IDOR + role checks (tenant/landlord/realtor) | **Partially** | Staff bypass in RLS - operational access for support is controlled. |
| **CSRF** | JWT for API JSON; **CSRF** for Django **admin** and session forms | N/A | See checklist. |
| **Webhooks & signed callbacks** | Verify webhook signatures (e.g. Stripe); restrict outbound URLs for any generic URL-fetch features | N/A | Production **only** uses authenticated, verified payment webhooks. |
| **Row-level data isolation (tenant A vs B)** | PostgreSQL **RLS** on selected tables + `app.request_user_id` | **Yes** - for those tables | Local SQLite development does not apply RLS; production validation uses PostgreSQL. |

---

## 2. XSS - practices

1. **Treat user input as untrusted** for bios, messages, listing text, and notes.
2. **Backend:** Plain-text paths use sanitization helpers so stored data matches intended format.
3. **Frontend:** Prefer **React text nodes** (default escaping). If HTML is required, use a **sanitizer** with a strict allow-list.
4. **CSP (Content-Security-Policy):** Reduces impact of script injection; configured at the **CDN / static host** where applicable.
5. **Tokens:** Combine short-lived access tokens, refresh rotation, and CSP as part of a defense-in-depth strategy.

---

## 3. RLS - practices

1. **Application authorization is primary:** Django views and DRF permissions must scope data correctly.
2. **RLS adds defense in depth** on **listed** PostgreSQL tables; **excluded** domains (**payments**, **messaging**, **e-sign**, etc.) rely on **explicit** API checks.
3. **Development vs production:** SQLite skips RLS migrations - validate behavior on **staging PostgreSQL** for RLS-sensitive flows.
4. **Webhooks:** Payment flows set the RLS context where required so legitimate server-side work remains consistent with policies.

---

## 4. Other categories

| Category | Direction |
|----------|-----------|
| **Rate limiting / abuse** | Auth endpoints, verification, OTP, webhooks |
| **Secrets** | Environment-only storage; rotation on incident |
| **Private files** | Authenticated or signed access for documents |
| **Headers** | HSTS, frame-ancestors, Referrer-Policy as appropriate |
| **Dependencies** | Ongoing updates and vulnerability monitoring |

---

## 5. Evidence for questionnaires

For security questionnaires, map each control to **artifacts** (config summaries, policy excerpts, review dates). Internal assembly guidance: [`../diligence/evidence-preparation.md`](../diligence/evidence-preparation.md) (**internal**).

---

## Related docs

- [`../SECURITY_CHECKLIST.md`](../SECURITY_CHECKLIST.md) - Controls overview  
- [`../DATABASE_RLS.md`](../DATABASE_RLS.md) - PostgreSQL RLS scope and operations  
- [`../client/README.md`](../client/README.md) - Client document package index  
