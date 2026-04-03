"""Composition-facing adapter for composite Polars join execution."""

from __future__ import annotations

from bioetl.application.composite.join_execution import JoinExecutorService

PolarsJoinAdapter = JoinExecutorService

__all__ = ["PolarsJoinAdapter"]
