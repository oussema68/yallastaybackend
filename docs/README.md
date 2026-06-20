# Yallastay documentation

Canonical technical and product docs for the Django backend (`yallastay/`). The **React web app** lives in a separate repo (`yallastay`); it consumes the same `/api/` surface.

**Sending docs to a client or partner?** Start with [`client/README.md`](./client/README.md) - it lists **client-facing** files, **internal-only** files, and redaction notes.

---

## Index

### Client package

| Doc | Purpose |
|-----|---------|
| [`client/README.md`](./client/README.md) | **What to send to clients** - recommended set, internal-only docs, redaction notes. |

### Security & database

| Doc | Purpose |
|-----|---------|
| [`../yallastay/.env.example`](../yallastay/.env.example) | Environment variable template (copy to `.env`; secrets never committed). |
| [`SECURITY_CHECKLIST.md`](./SECURITY_CHECKLIST.md) | **Client-facing** security & privacy controls overview (not a certification). |
| [`DATABASE_RLS.md`](./DATABASE_RLS.md) | PostgreSQL RLS scope and operations (technical due diligence). |
| [`security/defense-layers.md`](./security/defense-layers.md) | Layered defenses: XSS, RLS, IDOR, CSP, webhooks. |

### Presentations

| Doc | Purpose |
|-----|---------|
| [`presentations/partner-investor-platform-overview.md`](./presentations/partner-investor-platform-overview.md) | Partner / investor deck (MD): full-stack story, architecture, pillars, roadmap honesty, links to deep docs. |

### Platform & product

| Doc | Purpose |
|-----|---------|
| [`platform/vision-and-implementation.md`](./platform/vision-and-implementation.md) | Workflows, payments, e-sign, env vars, API order, frontend journeys. |
| [`product/mvp-gap-analysis.md`](./product/mvp-gap-analysis.md) | Gaps to a production MVP (features, security, ops). |
| [`product/uae-verification-pipeline.md`](./product/uae-verification-pipeline.md) | UAE-aligned verification: tenants, realtors, owners, title deeds, realtor ordering. |
| [`product/mobile-roadmap.md`](./product/mobile-roadmap.md) | Android/iOS roadmap vs the existing API. |
| [`product/mobile-api-readiness.md`](./product/mobile-api-readiness.md) | Whether the current API-first stack fits later native apps (and what to tighten). |

### Operations & capacity

| Doc | Purpose |
|-----|---------|
| [`operations/scaling-100k-users.md`](./operations/scaling-100k-users.md) | Path toward ~100k users: pooling, horizontal scale, DB, cache, phased roadmap. |
| [`operations/staff-verification-console.md`](./operations/staff-verification-console.md) | Staff verification console: access, API, localhost vs staff host, demo account. |

### Quality & testing

| Doc | Purpose |
|-----|---------|
| [`testing/testing-report.md`](./testing/testing-report.md) | What test types exist (Django, Vitest, Playwright, manual), gaps, and stakeholder wording. |
| [`GITHUB_SETUP.md`](./GITHUB_SETUP.md) | First-time Git init, push to GitHub, CI jobs, local parity commands. |
| [`DEMO_PRESENTATION.md`](./DEMO_PRESENTATION.md) | Live demo / Railway checklist, demo accounts, presenter script. |
| [`RESEND_SETUP.md`](./RESEND_SETUP.md) | Production email via Resend (`demo@yallastay.ae`), Railway env vars. |
| [`DEMO_GAP_REVIEW.md`](./DEMO_GAP_REVIEW.md) | Demo vs product gaps; aligns with `seed_demo` and presentation script. |

### Payments

| Doc | Purpose |
|-----|---------|
| [`payments/stripe-setup.md`](./payments/stripe-setup.md) | Stripe webhooks, CLI, Checkout, wallets. |

### Lease e-sign

| Doc | Purpose |
|-----|---------|
| [`esign/pdf-signing-agreement.md`](./esign/pdf-signing-agreement.md) | Product agreement: PDF signing, provider target. |
| [`esign/setup.md`](./esign/setup.md) | How the stub e-sign flow works in this repo (API, hooks). |
| [`esign/authority-verification.md`](./esign/authority-verification.md) | How audit trails tie to parties (compliance briefing). |

### Commercial / SOW

| Doc | Purpose |
|-----|---------|
| [`commercial/bill-template.md`](./commercial/bill-template.md) | Invoice / statement of work template. |
| [`commercial/bill-detailed.md`](./commercial/bill-detailed.md) | Technical scope breakdown (companion to the template). |
| [`commercial/project-bill-status.md`](./commercial/project-bill-status.md) | Same commercial totals with **Finished / Partial / Not started** per block. |

---

## Layout

```
docs/
├── README.md                 ← this file
├── DEMO_PRESENTATION.md
├── DEMO_GAP_REVIEW.md
├── client/
│   └── README.md             ← what to send to clients / NDAs
├── SECURITY_CHECKLIST.md
├── DATABASE_RLS.md
├── security/
│   └── defense-layers.md
├── presentations/
│   └── partner-investor-platform-overview.md
├── platform/
├── product/
│   ├── mobile-roadmap.md
│   └── mobile-api-readiness.md
├── operations/
│   ├── scaling-100k-users.md
│   └── staff-verification-console.md
├── testing/
│   └── testing-report.md
├── payments/
├── esign/
└── commercial/
```
