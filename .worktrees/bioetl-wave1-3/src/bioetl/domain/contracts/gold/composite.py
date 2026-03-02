"""Composite Gold layer data contracts.

Contains Pandera DataFrameModel schemas for composite pipeline entities in the Gold layer:
- CompositePublicationGoldSchema: Merged publication from multiple providers
- CompositeMoleculeGoldSchema: Merged molecule from ChEMBL + PubChem

Composite schemas use qualified column names in format: {provider}.{entity}.{field}
This allows tracking which source contributed each value.

Int→Float coercion note:
    Fields marked with `coerce=True` and `Series[float]` that are `int64` in Silver
    use float to handle nullable integers. This is a deliberate design decision
    documented in RULES.md §2.6.

Note on strict mode:
    Composite schemas use ``strict = False`` because the actual columns depend on
    which enrichers succeeded. The schema validates core required fields while
    allowing extra provider-qualified columns (e.g. chembl.publication.title) through.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series


class CompositePublicationGoldSchema(pa.DataFrameModel):
    """Schema for Composite Publication in Gold layer.

    Merged publication entity combining data from multiple providers:
    - Seed: chembl_publication
    - Enrichers: crossref, openalex, pubmed, semanticscholar

    Column naming:
        Business columns use qualified format: {provider}.{entity}.{field}
        Example: chembl.publication.title, crossref.publication.citation_count

    Required fields:
        - System fields (entity_id)
        - Seed primary key (document_chembl_id via qualified name)
        - Title (required for valid publication)
        - Lineage metadata (_composite_run_id, etc.)

    Note: Uses strict=False to enforce required fields while allowing variable enricher columns.
    Note: content_hash is excluded from Gold layer by FieldGroupRegistry
          (SYSTEM_METADATA group, include_in_gold=False). It is computed in Silver
          for SCD Type 2 tracking but filtered out before Gold schema validation.
    """

    # =========================================================================
    # System Fields (from seed)
    # =========================================================================
    entity_id: Series[str] = pa.Field(
        nullable=False,
        description="Stable business identifier for merged publication entity.",
    )

    # =========================================================================
    # DQ Fields (from seed)
    # =========================================================================
    dq_warn: Series[bool] = pa.Field(
        nullable=False,
        default=False,
        alias="_dq_warn",
        description="Soft data-quality warning flag.",
    )
    dq_error: Series[bool] = pa.Field(
        nullable=False,
        default=False,
        alias="_dq_error",
        description="Hard data-quality error flag.",
    )

    # =========================================================================
    # Lineage Metadata (from seed)
    # =========================================================================
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    # Source tracking (from seed)
    source: Series[str] = pa.Field(nullable=True, alias="_source")

    # Lookup metadata (from seed)
    lookup_method: Series[str] = pa.Field(nullable=True, alias="_lookup_method")
    original_id: Series[str] = pa.Field(nullable=True, alias="_original_id")

    # =========================================================================
    # Composite Lineage Metadata (added by MergeService)
    # =========================================================================
    composite_run_id: Series[str] = pa.Field(nullable=False, alias="_composite_run_id")
    source_providers: Series[str] = pa.Field(
        nullable=False, alias="_source_providers"
    )  # JSON list
    enrichment_status: Series[str] = pa.Field(
        nullable=False, alias="_enrichment_status"
    )  # JSON dict
    lineage_created_at: Series[str] = pa.Field(
        nullable=False, alias="_lineage_created_at"
    )  # ISO timestamp

    # =========================================================================
    # Seed Primary Key (ChEMBL document ID)
    # =========================================================================
    # Note: Qualified column name from seed
    # In the merged output, this appears as: chembl.publication.document_chembl_id
    # The unqualified version may also be present depending on merge configuration

    # =========================================================================
    # Core Business Fields (may be qualified or coalesced)
    # =========================================================================
    # Note: These fields may appear with qualified names depending on merge strategy.
    # With coalesce/seed_priority, the winning value uses the seed column name.
    # With no coalesce, all provider columns are preserved with qualified names.
    #
    # Example qualified names:
    # - chembl.publication.title
    # - chembl.publication.document_chembl_id
    # - crossref.publication.citations_received
    # - pubmed.publication.subject_mesh
    # - openalex.publication.subject_topics
    # - semanticscholar.publication.tldr
    #
    # Since columns are dynamically determined by enrichers, we use strict="filter"

    class Config:
        """Pandera configuration.

        Note: strict=False validates required columns while allowing extra enricher columns.
        The actual columns depend on which enrichers succeeded and the merge strategy.
        """

        # Validate required contract columns while allowing extra
        # provider-qualified columns through.
        strict = False
        coerce = True  # Enable type coercion for nullable integers


class CompositeMoleculeGoldSchema(pa.DataFrameModel):
    """Schema for Composite Molecule in Gold layer.

    Merged molecule entity combining data from multiple providers:
    - Seed: chembl_molecule (pharmaceutical compounds with clinical data)
    - Enrichers: pubchem_compound (chemical properties and synonyms)

    Column naming:
        Business columns use qualified format: {provider}.{entity}.{field}
        Example: chembl.molecule.canonical_smiles, pubchem.compound.molecular_weight

    Join keys:
        - Primary: inchikey (IUPAC standard, 27 characters)
        - Fallback: canonical_smiles (less reliable due to canonization differences)

    Required fields:
        - System fields (entity_id)
        - Seed primary key (molecule_chembl_id)
        - Lineage metadata (_composite_run_id, etc.)

    Note: Uses strict=False to enforce required fields while allowing variable enricher columns.
    Note: content_hash is excluded from Gold layer by FieldGroupRegistry
          (SYSTEM_METADATA group, include_in_gold=False).
    """

    # =========================================================================
    # System Fields (from seed)
    # =========================================================================
    entity_id: Series[str] = pa.Field(
        nullable=False,
        description="Stable business identifier for merged molecule entity.",
    )

    # =========================================================================
    # DQ Fields (from seed)
    # =========================================================================
    dq_warn: Series[bool] = pa.Field(
        nullable=False,
        default=False,
        alias="_dq_warn",
        description="Soft data-quality warning flag.",
    )
    dq_error: Series[bool] = pa.Field(
        nullable=False,
        default=False,
        alias="_dq_error",
        description="Hard data-quality error flag.",
    )

    # =========================================================================
    # Lineage Metadata (from seed)
    # =========================================================================
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    # Note: _source is NOT present in chembl_molecule Silver (CSV-filter pipeline,
    # not enricher-mode). Provenance is tracked via _source_providers instead.

    # =========================================================================
    # Composite Lineage Metadata (added by MergeService)
    # =========================================================================
    composite_run_id: Series[str] = pa.Field(nullable=False, alias="_composite_run_id")
    source_providers: Series[str] = pa.Field(
        nullable=False, alias="_source_providers"
    )  # JSON list
    enrichment_status: Series[str] = pa.Field(
        nullable=False, alias="_enrichment_status"
    )  # JSON dict
    lineage_created_at: Series[str] = pa.Field(
        nullable=False, alias="_lineage_created_at"
    )  # ISO timestamp

    # =========================================================================
    # Seed Primary Key (ChEMBL molecule ID)
    # =========================================================================
    # Note: In merged output, this appears as: chembl.molecule.molecule_chembl_id
    # The unqualified version may also be present depending on merge configuration

    # =========================================================================
    # Core Business Fields (may be qualified or coalesced)
    # =========================================================================
    # Note: These fields may appear with qualified names depending on merge strategy.
    #
    # Example qualified names:
    # - chembl.molecule.molecule_chembl_id
    # - chembl.molecule.canonical_smiles
    # - chembl.molecule.inchi_key
    # - chembl.molecule.max_phase
    # - pubchem.compound.cid
    # - pubchem.compound.molecular_weight
    # - pubchem.compound.xlogp
    # - pubchem.compound.iupac_name
    #
    # Since columns are dynamically determined by enrichers, we use strict="filter"

    class Config:
        """Pandera configuration.

        Note: strict=False validates required columns while allowing extra enricher columns.
        The actual columns depend on which enrichers succeeded and the merge strategy.
        """

        # Validate required contract columns while allowing extra
        # provider-qualified columns through.
        strict = False
        coerce = True  # Enable type coercion for nullable integers


class CompositeActivityGoldSchema(pa.DataFrameModel):
    """Schema for Composite Activity in Gold layer.

    Merged activity entity with seed from ChEMBL activity and optional dependency
    enrichment from ChEMBL compound record.

    Uses strict=False because available qualified columns depend on dependency
    availability and merge configuration.
    """

    # Note: content_hash excluded from Gold (SYSTEM_METADATA, include_in_gold=False)
    entity_id: Series[str] = pa.Field(nullable=False)

    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    # Note: _source, _lookup_method, _original_id are NOT present in
    # chembl_activity Silver (CSV-filter pipeline, not enricher-mode).
    # Provenance is tracked via _source_providers instead.

    composite_run_id: Series[str] = pa.Field(nullable=False, alias="_composite_run_id")
    source_providers: Series[str] = pa.Field(nullable=False, alias="_source_providers")
    enrichment_status: Series[str] = pa.Field(
        nullable=False, alias="_enrichment_status"
    )
    lineage_created_at: Series[str] = pa.Field(
        nullable=False, alias="_lineage_created_at"
    )

    class Config:
        """Pandera configuration for composite activity output."""

        strict = False
        coerce = True


class CompositeAssayGoldSchema(pa.DataFrameModel):
    """Schema for Composite Assay in Gold layer.

    Merged assay entity with seed from ChEMBL assay and optional dependency/
    enricher data from cell line and tissue.
    """

    # Note: content_hash excluded from Gold (SYSTEM_METADATA, include_in_gold=False)
    entity_id: Series[str] = pa.Field(nullable=False)

    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    # Note: _source, _lookup_method, _original_id are NOT present in
    # chembl_assay Silver (CSV-filter pipeline, not enricher-mode).
    # Provenance is tracked via _source_providers instead.

    composite_run_id: Series[str] = pa.Field(nullable=False, alias="_composite_run_id")
    source_providers: Series[str] = pa.Field(nullable=False, alias="_source_providers")
    enrichment_status: Series[str] = pa.Field(
        nullable=False, alias="_enrichment_status"
    )
    lineage_created_at: Series[str] = pa.Field(
        nullable=False, alias="_lineage_created_at"
    )

    class Config:
        """Pandera configuration for composite assay output."""

        strict = False
        coerce = True


class CompositeTargetGoldSchema(pa.DataFrameModel):
    """Schema for Composite Target in Gold layer.

    Merged target entity with seed from ChEMBL target and optional dependency
    enrichment from target component, protein class, UniProt ID mapping, and
    UniProt protein datasets.
    """

    # Note: content_hash excluded from Gold (SYSTEM_METADATA, include_in_gold=False)
    entity_id: Series[str] = pa.Field(nullable=False)

    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    # Note: _source, _lookup_method, _original_id are NOT present in
    # chembl_target Silver (CSV-filter pipeline, not enricher-mode).
    # Provenance is tracked via _source_providers instead.

    composite_run_id: Series[str] = pa.Field(nullable=False, alias="_composite_run_id")
    source_providers: Series[str] = pa.Field(nullable=False, alias="_source_providers")
    enrichment_status: Series[str] = pa.Field(
        nullable=False, alias="_enrichment_status"
    )
    lineage_created_at: Series[str] = pa.Field(
        nullable=False, alias="_lineage_created_at"
    )

    class Config:
        """Pandera configuration for composite target output."""

        strict = False
        coerce = True


__all__ = [
    "CompositeActivityGoldSchema",
    "CompositeAssayGoldSchema",
    "CompositeMoleculeGoldSchema",
    "CompositePublicationGoldSchema",
    "CompositeTargetGoldSchema",
]
