"""Logger protocol port."""

from __future__ import annotations

from typing import Any, Protocol, Self, runtime_checkable


@runtime_checkable
class LoggerPort(Protocol):
    """Port for structured logging."""

    def bind(self, **kwargs: Any) -> Self:  # Any: structlog-compatible API
        ...

    def info(self, _event: str, **kwargs: Any) -> Any:  # Any: structlog-compatible API
        ...

    def warning(
        self,
        _event: str,
        **kwargs: Any,  # Any: structlog-compatible API
    ) -> Any: ...  # Any: structlog-compatible API

    def error(self, _event: str, **kwargs: Any) -> Any:  # Any: structlog-compatible API
        ...

    def debug(self, _event: str, **kwargs: Any) -> Any:  # Any: structlog-compatible API
        ...

    def exception(
        self,
        _event: str,
        **kwargs: Any,  # Any: structlog-compatible API
    ) -> Any: ...  # Any: structlog-compatible API
