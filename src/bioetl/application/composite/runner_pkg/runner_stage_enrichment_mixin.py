"""Enrichment-stage helpers for composite runner stage orchestration."""

from __future__ import annotations

from bioetl.application.composite.runner_pkg.runner_stage_enrichment_completion_mixin import (
    _CompositeRunnerStageEnrichmentCompletionMixin,
)
from bioetl.application.composite.runner_pkg.runner_stage_enrichment_execution_mixin import (
    _CompositeRunnerStageEnrichmentExecutionMixin,
)

__all__ = ["_CompositeRunnerStageEnrichmentMixin"]


class _CompositeRunnerStageEnrichmentMixin(
    _CompositeRunnerStageEnrichmentExecutionMixin,
    _CompositeRunnerStageEnrichmentCompletionMixin,
):
    """Host mixin for enrichment phase execution and final transition."""
