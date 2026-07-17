"""Secret redaction utilities for exception handling.

Extracted from base.py to reduce file size and improve separation of concerns.
"""

from __future__ import annotations

import re
from urllib.parse import SplitResult, urlsplit, urlunsplit

_SECRET_MARKERS = (
    "password",
    "passwd",
    "token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "private_key",
)
_INLINE_SECRET = re.compile(
    r"(?i)\b(password|passwd|token|secret|api[_-]?key|authorization)\b"
    r"\s*[:=]\s*([^\s,;&]+)"
)
_BEARER_SECRET = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_PREFIXED_SECRET = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:sk[-_]|gh[pousr]_|xox[baprs]-)[A-Za-z0-9._-]+"
)
_EMBEDDED_URL = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s<>'\"]+")


def _redact_inline_secrets(value: str) -> str:
    """Redact inline secret patterns like password=xyz."""
    return _INLINE_SECRET.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)


def _redact_url_hostname(parsed: SplitResult) -> str:
    """Extract and format hostname with optional port."""
    hostname = parsed.hostname or ""
    port = parsed.port
    if port is not None:
        hostname = f"{hostname}:{port}"
    return hostname


def _redact_url(value: str) -> str:
    """Remove user info, query values, and fragments from one URL."""
    try:
        parsed = urlsplit(value)
        hostname = _redact_url_hostname(parsed)
    except ValueError:
        return "[REDACTED URL]"
    if not parsed.scheme or not parsed.netloc:
        return value
    query = "[REDACTED]" if parsed.query else ""
    return urlunsplit((parsed.scheme, hostname, parsed.path, query, ""))


def _redact_string(value: str) -> str:
    """Redact secrets from string values."""
    redacted = _redact_embedded_urls(value)
    redacted = _redact_bearer_tokens(redacted)
    redacted = _redact_prefixed_secrets(redacted)
    return _redact_inline_secrets(redacted)


def _redact_embedded_urls(value: str) -> str:
    """Redact embedded URLs in string values."""
    return _EMBEDDED_URL.sub(lambda match: _redact_url(match.group()), value)


def _redact_bearer_tokens(value: str) -> str:
    """Redact Bearer tokens in string values."""
    return _BEARER_SECRET.sub("Bearer [REDACTED]", value)


def _redact_prefixed_secrets(value: str) -> str:
    """Redact prefixed secret patterns in string values."""
    return _PREFIXED_SECRET.sub("[REDACTED]", value)


def _is_secret_key(key: str) -> bool:
    """Check if a key name indicates a secret field."""
    normalized_key = key.lower().replace("-", "_").replace(" ", "_")
    return any(marker in normalized_key for marker in _SECRET_MARKERS)


def _redact_dict(value: dict[object, object]) -> dict[str, object]:
    """Redact dictionary values recursively."""
    return {str(k): _redact(v, str(k)) for k, v in value.items()}


def _redact_sequence(
    value: list[object] | tuple[object, ...],
    key: str,
) -> list[object] | tuple[object, ...]:
    """Redact sequence values recursively."""
    return type(value)(_redact(v, key) for v in value)


def _redact_set(value: set[object] | frozenset[object], key: str) -> list[object]:
    """Redact unordered values into a deterministic JSON-safe list."""
    redacted = [_redact(item, key) for item in value]
    return sorted(redacted, key=repr)


def _redact_exception(value: BaseException) -> dict[str, object]:
    """Redact exception to structured format."""
    return {
        "error_type": type(value).__name__,
        "message": _redact_string(str(value)),
    }


def _redact(value: object, key: str = "") -> object:
    """Recursively redact secrets from structured data."""
    if _is_secret_key(key):
        return "[REDACTED]"
    if isinstance(value, BaseException):
        return _redact_exception(value)
    if isinstance(value, str):
        return _redact_string(value)
    if isinstance(value, (dict, list, tuple, set, frozenset)):
        return _redact_structured(value, key)
    return value


def _redact_structured(value: object, key: str) -> object:
    """Redact structured types (dict, list, tuple, set)."""
    if isinstance(value, dict):
        return _redact_dict(value)
    if isinstance(value, (list, tuple)):
        return _redact_sequence(value, key)
    if isinstance(value, (set, frozenset)):
        return _redact_set(value, key)
    return value
