"""Immutable workflow configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from bioetl.domain.types import JsonDict
from bioetl.domain.workflow._run_options_config import WorkflowRunOptionsConfig
from bioetl.domain.workflow.dag import topologically_sorted_step_ids

__all__ = [
    "TransformStepConfig",
    "WorkflowConfig",
    "WorkflowRunOptionsConfig",
    "WorkflowStep",
    "WorkflowStepConfig",
]

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bioetl.domain.workflow.dag import _WorkflowStepLike


@dataclass(frozen=True, slots=True)
class WorkflowStepConfig:
    """Declarative pipeline step in a workflow DAG."""

    step_id: str
    pipeline_name: str
    depends_on: tuple[str, ...] = ()
    run_options: WorkflowRunOptionsConfig = field(
        default_factory=WorkflowRunOptionsConfig
    )


@dataclass(frozen=True, slots=True)
class TransformStepConfig:
    """Declarative transform step in a workflow DAG."""

    step_id: str
    transform_name: str
    depends_on: tuple[str, ...] = ()
    config: JsonDict | None = None

    def __post_init__(self) -> None:
        if self.config is not None:
            object.__setattr__(self, "config", dict(self.config))


type WorkflowStep = WorkflowStepConfig | TransformStepConfig


@dataclass(frozen=True, slots=True)
class WorkflowConfig:
    """Complete workflow configuration root."""

    name: str
    steps: tuple[WorkflowStep, ...]
    defaults: WorkflowRunOptionsConfig = field(default_factory=WorkflowRunOptionsConfig)
    version: str = "1.0.0"

    def __post_init__(self) -> None:
        topologically_sorted_step_ids(cast("Sequence[_WorkflowStepLike]", self.steps))

    @property
    def step_ids(self) -> tuple[str, ...]:
        """Return workflow step IDs in declared order."""
        return tuple(step.step_id for step in self.steps)

    @property
    def topological_step_ids(self) -> tuple[str, ...]:
        """Return workflow step IDs in dependency order."""
        return topologically_sorted_step_ids(
            cast("Sequence[_WorkflowStepLike]", self.steps)
        )

    @property
    def pipeline_steps(self) -> tuple[WorkflowStepConfig, ...]:
        """Return only declarative pipeline steps in declared order."""
        return tuple(
            step for step in self.steps if isinstance(step, WorkflowStepConfig)
        )

    @property
    def pipeline_names(self) -> tuple[str, ...]:
        """Return unique pipeline names represented by this workflow."""
        pipeline_names: list[str] = []
        for step in self.pipeline_steps:
            if step.pipeline_name not in pipeline_names:
                pipeline_names.append(step.pipeline_name)
        return tuple(pipeline_names)

    @property
    def single_pipeline_name(self) -> str | None:
        """Return the concrete pipeline when the workflow targets exactly one."""
        if len(self.pipeline_names) != 1:
            return None
        return self.pipeline_names[0]

    @property
    def pipeline_context(self) -> str:
        """Return the handoff-safe pipeline context for workflow surfaces."""
        return self.single_pipeline_name or "unknown"

    @property
    def run_type_context(self) -> str:
        """Return the handoff-safe run_type context for workflow surfaces."""
        pipeline_name = self.single_pipeline_name
        if pipeline_name is None:
            return "All"
        run_options = next(
            (
                step.run_options
                for step in self.pipeline_steps
                if step.pipeline_name == pipeline_name
            ),
            WorkflowRunOptionsConfig(),
        )
        return self.defaults.merged_with(run_options).run_type or "incremental"

    @property
    def provider_context(self) -> str:
        """Return the inferred provider context for single-pipeline workflows."""
        pipeline_name = self.single_pipeline_name
        if pipeline_name is None:
            return "unknown"
        provider, _separator, _entity = pipeline_name.partition("_")
        return provider or pipeline_name

    @property
    def workflow_context_labels(self) -> dict[str, str]:
        """Return bounded hidden-context labels for workflow metrics."""
        return {
            "pipeline_context": self.pipeline_context,
            "run_type_context": self.run_type_context,
            "provider_context": self.provider_context,
        }

    def get_step(self, step_id: str) -> WorkflowStep | None:
        """Look up a workflow step by ``step_id``."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None
