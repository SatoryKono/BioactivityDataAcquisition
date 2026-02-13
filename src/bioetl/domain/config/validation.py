"""Domain validation configuration value objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from bioetl.domain.config._converters import freeze_sequences


@dataclass(frozen=True, slots=True)
class ValidationConfig:
    """Centralized numeric validation ranges."""

    min_publication_year: int = 1500
    max_publication_year: int = 2100
    min_molecular_weight: float = 10.0
    max_molecular_weight: float = 10_000.0
    molecular_weight_precision: int = 10
    max_pmid: int = 10_000_000_000
    max_taxonomy_id: int = 10_000_000
    min_pchembl_value: float = 0.0
    max_pchembl_value: float = 15.0

    def __post_init__(self) -> None:
        checks = [
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
        for condition, message in checks:
            if condition:
                raise ValueError(message)


DEFAULT_VALIDATION_CONFIG = ValidationConfig()


@dataclass(frozen=True, slots=True)
class FieldValidation:
    """Single-field validation descriptor."""

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
    min_value: float | None = None
    max_value: float | None = None
    pattern: str | None = None
    allowed: tuple[str, ...] = ()
    max_length: int | None = None
    validator: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        freeze_sequences(self, ("allowed",))


@dataclass(frozen=True, slots=True)
class CrossFieldValidation:
    """Validation descriptor involving multiple fields."""

    name: str
    fields: tuple[str, ...]
    condition: Literal[
        "all_present",
        "any_present",
        "mutually_exclusive",
        "conditional_required",
        "custom",
    ]
    trigger_field: str | None = None
    required_field: str | None = None
    validator: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        freeze_sequences(self, ("fields",))


@dataclass(frozen=True, slots=True)
class ConditionalValidation:
    """Condition-dependent validation descriptor."""

    name: str
    condition_field: str
    condition_value: str | tuple[str, ...]
    condition_operator: Literal["eq", "ne", "in", "not_in"] = "eq"
    then_validations: tuple[FieldValidation, ...] = ()

    def __post_init__(self) -> None:
        freeze_sequences(self, ("condition_value", "then_validations"))
