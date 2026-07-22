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
    "WorkflowReconcileForeignKeysConfigSchema",
    "WorkflowReconcileRowsConfigSchema",
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
    resume_run_id: str | None = None
    resume_manifest_id: str | None = None
    exact_replay: bool | None = None
    required_persistence_profile: (
        Literal["degraded_observable", "replay_ready", "forensic_grade"] | None
    ) = None
    enable_tracing: bool | None = None
    debug_export_enabled: bool | None = None
    debug_export_formats: list[str] | None = None
    debug_export_dir: str | None = None
    workflow_id: str | None = None

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
            resume_run_id=self.resume_run_id,
            resume_manifest_id=self.resume_manifest_id,
            exact_replay=self.exact_replay,
            required_persistence_profile=self.required_persistence_profile,
            enable_tracing=self.enable_tracing,
            debug_export_enabled=self.debug_export_enabled,
            debug_export_formats=(
                tuple(self.debug_export_formats)
                if self.debug_export_formats is not None
                else None
            ),
            debug_export_dir=self.debug_export_dir,
            workflow_id=self.workflow_id,
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


class WorkflowReconcileRowsConfigSchema(BaseModel):
    """Strict config schema for the deterministic reconcile_rows transform."""

    model_config = ConfigDict(extra="forbid")

    layer: Literal["silver", "gold"]
    left_table: str = Field(..., min_length=1)
    right_table: str = Field(..., min_length=1)
    left_columns: list[str] = Field(..., min_length=1)
    right_columns: list[str] = Field(..., min_length=1)
    left_primary_keys: list[str] = Field(..., min_length=1)
    nulls_equal: bool = False
    type_policy: Literal["strict"] = "strict"
    report_only: bool = True
    preserve_order: bool = True

    @model_validator(mode="after")
    def validate_reconciliation_invariants(self) -> Self:
        """Validate deterministic row reconciliation invariants."""
        self.left_table = _normalize_required_name(self.left_table, "left_table")
        self.right_table = _normalize_required_name(self.right_table, "right_table")
        self.left_columns = _normalize_required_names(
            self.left_columns,
            "left_columns",
        )
        self.right_columns = _normalize_required_names(
            self.right_columns,
            "right_columns",
        )
        self.left_primary_keys = _normalize_required_names(
            self.left_primary_keys,
            "left_primary_keys",
        )
        if len(self.left_columns) != len(self.right_columns):
            raise ValueError(
                "reconcile_rows left_columns and right_columns must have "
                "the same length"
            )
        return self

    def to_config_dict(self) -> JsonDict:
        """Return normalized config with explicit defaults for fingerprinting."""
        return dict(self.model_dump())


class WorkflowReconcileForeignKeysConfigSchema(BaseModel):
    """Strict config schema for the destructive reconcile_foreign_keys transform."""

    model_config = ConfigDict(extra="forbid")

    source_layer: Literal["silver", "gold"] = "silver"
    reference_layer: Literal["silver", "gold"] = "silver"
    mutation_layer: Literal["silver", "gold"] | None = None
    source_table: str = Field(..., min_length=1)
    reference_table: str = Field(..., min_length=1)
    source_key: str | None = None
    reference_key: str | None = None
    source_keys: list[str] | None = None
    reference_keys: list[str] | None = None
    primary_keys: list[str] = Field(..., min_length=1)
    action: Literal["delete_orphans"]
    nulls_equal: bool = False

    @model_validator(mode="after")
    def validate_foreign_key_invariants(self) -> Self:
        """Validate destructive foreign-key reconciliation invariants."""
        self.source_table = _normalize_fk_required_name(
            self.source_table,
            "source_table",
        )
        self.reference_table = _normalize_fk_required_name(
            self.reference_table,
            "reference_table",
        )
        self.primary_keys = _normalize_fk_required_names(
            self.primary_keys,
            "primary_keys",
        )
        if self.mutation_layer is not None and self.mutation_layer != self.source_layer:
            raise ValueError(
                "reconcile_foreign_keys mutation_layer must match source_layer"
            )
        self._validate_key_contract()
        return self

    def _validate_key_contract(self) -> None:
        source_key = _normalize_fk_optional_name(self.source_key, "source_key")
        reference_key = _normalize_fk_optional_name(
            self.reference_key,
            "reference_key",
        )
        source_keys = _normalize_fk_optional_names(self.source_keys, "source_keys")
        reference_keys = _normalize_fk_optional_names(
            self.reference_keys,
            "reference_keys",
        )
        _require_fk_key_pairs_present(
            source_key=source_key,
            reference_key=reference_key,
            source_keys=source_keys,
            reference_keys=reference_keys,
        )
        _require_fk_key_pairs_together(
            source_key=source_key,
            reference_key=reference_key,
            source_keys=source_keys,
            reference_keys=reference_keys,
        )
        _validate_fk_composite_alignment(
            source_key=source_key,
            reference_key=reference_key,
            source_keys=source_keys,
            reference_keys=reference_keys,
        )
        self.source_key = source_key
        self.reference_key = reference_key
        self.source_keys = source_keys
        self.reference_keys = reference_keys

    def to_config_dict(self) -> JsonDict:
        """Return normalized config with explicit layer defaults for fingerprinting."""
        return {
            key: value for key, value in self.model_dump().items() if value is not None
        }


