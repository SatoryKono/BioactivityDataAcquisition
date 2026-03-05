"""ChEMBL reference/publication Gold-layer contracts."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series


class ChEMBLCellLineGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Cell Line in Gold layer."""

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary identifier
    cell_id: Series[str] = pa.Field(nullable=False)

    # Core metadata
    cell_name: Series[str] = pa.Field(nullable=False)
    cell_description: Series[str] = pa.Field(nullable=True)

    # Source information
    cell_source_tissue: Series[str] = pa.Field(nullable=True)
    cell_source_organism: Series[str] = pa.Field(nullable=True)
    cell_source_taxonomy_id: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # Standardized name

    # External identifiers
    cellosaurus_id: Series[str] = pa.Field(nullable=True)
    cl_lincs_id: Series[str] = pa.Field(nullable=True)
    efo_id: Series[str] = pa.Field(nullable=True)

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class ChEMBLCompoundRecordGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Compound Record in Gold layer."""

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary identifier
    record_id: Series[float] = pa.Field(nullable=False, coerce=True)  # int64 in Silver

    # Foreign keys
    molecule_id: Series[str] = pa.Field(nullable=False)
    publication_id: Series[str] = pa.Field(nullable=False)

    # Original compound names from document
    compound_key: Series[str] = pa.Field(nullable=True)
    compound_name: Series[str] = pa.Field(nullable=True)

    # Source information
    src_id: Series[float] = pa.Field(nullable=False, coerce=True)  # int64 in Silver
    src_compound_id: Series[str] = pa.Field(nullable=True)

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class ChEMBLDocumentGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Document in Gold layer."""

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)
    publication_id: Series[str] = pa.Field(nullable=False)
    # Cross-reference IDs (prefixed, for linking publications across providers)
    publication_doi: Series[str] = pa.Field(nullable=True)
    publication_pmid: Series[str] = pa.Field(nullable=True)
    publication_pmc_id: Series[str] = pa.Field(nullable=True)
    # Cross-reference IDs (raw identifiers from Silver)
    doi: Series[str] = pa.Field(nullable=True)
    pmc_id: Series[str] = pa.Field(nullable=True)
    pmid: Series[str] = pa.Field(nullable=True)
    # patent_id excluded from unified publication schema
    title: Series[str] = pa.Field(nullable=True)
    authors: Series[str] = pa.Field(nullable=True)
    abstract: Series[str] = pa.Field(nullable=True)
    affiliation_list: Series[str] = pa.Field(nullable=True)  # JSON array
    author_keys: Series[str] = pa.Field(nullable=True)  # Pipe-delimited Surname_F keys
    author_orcids: Series[str] = pa.Field(nullable=True)
    publication_type: Series[str] = pa.Field(nullable=True)
    publication_type_unified: Series[str] = pa.Field(nullable=True)
    publication_subclass: Series[str] = pa.Field(nullable=True)
    publication_class: Series[str] = pa.Field(nullable=True)
    publication_date: Series[str] = pa.Field(nullable=True)
    journal: Series[str] = pa.Field(nullable=True)
    publication_year: Series[float] = pa.Field(nullable=True, coerce=True)
    volume: Series[str] = pa.Field(nullable=True)
    issue: Series[str] = pa.Field(nullable=True)
    page_first: Series[str] = pa.Field(nullable=True)
    page_last: Series[str] = pa.Field(nullable=True)
    language: Series[str] = pa.Field(nullable=True)
    is_oa: Series[bool] = pa.Field(nullable=True, coerce=True)
    citations_received: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)
    citations_made: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)
    src_id: Series[float] = pa.Field(nullable=True, coerce=True)

    # ChEMBL release metadata
    chembl_release: Series[str] = pa.Field(nullable=True)
    creation_date: Series[str] = pa.Field(nullable=True)

    # System field (per SYSTEM_FIELDS_PREFIX)
    source: Series[str] = pa.Field(nullable=True, alias="_source")

    # Lookup metadata
    # _lookup_method: "direct" | "doi" | "pmid" | "title_fallback" | "unknown"
    # _original_id: Original identifier used for lookup (publication_id for direct)
    lookup_method: Series[str] = pa.Field(nullable=True, alias="_lookup_method")
    original_id: Series[str] = pa.Field(nullable=True, alias="_original_id")

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class ChEMBLDocumentSimilarityGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Document Similarity in Gold layer.

    Represents similarity between two ChEMBL documents based on Tanimoto coefficients.
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary key
    sim_id: Series[float] = pa.Field(nullable=False, coerce=True)  # int64 in Silver

    # Foreign keys
    doc_1: Series[float] = pa.Field(nullable=False, coerce=True)  # int64 in Silver
    doc_2: Series[float] = pa.Field(nullable=False, coerce=True)  # int64 in Silver

    # PubMed identifiers (numeric strings - matches Silver)
    pubmed_id1: Series[str] = pa.Field(nullable=True)
    pubmed_id2: Series[str] = pa.Field(nullable=True)

    # Tanimoto coefficients
    tid_tani: Series[float] = pa.Field(nullable=True, ge=0, le=1, coerce=True)
    mol_tani: Series[float] = pa.Field(nullable=True, ge=0, le=1, coerce=True)

    # Derived metrics
    avg_tani: Series[float] = pa.Field(nullable=True, ge=0, le=1, coerce=True)
    max_tani: Series[float] = pa.Field(nullable=True, ge=0, le=1, coerce=True)

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class ChEMBLDocumentTermGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Document Term in Gold layer.

    Derived entity extracted from Document records by flattening
    the 1:M relationship between documents and their terms.
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Composite key fields
    publication_id: Series[str] = pa.Field(nullable=False)
    term: Series[str] = pa.Field(nullable=False)
    term_type: Series[str] = pa.Field(nullable=False)

    # MeSH-specific fields
    mesh_id: Series[str] = pa.Field(nullable=True)
    qualifier: Series[str] = pa.Field(nullable=True)

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

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
    "ChEMBLCellLineGoldSchema",
    "ChEMBLCompoundRecordGoldSchema",
    "ChEMBLDocumentGoldSchema",
    "ChEMBLDocumentSimilarityGoldSchema",
    "ChEMBLDocumentTermGoldSchema",
]
