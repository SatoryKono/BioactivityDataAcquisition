"""Pandera schema for ChEMBL Publication entity.

Aligned with RULES.md v5.10, ChEMBL 34 schema, and Publication Schema Unification spec.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.common.publication_base import (
    LOOKUP_METHODS,
    PublicationBaseSchema,
)
from bioetl.domain.schemas.constants import (
    CHEMBL_ID_PATTERN,
    ISO_DATE_PATTERN,
    PUBLICATION_TYPES,
)
from bioetl.domain.validation import DOI_REGEX_PATTERN

# Re-export for backwards compatibility
__all__ = ["DOI_REGEX_PATTERN", "LOOKUP_METHODS", "ChemblPublicationSchema"]


class ChemblPublicationSchema(PublicationBaseSchema):
    """ChEMBL Publication validation schema for Silver layer.

    Inherits common fields from PublicationBaseSchema:
    - Cross-references: pmid, doi
    - Core content: title, abstract, authors
    - Metadata: journal, year, doc_type (overridden)
    - Lookup tracking: lookup_method (overridden), original_id, source

    Fields excluded from PyArrow/Gold schemas (not available from ChEMBL API):
    - pmc_id: ChEMBL API does not return PMC ID
    - publication_date: Only year is available, full date not provided
    - citation_count: Citation metrics not available from ChEMBL
    - is_oa: Open Access status not provided
    - language: Publication language not returned by ChEMBL
    """

    # === Primary Key (ChEMBL-specific) ===
    document_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=CHEMBL_ID_PATTERN,
        description="ChEMBL Document ID.",
    )

    # === Override lookup_method to be non-nullable ===
    lookup_method: Series[str] = pa.Field(
        alias="_lookup_method",
        nullable=False,
        isin=LOOKUP_METHODS,
        description="How record was resolved: direct for ChEMBL ID lookup",
    )

    # === Unified field names (ChEMBL-specific overrides) ===
    # Note: old fields 'year' and 'doc_type' removed - replaced by unified names
    publication_type: Series[str] = pa.Field(
        nullable=True,
        isin=list(PUBLICATION_TYPES),
        description="Document type (unified field name).",
    )

    # === System Fields ===
    _source: Series[str] = pa.Field(
        nullable=False,
        eq="chembl",
        description="Data source identifier.",
    )

    # === Provider-specific Identifiers ===
    src_id: Series[pd.Int64Dtype] = pa.Field(nullable=True, description="Source ID.")

    # === ChEMBL Release Metadata ===
    chembl_release: Series[str] = pa.Field(
        nullable=True,
        description="ChEMBL release version (e.g., CHEMBL_1, CHEMBL_34).",
    )
    creation_date: Series[str] = pa.Field(
        nullable=True,
        str_matches=ISO_DATE_PATTERN,
        description="Record creation date in ChEMBL database (YYYY-MM-DD).",
    )

    # === Provider-specific Journal Fields ===
    volume: Series[str] = pa.Field(nullable=True, description="Volume.")
    issue: Series[str] = pa.Field(nullable=True, description="Issue.")
    page_first: Series[str] = pa.Field(nullable=True, description="First page.")
    page_last: Series[str] = pa.Field(nullable=True, description="Last page.")

    # === DQ Fields ===
    _dq_warn: Series[pd.BooleanDtype] = pa.Field(
        nullable=True, default=False, description="DQ warning flag."
    )
    _dq_error: Series[pd.BooleanDtype] = pa.Field(
        nullable=True, default=False, description="DQ error flag."
    )

    class Config:
        """Pandera configuration."""

        strict = False  # Allow missing columns and extra columns
        ordered = False
        coerce = True
