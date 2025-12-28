"""Pandera schema for ChEMBL Assay entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""
from __future__ import annotations

from typing import Optional

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class AssaySchema(ETLRecordSchema):
    """Assay validation schema for Silver/Gold layers."""

    # === Primary Key ===
    assay_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="Primary key (ChEMBL identifier).",
    )

    # === Foreign Keys ===
    target_chembl_id: Optional[Series[str]] = pa.Field(
        nullable=True,
        str_matches=r"^CHEMBL\d+$",
        description="Foreign key to Target entity.",
    )
    document_chembl_id: Optional[Series[str]] = pa.Field(
        nullable=True,
        str_matches=r"^CHEMBL\d+$",
        description="Foreign key to Document entity.",
    )
    cell_chembl_id: Optional[Series[str]] = pa.Field(
        nullable=True,
        str_matches=r"^CHEMBL\d+$",
        description="Foreign key to Cell Line entity.",
    )
    tissue_chembl_id: Optional[Series[str]] = pa.Field(
        nullable=True,
        str_matches=r"^CHEMBL\d+$",
        description="Foreign key to Tissue entity.",
    )
    src_id: Optional[Series[int]] = pa.Field(
        nullable=True, description="Source ID."
    )
    src_assay_id: Optional[Series[str]] = pa.Field(
        nullable=True, description="Source Assay ID."
    )

    # === Classification ===
    assay_type: Optional[Series[str]] = pa.Field(
        nullable=True,
        isin=["B", "F", "A", "T", "P", "U"],
        description="Assay type (Binding, Functional, ADMET, Toxicity, Physicochemical, Unclassified).",
    )
    assay_type_description: Optional[Series[str]] = pa.Field(
        nullable=True, description="Description of the assay type."
    )
    assay_category: Optional[Series[str]] = pa.Field(
        nullable=True, description="Assay category."
    )
    assay_test_type: Optional[Series[str]] = pa.Field(
        nullable=True, description="Assay test type."
    )
    assay_group: Optional[Series[str]] = pa.Field(
        nullable=True, description="Assay group."
    )

    # === Biological Context ===
    assay_organism: Optional[Series[str]] = pa.Field(
        nullable=True, description="Organism used in the assay."
    )
    assay_tax_id: Optional[Series[int]] = pa.Field(
        nullable=True, description="Taxonomy ID of the organism."
    )
    assay_cell_type: Optional[Series[str]] = pa.Field(
        nullable=True, description="Cell type used in the assay."
    )
    assay_tissue: Optional[Series[str]] = pa.Field(
        nullable=True, description="Tissue used in the assay."
    )
    assay_strain: Optional[Series[str]] = pa.Field(
        nullable=True, description="Strain used in the assay."
    )
    assay_subcellular_fraction: Optional[Series[str]] = pa.Field(
        nullable=True, description="Subcellular fraction used in the assay."
    )

    # === Description & Quality ===
    description: Optional[Series[str]] = pa.Field(
        nullable=True, description="Assay description."
    )
    confidence_score: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=0,
        le=9,
        description="Confidence score (0-9) indicating the quality of the target assignment.",
    )
    confidence_description: Optional[Series[str]] = pa.Field(
        nullable=True, description="Description of the confidence score."
    )
    relationship_type: Optional[Series[str]] = pa.Field(
        nullable=True,
        isin=["D", "H", "M", "N", "S", "U"],
        description="Relationship type (Direct, Homologous, etc.).",
    )
    relationship_description: Optional[Series[str]] = pa.Field(
        nullable=True, description="Description of the relationship type."
    )
    assay_pref_name: Optional[Series[str]] = pa.Field(
        nullable=True, description="Preferred name of the assay."
    )
    score: Optional[Series[float]] = pa.Field(
        nullable=True, description="Assay score."
    )

    # === BAO Annotations ===
    bao_format: Optional[Series[str]] = pa.Field(
        nullable=True,
        str_matches=r"^BAO:\d+$",
        description="BioAssay Ontology format ID.",
    )
    bao_label: Optional[Series[str]] = pa.Field(
        nullable=True, description="BioAssay Ontology label."
    )

    # === Variant Information (Flattened) ===
    variant_accession: Optional[Series[str]] = pa.Field(nullable=True)
    variant_isoform: Optional[Series[str]] = pa.Field(nullable=True)
    variant_mutation: Optional[Series[str]] = pa.Field(nullable=True)
    variant_organism: Optional[Series[str]] = pa.Field(nullable=True)
    variant_sequence: Optional[Series[str]] = pa.Field(nullable=True)
    variant_tax_id: Optional[Series[int]] = pa.Field(nullable=True)
    variant_sequence_json: Optional[Series[str]] = pa.Field(nullable=True)

    # === Complex Fields (JSON) ===
    assay_classifications: Optional[Series[str]] = pa.Field(
        nullable=True, description="JSON string of assay classifications."
    )
    assay_parameters: Optional[Series[str]] = pa.Field(
        nullable=True, description="JSON string of assay parameters."
    )
    aidx: Optional[Series[str]] = pa.Field(
        nullable=True, description="Assay index."
    )

    class Config:
        """Pandera configuration."""
        strict = True
        ordered = False
        coerce = True
