"""Pandera schema for ChEMBL Subcellular Fraction entity."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.schemas.constants import CHEMBL_ID_PATTERN

__all__ = [
    "SubcellularFractionSchema",
]


class SubcellularFractionSchema(ETLRecordSchema):
    """Subcellular Fraction validation schema for Silver layer."""

    assay_count: Series[float] | None = pa.Field(
        nullable=True,
        ge=0,
        coerce=True,
        description="Number of assays using this fraction.",
    )
    example_assay_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=CHEMBL_ID_PATTERN,
        description="Example assay ChEMBL identifier.",
    )
    subcellular_fraction: Series[str] = pa.Field(
        nullable=False,
        unique=True,
        str_length={"min_value": 1, "max_value": 200},
        description="Normalized subcellular fraction name.",
    )
    subcellular_fraction_raw: Series[str] | None = pa.Field(
        nullable=True,
        str_length={"min_value": 1, "max_value": 200},
        description="Raw provider subcellular-fraction lexeme before canonical normalization.",
    )

    class Config:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
