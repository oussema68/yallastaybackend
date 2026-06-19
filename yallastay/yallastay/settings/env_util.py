"""Helpers to read typed configuration from the environment (no secrets in code)."""

from __future__ import annotations


def env_str(key: str, default: str = "") -> str:
    import os

    return (os.environ.get(key) or default).strip()


def env_int(
    key: str,
    default: int,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    import os

    raw = (os.environ.get(key) or "").strip()
    if not raw:
        return default
    try:
        v = int(raw, 10)
    except ValueError:
        return default
    if min_value is not None and v < min_value:
        return min_value
    if max_value is not None and v > max_value:
        return max_value
    return v


def env_bool(key: str, default: bool = False) -> bool:
    import os

    raw = (os.environ.get(key) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def env_csv(key: str, default: list[str] | None = None) -> list[str]:
    """Comma-separated non-empty strings."""
    import os

    raw = (os.environ.get(key) or "").strip()
    if not raw:
        return list(default) if default is not None else []
    return [part.strip() for part in raw.split(",") if part.strip()]
