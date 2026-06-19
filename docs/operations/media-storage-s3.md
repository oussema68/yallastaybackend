# Media storage: database vs files vs S3

| | |
|---|---|
| **Facts** | **`ImageField` / `FileField`** store only a **path or key** in PostgreSQL; **not** the binary image/PDF inside the database row. |
| **Local dev** | Files live under **`MEDIA_ROOT`** (default: `yallastay/media/`). **`GET /media/...`** is served only when **`DEBUG=True`** (see `yallastay/urls.py`). |
| **Production** | Serve uploads from **object storage** (e.g. **AWS S3** in **`me-central-1`**), not from the app container disk. |

---

## Optional S3 (django-storages)

When **`AWS_STORAGE_BUCKET_NAME`** is set (and **`USE_S3_MEDIA`** is not `false`), the project uses **`S3Boto3Storage`** for the default file storage.

| Variable | Purpose |
|----------|---------|
| `AWS_STORAGE_BUCKET_NAME` | Bucket name (required to enable S3). |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Optional if using **IAM roles** (ECS, EC2, etc.); omit both and rely on the instance profile. |
| `AWS_S3_REGION_NAME` | Default `me-central-1`. |
| `AWS_S3_CUSTOM_DOMAIN` | Optional CDN hostname (e.g. CloudFront) for cleaner URLs. |
| `USE_S3_MEDIA` | Set `false` to force filesystem even when a bucket name is present (e.g. local debugging). |

API responses use **`core.media_urls.absolute_media_url`**, which supports **relative** `/media/...` URLs and **absolute** HTTPS URLs (S3 signed URLs).

**Tests** always use **local disk** (`TESTING` disables S3).

---

## Bucket policy (professional)

- Prefer **private** buckets; **`AWS_QUERYSTRING_AUTH`** is enabled so object access uses **time-limited signed URLs** in serializers.
- For public marketing images only, some teams use a **separate** public bucket or CloudFront with OAC; evolve as needed.

---

## Related

- [`monitoring-and-backups.md`](./monitoring-and-backups.md): backups including object storage versioning  
- [`../product/mvp-gap-analysis.md`](../product/mvp-gap-analysis.md): private document access hardening  
