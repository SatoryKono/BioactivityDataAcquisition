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
    reject_delete_orphans_after_limited_extracts,
)
from bioetl.domain.workflow.config import WorkflowReferenceCohort
from bioetl.infrastructure.schemas.workflow_config_fk import (
    _normalize_fk_optional_name,
    _normalize_fk_optional_names,
    _normalize_fk_required_name,
    _normalize_fk_required_names,
    _require_fk_key_pairs_present,
    _require_fk_key_pairs_together,
    _validate_fk_composite_alignment,
)
from bioetl.infrastructure.schemas.workflow_run_options import (
    WorkflowDefaultsSchema,
    WorkflowRunOptionsSchema,
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


class WorkflowReferenceCohortSchema(BaseModel):
    """Strict selection binding; no independently sampled reference universe."""

    model_config = ConfigDict(extra="forbid")
    step_id: str = Field(..., min_length=1)
    table: str = Field(..., pattern=r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
    column: str = Field(..., min_length=1)
    filter_field: str = Field(..., min_length=1)


class WorkflowPipelineStepSchema(BaseModel):
    """Strict schema for pipeline workflow steps."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["pipeline"] = "pipeline"
    step_id: str = Field(..., min_length=1)
    pipeline_name: str = Field(..., min_length=1)
    reference_cohort: WorkflowReferenceCohortSchema | None = None
    depends_on: list[str] = Field(default_factory=list)
    run_options: WorkflowRunOptionsSchema = Field(
        default_factory=WorkflowRunOptionsSchema
    )

    def to_domain(self, *, defaults: WorkflowRunOptionsConfig) -> WorkflowStepConfig:
        """Convert pipeline step to immutable domain config."""
        return WorkflowStepConfig(
            step_id=self.step_id,
            pipeline_name=self.pipeline_name,
            reference_cohort=WorkflowReferenceCohort(
                **self.reference_cohort.model_dump()
            )
            if self.reference_cohort
            else None,
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
    require_closed_cohort: bool = False
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
    reconciliation_mode: Literal["complete-reference", "selected-snapshot"] = (
        "complete-reference"
    )
    source_scope: Literal["all_current", "current_run"] = "all_current"
    nulls_equal: bool = False
    require_closed_cohort: bool = False

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
        values = self.model_dump()
        if self.reconciliation_mode == "complete-reference":
            values.pop("reconciliation_mode")
        if self.source_scope == "all_current":
            values.pop("source_scope")
        return {key: value for key, value in values.items() if value is not None}


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
            domain = self.to_domain()
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        from bioetl.domain.workflow._delete_orphans_scope import (
            apply_reconciliation_mode,
        )

        domain = apply_reconciliation_mode(domain)
        reject_delete_orphans_after_limited_extracts(domain)
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
        from bioetl.domain.workflow._delete_orphans_scope import (
            apply_reconciliation_mode,
        )

        return apply_reconciliation_mode(
            WorkflowConfig(
                name=self.name,
                version=self.version,
                defaults=defaults,
                steps=steps,
            )
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
