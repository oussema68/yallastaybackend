# Evidence preparation - how to show proof (diligence, security reviews, large contracts)

| | |
|---|---|
| **Distribution** | **Internal  - ** how *your team* assembles diligence packs. **Do not** send this playbook to clients; send the **artifacts** it helps you build. |
| **Disclaimer** | Not legal or certification advice. |

This document describes **how to turn claims into evidence**: what to collect, how to organize it, and what reviewers typically accept.

**Related:** [`../product/production-readiness-gaps.md`](../product/production-readiness-gaps.md) (what is missing), [`../product/mvp-gap-analysis.md`](../product/mvp-gap-analysis.md) (technical gaps), [`../SECURITY_CHECKLIST.md`](../SECURITY_CHECKLIST.md), [`../DATABASE_RLS.md`](../DATABASE_RLS.md), [`../security/defense-layers.md`](../security/defense-layers.md) (XSS, RLS, layered controls).

---

## 1. Principles

| Principle | In practice |
|-----------|-------------|
| **Claim + artifact** | Every statement in a deck or questionnaire should point to a **named artifact** (doc, ticket, log policy, config export, test output). |
| **Dated and versioned** | Use **dates** on reviews (“RLS scope reviewed 2026-03-01”) and **version** policies (privacy policy v3). |
| **Reproducible** | Prefer **repeatable** checks (e.g. “run `pip audit` monthly”) over one-off screenshots that go stale. |
| **Least sensitive** | Share **summaries** and **redacted** configs in external packs; raw secrets never leave secure stores. |

---

## 2. Suggested evidence pack layout

Use a **single parent folder** (or secure workspace) per review round:

```text
evidence-YYYY-MM-DD/
  README.md                 # index: what each subfolder proves
  01-company-legal/         # terms, privacy, subprocessors, DPAs (as applicable)
  02-security-config/       # redacted env checklist, HSTS/CORS notes, WAF summary
  03-access-control/        # RLS scope doc, IDOR review notes, role matrix
  04-payments/              # Stripe mode proof, webhook setup, refund/dispute process
  05-operations/            # monitoring dashboards, on-call, backup/restore evidence
  06-testing/               # test strategy, CI output summary, smoke/E2E results
  07-incident-privacy/      # IR outline, breach notification steps, retention summary
```

Adjust names to match the **customer’s questionnaire**; duplicate pointers in `README.md` rather than duplicating files.

---

## 3. Gap → evidence mapping (quick reference)

| Topic | What reviewers ask | Typical evidence |
|-------|-------------------|------------------|
| **HTTPS / transport** | Is traffic encrypted? | Prod URL, HSTS config summary, certificate transparency optional |
| **Secrets** | How are keys stored? | “No secrets in repo” attestation, secret manager or env-injection description |
| **Authentication** | Token handling, session risks | Architecture one-pager, JWT/refresh policy, link to [`SECURITY_CHECKLIST.md`](../SECURITY_CHECKLIST.md) §1 |
| **Authorization** | IDOR, tenant isolation | RLS doc [`DATABASE_RLS.md`](../DATABASE_RLS.md), [`defense-layers.md`](../security/defense-layers.md) (what RLS does not cover), last queryset/review date, sample test cases |
| **XSS / content safety** | Untrusted user HTML, CSP | Sanitization approach (backend + frontend), CSP header summary or CDN config, avoid raw HTML in app review notes |
| **Payments** | PCI scope, webhooks | Stripe responsibility matrix (Stripe handles card data), webhook signature verification note, live vs test separation |
| **Private files** | Document access | Diagram: browser → API → storage; signed URL or auth proxy; negative test “unauthenticated cannot fetch” |
| **Logging / PII** | Data in logs | Log scrubbing policy, “no card numbers in logs” rule, retention |
| **Backups** | RPO/RTO | Schedule, last restore test, who runs it |
| **Incidents** | Response | Short IR plan: roles, comms, escalation; optional tabletop date |
| **Privacy / law** | PDPL, subprocessors | Published privacy policy URL, subprocessors table, data map high level |

---

## 4. Security questionnaire workflow

1. **Import** the customer’s spreadsheet or portal questions into a working doc.  
2. **Map** each row to an owner (eng, infra, legal).  
3. **Answer** with **short text** + **pointer** to artifact in the pack (`02-security-config/HSTS-notes.md`).  
4. **Review** internally for over-claims; replace “we are secure” with “we implement X per attached config summary.”  
5. **Version** the pack (`evidence-2026-03-28-v2`) if questions change.

---

## 5. A practical 90-day sequence (example)

Rough order for a team moving toward **stronger** external readiness - overlap as needed.

| Phase | Focus | Output |
|-------|--------|--------|
| **Days 1-30** | Production baseline | Checklist complete: HTTPS, secrets, Stripe live, stub off, private media model, monitoring alerts |
| **Days 31-60** | Documentation | Subprocessors list, privacy/terms URLs, RLS/IDOR review note dated, backup restore test |
| **Days 61-90** | External-facing polish | Security headers/CSP plan, questionnaire dry-run, optional pen test or vendor scan if budget allows |

This is **not** a guarantee of certification; it is a **reasonable** sequencing for artifact accumulation.

---

## 6. What to avoid

- **Unsigned or anonymous** “audits” with no methodology.  
- **Screenshots of secrets** or full `.env` files in shared drives.  
- **Blanket statements** (“we encrypt everything”) without scope (at rest, in transit, what data).  
- **Stale evidence** - if the last review was >12 months ago, say so and schedule refresh.

---

## 7. Maintenance

- **Owner:** Engineering lead + whoever runs GRC/compliance threads.  
- **Update when:** Major infra change, new subprocessors, or new geography (UAE vs other regions).
