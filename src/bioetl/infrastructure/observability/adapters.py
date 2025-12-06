"""Infrastructure adapters for observability ports."""

from __future__ import annotations

from typing import Any, Self

import structlog
from structlog.stdlib import BoundLogger

from bioetl.domain.observability import LoggingPort, TracingPort


class StructuredLoggerImpl(LoggingPort):
    """Structured logger adapter built on top of structlog."""

    def __init__(self, logger: BoundLogger | None = None) -> None:
        self._logger = logger or structlog.get_logger()

    def info(self, msg: str, **ctx: Any) -> None:
        self._logger.info(msg, **ctx)

    def error(self, msg: str, **ctx: Any) -> None:
        self._logger.error(msg, **ctx)

    def debug(self, msg: str, **ctx: Any) -> None:
        self._logger.debug(msg, **ctx)

    def warning(self, msg: str, **ctx: Any) -> None:
        self._logger.warning(msg, **ctx)

    def bind(self, **ctx: Any) -> Self:
        return self.__class__(self._logger.bind(**ctx))


class TracingAdapterImpl(TracingPort):
    """No-op tracing adapter placeholder for distributed tracing backends."""

    def start_span(self, name: str) -> dict[str, str]:
        return {"span": name}

    def end_span(self, span: Any) -> None:  # pragma: no cover - no-op
        _ = span

    def inject_context(self, headers: dict[str, str]) -> None:  # pragma: no cover - no-op
        headers.update({"trace": "noop"})


__all__ = [
    "StructuredLoggerImpl",
    "TracingAdapterImpl",
]
