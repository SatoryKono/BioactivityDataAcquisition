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
        """Return OpenTelemetry-compatible tracer instance.

        Args:
            name: Tracer name, typically the instrumented module or component name.

        Returns:
            OTel-compatible Tracer object for creating spans.
        """
        ...

    def close(self) -> None:
        """Flush pending spans and cleanup resources."""
        ...

    def flush(self) -> None:
        """Best-effort flush of pending spans without shutting the provider down."""
        ...
