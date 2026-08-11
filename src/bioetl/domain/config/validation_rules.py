"""Validation rule descriptors for field-level and cross-field validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from bioetl.domain.config._converters import freeze_sequences, require_literal

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
        """Convert lists to tuples for immutability and validate variant params."""
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
        self._validate_variant_parameters()

    def _validate_variant_parameters(self) -> None:
        """Reject incomplete or contradictory variant-specific parameters."""
        vtype = self.validation_type
        if vtype == "range":
            if self.min_value is None and self.max_value is None:
                raise ValueError("range validation requires min_value and/or max_value")
            if (
                self.min_value is not None
                and self.max_value is not None
                and self.min_value > self.max_value
            ):
                raise ValueError(
                    "range validation min_value must be <= max_value, "
                    f"got min={self.min_value}, max={self.max_value}"
                )
            return
        if vtype == "pattern":
            if not self.pattern or not str(self.pattern).strip():
                raise ValueError("pattern validation requires a non-empty pattern")
            return
        if vtype == "enum":
            if not self.allowed:
                raise ValueError("enum validation requires a non-empty allowed set")
            return
        if vtype == "max_length":
            if self.max_length is None or self.max_length < 0:
                raise ValueError(
                    "max_length validation requires a non-negative max_length"
                )
            return
        if vtype == "custom" and (
            not self.validator or not str(self.validator).strip()
        ):
            raise ValueError("custom validation requires a validator name")

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
