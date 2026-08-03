# mypy: disable-error-code="misc,untyped-decorator"
"""Common Pydantic schemas reused by pipeline configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from bioetl.domain.config import (
    ConditionalValidation as DomainConditionalValidation,
)
from bioetl.domain.config import (
    CrossFieldValidation as DomainCrossFieldValidation,
)
from bioetl.domain.config import (
    DQConfig as DomainDQConfig,
)
from bioetl.domain.config import (
    DQReportConfig as DomainDQReportConfig,
)
from bioetl.domain.config import (
    FieldValidation as DomainFieldValidation,
)
from bioetl.domain.resilience import CircuitBreakerConfig as DomainCircuitBreakerConfig

__all__ = [
    "CircuitBreakerYamlConfig",
    "ConditionalValidationConfig",
    "CrossFieldValidationConfig",
    "CsvExportConfig",
    "DQReportYamlConfig",
    "DQYamlConfig",
    "FieldValidationConfig",
]

type DQAllowedScalar = str | int | float | bool


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
    allowed: list[DQAllowedScalar] = Field(
        default_factory=list, description="Allowed values"
    )
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
        "equality",
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


class DQReportYamlConfig(BaseModel):
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


class DQYamlConfig(BaseModel):
    """Data Quality configuration."""

    soft_fail_threshold: float = Field(default=0.05)
    hard_fail_threshold: float = Field(default=0.20)
    strict_validation: bool = Field(
        default=False,
        description=(
            "Apply stricter validation rules for inline pipeline quality config; "
            "the canonical contract-YAML key remains strict_dq_validation"
        ),
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
    report: DQReportYamlConfig = Field(
        default_factory=DQReportYamlConfig,
        description="DQ report configuration",
    )

    @model_validator(mode="after")
    def validate_thresholds(self) -> DQYamlConfig:
        """Validate that thresholds are between 0 and 1."""
        DomainDQConfig.validate_thresholds(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
        )
        return self

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

    @classmethod
    def _to_domain_conditional_validation(
        cls,
        config: ConditionalValidationConfig,
    ) -> DomainConditionalValidation:
        condition_value = (
            tuple(config.condition_value)
            if isinstance(config.condition_value, list)
            else config.condition_value
        )
        return DomainConditionalValidation(
            name=config.name,
            condition_field=config.condition_field,
            condition_value=condition_value,
            condition_operator=config.condition_operator,
            then_validations=tuple(
                cls._to_domain_field_validation(validation)
                for validation in config.then_validations
            ),
        )

    @staticmethod
    def _to_domain_report_config(
        config: DQReportYamlConfig,
    ) -> DomainDQReportConfig:
        return DomainDQReportConfig(
            enabled=config.enabled,
            format=config.format,
            include_sample_failures=config.include_sample_failures,
            sample_size=config.sample_size,
            output_path=config.output_path,
        )

    def to_domain(self) -> DomainDQConfig:
        """Convert to immutable domain DQ configuration.

        Returns:
            DomainDQConfig instance with merged field, cross-field, and conditional validations.
        """
        field_validations = tuple(
            self._to_domain_field_validation(config)
            for config in self.field_validations
        )
        cross_field_validations = tuple(
            self._to_domain_cross_field_validation(config)
            for config in self.cross_field_validations
        )
        conditional_validations = tuple(
            self._to_domain_conditional_validation(config)
            for config in self.conditional_validations
        )
        report_config = self._to_domain_report_config(self.report)
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


class CircuitBreakerYamlConfig(BaseModel):
    """Circuit Breaker configuration."""

    failure_threshold: int = Field(default=5, ge=1)
    recovery_timeout: int = Field(default=300, ge=60)

    def to_domain(self) -> DomainCircuitBreakerConfig:
        """Convert to immutable domain circuit-breaker config.

        Returns:
            DomainCircuitBreakerConfig instance with failure threshold and recovery timeout.
        """
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
