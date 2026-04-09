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
    enable_tracing: bool | None = None

    def merged_with(self, override: WorkflowRunOptionsConfig) -> WorkflowRunOptionsConfig:
        """Return a merged config where non-null override values win."""
        merged_values = {
            field.name: (
                override_value
                if (override_value := getattr(override, field.name)) is not None
                else getattr(self, field.name)
            )
            for field in fields(self)
        }
        return WorkflowRunOptionsConfig(**merged_values)

    def to_mapping(self) -> JsonDict:
        """Return non-null options as a plain mapping."""
        result: JsonDict = {}
        for field in fields(self):
            value = getattr(self, field.name)
            if value is None:
                continue
            if field.name == "multi_filter_ids" and isinstance(value, dict):
                result[field.name] = {
                    key: list(items)
                    for key, items in value.items()
                }
                continue
            if field.name == "filter_ids" and isinstance(value, tuple):
                result[field.name] = list(value)
                continue
            result[field.name] = value
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
        topologically_sorted_step_ids(
            cast("Sequence[_WorkflowStepLike]", self.steps)
        )

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