class WorkflowTransformStepSchema(BaseModel):
    """Strict schema for transform workflow steps."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["transform"] = "transform"
    step_id: str = Field(..., min_length=1)
    transform_name: str = Field(..., min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    config: JsonDict | None = None

    @model_validator(mode="after")
    def validate_transform_config(self) -> Self:
        """Validate transform-specific config contracts when available."""
        if self.transform_name == "reconcile_rows":
            if self.config is None:
                raise ValueError("reconcile_rows requires config")
            self.config = WorkflowReconcileRowsConfigSchema.model_validate(
                self.config
            ).to_config_dict()
        elif self.transform_name == "reconcile_foreign_keys":
            if self.config is None:
                raise ValueError("reconcile_foreign_keys requires config")
            self.config = WorkflowReconcileForeignKeysConfigSchema.model_validate(
                self.config
            ).to_config_dict()
        return self

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


def _normalize_required_name(value: str, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"reconcile_rows {field_name} cannot be empty")
    return normalized


def _normalize_required_names(values: list[str], field_name: str) -> list[str]:
    normalized = [_normalize_required_name(value, field_name) for value in values]
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"reconcile_rows {field_name} cannot contain duplicates")
    return normalized


def _normalize_fk_required_name(value: str, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"reconcile_foreign_keys {field_name} cannot be empty")
    return normalized


def _normalize_fk_optional_name(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _normalize_fk_required_name(value, field_name)


def _normalize_fk_required_names(values: list[str], field_name: str) -> list[str]:
    normalized = [_normalize_fk_required_name(value, field_name) for value in values]
    if len(set(normalized)) != len(normalized):
        raise ValueError(
            f"reconcile_foreign_keys {field_name} cannot contain duplicates"
        )
    return normalized


def _normalize_fk_optional_names(
    values: list[str] | None,
    field_name: str,
) -> list[str] | None:
    if values is None:
        return None
    return _normalize_fk_required_names(values, field_name)


def _require_fk_key_pairs_present(
    *,
    source_key: str | None,
    reference_key: str | None,
    source_keys: list[str] | None,
    reference_keys: list[str] | None,
) -> None:
    single_pair_present = source_key is not None or reference_key is not None
    composite_pair_present = source_keys is not None or reference_keys is not None
    if not single_pair_present and not composite_pair_present:
        raise ValueError(
            "reconcile_foreign_keys requires source_key/reference_key or "
            "source_keys/reference_keys"
        )


def _require_fk_key_pairs_together(
    *,
    source_key: str | None,
    reference_key: str | None,
    source_keys: list[str] | None,
    reference_keys: list[str] | None,
) -> None:
    if (source_key is None) != (reference_key is None):
        raise ValueError(
            "reconcile_foreign_keys requires source_key and reference_key together"
        )
    if (source_keys is None) != (reference_keys is None):
        raise ValueError(
            "reconcile_foreign_keys requires source_keys and reference_keys together"
        )


def _require_matching_key_prefix(
    single_key: str | None,
    composite_keys: list[str],
    *,
    field_label: str,
) -> None:
    if single_key is not None and composite_keys[0] != single_key:
        raise ValueError(
            f"reconcile_foreign_keys {field_label} must match first {field_label}s"
        )


def _validate_fk_composite_alignment(
    *,
    source_key: str | None,
    reference_key: str | None,
    source_keys: list[str] | None,
    reference_keys: list[str] | None,
) -> None:
    if source_keys is None or reference_keys is None:
        return
    if len(source_keys) != len(reference_keys):
        raise ValueError(
            "reconcile_foreign_keys source_keys and reference_keys must have "
            "the same length"
        )
    _require_matching_key_prefix(source_key, source_keys, field_label="source_key")
    _require_matching_key_prefix(
        reference_key,
        reference_keys,
        field_label="reference_key",
    )


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
