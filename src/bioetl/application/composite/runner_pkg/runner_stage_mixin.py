"""Stage execution helpers for CompositePipelineRunner."""

from __future__ import annotations

from bioetl.application.composite.runner_pkg.runner_merge_stage_mixin import (
    CompositeRunnerMergeStageMixin,
)
from bioetl.application.composite.runner_pkg.runner_stage_completion_mixin import (
    _CompositeRunnerStageCompletionMixin,
)
from bioetl.application.composite.runner_pkg.runner_stage_enrichment_mixin import (
    _CompositeRunnerStageEnrichmentMixin,
)
from bioetl.application.composite.runner_pkg.runner_stage_execution_mixin import (
    _CompositeRunnerStageExecutionMixin,
)
from bioetl.application.composite.runner_pkg.runner_stage_support_mixin import (
    _CompositeRunnerStageSupportMixin,
)

__all__ = ["CompositeRunnerStageMixin"]


class CompositeRunnerStageMixin(
    _CompositeRunnerStageExecutionMixin,
    _CompositeRunnerStageCompletionMixin,
    CompositeRunnerMergeStageMixin,
    _CompositeRunnerStageEnrichmentMixin,
    _CompositeRunnerStageSupportMixin,
):
    """Stage orchestration composed with merge helpers (ARCH-REF-R2 / #7729)."""
