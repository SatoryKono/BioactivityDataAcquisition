"""Pandera schema for normalized ChEMBL assay table.

This schema validates the structure and content of assay data
after normalization. Field definitions are based on domain specifications
in bioetl.domain.schemas.field_specs.
"""

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.field_specs import (
    BAO_ID_PATTERN,
    CHEMBL_ID_PATTERN,
)
from bioetl.infrastructure.validation.schemas.pandera_base import (
    BaseGeneratedColumnsSchema,
    build_output_column_order,
)

__all__ = ["AssayTableSchema", "OUTPUT_COLUMN_ORDER"]

_ASSAY_BUSINESS_COLUMNS: list[str] = [
    "aidx",
    "assay_category",
    "assay_cell_type",
    "assay_chembl_id",
    "assay_classifications",
    "assay_group",
    "assay_organism",
    "assay_parameters",
    "assay_strain",
    "assay_subcellular_fraction",
    "assay_tax_id",
    "assay_test_type",
    "assay_tissue",
    "assay_type",
    "assay_type_description",
    "bao_format",
    "bao_label",
    "cell_chembl_id",
    "confidence_description",
    "confidence_score",
    "description",
    "document_chembl_id",
    "relationship_description",
    "relationship_type",
    "score",
    "src_assay_id",
    "src_id",
    "target_chembl_id",
    "tissue_chembl_id",
    "variant_sequence",
]

OUTPUT_COLUMN_ORDER: list[str] = build_output_column_order(_ASSAY_BUSINESS_COLUMNS)


class AssayTableSchema(BaseGeneratedColumnsSchema):
    """Pandera schema describing normalized ChEMBL assay records.

    Validates ChEMBL assay definitions including:
    - Assay identifiers and descriptions
    - Target and cell mappings
    - Classification metadata
    - Confidence scores
    """

    aidx: Series[str] = pa.Field(
        nullable=True, description="Internal assay index/depositor ID"
    )
    assay_category: Series[str] = pa.Field(
        nullable=True,
        description="Assay category (primary/confirmatory/screening)",
    )
    assay_cell_type: Series[str] = pa.Field(
        nullable=True, description="Cell line type if applicable"
    )
    assay_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_PATTERN, description="ChEMBL assay identifier"
    )
    assay_classifications: Series[str] = pa.Field(
        nullable=True, description="Assay classifications (BAO, etc.)"
    )
    assay_group: Series[str] = pa.Field(nullable=True, description="Assay group/series")
    assay_organism: Series[str] = pa.Field(
        nullable=True, description="Testing system organism"
    )
    assay_parameters: Series[str] = pa.Field(
        nullable=True, description="Assay parameters (JSON)"
    )
    assay_strain: Series[str] = pa.Field(nullable=True, description="Organism strain")
    assay_subcellular_fraction: Series[str] = pa.Field(
        nullable=True, description="Subcellular fraction"
    )
    assay_tax_id: Series[float] = pa.Field(
        nullable=True, description="NCBI Taxonomy ID"
    )
    assay_test_type: Series[str] = pa.Field(
        nullable=True, description="Test type (in vitro, in vivo, ex vivo)"
    )
    assay_tissue: Series[str] = pa.Field(
        nullable=True, description="Tissue used in assay"
    )
    assay_type: Series[str] = pa.Field(
        isin=["B", "F", "A", "T", "P", "U"],
        description=(
            "Assay type (B=binding, F=functional, A=ADMET, T=toxicity, "
            "P=physicochemical, U=unknown)"
        ),
    )
    assay_type_description: Series[str] = pa.Field(
        nullable=True, description="Assay type description"
    )
    bao_format: Series[str] = pa.Field(
        nullable=True,
        str_matches=BAO_ID_PATTERN,
        description="BioAssay Ontology format",
    )
    bao_label: Series[str] = pa.Field(nullable=True, description="BAO format label")
    cell_chembl_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=CHEMBL_ID_PATTERN,
        description="ChEMBL cell line identifier",
    )
    confidence_description: Series[str] = pa.Field(
        nullable=True, description="Confidence level description"
    )
    confidence_score: Series[int] = pa.Field(
        nullable=True,
        ge=0,
        le=9,
        description="Target mapping confidence (0-9)",
    )
    description: Series[str] = pa.Field(nullable=True, description="Assay description")
    document_chembl_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=CHEMBL_ID_PATTERN,
        description="ChEMBL document identifier",
    )
    relationship_description: Series[str] = pa.Field(
        nullable=True, description="Relationship type description"
    )
    relationship_type: Series[str] = pa.Field(
        nullable=True,
        isin=["D", "H", "M", "N", "P", "T", "U", "d", "h", "m", "n", "p", "t", "u"],
        description="Assay-target relationship type",
    )
    score: Series[float] = pa.Field(nullable=True, description="Search ranking score")
    src_assay_id: Series[str] = pa.Field(
        nullable=True, description="Source database assay ID"
    )
    src_id: Series[float] = pa.Field(nullable=True, description="Data source ID")
    target_chembl_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=CHEMBL_ID_PATTERN,
        description="ChEMBL target identifier",
    )
    tissue_chembl_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=CHEMBL_ID_PATTERN,
        description="ChEMBL tissue identifier",
    )
    variant_sequence: Series[str] = pa.Field(
        nullable=True, description="Protein variant sequence if target is protein"
    )
