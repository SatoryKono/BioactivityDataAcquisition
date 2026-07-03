"""ChEMBL Subcellular Fraction domain entity.

Derived entity: extracts unique subcellular fractions from Assay records.
This is a reference/lookup entity for biological context normalization.

Source: assay_subcellular_fraction field from ChEMBL API /assay endpoint
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.entities.base import BaseEntity


@dataclass(frozen=True, kw_only=True)
class SubcellularFraction(BaseEntity):
    """Represents a subcellular fraction used in ChEMBL assays.

    Subcellular fractions describe the cellular compartment or preparation
    used in bioassay experiments (e.g., "Microsomes", "Cytosol", "Mitochondria").

    This is a derived entity that extracts and deduplicates unique subcellular
    fraction values from Assay records, creating a lookup/reference table.

    Composite Key: subcellular_fraction (normalized)
    Source: Nested in ChEMBL API /assay response (assay_subcellular_fraction field)
    See: https://www.ebi.ac.uk/chembl/api/data/assay

    Example values:
    - Microsomes
    - Cytosol
    - Mitochondria
    - Membrane
    - Cell lysate
    - S9 fraction
    """

    # === Primary Key Field ===
    subcellular_fraction_raw: str | None = None  # Raw provider lexeme if preserved
    subcellular_fraction: str  # Normalized subcellular fraction name

    # === Statistics (aggregated from source assays) ===
    assay_count: int | None = None  # Number of assays using this fraction

    # === Example Source Reference ===
    example_assay_id: str | None = None  # One assay using this fraction

    def _validate_invariants(self) -> None:
        if not self.subcellular_fraction:
            raise ValueError("Subcellular fraction name is required")
        self._validate_fraction_name()
        self._validate_assay_count()

    def _validate_fraction_name(self) -> None:
        """Validate normalized fraction name content."""
        if not self.subcellular_fraction.strip():
            raise ValueError("Subcellular fraction cannot be empty or whitespace")

    def _validate_assay_count(self) -> None:
        """Validate aggregated assay count when it is available."""
        if self.assay_count is not None and self.assay_count < 0:
            raise ValueError(
                f"assay_count must be non-negative, got {self.assay_count}"
            )


__all__ = ["SubcellularFraction"]
