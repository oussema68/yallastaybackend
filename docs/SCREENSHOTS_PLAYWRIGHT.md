# Screenshots & browser automation (Playwright)

This document describes how to capture **page screenshots** for **client handovers** (pitch decks, store listings, diligence, design review), **without** shipping automation tools to production or leaking sensitive data.

**Frontend repo:** `yallastay` (Vite + React), typically next to this backend.  
**Backend:** run separately (`python manage.py runserver` on **:8000**) when the UI needs live API data (login, listings, messages, etc.).

---

## Playwright vs Puppeteer

| | **Playwright** | **Puppeteer** |
|---|----------------|----------------|
| **Browsers** | Chromium, Firefox, WebKit | Mainly Chromium |
| **Use case** | E2E tests, screenshots, tracing | Chrome-only automation |
| **Typical install** | `@playwright/test` (devDependency) | `puppeteer` (devDependency) |

**Recommendation:** Use **Playwright** for screenshot runs and future E2E tests.

Neither tool ships in the **built** React bundle; they run as **Node** on your machine or in CI.

---

## What must NOT go to production

1. **Dependencies:** Keep Playwright in **`devDependencies`** in the frontend `package.json`.
2. **Docker / hosting:** Production images should not install devDependencies unless you run tests in that image.
3. **Secrets:** Do not hardcode passwords in scripts. Use **`.env`** and **demo** accounts only (`E2E_USER_EMAIL`, `E2E_USER_PASSWORD`).
4. **Data:** Prefer **local + seeded** data (`seed_core`, etc.) or **staging**. Do not screenshot **production** with real PII, payment details, or UAE ID documents.
5. **Artifacts:** Treat **`screenshots/`** as **local output**; gitignored; review before zipping for a client.

---

## Gitignored paths (frontend `yallastay`)

- `screenshots/` (generated PNGs)  
- `playwright-report/`, `test-results/`, `blob-report/`  
- `e2e/.auth/user.json` (saved JWT from setup; never commit)

---

## Automated capture list (current)

The frontend **`e2e/screenshots.spec.js`** writes **26 PNGs** per successful run (`npm run test:e2e` from `yallastay`). Filenames are stable for decks and appendices.

### A. Full-page routes (23)

| # | File | Route | What client sees |
|---|------|-------|-------------------|
| 01 | `01-home.png` | `/` | Landing / personalized home |
| 02 | `02-search.png` | `/search` | Search & filters |
| 03 | `03-property.png` | `/property/1` | Property detail (use a **real listing id** in seed data) |
| 04 | `04-login.png` | `/login` | Login (no saved session) |
| 05 | `05-signup.png` | `/signup` | Signup (no saved session) |
| 06 | `06-verify.png` | `/verify` | Verification hub |
| 07 | `07-dashboard.png` | `/dashboard` | Renter dashboard |
| 08 | `08-profile.png` | `/profile` | Account profile |
| 09 | `09-my-listings.png` | `/my-listings` | Lister / broker workspace |
| 10 | `10-services.png` | `/services` | Lifestyle services |
| 11 | `11-add-property.png` | `/add-property` | Add listing |
| 12 | `12-messages.png` | `/messages` | Messaging |
| 13 | `13-notifications.png` | `/notifications` | Notifications |
| 14 | `14-roommates.png` | `/roommates` | Roommates (role-dependent) |
| 15 | `15-documents.png` | `/documents` | Documents |
| 16 | `16-for-partners.png` | `/for-partners` | Partners / B2B |
| 17 | `17-terms.png` | `/terms` | Terms of use |
| 18 | `18-privacy.png` | `/privacy` | Privacy policy |
| 19 | `19-payment-success.png` | `/payment/success?session_id=demo_session` | Post-payment confirmation |
| 20 | `20-payment-cancel.png` | `/payment/cancel` | Cancelled checkout |
| 21 | `21-edit-property.png` | `/edit-property/1` | Edit listing (id must exist + permission) |
| 22 | `22-user-profile.png` | `/user/1` | Public user profile (id must exist) |
| 23 | `23-sign-lease-invalid.png` | `/sign/lease/invalid-or-expired-token` | Lease signing error / invalid link state |

**Not automated:** `/backend` (developer health page); **omitted** from client packs; use API docs or monitoring screenshots instead if needed.

