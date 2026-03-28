"""Pandera schema for ChEMBL Publication entity.

Aligned with RULES.md v5.24, ChEMBL 34 schema, and Publication Schema Unification spec.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.common.publication_base import (
    PublicationBaseSchema,
)
from bioetl.domain.schemas.constants import (
    CHEMBL_ID_PATTERN,
    ISO_DATE_PATTERN,
    PUBLICATION_TYPES,
)
from bioetl.domain.validation import DOI_REGEX_PATTERN

# Re-export for backwards compatibility
__all__ = ["DOI_REGEX_PATTERN", "ChemblPublicationSchema"]


class ChemblPublicationSchema(PublicationBaseSchema):
    """ChEMBL Publication validation schema for Silver layer.

    Inherits common fields from PublicationBaseSchema:
    - Cross-references: pmid, doi
    - Core content: title, abstract, authors
    - Metadata: journal, year, doc_type (overridden)
    - Lookup tracking: lookup_method, original_id, source

    Fields excluded from PyArrow/Gold schemas (not available from ChEMBL API):
    - pmc_id: ChEMBL API does not return PMC ID
    - publication_date: Only year is available, full date not provided
    - citation_count: Citation metrics not available from ChEMBL
    - is_oa: Open Access status not provided
    - language: Publication language not returned by ChEMBL
    """

    # === Primary Key (ChEMBL-specific) ===
    publication_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=CHEMBL_ID_PATTERN,
        description="ChEMBL Document ID.",
    )

    title: Series[str] = pa.Field(
        nullable=False,
        description="Publication title",
    )

    # _lookup_method: inherited from PublicationBaseSchema (non-nullable, isin=LOOKUP_METHODS)

    # === Unified field names (ChEMBL-specific overrides) ===
    # Note: old fields 'year' and 'doc_type' removed - replaced by unified names
    publication_type: Series[str] = pa.Field(
        nullable=False,
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
    src_id: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Source ID."
    )

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

    # DQ fields (_dq_warn, _dq_error) inherited from ETLRecordSchema as bool, nullable=False

    class Config:
        """Pandera configuration."""

        strict = False  # Allow extra columns beyond schema definition
        ordered = False
        coerce = True
        # Note: Fields from PublicationBaseSchema that ChEMBL doesn't provide
        # (pmc_id, affiliation_list, author_orcids, publication_date, language, is_oa)
        # are set to None by the transformer to satisfy schema inheritance
