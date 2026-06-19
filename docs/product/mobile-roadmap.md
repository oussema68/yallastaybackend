# Yallastay - Android & iOS development roadmap

| | |
|---|---|
| **Audience** | Clients, partners, product, engineering |
| **Distribution** | **Client-facing** - roadmap is **indicative**, not a fixed delivery commitment unless agreed in writing. |
| **Disclaimer** | Stack choice and dates may change after discovery. |

This document outlines a **practical path** to ship **native-quality** mobile clients on top of the existing **Django REST API** and **Vite/React** web app. It is a **product/engineering roadmap**, not a commitment to a single framework - choose stack after one discovery sprint.

**Related docs:** [`../platform/vision-and-implementation.md`](../platform/vision-and-implementation.md), [`../SECURITY_CHECKLIST.md`](../SECURITY_CHECKLIST.md), [`mobile-api-readiness.md`](./mobile-api-readiness.md) (current stack vs native apps). Internal gap analysis: [`mvp-gap-analysis.md`](./mvp-gap-analysis.md) (**internal**).

---

## 1. Principles

| Principle | Implication |
|-----------|-------------|
| **API-first** | Mobile uses the **same** `/api/` contracts as the web app; avoid mobile-only endpoints unless necessary (push tokens, app version). |
| **No duplicate business logic** | Payments, signing, bookings stay on the **server**; apps are clients. |
| **Security upgrade** | Replace **localStorage JWT** patterns with **OS-managed storage** (see §6). |
| **Ship thin, iterate** | First store releases can be **subset** of web (search, chat, payments) if core journeys are solid. |

---

## 2. Stack decision (pick one path)

Do a **1-2 week** spike before full build:

| Option | Pros | Cons |
|--------|------|------|
| **React Native (Expo)** | Shared logic with React patterns; OTA updates; one team can own web + mobile. | Bridge quirks; native modules when needed. |
| **Flutter** | Strong UI consistency; performance; growing ecosystem. | Dart stack; different from current React. |
| **Kotlin Multiplatform + Swift UI** | Best platform fit; long-term at scale. | Two UI codebases or shared KMP with Swift UI - higher cost. |
| **Capacitor / WebView shell** | Fastest to “an app”; reuse web. | **Poor** for payments, signing, offline UX; store review risk; **not recommended** for a marketplace MVP. |

**Recommendation for most teams:** **React Native (Expo)** or **Flutter** for a balance of speed and quality; **avoid** wrapping the SPA as the only mobile strategy for payments and e-sign.

---

## 3. Phased roadmap

### Phase 0 - Foundations (2-4 weeks)

- **API audit:** List every endpoint the web app uses for **auth, listings, bookings, payments, messaging, notifications, esign, documents**; confirm **pagination**, **errors**, and **rate limits** behave well for mobile (no reliance on hidden cookies except CSRF where applicable).
- **Auth contract:** Document **JWT access + refresh** flow; plan **logout everywhere** and **token refresh** on 401.
- **Environments:** `staging` and `production` base URLs; **certificate pinning** (optional) later.
- **Design:** Mobile navigation model (tabs vs stack), **one** design system (Figma) aligned with web branding.

**Exit criteria:** Written API + auth spec; spike app calls `/api/auth/me/` and refreshes token.

---

### Phase 1 - MVP mobile (8-12 weeks, parallel tracks)

**Goal:** Installable **Android + iOS** apps that pass store review and support the **core renter journey**.

**Features (minimum viable):**

| Area | Scope |
|------|--------|
| **Onboarding** | Splash, login, signup, email verification deep link (universal links / app links). |
| **Browse** | Search + filters + property detail (parity with web **read** APIs). |
| **Favorites** | If backend supports favorites - same as web. |
| **Messaging** | Conversation list + thread (polling or WebSocket if backend adds it later). |
| **Profile** | View/edit profile, verification status. |
| **Payments** | **Stripe Checkout** in **in-app browser** or **Stripe Payment Sheet** - align with backend `PAYMENT_PROVIDER` and webhooks; **do not** embed stub payment in production. |
| **Notifications** | Push token registration endpoint + **FCM (Android)** + **APNs (iOS)**; in-app notification list if API exists. |

