"""Pandera schema for ChEMBL target data.

This schema validates the structure and content of target data
after normalization.
"""

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.field_specs import (
    CHEMBL_ID_PATTERN,
    UNIPROT_ID_PATTERN,
)
from bioetl.infrastructure.validation.schemas.pandera_base import (
    BaseGeneratedColumnsSchema,
    build_output_column_order,
)

__all__ = ["TargetTableSchema", "OUTPUT_COLUMN_ORDER"]

_TARGET_BUSINESS_COLUMNS: list[str] = [
    "target_chembl_id",
    "pref_name",
    "score",
    "organism",
    "target_type",
    "tax_id",
    "species_group_flag",
    "target_components",
    "cross_references",
    "uniprot_id",
]

OUTPUT_COLUMN_ORDER: list[str] = build_output_column_order(_TARGET_BUSINESS_COLUMNS)


class TargetTableSchema(BaseGeneratedColumnsSchema):
    """Schema for biological target table (pipeline output).

    Validates ChEMBL target records including:
    - Target identifiers (ChEMBL, UniProt)
    - Target classification and type
    - Organism information
    - Cross-references
    """

    target_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_PATTERN, description="ChEMBL target identifier"
    )
    pref_name: Series[str] = pa.Field(
        nullable=True, description="Target preferred name"
    )
    score: Series[float] = pa.Field(nullable=True, description="Search ranking score")
    organism: Series[str] = pa.Field(nullable=True, description="Target organism")
    target_type: Series[str] = pa.Field(
        description="Target type (SINGLE PROTEIN, FAMILY, etc.)"
    )
    tax_id: Series[float] = pa.Field(nullable=True, description="NCBI Taxonomy ID")
    species_group_flag: Series[bool] = pa.Field(
        nullable=True, description="Species group target flag"
    )
    target_components: Series[str] = pa.Field(
        nullable=True, description="Target components (JSON)"
    )
    cross_references: Series[str] = pa.Field(
        nullable=True, description="External cross-references"
    )
    uniprot_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=UNIPROT_ID_PATTERN,
        description="Primary UniProt ID",
    )
