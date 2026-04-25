"""Immutable workflow configuration models."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, TypeAlias, cast

from bioetl.domain.types import JsonDict
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


_RUN_OPTIONS_MULTI_FILTER_IDS = "multi_filter_ids"
_RUN_OPTIONS_FILTER_IDS = "filter_ids"


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
    enable_tracing: bool | None = None

    def merged_with(
        self, override: WorkflowRunOptionsConfig
    ) -> WorkflowRunOptionsConfig:
        """Return a merged config where non-null override values win."""
        return WorkflowRunOptionsConfig(
            run_type=override.run_type if override.run_type is not None else self.run_type,
            resume=override.resume if override.resume is not None else self.resume,
            start_offset=(
                override.start_offset
                if override.start_offset is not None
                else self.start_offset
            ),
            limit=override.limit if override.limit is not None else self.limit,
            dry_run=override.dry_run if override.dry_run is not None else self.dry_run,
            input_csv=override.input_csv if override.input_csv is not None else self.input_csv,
            filter_column=(
                override.filter_column
                if override.filter_column is not None
                else self.filter_column
            ),
            filter_field=(
                override.filter_field
                if override.filter_field is not None
                else self.filter_field
            ),
            filter_ids=(
                override.filter_ids if override.filter_ids is not None else self.filter_ids
            ),
            multi_filter_ids=(
                override.multi_filter_ids
                if override.multi_filter_ids is not None
                else self.multi_filter_ids
            ),
            fallback_column=(
                override.fallback_column
                if override.fallback_column is not None
                else self.fallback_column
            ),
            fallback_mapping=(
                override.fallback_mapping
                if override.fallback_mapping is not None
                else self.fallback_mapping
            ),
            vacuum_after_run=(
                override.vacuum_after_run
                if override.vacuum_after_run is not None
                else self.vacuum_after_run
            ),
            vacuum_retention_days=(
                override.vacuum_retention_days
                if override.vacuum_retention_days is not None
                else self.vacuum_retention_days
            ),
            log_level=override.log_level if override.log_level is not None else self.log_level,
            ignore_yaml_filter=(
                override.ignore_yaml_filter
                if override.ignore_yaml_filter is not None
                else self.ignore_yaml_filter
            ),
            skip_gold=override.skip_gold if override.skip_gold is not None else self.skip_gold,
            execution_context=(
                override.execution_context
                if override.execution_context is not None
                else self.execution_context
            ),
            use_cached_bronze=(
                override.use_cached_bronze
                if override.use_cached_bronze is not None
                else self.use_cached_bronze
            ),
            cached_bronze_path=(
                override.cached_bronze_path
                if override.cached_bronze_path is not None
                else self.cached_bronze_path
            ),
            cached_bronze_date=(
                override.cached_bronze_date
                if override.cached_bronze_date is not None
                else self.cached_bronze_date
            ),
            replay_of_run_id=(
                override.replay_of_run_id
                if override.replay_of_run_id is not None
                else self.replay_of_run_id
            ),
            replay_of_manifest_id=(
                override.replay_of_manifest_id
                if override.replay_of_manifest_id is not None
                else self.replay_of_manifest_id
            ),
            exact_replay=(
                override.exact_replay
                if override.exact_replay is not None
                else self.exact_replay
            ),
            enable_tracing=(
                override.enable_tracing
                if override.enable_tracing is not None
                else self.enable_tracing
            ),
        )

    def to_mapping(self) -> JsonDict:
        """Return non-null options as a plain mapping."""
        result: JsonDict = {}
        for field in fields(self):
            value = getattr(self, field.name)
            if value is None:
                continue
            result[field.name] = _serialize_workflow_run_option_value(field.name, value)
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


WorkflowStep: TypeAlias = WorkflowStepConfig | TransformStepConfig


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

    def get_step(self, step_id: str) -> WorkflowStep | None:
        """Look up a workflow step by ``step_id``."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None


def _serialize_workflow_run_option_value(field_name: str, value: object) -> object:
    """Serialize one workflow run-option value for JSON-compatible mappings."""
    if field_name == _RUN_OPTIONS_MULTI_FILTER_IDS:
        return _serialize_multi_filter_ids(value)
    if field_name == _RUN_OPTIONS_FILTER_IDS:
        return _serialize_filter_ids(value)
    return value


def _serialize_multi_filter_ids(value: object) -> object:
    """Serialize ``multi_filter_ids`` into a JSON-compatible mapping."""
    if not isinstance(value, dict):
        return value
    return {key: list(items) for key, items in value.items()}


def _serialize_filter_ids(value: object) -> object:
    """Serialize ``filter_ids`` into a JSON-compatible list."""
    if not isinstance(value, tuple):
        return value
    return list(value)
