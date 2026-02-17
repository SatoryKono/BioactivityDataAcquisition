"""UniProt Gold layer data contracts.

Contains Pandera DataFrameModel schemas for UniProt entities in the Gold layer:
- Protein: UniProt protein sequences and metadata
- IDMapping: ChEMBL→UniProt target ID mappings with status tracking

Int→Float coercion note:
    Fields marked with `coerce=True` and `Series[float]` that are `int64` in Silver
    use float to handle nullable integers. This is a deliberate design decision
    documented in RULES.md §2.6.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series


class UniProtProteinGoldSchema(pa.DataFrameModel):
    """Schema for UniProt Protein in Gold layer.

    Extended schema with functional annotations, cross-references, and quality metrics.
    See Silver schema in infrastructure/schemas/silver.py for field descriptions.
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Core identifiers
    accession: Series[str] = pa.Field(nullable=False)
    entry_name: Series[str] = pa.Field(nullable=True)

    # Structural features (JSON)
    active_sites: Series[str] = pa.Field(nullable=True)  # ft_act_site features
    binding_sites: Series[str] = pa.Field(nullable=True)  # ft_binding features
    domains: Series[str] = pa.Field(nullable=True)  # ft_domain features
    features_json: Series[str] = pa.Field(nullable=True)  # All features (forensic)

    # Functional annotations
    activity_regulation: Series[str] = pa.Field(nullable=True)
    catalytic_activity: Series[str] = pa.Field(nullable=True)
    disease_involvement: Series[str] = pa.Field(nullable=True)
    function_comment: Series[str] = pa.Field(nullable=True)
    pathway: Series[str] = pa.Field(nullable=True)
    similarity_comment: Series[str] = pa.Field(nullable=True)
    subcellular_location: Series[str] = pa.Field(nullable=True)
    tissue_specificity: Series[str] = pa.Field(nullable=True)

    # Cross-references (JSON arrays)
    chembl_ids: Series[str] = pa.Field(nullable=True)
    drugbank_ids: Series[str] = pa.Field(nullable=True)
    go_terms: Series[str] = pa.Field(nullable=True)
    interpro_xrefs: Series[str] = pa.Field(nullable=True)
    pdb_xrefs: Series[str] = pa.Field(nullable=True)
    pfam_xrefs: Series[str] = pa.Field(nullable=True)
    reactome_xrefs: Series[str] = pa.Field(nullable=True)

    # Basic protein data
    gene_names: Series[str] = pa.Field(nullable=True)  # list[str]
    organism_id: Series[float] = pa.Field(nullable=True, coerce=True)  # int64 → float
    protein_name: Series[str] = pa.Field(nullable=True)
    sequence_length: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # int64 → float

    # Quality metrics
    annotation_score: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # int64 → float
    protein_existence: Series[str] = pa.Field(nullable=True)  # Evidence level string
    reviewed: Series[bool] = pa.Field(
        nullable=True, coerce=True
    )  # Swiss-Prot vs TrEMBL

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class UniProtIDMappingGoldSchema(pa.DataFrameModel):
    """Schema for UniProt ID Mapping in Gold layer.

    Maps ChEMBL target IDs to UniProt accessions with entry metadata.
    Records with mapping_status='not_found' have null uniprot_accession.
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary key (source identifier)
    target_id: Series[str] = pa.Field(nullable=False)

    # Mapped identifier (nullable - None if not found)
    uniprot_accession: Series[str] = pa.Field(nullable=True)

    # Mapping status: 'found', 'not_found', 'error', 'multiple'
    mapping_status: Series[str] = pa.Field(nullable=False)

    # UniProt entry metadata
    uniprot_entry_name: Series[str] = pa.Field(nullable=True)
    organism_scientific: Series[str] = pa.Field(nullable=True)
    organism_common: Series[str] = pa.Field(nullable=True)
    taxonomy_id: Series[float] = pa.Field(nullable=True, coerce=True)  # int → float
    protein_name: Series[str] = pa.Field(nullable=True)
    gene_primary: Series[str] = pa.Field(nullable=True)
    sequence_length: Series[float] = pa.Field(nullable=True, coerce=True)  # int → float
    sequence_mass: Series[float] = pa.Field(nullable=True, coerce=True)  # int → float
    reviewed: Series[bool] = pa.Field(nullable=True, coerce=True)  # nullable bool
    annotation_score: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # int → float
    all_mappings: Series[str] = pa.Field(nullable=True)

    # DQ warning flag (True for not_found)
    dq_warn: Series[bool] = pa.Field(nullable=False, alias="_dq_warn")

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


__all__ = [
    "UniProtIDMappingGoldSchema",
    "UniProtProteinGoldSchema",
]
