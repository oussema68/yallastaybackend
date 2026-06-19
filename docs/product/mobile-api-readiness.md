# Mobile (iOS / Android) readiness vs current stack

| | |
|---|---|
| **Audience** | Engineering, product |
| **Related** | [`mobile-roadmap.md`](./mobile-roadmap.md), [`../platform/vision-and-implementation.md`](../platform/vision-and-implementation.md) |

This note answers whether the **current direction** (Django REST API + JWT + React web) sets the product up well for **later native app integration**.

---

## Verdict

**Yes - the architecture is aligned** with a typical API-first mobile strategy, as long as the **backend** remains the source of truth for business rules and the **web app** is treated as **one client** among future iOS/Android clients.

---

## What already helps

| Direction | Why it helps mobile |
|-----------|---------------------|
| **Django REST + `/api/`** | Native apps consume the same JSON contracts as the web; avoid duplicating business logic in clients. |
| **JWT (access + refresh)** | Standard for mobile; web `localStorage` can later be replaced with **OS-managed storage** (Keychain, EncryptedSharedPreferences, etc.) without redesigning auth. |
| **Stripe + server-side webhooks** | Payment and post-payment logic stays on the server; apps use Stripe Checkout, Payment Sheet, or in-app browser patterns - same backend webhooks. |
| **React web in a separate repo** | You are not forced into a WebView-only shell; React Native, Flutter, or native stacks can share the API. |

---

## What to tighten over time

These improvements pay off for **web and mobile** together. Details are in [`mvp-gap-analysis.md`](./mvp-gap-analysis.md) and [`mobile-roadmap.md`](./mobile-roadmap.md).

1. **API contracts:** Stable error shapes, pagination, versioning strategy if breaking changes are needed; idempotent actions where appropriate.
2. **Auth behavior:** Same endpoints for login, refresh, logout, password reset; consistent handling of protected resources (see gap analysis on route protection and token refresh).
3. **Push notifications:** Backend (or adjacent service) for **FCM** (Android) and **APNs** (iOS) device registration - listed in the mobile roadmap as backend work.
4. **Deep links:** Email verification, magic links for signing - plan **universal links** / **app links** so installed apps open the right screen.
5. **Payments and signing in production:** Do not rely on **stub** checkout in production; align with Stripe and your e-sign approach before store release.

---

## What to avoid as the only mobile strategy

The mobile roadmap **does not recommend** a **Capacitor / WebView-only** wrapper as the long-term approach for a **marketplace** with payments and e-sign: store review risk, weaker UX for payments and signing, and offline limitations. Prefer **React Native (Expo)**, **Flutter**, or **native** UIs per your roadmap, with **thin** WebView use only where acceptable (e.g. short-term signing via SFSafariView / Chrome Custom Tabs).

---

## Short summary for stakeholders

**Current stack:** API-first backend + JWT + server-side payments is **compatible** with future iOS and Android apps.

**Ongoing discipline:** Keep business rules on the **server**, document **auth and payment** flows for **all** clients, and close the same production gaps (auth consistency, private media, production Stripe) that matter for web and mobile.

---

*Last updated: March 2026*
