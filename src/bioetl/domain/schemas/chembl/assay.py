"""Pandera schema for ChEMBL Assay entity.

Aligned with RULES.md v5.24 and ChEMBL 34 schema.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.schemas.constants import (
    ASSAY_CATEGORIES,
    ASSAY_TEST_TYPES,
    ASSAY_TYPES,
    BAO_ID_PATTERN,
    CHEMBL_ID_PATTERN,
    RELATIONSHIP_TYPES,
)

__all__ = [
    "AssaySchema",
]


class AssaySchema(ETLRecordSchema):
    """Assay validation schema for Silver layer."""

    # === Primary Key ===
    # assay_id: Series[int] = pa.Field(
    #     nullable=False, description="Primary key."
    # )
    # Removed assay_id as it is not in Silver schema. assay_id is the PK.

    # === Identifiers ===
    assay_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=CHEMBL_ID_PATTERN,
        description="ChEMBL ID.",
    )

    # === Description & Classification ===
    description: Series[str] = pa.Field(
        nullable=False, description="Assay description."
    )
    assay_type: Series[str] = pa.Field(
        nullable=False,
        isin=list(ASSAY_TYPES),
        description="Assay type.",
    )
    assay_type_description: Series[str] = pa.Field(
        nullable=False, description="Assay type description."
    )
    assay_test_type: Series[str] | None = pa.Field(
        nullable=True,
        isin=list(ASSAY_TEST_TYPES),
        description="Assay test type.",
    )
    assay_category: Series[str] | None = pa.Field(
        nullable=True,
        isin=list(ASSAY_CATEGORIES),
        description="Assay category.",
    )
    assay_group: Series[str] | None = pa.Field(
        nullable=True, description="Assay group."
    )

    # === Biological Context ===
    assay_organism: Series[str] | None = pa.Field(
        nullable=True, description="Organism."
    )
    assay_taxonomy_id: Series[float] | None = pa.Field(
        nullable=True,
        description="NCBI Taxonomy ID (float for nullable int).",
    )
    assay_strain: Series[str] | None = pa.Field(nullable=True, description="Strain.")
    assay_tissue: Series[str] | None = pa.Field(nullable=True, description="Tissue.")
    assay_cell_type: Series[str] | None = pa.Field(
        nullable=True, description="Cell type."
    )
    assay_subcellular_fraction: Series[str] | None = pa.Field(
        nullable=True, description="Subcellular fraction."
    )

    # === Target & Relationship ===
    target_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=CHEMBL_ID_PATTERN,
        description="Target ChEMBL ID.",
    )
    relationship_type: Series[str] = pa.Field(
        nullable=False,
        isin=list(RELATIONSHIP_TYPES),
        description="Relationship type.",
    )
    relationship_description: Series[str] | None = pa.Field(
        nullable=True, description="Relationship description."
    )
    confidence_score: Series[float] = pa.Field(
        nullable=False,
        ge=0,
        le=9,
        description="Confidence score.",
    )
    confidence_description: Series[str] | None = pa.Field(
        nullable=True, description="Confidence description."
    )

    # === Curation & Metadata ===
    # curated_by: Optional[Series[str]] = pa.Field(
    #     nullable=True, description="Curator."
    # )
    # activity_count: Optional[Series[int]] = pa.Field(
    #     nullable=True,
    #     ge=0,
    #     description="Activity count.",
    # )
    src_id: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Source ID."
    )
    src_assay_id: Series[str] | None = pa.Field(
        nullable=True, description="Source Assay ID."
    )
    publication_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=CHEMBL_ID_PATTERN,
        description="Document ChEMBL ID.",
    )
    assay_pref_name: Series[str] | None = pa.Field(
        nullable=True, description="Preferred name."
    )
    score: Series[float] | None = pa.Field(nullable=True, description="Score.")

    # === Foreign Keys ===
    cell_id: Series[str] | None = pa.Field(
        nullable=True, description="FK to cell_line."
    )
    tissue_id: Series[str] | None = pa.Field(nullable=True, description="FK to tissue.")

    # === Other Fields ===
    bao_format: Series[str] = pa.Field(
        nullable=False,
        str_matches=BAO_ID_PATTERN,
        description="BAO format.",
    )
    bao_label: Series[str] | None = pa.Field(nullable=True, description="BAO label.")
    aidx: Series[str] | None = pa.Field(nullable=True, description="Assay index.")

    # === Variant Information (Flattened) ===
    variant_accession: Series[str] | None = pa.Field(
        nullable=True, description="Variant protein accession number."
    )
    variant_isoform: Series[str] | None = pa.Field(
        nullable=True, description="Variant isoform identifier."
    )
    variant_mutation: Series[str] | None = pa.Field(
        nullable=True, description="Variant mutation description."
    )
    variant_organism: Series[str] | None = pa.Field(
        nullable=True, description="Variant organism name."
    )
    variant_sequence: Series[str] | None = pa.Field(
        nullable=True, description="Variant amino acid sequence."
    )
    variant_taxonomy_id: Series[float] | None = pa.Field(
        nullable=True,
        description="Variant taxonomy ID (float for nullable int).",
    )
    variant_sequence_json: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of variant sequence details."
    )

    # === Complex Fields (JSON) ===
    assay_classifications: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of assay classifications."
    )
    assay_parameters: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of assay parameters."
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True

    @pa.check("confidence_score", name="confidence_score_integer")
    def confidence_score_integer(cls, series: Series[float]) -> Series[bool]:
        """Require confidence scores to remain integer-valued after coercion."""
        return series.mod(1).eq(0)
