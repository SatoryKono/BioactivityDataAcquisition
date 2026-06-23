"""Leaf result-context types for composite runner completion helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bioetl.application.composite.runtime_models import CompositeExecutionContext

__all__ = [
    "CompositeResultBuildContext",
    "CompositeResultBuildRequest",
    "_PreparedCompositeResultContext",
]


@dataclass(frozen=True, slots=True)
class CompositeResultBuildContext:
    """Explicit data required to assemble the final ``CompositeResult``."""

    artifacts: CompositeExecutionContext
    composite_name: str
    run_id: str
    start_time: float | None
    started_at: datetime | None
    original_run_id: str | None
    required_enrichers: frozenset[str]
    required_dependencies: frozenset[str]


@dataclass(frozen=True, slots=True)
class _PreparedCompositeResultContext:
    """Resolved completion metadata used for final result assembly."""

    artifacts: CompositeExecutionContext
    completed_at: datetime
    total_duration: float
    had_warnings: bool


CompositeResultBuildRequest = CompositeResultBuildContext
