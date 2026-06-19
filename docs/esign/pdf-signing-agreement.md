# Lease signing on PDF - agreed product approach (Yallastay)

| | |
|---|---|
| **Audience** | Product, legal, partners, clients |
| **Distribution** | **Client-facing** - under NDA; **not legal advice**. |
| **Disclaimer** | UAE/Dubai lease format, Ejari, and qualified signatures - **counsel** decides final requirements. |

This document records **what we are building toward**: **legally meaningful signing on a PDF lease**, not only a database flag. It aligns engineering, product, and external counsel on scope. **It is not legal advice** - UAE/Dubai lease format, Ejari registration, and final sign-off remain with **qualified UAE legal and property advisors**.

---

## 1. What we agreed

| Topic | Agreement |
|-------|-----------|
| **Artifact** | The tenancy agreement is represented by a **PDF document** (one definitive file per signing case, versioned as needed). |
| **Signing** | Each party applies their signature **to that PDF** (or to an **envelope** that wraps it) via a **recognised e-sign process** with **audit trail** and a **completed/signed PDF** output. |
| **Order** | **Renter signs first**, then **landlord / listing owner (or authorised realtor)** countersigns - same rule as today’s app logic; in production this is enforced by **signing order** in the e-sign flow (preferred) or equivalent controls. |
| **System of record** | Yallastay continues to track **`LeaseSigningSession`** (or successor model) with links to **unsigned** and **signed** documents, vendor metadata, and status. |
| **Stub vs production** | Today’s **stub** (confirm button without a PDF) is **development-only**. **Production** means **PDF + provider workflow** (see §3). |

---

## 2. Why PDF (not “click agree” only)

- **Evidence:** Disputes and regulators care about **what text was agreed** and **who agreed to it**. A **stable PDF** (with integrity checks) supports that.
- **Dubai / UAE context:** Practical tenancy workflows often involve **written contracts** and **registration** steps; counsel should confirm how **Ejari / DLD** requirements apply to **your** lease and whether additional steps apply beyond e-sign. This doc does not replace that review.
- **Partner trust:** Landlords, realtors, and renters expect a **real contract file**, not only in-app status.

---

## 3. Target architecture (production)

### 3.1 Document lifecycle

1. **Source PDF** - Either:
   - **Generated** by the platform from an approved template (merge fields: parties, property, rent, dates), or  
   - **Uploaded** by an authorised role from a lawyer-approved file (with versioning rules).
2. **Freeze / hash** - Store a **content hash** (e.g. SHA-256) of the PDF **before** signing so the agreed text is identifiable.
3. **Send for signature** - Create an **envelope** (or equivalent) with the PDF in the chosen **e-sign provider**.
4. **Sign** - Renter then lister (or provider-enforced order) sign **on the PDF** in the provider UI (embedded in our app or hosted by the provider).
5. **Complete** - On completion, **download and store** the **signed PDF** and any **completion certificate / audit** the provider supplies.
6. **Sync app state** - Webhooks (or polling where needed) update **`LeaseSigningSession`**, **`reservation` / `dld_metadata`**, and **`listing.leased`** consistent with existing behaviour.

### 3.2 Provider

- Use a **commercial e-sign API** (e.g. DocuSign, Dropbox Sign, Adobe Sign, or another vetted by counsel and security review).
- Store **`provider_metadata`** on `LeaseSigningSession` (envelope id, request id, signer mapping, etc.) - field already exists for this purpose.
- **Bank/wire** and payment rails are **out of scope** for this document; payments remain as implemented elsewhere.

### 3.2a Yallastay-native signature placement (implemented in app)

- The lister/realtor can define **two rectangles** on the **contract PDF** - one for the renter, one for the lister - via **`signature_field_boxes`** on `LeaseSigningSession` (see API `PATCH …/signature-fields/`).
- Coordinates use **PDF points** with origin **bottom-left** (same as ReportLab), per field: `page_index`, `x`, `y`, `width`, `height`.
- When **both** boxes are set, **`signed_pdf`** is built by **overlaying** the captured PNG signatures onto those pages **instead of** appending separate certificate pages. If the field is empty, the legacy behaviour (contract + certificate pages) remains.
- **Frontend follow-up:** a PDF viewer where the realtor **draws** or **places** boxes (then sends coordinates) is still the product work; the backend accepts the JSON.

### 3.3 Frontend

- Replace the **stub** “Confirm signature” experience with:
  - **Embedded signing** or **redirect** to the provider’s signing session for the current party, **or**
  - **PDF preview** (optional) plus **CTA** to open signing when the provider session is ready.
- Continue to support **magic-link style access** only where security review allows; prefer **authenticated + provider** flows where required.

---

## 4. Relationship to current code

| Piece | Role |
|-------|------|
| **`LeaseSigningSession`** | Keeps **one session per reservation**; extended to reference **PDF** assets and **vendor** ids. |
| **`LeaseSigningAuditEvent`** | **UAE-aligned audit trail** (preview opened, contract PDF viewed, electronic consent, each signature commit, session completed) with **IP** and **User-Agent**; consent text references **Federal Decree-Law No. 46 of 2021** (electronic transactions). Magic-link **POST** must send **`consent_to_electronic_signature`** on the first signature submission per party (multi-slot: once per party). |
| **`payments.hooks` → `after_rental_payment_completed`** | Remains the **trigger** to **start** signing once payment rules are met (or move trigger if product changes - document in a change log). |
| **`esign.services.sign_with_token` (stub)** | **Replaced or narrowed** when the provider owns signature capture; webhooks become the **source of truth** for “signed”. |
| **`listing.leased` / public search** | Unchanged in intent: **fully signed** lease ⇒ listing **leased** and hidden from anonymous discovery per product rules. |

---

## 5. Non-goals (unless explicitly added later)

- **Hand-drawn PNG pasted on PDF** as the sole compliance mechanism (without provider audit).
- **Guaranteed Ejari registration** from this flow alone - **registration** is a **separate** operational/legal step unless/until integrated with approved channels.
- **Choosing a single vendor** in this doc - selection is a **procurement + legal + security** decision.

---

## 6. Acceptance criteria (for “PDF signing done”)

- [x] **Dev/test:** A **PDF** exists per signing case (`contract_pdf`); **`signed_pdf`** updates with certificate pages after each party confirms (ReportLab + pypdf - replace with vendor for production).
- [ ] A **PDF** exists per signing case and is **immutable** after freeze (new terms ⇒ new version / new session).
- [ ] Both parties complete signing **on that PDF** via the **agreed provider**.
- [ ] **Signed PDF** (and certificate if available) **stored** and **retrievable** for support and authorised users.
- [ ] **Webhook (or equivalent)** updates app state; **renter-first** order preserved.
- [ ] **Counsel** has reviewed template wording and flow for **UAE/Dubai** use cases relevant to Yallastay.

---

## 7. References (internal)

- Technical runbook: [`setup.md`](./setup.md)
- Payments / Stripe: [`../payments/stripe-setup.md`](../payments/stripe-setup.md)
- Platform overview: [`../platform/vision-and-implementation.md`](../platform/vision-and-implementation.md)

---

*Document version: 1.0 - reflects engineering/product alignment on **PDF-based lease signing**; update when vendor or trigger rules change.*
