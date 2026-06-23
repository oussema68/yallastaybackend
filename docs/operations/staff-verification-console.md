# Staff verification console (brokers & owners)

| | |
|---|---|
| **Audience** | Engineering, operations, trusted Yallastay staff |
| **Purpose** | Document how to **grant access**, use the **SPA console**, call the **API**, and avoid common **localhost / hostname** pitfalls. |

Product rules for *what* to verify (documents, RERA, title deeds) stay in [`../product/uae-verification-pipeline.md`](../product/uae-verification-pipeline.md). This file covers **how the platform implements** staff review.

---

## 1. What it is

- **Frontend:** A dedicated **staff-only** Vite app in the sibling repo **`yallastay_staff`** (default dev **http://localhost:3001**). The marketplace (`yallastay`) shows header link **“Verify team”** when **`VITE_STAFF_APP_URL`** is set (opens the staff app in a **new tab**). JWTs live on the **staff origin** only - staff must **sign in on that app**, not rely on the main site session.
- **Backend:** JSON API under **`/api/staff/verification/`** (JWT). Each pending broker/owner row includes a **document checklist** (required vs uploaded) and flags **`checklist_complete`** (informational; staff may still approve with business judgment).
- **Django Admin** remains valid: approving **`RealtorProfile`** / **`LandlordProfile`** in admin does the same as **Approve** in the console (same models and signals).

---

## 2. Verification specialist accounts (what “a staff profile” is)

**Terminology.** The product does **not** maintain a separate “staff profile” entity. A **verification specialist** is a normal **user account** that has been explicitly granted permission to call the staff verification API and use the **verification console** SPA. The same identity can exist in the marketplace database as any other user; what changes is the **authorisation flag** on that account.

**Who may access** - any authenticated user who satisfies **at least one** of the following (enforced by `accounts.staff_permissions.IsVerificationStaff`):

| Mechanism | Where it is set |
|-----------|-----------------|
| **`UserProfile.can_verify_documents`** | Django Admin → **Accounts → User profiles** → enable **Can verify documents** |
| **`User.is_staff`** | Django Admin → **Users** |
| **`User.is_superuser`** | Superuser accounts |

**Least privilege (recommended).** For operators who **only** review broker and landlord verification queues, prefer **`can_verify_documents`** over Django **staff** or **superuser**, so they are not implicitly authorised for Django Admin or other staff-only surfaces unless your organisation deliberately combines those roles.

**`GET /api/auth/me/`** exposes **`profile.can_verify_documents`** (read-only) so the **marketplace** header can show **Verify team** when **`VITE_STAFF_APP_URL`** is set; the **staff** app uses the same check before loading the queue.

---

## 3. Provisioning procedure (production)

Use this sequence when onboarding a new verification specialist; adjust steps to match your internal access-management policy (ticketing, manager approval, etc.).

1. **Identity** - Assign a dedicated work email (or approved shared mailbox policy) and record who is being provisioned and on whose authority.
2. **User account** - Create the user in your normal process (self-registration on a controlled route, or Django Admin → **Users** → **Add user** with a strong initial password and **force password change** if your policy requires it).
3. **Profile** - Ensure an **Accounts → User profiles** row exists for that user (created automatically on signup in typical flows).
4. **Authorisation** - Open that profile in Django Admin and enable **Can verify documents**. Do **not** enable Django **staff** unless this person also needs Admin.
5. **First login** - Direct the specialist to the **deployed verification console URL** (see §6 for local vs production). They authenticate with JWT on the **staff origin** only; the marketplace session does not grant console access by itself.
6. **Optional discovery** - If the main app exposes **Verify team**, it is a convenience link; the specialist must still complete sign-in on the staff app origin.
7. **Offboarding** - On role change or departure, remove **Can verify documents** (and revoke **staff** / deactivate the user) promptly; treat the flag as **privileged access** (see §9).

---

## 4. Demo / local seed account

After **`python manage.py seed_demo`** (or **`bootstrap_demo`**):

| Field | Value |
|-------|--------|
| Staff console login | `demo.verify@present.yallastay` |
| Password | `DemoPresent2026!` (same as other `seed_demo` accounts) |

That user has **`can_verify_documents=True`**.

**Queue fixtures (re-run `seed_demo` to restore after you approve them in the console):**

| Account | Role in demo |
|---------|----------------|
| `demo.realtor-pending@present.yallastay` | Pending **realtor** (private brokerage) in queue |
| `demo.owner-pending@present.yallastay` | Pending **landlord** in queue |

Also documented in [`../DEMO_PRESENTATION.md`](../DEMO_PRESENTATION.md).

---

## 5. API reference

All routes require **`Authorization: Bearer <access_token>`** unless noted.

| Method | Path | Body | Success |
|--------|------|------|---------|
| `GET` | `/api/staff/verification/queue/` | - | `200` - `{ "realtors": [...], "landlords": [...] }` |
| `POST` | `/api/staff/verification/realtors/<user_id>/decision/` | `{"action":"approve"}` or `{"action":"reject","message":"..."}` | `200` |
| `POST` | `/api/staff/verification/landlords/<user_id>/decision/` | same | `200` |

- **`reject`:** sends an **in-app notification** (`notifications.services.notify_user`) with optional **`message`**; does not flip an already-unapproved profile beyond clearing approval if it was set.
- **`approve`:** sets **`is_approved`** and **`approved_at`** (same behaviour as admin actions; realtor/landlord approval emails/notifications follow existing signals).

**403** if the JWT user is not verification staff.

**Manual curl-style matrix:** [`../MANUAL_TESTING.md`](../MANUAL_TESTING.md) → *Staff verification (brokers & owners)*.

---

## 6. Localhost and origins (important)

JWT access + refresh tokens are stored in **`localStorage`**, which is **scoped per origin** (scheme + host + port). The staff console is a **separate dev server** (port **3001** by default) from the marketplace (**3000**).

| Scenario | What to do |
|----------|------------|
| **Normal local dev** | Run **`yallastay_staff`** (`npm run dev` → **http://localhost:3001**). Sign in there with a verification-staff user. Ensure Django **dev** `CORS_ALLOWED_ORIGINS` includes `http://localhost:3001` (default in repo `settings/dev.py`). |
| **Marketplace header link** | In **`yallastay`**, set **`VITE_STAFF_APP_URL=http://localhost:3001`**. “Verify team” only appears for users who **could** use the console (`can_verify_documents` / staff); they still **log in on :3001** to act. |
| **Production** | Deploy **`yallastay_staff`** static build on e.g. **`staff.yourdomain.com`**. Build with **`VITE_API_URL`** pointing at your API. Add that staff origin to **`CORS_ALLOWED_ORIGINS`** on the API. Set **`VITE_STAFF_APP_URL`** on the main frontend to the staff site URL. |
| **Session expired** | Staff app redirects to **`/login?next=/`** on the **staff** origin after refresh failure. |

Frontend env: **`yallastay/.env.example`** (`VITE_STAFF_APP_URL`), **`yallastay_staff/.env.example`** (`VITE_API_URL`, `VITE_MAIN_APP_URL`).

---

## 7. Viewing applicant documents

Verification staff may **`GET /api/documents/<id>/`** for **any** user’s document row (see `documents.access.user_can_read_document`). The SPA “**View**” link on a checklist item uses that endpoint, then opens the file URL (with `VITE_MEDIA_ORIGIN` / proxy as for the rest of the app).

---

## 8. Checklist logic (engineering)

Implemented in **`accounts/verification_checklist.py`**:

- **Realtors:** trade licence, RERA broker card, passport, residence visa; agency brokers also ORN (and optional agency-specific types per model).
- **Landlords:** passport, UAE ID scan; **residence visa** required when **`LandlordProfile.is_emirati`** is **`False`**.

---

## 9. Security notes (brief)

- Treat **`can_verify_documents`** like a **privileged role**: only trusted staff; revoke via admin when someone leaves.
- **Approve** is authoritative for **`is_approved`**; combine with your internal SOP (who may override an incomplete checklist).
- The **stub payment webhook** and other production topics are unchanged; see [`../SECURITY_CHECKLIST.md`](../SECURITY_CHECKLIST.md).

---

## 10. Related documents

| Doc | Link |
|-----|------|
| Demo script & demo verify account | [`../DEMO_PRESENTATION.md`](../DEMO_PRESENTATION.md) |
| Manual API tests (staff section) | [`../MANUAL_TESTING.md`](../MANUAL_TESTING.md) |
| UAE verification product rules | [`../product/uae-verification-pipeline.md`](../product/uae-verification-pipeline.md) |
| Full-stack runbook | [`../USAGE_GUIDE.md`](../USAGE_GUIDE.md) |
| Platform workflows | [`../platform/vision-and-implementation.md`](../platform/vision-and-implementation.md) |
