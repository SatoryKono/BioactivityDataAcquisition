"""Data Quality configuration objects.

DQ threshold and validation rule descriptors used by the DQ subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from bioetl.domain.config._converters import freeze_sequences
from bioetl.domain.config.validation import (
    ConditionalValidation,
    CrossFieldValidation,
    FieldValidation,
)


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


@dataclass(frozen=True, slots=True)
class DQConfig:
    """Configuration for Data Quality thresholds and validations.

    Attributes:
        soft_fail_threshold: Error rate threshold for warnings (0.0-1.0).
        hard_fail_threshold: Error rate threshold for failures (0.0-1.0).
        strict_validation: If True, apply stricter validation rules that may
            reject more records. Use with caution in production. Default: False.
        field_validations: Field-level validation rules.
        cross_field_validations: Cross-field validation rules.
        conditional_validations: Conditional validation rules.
        invalid_record_policy: Policy for handling invalid records.
        report: DQ report configuration.
    """

    soft_fail_threshold: float = 0.05
    hard_fail_threshold: float = 0.20
    strict_validation: bool = False
    # Extended DQ configuration
    field_validations: tuple[FieldValidation, ...] = ()
    cross_field_validations: tuple[CrossFieldValidation, ...] = ()
    conditional_validations: tuple[ConditionalValidation, ...] = ()
    invalid_record_policy: Literal["quarantine", "skip", "fail"] = "quarantine"
    report: DQReportConfig = field(default_factory=DQReportConfig)

    def __post_init__(self) -> None:
        """Validate threshold invariants on creation."""
        self.validate_thresholds(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
        )
        freeze_sequences(
            self,
            ("field_validations", "cross_field_validations", "conditional_validations"),
        )

    @staticmethod
    def validate_thresholds(
        *, soft_fail_threshold: float, hard_fail_threshold: float
    ) -> None:
        """Validate ordering and bounds for DQ thresholds."""
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
