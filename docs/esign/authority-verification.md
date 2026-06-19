# How an authority can verify who participated in lease e-signing (Yallastay)

| | |
|---|---|
| **Audience** | Compliance, support, counsel, technical auditors |
| **Distribution** | **Client-facing** under NDA - briefing note, **not legal advice**. |

This note describes **what the current backend records** and **how to trace activity to the two contractual roles** (renter vs landlord/realtor) and **underlying user accounts**. It supports internal compliance, support, and counsel briefings. **It is not legal advice** - regulators may require additional evidence (identity proof, qualified signatures, Ejari, etc.).

---

## 1. What “these people” means in the system

| Layer | What it identifies |
|--------|---------------------|
| **Accounts** | Django **User** records (email, name fields, etc.) - the renter and the listing owner / realtor as registered on the platform. |
| **Reservation** | Links **one renter** (`reservation.user`) to **one listing**; the listing’s **`listed_by`** user is the landlord/realtor side for that deal. |
| **Lease signing case** | **`LeaseSigningSession`** - one row per reservation (`OneToOne` with `Reservation`). This is the **signing envelope** for that tenancy. |
| **Roles at signing** | **`actor_role`** on audit events is `renter` or `lister`, matching **which magic-link token** was used (`renter_token` vs `lister_token`). |

So: **people** are anchored in **User** + **Reservation**; **signing actions** are anchored in **`LeaseSigningSession`** + **`LeaseSigningAuditEvent`** + **stored PDF/signature files**.

---

## 2. How to tie audit events to the two parties

1. Start from **`LeaseSigningSession.id`** (or `reservation_id`).
2. Load **`session.reservation`**:
   - **Renter (tenant):** `reservation.user_id` → **User** (email, profile).
   - **Lister (landlord/realtor):** `reservation.listing.listed_by_id` → **User**.
3. Open **`LeaseSigningAuditEvent`** rows where **`session_id`** matches, ordered by **`created_at`**.
4. For each row, read **`actor_role`**:
   - **`renter`** → actions taken with the **renter** magic link (same session’s `renter_token`).
   - **`lister`** → actions taken with the **lister** magic link (`lister_token`).

**Important limitation:** The platform **does not** perform government biometric verification at the signing step. Access is **possession of the secret link** sent to each party’s registered email (product assumption: only the intended recipient opens it). An authority may ask how you **authenticate users** elsewhere (account signup, UAE ID on listing, etc.) - that is outside this single document.

---

## 3. What each audit event type shows

| `event_type` | Meaning for verification |
|--------------|-------------------------|
| `sign_preview_accessed` | That role opened the signing preview page (GET). |
| `contract_pdf_viewed` | That role loaded the contract PDF in the browser (GET `/pdf/`). |
| `electronic_consent_accepted` | First-time **UAE electronic consent** for that **role** on this session (references Decree-Law 46 / version in metadata). |
| `signature_committed` | A signature submission **succeeded** for that **role** (slot index in `metadata` if multi-placement). |
| `signing_session_completed` | Both parties had signed; session reached **completed**. |

Each row stores **`ip_address`**, **`user_agent`**, and **`metadata`** (e.g. non-reversible **`token_fp`** correlating events without storing the raw URL token).

---

## 4. What to produce for an inspection

| Artifact | Where | Why it matters |
|----------|--------|----------------|
| **Audit export** | DB: `esign_leasesigningauditevent` joined to `esign_leasesigningsession` | Timeline + role + IP/UA. |
| **Session row** | `esign_leasesigningsession` | Status, `renter_signed_at` / `lister_signed_at`, links to PDFs. |
| **Reservation + users** | `bookings_reservation` + `accounts_user` (or your user table) | Legal names/emails tied to renter vs lister. |
| **Signed PDF** | Storage path in `signed_pdf` | What was agreed and signature placement / certificate pages. |
| **Signature images** | `renter_signature_image` / `lister_signature_image` (and slot fields if used) | Drawn marks associated with each role. |
| **Contract integrity** | `contract_pdf_sha256` when set | Reference hash for the unsigned contract source. |
| **Django admin** | Read-only **Lease signing audit events** (if enabled in production) | Human-friendly review by session id. |

**Counsel** can turn this into a formal disclosure package (screenshots, signed PDFs, CSV extracts, chain-of-custody for exports).

---

## 5. Honest scope statement (for authorities)

- The implementation aims for **identifiable electronic records** (who did what, when, from which IP, with consent wording aligned to **UAE Federal Decree-Law No. 46 of 2021** framing).
- It is **not** a **qualified electronic signature** from a **TDRA-licensed trust service** unless/until you integrate one and store provider certificates.
- **Ejari / DLD** registration is a **separate** process unless you integrate it later.

---

## 6. Internal references

- Product/technical agreement: [`pdf-signing-agreement.md`](./pdf-signing-agreement.md)
- Models: `esign.models.LeaseSigningSession`, `esign.models.LeaseSigningAuditEvent`
- Audit helpers: `esign/audit.py` (`token_fingerprint`, consent version)

---

*Document version: 1.0 - update when signing flow, identity checks, or provider integration changes.*