**Explicitly out of scope for Phase 1 (unless trivial):**

- Full **realtor dashboard** parity (can be Phase 2).
- **Lease PDF signing** in WebView only - **acceptable short-term** if magic-link opens **SFSafariView / Chrome Custom Tabs**; **native** signing UX is Phase 2+.

**Exit criteria:** Internal TestFlight + Play Internal Testing; **smoke E2E** on real devices; crash-free sessions > 99% in staging.

---

### Phase 2 - Parity & trust (6-10 weeks)

- **Lister / realtor** flows: dashboard, listings CRUD, viewing slots, **upload lease PDF** (document picker + multipart).
- **E-sign:** Native **SignLease** flow or **certified** in-app WebView with **clear** consent + audit; consider **deep linking** from email into the app.
- **Documents:** Secure download/view with **authenticated** API (no public media URLs for private docs).
- **Offline:** Cached **read-only** where safe (e.g. last messages); queue actions cautiously.

---

### Phase 3 - Polish & scale (ongoing)

- **Performance:** Image CDN, list virtualization, startup time.
- **Accessibility:** TalkBack / VoiceOver, dynamic type.
- **Localization:** Arabic + English if product requires (RTL layout).
- **Observability:** Mobile crash reporting (Sentry/Firebase), session analytics (privacy-compliant).
- **Store presence:** ASO, screenshots, privacy nutrition labels, data safety form (Android).

---

## 4. Backend work (mobile-specific)

| Item | Purpose |
|------|---------|
| **`POST /api/devices/` / similar** | Register **FCM token** + **APNs token** + platform + app version. |
| **Push payloads** | Reuse **notifications** service; silent vs visible rules. |
| **Universal links** | `/.well-known/apple-app-site-association`, Android **Digital Asset Links** for `verify`, `sign/lease`, `payment/success`. |
| **Optional: WebSocket** | Real-time messaging - **only if** polling is insufficient; adds ops complexity. |
| **Rate limits** | Mobile user-agents should not be throttled harder than web without reason. |

Coordinate with backend before locking **mobile-only** contracts.

---

## 5. Security & compliance (mobile)

- **Secrets:** Use **Keychain / EncryptedSharedPreferences** (or RN/Flutter secure storage) - **never** store refresh tokens in plain `AsyncStorage` alone for production.
- **Screenshots:** Flag sensitive screens (balance, ID) when OS allows blur on app switcher.
- **Jailbreak / root:** Detect and **warn** or **limit** sensitive actions (policy decision).
- **Play / App Store:** Privacy policy URL, data deletion, Stripe as processor disclosure.

See [`../SECURITY_CHECKLIST.md`](../SECURITY_CHECKLIST.md) - mobile should **not** rely on `localStorage` XSS model as the only line of defense.

---

## 6. Delivery & release

| Milestone | Android | iOS |
|-----------|---------|-----|
| Internal alpha | Internal App Sharing / internal track | TestFlight |
| Closed beta | Open track / beta | TestFlight external |
| Production | Play Console staged rollout | App Store phased release |

**CI:** Build **signed** artifacts on **tags** or `main`; separate **staging** vs **prod** bundle IDs / application IDs.

---

## 7. Team & estimates (rough)

| Role | Phase 0-1 |
|------|-----------|
| Mobile engineer(s) | 1-2 FTE |
| Backend support | 0.2 FTE (endpoints, push) |
| Design | 0.2 FTE |
| QA | 0.3 FTE |

**Calendar:** ~3-4 months from kickoff to **public** MVP mobile **if** API is stable and scope is Phase 1 only.

---

## 8. Checklist before “we start building screens”

- [ ] Stack chosen (RN/Flutter/native) and spike approved  
- [ ] Auth + refresh flow documented and tested against **staging** API  
- [ ] Stripe flow agreed (Checkout vs Payment Sheet)  
- [ ] Push notification provider (FCM + APNs keys in org accounts)  
- [ ] Apple Developer + Google Play accounts + legal entity for stores  
- [ ] Privacy policy and terms links ready for store listings  

---

*Version 1.0 - update when stack choice or Phase 1 scope changes.*
