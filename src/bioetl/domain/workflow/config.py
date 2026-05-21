"""Immutable workflow configuration models."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, cast

from bioetl.domain.types import JsonDict
from bioetl.domain.workflow._run_options_support import (
    prefer_override,
    prefer_stricter_persistence_profile,
    serialize_workflow_run_option_value,
)
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
class WorkflowRunOptionsConfig:
    """Partial run-options contract allowed in workflow YAML."""

    run_type: str | None = None
    resume: bool | None = None
    start_offset: int | None = None
    limit: int | None = None
    dry_run: bool | None = None
    input_csv: str | None = None
    filter_column: str | None = None
    filter_field: str | None = None
    filter_ids: tuple[str, ...] | None = None
    multi_filter_ids: dict[str, tuple[str, ...]] | None = None
    fallback_column: str | None = None
    fallback_mapping: dict[str, str] | None = None
    vacuum_after_run: bool | None = None
    vacuum_retention_days: int | None = None
    log_level: str | None = None
    ignore_yaml_filter: bool | None = None
    skip_gold: bool | None = None
    execution_context: str | None = None
    use_cached_bronze: bool | None = None
    cached_bronze_path: str | None = None
    cached_bronze_date: str | None = None
    replay_of_run_id: str | None = None
    replay_of_manifest_id: str | None = None
    exact_replay: bool | None = None
    required_persistence_profile: str | None = None
    enable_tracing: bool | None = None

    def merged_with(
        self, override: WorkflowRunOptionsConfig
    ) -> WorkflowRunOptionsConfig:
        """Return a merged config where non-null override values win."""
        return WorkflowRunOptionsConfig(
            run_type=prefer_override(self.run_type, override.run_type),
            resume=prefer_override(self.resume, override.resume),
            start_offset=prefer_override(self.start_offset, override.start_offset),
            limit=prefer_override(self.limit, override.limit),
            dry_run=prefer_override(self.dry_run, override.dry_run),
            input_csv=prefer_override(self.input_csv, override.input_csv),
            filter_column=prefer_override(
                self.filter_column,
                override.filter_column,
            ),
            filter_field=prefer_override(self.filter_field, override.filter_field),
            filter_ids=prefer_override(self.filter_ids, override.filter_ids),
            multi_filter_ids=prefer_override(
                self.multi_filter_ids,
                override.multi_filter_ids,
            ),
            fallback_column=prefer_override(
                self.fallback_column,
                override.fallback_column,
            ),
            fallback_mapping=prefer_override(
                self.fallback_mapping,
                override.fallback_mapping,
            ),
            vacuum_after_run=prefer_override(
                self.vacuum_after_run,
                override.vacuum_after_run,
            ),
            vacuum_retention_days=prefer_override(
                self.vacuum_retention_days,
                override.vacuum_retention_days,
            ),
            log_level=prefer_override(self.log_level, override.log_level),
            ignore_yaml_filter=prefer_override(
                self.ignore_yaml_filter,
                override.ignore_yaml_filter,
            ),
            skip_gold=prefer_override(self.skip_gold, override.skip_gold),
            execution_context=prefer_override(
                self.execution_context,
                override.execution_context,
            ),
            use_cached_bronze=prefer_override(
                self.use_cached_bronze,
                override.use_cached_bronze,
            ),
            cached_bronze_path=prefer_override(
                self.cached_bronze_path,
                override.cached_bronze_path,
            ),
            cached_bronze_date=prefer_override(
                self.cached_bronze_date,
                override.cached_bronze_date,
            ),
            replay_of_run_id=prefer_override(
                self.replay_of_run_id,
                override.replay_of_run_id,
            ),
            replay_of_manifest_id=prefer_override(
                self.replay_of_manifest_id,
                override.replay_of_manifest_id,
            ),
            exact_replay=prefer_override(self.exact_replay, override.exact_replay),
            required_persistence_profile=prefer_stricter_persistence_profile(
                self.required_persistence_profile,
                override.required_persistence_profile,
            ),
            enable_tracing=prefer_override(
                self.enable_tracing,
                override.enable_tracing,
            ),
        )

    def to_mapping(self) -> JsonDict:
        """Return non-null options as a plain mapping."""
        result: JsonDict = {}
        for field in fields(self):
            value = getattr(self, field.name)
            if value is None:
                continue
            result[field.name] = serialize_workflow_run_option_value(field.name, value)
        return result


@dataclass(frozen=True, slots=True)
class WorkflowStepConfig:
    """Declarative pipeline step in a workflow DAG."""

    step_id: str
    pipeline_name: str
    depends_on: tuple[str, ...] = ()
    run_options: WorkflowRunOptionsConfig = WorkflowRunOptionsConfig()


@dataclass(frozen=True, slots=True)
class TransformStepConfig:
    """Declarative transform step in a workflow DAG."""

    step_id: str
    transform_name: str
    depends_on: tuple[str, ...] = ()
    config: JsonDict | None = None


type WorkflowStep = WorkflowStepConfig | TransformStepConfig


@dataclass(frozen=True, slots=True)
class WorkflowConfig:
    """Complete workflow configuration root."""

    name: str
    steps: tuple[WorkflowStep, ...]
    defaults: WorkflowRunOptionsConfig = WorkflowRunOptionsConfig()
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
