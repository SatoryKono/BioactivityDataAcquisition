"""Composition-facing adapter for composite Polars join execution."""

from __future__ import annotations

from bioetl.application.composite.join_execution import JoinExecutorService

__all__ = ["PolarsJoinAdapter"]


class PolarsJoinAdapter(JoinExecutorService):
    """DI-friendly alias for the composite join executor used in composition."""
