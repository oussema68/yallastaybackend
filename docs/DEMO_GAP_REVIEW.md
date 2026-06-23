# Demo gap review (Yallastay)

Engineering-facing checklist of **what the live/demo story is missing or weak on**, compared to what the codebase supports and what `DEMO_PRESENTATION.md` scripts today.

Related docs: [`DEMO_PRESENTATION.md`](DEMO_PRESENTATION.md), [`USAGE_GUIDE.md`](USAGE_GUIDE.md), [`product/mvp-gap-analysis.md`](product/mvp-gap-analysis.md), [`operations/happy-path-e2e-checklist.md`](operations/happy-path-e2e-checklist.md).

---

## 1. Recently addressed in `seed_demo` / docs

| Item | Status |
|------|--------|
| **`demo.landlord@…` staff-approved** | `seed_demo` sets **`LandlordProfile.is_approved=True`** and **`approved_at`** so the landlord beat is not blocked by “Get verified”. |
| **Non-empty staff verification queue** | **`demo.realtor-pending@…`** (private broker, not approved) and **`demo.owner-pending@…`** (landlord, not approved) appear in the **`yallastay_staff`** queue for `demo.verify`. |
| **Approved demo realtor + broker listing** | **`demo.realtor@…`** with approved **`RealtorProfile`** and **`[Demo] Marina · broker-listed studio`** (10-digit Trakheesi placeholder on listing). |
| **Messages not empty** | One **Conversation** on the primary Marina demo listing between tenant and landlord, with an opening message from the landlord. |
| **Presenter script** | `DEMO_PRESENTATION.md` includes an optional **rent (stub) → webhook → lease e-sign** beat and points here. |

---

## 2. Scripted demo vs full product story (remaining gaps)

| Gap | Notes |
|-----|-------|
| **E-sign depth** | The demo script hits **start rent → complete stub → session exists**; full **both-party sign + download** is in [`operations/happy-path-e2e-checklist.md`](operations/happy-path-e2e-checklist.md) and `core.tests.test_happy_path_chain` - extend the script if you need every click on stage. |
| **Email-dependent flows** | Demo still **avoids** password reset, magic-link email, etc., unless **SMTP** is configured; those paths are not “demo proven”. |

---

## 3. Ops / environment (easy to miss on Railway or split hosts)

| Gap | Notes |
|-----|-------|
| **Wrong API URL on SPA build** | SPA built with `VITE_API_URL=/api` on **split** API/SPA hosts → requests hit the wrong origin (404). |
| **CORS / `ALLOWED_HOSTS`** | `CORS_ALLOWED_ORIGINS` must include the SPA origin; `ALLOWED_HOSTS` must match the public API hostname (`DEMO_PRESENTATION.md`). |
| **Cold start** | Railway latency; warm-up before investors is noted; still a **schedule** risk. |
| **Stub vs Stripe** | Investor demos assume **`PAYMENT_PROVIDER=stub`**. Real money / **Stripe** needs a separate rehearsal. |
| **Ephemeral media** | Without **S3** (`USE_S3_MEDIA` / `AWS_*`), uploads on Railway **disappear on redeploy**; weak for “upload deed / ID” visuals. |

---

## 4. Product / MVP (not “demo broken”, but “demo cannot claim this”)

| Area | Notes |
|------|-------|
| **Ejari / DLD** | No integrated government automation; education + manual process (`mvp-gap-analysis.md`). |
| **Bank transfer rent** | Out of scope for unified in-app flow. |
| **Refunds / disputes / invoices** | May be incomplete vs user expectations. |
| **E-sign legal story** | In-app PDF + audit trail; not **TDRA-trusted** / DocuSign-class for all diligence questions. |
| **Security posture** | **Stub webhook** requires **JWT (payment owner)** or **`X-Stub-Webhook-Secret`** when configured; **JWT in `localStorage`**, production **private media**; see `SECURITY_CHECKLIST.md`; be ready to answer. |

---

## 5. Frontend / UX consistency

| Gap | Notes |
|-----|-------|
| **Route protection** | Per-page `localStorage` + axios 401 → possible **deep-link flashes** (`mvp-gap-analysis.md`). |
| **Signup vs rest of app** | Signup may still use **raw `fetch`** while other flows use **axios**. |
| **i18n / a11y** | English-first; systematic accessibility not positioned as complete. |

---

## 6. Suggested next steps (when you iterate again)

1. **Playwright / video backup** for the investor path: [`SCREENSHOTS_PLAYWRIGHT.md`](../SCREENSHOTS_PLAYWRIGHT.md).
2. **Staging rehearsal** with **split hosts** and absolute **`VITE_API_URL`** exactly as on Railway.
3. **Optional:** a second seeded message or unread state if the Messages UI benefits from it.
4. **Keep this file aligned** whenever `seed_demo` or `DEMO_PRESENTATION.md` changes.

---

*Align with `seed_demo` / `bootstrap_demo` whenever demo accounts or approval rules change.*