### B. Header & navigation chrome (3)

These complement full-page shots so clients see **navigation**, **mobile menu**, and **account dropdown** (often required for App Store / Play **store listings** and UX reviews).

| # | File | How it is captured |
|---|------|----------------|
| 24 | `24-header-guest-mobile-menu-open.png` | **Guest** session, **390×844** viewport, hamburger open (Login / Sign up / nav) |
| 25 | `25-header-auth-mobile-menu-open.png` | **Logged-in** session (E2E user), **390×844**, hamburger open (Account block, messages, etc.) |
| 26 | `26-header-desktop-account-menu-open.png` | **Logged-in**, **1440×900**, **Account menu** (avatar) open: Messages, Notifications, Profile, etc. |

**Persona toggle** (Owner/Broker vs Renter): appears when the logged-in user is a **landlord** or **realtor**. To include it in screenshots, use an E2E account with that role and, if needed, **manually** add a shot after switching the toggle (not a separate file in the default spec unless you extend it).

---

## Optional manual captures for client packs

Automation cannot cover every **state** without many fixtures. For a **complete** client or investor pack, consider **manually** adding:

| Topic | Why |
|-------|-----|
| **Stub payment modal** | Dev-only checkout; only if explaining test vs production Stripe. |
| **Stripe Checkout** (hosted) | Real payment UX; capture from **staging** with test card. |
| **Sign lease (valid token)** | Happy path signing; needs a **valid** magic link from backend/email. |
| **Empty states** | No messages, no listings; clarify product behavior. |
| **Error / offline** | Optional, for trust / support story. |
| **Arabic / RTL** | If product later supports; not in default web build. |

---

## Quick setup (frontend `yallastay`)

```bash
npm install
npx playwright install chromium
```

**Logged-in routes:** create **`.env`** from **`.env.example`**:

```env
E2E_USER_EMAIL=your-user@example.com
E2E_USER_PASSWORD=your-password
```

Use an account that exists in your **local Django** DB. Playwright runs **`e2e/auth.setup.js`** first: it `POST`s to `/api/auth/login/` and saves **`e2e/.auth/user.json`** (gitignored). All tests except **Login** and **Signup** reuse that session.

**Capture everything:**

```bash
npm run test:e2e
```

Writes `screenshots/01-home.png` … `screenshots/26-header-desktop-account-menu-open.png`.

Start **Django on :8000** before running (Vite proxies `/api`). Playwright can start Vite on **:3000** if not running (`reuseExistingServer` in `playwright.config.js`).

**Guest header shot (`24-header-guest-mobile-menu-open`):** uses an **empty** `storageState` and clears `localStorage` / `sessionStorage` before loading `/`, so the menu shows **Login** and **Sign Up** (not the logged-in **Account** block). If this test fails while others pass, ensure no extension or script is injecting a token.

**Load + scroll (quality):** `e2e/helpers.js` waits for **`load`**, **`networkidle`** (best-effort), no “Loading…” shell text, and **`main`** with content. It then **scrolls the page in a bounded way** (few steps to trigger below-the-fold / lazy content), waits for **network idle** again, waits for **images** (capped), scrolls back to **top**, and applies a short **settle** pass before each PNG. Header shots call an extra **settle** after opening menus.

**Timeouts:** `playwright.config.js` sets **120s per test**; `page.screenshot` uses **90s** for full-page captures (font loading can exceed the old 30s default).

---

## Checklist before sending screenshots to a client

- [ ] No real credentials visible in images  
- [ ] No production URLs or private tenant data  
- [ ] Neutral filenames (`01-home.png`, not `ACME-prod-leak.png`)  
- [ ] Consistent **viewport** (default **1440×900** for pages; header tests use mobile + desktop as above)  
- [ ] Include **Terms** + **Privacy** if the client is legal/compliance  
- [ ] Include **header / mobile / account menu** shots for **store** or **UX** reviews  
- [ ] Zip **`screenshots/`** only; not `node_modules`, `.env`, or `e2e/.auth/`  

---

## Related docs

- **Backend repo:** `USAGE_GUIDE.md` (run backend + frontend together)  
- **Backend repo:** `MANUAL_TESTING.md` (API checks; complements UI screenshots)  
- **Client doc index:** [`client/README.md`](client/README.md) (links to security, compliance, and this screenshot guide)  
