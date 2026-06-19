# Price vs value - YallaStay (report)

| | |
|---|---|
| **Distribution** | **Confidential - commercial.** Share with clients under NDA or during formal proposals. |

This report relates **commercial price** (what the build is quoted at) to **value** (what the client receives in product terms, risk reduction, and time-to-market). Figures align with **[`bill-template.md`](./bill-template.md)** §4.6 and delivery notes in **[`project-bill-status.md`](./project-bill-status.md)**.

**Currency:** AED, excluding VAT, unless stated otherwise.

---

## 1. Price snapshot (one-time build)

| Layer | Quoted (§4.6) | Role in the product |
|-------|--------------:|---------------------|
| Backend API | 381,700 | Core rental + lifestyle logic, integrations, e-sign orchestration |
| Web (React) | 74,500 | Primary tenant/landlord/realtor UI on the same API |
| iOS + Android | 175,000 | Native store apps consuming the same `/api` surface |
| Deployment & external wiring | 44,000 | Host, SSL, env, Stripe/SMS/email keys |
| Documentation | 8,500 | Runbooks, mapping, payment setup |
| **Total (excl. tax)** | **683,700** | Full-stack contract as priced |

**Not in the table above:** recurring **§4.7** maintenance, optional **§4.8** scaling, and **metered vendor bills** (hosting usage, SMS, email, payment MDR, UAE ID API fees - typically on client accounts).

---

## 2. What “value” means here

| Dimension | Meaning |
|-----------|---------|
| **Functional value** | Features that work end-to-end for users (browse, book, pay, message, sign, notify). |
| **Integration value** | Fewer manual steps: webhooks, transactional email/SMS plumbing, Stripe checkout path. |
| **Compliance / trust value** | UAE electronic consent on signing, audit events, verification states - not a substitute for a qualified trust service, but structured records. |
| **Strategic value** | One API for web + future mobile; listings and reservations as a single system of record. |
| **Residual risk** | Gaps between quoted scope and current repo reduce *realized* value until closed (see §4). |

---

## 3. Value received vs price by layer (high level)

This is a **qualitative** mapping: high quoted amount + high delivery = strong value-for-money; high quoted amount + low delivery = value still “in the backlog.”

| Layer | Price (AED) | Value today (repo-aligned) |
|-------|------------:|----------------------------|
| **Backend** | 381,700 | **High** for listings, bookings, messaging, reviews, roommates, analytics, reports, comms apps. **Medium** where integrations are partial (Stripe prod discipline, push, lifestyle depth, document URLs). **Lower realized** for UAE ID live API and DocuSign-class e-sign - priced in the bill but not fully delivered per [`project-bill-status.md`](./project-bill-status.md). |
| **Web** | 74,500 | **High** for core journeys; polish and edge flows may still absorb time. |
| **Mobile** | 175,000 | **Not started** in this repo - **price reserved for future delivery**; no functional value from mobile line items until shipped. |
| **Deployment** | 44,000 | **Partial** - codebase is deployable; concrete env (domain, secrets, go-live) is client/ops-specific. |
| **Docs** | 8,500 | **High** relative to cost - navigation, Stripe notes, vision/gap docs reduce onboarding friction. |

---

## 4. Where price exceeds *realized* value (gaps)

These items are **priced in the SOW** but **not fully delivered** or **need production hardening**. Closing them moves quoted price closer to realized value.

| Area | Bill reference | Value gap (plain language) |
|------|----------------|----------------------------|
| UAE ID live API | §4.1 block (verification) | Gating and UX exist; **live government/API verification** is the main MVP gap. |
| Native iOS / Android | §4.3 | **175,000 AED** of scope is **future work** until apps ship. |
| E-sign | §4.1 (e-sign row) | Strong **in-app** flow + audit; **enterprise-grade** third-party e-sign is not integrated. |
| Notifications push | §4.1 | In-app value is real; **mobile push** completion adds renter/landlord responsiveness. |
| Documents | §4.1 | Upload flows exist; **private signed URLs** in production close security/value gap. |
| Deployment | §4.4 | **Integration wiring** is priced; **recurring hosting bills** stay client-paid by design. |

---

## 5. Where value is strong relative to price

- **Single API** consumed by web (and planned mobile) - avoids duplicate business logic.
- **Reservation → payment → lease signing → leased listing** is a coherent chain with real automation (webhooks, team messaging, e-sign session).
- **Operational documentation** (mapping, Stripe, testing) is inexpensive in the quote but saves weeks of discovery.
- **Cross-cutting** email/SMS models and webhooks support supportability and transparency (delivery status, admin visibility).

---

## 6. Summary

| Question | Answer |
|----------|--------|
| **What is the full-stack price?** | **683,700 AED** excl. VAT (§4.6). |
| **Is all of that value live today?** | **No** - mobile is unbuilt; UAE ID live and some hardening items remain; several areas are **partial**. |
| **Is the remaining work “extra”?** | Not always - some gaps are **scope in the bill not yet realized**; optional retainers (**§4.7**) and scaling (**§4.8**) are separate. |
| **How to read this report with finance?** | Use **§4.6** for contract totals; use **[`project-bill-status.md`](./project-bill-status.md)** for **earned vs pending** by block; use this file for **stakeholder narrative** between money and outcomes. |

---

## Related documents

| Document | Use |
|----------|-----|
| [`bill-template.md`](./bill-template.md) | Formal line items and §4.6 totals |
| [`bill-detailed.md`](./bill-detailed.md) | Technical/file-level scope |
| [`project-bill-status.md`](./project-bill-status.md) | Finished / partial / not started by block |
| [`../product/mvp-gap-analysis.md`](../product/mvp-gap-analysis.md) | Engineering gaps vs MVP |

---

*Figures and scope names follow the commercial docs at the time of writing; update this report when §4.6 or delivery status changes materially.*
