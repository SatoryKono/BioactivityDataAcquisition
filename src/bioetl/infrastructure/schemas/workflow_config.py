# mypy: disable-error-code="misc,untyped-decorator"
"""Strict schema contract for declarative workflow configuration."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bioetl.domain.types import JsonDict
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowRunOptionsConfig,
    WorkflowStepConfig,
)

__all__ = [
    "RUN_OPTIONS_OVERRIDE_FIELD_NAMES",
    "WorkflowConfigFileSchema",
    "WorkflowConfigSchema",
    "WorkflowDefaultsSchema",
    "WorkflowPipelineStepSchema",
    "WorkflowRunOptionsSchema",
    "WorkflowTransformStepSchema",
    "validate_workflow_config_payload",
]


RUN_OPTIONS_OVERRIDE_FIELD_NAMES = frozenset(
    WorkflowRunOptionsConfig.__dataclass_fields__.keys()
)


class WorkflowRunOptionsSchema(BaseModel):
    """Strict partial schema for run-option overrides in workflow YAML."""

    model_config = ConfigDict(extra="forbid")

    run_type: str | None = None
    resume: bool | None = None
    start_offset: int | None = None
    limit: int | None = None
    dry_run: bool | None = None
    input_csv: str | None = None
    filter_column: str | None = None
    filter_field: str | None = None
    filter_ids: list[str] | None = None
    multi_filter_ids: dict[str, list[str]] | None = None
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

    def to_domain(self) -> WorkflowRunOptionsConfig:
        """Convert validated overrides into immutable domain config."""
        multi_filter_ids = self.multi_filter_ids
        return WorkflowRunOptionsConfig(
            run_type=self.run_type,
            resume=self.resume,
            start_offset=self.start_offset,
            limit=self.limit,
            dry_run=self.dry_run,
            input_csv=self.input_csv,
            filter_column=self.filter_column,
            filter_field=self.filter_field,
            filter_ids=tuple(self.filter_ids) if self.filter_ids is not None else None,
            multi_filter_ids=(
                {key: tuple(values) for key, values in multi_filter_ids.items()}
                if multi_filter_ids is not None
                else None
            ),
            fallback_column=self.fallback_column,
            fallback_mapping=(
                dict(self.fallback_mapping)
                if self.fallback_mapping is not None
                else None
            ),
            vacuum_after_run=self.vacuum_after_run,
            vacuum_retention_days=self.vacuum_retention_days,
            log_level=self.log_level,
            ignore_yaml_filter=self.ignore_yaml_filter,
            skip_gold=self.skip_gold,
            execution_context=self.execution_context,
            use_cached_bronze=self.use_cached_bronze,
            cached_bronze_path=self.cached_bronze_path,
            cached_bronze_date=self.cached_bronze_date,
            replay_of_run_id=self.replay_of_run_id,
            replay_of_manifest_id=self.replay_of_manifest_id,
            exact_replay=self.exact_replay,
            enable_tracing=self.enable_tracing,
        )


class WorkflowDefaultsSchema(BaseModel):
    """Root defaults applied to workflow steps."""

    model_config = ConfigDict(extra="forbid")

    run_options: WorkflowRunOptionsSchema = Field(
        default_factory=WorkflowRunOptionsSchema
    )

    def to_domain(self) -> WorkflowRunOptionsConfig:
        """Convert workflow defaults to immutable domain config."""
        return self.run_options.to_domain()


class WorkflowPipelineStepSchema(BaseModel):
    """Strict schema for pipeline workflow steps."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["pipeline"] = "pipeline"
    step_id: str = Field(..., min_length=1)
    pipeline_name: str = Field(..., min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    run_options: WorkflowRunOptionsSchema = Field(
        default_factory=WorkflowRunOptionsSchema
    )

    def to_domain(self, *, defaults: WorkflowRunOptionsConfig) -> WorkflowStepConfig:
        """Convert pipeline step to immutable domain config."""
        return WorkflowStepConfig(
            step_id=self.step_id,
            pipeline_name=self.pipeline_name,
            depends_on=tuple(self.depends_on),
            run_options=defaults.merged_with(self.run_options.to_domain()),
        )


class WorkflowTransformStepSchema(BaseModel):
    """Strict schema for transform workflow steps."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["transform"] = "transform"
    step_id: str = Field(..., min_length=1)
    transform_name: str = Field(..., min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    config: JsonDict | None = None

    def to_domain(self) -> TransformStepConfig:
        """Convert transform step to immutable domain config."""
        return TransformStepConfig(
            step_id=self.step_id,
            transform_name=self.transform_name,
            depends_on=tuple(self.depends_on),
            config=dict(self.config) if self.config is not None else None,
        )


WorkflowStepSchema = Annotated[
    WorkflowPipelineStepSchema | WorkflowTransformStepSchema,
    Field(discriminator="kind"),
]


class WorkflowConfigSchema(BaseModel):
    """Strict schema for the workflow section of a YAML file."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    version: str = Field(default="1.0.0", min_length=1)
    defaults: WorkflowDefaultsSchema = Field(default_factory=WorkflowDefaultsSchema)
    steps: list[WorkflowStepSchema] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_domain_invariants(self) -> Self:
        """Delegate duplicate/dependency/cycle checks to the domain layer."""
        try:
            self.to_domain()
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        return self

    def to_domain(self) -> WorkflowConfig:
        """Convert to immutable workflow domain config."""
        defaults = self.defaults.to_domain()
        steps = tuple(
            step.to_domain(defaults=defaults)
            if isinstance(step, WorkflowPipelineStepSchema)
            else step.to_domain()
            for step in self.steps
        )
        return WorkflowConfig(
            name=self.name,
            version=self.version,
            defaults=defaults,
            steps=steps,
        )


class WorkflowConfigFileSchema(BaseModel):
    """Strict schema for the full workflow YAML file."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="1.0.0", min_length=1)
    workflow: WorkflowConfigSchema

    def to_domain(self) -> WorkflowConfig:
        """Convert the YAML root object to immutable domain config."""
        return self.workflow.to_domain()


def validate_workflow_config_payload(payload: JsonDict) -> WorkflowConfigFileSchema:
    """Validate a workflow YAML payload against the strict runtime contract."""
    result: WorkflowConfigFileSchema = WorkflowConfigFileSchema.model_validate(payload)
    return result
