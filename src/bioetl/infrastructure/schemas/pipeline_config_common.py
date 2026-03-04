"""Common Pydantic schemas reused by pipeline configuration."""

from __future__ import annotations

__all__ = [
    "CircuitBreakerConfig",
    "ConditionalValidationConfig",
    "CrossFieldValidationConfig",
    "CsvExportConfig",
    "DQConfig",
    "DQReportConfig",
    "FieldValidationConfig",
]


from typing import Literal

from pydantic import BaseModel, Field, model_validator

from bioetl.domain.config import DQConfig as DomainDQConfig
from bioetl.domain.resilience import CircuitBreakerConfig as DomainCircuitBreakerConfig


class FieldValidationConfig(BaseModel):
    """Configuration for a single field validation rule."""

    field: str = Field(description="Field name to validate")
    type: Literal[
        "required",
        "not_null",
        "range",
        "pattern",
        "enum",
        "max_length",
        "not_empty_list",
        "custom",
    ] = Field(description="Validation type")
    nullable: bool = Field(default=True, description="Whether field can be null")
    severity: Literal["error", "warn"] = Field(
        default="error", description="Severity level (error or warn)"
    )
    severity_enricher: Literal["error", "warn"] | None = Field(
        default=None,
        description="Override severity when running as enricher in composite pipeline",
    )
    min: float | None = Field(default=None, description="Minimum value (range)")
    max: float | None = Field(default=None, description="Maximum value (range)")
    pattern: str | None = Field(default=None, description="Regex pattern")
    allowed: list[str] = Field(default_factory=list, description="Allowed values")
    max_length: int | None = Field(default=None, description="Maximum string length")
    validator: str | None = Field(default=None, description="Custom validator name")
    error_message: str | None = Field(default=None, description="Custom error message")


class CrossFieldValidationConfig(BaseModel):
    """Configuration for cross-field validation rule."""

    name: str = Field(description="Unique validation rule name")
    fields: list[str] = Field(description="Fields involved in validation")
    condition: Literal[
        "all_present",
        "any_present",
        "mutually_exclusive",
        "conditional_required",
        "custom",
    ] = Field(description="Validation condition type")
    severity: Literal["error", "warn"] = Field(
        default="error", description="Severity level (error or warn)"
    )
    trigger_field: str | None = Field(
        default=None, description="Field that triggers conditional requirement"
    )
    required_field: str | None = Field(
        default=None, description="Field required when trigger is present"
    )
    validator: str | None = Field(default=None, description="Custom validator name")
    error_message: str | None = Field(default=None, description="Custom error message")


class ConditionalValidationConfig(BaseModel):
    """Configuration for conditional validation rule."""

    name: str = Field(description="Unique validation rule name")
    condition_field: str = Field(description="Field to check for condition")
    condition_value: str | list[str] = Field(description="Value(s) that trigger")
    condition_operator: Literal["eq", "ne", "in", "not_in"] = Field(
        default="eq", description="Comparison operator"
    )
    then_validations: list[FieldValidationConfig] = Field(
        default_factory=list, description="Validations to apply when condition is true"
    )


class DQReportConfig(BaseModel):
    """Configuration for DQ report generation."""

    enabled: bool = Field(default=True, description="Generate DQ reports")
    format: Literal["json", "yaml", "csv"] = Field(
        default="json", description="Report format"
    )
    include_sample_failures: bool = Field(
        default=True, description="Include sample failed records"
    )
    sample_size: int = Field(
        default=10, ge=1, le=100, description="Number of sample failures"
    )
    output_path: str | None = Field(default=None, description="Custom output path")


