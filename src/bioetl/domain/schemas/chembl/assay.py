"""Pandera schema for ChEMBL Assay entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class AssaySchema(ETLRecordSchema):
    """Assay validation schema for Silver layer."""

    # === Primary Key ===
    # assay_id: Series[int] = pa.Field(
    #     nullable=False, description="Primary key."
    # )
    # Removed assay_id as it is not in Silver schema. assay_chembl_id is the PK.

    # === Identifiers ===
    assay_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="ChEMBL ID.",
    )

    # === Description & Classification ===
    description: Series[str] | None = pa.Field(
        nullable=True, description="Assay description."
    )
    assay_type: Series[str] | None = pa.Field(
        nullable=True,
        isin=["B", "F", "A", "T", "P", "U"],
        description="Assay type.",
    )
    assay_test_type: Series[str] | None = pa.Field(
        nullable=True,
        isin=["In vivo", "In vitro", "Ex vivo"],
        description="Assay test type.",
    )
    assay_category: Series[str] | None = pa.Field(
        nullable=True,
        isin=["screening", "confirmatory", "panel", "summary", "other"],
        description="Assay category.",
    )
    assay_group: Series[str] | None = pa.Field(
        nullable=True, description="Assay group."
    )

    # === Biological Context ===
    assay_organism: Series[str] | None = pa.Field(
        nullable=True, description="Organism."
    )
    assay_tax_id: Series[int] | None = pa.Field(
        nullable=True, description="NCBI Taxonomy ID."
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
    target_chembl_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^CHEMBL\d+$",
        description="Target ChEMBL ID.",
    )
    relationship_type: Series[str] | None = pa.Field(
        nullable=True,
        isin=["D", "H", "M", "N", "S", "U"],
        description="Relationship type.",
    )
    relationship_description: Series[str] | None = pa.Field(
        nullable=True, description="Relationship description."
    )
    confidence_score: Series[int] | None = pa.Field(
        nullable=True,
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
    src_id: Series[int] | None = pa.Field(nullable=True, description="Source ID.")
    src_assay_id: Series[str] | None = pa.Field(
        nullable=True, description="Source Assay ID."
    )
    document_chembl_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^CHEMBL\d+$",
        description="Document ChEMBL ID.",
    )
    assay_pref_name: Series[str] | None = pa.Field(
        nullable=True, description="Preferred name."
    )
    score: Series[float] | None = pa.Field(nullable=True, description="Score.")

    # === Foreign Keys ===
    cell_chembl_id: Series[str] | None = pa.Field(
        nullable=True, description="FK to cell_line."
    )
    tissue_chembl_id: Series[str] | None = pa.Field(
        nullable=True, description="FK to tissue."
    )
    # variant_id: Optional[Series[int]] = pa.Field(
    #     nullable=True, description="FK to variant_sequences."
    # )

    # === Other Fields ===
    bao_format: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^BAO:\d+$",
        description="BAO format.",
    )
    bao_label: Series[str] | None = pa.Field(nullable=True, description="BAO label.")
    # a2t_complex: Optional[Series[int]] = pa.Field(
    #     nullable=True,
    #     isin=[0, 1],
    #     description="Assay-to-target complex flag.",
    # )
    # a2t_multi: Optional[Series[int]] = pa.Field(
    #     nullable=True,
    #     isin=[0, 1],
    #     description="Assay-to-target multi flag.",
    # )
    # mc_tax_id: Optional[Series[int]] = pa.Field(
    #     nullable=True, description="MC Tax ID."
    # )
    # mc_organism: Optional[Series[str]] = pa.Field(
    #     nullable=True, description="MC Organism."
    # )
    # mc_target_type: Optional[Series[str]] = pa.Field(
    #     nullable=True, description="MC Target Type."
    # )
    # mc_target_name: Optional[Series[str]] = pa.Field(
    #     nullable=True, description="MC Target Name."
    # )
    # mc_target_accession: Optional[Series[str]] = pa.Field(
    #     nullable=True, description="MC Target Accession."
    # )
    aidx: Series[str] | None = pa.Field(nullable=True, description="Assay index.")
    # ridx: Optional[Series[str]] = pa.Field(
    #     nullable=True, description="Record index."
    # )
    # tid_fixed: Optional[Series[int]] = pa.Field(
    #     nullable=True,
    #     isin=[0, 1],
    #     description="TID fixed flag.",
    # )

    # === Variant Information (Flattened) ===
    variant_accession: Series[str] | None = pa.Field(nullable=True)
    variant_isoform: Series[str] | None = pa.Field(nullable=True)
    variant_mutation: Series[str] | None = pa.Field(nullable=True)
    variant_organism: Series[str] | None = pa.Field(nullable=True)
    variant_sequence: Series[str] | None = pa.Field(nullable=True)
    variant_tax_id: Series[int] | None = pa.Field(nullable=True)
    variant_sequence_json: Series[str] | None = pa.Field(nullable=True)

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
