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
            run_type=cast(
                str | None,
                _resolve_workflow_run_option_value(self, override, "run_type"),
            ),
            resume=cast(
                bool | None,
                _resolve_workflow_run_option_value(self, override, "resume"),
            ),
            start_offset=cast(
                int | None,
                _resolve_workflow_run_option_value(self, override, "start_offset"),
            ),
            limit=cast(
                int | None,
                _resolve_workflow_run_option_value(self, override, "limit"),
            ),
            dry_run=cast(
                bool | None,
                _resolve_workflow_run_option_value(self, override, "dry_run"),
            ),
            input_csv=cast(
                str | None,
                _resolve_workflow_run_option_value(self, override, "input_csv"),
            ),
            filter_column=cast(
                str | None,
                _resolve_workflow_run_option_value(self, override, "filter_column"),
            ),
            filter_field=cast(
                str | None,
                _resolve_workflow_run_option_value(self, override, "filter_field"),
            ),
            filter_ids=cast(
                tuple[str, ...] | None,
                _resolve_workflow_run_option_value(self, override, "filter_ids"),
            ),
            multi_filter_ids=cast(
                dict[str, tuple[str, ...]] | None,
                _resolve_workflow_run_option_value(self, override, "multi_filter_ids"),
            ),
            fallback_column=cast(
                str | None,
                _resolve_workflow_run_option_value(self, override, "fallback_column"),
            ),
            fallback_mapping=cast(
                dict[str, str] | None,
                _resolve_workflow_run_option_value(self, override, "fallback_mapping"),
            ),
            vacuum_after_run=cast(
                bool | None,
                _resolve_workflow_run_option_value(self, override, "vacuum_after_run"),
            ),
            vacuum_retention_days=cast(
                int | None,
                _resolve_workflow_run_option_value(
                    self, override, "vacuum_retention_days"
                ),
            ),
            log_level=cast(
                str | None,
                _resolve_workflow_run_option_value(self, override, "log_level"),
            ),
            ignore_yaml_filter=cast(
                bool | None,
                _resolve_workflow_run_option_value(
                    self, override, "ignore_yaml_filter"
                ),
            ),
            skip_gold=cast(
                bool | None,
                _resolve_workflow_run_option_value(self, override, "skip_gold"),
            ),
            execution_context=cast(
                str | None,
                _resolve_workflow_run_option_value(self, override, "execution_context"),
            ),
            use_cached_bronze=cast(
                bool | None,
                _resolve_workflow_run_option_value(self, override, "use_cached_bronze"),
            ),
            cached_bronze_path=cast(
                str | None,
                _resolve_workflow_run_option_value(
                    self, override, "cached_bronze_path"
                ),
            ),
            cached_bronze_date=cast(
                str | None,
                _resolve_workflow_run_option_value(
                    self, override, "cached_bronze_date"
                ),
            ),
            replay_of_run_id=cast(
                str | None,
                _resolve_workflow_run_option_value(self, override, "replay_of_run_id"),
            ),
            replay_of_manifest_id=cast(
                str | None,
                _resolve_workflow_run_option_value(
                    self, override, "replay_of_manifest_id"
                ),
            ),
            exact_replay=cast(
                bool | None,
                _resolve_workflow_run_option_value(self, override, "exact_replay"),
            ),
            enable_tracing=cast(
                bool | None,
                _resolve_workflow_run_option_value(self, override, "enable_tracing"),
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
        return cast(
            tuple[str, ...],
            topologically_sorted_step_ids(cast("Sequence[_WorkflowStepLike]", self.steps)),
        )

    def get_step(self, step_id: str) -> WorkflowStep | None:
        """Look up a workflow step by ``step_id``."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None


def _resolve_workflow_run_option_value(
    base: WorkflowRunOptionsConfig,
    override: WorkflowRunOptionsConfig,
    field_name: str,
) -> object | None:
    """Return one merged workflow run-option value."""
    override_value = getattr(override, field_name)
    if override_value is not None:
        return cast("object", override_value)
    return cast("object | None", getattr(base, field_name))


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
