"""Tracing protocol port (OTel-compatible facade)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TracingPort(Protocol):
    """Port for distributed tracing."""

    def get_tracer(
        self,
        name: str,
    ) -> Any:  # Any: OTel Tracer-compatible object
        """Return OpenTelemetry-compatible tracer instance."""
        ...

    def close(self) -> None:
        """Flush pending spans and cleanup resources."""
        ...
