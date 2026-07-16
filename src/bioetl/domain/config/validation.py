"""Validation configuration objects.

Defines domain value-object validation ranges and field-level /
cross-field / conditional validation rule descriptors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from bioetl.domain.config._converters import freeze_sequences, require_literal

__all__ = [
    "DEFAULT_VALIDATION_CONFIG",
    "ConditionalValidation",
    "CrossFieldValidation",
    "FieldValidation",
    "ValidationConfig",
]


# =============================================================================
# Validation Configuration
# =============================================================================


@dataclass(frozen=True, slots=True)
class ValidationConfig:
    """Centralized configuration for validation ranges.

    Provides configurable validation parameters for domain value objects
    and validation functions. This enables:
    - Consistent validation across all components
    - Override capability via pipeline config
    - Single source of truth for validation rules

    Attributes:
        min_publication_year: Minimum valid publication year. Default 1500
            covers historical scientific publications.
        max_publication_year: Maximum valid publication year. Default 2100.
        min_molecular_weight: Minimum molecular weight in Daltons. Default 10.0.
        max_molecular_weight: Maximum molecular weight in Daltons. Default 10000.0
            covers small molecules to large peptides.
        max_pmid: Maximum valid PubMed ID. Default 10_000_000_000.
        max_taxonomy_id: Maximum valid NCBI Taxonomy ID. Default 10_000_000.
        min_pchembl_value: Minimum pChEMBL value. Default 0.0.
        max_pchembl_value: Maximum pChEMBL value. Default 15.0 (-log10(10^-15 M)).
        molecular_weight_precision: Decimal precision for MW rounding. Default 10.

    Example:
        >>> config = ValidationConfig()
        >>> config.min_publication_year
        1500

    """

    # Publication year range
    min_publication_year: int = 1500
    max_publication_year: int = 2100

    # Molecular properties
    min_molecular_weight: float = 10.0
    max_molecular_weight: float = 10_000.0
    molecular_weight_precision: int = 10

    # Identifiers
    max_pmid: int = 10_000_000_000
    max_taxonomy_id: int = 10_000_000

    # Activity values
    min_pchembl_value: float = 0.0
    max_pchembl_value: float = 15.0

    def __post_init__(self) -> None:
        """Validate configuration invariants."""
        self._validate_ranges()

    def _validate_ranges(self) -> None:
        """Validate that min/max ranges are valid."""
        validations = [
            (
                self.min_publication_year >= self.max_publication_year,
                "min_publication_year must be less than max_publication_year",
            ),
            (
                self.min_molecular_weight >= self.max_molecular_weight,
                "min_molecular_weight must be less than max_molecular_weight",
            ),
            (
                self.min_pchembl_value >= self.max_pchembl_value,
                "min_pchembl_value must be less than max_pchembl_value",
            ),
            (
                self.molecular_weight_precision < 0,
                "molecular_weight_precision must be non-negative",
            ),
        ]
        for condition, message in validations:
            if condition:
                raise ValueError(message)


# Default singleton instance for use when no custom config is provided
DEFAULT_VALIDATION_CONFIG = ValidationConfig()


DQAllowedScalar = str | int | float | bool


@dataclass(frozen=True, slots=True)
class FieldValidation:
    """Configuration for a single field validation rule.

    Supports multiple validation types:
    - required: Field must be present and non-null
    - not_null: Field should not be null (typically used with severity=warn)
    - range: Numeric range validation (min/max)
    - pattern: Regex pattern matching
    - enum: Allowed values validation
    - max_length: Maximum string length validation
    - not_empty_list: List field must be non-empty when present
    - custom: Custom validator function reference

    Attributes:
        field: Field name to validate.
        validation_type: Type of validation.
        nullable: Whether field can be null/None. Default: True.
        severity: Severity level (error or warn). Default: error.
        severity_enricher: Override severity for enricher context. None means
            use the base ``severity``. Allows DQ rules to downgrade from
            error to warn when a pipeline runs as an enricher in a
            composite pipeline.
        min_value: Minimum value for range validation.
        max_value: Maximum value for range validation.
        pattern: Regex pattern for pattern validation.
        allowed: Allowed values for enum validation.
        max_length: Maximum string length for max_length validation.
        validator: Validator function name for custom validation.
        error_message: Custom error message template.
    """

    field: str
    validation_type: Literal[
        "required",
        "not_null",
        "range",
        "pattern",
        "enum",
        "max_length",
        "not_empty_list",
        "custom",
    ]
    nullable: bool = True
    severity: Literal["error", "warn"] = "error"
    severity_enricher: Literal["error", "warn"] | None = None
    # Range validation
    min_value: float | None = None
    max_value: float | None = None
    # Pattern validation
    pattern: str | None = None
    # Enum validation
    allowed: tuple[DQAllowedScalar, ...] = ()
    # Max length validation
    max_length: int | None = None
    # Custom validation
    validator: str | None = None
    # Custom error message
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Convert lists to tuples for immutability."""
        require_literal(
            self.validation_type,
            field_name="validation_type",
            allowed=frozenset(
                {
                    "required",
                    "not_null",
                    "range",
                    "pattern",
                    "enum",
                    "max_length",
                    "not_empty_list",
                    "custom",
                }
            ),
        )
        require_literal(
            self.severity,
            field_name="severity",
            allowed=frozenset({"error", "warn"}),
        )
        if self.severity_enricher is not None:
            require_literal(
                self.severity_enricher,
                field_name="severity_enricher",
                allowed=frozenset({"error", "warn"}),
            )
        freeze_sequences(self, ("allowed",))

    def effective_severity(
        self, *, is_enricher: bool = False
    ) -> Literal["error", "warn"]:
        """Return the applicable severity given execution context.

        When running as an enricher inside a composite pipeline and
        ``severity_enricher`` is set, that override takes precedence.
        Otherwise the base ``severity`` is returned.

        Args:
            is_enricher: True when the pipeline runs as an enricher
                within a composite pipeline.

        Returns:
            ``"error"`` or ``"warn"``.
        """
        if is_enricher and self.severity_enricher is not None:
            return self.severity_enricher
        return self.severity


