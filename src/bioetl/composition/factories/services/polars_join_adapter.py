"""Composition-facing adapter for composite Polars join execution."""

from __future__ import annotations

from bioetl.application.composite.join_execution import JoinExecutorService


class PolarsJoinAdapter:
    """Adapter wrapper for JoinExecutorService in composition layer.

    This real adapter provides composition-specific interface and behavior
    while delegating to the underlying JoinExecutorService.
    """

    def __init__(self, join_service: JoinExecutorService) -> None:
        """Initialize adapter with underlying join service.

        Args:
            join_service: The JoinExecutorService to adapt
        """
        self._join_service = join_service

    def get_polars_join_type(self):
        """Get current join type from adapted service."""
        return self._join_service.get_polars_join_type()

    def execute_polars_join(self, *args, **kwargs):
        """Execute join through adapted service."""
        return self._join_service.execute_polars_join(*args, **kwargs)


__all__ = ["PolarsJoinAdapter"]
