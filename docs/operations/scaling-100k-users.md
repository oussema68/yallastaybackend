# Scaling toward ~100,000 users (capacity & architecture)

| | |
|---|---|
| **Audience** | Clients, partners, technical leadership |
| **Distribution** | **Client-facing** - indicative architecture; **not** a performance or uptime guarantee. |
| **Disclaimer** | Actual capacity depends on traffic patterns, hosting choices, and product changes. |

This note outlines a **practical path** for growing Yallastay (Django REST API, PostgreSQL, React SPA, Stripe, etc.) toward roughly **100k users**. It is **not** a capacity guarantee - actual load depends on **monthly actives**, **peak concurrency**, and **write-heavy flows** (bookings, messaging, payments).

**Related:** [`../SECURITY_CHECKLIST.md`](../SECURITY_CHECKLIST.md) (rate limits, WAF). Internal gap analysis: [`../product/mvp-gap-analysis.md`](../product/mvp-gap-analysis.md) (**internal**).

---

## 1. Define what “100k users” means

| Metric | Typical implication |
|--------|---------------------|
| **100k registered accounts** | Mostly storage + sporadic logins; moderate load if spread over months. |
| **100k MAU** (monthly active) | Steady API + DB capacity, caching, monitoring. |
| **High concurrent users** (e.g. thousands at once) | Horizontal scaling, connection pooling, often read replicas or stronger caching. |

**Peak concurrent sessions** and **writes per second** (messages, reservations, webhooks) usually matter more than total registered users.

---

## 2. Foundations (before scaling instances)

1. **Stateless API** - No reliance on single-server memory for sessions; JWT aligns with this. Long-running work must not block the HTTP request.
2. **Database connection pooling** - **PgBouncer** (or managed pooler) in front of PostgreSQL when multiple app workers/instances exist; avoid one connection per worker without limits.
3. **Indexes & queries** - Profile slow queries; avoid N+1 in serializers; index listing/search and message threads as usage patterns clarify.
4. **Background jobs** - **Celery** (or similar) + **Redis/RabbitMQ** for email, notifications, heavy PDF work, webhook retries.
5. **Media** - Object storage (**S3-compatible**), **signed URLs** for private docs, **CDN** for public/static assets.
6. **Observability** - Metrics (latency, error rate, queue depth), structured logs, error tracking (e.g. Sentry). You cannot tune what you do not measure.

---

## 3. Application tier

- **Horizontal scaling**: Multiple API processes/containers behind a **load balancer** with health checks.
- **Worker count** - Balance Gunicorn/Uvicorn workers vs CPU; cap total DB connections to match **pooler** limits.
- **Rate limiting** - **Edge** (WAF/CDN) + **app** (DRF throttles); tighten auth and payment-adjacent routes.

---

## 4. Database

- **Scale up** (larger Postgres) until CPU/I/O or connection limits justify the next step.
- **Read replica** - Useful when **reads** dominate (browse, dashboards, search); route read-only or eventually consistent reads carefully.
- **Partitioning** - Consider only for clearly hot, large tables (e.g. high-volume events); usually a later phase.
- **Backups & PITR** - Automated backups + **tested restores**; document RPO/RTO.

---

## 5. Caching

- **Redis** - Session store if moving away from pure JWT; throttle storage; short-lived cache for hot read paths; idempotency keys for payment-related operations where applicable.
- **HTTP caching** - Where responses are safe to cache (public or semi-public GETs), use short TTLs and validators; avoid caching personalized data without care.

---

## 6. Domain-specific hotspots (marketplace)

| Area | Direction |
|------|-----------|
| **Search / listings** | Strong indexes + possibly PostgreSQL full-text; **OpenSearch/Elasticsearch** if search becomes complex and load-heavy. |
| **Messaging** | Pagination, cap payload per request; async notification fan-out. |
| **Payments** | Stripe scales; keep **webhook handlers idempotent** and fast - confirm state in DB, offload heavy work to queues. |

---

## 7. Phased roadmap (indicative)

| Phase | Rough band | Focus |
|-------|------------|--------|
| **1** | Early production | Pooling, indexes, background jobs, object storage + CDN, monitoring, load-test critical paths (search → book → pay → message). |
| **2** | Growing MAU | **Horizontal** API replicas, Redis for cache + broker, tune Postgres, optional **read replica** for read-heavy paths. |
| **3** | High concurrency / large scale | Dedicated search tier if needed, multi-AZ DB, formal SLOs, load testing and incident playbooks. |

---

## 8. What you usually do *not* need on day one

- Microservices decomposition “because scale.”
- Postgres sharding (unless data size and ops clearly require it).
- Kubernetes (optional; managed containers or PaaS often suffice until complexity warrants it).

---

## 9. Maintenance

- **Owner:** Engineering + infrastructure.  
- **Update when:** Major infra changes (new region, new data store, search stack) or after load-test results.

---

*Adjust numbers to your real MAU, peak QPS, and hosting choices.*
