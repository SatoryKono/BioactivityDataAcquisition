# mypy: disable-error-code="misc"
"""ChEMBL target and lookup Gold-layer contracts."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series


class ChEMBLTargetGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Target in Gold layer."""

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)
    target_id: Series[str] = pa.Field(nullable=False)
    pref_name: Series[str] = pa.Field(nullable=True)
    target_type: Series[str] = pa.Field(nullable=True)
    organism: Series[str] = pa.Field(nullable=True)
    taxonomy_id: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # Standardized name
    organism_class: Series[str] = pa.Field(nullable=True)
    species_group_flag: Series[bool] = pa.Field(nullable=True)
    description: Series[str] = pa.Field(nullable=True)
    downgraded: Series[bool] = pa.Field(nullable=True, coerce=True)
    pipeline_stages: Series[str] = pa.Field(nullable=True)
    target_components: Series[str] = pa.Field(nullable=True)
    cross_references: Series[str] = pa.Field(nullable=True)
    target_component_synonyms: Series[str] = pa.Field(nullable=True)
    component_accessions: Series[str] = pa.Field(nullable=True)  # list[str]
    primary_component_id: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # int → float (nullable)
    component_ids: Series[str] = pa.Field(nullable=True)  # list[int]
    component_types: Series[str] = pa.Field(nullable=True)  # list[str]
    component_descriptions: Series[str] = pa.Field(nullable=True)
    component_relationships: Series[str] = pa.Field(nullable=True)  # list[str]

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class ChEMBLTargetComponentGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Target Component in Gold layer."""

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)
    primary_component_id: Series[float] = pa.Field(
        nullable=False, coerce=True, alias="component_id"
    )  # int64
    accession: Series[str] = pa.Field(nullable=True)
    component_type: Series[str] = pa.Field(nullable=True)
    description: Series[str] = pa.Field(nullable=True)
    organism: Series[str] = pa.Field(nullable=True)
    taxonomy_id: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # Standardized name
    target_component_synonyms: Series[str] = pa.Field(nullable=True)
    target_component_xrefs: Series[str] = pa.Field(nullable=True)
    protein_classifications: Series[str] = pa.Field(nullable=True)
    protein_classification_id: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # int → float (nullable)
    protein_classification_ids: Series[str] = pa.Field(nullable=True)  # list[int]

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class ChEMBLTissueGoldSchema(pa.DataFrameModel):
    """Gold schema for ChEMBL Tissue entity.

    Validates:
    - tissue_id: Required, CHEMBL format (aliased from tissue_chembl_id by transformer)
    - pref_name: Required, non-empty
    - Ontology IDs: Optional, format validation
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary key (transformer maps tissue_chembl_id → tissue_id)
    tissue_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="ChEMBL tissue ID",
    )

    # Core metadata
    pref_name: Series[str] = pa.Field(
        nullable=False,
        str_length={"min_value": 1, "max_value": 200},
        description="Preferred tissue name",
    )

    # Ontology identifiers (optional)
    bto_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^BTO:\d{7}$",
        description="BRENDA Tissue Ontology ID",
    )
    caloha_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^TS-\d{4}$",
        description="CALIPHO ID",
    )
    efo_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^EFO[:_]\d{7}$",
        description="Experimental Factor Ontology ID",
    )
    uberon_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^UBERON[:_]\d{7}$",
        description="Uberon Ontology ID",
    )

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class ChEMBLSubcellularFractionGoldSchema(pa.DataFrameModel):
    """Gold schema for ChEMBL Subcellular Fraction entity.

    Derived entity: unique subcellular fractions extracted from Assay records.
    Creates a lookup/reference table for biological context normalization.

    Validates:
    - entity_id: Required, 16-char SHA256 prefix
    - subcellular_fraction: Required, non-empty
    - assay_count: Optional, non-negative
    - example_assay_chembl_id: Optional, CHEMBL format
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary key (normalized subcellular fraction name)
    subcellular_fraction: Series[str] = pa.Field(
        nullable=False,
        str_length={"min_value": 1, "max_value": 200},
        description="Subcellular fraction name",
    )

    # Statistics
    assay_count: Series[float] = pa.Field(
        nullable=True,
        coerce=True,
        description="Number of assays using this fraction",
    )

    # Example reference
    example_assay_id: Series[str] = pa.Field(
        nullable=True,
        description="Example assay ChEMBL ID",
    )

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


__all__ = [
    "ChEMBLSubcellularFractionGoldSchema",
    "ChEMBLTargetComponentGoldSchema",
    "ChEMBLTargetGoldSchema",
    "ChEMBLTissueGoldSchema",
]