@dataclass(frozen=True, slots=True)
class CrossFieldValidation:
    """Configuration for cross-field validation rule.

    Validates relationships between multiple fields.

    Attributes:
        name: Unique name for the validation rule.
        fields: Fields involved in the validation.
        condition: Validation condition type.
        severity: Severity level (error or warn). Default: error.
        error_message: Custom error message template.
    """

    name: str
    fields: tuple[str, ...]
    condition: Literal[
        "all_present",  # All fields must be non-null
        "any_present",  # At least one field must be non-null
        "equality",  # Present fields must have equal values
        "mutually_exclusive",  # Only one field can be non-null
        "conditional_required",  # If field A present, field B required
        "custom",  # Custom validation function
    ]
    severity: Literal["error", "warn"] = "error"
    # For conditional_required: (trigger_field, required_field)
    trigger_field: str | None = None
    required_field: str | None = None
    # Custom validation
    validator: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Convert lists to tuples for immutability."""
        require_literal(
            self.condition,
            field_name="condition",
            allowed=frozenset(
                {
                    "all_present",
                    "any_present",
                    "equality",
                    "mutually_exclusive",
                    "conditional_required",
                    "custom",
                }
            ),
        )
        require_literal(
            self.severity,
            field_name="severity",
            allowed=frozenset({"error", "warn"}),
        )
        freeze_sequences(self, ("fields",))


@dataclass(frozen=True, slots=True)
class ConditionalValidation:
    """Configuration for conditional validation rule.

    Applies validation only when a condition is met.

    Attributes:
        name: Unique name for the validation rule.
        condition_field: Field to check for condition.
        condition_value: Value that triggers the validation.
        condition_operator: Comparison operator (eq, ne, in, not_in).
        then_validations: Field validations to apply when condition is true.
    """

    name: str
    condition_field: str
    condition_value: str | tuple[str, ...]
    condition_operator: Literal["eq", "ne", "in", "not_in"] = "eq"
    then_validations: tuple[FieldValidation, ...] = ()

    def __post_init__(self) -> None:
        """Convert lists to tuples for immutability."""
        require_literal(
            self.condition_operator,
            field_name="condition_operator",
            allowed=frozenset({"eq", "ne", "in", "not_in"}),
        )
        freeze_sequences(self, ("condition_value", "then_validations"))
