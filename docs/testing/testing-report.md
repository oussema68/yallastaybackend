# Testing report (Yallastay)

**Scope:** Django API (`yallastay_backend`) and React web app (`yallastay` on Desktop).  
**Purpose:** Summarize which **types** of testing exist in the repos, what is **manual**, and what remains **thin or missing**.  
**Last updated:** March 2026

---

## Executive summary

| Category | Status |
|----------|--------|
| Backend automated tests (Django) | **In place** across many apps |
| Frontend automated tests (Vitest) | **In place** for selected utils, hooks, components, pages |
| Browser automation (Playwright) | **In place** primarily as **route screenshots**, not assertion-heavy E2E |
| Manual API QA | **Documented** ([`MANUAL_TESTING.md`](../MANUAL_TESTING.md) in `docs/`) |
| Critical-path E2E (e.g. login to pay to sign) | **Not** fully covered as automated assertions |
| CI always running tests | **Verify** in your pipeline (not guaranteed by repo alone) |

---

## 1. What exists today

### 1.1 Backend: Django tests

- **Location:** `yallastay/<app>/tests/test_*.py` (e.g. `accounts`, `bookings`, `esign`, `listings`, `payments`, `messaging`, `roommates`, `lifestyle_services`, …).
- **How to run:** From the backend project (with venv activated):

  ```bash
  python manage.py test
  ```

  Targeted runs (examples from project docs):

  ```bash
  python manage.py test core accounts listings bookings reviews payments messaging lifestyle_services notifications sms emails analytics reports roommates documents yallastay
  ```

- **Nature:** Mix of **unit-style** tests (models, pure helpers, serializers) and **integration / API** tests (views, authenticated flows) using Django/DRF test utilities.

### 1.2 Frontend: Vitest

- **Location:** `yallastay/tests/unit/` (separate frontend repo).
- **How to run:**

  ```bash
  npm test
  # or: npx vitest run
  ```

- **Examples:** `sanitize`, `messagesPayload`, `useMessagesBackgroundSync`, `SignatureCanvas`, `SignLease`, `paymentCheckout`, `client` exports, `logger`.

### 1.3 Playwright (frontend)

- **Location:** `yallastay/e2e/` (e.g. `screenshots.spec.js`).
- **How to run:**

  ```bash
  npm run test:e2e
  ```

- **Nature:** **Screenshot capture** per route (PNG outputs), useful for visual regression and documentation. This is **not** the same as full **E2E tests** that assert business outcomes (success messages, DB side effects, payment completion).

### 1.4 Manual testing

- **Location:** [`docs/MANUAL_TESTING.md`](../MANUAL_TESTING.md) (API matrix: methods, paths, sample bodies, expected codes).
- **Nature:** Manual QA with Postman, Insomnia, curl, or similar - **not** automated.

### 1.5 Supporting docs

| Doc | Role |
|-----|------|
| [`MANUAL_TESTING.md`](../MANUAL_TESTING.md) | Manual API checklist |
| [`USAGE_GUIDE.md`](../USAGE_GUIDE.md) | Includes `manage.py test` examples |
| [`SCREENSHOTS_PLAYWRIGHT.md`](../SCREENSHOTS_PLAYWRIGHT.md) | Playwright vs alternatives, screenshot workflow |
| [`product/mvp-gap-analysis.md`](../product/mvp-gap-analysis.md) | Notes gaps (E2E, CI, etc.) |

---

## 2. Gaps and recommended next steps

These are **not** a failure of current work; they are typical **next layer** items for a marketplace product.

| Gap | Detail |
|-----|--------|
| **Assertion-based E2E** | Add Playwright (or similar) tests for **critical paths**: e.g. sign-in, booking/payment happy path, lease signing stub flow - with **expects**, not only screenshots. |
| **CI** | Backend: `python manage.py test` (see `.github/workflows/ci.yml`). Frontend repo: `npm test`; optionally Playwright in CI (known flakiness trade-offs). |
| **Staging sign-off** | Password reset, email verification, Stripe test vs live separation - often validated **manually** on staging until automated. |
| **Load / performance** | Not described as a standard artifact in-repo; add if you have SLOs or before major campaigns. |
| **Security testing** | Penetration test, vendor scan, or structured review - optional but valuable for diligence (`docs/diligence/evidence-preparation.md` references such artifacts). |
| **Mobile** | Native app testing is **out of scope** for the web repo; `docs/product/mobile-roadmap.md` references staging API checks for future apps. |

---

## 3. How to describe this to stakeholders

- **"We have automated tests"** - Yes: Django + Vitest; qualify that coverage is **per-feature**, not necessarily 100% of user journeys.
- **"We have E2E tests"** - Be precise: you have **browser automation**; **full E2E coverage** of money and signing flows may still be **partial** until explicit tests are added.
- **"We have a test plan"** - Yes for APIs via `MANUAL_TESTING.md` for manual runs.

---

## 4. Related files (quick reference)

| Repo | Path |
|------|------|
| Backend tests | `yallastay_backend/yallastay/*/tests/` |
| Frontend unit tests | `yallastay/tests/unit/` |
| Playwright | `yallastay/e2e/` |
| Manual API guide | `yallastay_backend/docs/MANUAL_TESTING.md` |

---

*This report is descriptive. Commands assume correct Python/Node environments and env files per `USAGE_GUIDE.md` and `.env.example`.*
