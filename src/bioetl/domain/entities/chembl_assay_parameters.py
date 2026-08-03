# src/bioetl/domain/entities/chembl_assay_parameters.py
"""ChEMBL AssayParameters domain entity.

Contains the AssayParameters entity for experimental assay parameters.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.entities.base import BaseEntity


@dataclass(frozen=True, kw_only=True)
class AssayParameters(BaseEntity):
    """Represents experimental conditions for bioassays (ChEMBL AssayParameters).

    Contains parameters such as concentrations, pH, temperature, incubation time, etc.
    Includes both raw values from original source and standardized values for comparison.

    M:1 relationship with Assay (many parameters -> one assay via assay_id FK).

    API Endpoint: https://www.ebi.ac.uk/chembl/api/data/assay_parameters

    Entity ID: chembl:{assay_param_id}
    Content Hash: sha256(chembl + canonical_json(business_fields))

    Value Types:
        - Numeric: value + units (e.g., 10 μM)
        - Text: text_value (e.g., "Room temperature")
        - Standard_*: ChEMBL-standardized versions

    Common Parameter Types:
        - CONC: Concentration
        - PH: pH level
        - TEMP: Temperature
        - TIME: Incubation time
        - CELL_COUNT: Cell count
        - SERUM: Serum percentage
    """

    # === Primary Key (Surrogate, REQUIRED) ===
    assay_param_id: int

    # === Foreign Key (REQUIRED) ===
    assay_id: str

    # === Parameter Type (Optional, may be None if not provided by API) ===
    type_raw: str | None = None
    type: str | None = None

    # === Raw Values (API-OPTIONAL) ===
    relation: str | None = None  # Relation (=, <, >, ~, >=, <=)
    value: float | None = None  # Numeric value
    units: str | None = None  # Original units
    text_value: str | None = None  # Text value (for non-numeric params)
    comments: str | None = None  # Additional comments

    # === Standardized Values (API-OPTIONAL) ===
    standard_type: str | None = None  # Standardized type
    standard_relation: str | None = None  # Standardized relation
    standard_value: float | None = None  # Standardized value
    standard_units: str | None = None  # Standardized units
    standard_text_value: str | None = None  # Standardized text value

    def _validate_invariants(self) -> None:
        """Validate entity invariants."""
        # Integer fields: < 1 covers 0 and negatives
        if self.assay_param_id < 1:
            raise ValueError(
                f"assay_param_id must be positive integer, got {self.assay_param_id}"
            )
        if not self.assay_id or not self.assay_id.startswith("CHEMBL"):
            raise ValueError(f"Invalid assay_id: {self.assay_id}")

    def has_numeric_value(self) -> bool:
        """Check if parameter has numeric value (raw or standardized).

        Returns:
            True if the condition is met, False otherwise.
        """
        return self.value is not None or self.standard_value is not None

    def has_text_value(self) -> bool:
        """Check if parameter has text value (raw or standardized).

        Returns:
            True if the condition is met, False otherwise.
        """
        return self.text_value is not None or self.standard_text_value is not None

    def get_comparable_value(self) -> tuple[float | None, str | None]:
        """Get best available value for comparison.

        Prefers standardized values over raw values.

        Returns:
            Tuple of (value, units) preferring standardized over raw.
        """
        if self.standard_value is not None:
            return (self.standard_value, self.standard_units)
        return (self.value, self.units)


__all__ = ["AssayParameters"]
