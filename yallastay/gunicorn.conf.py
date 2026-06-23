"""
Gunicorn config. Concurrency is env-tunable so you can scale on Railway WITHOUT code
changes - set these as service variables and redeploy:

  WEB_CONCURRENCY            worker processes (default 3). Rule of thumb: ~2x vCPU.
  GUNICORN_THREADS           threads per worker (default 4). Good for I/O-bound DB work.
  GUNICORN_TIMEOUT           seconds before a stuck worker is killed (default 60).
  GUNICORN_GRACEFUL_TIMEOUT  seconds to finish in-flight requests on reload (default 30).
  GUNICORN_KEEPALIVE         keep-alive seconds for idle connections (default 5).
  GUNICORN_MAX_REQUESTS      recycle a worker after N requests to bound memory (default 1000).

Effective concurrent requests per container ≈ workers * threads.
NOTE: each worker*thread can hold a DB connection - keep workers*threads*replicas
under your Postgres connection limit (or put PgBouncer in front). See the scaling notes.
"""

import os


def _int_env(key: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(key, "").strip() or default))
    except (TypeError, ValueError):
        return default


workers = _int_env("WEB_CONCURRENCY", 3)
threads = _int_env("GUNICORN_THREADS", 4)
worker_class = "gthread"  # threads only take effect with the threaded worker

timeout = _int_env("GUNICORN_TIMEOUT", 60)
graceful_timeout = _int_env("GUNICORN_GRACEFUL_TIMEOUT", 30)
keepalive = _int_env("GUNICORN_KEEPALIVE", 5)

# Recycle workers periodically so a slow leak can't degrade the service under load.
max_requests = _int_env("GUNICORN_MAX_REQUESTS", 1000)
max_requests_jitter = _int_env("GUNICORN_MAX_REQUESTS_JITTER", 100)

# Log to stdout/stderr so Railway captures it.
accesslog = "-"
errorlog = "-"
