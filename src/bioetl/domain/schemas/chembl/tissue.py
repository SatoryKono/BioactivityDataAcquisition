"""Pandera schema for ChEMBL Tissue entity.

Aligned with ChEMBL tissue transformer output and pipeline contract.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.schemas.constants import CHEMBL_ID_PATTERN

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
        str_matches=r"^BTO:\d{7}$",
        description="BRENDA Tissue Ontology identifier.",
    )
    caloha_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^TS-\d{4}$",
        description="CALIPHO tissue ontology identifier.",
    )
    efo_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^EFO:\d{7}$",
        description="Experimental Factor Ontology identifier.",
    )
    uberon_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^UBERON:\d{7}$",
        description="Uberon anatomy ontology identifier.",
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
