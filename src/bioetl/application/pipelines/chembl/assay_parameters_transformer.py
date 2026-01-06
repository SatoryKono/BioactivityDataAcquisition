# src/bioetl/application/pipelines/chembl/assay_parameters_transformer.py
"""ChEMBL AssayParameters Transformer.

Transforms Bronze records to Silver format (AssayParameters entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.field_specs import (
    FieldGroup,
    FieldSpec,
    float_fields,
    map_field_groups,
    simple_fields,
)
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities.chembl_assay_parameters import AssayParameters
from bioetl.domain.normalization import normalize_to_string

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


# Known parameter types for validation/metrics
KNOWN_PARAM_TYPES: frozenset[str] = frozenset(
    {
        "CONC",
        "PH",
        "TEMP",
        "TIME",
        "CELL_COUNT",
        "SERUM",
        "DOSE",
        "VOLUME",
        "WAVELENGTH",
        "PERCENT",
        "PRESSURE",
        "HUMIDITY",
        "PASSAGE",
        "CELL_DENSITY",
        "INCUBATION",
    }
)


# ============================================================================
# Declarative field groups for AssayParameters entity
# ============================================================================

_RAW_VALUES = FieldGroup(
    name="raw_values",
    fields=(
        *simple_fields("relation", "units", "text_value", "comments"),
        *float_fields("value"),
    ),
)

_STANDARD_VALUES = FieldGroup(
    name="standard_values",
    fields=(
        *simple_fields(
            "standard_type",
            "standard_relation",
            "standard_units",
            "standard_text_value",
        ),
        FieldSpec(
            "standard_value", converter=lambda v: float(v) if v is not None else None
        ),
    ),
)

_ASSAY_PARAMS_GROUPS: tuple[FieldGroup, ...] = (
    _RAW_VALUES,
    _STANDARD_VALUES,
)


def _normalize_type(param_type: Any) -> str:
    """Normalize parameter type to uppercase.

    Args:
        param_type: Raw parameter type from API (may be Any type).

    Returns:
        Normalized uppercase type or "UNKNOWN".
    """
    if param_type is None:
        return "UNKNOWN"
    normalized = normalize_to_string(param_type)
    return normalized.upper() if normalized else "UNKNOWN"


class AssayParametersTransformer(BaseChemblTransformer):
    """Transforms ChEMBL assay_parameters bronze records to silver.

    Handles:
        - Numeric value normalization (round to 10 decimals via safe_float)
        - Unit standardization awareness
        - Text value preservation
        - Parameter type normalization
        - Heterogeneous value handling (numeric vs text)

    Entity Class: AssayParameters
    Primary ID Field: assay_param_id
    """

    entity_class = AssayParameters
    primary_id_field = "assay_param_id"

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract AssayParameters business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated assay_param_id value.

        Returns:
            Dictionary of AssayParameters business fields.
        """
        # Normalize type
        raw_type = record.get("type")
        normalized_type = _normalize_type(raw_type)

        # Build business data dictionary
        business_data: dict[str, Any] = {
            # Primary identifier (integer)
            "assay_param_id": int(primary_id),
            # Foreign key
            "assay_chembl_id": record.get("assay_chembl_id"),
            # Normalized type
            "type": normalized_type,
        }

        # Apply declarative field groups
        business_data.update(map_field_groups(record, _ASSAY_PARAMS_GROUPS))

        return business_data

    def _has_any_value(self, record: BronzeRecord) -> bool:
        """Check if record has at least one value field populated.

        Used for DQ validation - parameters without any values
        are flagged but not rejected.

        Args:
            record: Bronze record to check.

        Returns:
            True if at least one value field is present.
        """
        return any(
            [
                record.get("value") is not None,
                record.get("text_value") is not None,
                record.get("standard_value") is not None,
                record.get("standard_text_value") is not None,
            ]
        )


__all__ = ["KNOWN_PARAM_TYPES", "AssayParametersTransformer"]
