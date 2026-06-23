# Monitoring, alerts, and backups

| | |
|---|---|
| **Audience** | DevOps, on-call, engineering leads |
| **Purpose** | Operational baseline: **observability** (Sentry, uptime), **alerts** on **5xx** and **payment/webhook** failures, and **backup / restore** discipline. |

---

## Error tracking (e.g. Sentry)

1. Create a **Sentry** (or similar) project for the Django API and optionally a separate project for the SPA.  
2. Install the SDK (e.g. `sentry-sdk` for Python), initialize in **`wsgi.py`** / **`asgi.py`** with **DSN from environment** only (`SENTRY_DSN`).  
3. Set **environment** (`staging` / `production`) and **release** (git SHA or version).  
4. **Do not** send PII in breadcrumbs; scrub tokens and passwords.  
5. **Sample rate**: lower in high-traffic environments if needed.

**Alerting in Sentry:** create alert rules for **new issues**, **regression**, and **high error volume** on the production environment.

---

## Uptime monitoring

1. Use an external monitor (e.g. **Better Stack**, **Pingdom**, **UptimeRobot**, cloud load balancer health checks) against a **public** URL.  
2. **Probe target:** **`GET /`**: returns JSON `{"message": "Yallastay API", "status": "ok"}` (see **`core.tests.test_api_health_smoke`**).  
3. Optionally add a **`/health/`** or **`/ready/`** endpoint later that checks DB connectivity; keep it **fast** and **unauthenticated** for probes.  
4. **SLA:** define expected response time and regions; page on-call if probes fail **N** times in **M** minutes.

---

## Alerts: 5xx and payment / webhook failures

| Signal | Suggested source | Action |
|--------|------------------|--------|
| **HTTP 5xx** rate | Reverse proxy / CDN / app metrics | Page or ticket; link to Sentry |
| **Stripe webhook** `4xx/5xx` or signature failures | Stripe Dashboard → Webhooks → logs | Fix endpoint or secret rotation |
| **Application logs** | `payment.initiate.stripe.failed`, `payment.webhook.stub` with `not_found`, `esign.*` exceptions | Triage in Sentry / log store |
| **DB / queue** | Managed service alarms | Scale or failover runbook |

**Stripe:** enable **email** on failed webhook deliveries in the Dashboard; mirror critical failures into Slack/PagerDuty via Sentry or log-based alerts.

**Django:** ensure **`LOGGING`** captures **`payments`**, **`esign`**, **`payments.stripe_service`** at **INFO**/**ERROR** in production (see `settings/base.py` loggers).

---

## Backups

1. **PostgreSQL** (production): use the provider’s **automated backups** (point-in-time recovery if available).  
2. **Retention**: align with policy (e.g. 7-35 days); **test** restores quarterly.  
3. **Secrets**: backup **encryption keys** and **off-site** credential storage separately from DB dumps.  
4. **Object storage** (e.g. S3 for media): **versioning** + **lifecycle** rules; separate bucket or prefix for **sensitive** documents if required. Configure uploads via env; see [`media-storage-s3.md`](./media-storage-s3.md).

---

## Dated restore test (required discipline)

Run at least **quarterly** (and after major infra changes):

| # | Step | Record |
|---|------|--------|
| 1 | Pick a **backup timestamp** **T** (e.g. yesterday 00:00 UTC). | Ticket ID |
| 2 | Restore to an **isolated** DB instance or schema (never overwrite prod). | Instance name |
| 3 | Run **`migrate`** if needed and **smoke** `GET /` + one authenticated read-only query. | Pass/fail |
| 4 | **Document** outcome and **time to restore** in the ticket. | Date signed |

This proves backups are **restorable**, not merely “enabled.”

---

## Synthetic checks (optional)

- **POST** stub webhook in **staging** with a known test `transaction_id` (idempotent) to verify the **full hook path** periodically; use a **dedicated** test payment row, not production data.

---

## Related

- [`happy-path-e2e-checklist.md`](./happy-path-e2e-checklist.md): release happy path  
- [`../SECURITY_CHECKLIST.md`](../SECURITY_CHECKLIST.md)  
- [`../payments/stripe-setup.md`](../payments/stripe-setup.md)
