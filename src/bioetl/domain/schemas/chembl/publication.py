"""Pandera schema for ChEMBL Publication entity.

Aligned with RULES.md v5.10, ChEMBL 34 schema, and Publication Schema Unification spec.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.common.publication_base import (
    LOOKUP_METHODS,
    PublicationBaseSchema,
)
from bioetl.domain.validation import DOI_REGEX_PATTERN

# Re-export for backwards compatibility
__all__ = ["DOI_REGEX_PATTERN", "LOOKUP_METHODS", "ChemblPublicationSchema"]


class ChemblPublicationSchema(PublicationBaseSchema):
    """ChEMBL Publication validation schema for Silver layer.

    Inherits common fields from PublicationBaseSchema:
    - Cross-references: pmid, doi, pmc_id
    - Core content: title, abstract, authors
    - Metadata: journal, year, publication_date, doc_type (overridden), language
    - Metrics: citation_count
    - Open Access: is_oa
    - Lookup tracking: lookup_method (overridden), original_id, source
    """

    # === Primary Key (ChEMBL-specific) ===
    document_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="ChEMBL Document ID.",
    )

    # === Override lookup_method to be non-nullable ===
    lookup_method: Series[str] = pa.Field(
        alias="_lookup_method",
        nullable=False,
        isin=LOOKUP_METHODS,
        description="How record was resolved: direct for ChEMBL ID lookup",
    )

    # === Override doc_type with ChEMBL-specific values ===
    doc_type: Series[str] = pa.Field(
        nullable=True,
        isin=["PUBLICATION", "PATENT", "DATASET", "BOOK"],
        description="Document type.",
    )

    # === System Fields ===
    _source: Series[str] = pa.Field(
        nullable=False,
        default="chembl",
        description="Data source identifier.",
    )

    # === Provider-specific Identifiers ===
    src_id: Series[int] = pa.Field(nullable=True, description="Source ID.")

    # === ChEMBL Release Metadata ===
    chembl_release: Series[str] = pa.Field(
        nullable=True,
        description="ChEMBL release version (e.g., CHEMBL_1, CHEMBL_34).",
    )
    creation_date: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^\d{4}-\d{2}-\d{2}$",
        description="Record creation date in ChEMBL database (YYYY-MM-DD).",
    )

    # === Provider-specific Journal Fields ===
    journal_full_title: Series[str] = pa.Field(
        nullable=True, description="Full journal title."
    )
    volume: Series[str] = pa.Field(nullable=True, description="Volume.")
    issue: Series[str] = pa.Field(nullable=True, description="Issue.")
    first_page: Series[str] = pa.Field(nullable=True, description="First page.")
    last_page: Series[str] = pa.Field(nullable=True, description="Last page.")

    # === DQ Fields ===
    _dq_warn: Series[bool] = pa.Field(
        nullable=True, default=False, description="DQ warning flag."
    )
    _dq_error: Series[bool] = pa.Field(
        nullable=True, default=False, description="DQ error flag."
    )

    class Config:
        """Pandera configuration."""

        strict = False  # Allow missing columns and extra columns
        ordered = False
        coerce = True
