# pyright: reportIncompatibleVariableOverride=false
# Pandera/ETL nested Config override pattern (PD2-7).
"""Pandera schema for ChEMBL Cell Line entity.

Aligned with RULES.md v5.24 and ChEMBL 34 schema.
Source: ChEMBL REST API, table cell_dictionary.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.schemas.constants import (
    CELLOSAURUS_ID_PATTERN,
    CHEMBL_ID_PATTERN,
    CLO_ID_PATTERN,
    EFO_ID_PATTERN,
    ONTOLOGY_MAPPING_STATUSES,
)

__all__ = [
    "CellLineSchema",
]

HTTP_IRI_PATTERN = r"^https?://[^\s]+$"


class CellLineSchema(ETLRecordSchema):
    """Cell Line validation schema for Silver layer.

    Cell lines are biological objects used for in vitro experiments.
    They have M:N relationship with Assay (via assay.cell_chembl_id FK).
    """

    # === Primary Key ===
    cell_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=CHEMBL_ID_PATTERN,
        unique=True,
        description="ChEMBL ID for cell line (PK).",
    )

    # === Core Metadata ===
    cell_name: Series[str] = pa.Field(
        nullable=False,
        description="Cell line name (e.g., HeLa, MCF7).",
    )
    cell_description: Series[str] | None = pa.Field(
        nullable=True,
        description="Cell line description.",
    )

    # === Source Information ===
    cell_source_tissue: Series[str] | None = pa.Field(
        nullable=True,
        description="Source tissue (e.g., Cervix, Breast).",
    )
    cell_source_organism: Series[str] | None = pa.Field(
        nullable=True,
        description="Source organism (e.g., Homo sapiens).",
    )
    cell_source_taxonomy_id: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True,
        description="NCBI Taxonomy ID for source organism.",
    )

    # === Cell Type Classification ===
    cell_type: Series[str] | None = pa.Field(
        nullable=True,
        description="Cell type classification (e.g., Cancer cell line).",
    )

    # === External Identifiers ===
    cellosaurus_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=CELLOSAURUS_ID_PATTERN,
        description="Cellosaurus ID (external reference).",
    )
    clo_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=CLO_ID_PATTERN,
        description="Cell Line Ontology ID.",
    )
    clo_iri: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=HTTP_IRI_PATTERN,
        description="Persistent IRI for the CLO identifier.",
    )
    clo_mapping_status: Series[str] | None = pa.Field(
        nullable=True,
        isin=list(ONTOLOGY_MAPPING_STATUSES),
        description="CLO IRI mapping status.",
    )
    clo_ontology_version: Series[str] | None = pa.Field(
        nullable=True,
        description="CLO ontology release/version used for IRI mapping.",
    )
    cl_lincs_id: Series[str] | None = pa.Field(
        nullable=True,
        description="LINCS ID (Library of Integrated Network-Based Cellular Signatures).",
    )
    efo_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=EFO_ID_PATTERN,
        description="EFO ontology ID.",
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

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
