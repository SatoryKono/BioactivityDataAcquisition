# src/bioetl/domain/schemas/chembl/assay_parameters.py
"""Pandera schema for ChEMBL AssayParameters entity.

Aligned with RULES.md v5.24 and ChEMBL 35 schema.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.schemas.constants import (
    ASSAY_PARAMETER_STANDARD_TYPES,
    ONTOLOGY_MAPPING_STATUSES,
    STANDARD_RELATIONS,
)


class AssayParametersSchema(ETLRecordSchema):
    """AssayParameters validation schema for Silver layer.

    Validates experimental parameter data with both raw and standardized values.
    """

    # === Primary Key (Required) ===
    assay_param_id: Series[int] = pa.Field(
        nullable=False,
        coerce=True,
        ge=1,
        description="Parameter ID (PK, surrogate integer).",
    )

    # === Foreign Key (Required) ===
    assay_id: Series[str] = pa.Field(
        nullable=False,
        coerce=True,
        str_matches=r"^CHEMBL\d+$",
        description="FK → Assay (ChEMBL ID format).",
    )

    # === Raw Values (Optional) ===
    comments: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Additional comments.",
    )
    parameter_relation: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Relation operator (=, <, >, ~, >=, <=).",
    )
    text_value: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Text value for non-numeric parameters.",
    )
    parameter_type: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Parameter type (e.g., CONC, PH, TEMP, TIME).",
    )
    type_raw: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Raw provider parameter type before controlled-vocabulary normalization.",
    )
    units: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Original units (e.g., uM, nM, %).",
    )
    uo_units: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Optional Units Ontology identifier sidecar when published by the provider/runtime.",
    )
    uo_unit_iri: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Optional canonical Units Ontology IRI companion for uo_units.",
    )
    uo_unit_mapping_status: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        isin=list(ONTOLOGY_MAPPING_STATUSES),
        description="Optional Units Ontology mapping-status companion.",
    )
    uo_ontology_version: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Optional Units Ontology version companion for uo_units.",
    )
    qudt_units: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Optional QUDT unit token/IRI sidecar when published by the provider/runtime.",
    )
    qudt_unit_iri: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Optional canonical QUDT IRI companion for qudt_units.",
    )
    qudt_unit_mapping_status: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        isin=list(ONTOLOGY_MAPPING_STATUSES),
        description="Optional QUDT mapping-status companion.",
    )
    qudt_ontology_version: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Optional QUDT ontology version companion for qudt_units.",
    )
    parameter_value: Series[float] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Numeric value.",
    )

    # === Standardized Values (Optional) ===
    standard_type: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        isin=list(ASSAY_PARAMETER_STANDARD_TYPES),
        description="Standardized type (IC50, EC50, CONC, PH, TEMP, etc.).",
    )
    standard_relation: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        isin=list(STANDARD_RELATIONS),
        description="Standardized relation.",
    )
    standard_value: Series[float] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Standardized value.",
    )
    standard_units: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Standardized units.",
    )
    standard_text_value: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Standardized text value.",
    )

    class Config:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True


__all__ = ["AssayParametersSchema"]
