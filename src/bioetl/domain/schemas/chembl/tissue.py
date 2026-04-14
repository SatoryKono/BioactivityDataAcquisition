"""Pandera schema for ChEMBL Tissue entity.

Aligned with ChEMBL tissue transformer output and pipeline contract.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.schemas.constants import (
    BTO_ID_PATTERN,
    CALOHA_ID_PATTERN,
    CHEMBL_ID_PATTERN,
    EFO_ID_PATTERN,
    UBERON_ID_PATTERN,
)

__all__ = [
    "TissueSchema",
]


class TissueSchema(ETLRecordSchema):
    """Tissue validation schema for Silver layer."""

    tissue_id: Series[str] = pa.Field(
        nullable=False,
        unique=True,
        str_matches=CHEMBL_ID_PATTERN,
        description="ChEMBL tissue identifier (primary key).",
    )
    pref_name: Series[str] = pa.Field(
        nullable=False,
        str_length={"min_value": 1, "max_value": 200},
        description="Preferred tissue name.",
    )
    bto_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=BTO_ID_PATTERN,
        description="BRENDA Tissue Ontology identifier.",
    )
    caloha_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=CALOHA_ID_PATTERN,
        description="CALIPHO tissue ontology identifier.",
    )
    efo_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=EFO_ID_PATTERN,
        description="Experimental Factor Ontology identifier.",
    )
    uberon_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=UBERON_ID_PATTERN,
        description="Uberon anatomy ontology identifier.",
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
