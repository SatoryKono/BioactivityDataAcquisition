# mypy: disable-error-code="misc,untyped-decorator"
"""Validation-focused schemas for composite pipeline configuration."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bioetl.domain.composite import (
    CompositeDQConfig,
    CrossValidationConfig,
    DQOverrideConfig,
    ExecutionConfig,
    LineageConfig,
)
from bioetl.domain.composite.cross_validation import (
    ComparisonMethod,
    EnricherFieldPairing,
    FieldComparisonSpec,
)
from bioetl.domain.config import (
    CrossFieldValidation as DomainCrossFieldValidation,
)
from bioetl.domain.config import FieldValidation as DomainFieldValidation
from bioetl.infrastructure.schemas.pipeline_config_common import (
    CrossFieldValidationConfig,
    FieldValidationConfig,
)


class DQOverrideSchema(BaseModel):
    """Pydantic schema for per-enricher DQ threshold override."""

    model_config = ConfigDict(extra="forbid")

    soft_fail_threshold: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Override soft threshold (0.0-1.0)"
    )
    hard_fail_threshold: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Override hard threshold (0.0-1.0)"
    )

    @model_validator(mode="after")
    def validate_threshold_order(self) -> DQOverrideSchema:
        """Ensure soft_fail_threshold < hard_fail_threshold when both set."""
        if (
            self.soft_fail_threshold is not None
            and self.hard_fail_threshold is not None
            and self.soft_fail_threshold >= self.hard_fail_threshold
        ):
            raise ValueError(
                "soft_fail_threshold must be less than hard_fail_threshold"
            )
        return self

    def to_domain(self) -> DQOverrideConfig:
        """Convert to immutable domain DQOverrideConfig.

        Returns:
            DQOverrideConfig instance with soft and hard fail threshold overrides.
        """
        return DQOverrideConfig(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
        )


class CompositeDQSchema(BaseModel):
    """Pydantic schema for composite data quality configuration."""

    model_config = ConfigDict(extra="forbid")

    dq_config_file: str | None = Field(
        default=None,
        description="Optional pointer to the external composite DQ bundle file",
    )
    soft_fail_threshold: float = Field(
        default=0.10, ge=0.0, le=1.0, description="Default soft threshold (0.0-1.0)"
    )
    hard_fail_threshold: float = Field(
        default=0.30, ge=0.0, le=1.0, description="Default hard threshold (0.0-1.0)"
    )
    enricher_overrides: dict[str, DQOverrideSchema] = Field(
        default_factory=dict, description="Per-enricher DQ threshold overrides"
    )
    required_fields: list[str] = Field(
        default_factory=list, description="Fields required in final Gold output"
    )
    field_validations: list[FieldValidationConfig] = Field(
        default_factory=list,
        description="Field-level validation rules for composite Gold output",
    )
    cross_field_validations: list[CrossFieldValidationConfig] = Field(
        default_factory=list,
        description="Cross-field validation rules for composite Gold output",
    )

    @model_validator(mode="after")
    def validate_threshold_order(self) -> CompositeDQSchema:
        """Ensure soft_fail_threshold < hard_fail_threshold."""
        if self.soft_fail_threshold >= self.hard_fail_threshold:
            raise ValueError(
                f"soft_fail_threshold ({self.soft_fail_threshold}) must be "
                f"< hard_fail_threshold ({self.hard_fail_threshold})"
            )
        return self

    def to_domain(self) -> CompositeDQConfig:
        """Convert to immutable domain CompositeDQConfig.

        Returns:
            CompositeDQConfig instance with thresholds, enricher overrides, and required fields.
        """
        overrides = {
            name: override.to_domain()
            for name, override in self.enricher_overrides.items()
        }
        return CompositeDQConfig(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
            enricher_overrides=overrides,
            required_fields=tuple(self.required_fields),
            field_validations=tuple(
                self._to_domain_field_validation(config)
                for config in self.field_validations
            ),
            cross_field_validations=tuple(
                self._to_domain_cross_field_validation(config)
                for config in self.cross_field_validations
            ),
        )

    @staticmethod
    def _to_domain_field_validation(
        config: FieldValidationConfig,
    ) -> DomainFieldValidation:
        return DomainFieldValidation(
            field=config.field,
            validation_type=config.type,
            nullable=config.nullable,
            severity=config.severity,
            severity_enricher=config.severity_enricher,
            min_value=config.min,
            max_value=config.max,
            pattern=config.pattern,
            allowed=tuple(config.allowed),
            max_length=config.max_length,
            validator=config.validator,
            error_message=config.error_message,
        )

    @staticmethod
    def _to_domain_cross_field_validation(
        config: CrossFieldValidationConfig,
    ) -> DomainCrossFieldValidation:
        return DomainCrossFieldValidation(
            name=config.name,
            fields=tuple(config.fields),
            condition=config.condition,
            severity=config.severity,
            trigger_field=config.trigger_field,
            required_field=config.required_field,
            validator=config.validator,
            error_message=config.error_message,
        )


class RetrySchema(BaseModel):
    """Pydantic schema for retry configuration."""

    max_attempts: int = Field(
        default=3, ge=0, description="Maximum retry attempts per enricher"
    )
    backoff_multiplier: float = Field(
        default=2.0, gt=0, description="Backoff multiplier for retries"
    )


class ExecutionSchema(BaseModel):
    """Pydantic schema for execution options."""

    max_concurrency: int = Field(
        default=4, gt=0, description="Maximum concurrent enrichers"
    )
    checkpoint_enabled: bool = Field(
        default=True, description="Enable checkpointing for resume"
    )
    retry: RetrySchema = Field(
        default_factory=RetrySchema, description="Retry configuration"
    )

    def to_domain(self) -> ExecutionConfig:
        """Convert to immutable domain ExecutionConfig.

        Returns:
            ExecutionConfig instance with concurrency, checkpoint, and retry settings.
        """
        return ExecutionConfig(
            max_concurrency=self.max_concurrency,
            checkpoint_enabled=self.checkpoint_enabled,
            retry_max_attempts=self.retry.max_attempts,
            retry_backoff_multiplier=self.retry.backoff_multiplier,
        )


class LineageSchema(BaseModel):
    """Pydantic schema for lineage tracking configuration."""

    track_field_sources: bool = Field(
        default=True, description="Track which source provided each field"
    )
    track_timestamps: bool = Field(
        default=True, description="Include enrichment timestamps"
    )
    track_status: bool = Field(
        default=True, description="Include per-record enrichment status"
    )
    provider_lookup_fields: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Per-provider mapping of lookup metadata field names",
    )
    track_source_for_fields: list[str] = Field(
        default_factory=list,
        description="Field names requiring source tracking for overlapping data",
    )

    def to_domain(self) -> LineageConfig:
        """Convert to immutable domain LineageConfig.

        Returns:
            LineageConfig instance with field source, timestamp, and status tracking settings.
        """
        return LineageConfig(
            track_field_sources=self.track_field_sources,
            track_timestamps=self.track_timestamps,
            track_status=self.track_status,
            provider_lookup_fields=self.provider_lookup_fields,
            track_source_for_fields=tuple(self.track_source_for_fields),
        )


class FieldComparisonSpecSchema(BaseModel):
    """Pydantic schema for a single field comparison specification."""

    field: str = Field(..., min_length=1, description="Unified Silver column name")
    method: Literal["exact", "fuzzy", "numeric_tolerance", "skip"] = Field(
        default="exact", description="Comparison method"
    )
    threshold: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Threshold for fuzzy/numeric"
    )

    def to_domain(self) -> FieldComparisonSpec:
        """Convert to domain FieldComparisonSpec.

        Returns:
            FieldComparisonSpec instance with field name, comparison method, and threshold.
        """
        return FieldComparisonSpec(
            field_name=self.field,
            method=ComparisonMethod(self.method),
            threshold=self.threshold,
        )


class EnricherFieldPairingSchema(BaseModel):
    """Pydantic schema for enricher field pairing."""

    enricher_pipeline: str = Field(
        ..., min_length=1, description="Enricher pipeline name"
    )
    fields: list[FieldComparisonSpecSchema] = Field(
        ..., min_length=1, description="Field comparison specs"
    )

    def to_domain(self) -> EnricherFieldPairing:
        """Convert to domain EnricherFieldPairing.

        Returns:
            EnricherFieldPairing instance with enricher pipeline name and field comparison specs.
        """
        return EnricherFieldPairing(
            enricher_pipeline=self.enricher_pipeline,
            fields=tuple(f.to_domain() for f in self.fields),
        )


class CrossValidationSchema(BaseModel):
    """Pydantic schema for cross-validation configuration."""

    enabled: bool = Field(default=True, description="Enable cross-validation")
    warning_threshold: int = Field(
        default=1, ge=1, description="Mismatches to trigger WARNING"
    )
    error_threshold: int = Field(
        default=2, ge=2, description="Mismatches to trigger ENRICHER_ERROR"
    )
    quarantine_threshold: int = Field(
        default=2, ge=1, description="Enricher errors to quarantine seed"
    )
    fuzzy_threshold: float = Field(
        default=0.8, gt=0.0, le=1.0, description="Jaccard threshold for fuzzy"
    )
    numeric_tolerance: float = Field(
        default=0.10, gt=0.0, le=1.0, description="Relative tolerance for numeric"
    )
    enricher_pairings: list[EnricherFieldPairingSchema] = Field(
        default_factory=list, description="Per-enricher field pairings"
    )

    @model_validator(mode="after")
    def validate_thresholds(self) -> Self:
        """Ensure warning_threshold < error_threshold."""
        if self.warning_threshold >= self.error_threshold:
            raise ValueError("warning_threshold must be < error_threshold")
        return self

    def to_domain(self) -> CrossValidationConfig:
        """Convert to domain CrossValidationConfig.

        Returns:
            CrossValidationConfig instance with thresholds, tolerances, and enricher pairings.
        """
        return CrossValidationConfig(
            enabled=self.enabled,
            warning_threshold=self.warning_threshold,
            error_threshold=self.error_threshold,
            quarantine_threshold=self.quarantine_threshold,
            fuzzy_threshold=self.fuzzy_threshold,
            numeric_tolerance=self.numeric_tolerance,
            enricher_pairings=tuple(p.to_domain() for p in self.enricher_pairings),
        )


__all__ = [
    "CompositeDQSchema",
    "CrossValidationSchema",
    "DQOverrideSchema",
    "EnricherFieldPairingSchema",
    "ExecutionSchema",
    "FieldComparisonSpecSchema",
    "LineageSchema",
    "RetrySchema",
]
