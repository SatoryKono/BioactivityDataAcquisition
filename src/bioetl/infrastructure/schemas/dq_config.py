# mypy: disable-error-code="misc,untyped-decorator"
"""Pydantic schemas for standalone DQ configuration files.

Validates external YAML files (configs/quality/*.yaml) before converting
to domain objects. Supports hierarchical merge of configurations.

Implements RULES.md §3.1.2 DQ Thresholds.

Structure:
    ThresholdsConfig: Threshold settings with soft_fail < hard_fail validation.
    DQConfigFile: Complete DQ configuration file schema for standalone files.

Usage:
    >>> from bioetl.infrastructure.schemas.dq_config import DQConfigFile
    >>> config = DQConfigFile.model_validate(yaml_data)
    >>> domain_config = config.to_domain()
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from bioetl.domain.config import ConditionalValidation as DomainConditionalValidation
from bioetl.domain.config import CrossFieldValidation as DomainCrossFieldValidation
from bioetl.domain.config import DQConfig as DomainDQConfig
from bioetl.domain.config import DQReportConfig as DomainDQReportConfig
from bioetl.domain.config import FieldValidation as DomainFieldValidation
from bioetl.domain.config import KeyNullabilityRule as DomainKeyNullabilityRule
from bioetl.infrastructure.schemas.pipeline_config import (
    ConditionalValidationConfig,
    CrossFieldValidationConfig,
    DQReportYamlConfig,
    FieldValidationConfig,
)


class ThresholdsConfig(BaseModel):
    """Threshold configuration section.

    Validates DQ error thresholds for warning and failure modes.
    Enforces the invariant that soft_fail must be less than hard_fail.

    Attributes:
        soft_fail: Warning threshold (0.0-1.0). Default: 0.05 (5%).
            When error rate exceeds this threshold, a warning is emitted.
        hard_fail: Failure threshold (0.0-1.0). Default: 0.50 (50%).
            When error rate exceeds this threshold, the batch fails.

    Example:
        >>> thresholds = ThresholdsConfig(soft_fail=0.05, hard_fail=0.15)
        >>> thresholds.soft_fail
        0.05
        >>> thresholds.hard_fail
        0.15
    """

    soft_fail: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Warning threshold (0.0-1.0). Default: 0.05 (5%)",
    )
    hard_fail: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Failure threshold (0.0-1.0). Default: 0.50 (50%)",
    )

    @model_validator(mode="after")
    def validate_order(self) -> ThresholdsConfig:
        """Ensure soft_fail < hard_fail.

        Raises:
            ValueError: If soft_fail is not strictly less than hard_fail.

        Returns:
            Validated ThresholdsConfig.
        """
        if self.soft_fail >= self.hard_fail:
            raise ValueError(
                f"soft_fail ({self.soft_fail}) must be < hard_fail ({self.hard_fail})"
            )
        return self


class KeyNullabilityRuleConfig(BaseModel):
    """Nullability policy for Silver merge/partition keys."""

    field: str = Field(description="Field name")
    key_type: Literal["merge", "partition"] = Field(
        description="Key role in Silver write strategy"
    )
    nullable: bool = Field(
        default=False,
        description="Whether null values are allowed for this key field",
    )


class DQConfigFile(BaseModel):
    """Complete DQ configuration file schema.

    Represents structure of configs/quality/*.yaml files.
    Contract YAML under configs/contracts/* uses ``strict_dq_validation`` as
    the canonical file key, while this quality-config schema exposes the
    normalized domain property name ``strict_validation``.
    Supports three levels of field validations for hierarchical merge:
    - common_*: from _defaults.yaml
    - provider_*: from providers/{provider}.yaml
    - entity_*: from entities/{provider}/{entity}.yaml

    The merge order is: common → provider → entity (entity takes precedence).

    Attributes:
        version: Schema version for compatibility checking.
        provider: Provider name (optional, for provider/entity configs).
        entity: Entity name (optional, for entity configs).
        thresholds: DQ threshold configuration (soft/hard fail).
        strict_validation: Normalized domain property corresponding to the
            canonical contract-YAML key ``strict_dq_validation``.
        invalid_record_policy: How to handle invalid records.
        report: DQ report generation settings.
        common_field_validations: Field validations from defaults.
        provider_field_validations: Field validations from provider config.
        entity_field_validations: Field validations from entity config.
        common_cross_field_validations: Cross-field validations from defaults.
        entity_cross_field_validations: Cross-field validations from entity.
        entity_conditional_validations: Conditional validations from entity.

    Example:
        >>> config = DQConfigFile(
        ...     provider='chembl',
        ...     entity='activity',
        ...     thresholds=ThresholdsConfig(soft_fail=0.05, hard_fail=0.15),
        ...     entity_field_validations=[
        ...         FieldValidationConfig(
        ...             field='activity_id',
        ...             type='range',
        ...             nullable=False
        ...         )
        ...     ]
        ... )
        >>> domain = config.to_domain()
    """

    # Metadata
    version: str = Field(
        default="1.0.0",
        description="Schema version for compatibility checking",
    )
    provider: str | None = Field(
        default=None,
        description="Provider name (for provider/entity configs)",
    )
    entity: str | None = Field(
        default=None,
        description="Entity name (for entity configs)",
    )

    # Core settings
    thresholds: ThresholdsConfig = Field(
        default_factory=ThresholdsConfig,
        description="DQ threshold configuration",
    )
    strict_validation: bool = Field(
        default=False,
        description=(
            "Normalized quality-config property corresponding to the canonical "
            "contract-YAML key strict_dq_validation under configs/contracts/*"
        ),
    )
    invalid_record_policy: Literal["quarantine", "skip", "fail"] = Field(
        default="quarantine",
        description="Policy for handling invalid records",
    )
    report: DQReportYamlConfig = Field(
        default_factory=DQReportYamlConfig,
        description="DQ report generation settings",
    )

    # Field validations (hierarchical merge support)
    common_field_validations: list[FieldValidationConfig] = Field(
        default_factory=list,
        description="Field validations from _defaults.yaml",
    )
    provider_field_validations: list[FieldValidationConfig] = Field(
        default_factory=list,
        description="Field validations from provider config",
    )
    entity_field_validations: list[FieldValidationConfig] = Field(
        default_factory=list,
        description="Field validations from entity config",
    )

    # Cross-field validations
    common_cross_field_validations: list[CrossFieldValidationConfig] = Field(
        default_factory=list,
        description="Cross-field validations from _defaults.yaml",
    )
    entity_cross_field_validations: list[CrossFieldValidationConfig] = Field(
        default_factory=list,
        description="Cross-field validations from entity config",
    )

    key_nullability: list[KeyNullabilityRuleConfig] = Field(
        default_factory=list,
        description="Nullability rules for merge/partition key fields",
    )

    # Conditional validations
    entity_conditional_validations: list[ConditionalValidationConfig] = Field(
        default_factory=list,
        description="Conditional validations from entity config",
    )

    def _to_domain_field_validations(self) -> tuple[DomainFieldValidation, ...]:
        all_field_validations = (
            self.common_field_validations
            + self.provider_field_validations
            + self.entity_field_validations
        )
        return tuple(
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
            for fv in all_field_validations
        )

    def _to_domain_cross_field_validations(
        self,
    ) -> tuple[DomainCrossFieldValidation, ...]:
        all_cross_field_validations = (
            self.common_cross_field_validations + self.entity_cross_field_validations
        )
        return tuple(
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
            for cfv in all_cross_field_validations
        )

    def _to_domain_conditional_validations(
        self,
    ) -> tuple[DomainConditionalValidation, ...]:
        return tuple(
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
            for cv in self.entity_conditional_validations
        )

    def _to_domain_report_config(self) -> DomainDQReportConfig:
        return DomainDQReportConfig(
            enabled=self.report.enabled,
            format=self.report.format,
            include_sample_failures=self.report.include_sample_failures,
            sample_size=self.report.sample_size,
            output_path=self.report.output_path,
        )

    def _to_domain_key_nullability_rules(self) -> tuple[DomainKeyNullabilityRule, ...]:
        return tuple(
            DomainKeyNullabilityRule(
                field=rule.field,
                key_type=rule.key_type,
                nullable=rule.nullable,
            )
            for rule in self.key_nullability
        )

    def to_domain(self) -> DomainDQConfig:
        """Convert to immutable domain DQConfig.

        Merges all validation lists in hierarchical order:
        - Field validations: common + provider + entity
        - Cross-field validations: common + entity
        - Conditional validations: entity only

        Returns:
            DomainDQConfig: Immutable domain configuration.
        """
        return DomainDQConfig(
            soft_fail_threshold=self.thresholds.soft_fail,
            hard_fail_threshold=self.thresholds.hard_fail,
            strict_validation=self.strict_validation,
            field_validations=self._to_domain_field_validations(),
            cross_field_validations=self._to_domain_cross_field_validations(),
            conditional_validations=self._to_domain_conditional_validations(),
            invalid_record_policy=self.invalid_record_policy,
            report=self._to_domain_report_config(),
            key_nullability_rules=self._to_domain_key_nullability_rules(),
        )


__all__ = [
    "DQConfigFile",
    "ThresholdsConfig",
]