class DQConfig(BaseModel):
    """Data Quality configuration."""

    soft_fail_threshold: float = Field(default=0.05)
    hard_fail_threshold: float = Field(default=0.20)
    strict_validation: bool = Field(
        default=False,
        description="Apply stricter validation rules (feature flag)",
    )
    field_validations: list[FieldValidationConfig] = Field(
        default_factory=list, description="Field-level validation rules"
    )
    cross_field_validations: list[CrossFieldValidationConfig] = Field(
        default_factory=list, description="Cross-field validation rules"
    )
    conditional_validations: list[ConditionalValidationConfig] = Field(
        default_factory=list, description="Conditional validation rules"
    )
    invalid_record_policy: Literal["quarantine", "skip", "fail"] = Field(
        default="quarantine", description="Policy for invalid records"
    )
    report: DQReportConfig = Field(
        default_factory=DQReportConfig, description="DQ report configuration"
    )

    @model_validator(mode="after")
    def validate_thresholds(self) -> DQConfig:
        """Validate that thresholds are between 0 and 1."""
        DomainDQConfig.validate_thresholds(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
        )
        return self

    def to_domain(self) -> DomainDQConfig:
        """Convert to immutable domain DQ configuration."""
        from bioetl.domain.config import (
            ConditionalValidation as DomainConditionalValidation,
        )
        from bioetl.domain.config import (
            CrossFieldValidation as DomainCrossFieldValidation,
        )
        from bioetl.domain.config import DQReportConfig as DomainDQReportConfig
        from bioetl.domain.config import FieldValidation as DomainFieldValidation

        field_validations = tuple(
            DomainFieldValidation(
                field=fv.field,
                validation_type=fv.type,
                nullable=fv.nullable,
                severity=fv.severity,
                severity_enricher=fv.severity_enricher,
                min_value=fv.min,
                max_value=fv.max,
                pattern=fv.pattern,
                allowed=tuple(fv.allowed),
                max_length=fv.max_length,
                validator=fv.validator,
                error_message=fv.error_message,
            )
            for fv in self.field_validations
        )

        cross_field_validations = tuple(
            DomainCrossFieldValidation(
                name=cfv.name,
                fields=tuple(cfv.fields),
                condition=cfv.condition,
                severity=cfv.severity,
                trigger_field=cfv.trigger_field,
                required_field=cfv.required_field,
                validator=cfv.validator,
                error_message=cfv.error_message,
            )
            for cfv in self.cross_field_validations
        )

        conditional_validations = tuple(
            DomainConditionalValidation(
                name=cv.name,
                condition_field=cv.condition_field,
                condition_value=(
                    tuple(cv.condition_value)
                    if isinstance(cv.condition_value, list)
                    else cv.condition_value
                ),
                condition_operator=cv.condition_operator,
                then_validations=tuple(
                    DomainFieldValidation(
                        field=tv.field,
                        validation_type=tv.type,
                        nullable=tv.nullable,
                        severity=tv.severity,
                        severity_enricher=tv.severity_enricher,
                        min_value=tv.min,
                        max_value=tv.max,
                        pattern=tv.pattern,
                        allowed=tuple(tv.allowed),
                        validator=tv.validator,
                        error_message=tv.error_message,
                    )
                    for tv in cv.then_validations
                ),
            )
            for cv in self.conditional_validations
        )

        report_config = DomainDQReportConfig(
            enabled=self.report.enabled,
            format=self.report.format,
            include_sample_failures=self.report.include_sample_failures,
            sample_size=self.report.sample_size,
            output_path=self.report.output_path,
        )

        return DomainDQConfig(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
            strict_validation=self.strict_validation,
            field_validations=field_validations,
            cross_field_validations=cross_field_validations,
            conditional_validations=conditional_validations,
            invalid_record_policy=self.invalid_record_policy,
            report=report_config,
        )


class CircuitBreakerConfig(BaseModel):
    """Circuit Breaker configuration."""

    failure_threshold: int = Field(default=5, ge=1)
    recovery_timeout: int = Field(default=300, ge=60)

    def to_domain(self) -> DomainCircuitBreakerConfig:
        """Convert to immutable domain circuit-breaker config."""
        return DomainCircuitBreakerConfig(
            failure_threshold=self.failure_threshold,
            recovery_timeout=self.recovery_timeout,
        )


class CsvExportConfig(BaseModel):
    """Configuration for CSV export."""

    enabled: bool = False
    path: str | None = None
    delimiter: str = ","
    header: bool = True
    encoding: str = "utf-8"
