"""
Render simple `{placeholder}` strings for transactional email/SMS templates.

Unknown placeholders resolve to empty strings so partial context is safe.
"""


class _SafeDict(dict):
    def __missing__(self, key):
        return ""


def render_template_string(template: str, context: dict | None = None) -> str:
    if not template:
        return ""
    context = context or {}
    safe = _SafeDict({k: str(v) if v is not None else "" for k, v in context.items()})
    try:
        return template.format_map(safe)
    except (ValueError, KeyError):
        # Invalid format string (e.g. unescaped braces) - return as-is for debugging in admin
        return template
