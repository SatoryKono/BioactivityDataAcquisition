from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

@dataclass(frozen=True, slots=True)
class PipelineRunSnapshot:
    pipeline: str
    run_type: str
    status: str
    provider: str | None
    run_id: str
    observed_unix: float

@dataclass(frozen=True, slots=True)
class WorkflowPipelineScopeInfo:
    pipeline: str
    run_type: str
    provider: str

@dataclass(frozen=True, slots=True)
class WorkflowRunSnapshot:
    workflow: str
    status: str
    provider: str
    run_id: str
    pipelines: tuple[WorkflowPipelineScopeInfo, ...]

@dataclass(frozen=True, slots=True)
class RehydrateResult:
    anchors: int
    pipeline_runs_seeded: int
    provider_universe_seeded: int
    stage_series_seeded: int
    workflow_anchors: int = 0
    workflow_expected_seeded: int = 0
    workflow_pipeline_expected_seeded: int = 0
    error: str | None = None
