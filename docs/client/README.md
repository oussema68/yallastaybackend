# Client document package (Yallastay)

Use this folder as the **checklist of what to send** to clients, partners, or external reviewers. Individual files live under `docs/`; this index describes **audience** and **what to redact**.

---

## Standard cover for any attachment

When sending PDFs or exports, include a short cover line:

> **Yallastay - technical & product documentation**  
> Provided for **informational purposes** under [your NDA / contract]. Not a legal warranty, certification, or service-level commitment unless **expressly stated in a signed agreement**.

---

## Recommended client-facing set

| Document | Path | Notes |
|----------|------|--------|
| Security & privacy overview | [`../SECURITY_CHECKLIST.md`](../SECURITY_CHECKLIST.md) | Controls and practices (not a certification). |
| Layered security (XSS, authz, RLS) | [`../security/defense-layers.md`](../security/defense-layers.md) | How defenses combine. |
| Database row-level controls | [`../DATABASE_RLS.md`](../DATABASE_RLS.md) | PostgreSQL RLS scope; technical audience. |
| UAE verification rules | [`../product/uae-verification-pipeline.md`](../product/uae-verification-pipeline.md) | Product rules; not legal advice. |
| Mobile direction | [`../product/mobile-roadmap.md`](../product/mobile-roadmap.md) | Roadmap; not a fixed delivery promise. |
| Capacity & architecture | [`../operations/scaling-100k-users.md`](../operations/scaling-100k-users.md) | Indicative; not a performance guarantee. |
| Payments (Stripe) | [`../payments/stripe-setup.md`](../payments/stripe-setup.md) | Remove env values; variable **names** only. |
| E-sign product & compliance | [`../esign/pdf-signing-agreement.md`](../esign/pdf-signing-agreement.md), [`authority-verification.md`](../esign/authority-verification.md) | Legal/product review advised. |
| E-sign technical | [`../esign/setup.md`](../esign/setup.md) | For technical stakeholders. |
| Platform vision | [`../platform/vision-and-implementation.md`](../platform/vision-and-implementation.md) | Redact internal timelines if needed. |
| Partner / M2M API auth (OAuth 2.0 client credentials) | [`../platform/partner-api-authentication.md`](../platform/partner-api-authentication.md) | Recommended pattern for **server-to-server** integrations; distinct from interactive user JWT. |
| UI screenshots (Playwright) | [`../SCREENSHOTS_PLAYWRIGHT.md`](../SCREENSHOTS_PLAYWRIGHT.md) | **What to capture** for clients: full routes, header/menus, checklist before sending. |

---

## Share only under NDA or after redaction

| Document | Path | Reason |
|----------|------|--------|
| Commercial / SOW / bill | [`../commercial/`](../commercial/) | Pricing and scope - **redact** or send only **executed** excerpts. |
| MVP gap analysis | [`../product/mvp-gap-analysis.md`](../product/mvp-gap-analysis.md) | Marked **internal**. |
| Production readiness gaps | [`../product/production-readiness-gaps.md`](../product/production-readiness-gaps.md) | Marked **internal**. |
| Evidence pack playbook | [`../diligence/evidence-preparation.md`](../diligence/evidence-preparation.md) | Marked **internal** (how *you* assemble diligence). |
| Staff verification console | [`../operations/staff-verification-console.md`](../operations/staff-verification-console.md) | Privileged access and API; **do not** share with applicants. |

---

## Main docs index

See [`../README.md`](../README.md) for the full repository documentation map.
