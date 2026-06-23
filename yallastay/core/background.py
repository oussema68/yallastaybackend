"""Best-effort async side effects for non-critical tasks (emails, notifications)."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings

logger = logging.getLogger(__name__)
_executor: ThreadPoolExecutor | None = None


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        workers = max(1, min(int(getattr(settings, "ASYNC_SIDE_EFFECT_WORKERS", 2)), 8))
        _executor = ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="ysidefx",
        )
    return _executor


def run_side_effect(task_name: str, fn, *args, **kwargs) -> None:
    """
    Run a side-effect task inline (tests) or in a background thread (prod).

    Errors are logged and swallowed so non-critical tasks do not fail API requests.
    """

    def _invoke():
        try:
            fn(*args, **kwargs)
        except Exception:
            logger.exception("side_effect_failed: %s", task_name)

    if not bool(getattr(settings, "ASYNC_SIDE_EFFECTS_ENABLED", False)):
        _invoke()
        return
    _get_executor().submit(_invoke)
