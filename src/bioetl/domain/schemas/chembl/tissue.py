# pyright: reportIncompatibleVariableOverride=false
# Pandera/ETL nested Config override pattern (PD2-7).
"""Pandera schema for ChEMBL Tissue entity.

Aligned with ChEMBL tissue transformer output and pipeline contract.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.schemas.constants import (
    CALOHA_ID_PATTERN,
    CHEMBL_ID_PATTERN,
    ONTOLOGY_MAPPING_STATUSES,
)

__all__ = [
    "TissueSchema",
]

HTTP_IRI_PATTERN = r"^https?://[^\s]+$"
CANONICAL_BTO_ID_PATTERN = r"^BTO_\d+$"
CANONICAL_EFO_ID_PATTERN = r"^EFO_\d+$"
CANONICAL_UBERON_ID_PATTERN = r"^UBERON_\d+$"


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
        str_matches=CANONICAL_BTO_ID_PATTERN,
        description="BRENDA Tissue Ontology identifier.",
    )
    bto_iri: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=HTTP_IRI_PATTERN,
        description="Persistent IRI for the BTO identifier.",
    )
    bto_mapping_status: Series[str] | None = pa.Field(
        nullable=True,
        isin=list(ONTOLOGY_MAPPING_STATUSES),
        description="BTO IRI mapping status.",
    )
    bto_ontology_version: Series[str] | None = pa.Field(
        nullable=True,
        description="BTO ontology release/version used for IRI mapping.",
    )
    caloha_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=CALOHA_ID_PATTERN,
        description="CALIPHO tissue ontology identifier.",
    )
    efo_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=CANONICAL_EFO_ID_PATTERN,
        description="Experimental Factor Ontology identifier.",
    )
    efo_iri: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=HTTP_IRI_PATTERN,
        description="Persistent IRI for the EFO identifier.",
    )
    efo_mapping_status: Series[str] | None = pa.Field(
        nullable=True,
        isin=list(ONTOLOGY_MAPPING_STATUSES),
        description="EFO IRI mapping status.",
    )
    efo_ontology_version: Series[str] | None = pa.Field(
        nullable=True,
        description="EFO ontology release/version used for IRI mapping.",
    )
    uberon_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=CANONICAL_UBERON_ID_PATTERN,
        description="Uberon anatomy ontology identifier.",
    )
    uberon_iri: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=HTTP_IRI_PATTERN,
        description="Persistent IRI for the Uberon identifier.",
    )
    uberon_mapping_status: Series[str] | None = pa.Field(
        nullable=True,
        isin=list(ONTOLOGY_MAPPING_STATUSES),
        description="Uberon IRI mapping status.",
    )
    uberon_ontology_version: Series[str] | None = pa.Field(
        nullable=True,
        description="Uberon ontology release/version used for IRI mapping.",
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
