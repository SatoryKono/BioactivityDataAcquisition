"""Validation configuration for domain value objects."""

from __future__ import annotations

from dataclasses import dataclass


def _nonpositive_optional(value: object) -> bool:
    return value is not None and isinstance(value, int | float) and value <= 0


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
        self._validate_positive_identifiers()

    def _validate_ranges(self) -> None:
        """Validate that min/max ranges are valid."""
        from math import isfinite

        for name, value in (
            ("min_molecular_weight", self.min_molecular_weight),
            ("max_molecular_weight", self.max_molecular_weight),
            ("min_pchembl_value", self.min_pchembl_value),
            ("max_pchembl_value", self.max_pchembl_value),
        ):
            if not isfinite(value):
                raise ValueError(f"{name} must be finite")
        validations = [
            (
                self.min_publication_year <= 0 or self.max_publication_year <= 0,
                "publication year bounds must be positive",
            ),
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
            (
                getattr(self, "max_pmid", 1) is not None
                and getattr(self, "max_pmid", 1) <= 0,
                "max_pmid must be positive",
            ),
            (
                getattr(self, "max_taxonomy_id", 1) is not None
                and getattr(self, "max_taxonomy_id", 1) <= 0,
                "max_taxonomy_id must be positive",
            ),
        ]
        for condition, message in validations:
            if condition:
                raise ValueError(message)

    def _validate_positive_identifiers(self) -> None:
        if self.min_publication_year <= 0 or self.max_publication_year <= 0:
            raise ValueError("publication year bounds must be positive")
        if _nonpositive_optional(getattr(self, "max_pmid", 1)):
            raise ValueError("max_pmid must be positive")
        if _nonpositive_optional(getattr(self, "max_taxonomy_id", 1)):
            raise ValueError("max_taxonomy_id must be positive")
