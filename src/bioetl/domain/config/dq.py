"""Data Quality configuration objects.

DQ threshold and validation rule descriptors used by the DQ subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from bioetl.domain.config._converters import freeze_sequences, require_literal
from bioetl.domain.config.validation import (
    ConditionalValidation,
    CrossFieldValidation,
    FieldValidation,
)
from bioetl.domain.types.dq_contracts import DQDisposition

__all__ = [
    "DQConfig",
    "DQReportConfig",
    "KeyNullabilityRule",
]


@dataclass(frozen=True, slots=True)
class DQReportConfig:
    """Configuration for DQ report generation.

    Attributes:
        enabled: Whether to generate DQ reports. Default: True.
        format: Report format (json, yaml, csv). Default: json.
        include_sample_failures: Include sample failed records. Default: True.
        sample_size: Number of sample failures to include. Default: 10.
        output_path: Path for report output. None = use pipeline output dir.
    """

    enabled: bool = True
    format: Literal["json", "yaml", "csv"] = "json"
    include_sample_failures: bool = True
    sample_size: int = 10
    output_path: str | None = None

    def __post_init__(self) -> None:
        require_literal(
            self.format,
            field_name="format",
            allowed=frozenset({"json", "yaml", "csv"}),
        )
        if self.sample_size < 0:
            raise ValueError("sample_size must be non-negative")


@dataclass(frozen=True, slots=True)
class KeyNullabilityRule:
    """Nullability rule for key fields used by Silver writes.

    Attributes:
        field: Field name.
        key_type: Key role in Silver writes.
        nullable: Whether null is allowed for this key field.
    """

    field: str
    key_type: Literal["merge", "partition"]
    nullable: bool = False

    def __post_init__(self) -> None:
        require_literal(
            self.key_type,
            field_name="key_type",
            allowed=frozenset({"merge", "partition"}),
        )


@dataclass(frozen=True, slots=True)
class DQConfig:
    """Configuration for Data Quality thresholds and validations.

    Attributes:
        soft_fail_threshold: Error rate threshold for warnings (0.0-1.0).
        hard_fail_threshold: Error rate threshold for failures (0.0-1.0).
        strict_validation: DQ-only strictness flag for rule evaluation and
            invalid-record handling. This is distinct from Gold write-path
            strict validation/runtime strict Gold enforcement. Default: False.
        field_validations: Field-level validation rules.
        cross_field_validations: Cross-field validation rules.
        conditional_validations: Conditional validation rules.
        invalid_record_policy: Policy for handling invalid records.
        report: DQ report configuration.

        # Contract-based DQ configuration (Epic 2: Effective Policy Resolver)
        contract_ref: str | None = None
        contract_version: str | None = None
        rule_bundle_version: str | None = None
        default_disposition_policy: Default disposition for unmatched rules.
        disposition_overrides: Mapping or sequence of (rule_id, disposition)
            pairs. Stored as an immutable tuple of items after construction.
        strictness_mode: Policy strictness mode (lenient/moderate/strict).
    """

    soft_fail_threshold: float = 0.05
    hard_fail_threshold: float = 0.50
    strict_validation: bool = False
    # Extended DQ configuration
    field_validations: tuple[FieldValidation, ...] = ()
    cross_field_validations: tuple[CrossFieldValidation, ...] = ()
    conditional_validations: tuple[ConditionalValidation, ...] = ()
    invalid_record_policy: Literal["quarantine", "skip", "fail"] = "quarantine"
    report: DQReportConfig = field(default_factory=DQReportConfig)
    key_nullability_rules: tuple[KeyNullabilityRule, ...] = ()

    # Contract-based DQ configuration
    contract_ref: str | None = None
    contract_version: str | None = None
    rule_bundle_version: str | None = None
    default_disposition_policy: DQDisposition = DQDisposition.WARN
    # Declared storage form is immutable item tuples; callers may pass a dict.
    disposition_overrides: tuple[tuple[str, DQDisposition], ...] = ()
    strictness_mode: Literal["lenient", "moderate", "strict"] = "moderate"

    def __post_init__(self) -> None:
        """Validate threshold invariants and freeze sequences on creation."""
        self.validate_thresholds(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
        )
        require_literal(
            self.invalid_record_policy,
            field_name="invalid_record_policy",
            allowed=frozenset({"quarantine", "skip", "fail"}),
        )
        require_literal(
            self.strictness_mode,
            field_name="strictness_mode",
            allowed=frozenset({"lenient", "moderate", "strict"}),
        )
        freeze_sequences(
            self,
            (
                "field_validations",
                "cross_field_validations",
                "conditional_validations",
                "key_nullability_rules",
            ),
        )
        # Normalize disposition_overrides to an immutable tuple of items.
        raw_overrides = self.disposition_overrides
        if isinstance(raw_overrides, dict):
            normalized = tuple(
                (str(key), value) for key, value in raw_overrides.items()
            )
        elif isinstance(raw_overrides, list | tuple):
            normalized = tuple(
                (str(item[0]), item[1])  # type: ignore[index]
                for item in raw_overrides
            )
        else:
            raise TypeError(
                "disposition_overrides must be a mapping or sequence of "
                f"(rule_id, disposition) pairs, got {type(raw_overrides).__name__}"
            )
        object.__setattr__(self, "disposition_overrides", normalized)

    @staticmethod
    def validate_thresholds(
        *, soft_fail_threshold: float, hard_fail_threshold: float
    ) -> None:
        """Validate ordering and bounds for DQ thresholds.

        Args:
            soft_fail_threshold: Soft fail threshold.
            hard_fail_threshold: Hard fail threshold.
        """
        if not 0.0 <= soft_fail_threshold <= 1.0:
            raise ValueError(
                "soft_fail_threshold must be between 0.0 and 1.0 inclusive"
            )
        if not 0.0 <= hard_fail_threshold <= 1.0:
            raise ValueError(
                "hard_fail_threshold must be between 0.0 and 1.0 inclusive"
            )
        if soft_fail_threshold >= hard_fail_threshold:
            raise ValueError(
                "soft_fail_threshold must be strictly less than hard_fail_threshold"
            )
