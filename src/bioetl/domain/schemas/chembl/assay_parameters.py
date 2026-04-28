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

    # === Parameter Type (Optional, may be None if not provided by API) ===
    type: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Parameter type (e.g., CONC, PH, TEMP, TIME).",
    )
    type_raw: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Raw provider parameter type before controlled-vocabulary normalization.",
    )

    # === Raw Values (Optional) ===
    relation: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Relation operator (=, <, >, ~, >=, <=).",
    )
    value: Series[float] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Numeric value.",
    )
    units: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Original units (e.g., uM, nM, %).",
    )
    text_value: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Text value for non-numeric parameters.",
    )
    comments: Series[str] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Additional comments.",
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

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True


__all__ = ["AssayParametersSchema"]
