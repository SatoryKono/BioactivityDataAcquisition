"""CrossRef datasource input validation helpers."""

from __future__ import annotations

from bioetl.domain.ports import LoggerPort
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.config._base import Settings


def resolve_mailto(kwargs: dict[str, object], settings: Settings | None) -> str:
    mailto_raw = kwargs.get("mailto")
    mailto = mailto_raw if isinstance(mailto_raw, str) and mailto_raw else None
    if not mailto and settings:
        mailto = getattr(settings, "default_email", None)
    if not mailto:
        raise ValueError(
            "CrossRef adapter requires mailto. "
            "Provide via 'mailto' kwarg or settings.default_email"
        )
    return mailto


def require_dependencies(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
) -> tuple[UnifiedHTTPClient, LoggerPort]:
    if http_client is None:
        raise ValueError("CrossRef adapter requires http_client")
    if logger is None:
        raise ValueError("CrossRef adapter requires logger")
    return http_client, logger
