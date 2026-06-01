# mypy: disable-error-code="misc"
"""Composite activity/assay/target Gold schemas."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.contracts.gold._composite_gold_common_schema import (
    CompositeLookupLineageSchema,
)


class CompositeActivityGoldSchema(CompositeLookupLineageSchema):
    """Schema for Composite Activity in Gold layer."""

    activity_id: Series[str] = pa.Field(
        nullable=True,
        description="ChEMBL activity identifier retained as activity lineage anchor.",
    )
    molecule_id: Series[str] = pa.Field(
        nullable=True,
        description="ChEMBL molecule identifier used as activity-to-molecule lineage anchor.",
    )
    assay_id: Series[str] = pa.Field(
        nullable=True,
        description="ChEMBL assay identifier used as activity-to-assay lineage anchor.",
    )
    target_id: Series[str] = pa.Field(
        nullable=True,
        description="ChEMBL target identifier used as activity-to-target lineage anchor.",
    )
    taxonomy_id: Series[int] = pa.Field(
        nullable=True,
        description="NCBI taxonomy identifier retained as inherited target lineage metadata.",
    )
    publication_id: Series[str] = pa.Field(
        nullable=True,
        description="ChEMBL publication identifier used as activity-to-publication lineage anchor.",
    )
    record_id: Series[int] = pa.Field(
        nullable=True,
        description="ChEMBL compound record identifier retained as source-scoped lineage.",
    )
    src_id: Series[int] = pa.Field(
        nullable=True,
        description="Provider source identifier retained as source-scoped lineage metadata.",
    )
    canonical_smiles: Series[str] = pa.Field(
        nullable=True,
        description="Inherited molecule structure identifier retained for activity context.",
    )
    type: Series[str] = pa.Field(
        nullable=True,
        description="ChEMBL raw activity measurement type, not a generic canonical type.",
    )
    relation: Series[str] = pa.Field(
        nullable=True,
        description="ChEMBL raw activity measurement relation, not a generic canonical relation.",
    )
    value: Series[float] = pa.Field(
        nullable=True,
        description="ChEMBL raw activity measurement value, not a generic canonical value.",
    )


class CompositeAssayGoldSchema(CompositeLookupLineageSchema):
    """Schema for Composite Assay in Gold layer."""

    assay_id: Series[str] = pa.Field(
        nullable=True,
        description="ChEMBL assay identifier retained as assay lineage anchor.",
    )
    target_id: Series[str] = pa.Field(
        nullable=True,
        description="ChEMBL target identifier used as assay-to-target lineage anchor.",
    )
    publication_id: Series[str] = pa.Field(
        nullable=True,
        description="ChEMBL publication identifier used as assay-to-publication lineage anchor.",
    )
    src_id: Series[int] = pa.Field(
        nullable=True,
        description="Provider source identifier retained as source-scoped lineage metadata.",
    )
    description: Series[str] = pa.Field(
        nullable=True,
        description="ChEMBL assay description retained as source-scoped metadata.",
    )
    score: Series[float] = pa.Field(
        nullable=True,
        description="ChEMBL assay confidence score retained as source-scoped metadata.",
    )


class CompositeTargetGoldSchema(CompositeLookupLineageSchema):
    """Schema for Composite Target in Gold layer."""

    target_id: Series[str] = pa.Field(
        nullable=True,
        description="ChEMBL target identifier retained as target lineage anchor.",
    )
    uniprot_accession: Series[str] = pa.Field(
        nullable=True,
        description="UniProt accession retained as partial cross-source protein lineage anchor.",
    )
    taxonomy_id: Series[int] = pa.Field(
        nullable=True,
        description="NCBI taxonomy identifier retained as organism lineage metadata.",
    )
    description: Series[str] = pa.Field(
        nullable=True,
        description="Target description retained as source-scoped metadata.",
    )
    protein_classifications: Series[str] = pa.Field(
        nullable=True,
        description="Deterministic JSON provenance for target protein classifications.",
    )
    target_protein_class_id_L1: Series[str] = pa.Field(
        nullable=True, description="L1 target protein class ID."
    )
    target_protein_class_name_L1: Series[str] = pa.Field(
        nullable=True, description="L1 target protein class name."
    )
    target_protein_class_desc_L1: Series[str] = pa.Field(
        nullable=True, description="L1 target protein class description."
    )
    target_protein_class_id_L2: Series[str] = pa.Field(
        nullable=True, description="L2 target protein class ID."
    )
    target_protein_class_name_L2: Series[str] = pa.Field(
        nullable=True, description="L2 target protein class name."
    )
    target_protein_class_desc_L2: Series[str] = pa.Field(
        nullable=True, description="L2 target protein class description."
    )
    target_protein_class_id_L3: Series[str] = pa.Field(
        nullable=True, description="L3 target protein class ID."
    )
    target_protein_class_name_L3: Series[str] = pa.Field(
        nullable=True, description="L3 target protein class name."
    )
    target_protein_class_desc_L3: Series[str] = pa.Field(
        nullable=True, description="L3 target protein class description."
    )
    target_protein_class_id_L4: Series[str] = pa.Field(
        nullable=True, description="L4 target protein class ID."
    )
    target_protein_class_name_L4: Series[str] = pa.Field(
        nullable=True, description="L4 target protein class name."
    )
    target_protein_class_desc_L4: Series[str] = pa.Field(
        nullable=True, description="L4 target protein class description."
    )
    target_protein_class_id_L5: Series[str] = pa.Field(
        nullable=True, description="L5 target protein class ID."
    )
    target_protein_class_name_L5: Series[str] = pa.Field(
        nullable=True, description="L5 target protein class name."
    )
    target_protein_class_desc_L5: Series[str] = pa.Field(
        nullable=True, description="L5 target protein class description."
    )
