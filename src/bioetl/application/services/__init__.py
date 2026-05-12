"""Compatibility re-exports for application service models.

This package intentionally stays thin and exposes only legacy public aliases
that are still imported by CLI and service-facing tests.
"""

from __future__ import annotations

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineNotFoundError,
    PipelineRunResult,
    RunOptions,
    RunResult,
)
from bioetl.application.services.export_models import (
    ColumnInfo,
    ExportOptions,
    ExportResult,
    TableInfo,
    TablePreview,
)
from bioetl.application.services.vacuum_service import (
    TableVacuumResult,
    VacuumAllResult,
)

__all__ = [
    "ColumnInfo",
    "ExportOptions",
    "ExportResult",
    "PipelineNotFoundError",
    "PipelineRunResult",
    "RunOptions",
    "RunResult",
    "TableInfo",
    "TablePreview",
    "TableVacuumResult",
    "VacuumAllResult",
]


def __dir__() -> list[str]:
    """Return stable service exports for introspection."""
    return sorted(set(globals()) | set(__all__))
