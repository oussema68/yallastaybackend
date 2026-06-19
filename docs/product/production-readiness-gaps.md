# Production and contract readiness - what’s missing

| | |
|---|---|
| **Distribution** | **Internal - engineering / leadership.** Do **not** send to clients unless you produce a **summary** without raw gap tables. |
| **Use** | Prioritization and diligence prep; pair with [`../client/README.md`](../client/README.md) for client-safe exports. |

This is a **prioritized, scannable** view of gaps for **real production**, **serious commercial use**, and **external scrutiny** (customers, investors, or diligence). It does **not** replace the detailed feature-by-feature comparison in [`mvp-gap-analysis.md`](./mvp-gap-analysis.md); use that document for engineering depth.

**Related:** [`../diligence/evidence-preparation.md`](../diligence/evidence-preparation.md) (how to collect and present proof), [`../SECURITY_CHECKLIST.md`](../SECURITY_CHECKLIST.md), [`../DATABASE_RLS.md`](../DATABASE_RLS.md), [`../security/defense-layers.md`](../security/defense-layers.md) (XSS vs RLS, IDOR, CSP).

---

## How to read this

| Audience | Use this doc for | Use `mvp-gap-analysis` for |
|----------|------------------|----------------------------|
| Engineering / PM | Priority themes and “definition of done” | Concrete feature and code-level gaps |
| Security / compliance reviewer | High-level risk areas and cross-links | Security table §3 and checklist items |
| Sales / leadership | What blocks “enterprise” or large contracts | Technical nuance |

---

## 1. Summary: gap → owner → typical evidence

| Theme | What’s missing or weak | Primary owner | Evidence type (see diligence doc) |
|-------|-------------------------|---------------|-----------------------------------|
| **Secrets & config** | All secrets in env; no stub payment path exposed in prod | Eng / DevOps | Env policy, deploy checklist, network/firewall notes |
| **Transport & perimeter** | HSTS, auth endpoint throttling, WAF optional | Eng / Infra | Config screenshots, WAF rules summary |
| **Private data** | ID/lease docs not publicly readable; signed URLs or auth proxy | Eng | Access test results, architecture diagram |
| **Payments** | Live Stripe + webhooks; refunds/disputes/receipts as product expects | Eng + Finance/Ops | Stripe dashboard config, runbook, sample receipt flow |
| **E-sign** | MVP flow is audit + PDF, not necessarily UAE “qualified” or TDRA-aligned | Product + Legal | Legal memo, provider comparison if you switch |
| **Observability** | Sentry (or equivalent), uptime, alerting on 5xx and payment failures | Eng / Ops | Dashboard access, on-call policy |
| **Backups & DR** | DB and media backup/restore tested | Ops | Backup schedule, last restore test date |
| **Legal / privacy** | PDPL-aligned privacy policy, terms, subprocessors, retention | Legal + Product | Published URLs, subprocessors list, DPA template |
| **Operational trust** | Support SLAs, incident response, optional insurance/DPA for large deals | Ops + Legal | SLA doc, IR plan, certificates if applicable |

---

## 2. By area (short)

### Security and access

Aligned with [`../SECURITY_CHECKLIST.md`](../SECURITY_CHECKLIST.md) and [`../security/defense-layers.md`](../security/defense-layers.md): **XSS** (sanitization, CSP, safe rendering), **RLS** as defense-in-depth on selected tables only, **IDOR** on non-RLS apps, JWT storage risk, CORS in non-prod, stub webhook exposure, private media, admin hardening, frontend security headers.

**Still missing for “serious” production:** explicit **auth-route** rate limits, **documented** annual or per-release **IDOR/RLS review**, and a **single place** (runbook or checklist) that states production URL, Stripe mode, and “stub webhook disabled.”

### Payments and money

`PAYMENT_PROVIDER=stub` must never be used for real funds. In-app **refunds**, **dispute handling**, and **downloadable invoices** may lag user or B2B expectations - see [`mvp-gap-analysis.md`](./mvp-gap-analysis.md) §2.4.

### E-sign and documents

Current stack is **strong for internal MVP**; **legal weight** for specific UAE use cases requires counsel; commercial **DocuSign-class** or **TDRA-trusted** paths are a product/legal decision, not only engineering. Magic-link signing is **not** liveness or government ID at signing time.

### Operations and reliability

CI/CD, monitoring, backups, and staging/prod separation need **documented** expectations and owners - see [`mvp-gap-analysis.md`](./mvp-gap-analysis.md) §5. **Incident response** and **who is on-call** are often missing until the first outage - capture minimally in an internal doc.

### Compliance and commercial (non-code)

UAE rental/broker rules, **PDPL**, terms for each actor type, **subprocessors** - legal deliverables. Large contracts may ask for **DPAs**, **insurance**, **SLAs**, and **penetration test** or **questionnaire** responses; plan evidence as in [`../diligence/evidence-preparation.md`](../diligence/evidence-preparation.md).

---

## 3. “Done” bar (three levels)

| Level | Meaning |
|-------|--------|
| **Launch** | Matches [`mvp-gap-analysis.md`](./mvp-gap-analysis.md) §7 - HTTPS, secrets, CORS/hosts, Stripe live, private docs model, critical flows tested, basic monitoring. |
| **Scaled consumer** | CSP/headers, tighter throttles, backup/restore tested, privacy/terms live, support path defined. |
| **Enterprise / large contract** | Written subprocessors + DPA path, SLA or support commitments as offered, security questionnaire answers backed by artifacts, optional third-party pen test or SOC path if required. |

---

## 4. Maintenance

- **Owner:** Engineering + product; legal for compliance rows.  
- **Update when:** Launch geography changes, major flow ships, or after security/legal review.  
- **Do not duplicate:** Keep detailed lists in [`mvp-gap-analysis.md`](./mvp-gap-analysis.md); adjust this file when **priorities** or **commercial** expectations change.
