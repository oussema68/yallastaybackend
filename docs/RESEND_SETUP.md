# Resend email (production)

Transactional mail (signup verification, password reset, listing notifications) uses Django’s **`emails`** app and **`DEFAULT_FROM_EMAIL`**. Production sends via **Resend SMTP**; all outbound mail should use **`demo@yallastay.ae`**.

## 1. Resend dashboard

1. Sign in at [resend.com](https://resend.com).
2. **Domains** → add **`yallastay.ae`** → add the DNS records Resend shows (SPF, DKIM, etc.) until status is **Verified**.
3. **API Keys** → create a key (starts with `re_`). Store it only in Railway / secrets - never in git.
4. Confirm you can send from **`demo@yallastay.ae`** (same verified domain).

## 2. Railway (API service variables)

Set on the **Django API** service (not the frontend):

```bash
DEFAULT_FROM_EMAIL=demo@yallastay.ae
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=resend
RESEND_API_KEY=re_your_key_here
```

Optional display name in the inbox:

```bash
DEFAULT_FROM_EMAIL=Yallastay Demo <demo@yallastay.ae>
```

Also required for verification links in emails:

```bash
BACKEND_URL=https://your-api-xxxx.up.railway.app
FRONTEND_URL=https://your-spa-xxxx.up.railway.app
```

Redeploy after saving variables.

## 3. Database

Email **templates** live in Postgres (migrations under `emails/`). On a fresh DB:

```bash
cd yallastay
python manage.py migrate --noinput
```

No `bootstrap_demo` required - template rows are created by migrations.

## 4. Verify

1. Register a new user on the live SPA.
2. Resend dashboard → **Emails** - should show a send to the registrant (`email_verification` template).
3. Backend **`EmailMessage`** rows should show `status=sent` (Django admin or DB).

Local dev stays on console backend unless you copy the SMTP vars into a gitignored `.env` (not recommended for day-to-day dev).

## Troubleshooting

| Symptom | Check |
|--------|--------|
| `EmailMessage` status `skipped` | `DEFAULT_FROM_EMAIL` empty or invalid |
| SMTP auth error | `RESEND_API_KEY` / `EMAIL_HOST_USER=resend` |
| Resend rejects sender | Domain not verified; From must be `@yallastay.ae` |
| No template | Run `migrate`; missing `emails_emailtemplate` |
| Broken verify link | `BACKEND_URL` must match public API URL |

Delivery/bounce webhooks in this repo target **SendGrid** (`/api/emails/webhooks/sendgrid/events/`). Resend delivery is tracked in the Resend dashboard until a Resend webhook is added.
