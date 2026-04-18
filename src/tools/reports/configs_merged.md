================================================================================
File: bronze_fixture_gaps.yaml
Path: base\bronze_fixture_gaps.yaml
================================================================================
version: 1.1.0
updated_at: "2026-03-25"
gaps:
  chembl/assay:
    status: in_progress
    reason: "Bronze fixture snapshots are local runtime artifacts and are not versioned in Git."
    owner: "data-platform"
    resolution_plan: "Promote a bounded assay sample into tracked test fixtures and register it in bronze_fixture_manifest.yaml."
  chembl/assay_parameters:
    status: open
    reason: "No factual Bronze JSONL artifacts are currently available in data/input or data/output."
    owner: "data-platform"
    resolution_plan: "Generate fixture from dedicated assay-parameters extraction run or VCR payloads."
  chembl/cell_line:
    status: open
    reason: "Bronze fixture snapshot was not materialized; only DQ report artifact existed."
    owner: "data-platform"
    resolution_plan: "Extract representative records from ChEMBL cell_line VCR cassettes into sample_*.jsonl."
  chembl/compound_record:
    status: open
    reason: "Bronze fixture snapshot was not materialized; only DQ report artifact existed."
    owner: "data-platform"
    resolution_plan: "Extract representative records from ChEMBL compound_record VCR cassettes into sample_*.jsonl."
  chembl/protein_class:
    status: open
    reason: "No factual Bronze JSONL artifacts are currently available in data/input or data/output."
    owner: "data-platform"
    resolution_plan: "Run pipeline or extract protein_classification records from VCR-backed requests."
  chembl/publication:
    status: in_progress
    reason: "Bronze publication fixtures are local runtime artifacts and are not versioned in Git."
    owner: "data-platform"
    resolution_plan: "Move a bounded publication sample into tracked test fixtures or fixture manifest."
  chembl/publication_similarity:
    status: open
    reason: "No factual Bronze JSONL artifacts are currently available in data/input or data/output."
    owner: "data-platform"
    resolution_plan: "Generate fixture from document_similarity endpoint captures or a bounded pipeline run."
  chembl/publication_term:
    status: open
    reason: "Current publication input sample has no mesh_terms/keywords to derive publication_term records."
    owner: "data-platform"
    resolution_plan: "Build fixture from publication_term VCR captures containing mesh/keyword records."
  chembl/subcellular_fraction:
    status: open
    reason: "No factual Bronze JSONL artifacts are currently available in data/input or data/output."
    owner: "data-platform"
    resolution_plan: "Create fixture using subcellular-fraction datasource output from a controlled run."
  chembl/target:
    status: in_progress
    reason: "Bronze fixture snapshots are local runtime artifacts and are not versioned in Git."
    owner: "data-platform"
    resolution_plan: "Introduce tracked lightweight fixture manifest or checked-in sample JSONL set for CI."
  chembl/target_component:
    status: open
    reason: "Bronze fixture snapshot was not materialized; only DQ report artifact existed."
    owner: "data-platform"
    resolution_plan: "Extract representative records from ChEMBL target_component VCR cassettes into sample_*.jsonl."
  chembl/tissue:
    status: open
    reason: "No factual Bronze JSONL artifacts are currently available in data/input or data/output."
    owner: "data-platform"
    resolution_plan: "Create fixture from tissue endpoint extraction run and persist sample_*.jsonl."
  openalex/publication:
    status: in_progress
    reason: "Bronze publication fixtures are local runtime artifacts and are not versioned in Git."
    owner: "data-platform"
    resolution_plan: "Promote bounded OpenAlex publication sample into tracked fixture storage."
  pubchem/compound:
    status: open
    reason: "Bronze fixture snapshot was not materialized; only DQ report artifact existed."
    owner: "data-platform"
    resolution_plan: "Materialize normalized PubChem adapter records into sample_*.jsonl from VCR-backed run."
  semanticscholar/publication:
    status: in_progress
    reason: "Bronze publication fixtures are local runtime artifacts and are not versioned in Git."
    owner: "data-platform"
    resolution_plan: "Promote bounded Semantic Scholar publication sample into tracked fixture storage."
  uniprot/idmapping:
    status: open
    reason: "No Bronze input directory/JSONL fixture exists for idmapping pipeline."
    owner: "data-platform"
    resolution_plan: "Generate sample idmapping records from UniProt ID mapping VCR cassettes."
  uniprot/protein:
    status: open
    reason: "Bronze fixture snapshot was not materialized; only DQ report artifact existed."
    owner: "data-platform"
    resolution_plan: "Extract representative UniProt protein records from VCR cassettes into sample_*.jsonl."

================================================================================
File: bronze_fixture_manifest.yaml
Path: base\bronze_fixture_manifest.yaml
================================================================================
version: 1.0.0
updated_at: "2026-03-25"
fixtures:
  chembl/activity:
    fixture_kind: tracked_ci_sample
    fixture_path: tests/fixtures/bronze/chembl/activity/sample_ci_2026-03-25.jsonl
    records: 20
    provenance: "Bounded CI sample extracted from representative Bronze snapshots."
    owner: "data-platform"
    last_refresh: "2026-03-25"
    validation_status: valid
  chembl/molecule:
    fixture_kind: tracked_ci_sample
    fixture_path: tests/fixtures/bronze/chembl/molecule/sample_ci_2026-03-25.jsonl
    records: 20
    provenance: "Bounded CI sample extracted from representative Bronze snapshots."
    owner: "data-platform"
    last_refresh: "2026-03-25"
    validation_status: valid
  crossref/publication:
    fixture_kind: tracked_ci_sample
    fixture_path: tests/fixtures/bronze/crossref/publication/sample_ci_2026-03-25.jsonl
    records: 20
    provenance: "Bounded CI sample extracted from representative Bronze snapshots."
    owner: "data-platform"
    last_refresh: "2026-03-25"
    validation_status: valid
  pubmed/publication:
    fixture_kind: tracked_ci_sample
    fixture_path: tests/fixtures/bronze/pubmed/publication/sample_ci_2026-03-25.jsonl
    records: 20
    provenance: "Bounded CI sample extracted from representative Bronze snapshots."
    owner: "data-platform"
    last_refresh: "2026-03-25"
    validation_status: valid

================================================================================
File: contract_registry.yaml
Path: base\contract_registry.yaml
================================================================================
# Contract Registry
# Machine-verifiable governance for data contracts.

version: "1.0"
entries:
  chembl.molecule:
    identity:
      contract_version: "1.0.0"
      compatibility_level: "major"
      schema_hash: "21d72caf50bf2693400387dc42cad8deaa305444caf7b6a19845af0e81521b47"
      dq_policy_ref: "chembl.dq.v1"
      rule_bundle_version: "dq-rules.v1.0"
    status: "active"
    source_path: "../../src/bioetl/domain/contracts/gold/_chembl_molecule_target_schemas.py"
    published_artifacts:
      - "../../docs/04-reference/contracts/gold/chembl_molecule_v1.0.json"
    supported_versions: ["1.0.0"]
    migration_guides: {}
    last_updated: "2026-03-25T00:00:00Z"
    owners: ["chembl-team"]
    dq_policy_ref: "chembl.dq.v1"
    rule_bundle_version: "dq-rules.v1.0"

  chembl.activity:
    identity:
      contract_version: "1.0.0"
      compatibility_level: "major"
      schema_hash: "a783fd6145e41d1da4d854040ba627aad83602627f92d494a9f040e51b3b49ac"
      dq_policy_ref: "chembl.dq.v1"
      rule_bundle_version: "dq-rules.v1.0"
    status: "active"
    source_path: "../../src/bioetl/domain/contracts/gold/_chembl_activity_assay_schemas.py"
    published_artifacts:
      - "../../docs/04-reference/contracts/gold/chembl_activity_v1.0.json"
    supported_versions: ["1.0.0"]
    migration_guides: {}
    last_updated: "2026-03-25T00:00:00Z"
    owners: ["chembl-team"]
    dq_policy_ref: "chembl.dq.v1"
    rule_bundle_version: "dq-rules.v1.0"

  pubchem.compound:
    identity:
      contract_version: "1.0.0"
      compatibility_level: "major"
      schema_hash: "caa17be6e466eaae2eb97f9fffda050897bdf5e7169ab5ed7e92a73320ba79f5"
      dq_policy_ref: "pubchem.dq.v1"
      rule_bundle_version: "dq-rules.v1.0"
    status: "active"
    source_path: "../../src/bioetl/domain/contracts/gold/pubchem.py"
    published_artifacts:
      - "../../docs/04-reference/contracts/gold/pubchem_compound_v1.0.json"
    supported_versions: ["1.0.0"]
    migration_guides: {}
    last_updated: "2026-03-25T00:00:00Z"
    owners: ["pubchem-team"]
    dq_policy_ref: "pubchem.dq.v1"
    rule_bundle_version: "dq-rules.v1.0"

  pubmed.publication:
    identity:
      contract_version: "1.0.0"
      compatibility_level: "major"
      schema_hash: "fb070a529d0c8c2ac0001b4f66e0815dc68c9415e166ffc76b1adc6944c0e6b1"
      dq_policy_ref: "pubmed.dq.v1"
      rule_bundle_version: "dq-rules.v1.0"
    status: "active"
    source_path: "../../src/bioetl/domain/contracts/gold/publications_pubmed.py"
    published_artifacts:
      - "../../docs/04-reference/contracts/gold/pubmed_publication_v1.0.json"
    supported_versions: ["1.0.0"]
    migration_guides: {}
    last_updated: "2026-03-25T00:00:00Z"
    owners: ["biblio-team"]
    dq_policy_ref: "pubmed.dq.v1"
    rule_bundle_version: "dq-rules.v1.0"

  crossref.works:
    identity:
      contract_version: "1.0.0"
      compatibility_level: "major"
      schema_hash: "de52b06a3ff61efedba5dd82a3570c191b532102e8d988f891f41dedc499b3bb"
      dq_policy_ref: "crossref.dq.v1"
      rule_bundle_version: "dq-rules.v1.0"
    status: "active"
    source_path: "../../src/bioetl/domain/contracts/gold/publications_crossref.py"
    published_artifacts:
      - "../../docs/04-reference/contracts/gold/crossref_publication_v1.0.json"
    supported_versions: ["1.0.0"]
    migration_guides: {}
    last_updated: "2026-03-25T00:00:00Z"
    owners: ["biblio-team"]
    dq_policy_ref: "crossref.dq.v1"
    rule_bundle_version: "dq-rules.v1.0"

metadata:
  last_updated: "2026-03-25T00:00:00Z"
  updated_by: "wave-2-governance-kernel"
  governance_policy: "ADR-045"
  validation_rules:
    - "All contracts must have explicit owners"
    - "All contracts must have valid source paths"
    - "Current version must be in supported_versions"
    - "Migration guides must exist for all version transitions"

================================================================================
File: pipeline.yaml
Path: base\pipeline.yaml
================================================================================
# =============================================================================
# Base Pipeline Configuration — consolidated defaults
# =============================================================================
# Preferred base path for pipeline defaults.
# Legacy fallback remains: configs/pipelines/_base.yaml

version: "1.2.0"
technical_primary_key: "entity_id"

# Loading strategy (ADR-031). null = default incremental.
loading_strategy: null

source: { }

transform:
    steps: [ ]

# DQ defaults are loaded via DQConfigLoader (base/quality.yaml).
dq_overrides: { }

sink:
    bronze:
        format: jsonl
        save_json: true
        save_metadata: true
        dq_report:
            enabled: true
        flat_structure: true

    silver:
        format: delta
        mode: merge
        sort_by:
            - entity_id
        on_schema_mismatch: evolve
        save_metadata: true
        dq_report:
            enabled: true
        csv_export:
            enabled: true
            delimiter: ","
            header: true
            encoding: "utf-8"
        flat_structure: true

    gold:
        enabled: true
        format: delta
        mode: scd2
        sort_by:
            - entity_id
        scd_config:
            valid_from_col: _valid_from
            valid_to_col: _valid_to
            current_flag_col: _is_current
            version_col: _version
        deterministic: true
        save_metadata: true
        dq_report:
            enabled: true
        csv_export:
            enabled: true
            delimiter: ","
            header: true
            encoding: "utf-8"
        flat_structure: true

maintenance:
    auto_vacuum: false
    vacuum_retention_days: 7

input_filter:
    enabled: false
    batch_size: 1000

# Replaces configs/filters/_defaults.yaml
filter_defaults:
    silver_filters:
        required_fields: [ ]
        columns: { }
        ranges: { }
        list_lengths: { }
        list_contains: { }
        exclude_if_present: [ ]
    gold_filters:
        required_fields: [ ]
        columns: { }
        ranges: { }
        list_lengths: { }
        list_contains: { }
        exclude_if_present: [ ]

# Shared contract defaults for future contract consolidation.
contract_defaults:
    rename_map:
        run_id: _run_id
        run_type: _run_type
        source_batch_id: _source_batch_id
        ingestion_ts: _ingestion_ts
        source: _source
    hash_include: [ ]
    hash_exclude:
        - _ingestion_ts
        - _run_id
        - _run_type
        - _dq_error
        - _dq_warn

================================================================================
File: quality.yaml
Path: base\quality.yaml
================================================================================
# configs/base/quality.yaml
# Global DQ defaults for all BioETL pipelines.
# Preferred defaults path for DQConfigLoader.

version: "1.0.0"

thresholds:
  soft_fail: 0.05
  hard_fail: 0.20

strict_validation: false
invalid_record_policy: quarantine

report:
  enabled: true
  format: json
  include_sample_failures: true
  sample_size: 10
  output_path: null

common_field_validations:
  - field: _content_hash
    type: required
    nullable: false
    error_message: "Content hash is required for deduplication"

  - field: _ingestion_ts
    type: pattern
    pattern: '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
    nullable: false
    error_message: "Ingestion timestamp must be ISO 8601 format"

common_cross_field_validations: []

================================================================================
File: activity.yaml
Path: composites\activity.yaml
================================================================================
# configs/composites/activity.yaml
# =============================================================================
# Composite Activity Pipeline Configuration
# =============================================================================
#
# Combines bioactivity data from ChEMBL with compound record metadata:
# - Seed: ChEMBL activities (activity_id, molecule_id, ...)
# - Dependencies:
#   1. chembl_compound_record: compound records filtered by
#      molecule_id AND publication_id (dual-key enrichment)
#
# This pipeline enables correlation of activity measurements with their
# original compound names and document references from compound records.
#
# Join Strategy:
# - Composite key: (molecule_id, publication_id)
# - Activity → CompoundRecord is ~1:1 with composite key
#   (one compound record per molecule-document pair)
# - Merge uses left_outer to preserve all activities
#
# Version: 1.0.0
# Reference: ADR-026 Composite Pipeline Pattern
# Last Updated: 2026-02-04
#
# =============================================================================

# -----------------------------------------------------------------------------
# Composite Pipeline Configuration
# -----------------------------------------------------------------------------
composite:
  name: composite_activity
  version: "1.0.0"

  # ---------------------------------------------------------------------------
  # Seed Pipeline Configuration
  # ---------------------------------------------------------------------------
  # The seed pipeline extracts bioactivity data from ChEMBL.
  # Its output provides join keys (molecule_id, publication_id)
  # for dependency dual-key filtering and composite join.
  seed:
    pipeline: chembl_activity
    output_keys:
      - activity_id           # Primary key
      - molecule_id           # FK for compound_record join (key 1)
      - assay_id              # FK for future assay enrichment
      - target_id             # FK for future target enrichment
      - publication_id        # FK for compound_record join (key 2)
    silver_table: silver/chembl/activity

  # ---------------------------------------------------------------------------
  # Dependency Pipelines (sequential execution)
  # ---------------------------------------------------------------------------
  # compound_record is a dependency (not enricher) because:
  # 1. It requires API calls (not just Silver table lookup)
  # 2. It should be filtered by molecule_id AND publication_id
  # 3. It must complete before any merge can occur
  dependencies:
    # ChEMBL Compound Record: original compound names from publications
    # Fetches compound records filtered by BOTH molecule_id AND
    # publication_id from seed (dual-key enrichment).
    # API call: /compound_record?molecule_id__in=...&publication_id__in=...
    # This produces ~1:1 mapping (one record per molecule-document pair).
    - pipeline: chembl_compound_record
      join_keys:
        - molecule_id          # Composite join key 1
        - publication_id       # Composite join key 2
      filter_fields:           # Multi-field API filtering (AND logic)
        - molecule_id
        - publication_id
      required: false          # Optional - missing records don't block composite
      timeout_seconds: 600
      silver_table: silver/chembl/compound_record

  # ---------------------------------------------------------------------------
  # Enricher Pipelines
  # ---------------------------------------------------------------------------
  # Currently empty. Future expansion could include:
# - PubChem compound properties (via molecule_id → inchi_key → PubChem)
# - UniProt target data (via target_id → UniProt accession)
  enrichers: []

  # ---------------------------------------------------------------------------
  # Merge Configuration
  # ---------------------------------------------------------------------------
  # Defines how compound_record data is joined with activities.
  merge:
    # Join strategy: left_outer preserves all activities
    strategy: left_outer

    # Conflict resolution: seed (activity) values take priority
    conflict_resolution: seed_priority

    # Preserve provider-qualified columns for overlapping fields
    # molecule_id appears in both sources, keep both for lineage
    preserve_all_sources: false

    # Output paths for merged data
    output:
      silver: data/output/silver/composite/activity
      gold: data/output/gold/composite/activity
    sort_by:
      silver:
        - entity_id
        - activity_id
      gold:
        - entity_id
        - activity_id

    # Field-level priority for overlapping fields
    field_priorities:
      molecule_id:
        - chembl.activity     # Activity FK is authoritative
      publication_id:
        - chembl.activity     # Activity document reference is primary

    # -------------------------------------------------------------------------
    # Column Ordering by Semantic Categories
    # -------------------------------------------------------------------------
    column_groups:
      # === System / ETL metadata (MUST be first) ===
      - name: system
        fields:
          - entity_id
          - content_hash
          - _run_id
          - _run_type
          - _source_batch_id
          - _source
          - _ingestion_ts
          - _index
          - _lookup_method
          - _original_id
        pattern: "^_composite_|^_source_providers|^_enrichment_|^_lineage_"
        provider_order: [chembl]

      # === Primary identifiers ===
      - name: identifiers
        fields:
          - activity_id
          - molecule_id
          - assay_id
          - target_id
          - publication_id
        provider_order: [chembl]

      # === Standardized activity values ===
      - name: activity_values
        fields:
          - standard_type
          - standard_relation
          - standard_value
          - standard_units
          - standard_flag
          - pchembl_value
        provider_order: [chembl]

      # === Original (non-standardized) values ===
      - name: original_values
        fields:
          - type
          - relation
          - value
          - units
          - text_value
          - standard_text_value
          - upper_value
          - standard_upper_value
        provider_order: [chembl]

      # === Ligand efficiency metrics ===
      - name: ligand_efficiency
        fields:
          - ligand_efficiency_bei
          - ligand_efficiency_le
          - ligand_efficiency_lle
          - ligand_efficiency_sei
        provider_order: [chembl]

      # === Compound record metadata (from dependency) ===
      - name: compound_record
        fields:
          - record_id
          - compound_key
          - compound_name
          - src_compound_id
        provider_order: [chembl]

      # === Molecule context (denormalized from activity) ===
      - name: molecule_context
        fields:
          - canonical_smiles
          - molecule_pref_name
          - parent_molecule_id
        provider_order: [chembl]

      # === Target context (denormalized from activity) ===
      - name: target_context
        fields:
          - target_pref_name
          - target_organism
          - taxonomy_id
        provider_order: [chembl]

      # === Assay context (denormalized from activity) ===
      - name: assay_context
        fields:
          - assay_type
          - assay_description
          - assay_variant_accession
          - assay_variant_mutation
          - bao_format
          - bao_label
          - bao_endpoint
        provider_order: [chembl]

      # === Document context ===
      - name: document_context
        fields:
          - document_journal
          - document_year
        provider_order: [chembl]

      # === Ontologies ===
      - name: ontology
        fields:
          - uo_units
          - qudt_units
        provider_order: [chembl]

      # === Quality and curation ===
      - name: quality
        fields:
          - data_validity_comment
          - data_validity_description
          - activity_comment
          - potential_duplicate
          - manual_curation_flag
        provider_order: [chembl]

      # === Action types ===
      - name: action
        fields:
          - action_type_action_type
          - action_type_description
          - action_type_parent_type
          - activity_properties
        provider_order: [chembl]

      # === Source metadata ===
      - name: source
        fields:
          - src_id
          - original_activity_id
          - toid
        provider_order: [chembl]

    # Note: output paths auto-computed per ADR-029 convention-based resolution
    # silver: data/output/silver/composite/activity (auto)
    # gold: data/output/gold/composite/activity (auto)

  # ---------------------------------------------------------------------------
  # Data Quality Configuration
  # ---------------------------------------------------------------------------
  # Thresholds, required_fields, and field_validations externalized to:
  #   configs/quality/entities/composite/activity.yaml
  # Only pipeline-specific enricher_overrides remain inline.
  dq_overrides:
    # External baseline DQ config (ADR-027)
    dq_config_file: ../quality/entities/composite/activity.yaml
    # Per-dependency threshold overrides (pipeline-specific)
    enricher_overrides:
      # compound_record may not exist for all molecules
      chembl_compound_record:
        soft_fail_threshold: 0.30  # 30% missing is acceptable
        hard_fail_threshold: 0.70  # Only fail if >70% errors

  # ---------------------------------------------------------------------------
  # Execution Options
  # ---------------------------------------------------------------------------
  execution:
    # Maximum concurrent dependencies/enrichers
    max_concurrency: 2

    # Enable checkpointing for resume capability
    checkpoint_enabled: true

    # Retry configuration for recoverable errors
    retry:
      max_attempts: 3
      backoff_multiplier: 2.0

  # ---------------------------------------------------------------------------
  # Lineage Configuration
  # ---------------------------------------------------------------------------
  lineage:
    # Track which source provided each field value
    track_field_sources: true

    # Include timestamps for each step
    track_timestamps: true

    # Include per-record status
    track_status: true

    # Provider-specific lookup metadata
    provider_lookup_fields:
      chembl:
        _lookup_method: chembl_lookup_method
        _original_id: chembl_original_id

    # Field-level source tracking for overlapping fields
    track_source_for_fields:
      - molecule_id
      - publication_id
      - src_id

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Gold filters resolve from:
#   1. configs/base/pipeline.yaml (`filter_defaults`)
#   2. local `gold_filters` in this composite config (if present)
# No separate composite filter file is used here.

================================================================================
File: assay.yaml
Path: composites\assay.yaml
================================================================================
# configs/composites/assay.yaml
# =============================================================================
# Composite Assay Pipeline Configuration
# =============================================================================
#
# Combines ChEMBL assay data with cell line and tissue metadata:
# - Seed: ChEMBL assays
# - Enrichers: ChEMBL cell_line (cell context), ChEMBL tissue (tissue context)
#
# Architecture Decision: Using ENRICHERS (not dependencies) because:
# - Cell Line and Tissue are reference tables already populated in Silver
# - No API calls needed - just lookup from existing Silver tables
# - Enrichers execute in parallel (unlike sequential dependencies)
#
# Join Strategy:
# - cell_chembl_id and tissue_chembl_id are nullable foreign keys
# - ~70% of assays lack cell_line or tissue data
# - Merge uses left_outer to preserve all assays
#
# Version: 1.0.0
# Reference: ADR-026 Composite Pipeline Pattern
# Last Updated: 2026-02-04
#
# =============================================================================

composite:
  name: composite_assay
  version: "1.0.0"

  # ---------------------------------------------------------------------------
  # Seed Pipeline Configuration
  # ---------------------------------------------------------------------------
  seed:
    pipeline: chembl_assay
    output_keys:
      - assay_id            # Primary key
      - cell_id             # FK for cell_line enrichment (nullable)
      - tissue_id           # FK for tissue enrichment (nullable)
      - target_id           # FK to target (for context)
      - publication_id      # FK to publication (for context)
      - assay_type          # Classification
      - description         # For logging/debugging
    silver_table: silver/chembl/assay

  # ---------------------------------------------------------------------------
  # Dependencies (none - enrichers read from pre-populated Silver)
  # ---------------------------------------------------------------------------
  dependencies: []

  # ---------------------------------------------------------------------------
  # Enricher Pipelines (parallel execution)
  # ---------------------------------------------------------------------------
  enrichers:
    # ChEMBL Cell Line: cell context metadata
    # Provides: cell_name, cell_description, cell_source_organism, etc.
    # Cardinality: one_to_one (each assay FK points to at most one cell line)
    - pipeline: chembl_cell_line
      join_keys:
        - cell_id              # Direct FK match
      required: false          # Many assays lack cell line (~70%)
      filter_condition: "cell_id IS NOT NULL"
      timeout_seconds: 300
      silver_table: silver/chembl/cell_line

    # ChEMBL Tissue: tissue context metadata
    # Provides: pref_name (tissue_name), uberon_id, bto_id, efo_id, etc.
    # Cardinality: one_to_one (each assay FK points to at most one tissue)
    - pipeline: chembl_tissue
      join_keys:
        - tissue_id            # Direct FK match
      required: false          # Many assays lack tissue (~70%)
      filter_condition: "tissue_id IS NOT NULL"
      timeout_seconds: 300
      silver_table: silver/chembl/tissue

  # ---------------------------------------------------------------------------
  # Merge Configuration
  # ---------------------------------------------------------------------------
  merge:
    strategy: left_outer          # Preserve all assays
    conflict_resolution: seed_priority
    preserve_all_sources: false   # Coalesce to unified fields

    # Output paths for merged data
    output:
      silver: data/output/silver/composite/assay
      gold: data/output/gold/composite/assay
    sort_by:
      silver:
        - entity_id
        - assay_id
      gold:
        - entity_id
        - assay_id

    # Field-level priority overrides
    field_priorities:
      # FKs from seed are authoritative (prevent enricher overwrite)
      cell_id:
        - chembl.assay
      tissue_id:
        - chembl.assay

    # Field renaming for conflicts
    field_mappings:
      # cell_line.efo_id conflicts with tissue.efo_id
      "chembl.cell_line.efo_id": "cell_efo_id"
      "chembl.tissue.efo_id": "tissue_efo_id"
      # Tissue field renames for namespace clarity
      "chembl.tissue.pref_name": "tissue_pref_name"
      "chembl.tissue.uberon_id": "tissue_uberon_id"
      "chembl.tissue.bto_id": "tissue_bto_id"
      "chembl.tissue.caloha_id": "tissue_caloha_id"

    # Column ordering by semantic categories
    column_groups:
      # === System / ETL metadata (MUST be first) ===
      - name: system
        fields:
          - entity_id
          - content_hash
          - _run_id
          - _run_type
          - _source_batch_id
          - _source
          - _ingestion_ts
          - _index
          - _lookup_method
          - _original_id
        pattern: "^_composite_|^_source_providers|^_enrichment_|^_lineage_|^_dq_"
        provider_order: [chembl]

      # === Business identifiers ===
      - name: identifiers
        fields:
          - assay_id
          - cell_id
          - tissue_id
          - target_id
          - publication_id
          - src_id
          - src_assay_id
          - aidx
        provider_order: [chembl]

      # === Assay classification ===
      - name: classification
        fields:
          - assay_type
          - assay_category
          - assay_test_type
          - assay_group
          - assay_pref_name
          - relationship_type
          - relationship_description
          - confidence_score
          - confidence_description
        provider_order: [chembl]

      # === Biological context (from seed) ===
      - name: biological_context
        fields:
          - assay_organism
          - assay_taxonomy_id
          - assay_strain
          - assay_tissue
          - assay_cell_type
          - assay_subcellular_fraction
        provider_order: [chembl]

      # === Assay description ===
      - name: description
        fields:
          - description
          - score
        provider_order: [chembl]

      # === BAO ontology ===
      - name: ontology
        fields:
          - bao_format
          - bao_label
        provider_order: [chembl]

      # === Cell line metadata (from enricher) ===
      - name: cell_line
        fields:
          - cell_name
          - cell_description
          - cell_type
          - cell_source_tissue
          - cell_source_organism
          - cell_source_taxonomy_id
          - cellosaurus_id
          - clo_id
          - cl_lincs_id
          - cell_efo_id
        provider_order: [chembl]

      # === Tissue metadata (from enricher) ===
      - name: tissue
        fields:
          - tissue_pref_name
          - tissue_uberon_id
          - tissue_bto_id
          - tissue_caloha_id
          - tissue_efo_id
        provider_order: [chembl]

      # === Variant data ===
      - name: variant
        fields:
          - variant_accession
          - variant_isoform
          - variant_mutation
          - variant_organism
          - variant_sequence
          - variant_taxonomy_id
          - variant_sequence_json
        provider_order: [chembl]

      # === Complex JSON fields ===
      - name: complex
        fields:
          - assay_classifications
          - assay_parameters
        provider_order: [chembl]

    # Fields to exclude from merged output
    exclude_fields:
      # Exclude cell_line PK (already have FK in seed)
      - chembl.cell_line.cell_id
      # Exclude tissue PK (already have FK in seed)
      - chembl.tissue.tissue_id

  # ---------------------------------------------------------------------------
  # Data Quality Configuration
  # ---------------------------------------------------------------------------
  # Thresholds, required_fields, and field_validations externalized to:
  #   configs/quality/entities/composite/assay.yaml
  # Only pipeline-specific enricher_overrides remain inline.
  dq_overrides:
    # External baseline DQ config (ADR-027)
    dq_config_file: ../quality/entities/composite/assay.yaml
    # Per-enricher threshold overrides (lenient - many nulls expected)
    enricher_overrides:
      chembl_cell_line:
        soft_fail_threshold: 0.70   # ~70% assays lack cell line
        hard_fail_threshold: 0.95
      chembl_tissue:
        soft_fail_threshold: 0.70   # ~70% assays lack tissue
        hard_fail_threshold: 0.95

  # ---------------------------------------------------------------------------
  # Execution Options
  # ---------------------------------------------------------------------------
  execution:
    max_concurrency: 2              # Both enrichers can run in parallel
    checkpoint_enabled: true        # Enable resume capability
    retry:
      max_attempts: 3
      backoff_multiplier: 2.0

  # ---------------------------------------------------------------------------
  # Lineage Configuration
  # ---------------------------------------------------------------------------
  lineage:
    track_field_sources: true       # Track which provider contributed each field
    track_timestamps: true          # Include enrichment timestamps
    track_status: true              # Track per-record enrichment status

    # Provider-specific lookup metadata
    provider_lookup_fields:
      chembl:
        _lookup_method: chembl_lookup_method
        _original_id: chembl_original_id

    # Field-level source tracking for overlapping fields
    track_source_for_fields:
      - cell_chembl_id     # FK from seed vs enricher match
      - tissue_chembl_id   # FK from seed vs enricher match

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Gold filters and filter rules loaded from hierarchical config files.
# No inline gold_filters needed — filter entity config is authoritative.

================================================================================
File: publication.yaml
Path: composites\field_groups\publication.yaml
================================================================================
# Field Group Configuration for Composite Publication Pipeline
# See ADR-026 for rationale.
#
# Maps base field names to semantic groups and provider-qualified columns.
# Field naming convention: {provider}.publication.{field}
#
# Providers: chembl (seed), crossref, openalex, pubmed, semanticscholar (enrichers)

version: "1.0"
entity: publication
provider_order:
  - chembl
  - crossref
  - openalex
  - pubmed
  - semanticscholar

groups:
  # ===== ID_AND_STATUS =====
  - id: id_and_status
    display_name: "ID & Status"
    include_in_gold: true
    fields:
      - base_name: alternative_id
        columns:
          - crossref.publication.alternative_id

      - base_name: chembl_release
        columns:
          - chembl.publication.chembl_release

      - base_name: corpus_id
        columns:
          - semanticscholar.publication.corpus_id

      - base_name: dblp_id
        columns:
          - semanticscholar.publication.dblp_id

      - base_name: publication_id
        columns:
          - chembl.publication.publication_id

      - base_name: document_chembl_id
        columns:
          - chembl.publication.document_chembl_id

      - base_name: publication_doi
        columns:
          - chembl.publication.publication_doi
          - crossref.publication.publication_doi
          - openalex.publication.publication_doi
          - pubmed.publication.publication_doi
          - semanticscholar.publication.publication_doi

      - base_name: doi
        columns:
          - chembl.publication.doi
          - crossref.publication.doi
          - openalex.publication.doi
          - pubmed.publication.doi
          - semanticscholar.publication.doi

      - base_name: entity_id
        columns:
          - chembl.publication.entity_id
          - crossref.publication.entity_id
          - openalex.publication.entity_id
          - pubmed.publication.entity_id
          - semanticscholar.publication.entity_id

      - base_name: is_oa
        columns:
          - openalex.publication.is_oa
          - semanticscholar.publication.is_oa

      - base_name: is_retracted
        columns:
          - openalex.publication.is_retracted

      - base_name: mag_id
        columns:
          - openalex.publication.mag_id

      - base_name: nlm_unique_id
        columns:
          - pubmed.publication.nlm_unique_id

      - base_name: oa_status
        columns:
          - openalex.publication.oa_status
          - semanticscholar.publication.oa_status

      - base_name: open_access_url
        columns:
          - semanticscholar.publication.open_access_url

      - base_name: openalex_id
        columns:
          - openalex.publication.openalex_id

      - base_name: paper_id
        columns:
          - semanticscholar.publication.paper_id

      - base_name: pmc_id
        columns:
          - pubmed.publication.pmc_id

      - base_name: pmid
        columns:
          - chembl.publication.pmid
          - openalex.publication.pmid
          - pubmed.publication.pmid
          - semanticscholar.publication.pmid

      - base_name: publication_status
        columns:
          - pubmed.publication.publication_status

  # ===== BIBLIOGRAPHY =====
  - id: bibliography
    display_name: "Bibliography"
    include_in_gold: true
    fields:
      - base_name: abstract
        columns:
          - chembl.publication.abstract
          - openalex.publication.abstract
          - pubmed.publication.abstract
          - semanticscholar.publication.abstract

      - base_name: abstract_structured
        columns:
          - pubmed.publication.abstract_structured

      - base_name: page_first
        columns:
          - chembl.publication.page_first
          - crossref.publication.page_first
          - openalex.publication.page_first
          - pubmed.publication.page_first
          - semanticscholar.publication.page_first

      - base_name: issn
        columns:
          - crossref.publication.issn
          - openalex.publication.issn
          - pubmed.publication.issn

      - base_name: issn_list
        columns:
          - crossref.publication.issn_list

      - base_name: issn_electronic
        columns:
          - crossref.publication.issn_electronic

      - base_name: issn_print
        columns:
          - crossref.publication.issn_print

      - base_name: issue
        columns:
          - chembl.publication.issue
          - crossref.publication.issue
          - openalex.publication.issue
          - pubmed.publication.issue
          - semanticscholar.publication.issue

      - base_name: journal
        columns:
          - chembl.publication.journal
          - crossref.publication.journal
          - openalex.publication.journal
          - pubmed.publication.journal
          - semanticscholar.publication.journal

      - base_name: journal_abbrev
        columns:
          - pubmed.publication.journal_abbrev

      - base_name: journal_full_title
        columns:
          - chembl.publication.journal_full_title

      - base_name: journal_iso_abbrev
        columns:
          - pubmed.publication.journal_iso_abbrev

      - base_name: journal_issn_type
        columns:
          - pubmed.publication.journal_issn_type

      - base_name: journal_name
        columns:
          - pubmed.publication.journal_name
          - openalex.publication.journal_name
          - semanticscholar.publication.journal_name

      - base_name: journal_title
        columns:
          - pubmed.publication.journal_title

      - base_name: page_last
        columns:
          - chembl.publication.page_last
          - crossref.publication.page_last
          - openalex.publication.page_last
          - pubmed.publication.page_last
          - semanticscholar.publication.page_last

      - base_name: page_range
        columns:
          - pubmed.publication.page_range

      - base_name: pages
        columns:
          - crossref.publication.pages
          - pubmed.publication.pages
          - semanticscholar.publication.pages

      - base_name: publisher
        columns:
          - crossref.publication.publisher
          - openalex.publication.publisher

      - base_name: journal_name_short
        columns:
          - crossref.publication.journal_name_short

      - base_name: title
        columns:
          - chembl.publication.title
          - crossref.publication.title
          - openalex.publication.title
          - pubmed.publication.title
          - semanticscholar.publication.title

      - base_name: venue
        columns:
          - semanticscholar.publication.venue

      - base_name: volume
        columns:
          - chembl.publication.volume
          - crossref.publication.volume
          - openalex.publication.volume
          - pubmed.publication.volume
          - semanticscholar.publication.volume

  # ===== AUTHOR_AND_AFFILIATIONS =====
  - id: author_and_affiliations
    display_name: "Author & Affiliations"
    include_in_gold: true
    fields:
      - base_name: affiliation_list
        columns:
          - openalex.publication.affiliation_list
          - pubmed.publication.affiliation_list
          - semanticscholar.publication.affiliation_list

      - base_name: author_count
        columns:
          - pubmed.publication.author_count

      - base_name: author_h_indices
        columns:
          - semanticscholar.publication.author_h_indices

      - base_name: author_keys
        columns:
          - chembl.publication.author_keys
          - crossref.publication.author_keys
          - openalex.publication.author_keys
          - pubmed.publication.author_keys
          - semanticscholar.publication.author_keys

      - base_name: author_openalex_ids
        columns:
          - openalex.publication.author_openalex_ids

      - base_name: author_orcids
        columns:
          - crossref.publication.author_orcids
          - openalex.publication.author_orcids
          - semanticscholar.publication.author_orcids

      - base_name: author_s2_ids
        columns:
          - semanticscholar.publication.author_s2_ids

      - base_name: authors
        columns:
          - chembl.publication.authors
          - crossref.publication.authors
          - openalex.publication.authors
          - pubmed.publication.authors
          - semanticscholar.publication.authors

      - base_name: authors_with_affiliations
        columns:
          - pubmed.publication.authors_with_affiliations

      - base_name: affiliation_structured
        columns:
          - pubmed.publication.affiliation_structured

      - base_name: institution_ids
        columns:
          - openalex.publication.institution_ids

      - base_name: ror_ids
        columns:
          - openalex.publication.ror_ids

  # ===== TERMS_AND_KEYWORDS_AND_TOPICS =====
  - id: terms_and_keywords_and_topics
    display_name: "Terms & Keywords & Topics"
    include_in_gold: true
    fields:
      - base_name: fields_of_study
        columns:
          - semanticscholar.publication.fields_of_study

      - base_name: chemical_count
        columns:
          - pubmed.publication.chemical_count

      - base_name: chemicals
        columns:
          - pubmed.publication.chemicals

      - base_name: citation_subset
        columns:
          - pubmed.publication.citation_subset

      - base_name: databanks
        columns:
          - pubmed.publication.databanks

      - base_name: gene_symbols
        columns:
          - pubmed.publication.gene_symbols

      - base_name: keyword_count
        columns:
          - pubmed.publication.keyword_count

      - base_name: keywords
        columns:
          - openalex.publication.keywords
          - pubmed.publication.keywords
          - semanticscholar.publication.keywords

      - base_name: mesh
        columns:
          - openalex.publication.mesh

      - base_name: mesh_heading_count
        columns:
          - pubmed.publication.mesh_heading_count

      - base_name: mesh_terms
        columns:
          - openalex.publication.mesh_terms
          - pubmed.publication.mesh_terms

      - base_name: primary_topic
        columns:
          - openalex.publication.primary_topic

      - base_name: tldr
        columns:
          - semanticscholar.publication.tldr

      - base_name: topics
        columns:
          - openalex.publication.topics

      - base_name: subject_fields
        columns:
          - semanticscholar.publication.subject_fields

      - base_name: subject_keywords
        columns:
          - crossref.publication.subject_keywords

      - base_name: subject_mesh
        columns:
          - openalex.publication.subject_mesh
          - pubmed.publication.subject_mesh

      - base_name: subject_topics
        columns:
          - openalex.publication.subject_topics

  # ===== CITATIONS_AND_REFERENCE =====
  - id: citations_and_reference
    display_name: "Citations & Reference"
    include_in_gold: true
    fields:
      - base_name: citation_contexts
        columns:
          - semanticscholar.publication.citation_contexts

      - base_name: citations_received
        columns:
          - crossref.publication.citations_received
          - openalex.publication.citations_received
          - pubmed.publication.citations_received
          - semanticscholar.publication.citations_received

      - base_name: citations_made
        columns:
          - crossref.publication.citations_made
          - openalex.publication.citations_made
          - pubmed.publication.citations_made
          - semanticscholar.publication.citations_made

      - base_name: fwci
        columns:
          - openalex.publication.fwci

      - base_name: grant_count
        columns:
          - pubmed.publication.grant_count
          - openalex.publication.grant_count

      - base_name: grants
        columns:
          - pubmed.publication.grants
          - openalex.publication.grants

      - base_name: influential_citation_count
        columns:
          - semanticscholar.publication.influential_citation_count

      - base_name: references
        columns:
          - crossref.publication.references

  # ===== DATE_AND_PLACES =====
  - id: date_and_places
    display_name: "Date & Places"
    include_in_gold: true
    fields:
      - base_name: institution_country_codes
        columns:
          - openalex.publication.institution_country_codes

      - base_name: country
        columns:
          - pubmed.publication.country

      - base_name: creation_date
        columns:
          - chembl.publication.creation_date

      - base_name: date_completed
        columns:
          - pubmed.publication.date_completed

      - base_name: date_revised
        columns:
          - pubmed.publication.date_revised

      - base_name: pub_date
        columns:
          - pubmed.publication.pub_date

      - base_name: pub_day
        columns:
          - pubmed.publication.pub_day

      - base_name: pub_month
        columns:
          - pubmed.publication.pub_month

      - base_name: publication_date
        columns:
          - crossref.publication.publication_date
          - openalex.publication.publication_date
          - pubmed.publication.publication_date
          - semanticscholar.publication.publication_date

      - base_name: publication_year
        columns:
          - openalex.publication.publication_year

      - base_name: published
        columns:
          - crossref.publication.published

      - base_name: published_online
        columns:
          - crossref.publication.published_online

      - base_name: published_print
        columns:
          - crossref.publication.published_print

      - base_name: year
        columns:
          - chembl.publication.year
          - crossref.publication.year
          - openalex.publication.year
          - pubmed.publication.year
          - semanticscholar.publication.year

  # ===== PUBLICATION_TYPES =====
  - id: publication_types
    display_name: "Publication Types"
    include_in_gold: true
    fields:
      - base_name: publication_type
        columns:
          - chembl.publication.publication_type
          - crossref.publication.publication_type
          - openalex.publication.publication_type
          - pubmed.publication.publication_type
          - semanticscholar.publication.publication_type

      - base_name: publication_type_list
        columns:
          - pubmed.publication.publication_type_list

      - base_name: publication_types
        columns:
          - pubmed.publication.publication_types
          - semanticscholar.publication.publication_types

      - base_name: type
        columns:
          - crossref.publication.type
          - openalex.publication.type

  # ===== SYSTEM_METADATA (excluded from Gold) =====
  - id: system_metadata
    display_name: "System Metadata"
    include_in_gold: false
    fields:
      - base_name: content_hash
        columns:
          - chembl.publication.content_hash
          - crossref.publication.content_hash
          - openalex.publication.content_hash
          - pubmed.publication.content_hash
          - semanticscholar.publication.content_hash

  # ===== TRASH (excluded from Gold) =====
  - id: trash
    display_name: "Trash (Excluded)"
    include_in_gold: false
    fields:
      - base_name: content_domain_crossmark_restriction
        columns:
          - crossref.publication.content_domain_crossmark_restriction

      - base_name: content_domain_domains
        columns:
          - crossref.publication.content_domain_domains

      - base_name: language
        columns:
          - crossref.publication.language
          - openalex.publication.language
          - pubmed.publication.language

      - base_name: license_url
        columns:
          - crossref.publication.license_url

      - base_name: medline_pgn
        columns:
          - pubmed.publication.medline_pgn

      - base_name: src_id
        columns:
          - chembl.publication.src_id

================================================================================
File: molecule.yaml
Path: composites\molecule.yaml
================================================================================
# configs/composites/molecule.yaml
# =============================================================================
# Composite Molecule Pipeline Configuration
# =============================================================================
#
# Combines molecule/compound data from multiple sources:
# - Seed: ChEMBL molecules (pharmaceutical compounds with clinical data)
# - Enrichers: PubChem compounds (chemical properties and synonyms)
#
# Join Strategy:
# - Primary: InChIKey (IUPAC standard, 27 characters)
# - Fallback: Canonical SMILES (less reliable due to canonization differences)
#
# Note: ChEMBL uses "molecule" terminology, PubChem uses "compound".
# Unified entity name: molecule
#
# Version: 1.0.0
# Reference: ADR-026 Composite Pipeline Pattern
# Last Updated: 2026-02-03
#
# =============================================================================

# -----------------------------------------------------------------------------
# Composite Pipeline Configuration
# -----------------------------------------------------------------------------
composite:
  name: composite_molecule
  version: "1.0.0"

  # ---------------------------------------------------------------------------
  # Seed Pipeline Configuration
  # ---------------------------------------------------------------------------
  # The seed pipeline extracts primary entities from ChEMBL.
  # Its output provides join keys (inchi_key, canonical_smiles) for enrichment.
  seed:
    pipeline: chembl_molecule
    output_keys:
      - molecule_id         # Primary key
      - inchi_key           # Join key 1 (IUPAC standard, preferred)
      - canonical_smiles    # Join key 2 (fallback)
      - pref_name           # For logging/debugging
    # Note: chembl_molecule uses flat_structure, so table is in path directly
    silver_table: silver/chembl/molecule

  # ---------------------------------------------------------------------------
  # Dependency Pipelines
  # ---------------------------------------------------------------------------
  # Dependencies run after seed but before enrichers to populate Silver tables.
  # No dependencies required for molecule pipeline.
  dependencies: []

  # ---------------------------------------------------------------------------
  # Enricher Pipelines
  # ---------------------------------------------------------------------------
  # Each enricher fetches supplemental data from an external source.
  enrichers:
    # PubChem: Chemical properties and synonyms
    # OPTIONAL: Failure logged, composite continues (graceful degradation)
    - pipeline: pubchem_compound
      join_keys:
        - inchi_key          # Primary join key (IUPAC standard) - uses seed field name
        - canonical_smiles   # Fallback key (less reliable)
      required: false        # Graceful degradation - seed data preserved on failure
      filter_condition: "inchi_key IS NOT NULL"  # Only join records with structure
      timeout_seconds: 3600
      silver_table: silver/pubchem/compound

  # ---------------------------------------------------------------------------
  # Field Aliases (RF-NORM-01: Canonical Field Alias Registry)
  # ---------------------------------------------------------------------------
  # Maps provider-specific field names to canonical names used in Gold schemas.
  # Source of truth: bioetl.domain.registry.field_aliases.MOLECULE_FIELD_ALIASES
  #
  # During merge, the ColumnRenamer normalizes provider fields to canonical
  # names so that columns from different providers can be grouped, compared,
  # and priority-resolved correctly.
  #
  # Example: PubChem's "h_bond_acceptor_count" → canonical "hba_count"
  #   pubchem.compound.h_bond_acceptor_count → pubchem.compound.hba_count
  #   chembl.molecule.hba_count              → chembl.molecule.hba_count (unchanged)
  field_aliases:
    # Canonical Name         | ChEMBL Name          | PubChem Name
    # -----------------------|----------------------|------------------------
    # hba_count              | hba_count            | h_bond_acceptor_count
    # hbd_count              | hbd_count            | h_bond_donor_count
    # polar_surface_area     | polar_surface_area   | tpsa
    # logp                   | logp                 | xlogp
    # standard_inchi         | standard_inchi       | inchi
    hba_count:
      chembl: hba_count
      pubchem: h_bond_acceptor_count
    hbd_count:
      chembl: hbd_count
      pubchem: h_bond_donor_count
    polar_surface_area:
      chembl: polar_surface_area
      pubchem: tpsa
    logp:
      chembl: logp
      pubchem: xlogp
    standard_inchi:
      chembl: standard_inchi
      pubchem: inchi

  # ---------------------------------------------------------------------------
  # Merge Configuration
  # ---------------------------------------------------------------------------
  # Defines how enriched data is combined into the final output.
  merge:
    # Join strategy: left_outer preserves all seed records
    strategy: left_outer

    # Conflict resolution: seed values take priority (used when preserve_all_sources=false)
    conflict_resolution: seed_priority

    # Preserve all provider-qualified columns for common fields
    # When true, keeps columns like chembl.molecule.canonical_smiles, pubchem.compound.canonical_smiles
    preserve_all_sources: true

    # Output paths for merged data
    output:
      silver: data/output/silver/composite/molecule
      gold: data/output/gold/composite/molecule
    sort_by:
      silver:
        - entity_id
        - molecule_id
      gold:
        - entity_id
        - molecule_id

    # Field-level priority overrides
    # Maps field name to ordered list of source preferences
    field_priorities:
      # === Structural Identifiers (ChEMBL authoritative) ===
      # ChEMBL has curated structures from medicinal chemistry literature
      canonical_smiles:
        - chembl           # ChEMBL structures are manually curated
        - pubchem
      inchi_key:
        - chembl           # ChEMBL InChIKey from standardized structures
        - pubchem
      inchi:
        - chembl
        - pubchem
      isomeric_smiles:
        - pubchem          # PubChem provides isomeric SMILES
        - chembl

      # === Physicochemical Properties (PubChem more complete) ===
      # PubChem has computed descriptors for more compounds
      molecular_weight:
        - pubchem          # PubChem has MW for all compounds
        - chembl
      molecular_formula:
        - pubchem
        - chembl
      logp:
        - pubchem          # PubChem uses XLogP3
        - chembl           # ChEMBL uses ALogP
      logp_method:
        - pubchem
        - chembl
      polar_surface_area:
        - pubchem
        - chembl
      hba_count:
        - pubchem
        - chembl
      hbd_count:
        - pubchem
        - chembl
      rotatable_bond_count:
        - pubchem
        - chembl
      heavy_atom_count:
        - pubchem
        - chembl
      aromatic_ring_count:
        - pubchem
        - chembl

      # === Names and Synonyms (merge from both) ===
      pref_name:
        - chembl           # ChEMBL has curated preferred names
        - pubchem
      iupac_name:
        - pubchem          # PubChem has computed IUPAC names
        - chembl
      synonyms:
        - chembl           # Merge arrays from both
        - pubchem

      # === Clinical Data (ChEMBL only) ===
      # PubChem doesn't have clinical development data
      max_phase:
        - chembl           # Clinical phase (0-4)
      first_approval:
        - chembl           # FDA/EMA approval year
      therapeutic_flag:
        - chembl
      withdrawn_flag:
        - chembl
      black_box_warning:
        - chembl

      # === Quality Metrics (ChEMBL) ===
      qed_weighted:
        - chembl           # QED (Quantitative Estimate of Drug-likeness)

    # -------------------------------------------------------------------------
    # Column Ordering by Canonical Categories
    # -------------------------------------------------------------------------
    column_groups:
      # === System / ETL metadata (MUST be first) ===
      - name: system
        fields:
          - entity_id
          - content_hash
          - _run_id
          - _run_type
          - _source_batch_id
          - _source
          - _ingestion_ts
          - _index
        pattern: "^_composite_|^_source_providers|^_enrichment_|^_lineage_"
        provider_order: [chembl, pubchem]

      # === Business identifiers ===
      - name: identifiers
        fields:
          - molecule_id          # Canonical molecule id
          - inchi_key            # Standard InChIKey (both ChEMBL and PubChem)
          - inchi
          - standard_inchi
        provider_order: [chembl, pubchem]

      # === Structure representations ===
      - name: structure
        fields:
          - canonical_smiles
          - isomeric_smiles
          - helm_notation
          - structure_type
        provider_order: [chembl, pubchem]

      # === Physicochemical properties ===
      - name: properties
        fields:
          - molecular_weight
          - molecular_formula
          - logp
          - logp_method
          - polar_surface_area
          - hba_count
          - hbd_count
          - rotatable_bond_count
          - heavy_atom_count
          - aromatic_ring_count
          - qed_weighted
          - property_ro5_violations
          - property_ro3_pass
        provider_order: [chembl, pubchem]

      # === Names and synonyms ===
      - name: names
        fields:
          - pref_name
          - iupac_name
          - molecule_synonyms
        provider_order: [chembl, pubchem]

      # === Clinical and regulatory (ChEMBL-only) ===
      - name: clinical
        fields:
          - max_phase
          - first_approval
          - therapeutic_flag
          - black_box_warning
          - withdrawn_flag
          - oral
          - parenteral
          - topical
          - first_in_class
          - prodrug
          - natural_product
          - availability_type
        provider_order: [chembl]

      # === Molecular hierarchy (ChEMBL-only) ===
      - name: hierarchy
        fields:
          - hierarchy_parent_chembl_id
          - hierarchy_active_chembl_id
          - hierarchy_child_chembl_id
          - molecule_hierarchy
        provider_order: [chembl]

      # === Classification ===
      - name: classification
        fields:
          - molecule_type
          - atc_classifications
          - chirality
          - inorganic_flag
          - polymer_flag
          - dosed_ingredient
        provider_order: [chembl]

      # === Cross-references ===
      - name: xrefs
        fields:
          - cross_references
        provider_order: [chembl, pubchem]

      # === USAN nomenclature (ChEMBL-only) ===
      - name: usan
        fields:
          - usan_year
          - usan_stem
          - usan_substem
          - usan_stem_definition
        provider_order: [chembl]

    # Note: output paths auto-computed per ADR-029 convention-based resolution
    # silver: data/output/silver/composite/molecule (auto)
    # gold: data/output/gold/composite/molecule (auto)

  # ---------------------------------------------------------------------------
  # Data Quality Configuration
  # ---------------------------------------------------------------------------
  # Thresholds, required_fields, and field_validations externalized to:
  #   configs/quality/entities/composite/molecule.yaml
  # Only pipeline-specific enricher_overrides remain inline.
  dq_overrides:
    # External baseline DQ config (ADR-027)
    dq_config_file: ../quality/entities/composite/molecule.yaml
    # Per-enricher threshold overrides
    enricher_overrides:
      # PubChem may have many records without InChIKey match
      pubchem_compound:
        soft_fail_threshold: 0.20
        hard_fail_threshold: 0.50

  # ---------------------------------------------------------------------------
  # Execution Options
  # ---------------------------------------------------------------------------
  execution:
    # Maximum concurrent enrichers (only 1 enricher in this pipeline)
    max_concurrency: 1

    # Enable checkpointing for resume capability
    checkpoint_enabled: true

    # Retry configuration for recoverable errors
    retry:
      max_attempts: 3
      backoff_multiplier: 2.0

  # ---------------------------------------------------------------------------
  # Lineage Configuration
  # ---------------------------------------------------------------------------
  lineage:
    # Track which source provided each field value
    track_field_sources: true

    # Include timestamps for each enrichment
    track_timestamps: true

    # Include per-record enrichment status
    track_status: true

    # Provider-specific lookup metadata
    provider_lookup_fields:
      chembl:
        _lookup_method: chembl_lookup_method
        _original_id: chembl_original_id
      pubchem:
        _lookup_method: pubchem_lookup_method
        _original_id: pubchem_original_id

    # Field-level source tracking for overlapping fields
    track_source_for_fields:
      - canonical_smiles
      - inchi_key
      - molecular_weight
      - logp
      - polar_surface_area
      - hba_count
      - hbd_count

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Gold filters and filter rules loaded from hierarchical config files.
# No inline gold_filters needed — filter entity config is authoritative.

# -----------------------------------------------------------------------------
# Maintenance Configuration
# -----------------------------------------------------------------------------

================================================================================
File: publication.yaml
Path: composites\publication.yaml
================================================================================
# configs/composites/publication.yaml
# =============================================================================
# Composite Publication Pipeline Configuration
# =============================================================================
#
# Combines publication data from multiple sources:
# - Seed: ChEMBL publications
# - Enrichers: CrossRef (citations), OpenAlex (topics), PubMed (MeSH),
#              SemanticScholar (embeddings)
#
# NOTE: chembl_publication_term was removed because ChEMBL API no longer
# provides subject_mesh/subject_keywords fields in /document endpoint, and the
# /document_term endpoint has been deprecated (returns 404).
#
# Field exclusions (2026-01-27):
# - CrossRef: pmid, pmc_id, publication_type (uses raw 'type' mapped to publication_type)
# - OpenAlex: pmc_id, publication_type (uses raw 'type' mapped to publication_type)
# - PubMed: vernacular_title, epub_date, received_date, revised_date, accepted_date
# - SemanticScholar: pmc_id, arxiv_id
#
# Full field coverage update (2026-01-28):
# This configuration now includes ALL 181 extractable fields (100% coverage).
# Previously included 142 of 181 fields (78.5%).
# See schema.column_groups and field_aliases below for the current field mapping registry.
#
# Version: 1.1.0
# Reference: ADR-026 Composite Pipeline Pattern
# Last Updated: 2026-01-28
#
# =============================================================================

# -----------------------------------------------------------------------------
# Composite Pipeline Configuration
# -----------------------------------------------------------------------------
composite:
    name: composite_publication
    version: "1.1.0"

    # ---------------------------------------------------------------------------
    # Seed Pipeline Configuration
    # ---------------------------------------------------------------------------
    # The seed pipeline extracts primary entities from ChEMBL.
    # Its output provides join keys (publication_id, doi, pmid) for enrichment.
    seed:
        pipeline: chembl_publication
        output_keys:
            - publication_id         # ChEMBL document ID (primary key)
            - doi                    # Digital Object Identifier
            - pmid                   # PubMed ID
            - pmc_id                 # PubMed Central ID
            - title                  # Publication title (for fallback joins)
        # Note: chembl_publication uses flat_structure, so table is in path directly
        silver_table: silver/chembl/publication

    # ---------------------------------------------------------------------------
    # Dependency Pipelines
    # ---------------------------------------------------------------------------
    # Dependencies run after seed but before enrichers to populate Silver tables.
    # Unlike enrichers which can read from existing Silver tables, dependencies
    # call APIs to fetch data and write to Silver.
    #
    # Use dependencies for:
    # - Derived entities (e.g., publication_term extracted from publication data)
    # - Pipelines with full_scan_only strategy that don't work with enricher filtering
    # - Data that must be pre-populated before enrichment phase
    dependencies: []  # No dependencies currently

    # ---------------------------------------------------------------------------
    # Enricher Pipelines
    # ---------------------------------------------------------------------------
    # Each enricher fetches supplemental data from an external source.
    # Enrichers can run in parallel up to max_concurrency limit.
    enrichers:
        # CrossRef: Citation and reference data
        # REQUIRED: Primary source for citation data (needs doi)
        -   pipeline: crossref_publication
            join_keys:
                - doi               # Primary join key
                - title
            required: false    # Optional - seed may not have DOIs
            filter_condition: "doi IS NOT NULL"
            timeout_seconds: 3600
            silver_table: silver/crossref/publication

        # OpenAlex: Academic topics and institutions
        # OPTIONAL: Failure logged, composite continues
        -   pipeline: openalex_publication
            join_keys:
                - doi               # Primary key
                - title             # Fallback key if doi not found
            required: false    # Optional - needs doi or pmid
            filter_condition: "doi IS NOT NULL OR pmid IS NOT NULL"
            timeout_seconds: 3600
            silver_table: silver/openalex/publication

        # PubMed: MeSH terms and medical metadata
        # OPTIONAL: Only processes records with pmid
        -   pipeline: pubmed_publication
            join_keys:
                - pmid                 # PubMed-specific identifier
                - doi
            required: false    # Optional - only for records with pmid
            filter_condition: "pmid IS NOT NULL"
            timeout_seconds: 3600
            silver_table: silver/pubmed/publication

        # Semantic Scholar: AI/ML embeddings and TLDR (mapped to abstract)
        # OPTIONAL: Higher rate limits, ok to skip
        -   pipeline: semanticscholar_publication
            join_keys:
                - doi
                - title
            required: false    # Optional - high rate limits, ok to skip
            filter_condition: "doi IS NOT NULL OR title IS NOT NULL"
            timeout_seconds: 7200
            #fallback_strategy: skip  # Skip on failure (high rate limits)
            silver_table: silver/semanticscholar/publication

    # ---------------------------------------------------------------------------
    # Merge Configuration
    # ---------------------------------------------------------------------------
    # Defines how enriched data is combined into the final output.
    merge:
        # Join strategy: left_outer preserves all seed records
        strategy: left_outer

        # Conflict resolution: seed values take priority (used when preserve_all_sources=false)
        conflict_resolution: seed_priority

        # NEW: Preserve all provider-qualified columns for common fields
        # When true, keeps columns like chembl.publication.title, crossref.publication.title
        # instead of coalescing them into a single 'title' column
        preserve_all_sources: true

        # CV-validated enricher fields to exclude from output.
        # These fields are redundant: seed_priority means seed values always win,
        # and cross-validation already verified consistency.
        # citations_received is kept — providers may report different counts.
        exclude_fields:
            # crossref (7)
            - "crossref.publication.doi"
            - "crossref.publication.title"
            - "crossref.publication.volume"
            - "crossref.publication.issue"
            - "crossref.publication.page_first"
            - "crossref.publication.page_last"
            - "crossref.publication.publication_year"
            # openalex (8)
            - "openalex.publication.doi"
            - "openalex.publication.pmid"
            - "openalex.publication.title"
            - "openalex.publication.volume"
            - "openalex.publication.issue"
            - "openalex.publication.page_first"
            - "openalex.publication.page_last"
            - "openalex.publication.publication_year"
            # pubmed (8)
            - "pubmed.publication.doi"
            - "pubmed.publication.pmid"
            - "pubmed.publication.title"
            - "pubmed.publication.volume"
            - "pubmed.publication.issue"
            - "pubmed.publication.page_first"
            - "pubmed.publication.page_last"
            - "pubmed.publication.publication_year"
            # semanticscholar (8)
            - "semanticscholar.publication.doi"
            - "semanticscholar.publication.pmid"
            - "semanticscholar.publication.title"
            - "semanticscholar.publication.volume"
            - "semanticscholar.publication.issue"
            - "semanticscholar.publication.page_first"
            - "semanticscholar.publication.page_last"
            - "semanticscholar.publication.publication_year"
            # Additional low-value / redundant fields
            - "chembl.publication.affiliation_list"
            - "chembl.publication.author_orcids"
            - "chembl.publication.citations_made"
            - "chembl.publication.citations_received"
            - "chembl.publication.is_oa"
            - "chembl.publication.language"
            - "chembl.publication.pmc_id"
            - "chembl.publication.publication_class"
            - "chembl.publication.publication_date"
            - "chembl.publication.publication_subclass"
            - "chembl.publication.publication_type_unified"
            - "crossref.publication.abstract"
            - "crossref.publication.affiliation_list"
            - "crossref.publication.author_orcids"
            - "crossref.publication.content_domain_domains"
            - "crossref.publication.pmc_id"
            - "crossref.publication.pmid"
            - "openalex.publication.grants"
            - "openalex.publication.pmc_id"
            - "semanticscholar.publication.dblp_id"
            - "semanticscholar.publication.affiliation_list"
            - "semanticscholar.publication.author_orcids"
            - "semanticscholar.publication.citation_contexts"
            - "semanticscholar.publication.influential_citation_count"
            - "semanticscholar.publication.pmc_id"
        # Output paths for merged data
        output:
            silver: data/output/silver/composite/publication
            gold: data/output/gold/composite/publication
        sort_by:
            silver:
                - entity_id
                - publication_id
            gold:
                - entity_id
                - publication_id

        # Field-level priority overrides (when using explicit_rules)
        # Maps field name to ordered list of source preferences
        field_priorities:
            # === Core Content ===
            title:
                - chembl         # ChEMBL title is authoritative
                - crossref
                - openalex
            abstract:
                - pubmed         # PubMed has best abstracts
                - openalex
                - chembl
                - semanticscholar  # Fallback (mapped from TLDR)

            # === Citation Metrics ===
            citations_received:
                - crossref       # CrossRef is citation authority
                - openalex
                - semanticscholar
            citations_made:
                - crossref       # CrossRef has most complete reference data
                - openalex
                - pubmed
                - semanticscholar
            influential_citation_count:
                - semanticscholar  # S2-only field

            # === Classification/Topics ===
            # NOTE: subject_topics replaces deprecated concepts/topics per OpenAlex 2024 migration
            subject_topics:
                - openalex       # OpenAlex hierarchical topics
            primary_topic:
                - openalex       # OpenAlex-unique field
            subject_keywords:
                - crossref       # CrossRef subjects -> subject_keywords
                - openalex
                - pubmed
                - semanticscholar
            subject_mesh:
                - pubmed         # PubMed MeSH is authoritative
                - openalex       # OpenAlex MeSH extraction (fallback)
            subject_fields:
                - semanticscholar  # S2-unique field

            # === Author Metadata ===
            author_orcids:
                - crossref       # CrossRef has most complete ORCID data
                - openalex
                - semanticscholar
            author_details:
                - crossref       # CrossRef-unique detailed author objects
            author_s2_ids:
                - semanticscholar  # S2-unique author identifiers
            author_openalex_ids:
                - openalex         # OpenAlex-unique author identifiers
            author_h_indices:
                - semanticscholar  # S2-unique h-index data

            # === Affiliations ===
            # Note: affiliation_structured (PubMed) preferred over affiliation_list
            # PubMed affiliation_structured contains ROR/GRID identifiers
            affiliation_structured:
                - pubmed         # PubMed has structured affiliation data with ROR/GRID
            affiliation_list:
                - pubmed         # PubMed raw affiliations
                - openalex
                - semanticscholar
            institution_ids:
                - openalex       # OpenAlex institution IDs (e.g., I1234567890)
            institution_country_codes:
                - openalex       # OpenAlex institution country codes (ISO 2-letter)

            # === References/Citations Context ===
            references:
                - crossref       # CrossRef-unique cited references
            citation_contexts:
                - semanticscholar  # S2-unique citation context sentences

            # === Quality Indicators ===
            is_retracted:
                - openalex       # OpenAlex-unique retraction status (CRITICAL)
            fwci:
                - openalex       # OpenAlex-unique FWCI metric

            # === Funding ===
            grants:
                - openalex       # OpenAlex-unique grant/funding data

            # === Chemicals & Genes (PubMed-specific) ===
            chemicals:
                - pubmed         # PubMed-unique chemical substances
            gene_symbols:
                - pubmed         # PubMed-unique gene symbols
            databanks:
                - pubmed         # PubMed-unique databank accessions

            # === Alternative Identifiers ===
            pii:
                - pubmed         # PubMed Publisher Item Identifier
            mid:
                - pubmed         # PubMed Manuscript ID
            publisher_id:
                - pubmed         # PubMed publisher-specific ID
            dblp_id:
                - semanticscholar  # S2-unique DBLP identifier
            mag_id:
                - openalex       # OpenAlex MAG legacy ID

        # -------------------------------------------------------------------------
        # Column Ordering by Canonical Categories
        # -------------------------------------------------------------------------
        # Defines the order of columns in the merged output.
        # Categories and field order follow the historical ordering artifact
        # docs/04-reference/schemas/publication_field_order.csv.
        # Canonical field names and aliases live in
        # configs/entities/{provider}/publication.yaml and provider reference docs.
        #
        # The "system" group MUST be first: it captures ETL metadata columns
        # (entity_id, content_hash, _run_id, etc.) that would otherwise fall
        # into the "remaining" bucket at the end of the output.
        column_groups:
            # === System / ETL metadata (MUST be first) ===
            -   name: system
                fields:
                    - entity_id
                    - content_hash
                    - _run_id
                    - _run_type
                    - _source_batch_id
                    - _source
                    - _ingestion_ts
                    - _index
                    - _lookup_method
                    - _original_id
                pattern: "^_composite_|^_source_providers|^_enrichment_|^_lineage_"
                provider_order: [ chembl, crossref, openalex, pubmed, semanticscholar ]

            # === Provider identifiers ===
            -   name: provider_ids
                fields:
                    - alternative_id
                    - chembl_release
                    - corpus_id
                    - dblp_id
                    - document_chembl_id
                    - mag_id
                    - nlm_unique_id
                    - openalex_id
                    - paper_id
                    - pmc_id
                    - pmid
                    - publication_id
                    - publication_pmc_id
                    - publication_pmid
                    - src_id
                provider_order: [ semanticscholar, openalex, pubmed, chembl, crossref ]

            # === Journal / Venue information ===
            -   name: journal
                fields:
                    - abstract
                    - abstract_structured
                    - doi
                    - issn
                    - issn_electronic
                    - issn_list
                    - issn_print
                    - issue
                    - journal
                    - journal_iso_abbrev
                    - journal_issn_type
                    - journal_name_short
                    - publication_doi
                    - publisher
                    - title
                    - venue
                    - volume
                provider_order: [ pubmed, semanticscholar, chembl, crossref, openalex ]

            # === Pagination ===
            -   name: pagination
                fields:
                    - medline_pgn
                    - page_first
                    - page_last
                    - page_range
                provider_order: [ pubmed, chembl, crossref, openalex, semanticscholar ]

            # === Authors ===
            -   name: authors
                fields:
                    - author_count
                    - author_details
                    - author_h_indices
                    - author_openalex_ids
                    - author_orcids
                    - author_s2_ids
                    - authors
                    - authors_with_affiliations
                provider_order: [ pubmed, semanticscholar, openalex, chembl, crossref ]

            # === Affiliations ===
            -   name: affiliations
                fields:
                    - affiliation_list
                    - affiliation_structured
                    - institution_country_codes
                    - institution_ids
                    - ror_ids
                    - country
                provider_order: [ pubmed, openalex, semanticscholar, chembl, crossref ]

            # === Date ===
            -   name: date
                fields:
                    - creation_date
                    - date_completed
                    - date_revised
                    - pub_date
                    - pub_day
                    - pub_month
                    - publication_date
                    - publication_year
                    - year
                provider_order: [ chembl, crossref, openalex, pubmed, semanticscholar ]

            # === Subjects / Topics ===
            -   name: subjects
                fields:
                    - keyword_count
                    - mesh_heading_count
                    - primary_topic
                    - subject_fields
                    - subject_keywords
                    - subject_mesh
                    - subject_topics
                    - tldr
                provider_order: [ pubmed, openalex, semanticscholar, crossref, chembl ]

            # === Biomedical (NEW) ===
            -   name: biomedical
                fields:
                    - chemicals
                    - chemical_count
                    - gene_symbols
                    - databanks
                    - grants
                    - grant_count
                provider_order: [ pubmed, openalex, chembl ]

            # === Citations / Metrics ===
            -   name: citations
                fields:
                    - citation_contexts
                    - citation_subset
                    - citations_made
                    - citations_received
                    - fwci
                    - influential_citation_count
                    - references
                provider_order: [ semanticscholar, crossref, openalex, pubmed, chembl ]

            # === Document type and status ===
            -   name: doc_type
                fields:
                    - content_domain_crossmark_restriction
                    - content_domain_domains
                    - is_oa
                    - is_retracted
                    - language
                    - license_url
                    - oa_status
                    - open_access_url
                    - publication_status
                    - publication_type
                    - publication_type_list
                    - publication_types
                provider_order: [ semanticscholar, pubmed, chembl, crossref, openalex ]

        # Note: output paths auto-computed per ADR-029 convention-based resolution
        # silver: data/output/silver/composite/publication (auto)
        # gold: data/output/gold/composite/publication (auto)

    # ---------------------------------------------------------------------------
    # Cross-Validation Configuration (Pre-Merge)
    # ---------------------------------------------------------------------------
    # Compares paired fields between seed and each enricher before merge.
    # Detects mismatches and flags/nullifies divergent enricher data.
    # Rules:
    #   1 mismatch   -> WARNING
    #   2+ mismatches -> ENRICHER_ERROR (null all enricher fields for that record)
    #   2+ enrichers with ENRICHER_ERROR -> QUARANTINE seed record
    cross_validation:
        enabled: true
        warning_threshold: 1
        error_threshold: 2
        quarantine_threshold: 2
        fuzzy_threshold: 0.8
        numeric_tolerance: 0.10
        enricher_pairings:
            # CrossRef: 8 paired fields
            -   enricher_pipeline: crossref_publication
                fields:
                    - { field: doi, method: exact }
                    - { field: title, method: fuzzy, threshold: 0.8 }
                    - { field: volume, method: exact }
                    - { field: issue, method: exact }
                    - { field: page_first, method: exact }
                    - { field: page_last, method: exact }
                    - { field: publication_year, method: exact }
                    - { field: citations_received, method: numeric_tolerance, threshold: 0.10 }

            # OpenAlex: 9 paired fields
            -   enricher_pipeline: openalex_publication
                fields:
                    - { field: doi, method: exact }
                    - { field: pmid, method: exact }
                    - { field: title, method: fuzzy, threshold: 0.8 }
                    - { field: volume, method: exact }
                    - { field: issue, method: exact }
                    - { field: page_first, method: exact }
                    - { field: page_last, method: exact }
                    - { field: publication_year, method: exact }
                    - { field: citations_received, method: numeric_tolerance, threshold: 0.10 }

            # PubMed: 8 paired fields (no citations_received)
            -   enricher_pipeline: pubmed_publication
                fields:
                    - { field: doi, method: exact }
                    - { field: pmid, method: exact }
                    - { field: title, method: fuzzy, threshold: 0.8 }
                    - { field: volume, method: exact }
                    - { field: issue, method: exact }
                    - { field: page_first, method: exact }
                    - { field: page_last, method: exact }
                    - { field: publication_year, method: exact }

            # SemanticScholar: 9 paired fields
            -   enricher_pipeline: semanticscholar_publication
                fields:
                    - { field: doi, method: exact }
                    - { field: pmid, method: exact }
                    - { field: title, method: fuzzy, threshold: 0.8 }
                    - { field: volume, method: exact }
                    - { field: issue, method: exact }
                    - { field: page_first, method: exact }
                    - { field: page_last, method: exact }
                    - { field: publication_year, method: exact }
                    - { field: citations_received, method: numeric_tolerance, threshold: 0.10 }

    # ---------------------------------------------------------------------------
    # Data Quality Configuration
    # ---------------------------------------------------------------------------
    dq_overrides:
        # External baseline DQ config (ADR-027)
        dq_config_file: ../quality/entities/composite/publication.yaml

        # Per-enricher threshold overrides
        enricher_overrides:
            # Semantic Scholar has higher rate limits, allow more errors
            semanticscholar_publication:
                soft_fail_threshold: 0.20
                hard_fail_threshold: 0.50
            # PubMed may have many pmid-less records filtered
            pubmed_publication:
                soft_fail_threshold: 0.15
                hard_fail_threshold: 0.40

    # ---------------------------------------------------------------------------
    # Execution Options
    # ---------------------------------------------------------------------------
    execution:
        # Maximum concurrent enrichers
        max_concurrency: 4

        # Enable checkpointing for resume capability
        checkpoint_enabled: true

        # Retry configuration for recoverable errors
        retry:
            max_attempts: 3
            backoff_multiplier: 2.0

    # ---------------------------------------------------------------------------
    # Lineage Configuration
    # ---------------------------------------------------------------------------
    lineage:
        # Track which source provided each field value
        track_field_sources: true

        # Include timestamps for each enrichment
        track_timestamps: true

        # Include per-record enrichment status
        track_status: true

        # Provider-specific lookup metadata (renamed with provider prefix)
        # These fields track how each provider resolved the publication
        provider_lookup_fields:
            chembl:
                _lookup_method: chembl_lookup_method
                _original_id: chembl_original_id
            crossref:
                _lookup_method: crossref_lookup_method
                _original_id: crossref_original_id
            openalex:
                _lookup_method: openalex_lookup_method
                _original_id: openalex_original_id
            pubmed:
                _lookup_method: pubmed_lookup_method
                _original_id: pubmed_original_id
            semanticscholar:
                _lookup_method: semanticscholar_lookup_method
                _original_id: semanticscholar_original_id

        # Field-level source tracking for overlapping fields
        # These are fields that come from multiple providers
        track_source_for_fields:
            - title
            - abstract
            - citations_received
            - citations_made
            - subject_mesh
            - affiliation_list
            - author_orcids
            - is_oa
            - oa_status
            - subject_keywords

# -----------------------------------------------------------------------------
# Gold Filters (applied to merged output)
# -----------------------------------------------------------------------------
gold_filters:
    # Only include publications with title
    required_fields:
        - title

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filter rules resolve from:
#   1. configs/base/pipeline.yaml (`filter_defaults`)
#   2. local `gold_filters` in this composite config

# -----------------------------------------------------------------------------
# Maintenance Configuration
# -----------------------------------------------------------------------------

================================================================================
File: target.yaml
Path: composites\target.yaml
================================================================================
# configs/composites/target.yaml
# =============================================================================
# Composite Target Pipeline Configuration
# =============================================================================
#
# Combines biological target data from multiple sources:
# - Seed: ChEMBL targets (target_id, target_type, pref_name, ...)
# - Dependencies (ordered, chained):
#   1. chembl_target_component: fetches component data using primary_component_id from seed
#   2. chembl_protein_class: fetches protein classifications using
#      protein_classification_id from target_component Silver table (chained dep)
#   3. uniprot_idmapping: maps ChEMBL target IDs to UniProt accessions
#   4. uniprot_protein: fetches detailed protein data using uniprot_accession
#      from idmapping Silver table (chained dep)
#
# Dependency chaining (key_source):
# - chembl_target_component uses primary_component_id from seed (standard)
# - chembl_protein_class uses protein_classification_id from target_component
#   Silver table via key_source field (chained dependency)
# - uniprot_idmapping uses target_id from seed (standard)
# - uniprot_protein uses uniprot_accession from idmapping Silver table
#   via key_source field (chained dependency)
#
# Version: 1.2.0
# Reference: ADR-026 Composite Pipeline Pattern
# Last Updated: 2026-02-03
#
# =============================================================================

# -----------------------------------------------------------------------------
# Composite Pipeline Configuration
# -----------------------------------------------------------------------------
composite:
  name: composite_target
  version: "1.2.0"

  # ---------------------------------------------------------------------------
  # Seed Pipeline Configuration
  # ---------------------------------------------------------------------------
  # The seed pipeline extracts primary entities from ChEMBL.
  # Its output provides join keys (target_id) for enrichment.
  seed:
    pipeline: chembl_target
    output_keys:
      - target_id         # ChEMBL target ID (primary key, join key for idmapping)
      - primary_component_id      # Primary component ID (join key for target_component)
      - pref_name         # Target name (for logging/debugging)
      - target_type       # Classification (for filtering)
    silver_table: silver/chembl/target

  # ---------------------------------------------------------------------------
  # Dependency Pipelines (sequential, pre-populate Silver)
  # ---------------------------------------------------------------------------
  # Dependencies run after seed but before enrichers to populate Silver tables.
  # They execute as full standalone pipelines (API -> Bronze -> Silver).
  #
  # Order matters for chained dependencies:
  # 1. chembl_target_component runs first (uses primary_component_id from seed)
  # 2. chembl_protein_class runs second (uses protein_classification_id from
  #    target_component Silver table via key_source)
  # 3. uniprot_idmapping runs third (uses target_id from seed)
  # 4. uniprot_protein runs fourth (uses uniprot_accession from idmapping
  #    Silver table via key_source - CHAINED)
  dependencies:
    # ChEMBL Target Component: detailed per-component data
    # Fetches protein_classifications, xrefs for each component.
    # Uses primary_component_id from seed to filter API requests.
    - pipeline: chembl_target_component
      join_keys:
        - primary_component_id      # Scalar join key from seed (int)
      filter_field: component_id    # Target API filter field
      required: false       # Optional - some targets have no components
      timeout_seconds: 600
      silver_table: silver/chembl/target_component

    # ChEMBL Protein Classification: hierarchical protein class tree
    # Uses protein_classification_id from target_component Silver table.
    # This is a CHAINED DEPENDENCY: reads keys from another dependency's output.
    # Field mapping: source column (protein_classification_id) differs from
    # target API field (protein_class_id).
    - pipeline: chembl_protein_class
      join_keys:
        - protein_classification_id  # Source column in target_component Silver
      filter_field: protein_class_id  # Target API filter field
      key_source: chembl_target_component  # Read keys from this Silver table
      required: false
      timeout_seconds: 300
      silver_table: silver/chembl/protein_class

    # UniProt ID Mapping: maps ChEMBL target IDs to UniProt accessions
    # This MUST run before uniprot_protein to provide uniprot_accession keys.
    # OPTIONAL: Many non-protein targets lack UniProt mappings.
    #
    # ID source: target_id values extracted from seed DataFrame
    #   (NOT from data/input/target.csv — CSV is fallback for standalone mode only).
    #   Flow: seed DataFrame → dependencies_runner_factory extracts join_keys
    #         → filter_ids → IDMappingDataSource.seed_ids → UniProt API.
    #
    # API parameters (from configs/entities/uniprot/idmapping.yaml and configs/providers/uniprot.yaml):
    #   from_db: ChEMBL          — source database for UniProt ID Mapping API
    #   to_db: UniProtKB         — target database
    #   base_url: https://rest.uniprot.org
    #   batch_size: 500 IDs/job  — MAX_IDS_PER_BATCH in idmapping_client.py
    #   polling_interval: 3s     — job status polling period
    #   max_poll_attempts: 100   — ~5 min max wait per batch
    - pipeline: uniprot_idmapping
      join_keys:
        - target_id  # Direct join key from seed
      required: false       # Optional - many targets lack UniProt accessions
      filter_condition: "target_id IS NOT NULL"
      timeout_seconds: 600
      silver_table: silver/uniprot/idmapping

    # UniProt Protein: detailed protein functional data
    # Uses uniprot_accession from idmapping Silver table.
    # This is a CHAINED DEPENDENCY: reads keys from uniprot_idmapping output.
    # Only fetches proteins where mapping_status = 'found'.
    # Provides: function, GO terms, disease associations, subcellular location,
    # pathway, catalytic activity, PDB cross-references, and more.
    - pipeline: uniprot_protein
      join_keys:
        - uniprot_accession  # Source column in idmapping Silver
      filter_field: accession  # Target API filter field (UniProt uses 'accession')
      key_source: uniprot_idmapping  # Read keys from idmapping Silver table
      key_filter: "mapping_status = 'found'"  # Only fetch successfully mapped IDs
      required: false       # Optional - not all targets have UniProt data
      timeout_seconds: 900  # Longer timeout due to rich data
      silver_table: silver/uniprot/protein

  # ---------------------------------------------------------------------------
  # Enricher Pipelines
  # ---------------------------------------------------------------------------
  # Enrichers read from pre-populated Silver tables and join with seed data.
  # All UniProt pipelines moved to dependencies for proper chaining.
  enrichers: []

  # ---------------------------------------------------------------------------
  # Merge Configuration
  # ---------------------------------------------------------------------------
  # Defines how enriched data is combined into the final output.
  merge:
    # Join strategy: left_outer preserves all seed records
    strategy: left_outer

    # Conflict resolution: seed values take priority
    conflict_resolution: seed_priority

    # preserve_all_sources: false
    # Multiple sources with field overlap. Seed values take priority.
    preserve_all_sources: false

    # Field renames for namespace disambiguation
    field_mappings:
      # target_component.description conflicts with target.description
      "chembl.target_component.description": "component_description"

    # Output paths for merged data
    output:
      silver: data/output/silver/composite/target
      gold: data/output/gold/composite/target
    sort_by:
      silver:
        - entity_id
        - target_id
      gold:
        - entity_id
        - target_id

    # Field-level priority for overlapping fields
    # seed_priority applies globally; these are explicit overrides per field.
    field_priorities:
      target_id:
        - chembl  # Seed is authoritative for PK
      primary_component_id:
        - chembl  # Seed primary_component_id is authoritative
      taxonomy_id:
        - chembl  # ChEMBL taxonomy_id takes priority over UniProt
      organism:
        - chembl  # ChEMBL organism name is authoritative

    # -------------------------------------------------------------------------
    # Column Ordering by Semantic Categories
    # -------------------------------------------------------------------------
    # Defines the order of columns in the merged output.
    # The "system" group MUST be first: it captures ETL metadata columns
    # that would otherwise fall into the "remaining" bucket at the end.
    column_groups:
      # === System / ETL metadata (MUST be first) ===
      - name: system
        fields:
          - entity_id
          - content_hash
          - _run_id
          - _run_type
          - _source_batch_id
          - _source
          - _ingestion_ts
          - _index
          - _lookup_method
          - _original_id
        pattern: "^_composite_|^_source_providers|^_enrichment_|^_lineage_|^_dq_"
        provider_order: [chembl, uniprot]

      # === Business identifiers ===
      - name: identifiers
        fields:
          - target_id
          - primary_component_id
          - uniprot_accession
          - mapping_status
        provider_order: [chembl, uniprot]

      # === Target classification ===
      - name: classification
        fields:
          - target_type
          - organism
          - taxonomy_id
          - species_group_flag
        provider_order: [chembl]

      # === Descriptive metadata ===
      - name: descriptors
        fields:
          - pref_name
          - description
          - downgraded
        provider_order: [chembl]

      # === Component data (pre-flattened from ChEMBL API) ===
      - name: components
        fields:
          - component_ids
          - component_accessions
          - component_types
          - component_relationships
          - component_descriptions
          - component_organisms
          - component_taxonomy_ids
          - target_component_synonyms
        provider_order: [chembl]

      # === Enriched component data (from target_component dependency) ===
      - name: enriched_components
        fields:
          - component_type
          - component_description
          - protein_classification_id
          - protein_classification_ids
        provider_order: [chembl]

      # === UniProt protein functional annotations ===
      - name: protein_function
        fields:
          - function_comment
          - catalytic_activity
          - activity_regulation
          - pathway
          - subcellular_location
          - tissue_specificity
          - subunit
        provider_order: [uniprot]

      # === UniProt disease and pharmacology ===
      - name: disease_pharma
        fields:
          - disease_involvement
          - drugbank_ids
          - guidetopharmacology_ids
          - chembl_ids
        provider_order: [uniprot]

      # === UniProt ontology and structure ===
      - name: ontology_structure
        fields:
          - go_terms
          - pdb_xrefs
          - interpro_xrefs      # InterPro domain families (NEW)
          - pfam_xrefs          # Pfam protein families (NEW)
          - reactome_xrefs      # Reactome pathway entries (NEW)
          - keywords
        provider_order: [uniprot]

      # === UniProt protein properties ===
      - name: protein_properties
        fields:
          - protein_name
          - gene_primary
          - protein_existence
          - annotation_score
          - reviewed
          - sequence_length
          - sequence_mass
        provider_order: [uniprot]

      # === Cross-references and pipeline stages ===
      - name: references
        fields:
          - pipeline_stages
        provider_order: [chembl]

    # Fields excluded from merged output (Silver + Gold)
    exclude_fields:
      # --- ChEMBL target exclusions ---
      - chembl.target.target_components
      - chembl.target.cross_references
      # --- ChEMBL target_component exclusions ---
      - chembl.target_component.primary_component_id
      - chembl.target_component.protein_classifications
      - chembl.target_component.target_component_synonyms
      - chembl.target_component.target_component_xrefs
      # --- ChEMBL protein_class exclusions ---
      - chembl.protein_class.protein_class_id
      # --- UniProt idmapping exclusions (data comes from protein) ---
      - uniprot.idmapping.all_mappings
      - uniprot.idmapping.annotation_score
      - uniprot.idmapping.gene_primary
      - uniprot.idmapping.organism_common
      - uniprot.idmapping.organism_scientific
      - uniprot.idmapping.protein_name
      - uniprot.idmapping.reviewed
      - uniprot.idmapping.sequence_length
      - uniprot.idmapping.sequence_mass
      - uniprot.idmapping.target_id
      - uniprot.idmapping.taxonomy_id
      - uniprot.idmapping.uniprot_entry_name
      # --- UniProt protein exclusions (redundant or too large) ---
      - uniprot.protein.accession           # Already have uniprot_accession from idmapping
      - uniprot.protein.entry_name          # Technical field, not needed
      - uniprot.protein.entry_type          # Technical field
      - uniprot.protein.secondary_accessions  # Rarely needed
      - uniprot.protein.sequence            # Too large for composite table
      - uniprot.protein.sequence_checksum   # Technical field
      - uniprot.protein.sequence_modified   # Audit field
      - uniprot.protein.lineage             # Redundant with taxonomy_id
      - uniprot.protein.gene_names          # Use gene_primary instead
      - uniprot.protein.gene_synonyms       # Too verbose
      - uniprot.protein.gene_orf_names      # Too verbose
      - uniprot.protein.protein_short_names  # Use protein_name instead
      - uniprot.protein.protein_alternative_names  # Too verbose
      - uniprot.protein.protein_ec_numbers  # Specialized
      - uniprot.protein.flag                # Technical field
      - uniprot.protein.entry_version       # Audit field
      - uniprot.protein.entry_created       # Audit field
      - uniprot.protein.entry_modified      # Audit field
      - uniprot.protein.features            # JSON, too large
      - uniprot.protein.alternative_products  # Specialized
      - uniprot.protein.similarity_comment  # Low value
      - uniprot.protein.caution             # Low value
      - uniprot.protein.cofactors           # Specialized
      - uniprot.protein.biophysicochemical_properties  # Specialized
      - uniprot.protein.induction           # Specialized
      - uniprot.protein.cross_reference_count  # Metadata
      - uniprot.protein.feature_count       # Metadata
      - uniprot.protein.keyword_count       # Metadata
      - uniprot.protein.isoform_count       # Metadata
      - uniprot.protein.organism_id         # Duplicate of taxonomy_id
      - uniprot.protein.organism_scientific  # Use ChEMBL organism
      - uniprot.protein.organism_common     # Use ChEMBL organism

    # Note: output paths auto-computed per ADR-029 convention-based resolution
    # silver: data/output/silver/composite/target (auto)
    # gold: data/output/gold/composite/target (auto)

  # ---------------------------------------------------------------------------
  # Data Quality Configuration
  # ---------------------------------------------------------------------------
  # Thresholds, required_fields, and field_validations externalized to:
  #   configs/quality/entities/composite/target.yaml
  # Only pipeline-specific enricher_overrides remain inline.
  dq_overrides:
    # External baseline DQ config (ADR-027)
    dq_config_file: ../quality/entities/composite/target.yaml
    # Per-dependency threshold overrides (pipeline-specific)
    enricher_overrides:
      # Many non-protein targets -> UniProt mapping_status="not_found" is expected
      uniprot_idmapping:
        soft_fail_threshold: 0.30  # 30% not_found is acceptable
        hard_fail_threshold: 0.80  # Only fail if >80% errors
      # UniProt protein: chained from idmapping, some accessions may not resolve
      uniprot_protein:
        soft_fail_threshold: 0.20  # 20% missing is acceptable
        hard_fail_threshold: 0.60  # Only fail if >60% errors

  # ---------------------------------------------------------------------------
  # Execution Options
  # ---------------------------------------------------------------------------
  execution:
    # Maximum concurrent dependencies/enrichers
    max_concurrency: 2

    # Enable checkpointing for resume capability
    checkpoint_enabled: true

    # Retry configuration for recoverable errors
    retry:
      max_attempts: 3
      backoff_multiplier: 2.0

  # ---------------------------------------------------------------------------
  # Lineage Configuration
  # ---------------------------------------------------------------------------
  lineage:
    # Track which source provided each field value
    track_field_sources: true

    # Include timestamps for each enrichment
    track_timestamps: true

    # Include per-record enrichment status
    track_status: true

    # Provider-specific lookup metadata
    provider_lookup_fields:
      chembl:
        _lookup_method: chembl_lookup_method
        _original_id: chembl_original_id
      uniprot:
        _lookup_method: uniprot_lookup_method
        _original_id: uniprot_original_id

    # Field-level source tracking (for fields from multiple providers)
    track_source_for_fields:
      - target_id  # Overlapping field between seed and idmapping
      - primary_component_id      # Overlapping field between seed and target_component
      - taxonomy_id       # Overlapping between ChEMBL and UniProt
      - organism          # Overlapping between ChEMBL and UniProt

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Gold filters and filter rules loaded from hierarchical config files.
# No inline gold_filters needed — filter entity config is authoritative.

================================================================================
File: activity.yaml
Path: contracts\chembl\activity.yaml
================================================================================
# ChEMBL Activity Data Quality Contract
# Aligned with configs/base/contract_registry.yaml identity tuple.

contract_ref: "chembl.activity"
contract_version: "1.0.0"
dq_policy_ref: "chembl.dq.v1"
rule_bundle_version: "dq-rules.v1.0"
default_disposition_policy: "warn"
strictness_mode: "moderate"
soft_fail_threshold: 0.05
hard_fail_threshold: 0.20
strict_validation: false
invalid_record_policy: "quarantine"
disposition_overrides:
  "activity_id_required": "fail"
  "standard_value_range": "warn"
report:
  enabled: true
  format: "json"
  include_sample_failures: truebc
  sample_size: 1000

================================================================================
File: molecule.yaml
Path: contracts\chembl\molecule.yaml
================================================================================
# ChEMBL Molecule Data Quality Contract
# Aligned with configs/base/contract_registry.yaml identity tuple.

contract_ref: "chembl.molecule"
contract_version: "1.0.0"
dq_policy_ref: "chembl.dq.v1"
rule_bundle_version: "dq-rules.v1.0"
default_disposition_policy: "warn"
strictness_mode: "moderate"
soft_fail_threshold: 0.05
hard_fail_threshold: 0.20
strict_validation: false
invalid_record_policy: "quarantine"
disposition_overrides:
  "molecule_id_required": "fail"
report:
  enabled: true
  format: "json"
  include_sample_failures: true
  sample_size: 10

================================================================================
File: works.yaml
Path: contracts\crossref\works.yaml
================================================================================
# CrossRef Works Data Quality Contract
# Aligned with configs/base/contract_registry.yaml identity tuple.

contract_ref: "crossref.works"
contract_version: "1.0.0"
dq_policy_ref: "crossref.dq.v1"
rule_bundle_version: "dq-rules.v1.0"
default_disposition_policy: "warn"
strictness_mode: "moderate"
soft_fail_threshold: 0.05
hard_fail_threshold: 0.20
strict_validation: false
invalid_record_policy: "quarantine"
disposition_overrides:
  "doi_required": "fail"
report:
  enabled: true
  format: "json"
  include_sample_failures: true
  sample_size: 10

================================================================================
File: compound.yaml
Path: contracts\pubchem\compound.yaml
================================================================================
# PubChem Compound Data Quality Contract
# Aligned with configs/base/contract_registry.yaml identity tuple.

contract_ref: "pubchem.compound"
contract_version: "1.0.0"
dq_policy_ref: "pubchem.dq.v1"
rule_bundle_version: "dq-rules.v1.0"
default_disposition_policy: "warn"
strictness_mode: "moderate"
soft_fail_threshold: 0.05
hard_fail_threshold: 0.20
strict_validation: false
invalid_record_policy: "quarantine"
disposition_overrides:
  "compound_id_required": "fail"
report:
  enabled: true
  format: "json"
  include_sample_failures: true
  sample_size: 10

================================================================================
File: publication.yaml
Path: contracts\pubmed\publication.yaml
================================================================================
# PubMed Publication Data Quality Contract
# Aligned with configs/base/contract_registry.yaml identity tuple.

contract_ref: "pubmed.publication"
contract_version: "1.0.0"
dq_policy_ref: "pubmed.dq.v1"
rule_bundle_version: "dq-rules.v1.0"
default_disposition_policy: "warn"
strictness_mode: "moderate"
soft_fail_threshold: 0.05
hard_fail_threshold: 0.20
strict_validation: false
invalid_record_policy: "quarantine"
disposition_overrides:
  "pmid_required": "fail"
report:
  enabled: true
  format: "json"
  include_sample_failures: true
  sample_size: 10

================================================================================
File: activity.yaml
Path: entities\chembl\activity.yaml
================================================================================
version: 1.0.0
provider: chembl
entity: activity
pipeline:
    pipeline_name: chembl_activity
    provider: chembl
    entity_type: activity
    description: Extract biological activity records from ChEMBL API
    business_primary_keys:
        - activity_id
    batch_size: 1000
    sink:
        silver:
            mode: append
        gold:
            enabled: false
schema:
    content_hash:
        include: []
        exclude: []
    column_groups:
        -   name: system
            fields:
                - entity_id
                - content_hash
                - _run_id
                - _run_type
                - _source_batch_id
                - _ingestion_ts
                - _index
                - _state
        -   name: business
            fields:
                - activity_id
                - assay_id
                - molecule_id
                - target_id
                - publication_id
                - standard_relation
                - standard_value
                - standard_units
                - standard_type
                - standard_flag
                - pchembl_value
                - data_validity_comment
                - activity_comment
                - potential_duplicate
                - bao_endpoint
                - uo_units
                - qudt_units
                - src_id
                - record_id
                - type
                - relation
                - value
                - units
                - text_value
                - standard_text_value
                - upper_value
                - standard_upper_value
                - toid
                - manual_curation_flag
                - original_activity_id
                - data_validity_description
                - ligand_efficiency_bei
                - ligand_efficiency_le
                - ligand_efficiency_lle
                - ligand_efficiency_sei
                - action_type
                - action_type_description
                - action_type_parent_type
                - activity_properties
                - canonical_smiles
                - molecule_pref_name
                - parent_molecule_id
                - target_pref_name
                - target_organism
                - target_taxonomy_id
                - assay_type
                - assay_description
                - assay_variant_accession
                - assay_variant_mutation
                - bao_format
                - bao_label
                - journal
                - publication_doi
                - publication_pmid
                - publication_pmc_id
                - publication_year
        -   name: dq
            pattern: ^_dq_
    silver:
        include_groups:
            - system
            - business
            - dq
        exclude_fields: []
        alias_policy: preserve
    gold:
        include_groups:
            - system
            - business
        exclude_fields:
            - _dq_*
            - _source_batch_id
            - _index
        alias_policy: canonical
quality:
    version: 1.1.0
    provider: chembl
    entity: activity
    entity_field_validations:
        -   field: activity_id
            type: required
            nullable: false
            error_message: Activity ID is required
        -   field: standard_value
            type: range
            min: 0
            max: 1000000000
            nullable: true
            error_message: standard_value must be non-negative and below 1B
        -   field: pchembl_value
            type: range
            min: 0
            max: 15
            nullable: true
            error_message: pChEMBL value must be between 0 and 15
        -   field: standard_type
            type: enum
            allowed:
                - IC50
                - Ki
                - Kd
                - EC50
                - AC50
                - GI50
                - ED50
                - MIC
                - CC50
                - Potency
                - Activity
                - Inhibition
            nullable: true
            error_message: Invalid standard_type value
        -   field: standard_units
            type: enum
            allowed:
                - nM
                - uM
                - mM
                - pM
                - M
                - '%'
                - ug.mL-1
                - mg.kg-1
            nullable: true
            error_message: Invalid standard_units value
    entity_cross_field_validations:
        -   name: value_requires_units
            fields:
                - standard_value
                - standard_units
            condition: conditional_required
            trigger_field: standard_value
            required_field: standard_units
            error_message: standard_units required when standard_value is present
        -   name: activity_completeness
            fields:
                - standard_value
                - standard_units
                - standard_type
            condition: all_present
            error_message: Complete activity data requires value, units, and type
    entity_conditional_validations:
        -   name: binding_requires_target
            condition_field: assay_type
            condition_value: B
            condition_operator: eq
            then_validations:
                -   field: target_id
                    type: required
                    nullable: false
                    error_message: Binding assays must have a target
        -   name: ic50_range_check
            condition_field: standard_type
            condition_value: IC50
            condition_operator: eq
            then_validations:
                -   field: standard_value
                    type: range
                    min: 0.001
                    max: 100000
                    nullable: false
    key_nullability:
        -   field: activity_id
            key_type: merge
            nullable: false
filters:
    version: 1.0.0
    provider: chembl
    entity: activity
    input_filter:
        enabled: false
        source_path: data/input/activity.csv
        column_name: activity_id
        filter_field: activity_id
    extraction_params:
        standard_type__in: IC50,Ki
        standard_units: nM
        standard_relation: '='
        assay_type__in: B,F
        potential_duplicate: 0
        data_validity_comment__isnull: true
        pchembl_value__isnull: false
        standard_flag: 1
        target_tax_id__isnull: false
    silver_filters:
        columns:
            standard_type:
                - IC50
                - Ki
            standard_relation:
                - '='
            standard_units:
                - nM
            assay_type:
                - B
                - F
            potential_duplicate:
                - '0'
        ranges:
            activity_id:
                min: 1
                max: 10000000000
            standard_value:
                min: 0
                include_min: false
            pchembl_value:
                min: 3
                max: 10
            publication_year:
                min: 1950
                max: 2050
        required_fields:
            # Final Silver policy: unit-less activity records are quarantined
            # instead of relaxing canonical chemistry/unit fields to nullable.
            - activity_id
            - molecule_id
            - assay_id
            - target_id
            - publication_id
            - record_id
            - src_id
            - canonical_smiles
            - target_organism
            - target_taxonomy_id
            - assay_description
            - bao_endpoint
            - bao_format
            - bao_label
            - relation
            - value
            - units
            - standard_value
            - standard_units
            - standard_flag
            - pchembl_value
            - uo_units
            - journal
            - publication_year
            - _state
        exclude_if_present:
            - data_validity_comment
    gold_filters:
        columns:
            standard_type:
                - IC50
                - Ki
            standard_units:
                - nM
            standard_relation:
                - '='
            assay_type:
                - B
                - F
            potential_duplicate:
                - '0'
        ranges:
            standard_value:
                min: 0
                include_min: false
        required_fields:
            - standard_type
            - standard_value
            - standard_units
            - target_id
contracts:
    primary_key:
        - activity_id
    merge_keys:
        - activity_id
    hash_include: []
hash_policy:
    provider: chembl
    entity: activity
    contract:
        version: 1.0.0
        migration_note: Initial hash policy baseline for chembl/activity.
    hash_policy:
        algorithm: sha256
        canonicalization: provider + canonical_json_dumps(normalized_record)
        include_fields:
            - activity_chembl_id
            - assay_chembl_id
            - molecule_chembl_id
            - standard_type
            - standard_relation
            - standard_value
            - standard_units
            - pchembl_value
            - confidence_score
            - document_chembl_id
            - year
        exclude_fields:
            - _ingestion_ts
            - _run_id
            - _run_type
            - _dq_warn
            - _dq_error
            - _source_batch_id
            - _index
        exclude_patterns:
            - ^_dq_
        normalization:
            trim_strings: true
            round_floats:
                enabled: true
                precision: 10
            dates:
                enabled: true
                format: YYYY-MM-DD
            null_handling:
                nan_to_null: true
                inf_to_null: true

================================================================================
File: assay.yaml
Path: entities\chembl\assay.yaml
================================================================================
version: 1.0.0
provider: chembl
entity: assay
pipeline:
    pipeline_name: chembl_assay
    provider: chembl
    entity_type: assay
    description: Extract bioassay definitions from ChEMBL API
    business_primary_keys:
        - assay_id
    batch_size: 1000

    sink:
        silver:
            partition_by:
                - assay_type
        gold:
            mode: scd2
            scd_config:
                valid_from_col: _valid_from
                valid_to_col: _valid_to
                current_flag_col: _is_current
                version_col: _version
schema:
    content_hash:
        include: []
        exclude: []
    column_groups:
        -   name: system
            fields:
                - entity_id
                - content_hash
                - _run_id
                - _run_type
                - _source_batch_id
                - _ingestion_ts
                - _index
        -   name: business
            fields:
                - assay_id
                - description
                - assay_type
                - assay_type_description
                - assay_test_type
                - assay_category
                - assay_group
                - assay_organism
                - assay_taxonomy_id
                - assay_strain
                - assay_tissue
                - assay_cell_type
                - assay_subcellular_fraction
                - target_id
                - relationship_type
                - relationship_description
                - confidence_score
                - confidence_description
                - src_id
                - src_assay_id
                - publication_id
                - assay_pref_name
                - score
                - cell_id
                - tissue_id
                - bao_format
                - bao_label
                - aidx
                - variant_accession
                - variant_isoform
                - variant_mutation
                - variant_organism
                - variant_sequence
                - variant_taxonomy_id
                - variant_sequence_json
                - assay_classifications
                - assay_parameters
        -   name: dq
            pattern: ^_dq_
    silver:
        include_groups:
            - system
            - business
            - dq
        exclude_fields: []
        alias_policy: preserve
    gold:
        include_groups:
            - system
            - business
        exclude_fields:
            - _dq_*
            - _source_batch_id
            - _index
        alias_policy: canonical
quality:
    version: 1.1.0
    provider: chembl
    entity: assay
    entity_field_validations:
        -   field: assay_id
            type: required
            nullable: false
            error_message: Assay ID is required
        -   field: assay_type
            type: enum
            allowed:
                - B
                - F
                - A
                - T
                - P
                - U
            nullable: false
            error_message: assay_type must be one of B, F, A, T, P, U
        -   field: confidence_score
            type: range
            min: 0
            max: 9
            nullable: true
        -   field: relationship_type
            type: enum
            allowed:
                - D
                - H
                - M
                - N
                - S
                - U
            nullable: true
    entity_cross_field_validations:
        -   name: assay_identifiable
            fields:
                - assay_id
                - description
            condition: all_present
            error_message: Assay must have ID and description
    entity_conditional_validations: []
    key_nullability:
        -   field: assay_id
            key_type: merge
            nullable: false
        -   field: assay_type
            key_type: partition
            nullable: false
filters:
    version: 1.0.0
    provider: chembl
    entity: assay
    input_filter:
        enabled: false
        source_path: data/input/assay.csv
        column_name: assay_chembl_id
        filter_field: assay_id
    extraction_params:
        assay_type__in: B,F
        confidence_score__gte: 8
        relationship_type: D
        target_chembl_id__isnull: false
        src_id: 1
    silver_filters:
        columns:
            assay_type:
                - B
                - F
            relationship_type:
                - D
            src_id:
                - '1'
        ranges:
            confidence_score:
                min: 8
                max: 9
        required_fields:
            - assay_id
            - assay_type
            - description
            - target_id
            - publication_id
            - bao_format
            - assay_type_description
            - relationship_type
            - confidence_score
    gold_filters:
        columns:
            assay_type:
                - B
                - F
            confidence_score:
                - '8'
                - '9'
            relationship_type:
                - D
        required_fields:
            - assay_type
            - description
contracts:
    primary_key:
        - assay_id
    merge_keys:
        - assay_id
    hash_include: []

================================================================================
File: assay_parameters.yaml
Path: entities\chembl\assay_parameters.yaml
================================================================================
version: 1.0.0
provider: chembl
entity: assay_parameters
pipeline:
  pipeline_name: chembl_assay_parameters
  provider: chembl
  entity_type: assay_parameters
  description: Extract experimental assay parameters from ChEMBL API
  business_primary_keys:
  - assay_param_id
  sink:
    silver:
      partition_by:
      - type
    gold:
      mode: scd2
      scd_config:
        valid_from_col: _valid_from
        valid_to_col: _valid_to
        current_flag_col: _is_current
        version_col: _version
schema:
  content_hash:
    include: []
    exclude: []
  column_groups:
  - name: system
    fields:
    - entity_id
    - content_hash
    - _run_id
    - _run_type
    - _source_batch_id
    - _ingestion_ts
    - _index
  - name: business
    fields:
    - assay_param_id
    - assay_id
    - type
    - relation
    - value
    - units
    - text_value
    - comments
    - standard_type
    - standard_relation
    - standard_value
    - standard_units
    - standard_text_value
  - name: dq
    pattern: ^_dq_
  silver:
    include_groups:
    - system
    - business
    - dq
    exclude_fields: []
    alias_policy: preserve
  gold:
    include_groups:
    - system
    - business
    exclude_fields:
    - _dq_*
    - _source_batch_id
    - _index
    alias_policy: canonical
quality:
  version: 1.0.0
  provider: chembl
  entity: assay_parameters
  entity_field_validations:
  - field: assay_param_id
    type: range
    min: 1
    nullable: false
    error_message: Assay parameter ID is required and must be positive
  - field: assay_id
    type: pattern
    pattern: ^CHEMBL\d+$
    nullable: false
    error_message: assay_id must match CHEMBL format
  - field: type
    type: pattern
    pattern: ^.{1,100}$
    nullable: false
    error_message: Parameter type is required
  entity_cross_field_validations:
  - name: param_linkage
    fields:
    - assay_param_id
    - assay_id
    condition: all_present
    error_message: Both param ID and assay ID are required
  entity_conditional_validations: []
  key_nullability:
  - field: assay_param_id
    key_type: merge
    nullable: false
  - field: type
    key_type: partition
    nullable: false
filters:
  version: 1.0.0
  provider: chembl
  entity: assay_parameters
  input_filter:
    enabled: true
    source_path: data/input/assay_parameters.csv
    column_name: assay_param_id
    filter_field: assay_param_id
    batch_size: 1000
  silver_filters:
    required_fields:
    - assay_id
    - assay_param_id
    - type
  gold_filters:
    required_fields:
    - assay_id
    - type
contracts:
  primary_key:
  - assay_param_id
  merge_keys:
  - assay_param_id
  hash_include: []

================================================================================
File: cell_line.yaml
Path: entities\chembl\cell_line.yaml
================================================================================
version: 1.0.0
provider: chembl
entity: cell_line
pipeline:
  pipeline_name: chembl_cell_line
  provider: chembl
  entity_type: cell_line
  description: Extract cell lines from ChEMBL API
  business_primary_keys:
  - cell_id
  sink:
    gold:
      mode: scd2
      scd_config:
        valid_from_col: _valid_from
        valid_to_col: _valid_to
        current_flag_col: _is_current
        version_col: _version
schema:
  content_hash:
    include: []
    exclude: []
  column_groups:
  - name: system
    fields:
    - entity_id
    - content_hash
    - _run_id
    - _run_type
    - _source_batch_id
    - _ingestion_ts
    - _index
  - name: business
    fields:
    - cell_id
    - cell_name
    - cell_description
    - cell_source_tissue
    - cell_source_organism
    - cell_source_taxonomy_id
    - cell_type
    - cellosaurus_id
    - clo_id
    - cl_lincs_id
    - efo_id
  - name: dq
    pattern: ^_dq_
  silver:
    include_groups:
    - system
    - business
    - dq
    exclude_fields: []
    alias_policy: preserve
  gold:
    include_groups:
    - system
    - business
    exclude_fields:
    - _dq_*
    - _source_batch_id
    - _index
    alias_policy: canonical
quality:
  version: 1.0.0
  provider: chembl
  entity: cell_line
  entity_field_validations:
  - field: cell_id
    type: pattern
    pattern: ^CHEMBL\d+$
    nullable: false
    error_message: cell_id must match CHEMBL format
  - field: cell_name
    type: pattern
    pattern: ^.{1,200}$
    nullable: false
    error_message: cell_name is required and must not exceed 200 chars
  - field: cellosaurus_id
    type: pattern
    pattern: ^CVCL_[A-Z0-9]+$
    nullable: true
    error_message: cellosaurus_id must match CVCL format
  - field: cell_source_taxonomy_id
    type: range
    min: 1
    max: 10000000
    nullable: true
  entity_cross_field_validations: []
  entity_conditional_validations: []
  key_nullability:
  - field: cell_id
    key_type: merge
    nullable: false
filters:
  version: 1.0.0
  provider: chembl
  entity: cell_line
  input_filter:
    enabled: true
    source_path: data/input/cell.csv
    column_name: cell_chembl_id
    filter_field: cell_chembl_id
    batch_size: 20
  silver_filters:
    required_fields:
    - cell_id
    - cell_name
  gold_filters:
    required_fields:
    - cell_name
contracts:
  primary_key:
  - cell_id
  merge_keys:
  - cell_id
  hash_include: []

================================================================================
File: compound_record.yaml
Path: entities\chembl\compound_record.yaml
================================================================================
version: 1.0.0
provider: chembl
entity: compound_record
pipeline:
  pipeline_name: chembl_compound_record
  provider: chembl
  entity_type: compound_record
  description: Extract compound records from ChEMBL API
  business_primary_keys:
  - record_id
  sink:
    gold:
      mode: scd2
      scd_config:
        valid_from_col: _valid_from
        valid_to_col: _valid_to
        current_flag_col: _is_current
        version_col: _version
schema:
  content_hash:
    include: []
    exclude: []
  column_groups:
  - name: system
    fields:
    - entity_id
    - content_hash
    - _run_id
    - _run_type
    - _source_batch_id
    - _ingestion_ts
    - _index
  - name: business
    fields:
    - record_id
    - molecule_id
    - publication_id
    - src_id
    - compound_key
    - compound_name
    - src_compound_id
  - name: dq
    pattern: ^_dq_
  silver:
    include_groups:
    - system
    - business
    - dq
    exclude_fields: []
    alias_policy: preserve
  gold:
    include_groups:
    - system
    - business
    exclude_fields:
    - _dq_*
    - _source_batch_id
    - _index
    alias_policy: canonical
quality:
  version: 1.0.0
  provider: chembl
  entity: compound_record
  entity_field_validations:
  - field: record_id
    type: range
    min: 1
    nullable: false
    error_message: Record ID is required and must be positive
  - field: molecule_id
    type: pattern
    pattern: ^CHEMBL\d+$
    nullable: false
    error_message: molecule_id must match CHEMBL format
  - field: publication_id
    type: pattern
    pattern: ^CHEMBL\d+$
    nullable: false
    error_message: publication_id must match CHEMBL format
  - field: src_id
    type: range
    min: 1
    nullable: true
  entity_cross_field_validations:
  - name: record_linkage
    fields:
    - molecule_id
    - publication_id
    condition: all_present
    error_message: Both molecule and document IDs are required
  entity_conditional_validations: []
  key_nullability:
  - field: record_id
    key_type: merge
    nullable: false
filters:
  version: 1.0.0
  provider: chembl
  entity: compound_record
  input_filter:
    enabled: true
    source_path: data/input/molecule.csv
    column_name: molecule_chembl_id
    filter_field: molecule_id
    batch_size: 1
  silver_filters:
    required_fields:
    - molecule_id
    - publication_id
    - record_id
  gold_filters:
    required_fields:
    - molecule_id
    - publication_id
contracts:
  primary_key:
  - record_id
  merge_keys:
  - record_id
  hash_include: []

================================================================================
File: molecule.yaml
Path: entities\chembl\molecule.yaml
================================================================================
version: 1.0.0
provider: chembl
entity: molecule
pipeline:
    pipeline_name: chembl_molecule
    provider: chembl
    entity_type: molecule
    description: Extract molecules/compounds from ChEMBL API
    business_primary_keys:
        - molecule_id
    field_policy:
        therapeutic_flag:
            boolean_true_values:
                - 'true'
                - therapeutic
            boolean_false_values:
                - 'false'
                - non_therapeutic
    sink:
        silver:
            partition_by:
                - molecule_type
        gold:
            mode: scd2
            scd_config:
                valid_from_col: _valid_from
                valid_to_col: _valid_to
                current_flag_col: _is_current
                version_col: _version
schema:
    content_hash:
        include: []
        exclude: []
    column_groups:
        -   name: system
            fields:
                - entity_id
                - content_hash
                - _run_id
                - _run_type
                - _source_batch_id
                - _ingestion_ts
                - _index
        -   name: business
            fields:
                - molecule_id
                - pref_name
                - max_phase
                - structure_type
                - molecule_type
                - first_approval
                - therapeutic_flag
                - oral
                - parenteral
                - topical
                - black_box_warning
                - natural_product
                - first_in_class
                - prodrug
                - inorganic_flag
                - polymer_flag
                - withdrawn_flag
                - chirality
                - dosed_ingredient
                - availability_type
                - usan_year
                - usan_stem
                - usan_substem
                - usan_stem_definition
                - helm_notation
                - molecule_species
                - hierarchy_parent_chembl_id
                - hierarchy_active_chembl_id
                - hierarchy_child_chembl_id
                - logp
                - logp_method
                - mw_freebase
                - molecular_weight
                - hba_count
                - hbd_count
                - polar_surface_area
                - rotatable_bond_count
                - ro5_violation_count
                - heavy_atom_count
                - aromatic_ring_count
                - qed_score
                - molecular_formula
                - ro3_pass
                - canonical_smiles
                - standard_inchi
                - inchi_key
                - molecule_hierarchy
                - molecule_properties
                - molecule_structures
                - molecule_synonyms
                - cross_references
                - atc_classifications
        -   name: dq
            pattern: ^_dq_
    silver:
        include_groups:
            - system
            - business
            - dq
        exclude_fields: []
        alias_policy: preserve
    gold:
        include_groups:
            - system
            - business
        exclude_fields:
            - _dq_*
            - _source_batch_id
            - _index
        alias_policy: canonical
quality:
    version: 1.1.0
    provider: chembl
    entity: molecule
    entity_field_validations:
        -   field: molecule_id
            type: required
            nullable: false
            error_message: Molecule ChEMBL ID is required
        -   field: property_full_mwt
            type: range
            min: 100
            max: 1000
            nullable: true
            error_message: Molecular weight must be between 10 and 10000 Da
        -   field: property_alogp
            type: range
            min: -10
            max: 20
            nullable: true
            error_message: ALogP value out of expected range
        -   field: molecule_type
            type: enum
            allowed:
                - Small molecule
                - Protein
                - Antibody
                - Oligosaccharide
                - Oligonucleotide
                - Cell
                - Enzyme
                - Unknown
            nullable: true
        -   field: structure_type
            type: enum
            allowed:
                - MOL
                - SEQ
                - NONE
                - BOTH
            nullable: true
        -   field: canonical_smiles
            type: custom
            validator: smiles_validator
            nullable: true
        -   field: property_hba
            type: range
            min: 0
            max: 50
            nullable: true
        -   field: property_hbd
            type: range
            min: 0
            max: 30
            nullable: true
        -   field: property_psa
            type: range
            min: 0
            max: 1000
            nullable: true
    entity_cross_field_validations:
        -   name: structure_completeness
            fields:
                - canonical_smiles
                - standard_inchi
                - inchi_key
            condition: any_present
            error_message: At least one structure identifier required
    entity_conditional_validations: []
    key_nullability:
        -   field: molecule_id
            key_type: merge
            nullable: false
        -   field: molecule_type
            key_type: partition
            nullable: false
filters:
    version: 1.0.0
    provider: chembl
    entity: molecule
    input_filter:
        enabled: false
        source_path: data/input/molecule.csv
        column_name: molecule_chembl_id
        filter_field: molecule_id
        batch_size: 20
    extraction_params:
        molecule_type: Small molecule
        structure_type: MOL
        inorganic_flag: 0
    silver_filters:
        columns:
            molecule_type:
                - Small molecule
            structure_type:
                - MOL
            inorganic_flag:
                - '0'
        required_fields:
            - molecule_id
            - molecule_type
    gold_filters:
        columns:
            molecule_type:
                - Small molecule
            structure_type:
                - MOL
            inorganic_flag:
                - '0'
        required_fields:
            - molecule_id
contracts:
    primary_key:
        - molecule_id
    merge_keys:
        - molecule_id
    hash_include: []

================================================================================
File: protein_class.yaml
Path: entities\chembl\protein_class.yaml
================================================================================
version: 1.0.0
provider: chembl
entity: protein_class
pipeline:
  pipeline_name: chembl_protein_class
  provider: chembl
  entity_type: protein_class
  description: ChEMBL Protein Classification hierarchy (enzyme classes, receptor types,
    etc.)
  business_primary_keys:
  - protein_class_id
  batch_size: 500
  checkpoint_interval: 500
  sink:
    silver:
      partition_by:
      - class_level
    gold:
      mode: scd2
      scd_config:
        valid_from_col: _valid_from
        valid_to_col: _valid_to
        current_flag_col: _is_current
        version_col: _version
schema:
  content_hash:
    include: []
    exclude: []
  column_groups:
  - name: system
    fields:
    - entity_id
    - content_hash
    - _run_id
    - _run_type
    - _source_batch_id
    - _ingestion_ts
    - _index
  - name: business
    fields:
    - protein_class_id
    - parent_id
    - replaced_by
    - pref_name
    - short_name
    - protein_class_desc
    - definition
    - class_level
    - sort_order
    - downgraded
  - name: dq
    pattern: ^_dq_
  silver:
    include_groups:
    - system
    - business
    - dq
    exclude_fields: []
    alias_policy: preserve
  gold:
    include_groups:
    - system
    - business
    exclude_fields:
    - _dq_*
    - _source_batch_id
    - _index
    alias_policy: canonical
quality:
  version: 1.0.0
  provider: chembl
  entity: protein_class
  common_field_validations:
  - field: protein_class_id
    type: range
    min: 1
    nullable: false
    error_message: Protein class ID is required and must be positive
  - field: class_level
    type: range
    min: 1
    max: 10
    nullable: true
    error_message: Class level must be between 1 and 10
  - field: pref_name
    type: pattern
    pattern: ^.{1,500}$
    nullable: false
    error_message: pref_name is required
  - field: parent_id
    type: range
    min: 1
    nullable: true
    error_message: parent_id must be positive when present
  common_cross_field_validations:
  - name: hierarchy_valid
    fields:
    - protein_class_id
    - parent_id
    condition: custom
    validator: validate_hierarchy_no_self_reference
    error_message: parent_id cannot equal protein_class_id
  entity_conditional_validations: []
  key_nullability:
  - field: protein_class_id
    key_type: merge
    nullable: false
  - field: class_level
    key_type: partition
    nullable: false
filters:
  version: 1.0.0
  provider: chembl
  entity: protein_class
  input_filter:
    enabled: false
  silver_filters:
    required_fields:
    - class_level
    - protein_class_id
  gold_filters:
    columns:
      downgraded:
      - '0'
    required_fields:
    - pref_name
contracts:
  primary_key:
  - protein_class_id
  merge_keys:
  - protein_class_id
  hash_include: []

================================================================================
File: publication.yaml
Path: entities\chembl\publication.yaml
================================================================================
version: 1.0.0
provider: chembl
entity: publication
pipeline:
    pipeline_name: chembl_publication
    provider: chembl
    entity_type: publication
    version: 2.1.0
    description: Extract scientific publications from ChEMBL API
    page_size_override: 1000
    batch_size: 1000
    loading_strategy: full_scan_only
    business_primary_keys:
        - publication_id
    sink:
        gold:
            mode: scd2
            scd_config:
                valid_from_col: _valid_from
                valid_to_col: _valid_to
                current_flag_col: _is_current
                version_col: _version
schema:
    column_groups:
        -   name: system
            fields:
                - entity_id
                - content_hash
                - _run_id
                - _run_type
                - _source_batch_id
                - _source
                - _ingestion_ts
                - _index
                - _lookup_method
                - _original_id
        -   name: identifiers
            fields:
                - publication_id
                - publication_doi
                - publication_pmid
                - publication_pmc_id
        -   name: title
            fields:
                - title
        -   name: abstract
            fields:
                - abstract
        -   name: authors
            fields:
                - authors
        -   name: journal
            fields:
                - journal
        -   name: year
            fields:
                - publication_year
        -   name: pagination
            fields:
                - volume
                - issue
                - page_first
                - page_last
        -   name: doc_type
            fields:
                - publication_type
        -   name: provider_ids
            fields:
                - src_id
                - chembl_release
                - creation_date
        -   name: dq
            pattern: ^_dq_
    silver:
        include_groups:
            - system
            - identifiers
            - title
            - abstract
            - authors
            - journal
            - year
            - pagination
            - doc_type
            - provider_ids
            - dq
    gold:
        include_groups:
            - system
            - identifiers
            - title
            - abstract
            - authors
            - journal
            - year
            - pagination
            - doc_type
        exclude_fields:
            - _dq_*
            - _source_batch_id
            - _index
            - _lookup_method
            - _original_id
quality:
    version: 1.0.0
    provider: chembl
    entity: publication
    entity_field_validations:
        -   field: publication_id
            type: pattern
            pattern: ^CHEMBL\d+$
            nullable: false
            error_message: publication_id must match CHEMBL format
        -   field: publication_type
            type: enum
            allowed:
                - journal-article
                - book
                - dataset
                - patent
            nullable: false
        -   field: publication_year
            type: range
            min: 1500
            max: 2100
            nullable: true
            error_message: Publication year must be between 1500 and 2100
        -   field: publication_year
            type: range
            min: 1950
            nullable: true
            severity: warn
            error_message: "Publication year before 1950 \u2014 will be filtered at Gold stage"
        -   field: publication_pmid
            type: range
            min: 1
            max: 10000000000
            nullable: true
            error_message: PubMed ID must be a positive integer
        -   field: publication_doi
            type: pattern
            pattern: ^10\.\d{4,}/\S+$
            nullable: true
            error_message: DOI must match format 10.XXXX/suffix (no whitespace)
        -   field: title
            type: max_length
            max_length: 2000
            nullable: false
            error_message: Title must not exceed 2000 characters
        -   field: title
            type: not_null
            nullable: false
            error_message: Missing title is not allowed for Silver publication records
        -   field: title
            type: pattern
            pattern: \S
            nullable: false
            error_message: Title must not be empty or whitespace-only
        -   field: citations_received
            type: range
            min: 0
            nullable: true
            error_message: Citation count must be non-negative
        -   field: citations_received
            type: range
            min: 0
            max: 10000000
            nullable: true
            severity: warn
            error_message: Unusually high citation count
        -   field: citations_made
            type: range
            min: 0
            nullable: true
            error_message: Reference count must be non-negative
    entity_cross_field_validations:
        -   name: publication_identifiable
            fields:
                - publication_id
                - title
            condition: all_present
            severity: error
            error_message: Publication must have publication_id and title
        -   name: has_cross_reference
            fields:
                - publication_pmid
                - publication_doi
            condition: any_present
            severity: warn
            error_message: Publication should have at least one external identifier (PMID
                or DOI)
    entity_conditional_validations:
        -   name: publication_requires_title
            condition_field: publication_type
            condition_value: journal-article
            condition_operator: eq
            then_validations:
                -   field: title
                    type: not_null
                    nullable: false
                    error_message: Publications of type PUBLICATION must have a title
    key_nullability:
        -   field: publication_id
            key_type: merge
            nullable: false
filters:
    version: 1.0.0
    provider: chembl
    entity: publication
    input_filter:
        enabled: false
        source_path: data/input/publication.csv
        column_name: publication_id
        filter_field: publication_id
        batch_size: 16
    extraction_params:
        doc_type: PUBLICATION
        year__gte: 1950
        year__lte: 2050
    silver_filters:
        columns:
            publication_type:
                - journal-article
        ranges:
            publication_year:
                min: 1950
                max: 2050
        required_fields:
            - publication_id
            - publication_type
            - title
    gold_filters:
        columns:
            publication_type:
                - journal-article
        ranges:
            publication_year:
                min: 1950
                max: 2050
        required_fields:
            - publication_id
            - publication_type
            - title
contracts:
    primary_key:
        - publication_id
    merge_keys:
        - publication_id
    hash_include: []

================================================================================
File: publication_similarity.yaml
Path: entities\chembl\publication_similarity.yaml
================================================================================
version: 1.0.0
provider: chembl
entity: publication_similarity
pipeline:
  pipeline_name: chembl_publication_similarity
  provider: chembl
  entity_type: publication_similarity
  version: 2.1.0
  description: Extract publication similarity data (Tanimoto coefficients) from ChEMBL
    API
  loading_strategy: full_scan_only
  business_primary_keys:
  - sim_id
  sink:
    gold:
      mode: overwrite
schema:
  content_hash:
    include: []
    exclude: []
  column_groups:
  - name: system
    fields:
    - entity_id
    - content_hash
    - _run_id
    - _run_type
    - _source_batch_id
    - _ingestion_ts
    - _index
  - name: business
    fields:
    - sim_id
    - doc_1
    - doc_2
    - pubmed_id1
    - pubmed_id2
    - tid_tani
    - mol_tani
    - avg_tani
    - max_tani
  - name: dq
    pattern: ^_dq_
  silver:
    include_groups:
    - system
    - business
    - dq
    exclude_fields: []
    alias_policy: preserve
  gold:
    include_groups:
    - system
    - business
    exclude_fields:
    - _dq_*
    - _source_batch_id
    - _index
    alias_policy: canonical
quality:
  version: 1.0.0
  provider: chembl
  entity: publication_similarity
  entity_field_validations:
  - field: sim_id
    type: range
    min: 1
    nullable: false
    error_message: Similarity ID is required and must be positive
  - field: doc_1
    type: range
    min: 1
    nullable: false
    error_message: First document ID is required
  - field: doc_2
    type: range
    min: 1
    nullable: false
    error_message: Second document ID is required
  - field: max_tani
    type: range
    min: 0
    max: 1
    nullable: true
    error_message: Tanimoto coefficient must be between 0 and 1
  - field: avg_tani
    type: range
    min: 0
    max: 1
    nullable: true
    error_message: Average Tanimoto must be between 0 and 1
  entity_cross_field_validations:
  - name: similarity_pair
    fields:
    - doc_1
    - doc_2
    condition: all_present
    error_message: Both document IDs are required
  entity_conditional_validations: []
  key_nullability:
  - field: sim_id
    key_type: merge
    nullable: false
filters:
  version: 1.0.0
  provider: chembl
  entity: publication_similarity
  input_filter:
    enabled: false
  silver_filters:
    required_fields:
    - sim_id
    - doc_1
    - doc_2
  gold_filters:
    ranges:
      max_tani:
        min: 0.5
        include_min: true
    required_fields:
    - sim_id
    - doc_1
    - doc_2
contracts:
  primary_key:
  - sim_id
  merge_keys:
  - sim_id
  hash_include: []

================================================================================
File: publication_term.yaml
Path: entities\chembl\publication_term.yaml
================================================================================
version: 1.0.0
provider: chembl
entity: publication_term
pipeline:
  pipeline_name: chembl_publication_term
  provider: chembl
  entity_type: publication_term
  version: 2.1.0
  description: Extract publication terms (MeSH, keywords) from ChEMBL Publication
    records
  loading_strategy: full_scan_only
  business_primary_keys:
  - entity_id
  sink:
    silver:
      partition_by:
      - term_type
    gold:
      mode: overwrite
schema:
  content_hash:
    include: []
    exclude: []
  column_groups:
  - name: system
    fields:
    - entity_id
    - content_hash
    - _run_id
    - _run_type
    - _source_batch_id
    - _ingestion_ts
    - _index
  - name: business
    fields:
    - publication_id
    - term
    - term_type
    - mesh_id
    - qualifier
  - name: dq
    pattern: ^_dq_
  silver:
    include_groups:
    - system
    - business
    - dq
    exclude_fields: []
    alias_policy: preserve
  gold:
    include_groups:
    - system
    - business
    exclude_fields:
    - _dq_*
    - _source_batch_id
    - _index
    alias_policy: canonical
quality:
  version: 1.0.0
  provider: chembl
  entity: publication_term
  entity_field_validations:
  - field: entity_id
    type: pattern
    pattern: ^[a-f0-9]{64}$
    nullable: false
    error_message: entity_id must be a 64-char SHA256 hash
  - field: publication_id
    type: pattern
    pattern: ^CHEMBL\d+$
    nullable: false
    error_message: publication_id must match CHEMBL format
  - field: term_type
    type: enum
    allowed:
    - MESH_HEADING
    - KEYWORD
    - AUTHOR
    - INSTITUTION
    nullable: false
    error_message: term_type is required and must be valid
  - field: term
    type: pattern
    pattern: ^.{1,500}$
    nullable: false
    error_message: term is required and must not exceed 500 chars
  entity_cross_field_validations:
  - name: term_completeness
    fields:
    - publication_id
    - term
    - term_type
    condition: all_present
    error_message: All term fields are required
  entity_conditional_validations: []
  key_nullability:
  - field: entity_id
    key_type: merge
    nullable: false
  - field: term_type
    key_type: partition
    nullable: false
filters:
  version: 1.0.0
  provider: chembl
  entity: publication_term
  input_filter:
    enabled: true
    source_path: data/input/publication.csv
    column_name: publication_id
    filter_field: publication_id
    batch_size: 20
  extraction_params:
    doc_type: PUBLICATION
    year__gte: 1950
    year__lte: 2050
  silver_filters:
    required_fields:
    - publication_id
    - term
    - term_type
  gold_filters:
    columns:
      term_type:
      - MESH_HEADING
      - KEYWORD
    required_fields:
    - publication_id
    - term
    - term_type
contracts:
  primary_key:
  - entity_id
  merge_keys:
  - entity_id
  hash_include: []

================================================================================
File: subcellular_fraction.yaml
Path: entities\chembl\subcellular_fraction.yaml
================================================================================
version: 1.0.0
provider: chembl
entity: subcellular_fraction
pipeline:
  pipeline_name: chembl_subcellular_fraction
  provider: chembl
  entity_type: subcellular_fraction
  version: 1.0.0
  description: Extract unique subcellular fractions from ChEMBL Assay records
  loading_strategy: full_scan_only
  business_primary_keys:
  - entity_id
  sink:
    gold:
      mode: scd2
      scd_config:
        valid_from_col: _valid_from
        valid_to_col: _valid_to
        current_flag_col: _is_current
        version_col: _version
schema:
  content_hash:
    include: []
    exclude: []
  column_groups:
  - name: system
    fields:
    - entity_id
    - content_hash
    - _run_id
    - _run_type
    - _source_batch_id
    - _ingestion_ts
    - _index
  - name: business
    fields:
    - subcellular_fraction
    - assay_count
    - example_assay_id
  - name: dq
    pattern: ^_dq_
  silver:
    include_groups:
    - system
    - business
    - dq
    exclude_fields: []
    alias_policy: preserve
  gold:
    include_groups:
    - system
    - business
    exclude_fields:
    - _dq_*
    - _source_batch_id
    - _index
    alias_policy: canonical
quality:
  version: 1.0.0
  provider: chembl
  entity: subcellular_fraction
  entity_field_validations:
  - field: entity_id
    type: pattern
    pattern: ^[a-f0-9]{16}$
    nullable: false
    error_message: entity_id must be a 16-char SHA256 hash prefix
  - field: subcellular_fraction
    type: pattern
    pattern: ^.{1,200}$
    nullable: false
    error_message: subcellular_fraction is required and must not exceed 200 chars
  - field: assay_count
    type: range
    min: 0
    nullable: true
    error_message: assay_count must be non-negative
  - field: example_assay_id
    type: pattern
    pattern: ^CHEMBL\d+$
    nullable: true
    error_message: example_assay_id must match CHEMBL format if present
  entity_cross_field_validations: []
  entity_conditional_validations: []
  key_nullability:
  - field: entity_id
    key_type: merge
    nullable: false
filters:
  version: 1.0.0
  provider: chembl
  entity: subcellular_fraction
  input_filter:
    enabled: false
  silver_filters:
    required_fields:
    - subcellular_fraction
  gold_filters:
    required_fields:
    - subcellular_fraction
    columns: {}
contracts:
  primary_key:
  - entity_id
  merge_keys:
  - entity_id
  hash_include: []

================================================================================
File: target.yaml
Path: entities\chembl\target.yaml
================================================================================
version: 1.0.0
provider: chembl
entity: target
pipeline:
    pipeline_name: chembl_target
    provider: chembl
    entity_type: target
    description: Extract biological targets from ChEMBL API
    business_primary_keys:
        - target_id
    batch_size: 1000
    sink:
        silver:
            partition_by:
                - target_type
        gold:
            mode: scd2
            scd_config:
                valid_from_col: _valid_from
                valid_to_col: _valid_to
                current_flag_col: _is_current
                version_col: _version
schema:
  content_hash:
    include: []
    exclude: []
  column_groups:
  - name: system
    fields:
    - entity_id
    - content_hash
    - _run_id
    - _run_type
    - _source_batch_id
    - _ingestion_ts
    - _index
  - name: business
    fields:
    - target_id
    - target_type
    - pref_name
    - taxonomy_id
    - organism
    - organism_class
    - species_group_flag
    - description
    - downgraded
    - target_components
    - cross_references
    - pipeline_stages
    - target_component_synonyms
    - component_accessions
    - component_descriptions
    - primary_component_id
    - component_ids
    - component_types
    - component_relationships
  - name: dq
    pattern: ^_dq_
  silver:
    include_groups:
    - system
    - business
    - dq
    exclude_fields: []
    alias_policy: preserve
  gold:
    include_groups:
    - system
    - business
    exclude_fields:
    - _dq_*
    - _source_batch_id
    - _index
    alias_policy: canonical
quality:
    version: 1.1.0
    provider: chembl
    entity: target
    entity_field_validations:
        -   field: target_id
            type: required
            nullable: false
            error_message: Target ChEMBL ID is required
        -   field: target_type
            type: enum
            allowed:
                - SINGLE PROTEIN
                - PROTEIN COMPLEX
                - PROTEIN FAMILY
                - SELECTIVITY GROUP
                - ORGANISM
                - TISSUE
                - CELL-LINE
                - SUBCELLULAR
                - UNKNOWN
                - CHIMERIC PROTEIN
                - PROTEIN-PROTEIN INTERACTION
                - NUCLEIC-ACID
                - METAL
                - LIPID
                - MACROMOLECULE
                - PHENOTYPE
                - ADMET
            nullable: true
            error_message: Invalid target_type value
        -   field: organism
            type: pattern
            pattern: ^[A-Z][a-z]+ [a-z]+.*$
            nullable: true
            error_message: organism should be in binomial nomenclature
        -   field: tax_id
            type: range
            min: 1
            max: 10000000
            nullable: true
    entity_cross_field_validations:
        -   name: target_identifiable
            fields:
                - target_id
                - pref_name
            condition: all_present
            error_message: Target must have ID and preferred name
    entity_conditional_validations: []
    key_nullability:
        -   field: target_id
            key_type: merge
            nullable: false
        -   field: target_type
            key_type: partition
            nullable: false
filters:
    version: 1.0.0
    provider: chembl
    entity: target
    input_filter:
        enabled: false
        source_path: data/input/target.csv
        column_name: target_chembl_id
        filter_field: target_id
        batch_size: 20
    extraction_params:
        target_type: SINGLE PROTEIN
        organism__isnull: false
        tax_id__isnull: false
    silver_filters:
        columns:
            target_type:
                - SINGLE PROTEIN
        required_fields:
            - target_id
            - pref_name
            - organism
            - target_type
    gold_filters:
        columns:
            target_type:
                - SINGLE PROTEIN
        list_lengths:
            component_accessions:
                min: 1
                max: 1
            component_ids:
                min: 1
        list_contains:
            component_types:
                values:
                    - PROTEIN
                mode: all
        required_fields:
            - pref_name
            - organism
contracts:
    primary_key:
        - target_id
    merge_keys:
        - target_id
    hash_include: []

================================================================================
File: target_component.yaml
Path: entities\chembl\target_component.yaml
================================================================================
version: 1.0.0
provider: chembl
entity: target_component
pipeline:
  pipeline_name: chembl_target_component
  provider: chembl
  entity_type: target_component
  description: ChEMBL Target Components (protein sequences, etc.)
  business_primary_keys:
  - component_id
  sink:
    silver:
      partition_by:
      - organism
    gold:
      mode: scd2
      scd_config:
        valid_from_col: _valid_from
        valid_to_col: _valid_to
        current_flag_col: _is_current
        version_col: _version
schema:
  content_hash:
    include: []
    exclude: []
  column_groups:
  - name: system
    fields:
    - entity_id
    - content_hash
    - _run_id
    - _run_type
    - _source_batch_id
    - _ingestion_ts
    - _index
  - name: business
    fields:
    - component_id
    - accession
    - component_type
    - description
    - organism
    - taxonomy_id
    - target_component_synonyms
    - target_component_xrefs
    - protein_classifications
    - protein_classification_id
    - protein_classification_ids
  - name: dq
    pattern: ^_dq_
  silver:
    include_groups:
    - system
    - business
    - dq
    exclude_fields: []
    alias_policy: preserve
  gold:
    include_groups:
    - system
    - business
    exclude_fields:
    - _dq_*
    - _source_batch_id
    - _index
    alias_policy: canonical
quality:
  version: 1.0.0
  provider: chembl
  entity: target_component
  entity_field_validations:
  - field: component_id
    type: range
    min: 1
    nullable: false
    error_message: Component ID is required and must be positive
  - field: component_type
    type: enum
    allowed:
    - PROTEIN
    - DNA
    - RNA
    nullable: true
  - field: accession
    type: pattern
    pattern: ^[A-Z0-9]{6,10}$
    nullable: true
    error_message: accession should be UniProt format (6-10 alphanumeric chars)
  - field: tax_id
    type: range
    min: 1
    max: 10000000
    nullable: true
    error_message: Taxonomy ID must be between 1 and 10,000,000
  entity_cross_field_validations:
  - name: component_identifiable
    fields:
    - component_id
    - accession
    condition: any_present
    error_message: Component must have ID or accession
  entity_conditional_validations: []
  key_nullability:
  - field: component_id
    key_type: merge
    nullable: false
  - field: organism
    key_type: partition
    nullable: false
filters:
  version: 1.0.0
  provider: chembl
  entity: target_component
  input_filter:
    enabled: true
    source_path: data/input/target_component.csv
    column_name: component_id
    filter_field: component_id
    batch_size: 100
  silver_filters:
    required_fields:
    - component_id
    - organism
  gold_filters:
    columns:
      component_type:
      - PROTEIN
    required_fields:
    - accession
contracts:
  primary_key:
  - component_id
  merge_keys:
  - component_id
  hash_include: []

================================================================================
File: tissue.yaml
Path: entities\chembl\tissue.yaml
================================================================================
version: 1.0.0
provider: chembl
entity: tissue
pipeline:
  pipeline_name: chembl_tissue
  provider: chembl
  entity_type: tissue
  version: 1.0.0
  description: Extract tissues from ChEMBL API
  business_primary_keys:
  - tissue_id
  sink:
    gold:
      mode: scd2
      scd_config:
        valid_from_col: _valid_from
        valid_to_col: _valid_to
        current_flag_col: _is_current
        version_col: _version
schema:
  content_hash:
    include: []
    exclude: []
  column_groups:
  - name: system
    fields:
    - entity_id
    - content_hash
    - _run_id
    - _run_type
    - _source
    - _ingestion_ts
  - name: identifiers
    fields:
    - tissue_id
  - name: business
    fields:
    - pref_name
    - bto_id
    - caloha_id
    - efo_id
    - uberon_id
  silver:
    include_groups:
    - system
    - identifiers
    - business
  gold:
    include_groups:
    - system
    - identifiers
    - business
quality:
  version: 1.0.0
  provider: chembl
  entity: tissue
  entity_field_validations:
  - field: tissue_id
    type: pattern
    pattern: ^CHEMBL\d+$
    nullable: false
    error_message: tissue_id must match CHEMBL format
  - field: pref_name
    type: pattern
    pattern: ^.{1,200}$
    nullable: false
    error_message: pref_name is required and must not exceed 200 chars
  - field: bto_id
    type: pattern
    pattern: ^BTO:\d{7}$
    nullable: true
    error_message: bto_id must match BTO format (BTO:0000000)
  - field: caloha_id
    type: pattern
    pattern: ^TS-\d{4}$
    nullable: true
    error_message: caloha_id must match CALIPHO format (TS-0000)
  - field: efo_id
    type: pattern
    pattern: ^EFO:\d{7}$
    nullable: true
    error_message: efo_id must match EFO format (EFO:0000000)
  - field: uberon_id
    type: pattern
    pattern: ^UBERON:\d{7}$
    nullable: true
    error_message: uberon_id must match UBERON format (UBERON:0000000)
  entity_cross_field_validations: []
  entity_conditional_validations: []
  key_nullability:
  - field: tissue_id
    key_type: merge
    nullable: false
filters:
  version: 1.0.0
  provider: chembl
  entity: tissue
  input_filter:
    enabled: false
  silver_filters:
    required_fields:
    - tissue_id
    - pref_name
  gold_filters:
    required_fields:
    - tissue_id
contracts:
  primary_key:
  - tissue_id
  merge_keys:
  - tissue_id
  hash_include: []

================================================================================
File: publication.yaml
Path: entities\crossref\publication.yaml
================================================================================
version: 1.0.0
provider: crossref
entity: publication
pipeline:
  pipeline_name: crossref_publication
  provider: crossref
  entity_type: publication
  description: Enrich publication records with CrossRef metadata via DOI resolution
  loading_strategy: full_scan_only
  business_primary_keys:
  - doi
  sink:
    gold:
      mode: scd2
      scd_config:
        valid_from_col: _valid_from
        valid_to_col: _valid_to
        current_flag_col: _is_current
        version_col: _version
schema:
  column_groups:
  - name: system
    fields:
    - entity_id
    - content_hash
    - _run_id
    - _run_type
    - _source_batch_id
    - _source
    - _ingestion_ts
    - _index
    - _lookup_method
    - _original_id
  - name: identifiers
    fields:
    - publication_doi
    - alternative_id
  - name: title
    fields:
    - title
  - name: authors
    fields:
    - authors
  - name: journal
    fields:
    - journal
    - journal_name_short
  - name: issn
    fields:
    - issn
    - issn_list
    - issn_print
    - issn_electronic
  - name: year
    fields:
    - publication_year
  - name: dates
    fields:
    - publication_date
    - published
    - published_online
    - published_print
  - name: pagination
    fields:
    - volume
    - issue
    - page_first
    - page_last
  - name: citations
    fields:
    - citations_received
    - citations_made
  - name: subjects
    fields:
    - subject_keywords
  - name: language
    fields:
    - language
  - name: publisher
    fields:
    - publisher
  - name: doc_type
    fields:
    - publication_type
    - publication_type_unified
    - publication_subclass
    - publication_class
  - name: content_domain
    fields:
    - content_domain_domains
    - content_domain_crossmark_restriction
  - name: license
    fields:
    - license_url
  - name: dq
    pattern: ^_dq_
  field_aliases:
    short_container_title: journal_name_short
    citation_count: citations_received
    reference_count: citations_made
    subjects: subject_keywords
    source_type: publication_type
  silver:
    include_groups:
    - system
    - identifiers
    - title
    - authors
    - journal
    - issn
    - year
    - dates
    - pagination
    - citations
    - subjects
    - language
    - publisher
    - doc_type
    - content_domain
    - license
    - dq
  gold:
    include_groups:
    - system
    - identifiers
    - title
    - authors
    - journal
    - year
    - pagination
    - citations
    - publisher
    - doc_type
    exclude_fields:
    - _dq_*
    - _source_batch_id
    - _index
    - _lookup_method
    - _original_id
quality:
  version: 1.0.0
  provider: crossref
  entity: publication
  entity_field_validations:
  - field: doi
    type: pattern
    pattern: ^10\.\d{4,}/\S+$
    nullable: false
    error_message: DOI is required and must match format 10.XXXX/suffix (no whitespace)
  - field: title
    type: max_length
    max_length: 2000
    nullable: true
    error_message: Title must not exceed 2000 characters
  - field: title
    type: not_null
    nullable: true
    severity: warn
    error_message: "Missing title \u2014 record will be filtered before Gold"
  - field: title
    type: pattern
    pattern: \S
    nullable: true
    severity: warn
    error_message: Title should not be empty or whitespace-only
  - field: publication_year
    type: range
    min: 1950
    nullable: true
    severity: warn
    error_message: "Publication year before 1950 \u2014 will be filtered at Gold stage"
  - field: publication_type
    type: enum
    allowed:
    - journal-article
    - book-chapter
    - proceedings-article
    - posted-content
    - book
    - report
    - dataset
    - standard
    nullable: true
  - field: citations_received
    type: range
    min: 0
    nullable: true
    error_message: Citation count must be non-negative
  - field: citations_received
    type: range
    min: 0
    max: 10000000
    nullable: true
    severity: warn
    error_message: Unusually high citation count
  - field: citations_made
    type: range
    min: 0
    nullable: true
    error_message: Reference count must be non-negative
  entity_cross_field_validations:
  - name: publication_identifiable
    fields:
    - doi
    - title
    condition: all_present
    error_message: Publication must have DOI and title
  entity_conditional_validations:
  - name: article_requires_title
    condition_field: publication_type
    condition_value:
    - journal-article
    - proceedings-article
    condition_operator: in
    then_validations:
    - field: title
      type: not_null
      nullable: false
      error_message: Journal and proceedings articles must have a title
  key_nullability:
  - field: doi
    key_type: merge
    nullable: false
filters:
  version: 1.0.0
  provider: crossref
  entity: publication
  input_filter:
    enabled: true
    source_path: data/input/dois.csv
    column_name: doi
    filter_field: doi
    batch_size: 50
    fallback_column: title
  silver_filters:
    required_fields:
    - doi
    - title
  gold_filters:
    ranges:
      publication_year:
        min: 1950
        max: 2050
    required_fields:
    - doi
    - title
contracts:
  primary_key:
  - doi
  merge_keys:
  - doi
  hash_include: []

================================================================================
File: publication.yaml
Path: entities\openalex\publication.yaml
================================================================================
version: 1.0.0
provider: openalex
entity: publication
pipeline:
  pipeline_name: openalex_publication
  provider: openalex
  entity_type: publication
  description: Batch DOI resolution via OpenAlex with title fallback
  loading_strategy: full_scan_only
  business_primary_keys:
  - openalex_id
  source:
    email: ${BIOETL_OPENALEX_EMAIL}
  sink:
    gold:
      mode: scd2
      scd_config:
        valid_from_col: _valid_from
        valid_to_col: _valid_to
        current_flag_col: _is_current
        version_col: _version
schema:
  column_groups:
  - name: system
    fields:
    - entity_id
    - content_hash
    - _run_id
    - _run_type
    - _source_batch_id
    - _source
    - _ingestion_ts
    - _index
    - _lookup_method
    - _original_id
  - name: identifiers
    fields:
    - openalex_id
    - publication_doi
    - publication_pmid
    - mag_id
  - name: title
    fields:
    - title
  - name: abstract
    fields:
    - abstract
  - name: authors
    fields:
    - authors
    - author_openalex_ids
    - author_orcids
  - name: affiliations
    fields:
    - affiliation_list
  - name: institutions
    fields:
    - institution_ids
    - institution_country_codes
    - ror_ids
  - name: journal
    fields:
    - journal
    - issn
  - name: year
    fields:
    - publication_year
  - name: dates
    fields:
    - publication_date
  - name: pagination
    fields:
    - volume
    - issue
    - page_first
    - page_last
  - name: citations
    fields:
    - citations_received
    - citations_made
    - fwci
  - name: open_access
    fields:
    - is_oa
    - oa_status
  - name: subjects
    fields:
    - subject_topics
    - primary_topic
    - subject_keywords
    - subject_mesh
  - name: publisher
    fields:
    - publisher
  - name: funding
    fields:
    - grants
  - name: doc_type
    fields:
    - publication_type
    - publication_type_unified
    - publication_subclass
    - publication_class
  - name: quality
    fields:
    - is_retracted
  - name: language
    fields:
    - language
  - name: dq
    pattern: ^_dq_
  field_aliases:
    affiliations: affiliation_list
    citation_count: citations_received
    reference_count: citations_made
    topics: subject_topics
    keywords: subject_keywords
    mesh_terms: subject_mesh
    source_type: publication_type
  silver:
    include_groups:
    - system
    - identifiers
    - title
    - abstract
    - authors
    - affiliations
    - institutions
    - journal
    - year
    - dates
    - pagination
    - citations
    - open_access
    - subjects
    - publisher
    - funding
    - doc_type
    - quality
    - language
    - dq
  gold:
    include_groups:
    - system
    - identifiers
    - title
    - abstract
    - authors
    - journal
    - year
    - citations
    - open_access
    - subjects
    - quality
    exclude_fields:
    - _dq_*
    - _source_batch_id
    - _index
    - _lookup_method
    - _original_id
quality:
  version: 1.0.0
  provider: openalex
  entity: publication
  entity_field_validations:
  - field: openalex_id
    type: pattern
    pattern: ^W\d+$
    nullable: false
    error_message: OpenAlex ID is required and must start with W followed by digits
  - field: pmid
    type: range
    min: 1
    max: 10000000000
    nullable: true
    error_message: PubMed ID must be a positive integer
  - field: doi
    type: pattern
    pattern: ^10\.\d{4,}/\S+$
    nullable: true
    error_message: DOI must match format 10.XXXX/suffix (no whitespace)
  - field: title
    type: max_length
    max_length: 2000
    nullable: true
    error_message: Title must not exceed 2000 characters
  - field: title
    type: not_null
    nullable: true
    severity: warn
    error_message: "Missing title \u2014 record will be filtered before Gold"
  - field: title
    type: pattern
    pattern: \S
    nullable: true
    severity: warn
    error_message: Title should not be empty or whitespace-only
  - field: publication_year
    type: range
    min: 1950
    nullable: true
    severity: warn
    error_message: "Publication year before 1950 \u2014 will be filtered at Gold stage"
  - field: publication_type
    type: enum
    allowed:
    - journal-article
    - book-chapter
    - book
    - dataset
    - dissertation
    - editorial
    - letter
    - review
    - preprint
    - other
    nullable: true
  - field: citations_received
    type: range
    min: 0
    nullable: true
    error_message: Citation count must be non-negative
  - field: citations_received
    type: range
    min: 0
    max: 10000000
    nullable: true
    severity: warn
    error_message: Unusually high citation count
  - field: fwci
    type: range
    min: 0
    nullable: true
    error_message: FWCI must be non-negative
  - field: citations_made
    type: range
    min: 0
    nullable: true
    error_message: Reference count must be non-negative
  entity_cross_field_validations:
  - name: publication_identifiable
    fields:
    - openalex_id
    - title
    condition: all_present
    error_message: Publication must have OpenAlex ID and title
  entity_conditional_validations:
  - name: article_requires_title
    condition_field: publication_type
    condition_value:
    - journal-article
    - review
    condition_operator: in
    then_validations:
    - field: title
      type: not_null
      nullable: false
      error_message: Articles and reviews must have a title
  key_nullability:
  - field: openalex_id
    key_type: merge
    nullable: false
filters:
  version: 1.0.0
  provider: openalex
  entity: publication
  input_filter:
    enabled: true
    source_path: data/input/dois.csv
    column_name: doi
    filter_field: doi
    batch_size: 50
    fallback_column: title
  silver_filters:
    required_fields:
    - openalex_id
    - title
  gold_filters:
    ranges:
      publication_year:
        min: 1950
        max: 2050
    required_fields:
    - openalex_id
    - title
contracts:
  primary_key:
  - openalex_id
  merge_keys:
  - openalex_id
  hash_include: []

================================================================================
File: compound.yaml
Path: entities\pubchem\compound.yaml
================================================================================
version: 1.0.0
provider: pubchem
entity: compound
pipeline:
  pipeline_name: pubchem_compound
  provider: pubchem
  entity_type: compound
  description: Pipeline for ingesting PubChem compounds
  business_primary_keys:
  - molecule_id
  sink:
    silver:
      partition_by: []
    gold:
      mode: scd2
      scd_config:
        valid_from_col: _valid_from
        valid_to_col: _valid_to
        current_flag_col: _is_current
        version_col: _version
schema:
  content_hash:
    include: []
    exclude: []
  column_groups:
  - name: system
    fields:
    - entity_id
    - content_hash
    - _run_id
    - _run_type
    - _source_batch_id
    - _ingestion_ts
    - _index
  - name: business
    fields:
    - molecule_id
    - canonical_smiles
    - isomeric_smiles
    - inchi
    - inchi_key
    - molecular_formula
    - iupac_name
    - molecular_weight
    - exact_mass
    - monoisotopic_mass
    - xlogp
    - tpsa
    - complexity
    - charge
    - heavy_atom_count
    - h_bond_donor_count
    - h_bond_acceptor_count
    - rotatable_bond_count
    - atom_stereo_count
    - defined_atom_stereo_count
    - undefined_atom_stereo_count
    - bond_stereo_count
    - defined_bond_stereo_count
    - undefined_bond_stereo_count
    - isotope_atom_count
    - covalent_unit_count
    - volume_3d
    - conformer_count_3d
    - feature_acceptor_count_3d
    - feature_donor_count_3d
    - feature_anion_count_3d
    - feature_cation_count_3d
    - feature_ring_count_3d
    - feature_hydrophobe_count_3d
    - effective_rotor_count_3d
    - conformer_rmsd_3d
    - x_steric_quadrupole_3d
    - y_steric_quadrupole_3d
    - z_steric_quadrupole_3d
    - feature_count_3d
  - name: dq
    pattern: ^_dq_
  silver:
    include_groups:
    - system
    - business
    - dq
    exclude_fields: []
    alias_policy: preserve
  gold:
    include_groups:
    - system
    - business
    exclude_fields:
    - _dq_*
    - _source_batch_id
    - _index
    alias_policy: canonical
quality:
  version: 1.1.0
  provider: pubchem
  entity: compound
  entity_field_validations:
  - field: molecule_id
    type: required
    nullable: false
    error_message: CID is required
  - field: molecular_formula
    type: pattern
    pattern: ^[A-Z][A-Za-z0-9]*$
    nullable: true
    error_message: Molecular formula must start with uppercase letter
  - field: molecular_weight
    type: range
    min: 10
    max: 10000
    nullable: true
    error_message: Molecular weight must be between 10 and 10000 Da
  - field: canonical_smiles
    type: custom
    validator: smiles_validator
    nullable: true
  - field: isomeric_smiles
    type: custom
    validator: smiles_validator
    nullable: true
  - field: xlogp
    type: range
    min: -20
    max: 30
    nullable: true
  - field: tpsa
    type: range
    min: 0
    max: 1000
    nullable: true
  - field: h_bond_donor_count
    type: range
    min: 0
    max: 50
    nullable: true
  - field: h_bond_acceptor_count
    type: range
    min: 0
    max: 50
    nullable: true
  entity_cross_field_validations:
  - name: structure_present
    fields:
    - canonical_smiles
    - inchi
    - inchi_key
    condition: any_present
    error_message: At least one structure identifier required
  entity_conditional_validations: []
  key_nullability:
  - field: molecule_id
    key_type: merge
    nullable: false
filters:
  version: 1.0.0
  provider: pubchem
  entity: compound
  input_filter:
    enabled: true
    source_path: data/input/molecule.csv
    column_name: canonical_smiles
    filter_field: smiles
    batch_size: 1
  silver_filters:
    required_fields:
    - molecule_id
  gold_filters:
    required_fields:
    - molecule_id
    - molecular_formula
    columns: {}
contracts:
  primary_key:
  - molecule_id
  merge_keys:
  - molecule_id
  hash_include: []

================================================================================
File: publication.yaml
Path: entities\pubmed\publication.yaml
================================================================================
version: 1.0.0
provider: pubmed
entity: publication
pipeline:
  pipeline_name: pubmed_publication
  provider: pubmed
  entity_type: publication
  description: Extract publication metadata from PubMed via Entrez API
  loading_strategy: full_scan_only
  business_primary_keys:
  - pmid
  source:
    email: ${BIOETL_PUBMED_EMAIL}
    api_key: ${BIOETL_PUBMED_API_KEY}
  sink:
    gold:
      mode: scd2
      scd_config:
        valid_from_col: _valid_from
        valid_to_col: _valid_to
        current_flag_col: _is_current
        version_col: _version
schema:
  column_groups:
  - name: system
    fields:
    - entity_id
    - content_hash
    - _run_id
    - _run_type
    - _source_batch_id
    - _source
    - _ingestion_ts
    - _index
    - _lookup_method
    - _original_id
  - name: identifiers
    fields:
    - pmid
    - pmc_id
    - doi
    - nlm_unique_id
  - name: title
    fields:
    - title
  - name: abstract
    fields:
    - abstract
    - abstract_structured
  - name: authors
    fields:
    - authors
    - author_count
    - authors_with_affiliations
  - name: affiliations
    fields:
    - affiliation_list
    - affiliation_structured
  - name: journal
    fields:
    - journal
    - journal_name
    - journal_name_short
    - journal_iso_abbrev
    - issn
    - journal_issn_type
  - name: year
    fields:
    - publication_year
  - name: dates
    fields:
    - publication_date
    - pub_date
    - pub_day
    - pub_month
    - date_completed
    - date_revised
  - name: pagination
    fields:
    - volume
    - issue
    - page_first
    - page_last
    - page_range
    - medline_pgn
  - name: citations
    fields:
    - citations_made
    - citation_subset
  - name: subjects
    fields:
    - subject_mesh
    - mesh_heading_count
    - subject_keywords
    - keyword_count
    - publication_types
    - publication_type_list
  - name: funding
    fields:
    - grant_count
  - name: chemicals
    fields:
    - chemical_count
  - name: doc_type
    fields:
    - publication_type
    - publication_type_unified
    - publication_subclass
    - publication_class
  - name: language
    fields:
    - language
  - name: misc
    fields:
    - country
    - publication_status
  - name: dq
    pattern: ^_dq_
  field_aliases:
    affiliations: affiliation_list
    structured_affiliations: affiliation_structured
    journal_title: journal_name
    journal_abbrev: journal_name_short
    pages: page_range
    reference_count: citations_made
    mesh_terms: subject_mesh
    keywords: subject_keywords
  silver:
    include_groups:
    - system
    - identifiers
    - title
    - abstract
    - authors
    - affiliations
    - journal
    - year
    - dates
    - pagination
    - citations
    - subjects
    - funding
    - chemicals
    - doc_type
    - language
    - misc
    - dq
  gold:
    include_groups:
    - system
    - identifiers
    - title
    - abstract
    - authors
    - affiliations
    - journal
    - year
    - subjects
    exclude_fields:
    - _dq_*
    - _source_batch_id
    - _index
    - _lookup_method
    - _original_id
quality:
  version: 1.0.0
  provider: pubmed
  entity: publication
  entity_field_validations:
  - field: pmid
    type: range
    min: 1
    max: 10000000000
    nullable: false
    error_message: PMID is required and must be a positive integer
  - field: title
    type: max_length
    max_length: 2000
    nullable: true
    error_message: Title must not exceed 2000 characters
  - field: title
    type: not_null
    nullable: true
    severity: warn
    error_message: "Missing title \u2014 record will be filtered before Gold"
  - field: title
    type: pattern
    pattern: \S
    nullable: true
    severity: warn
    error_message: Title should not be empty or whitespace-only
  - field: doi
    type: pattern
    pattern: ^10\.\d{4,}/\S+$
    nullable: true
    error_message: DOI must match format 10.XXXX/suffix (no whitespace)
  - field: publication_year
    type: range
    min: 1950
    nullable: true
    severity: warn
    error_message: "Publication year before 1950 \u2014 will be filtered at Gold stage"
  - field: publication_type
    type: enum
    allowed:
    - journal-article
    - review
    - letter
    - editorial
    - clinical-trial
    - meta-analysis
    - case-reports
    - comparative-study
    - evaluation-study
    nullable: true
  - field: citations_received
    type: range
    min: 0
    nullable: true
    error_message: Citation count must be non-negative
  - field: citations_received
    type: range
    min: 0
    max: 10000000
    nullable: true
    severity: warn
    error_message: Unusually high citation count
  - field: citations_made
    type: range
    min: 0
    nullable: true
    error_message: Reference count must be non-negative
  entity_cross_field_validations:
  - name: publication_identifiable
    fields:
    - pmid
    - title
    condition: all_present
    error_message: Publication must have PMID and title
  - name: has_identifier
    fields:
    - pmid
    - doi
    - pmc_id
    condition: any_present
    error_message: At least one identifier required
  entity_conditional_validations: []
  key_nullability:
  - field: pmid
    key_type: merge
    nullable: false
filters:
  version: 1.0.0
  provider: pubmed
  entity: publication
  input_filter:
    enabled: true
    source_path: data/input/pubmed.csv
    column_name: pubmed_id
    filter_field: pmid
    batch_size: 100
    fallback_column: title
  silver_filters:
    required_fields:
    - pmid
    - title
  gold_filters:
    ranges:
      publication_year:
        min: 1950
        max: 2050
    required_fields:
    - pmid
    - title
    columns: {}
contracts:
  primary_key:
  - pmid
  merge_keys:
  - pmid
  hash_include: []

================================================================================
File: publication.yaml
Path: entities\semanticscholar\publication.yaml
================================================================================
version: 1.0.0
provider: semanticscholar
entity: publication
pipeline:
  pipeline_name: semanticscholar_publication
  provider: semanticscholar
  entity_type: publication
  description: Batch DOI resolution via Semantic Scholar with title fallback
  loading_strategy: full_scan_only
  business_primary_keys:
  - paper_id
  sink:
    gold:
      mode: scd2
      scd_config:
        valid_from_col: _valid_from
        valid_to_col: _valid_to
        current_flag_col: _is_current
        version_col: _version
schema:
  column_groups:
  - name: system
    fields:
    - entity_id
    - content_hash
    - _run_id
    - _run_type
    - _source_batch_id
    - _source
    - _ingestion_ts
    - _index
    - _lookup_method
    - _original_id
  - name: identifiers
    fields:
    - paper_id
    - publication_doi
    - publication_pmid
    - corpus_id
    - dblp_id
  - name: title
    fields:
    - title
  - name: abstract
    fields:
    - abstract
    - tldr
  - name: authors
    fields:
    - author_s2_ids
    - author_orcids
    - author_h_indices
  - name: affiliations
    fields:
    - affiliation_list
  - name: journal
    fields:
    - journal
  - name: year
    fields:
    - publication_year
  - name: dates
    fields:
    - publication_date
  - name: pagination
    fields:
    - volume
    - issue
    - page_first
    - page_last
    - page_range
  - name: citations
    fields:
    - citations_received
    - citations_made
    - influential_citation_count
    - citation_contexts
  - name: subjects
    fields:
    - subject_fields
    - publication_types
  - name: doc_type
    fields:
    - publication_type
    - publication_type_unified
    - publication_subclass
    - publication_class
  - name: open_access
    fields:
    - is_oa
    - oa_status
    - open_access_url
  - name: dq
    pattern: ^_dq_
  field_aliases:
    affiliations: affiliation_list
    pages: page_range
    citation_count: citations_received
    reference_count: citations_made
    fields_of_study: subject_fields
  silver:
    include_groups:
    - system
    - identifiers
    - title
    - abstract
    - authors
    - affiliations
    - journal
    - year
    - dates
    - pagination
    - citations
    - subjects
    - doc_type
    - open_access
    - dq
  gold:
    include_groups:
    - system
    - identifiers
    - title
    - abstract
    - authors
    - journal
    - year
    - doc_type
    - citations
    - open_access
    exclude_fields:
    - _dq_*
    - _source_batch_id
    - _index
    - _lookup_method
    - _original_id
quality:
  version: 1.0.0
  provider: semanticscholar
  entity: publication
  entity_field_validations:
  - field: paper_id
    type: pattern
    pattern: ^[a-f0-9]{40}$
    nullable: false
    error_message: paper_id is required and must be a 40-char hex string
  - field: pmid
    type: range
    min: 1
    max: 10000000000
    nullable: true
    error_message: PubMed ID must be a positive integer
  - field: doi
    type: pattern
    pattern: ^10\.\d{4,}/\S+$
    nullable: true
    error_message: DOI must match format 10.XXXX/suffix (no whitespace)
  - field: title
    type: max_length
    max_length: 2000
    nullable: true
    error_message: Title must not exceed 2000 characters
  - field: title
    type: not_null
    nullable: true
    severity: warn
    error_message: "Missing title \u2014 record will be filtered before Gold"
  - field: title
    type: pattern
    pattern: \S
    nullable: true
    severity: warn
    error_message: Title should not be empty or whitespace-only
  - field: publication_year
    type: range
    min: 1950
    nullable: true
    severity: warn
    error_message: "Publication year before 1950 \u2014 will be filtered at Gold stage"
  - field: publication_type
    type: pattern
    pattern: ^[a-z][a-z0-9-]+(\|[a-z][a-z0-9-]+)*$
    nullable: true
    severity: warn
    error_message: Unexpected publication_type format after normalization
  - field: citations_received
    type: range
    min: 0
    max: 10000000
    nullable: true
    severity: warn
    error_message: Unusually high citation count
  - field: citations_made
    type: range
    min: 0
    nullable: true
    error_message: Reference count must be non-negative
  - field: influential_citation_count
    type: range
    min: 0
    nullable: true
    error_message: Influential citation count must be non-negative
  entity_cross_field_validations:
  - name: publication_identifiable
    fields:
    - paper_id
    - title
    condition: all_present
    error_message: Publication must have paper_id and title
  entity_conditional_validations:
  - name: journal_article_requires_title
    condition_field: publication_type
    condition_value: journal-article
    condition_operator: eq
    then_validations:
    - field: title
      type: not_null
      nullable: false
      error_message: Journal articles must have a title
  key_nullability:
  - field: paper_id
    key_type: merge
    nullable: false
filters:
  version: 1.0.0
  provider: semanticscholar
  entity: publication
  input_filter:
    enabled: true
    source_path: data/input/dois.csv
    column_name: doi
    filter_field: doi
    batch_size: 100
    fallback_column: title
  silver_filters:
    required_fields:
    - paper_id
    - title
  gold_filters:
    ranges:
      publication_year:
        min: 1950
        max: 2050
    required_fields:
    - paper_id
    - title
contracts:
  primary_key:
  - paper_id
  merge_keys:
  - paper_id
  hash_include: []

================================================================================
File: idmapping.yaml
Path: entities\uniprot\idmapping.yaml
================================================================================
version: 1.0.0
provider: uniprot
entity: idmapping
pipeline:
  pipeline_name: uniprot_idmapping
  provider: uniprot
  entity_type: idmapping
  version: 1.1.0
  description: Maps ChEMBL target IDs to UniProt accessions via UniProt ID Mapping
    API
  business_primary_keys:
  - target_id
  source:
    api:
      base_url: https://rest.uniprot.org
      from_db: ChEMBL
      to_db: UniProtKB
  sink:
    gold:
      mode: scd2
      scd_config:
        valid_from_col: _valid_from
        valid_to_col: _valid_to
        current_flag_col: _is_current
        version_col: _version
schema:
  content_hash:
    include: []
    exclude: []
  column_groups:
  - name: system
    fields:
    - entity_id
    - content_hash
    - _run_id
    - _run_type
    - _source_batch_id
    - _ingestion_ts
    - _index
  - name: business
    fields:
    - target_id
    - uniprot_accession
    - mapping_status
    - uniprot_entry_name
    - organism_scientific
    - organism_common
    - taxonomy_id
    - protein_name
    - gene_primary
    - sequence_length
    - sequence_mass
    - reviewed
    - annotation_score
    - all_mappings
  - name: dq
    pattern: ^_dq_
  silver:
    include_groups:
    - system
    - business
    - dq
    exclude_fields: []
    alias_policy: preserve
  gold:
    include_groups:
    - system
    - business
    exclude_fields:
    - _dq_*
    - _source_batch_id
    - _index
    alias_policy: canonical
quality:
  version: 1.0.0
  provider: uniprot
  entity: idmapping
  thresholds:
    soft_fail: 0.3
    hard_fail: 0.8
  entity_field_validations:
  - field: target_id
    type: pattern
    pattern: ^CHEMBL\d+$
    nullable: false
    error_message: target_id must match CHEMBL format
  - field: mapping_status
    type: enum
    allowed:
    - found
    - not_found
    - error
    nullable: false
    error_message: mapping_status is required and must be valid
  - field: uniprot_accession
    type: pattern
    pattern: ^[A-Z0-9]{6,10}$
    nullable: true
    error_message: UniProt accession must be 6-10 alphanumeric chars
  entity_cross_field_validations: []
  entity_conditional_validations:
  - name: found_has_accession
    condition_field: mapping_status
    condition_value: found
    condition_operator: eq
    then_validations:
    - field: uniprot_accession
      type: pattern
      pattern: ^[A-Z0-9]{6,10}$
      nullable: false
      error_message: Found mappings must have UniProt accession
  key_nullability:
  - field: target_id
    key_type: merge
    nullable: false
filters:
  version: 1.0.0
  provider: uniprot
  entity: idmapping
  input_filter:
    enabled: false
    source_path: data/input/target.csv
    column_name: target_chembl_id
    filter_field: target_id
    batch_size: 100
  silver_filters:
    required_fields:
    - target_id
    - mapping_status
  gold_filters:
    required_fields:
    - target_id
    - mapping_status
contracts:
  primary_key:
  - target_id
  merge_keys:
  - target_id
  hash_include: []

================================================================================
File: protein.yaml
Path: entities\uniprot\protein.yaml
================================================================================
version: 1.0.0
provider: uniprot
entity: protein
pipeline:
  pipeline_name: uniprot_protein
  provider: uniprot
  entity_type: protein
  description: Pipeline for ingesting UniProt proteins
  business_primary_keys:
  - accession
  sink:
    silver:
      partition_by:
      - organism_scientific
    gold:
      mode: scd2
      scd_config:
        valid_from_col: _valid_from
        valid_to_col: _valid_to
        current_flag_col: _is_current
        version_col: _version
schema:
  content_hash:
    include: []
    exclude: []
  column_groups:
  - name: system
    fields:
    - entity_id
    - content_hash
    - _run_id
    - _run_type
    - _source_batch_id
    - _ingestion_ts
    - _index
  - name: business
    fields:
    - accession
    - entry_name
    - entry_type
    - secondary_accessions
    - protein_name
    - protein_short_names
    - protein_alternative_names
    - protein_ec_numbers
    - flag
    - gene_primary
    - gene_synonyms
    - gene_orf_names
    - organism_scientific
    - organism_common
    - taxonomy_id
    - lineage
    - sequence
    - sequence_length
    - sequence_mass
    - sequence_checksum
    - sequence_modified
    - entry_version
    - entry_created
    - entry_modified
    - reviewed
    - protein_existence
    - annotation_score
    - function_comment
    - catalytic_activity
    - activity_regulation
    - subunit
    - pathway
    - subcellular_location
    - tissue_specificity
    - alternative_products
    - disease_involvement
    - pharmaceutical_use
    - similarity_comment
    - caution
    - cofactors
    - biophysicochemical_properties
    - induction
    - go_terms
    - drugbank_ids
    - chembl_ids
    - guidetopharmacology_ids
    - pdb_xrefs
    - interpro_xrefs
    - pfam_xrefs
    - reactome_xrefs
    - superkingdom
    - phylum
    - genus
    - molecular_function
    - cellular_component
    - features_json
    - domains
    - binding_sites
    - active_sites
    - keywords
    - topology
    - transmembrane
    - intramembrane
    - signal_peptide
    - propeptide
    - glycosylation
    - lipidation
    - disulfide_bond
    - modified_residue
    - phosphorylation
    - acetylation
    - ubiquitination
    - isoform_names
    - isoform_ids
    - isoform_synonyms
    - reactions
    - reaction_ec_numbers
    - cross_reference_count
    - feature_count
    - keyword_count
    - publication_count
    - isoform_count
  - name: dq
    pattern: ^_dq_
  silver:
    include_groups:
    - system
    - business
    - dq
    exclude_fields: []
    alias_policy: preserve
  gold:
    include_groups:
    - system
    - business
    exclude_fields:
    - _dq_*
    - _source_batch_id
    - _index
    alias_policy: canonical
quality:
  version: 1.0.0
  provider: uniprot
  entity: protein
  entity_field_validations:
  - field: accession
    type: pattern
    pattern: ^[A-Z0-9]{6,10}$
    nullable: false
    error_message: UniProt accession must be 6-10 alphanumeric chars
  - field: entry_name
    type: pattern
    pattern: ^[A-Z0-9_]+$
    nullable: true
    error_message: Entry name must be alphanumeric with underscores
  - field: organism_scientific
    type: pattern
    pattern: ^[A-Z][a-z]+ [a-z]+.*$
    nullable: true
    error_message: Organism should be in binomial nomenclature
  - field: taxonomy_id
    type: range
    min: 1
    max: 10000000
    nullable: true
    error_message: Taxonomy ID must be positive
  - field: sequence_length
    type: range
    min: 1
    max: 100000
    nullable: true
    error_message: Sequence length must be between 1 and 100,000
  - field: sequence_mass
    type: range
    min: 100
    max: 10000000
    nullable: true
    error_message: Molecular mass must be between 100 and 10,000,000 Da
  - field: annotation_score
    type: range
    min: 1
    max: 5
    nullable: true
    error_message: Annotation score must be between 1 and 5
  - field: protein_existence
    type: range
    min: 1
    max: 5
    nullable: true
    error_message: Protein existence level must be between 1 and 5
  - field: go_terms
    type: not_empty_list
    nullable: true
    error_message: GO terms list cannot be empty if present
  - field: pdb_xrefs
    type: not_empty_list
    nullable: true
    error_message: PDB xrefs list cannot be empty if present
  - field: molecular_function
    type: pattern
    pattern: ^\[.*\]$
    nullable: true
    error_message: molecular_function must be JSON array
  - field: cellular_component
    type: pattern
    pattern: ^\[.*\]$
    nullable: true
    error_message: cellular_component must be JSON array
  - field: isoform_ids
    type: pattern
    pattern: ^\[.*\]$
    nullable: true
    error_message: isoform_ids must be JSON array
  - field: isoform_names
    type: pattern
    pattern: ^\[.*\]$
    nullable: true
    error_message: isoform_names must be JSON array
  - field: isoform_synonyms
    type: pattern
    pattern: ^\[.*\]$
    nullable: true
    error_message: isoform_synonyms must be JSON array
  - field: reactions
    type: pattern
    pattern: ^\[.*\]$
    nullable: true
    error_message: reactions must be JSON array
  - field: reaction_ec_numbers
    type: pattern
    pattern: ^\[.*\]$
    nullable: true
    error_message: reaction_ec_numbers must be JSON array
  entity_cross_field_validations:
  - name: protein_identifiable
    fields:
    - accession
    - entry_name
    condition: all_present
    error_message: Protein must have accession and entry name
  entity_conditional_validations: []
  key_nullability:
  - field: accession
    key_type: merge
    nullable: false
  - field: organism_scientific
    key_type: partition
    nullable: false
filters:
  version: 1.0.0
  provider: uniprot
  entity: protein
  input_filter:
    enabled: true
    source_path: data/input/protein.csv
    column_name: uniprot_id
    filter_field: accession
    batch_size: 100
  silver_filters:
    required_fields:
    - accession
    - organism_scientific
  gold_filters:
    columns:
      reviewed:
      - 'true'
    required_fields:
    - accession
    - entry_name
    - organism_scientific
contracts:
  primary_key:
  - accession
  merge_keys:
  - accession
  hash_include: []

================================================================================
File: chembl.yaml
Path: enums\chembl.yaml
================================================================================
# ChEMBL Database Enum Values
# Source: ChEMBL 35 (EBI)
# Last synced: 2026-02-16
#
# Canonical source of truth for all allowed enum values from ChEMBL DB.
# Used by: Pandera schemas (domain/schemas/constants.py),
#          filter configs (configs/filters/), DQ configs (configs/quality/).
#
# When ChEMBL releases a new version, update this file and bump `version`.

version: "chembl_35"

# =============================================================================
# Activity
# =============================================================================
activity:
    standard_relations:
        - "="
        - "<"
        - "<="
        - ">"
        - ">="

    standard_types:
        - IC50
        - EC50
        - Ki
        - Kd
        - AC50
        - GI50
        - Potency
        - Inhibition
        - "% Inhibition"
        - Activity
        - Ratio
        - ED50
        - ID50

    data_validity_comments:
        - Potential missing data
        - Potential author error
        - Manually validated
        - Potential transcription error
        - Outside typical range
        - Non standard unit for type
        - Author confirmed error

# =============================================================================
# Assay
# =============================================================================
assay:
    types:
        - B
        - F
        - A
        - T
        - P
        - U

    test_types:
        - In vivo
        - In vitro
        - Ex vivo

    categories:
        - screening
        - confirmatory
        - panel
        - summary
        - other
        - Affinity biochemical assay
        - Affinity on-target cellular assay
        - Affinity phenotypic cellular assay
        - Alphascreen assay
        - Cell health data
        - GPCR beta-arrestin recruitment assay
        - HTRF assay
        - ITC assay
        - Incucyte cell viability
        - NanoBRET assay
        - PDSP assay
        - Selectivity assay
        - Thermal shift assay

    confidence_descriptions:
        - Likely active
        - Active
        - Inactive
        - Potentially active
        - Potentially inactive
        - Inconclusive
        - Not determined

    relationship_types:
        - D
        - H
        - M
        - "N"
        - S
        - U

    assay_groups:
        - FUNCTIONAL
        - BINDING

    subcellular_fractions:
        - Membrane
        - Nucleus
        - Cytoplasm
        - Mitochondria
        - Endoplasmic reticulum

    # Parameter-specific types (merged with activity.standard_types at load time)
    parameter_standard_types:
        - CONC
        - PH
        - TEMP
        - TIME
        - DOSE
        - VOLUME
        - WAVELENGTH
        - PERCENT
        - PRESSURE
        - HUMIDITY
        - CELL_COUNT
        - CELL_DENSITY
        - SERUM

# =============================================================================
# Molecule
# =============================================================================
molecule:
    types:
        - Small molecule
        - Inorganic small molecule
        - Polymeric small molecule
        - Antibody
        - Antibody drug conjugate
        - Protein
        - Oligonucleotide
        - Oligosaccharide
        - Cell
        - Enzyme
        - Unknown
        - Unclassified

    structure_types:
        - MOL
        - SEQ
        - BOTH
        - NONE

    # Uses float for 0.5; loaded as tuple[float, ...] in Python
    max_phase_values:
        - -1
        - 0
        - 0.5
        - 1
        - 2
        - 3
        - 4

# =============================================================================
# Target
# =============================================================================
target:
    types:
        - SINGLE PROTEIN
        - PROTEIN FAMILY
        - PROTEIN COMPLEX
        - PROTEIN COMPLEX GROUP
        - SELECTIVITY GROUP
        - CHIMERIC PROTEIN
        - CELL-LINE
        - TISSUE
        - ORGANISM
        - MACROMOLECULE
        - SMALL MOLECULE
        - LIPID
        - METAL
        - UNKNOWN

    component_relationships:
        - SINGLE PROTEIN
        - PROTEIN SUBUNIT
        - RNA
        - INTERACTING PROTEIN

# =============================================================================
# Publication
# =============================================================================
# Unified publication types (kebab-case, cross-provider taxonomy).
# ChEMBL-native types (PUBLICATION, PATENT, DATASET, BOOK) are mapped
# to these canonical values by normalize_publication_type().
publication:
    types:
        - journal-article
        - patent
        - dataset
        - book
        - review
        - letter
        - editorial
        - clinical-trial
        - meta-analysis
        - case-reports
        - comparative-study
        - evaluation-study
        - preprint
        - book-chapter
        - proceedings-article
        - posted-content
        - report
        - standard
        - dissertation
        - other

================================================================================
File: publication_type_classification.meta.yaml
Path: enums\publication_type_classification.meta.yaml
================================================================================
schema_version: 2
asset: publication_type_classification
asset_version: v1
source:
  path: configs/enums/publication_type_classification.csv
  sha256: 039561f4112e7e3cbca158c8603e06628961b1dc4b418867fc63022069e4e0ea
  row_count: 214
artifact:
  path: configs/enums/publication_type_classification.asset.v1.json
  sha256: da2a216046a2b64c7aeb2604c5e39459f745d0b4677560a0a3043b856d0a6a33
  row_count: 214

================================================================================
File: naming_exceptions.yaml
Path: naming_exceptions.yaml
================================================================================
# Naming Convention Exceptions
# This file documents allowed exceptions to the naming conventions in RULES.md §2.
# Version: 2.2
# Last Updated: 2026-03-20

# Documentation files that are allowed to use UPPER_CASE names.
# These are conventional files recognized by GitHub and standard tooling.
documentation_exceptions:
    - README.md           # Standard project readme
    - CHANGELOG.md        # Standard changelog (Keep a Changelog format)
    - REQUIREMENTS.md     # Project requirements document
    - RULES.md            # Project rules/constitution
    - CONTRIBUTING.md     # Contribution guidelines
    - SECURITY.md         # Security policy
    - LICENSE.md          # License file
    - CLAUDE.md           # Claude Code instructions
    - AGENT.md            # Agent instructions (Jules)
    - SKILL.md            # Skill instruction files
    - INDEX.md            # Index / navigation hubs
    - ORCHESTRATION.md    # Runtime orchestration docs
    - TOOLS.md            # Tool reference docs
    - CODEX.md            # Codex runtime docs
    - GEMINI.md           # Gemini runtime docs

# Root-level files that may use non-standard naming
root_file_exceptions:
    - Makefile            # Standard build file
    - Dockerfile          # Standard container file
    - pyproject.toml      # Standard Python project config

# Classes without standard suffixes (domain entities, enums, value objects)
# These are exempt from the suffix requirement in RULES.md §2.1
class_suffix_exceptions:
    # Domain Entities (business objects)
    domain_entities:
        - Activity
        - Assay
        - Target
        - TargetComponent
        - Molecule
        # Canonical names (v2.0 - ADR-024)
        - ChemblPublication  # Replaces Document (no alias - direct migration)
        - PubchemMolecule    # Replaces Compound (no alias - direct migration)
        - UniprotTarget      # Replaces Protein (no alias - direct migration)
        # NOTE: Deprecated aliases (Document, Compound, Protein) were NEVER implemented.
        # Per ADR-024 update (2026-01-21), the codebase was migrated directly to
        # canonical names without backward compatibility shims.
        # Other publication entities
        - Publication

    # Enums (inherently self-describing)
    enums:
        - Layer
        - WriteMode
        - SilverWriteMode
        - GoldWriteMode
        - ClearPolicy
        - RunType
        - HealthStatus
        - DriftLevel
        - CircuitBreakerState
        - DataClassification
        - ErrorType
        - DQStatus
        - LifecyclePhase
        - AuditOperation
        - AuditLayer
        - AnomalyType
        - AnomalySeverity

    # TypedDict classes (suffix 'Dict' is implicit)
    typed_dicts:
        - BronzeRecord
        - SilverRecord
        - RawDate
        - NormalizedDate
        - RawAuthor
        - RawIdentifiers
        - NormalizedIdentifiers
        - RawClassification
        - NormalizedClassification
        # And all *Dict classes

    # Value objects and simple results
    value_objects:
        - Anomaly
        - ClearDecision
        - ClearResult
        - CleanupPreview
        - CleanupResult
        - LayerInfo
        - TransformResult
        - TransformedRecord
        - BatchResult
        - DQResult
        - VacuumResult
        - ValidationResult
        - HealthReport
        - PreflightReport
        - ComponentHealthResult
        - FilterLoadResult
        - MemoryStats
        - ProviderHealthState
        - ShutdownSignal
        - AuditEntry
        - LockContext
        - PipelineEvent
        - RetryPolicy
        - LineageRecord
        - BatchLineage

    # Context and configuration objects
    contexts:
        - InputFilterContext
        - VacuumConfig
        - PipelineContext
        - PipelineRunContext
        - StorageContext
        - ObservabilityBundle
        - RunnerServices
        - PipelineServices
        - PipelineDefinition
        - ProviderConfig
        - HttpConfig
        - RunOptions
        - VacuumOptions
        - ArchiveOptions
        - RecordProcessorConfig
        - MemoryConfig

    # Base classes (prefix 'Base' is sufficient)
    base_classes:
        - BaseEntity
        - BasePipeline
        - BaseTransformer
        - BaseHttpAdapter
        - BaseSyncAdapter
        - BaseFieldExtractor
        - BaseChemblTransformer
        - BaseServicesFactory
        - RequiredEntityFields

    # Policy classes
    policies:
        - MedallionPolicy
        - WriteModePolicy

    # Filter classes
    filters:
        - GoldRangeFilter
        - GoldColumnFilter
        - GoldListLengthFilter
        - GoldListContainsFilter
        - GoldFilterConfig
        - InputFilterConfig
        - FilteredDataSource

# Function prefix exceptions
# Functions that don't require standard prefixes (get_, fetch_, create_, etc.)
function_prefix_exceptions:
    # CLI entry points
    - main
    - cli
    - run

    # Event handlers (naming is descriptive)
    - vacuum_command
    - archive_command
    - quarantine
    - checkpoint
    - maintenance

    # Magic/dunder methods are exempt
    # - __init__, __call__, etc.

# Pipeline naming format
# Pipeline IDs follow the format: {provider}_{entity}
# They are stable external identifiers for CLI/config/public surfaces and may
# intentionally differ from canonical domain entity names defined by ADR-024.
pipeline_id_format:
    pattern: "{provider}_{entity}"
    examples:
        - chembl_activity
        - chembl_assay
        - chembl_target
        - chembl_molecule
        - chembl_publication  # Renamed from chembl_document per ADR-024
        - chembl_publication_similarity
        - chembl_publication_term
        - chembl_target_component
        - pubchem_compound   # Uses API term per glossary.md CLI conventions
        - uniprot_protein    # Uses API term per glossary.md CLI conventions
        - pubmed_publication

# Stable public surface names that intentionally preserve provider API terms.
# These names are not canonical domain entities, but they are normative for CLI,
# pipeline classes, transformers, and generated public contracts.
stable_public_surface:
    pipeline_ids:
        -   name: pubchem_compound
            location: configs/entities/pubchem/compound.yaml
            reason: Stable external pipeline identifier uses PubChem API term for CLI/config compatibility.
        -   name: uniprot_protein
            location: configs/entities/uniprot/protein.yaml
            reason: Stable external pipeline identifier uses UniProt API term for CLI/config compatibility.
    pipeline_classes:
        -   name: PubChemCompoundPipeline
            location: src/bioetl/application/pipelines/pubchem/__init__.py
            reason: Public application pipeline surface follows stable pipeline identifier rather than canonical domain entity name.
        -   name: UniProtProteinPipeline
            location: src/bioetl/application/pipelines/uniprot/__init__.py
            reason: Public application pipeline surface follows stable pipeline identifier rather than canonical domain entity name.
    transformers:
        -   name: PubChemCompoundTransformer
            location: src/bioetl/application/pipelines/pubchem/transformer.py
            reason: Transformer name matches stable external pipeline surface while validating against PubchemMolecule.
        -   name: UniProtProteinTransformer
            location: src/bioetl/application/pipelines/uniprot/transformer.py
            reason: Transformer name matches stable external pipeline surface while validating against UniprotTarget.
    gold_schemas:
        -   name: PubChemCompoundGoldSchema
            location: src/bioetl/domain/contracts/gold/pubchem.py
            reason: Generated/public Gold contract keeps the stable pipeline surface term Compound.
        -   name: UniProtProteinGoldSchema
            location: src/bioetl/domain/contracts/gold/uniprot.py
            reason: Generated/public Gold contract keeps the stable pipeline surface term Protein.

# Legacy domain aliases forbidden by ADR-024. These names are not valid
# replacements for canonical domain entities and must not reappear on export
# surfaces without an explicit, time-bound compatibility decision.
forbidden_domain_entity_aliases:
    -   legacy_name: Document
        canonical_name: ChemblPublication
        export_surface: src/bioetl/domain/entities/__init__.py
        reason: ADR-024 direct migration removed the need for a Document alias in the canonical domain layer.
    -   legacy_name: Compound
        canonical_name: PubchemMolecule
        export_surface: src/bioetl/domain/entities/__init__.py
        reason: ADR-024 direct migration removed the need for a Compound alias in the canonical domain layer.
    -   legacy_name: Protein
        canonical_name: UniprotTarget
        export_surface: src/bioetl/domain/entities/__init__.py
        reason: ADR-024 direct migration removed the need for a Protein alias in the canonical domain layer.

# Notes on enforcement
# - scripts/engineering/qa/naming_audit.py loads this file as the naming exception registry.
# - Violations against these exceptions should NOT be flagged.
# - Add new exceptions here with justification and concrete location.


# ADR-024 exception registry (audited 2026-03-20)
adr_024_known_exceptions:
    derived_entities:
        -   entity: DocumentSimilarity
            location: src/bioetl/domain/entities/chembl_structures.py
            reason: ChEMBL-specific derived entity kept per ADR-024
        -   entity: DocumentTerm
            location: src/bioetl/domain/entities/chembl_structures.py
            reason: ChEMBL-specific derived entity kept per ADR-024
    pipeline_ids:
        -   pipeline: pubchem_compound
            location: configs/entities/pubchem/compound.yaml
            reason: CLI compatibility uses provider API term per glossary and stable public ID policy.
        -   pipeline: uniprot_protein
            location: configs/entities/uniprot/protein.yaml
            reason: CLI compatibility uses provider API term per glossary and stable public ID policy.
    legacy_fields:
        -   field: document_id
            reason: foreign-key compatibility with ChEMBL API source model
        -   field: document_chembl_id
            reason: foreign-key compatibility with ChEMBL API source model
    backward_compatibility:
        -   module: src/bioetl/domain/entities/__init__.py
            note: compatibility export surface retained until alias removal window (v3.0).

================================================================================
File: chembl.yaml
Path: providers\chembl.yaml
================================================================================
version: 1.0.0
provider: chembl
source:
    provider_config:
        provider: chembl
        base_url: https://www.ebi.ac.uk/chembl/api/data
        auth_type: public
        client:
            timeout_sec: 120.0
            max_retries: 8
            trust_env: false
        pagination:
            page_size: 1000
            id_batch_size: 20
            strategy: offset
            max_url_length: 2000
        api_version: null
    circuit_breaker:
        failure_threshold: 3
        recovery_timeout: 3000
    rate_limit:
        requests_per_second: 0.1
        burst: 1
    health_check:
        endpoint: null
        timeout: 15
    retry:
        use_retry_after: false
entities:
    - activity
    - assay
    - assay_parameters
    - cell_line
    - compound_record
    - publication
    - publication_similarity
    - publication_term
    - molecule
    - protein_class
    - subcellular_fraction
    - target
    - target_component
    - tissue
entity_notes:
    activity:
        description: Primary bioactivity data with IC50, Ki, etc.
        typical_volume: ~20M records
    assay:
        description: Bioassay definitions and metadata
        typical_volume: ~1.5M records
    molecule:
        description: Chemical compounds with structures
        typical_volume: ~2.5M records
    target:
        description: Biological targets (proteins, genes)
        typical_volume: ~15K records
    protein_class:
        description: Reference table for protein classification
        typical_volume: ~1.5K records
    publication_term:
        description: Derived entity - extracted from document records
        derived_from: publication
quality:
    version: 1.0.0
    provider: chembl
    thresholds:
        soft_fail: 0.05
        hard_fail: 0.15
    provider_field_validations:
        -   field: molecule_id
            type: pattern
            pattern: ^CHEMBL\d+$
            nullable: true
            error_message: Invalid ChEMBL molecule ID format
        -   field: target_id
            type: pattern
            pattern: ^CHEMBL\d+$
            nullable: true
            error_message: Invalid ChEMBL target ID format
        -   field: assay_id
            type: pattern
            pattern: ^CHEMBL\d+$
            nullable: true
            error_message: Invalid ChEMBL assay ID format
        -   field: publication_id
            type: pattern
            pattern: ^CHEMBL\d+$
            nullable: true
            error_message: Invalid ChEMBL document ID format
filters:
    version: 1.0.0
    provider: chembl
    input_filter:
        batch_size: 1000

================================================================================
File: crossref.yaml
Path: providers\crossref.yaml
================================================================================
version: 1.0.0
provider: crossref
source:
    provider_config:
        provider: crossref
        base_url: https://api.crossref.org
        auth_type: email
        mailto: ${BIOETL_CROSSREF_EMAIL}
        client:
            timeout_sec: 30.0
            max_retries: 3
        pagination:
            page_size: 50
            id_batch_size: 50
            strategy: cursor
        fallback:
            enabled: true
            supported_filter_field: doi
            unsupported_filter_event: unsupported_filter_field_for_fallback
            unsupported_filter_message: CrossRef fallback only supports 'doi' filtering,
                proceeding with DOI semantics
            skip_on_unsupported_filter_field: false
            primary_lookup_method: doi
            trim_primary_ids_to_limit: true
            fallback_operation: fetch_filtered_with_fallback
    circuit_breaker:
        failure_threshold: 5
        recovery_timeout: 300
    rate_limit:
        requests_per_second: 50
        burst: 100
        polite_pool: true
    health_check:
        endpoint: /works
        params:
            rows: 1
        timeout: 5
    retry:
        use_retry_after: true
entities:
    - publication
entity_notes:
    publication:
        description: Publication metadata via DOI resolution
        input_mode: CSV file with DOIs
        fallback: Title search when DOI not found (404)
        batch_size: 50
quality:
    version: 1.0.0
    provider: crossref
    thresholds:
        soft_fail: 0.1
        hard_fail: 0.3
    provider_field_validations:
        -   field: doi
            type: pattern
            pattern: ^10\.\d{4,}/\S+$
            nullable: true
            error_message: Invalid DOI format (must match 10.XXXX/suffix, no whitespace)
        -   field: publication_year
            type: range
            min: 1500
            max: 2100
            nullable: true
            error_message: Publication year out of valid range
filters:
    version: 1.0.0
    provider: crossref
    input_filter:
        batch_size: 50

================================================================================
File: openalex.yaml
Path: providers\openalex.yaml
================================================================================
version: 1.0.0
provider: openalex
source:
    provider_config:
        provider: openalex
        base_url: https://api.openalex.org
        auth_type: email
        mailto: ${BIOETL_OPENALEX_EMAIL}
        client:
            timeout_sec: 30.0
            max_retries: 3
        pagination:
            page_size: 50
            id_batch_size: 50
            strategy: cursor
        fallback:
            enabled: true
            supported_filter_field: doi
            unsupported_filter_event: unsupported_filter_field_for_fallback
            unsupported_filter_message: OpenAlex fallback only supports 'doi' filtering,
                skipping
            skip_on_unsupported_filter_field: true
            primary_lookup_method: doi
            trim_primary_ids_to_limit: false
            fallback_operation: fetch_filtered_with_fallback
    circuit_breaker:
        failure_threshold: 5
        recovery_timeout: 300
    rate_limit:
        requests_per_second: 10
        burst: 20
        polite_pool: true
    health_check:
        endpoint: /works
        params:
            per-page: 1
        timeout: 5
    retry:
        use_retry_after: true
entities:
    - publication
entity_notes:
    publication:
        description: Scholarly works metadata via DOI resolution
        input_mode: CSV file with DOIs
        fallback: Title search when DOI not found
        batch_size: 50
quality:
    version: 1.0.0
    provider: openalex
    thresholds:
        soft_fail: 0.08
        hard_fail: 0.25
    provider_field_validations:
        -   field: openalex_id
            type: pattern
            pattern: ^W\d+$
            nullable: true
            error_message: Invalid OpenAlex ID format (must start with W followed by digits)
        -   field: doi
            type: pattern
            pattern: ^10\.\d{4,}/\S+$
            nullable: true
            error_message: Invalid DOI format (must match 10.XXXX/suffix, no whitespace)
        -   field: publication_year
            type: range
            min: 1500
            max: 2100
            nullable: true
            error_message: Publication year out of valid range
filters:
    version: 1.0.0
    provider: openalex
    input_filter:
        batch_size: 50

================================================================================
File: pubchem.yaml
Path: providers\pubchem.yaml
================================================================================
version: 1.0.0
provider: pubchem
source:
  provider_config:
    provider: pubchem
    base_url: https://pubchem.ncbi.nlm.nih.gov/rest/pug
    auth_type: public
    client:
      timeout_sec: 30.0
      max_retries: 3
    pagination:
      page_size: 50
      id_batch_size: 50
      strategy: offset
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 300
  rate_limit:
    requests_per_second: 5.0
    burst: 10
  health_check:
    method: Lightweight compound query
    timeout: 10
  retry:
    use_retry_after: true
entities:
- compound
entity_notes:
  compound:
    description: Chemical compounds with computed properties
    typical_volume: Depends on input filter (SMILES-based)
    input_mode: SMILES-based search
    batch_size: 1
quality:
  version: 1.0.0
  provider: pubchem
  thresholds:
    soft_fail: 0.08
    hard_fail: 0.25
  provider_field_validations:
  - field: molecule_id
    type: range
    min: 1
    nullable: true
    error_message: CID must be a positive integer
filters:
  version: 1.0.0
  provider: pubchem
  input_filter:
    batch_size: 1

================================================================================
File: pubmed.yaml
Path: providers\pubmed.yaml
================================================================================
version: 1.0.0
provider: pubmed
source:
    provider_config:
        provider: pubmed
        base_url: https://eutils.ncbi.nlm.nih.gov/entrez/eutils
        auth_type: api_key
        api_key_env: BIOETL_PUBMED_API_KEY
        email_env: BIOETL_PUBMED_EMAIL
        client:
            timeout_sec: 60.0
            max_retries: 3
        pagination:
            page_size: 100
            id_batch_size: 100
            strategy: offset
        default_email: bioetl-bot@example.com
        fallback:
            enabled: true
            supported_filter_field: null
            unsupported_filter_event: unsupported_filter_field_for_fallback
            unsupported_filter_message: PubMed fallback accepts any field and resolves via
                PMID/title phases
            skip_on_unsupported_filter_field: false
            primary_lookup_method: pmid
            trim_primary_ids_to_limit: false
            fallback_operation: fetch_filtered_with_fallback
    circuit_breaker:
        failure_threshold: 5
        recovery_timeout: 300
    rate_limit:
        requests_per_second: 3.0
        burst: 5
        with_api_key:
            requests_per_second: 10
            burst: 20
    health_check:
        endpoint: /einfo.fcgi
        timeout: 10
    retry:
        use_retry_after: true
entities:
    - publication
entity_notes:
    publication:
        description: PubMed article metadata via Entrez
        input_mode: Search term or PMID list
        search_syntax: PubMed boolean queries supported
quality:
    version: 1.0.0
    provider: pubmed
    thresholds:
        soft_fail: 0.05
        hard_fail: 0.15
    provider_field_validations:
        -   field: pmid
            type: range
            min: 1
            max: 10000000000
            nullable: true
            error_message: PMID must be a positive integer
        -   field: pmc_id
            type: pattern
            pattern: ^PMC\d+$
            nullable: true
            error_message: PMC ID must start with PMC followed by digits
        -   field: doi
            type: pattern
            pattern: ^10\.\d{4,}/\S+$
            nullable: true
            error_message: Invalid DOI format (must match 10.XXXX/suffix, no whitespace)
        -   field: publication_year
            type: range
            min: 1500
            max: 2100
            nullable: true
            error_message: Publication year out of valid range
filters:
    version: 1.0.0
    provider: pubmed
    input_filter:
        batch_size: 100

================================================================================
File: semanticscholar.yaml
Path: providers\semanticscholar.yaml
================================================================================
version: 1.0.0
provider: semanticscholar
source:
    provider_config:
        provider: semanticscholar
        base_url: https://api.semanticscholar.org/graph/v1
        auth_type: api_key
        api_key: ${BIOETL_SEMANTICSCHOLAR_API_KEY}
        client:
            timeout_sec: 60.0
            max_retries: 5
            retry_base_delay: 30.0
            retry_max_delay: 300.0
        pagination:
            page_size: 100
            id_batch_size: 50
            strategy: offset
        fallback:
            enabled: true
            supported_filter_field: doi
            unsupported_filter_event: unsupported_filter_field_for_fallback
            unsupported_filter_message: SemanticScholar fallback only supports 'doi' filtering,
                skipping
            skip_on_unsupported_filter_field: true
            primary_lookup_method: doi
            trim_primary_ids_to_limit: false
            fallback_operation: fetch_filtered_with_fallback
    circuit_breaker:
        failure_threshold: 10
        recovery_timeout: 600
    rate_limit:
        requests_per_second: 0.1
        burst: 1
        window: 300
        with_api_key:
            requests_per_second: 1.0
            burst: 5
    health_check:
        endpoint: /paper/search
        params:
            query: test
            limit: 1
            fields: paperId
        timeout: 30
        skip_on_429: true
    retry:
        use_retry_after: true
entities:
    - publication
entity_notes:
    publication:
        description: Semantic Scholar paper metadata via DOI resolution
        input_mode: CSV file with DOIs
        fallback: Title search when DOI not found
        batch_size: 100
quality:
    version: 1.0.0
    provider: semanticscholar
    thresholds:
        soft_fail: 0.15
        hard_fail: 0.4
    provider_field_validations:
        -   field: paper_id
            type: pattern
            pattern: ^[a-f0-9]{40}$
            nullable: true
            error_message: Invalid paper_id format (must be 40-char hex string)
        -   field: doi
            type: pattern
            pattern: ^10\.\d{4,}/\S+$
            nullable: true
            error_message: Invalid DOI format (must match 10.XXXX/suffix, no whitespace)
        -   field: publication_year
            type: range
            min: 1500
            max: 2100
            nullable: true
            error_message: Publication year out of valid range
        -   field: citations_received
            type: range
            min: 0
            nullable: true
            error_message: Citation count must be non-negative
filters:
    version: 1.0.0
    provider: semanticscholar
    input_filter:
        batch_size: 100

================================================================================
File: uniprot.yaml
Path: providers\uniprot.yaml
================================================================================
version: 1.0.0
provider: uniprot
source:
    provider_config:
        provider: uniprot
        base_url: https://rest.uniprot.org
        auth_type: api_key
        api_key_env: BIOETL_UNIPROT_API_KEY
        pagination:
            page_size: 200
            id_batch_size: 200
            strategy: offset
        client:
            timeout_sec: 30.0
            max_retries: 3
        fallback:
            enabled: true
            supported_filter_field: null
            unsupported_filter_event: unsupported_filter_field_for_fallback
            unsupported_filter_message: UniProt fallback accepts any filter field with provider-specific
                hooks
            skip_on_unsupported_filter_field: false
            primary_lookup_method: null
            trim_primary_ids_to_limit: false
            fallback_operation: fetch_filtered_with_fallback
    circuit_breaker:
        failure_threshold: 5
        recovery_timeout: 300
    rate_limit:
        requests_per_second: 10.0
        burst: 20
        with_api_key:
            requests_per_second: 100
            burst: 200
    health_check:
        method: Search probe query
        timeout: 10
    retry:
        use_retry_after: true
entities:
    - protein
    - idmapping
entity_notes:
    protein:
        description: UniProt protein entries (Swiss-Prot reviewed)
        typical_volume: ~570K reviewed entries
    idmapping:
        description: Maps ChEMBL target IDs to UniProt accessions
        input_mode: CSV file with target_id
        dq_thresholds:
            soft_fail: 0.3
            hard_fail: 0.8
quality:
    version: 1.0.0
    provider: uniprot
    thresholds:
        soft_fail: 0.03
        hard_fail: 0.1
    provider_field_validations:
        -   field: accession
            type: pattern
            pattern: ^[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$
            nullable: true
            error_message: Invalid UniProt accession format
filters:
    version: 1.0.0
    provider: uniprot
    input_filter:
        batch_size: 100

================================================================================
File: architecture_acceptance_baseline.yaml
Path: quality\architecture_acceptance_baseline.yaml
================================================================================
version: 1
policy_scope: architecture_acceptance_baseline
source_of_truth:
  execution_context_architecture_test: tests/architecture/test_execution_context_architecture.py
  logging_correlation_contract_test: tests/architecture/test_logging_correlation_contract.py
  no_structlog_contract_test: tests/architecture/test_no_structlog_in_application_interfaces.py
  layer_dependency_test: tests/architecture/test_layer_dependencies.py
  run_ledger_service_test: tests/unit/application/services/test_run_ledger_service.py
  checkpoint_suite_root: tests/unit/application/composite/checkpoint/
criteria:
  - id: canonical_runtime_contexts
    description: PipelineRunContext and PipelineContext remain the canonical runtime contexts.
    source_paths:
      - src/bioetl/domain/context.py
    verification_tests:
      - tests/architecture/test_execution_context_architecture.py
      - tests/unit/domain/test_pipeline_context.py
    code_anchors:
      - class PipelineContext
      - class PipelineRunContext
      - def log_correlation_fields
  - id: control_plane_run_manifest_provenance
    description: Control-plane RunManifest stays a provenance artifact and not a runtime replacement.
    source_paths:
      - src/bioetl/domain/control_plane/run_manifest.py
    verification_tests:
      - tests/architecture/test_execution_context_architecture.py
    code_anchors:
      - class RunManifest
      - provenance
  - id: run_ledger_lifecycle_timeline
    description: RunLedger exposes a deterministic lifecycle and stage timeline.
    source_paths:
      - src/bioetl/domain/control_plane/run_ledger.py
      - src/bioetl/application/services/run_ledger_service.py
    verification_tests:
      - tests/unit/application/services/test_run_ledger_service.py
      - tests/unit/domain/control_plane/test_run_ledger_replay.py
    code_anchors:
      - stage_started
      - stage_completed
      - project_run_ledger_replay
  - id: checkpoint_snapshot_only_contract
    description: Checkpoint remains snapshot-only and does not embed event history.
    source_paths:
      - src/bioetl/application/composite/checkpoint/state.py
      - src/bioetl/application/composite/checkpoint/load_service.py
    verification_tests:
      - tests/unit/application/composite/checkpoint/test_checkpoint_state.py
      - tests/unit/application/composite/checkpoint/test_checkpoint_service.py
    code_anchors:
      - last_event_id
      - last_event_occurred_at
  - id: resume_checkpoint_plus_replay
    description: Resume path restores checkpoint state and then replays ledger entries after the watermark.
    source_paths:
      - src/bioetl/application/composite/checkpoint/load_service.py
      - src/bioetl/domain/control_plane/run_ledger.py
    verification_tests:
      - tests/unit/application/composite/checkpoint/test_checkpoint_service.py
      - tests/unit/domain/control_plane/test_run_ledger_replay.py
    code_anchors:
      - list_entries_after
      - project_run_ledger_replay
  - id: strict_resume_compatibility_anchors
    description: Resume keeps strict compatibility validation before replay state is applied.
    source_paths:
      - src/bioetl/application/composite/checkpoint/load_service.py
    verification_tests:
      - tests/unit/application/composite/checkpoint/test_checkpoint_service.py
    code_anchors:
      - validate_resume_compatibility
      - CheckpointConflictError
  - id: no_infrastructure_runtime_imports
    description: Domain and application continue to avoid runtime imports from infrastructure.
    source_paths:
      - src/bioetl/domain/
      - src/bioetl/application/
    verification_tests:
      - tests/architecture/test_layer_dependencies.py
    code_anchors: []
  - id: logger_port_only_correlation_contract
    description: Correlation logging stays sourced from PipelineRunContext through LoggerPort seams.
    source_paths:
      - src/bioetl/domain/context.py
      - src/bioetl/application/services/pipeline_runner_service.py
    verification_tests:
      - tests/architecture/test_logging_correlation_contract.py
      - tests/architecture/test_no_structlog_in_application_interfaces.py
    code_anchors:
      - log_correlation_fields
      - self.logger.bind(**context.log_correlation_fields())
  - id: storage_checkpoint_error_consistency
    description: StorageError and CheckpointConflictError stay consistent across checkpoint and control-plane storage paths.
    source_paths:
      - src/bioetl/application/composite/checkpoint/load_service.py
      - src/bioetl/application/composite/checkpoint/service.py
    verification_tests:
      - tests/unit/application/composite/checkpoint/test_checkpoint_service.py
      - tests/unit/infrastructure/control_plane/test_file_run_ledger_store.py
    code_anchors:
      - CheckpointConflictError
  - id: deprecated_value_object_run_manifest_absent
    description: The removed value-object RunManifest remains absent and gains no new consumers.
    source_paths:
      - src/bioetl/domain/value_objects/
    verification_tests:
      - tests/architecture/test_value_object_run_manifest_deprecation.py
      - tests/architecture/test_execution_context_architecture.py
    code_anchors: []

================================================================================
File: architecture_metric_exemptions.yaml
Path: quality\architecture_metric_exemptions.yaml
================================================================================
schema_version: 1
policy:
  default_gate_mode: block
  owner_diversification_sync:
    source: configs/quality/debt_scorecard.yaml#governance.owner_diversification
    starts_quarter: 2026-Q2
    review_on: "2026-06-30"
  required_fields:
    - value
    - owner
    - reason
    - classification
    - linked_rf
    - expires_on
    - removal_step
registries:
  file_size_limits:
    src/bioetl/application/services/checkpoint_compatibility_service.py:
      value: 558
      owner: "@bioetl-platform"
      reason: "Checkpoint compatibility orchestration still carries transitional branching scheduled for decomposition."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Split compatibility and replay decision paths into helper owners, then retire this exemption."
    src/bioetl/infrastructure/storage/silver_writer.py:
      value: 1308
      owner: "@bioetl-platform"
      reason: "SilverWriter remains a large infrastructure facade while Delta write, validation, and recovery branches are still being peeled into dedicated storage helpers."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Continue extracting write-path orchestration into storage/silver helper modules until the facade falls back under the infrastructure LOC cap."
  function_complexity:
    {}
  function_length:
    src/bioetl/application/services/checkpoint_compatibility_service.py::_validate_execution_identity_compatibility:
      value: 102
      owner: "@bioetl-platform"
      reason: "Checkpoint compatibility orchestration still carries a transitional identity-validation path while helper extraction continues."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Continue splitting execution-identity validation branches into dedicated helpers until the function drops below the default limit."
    src/bioetl/application/services/checkpoint_compatibility_service_v2.py::check_compatibility:
      value: 140
      owner: "@bioetl-platform"
      reason: "Checkpoint compatibility v2 remains a migration-era orchestration entrypoint with multiple decision branches not yet decomposed."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Extract compatibility decision branches into dedicated helpers and retire the exemption once the entrypoint returns under the default limit."
    src/bioetl/application/services/control_plane/_run_manifest_diagnostics_ledger.py::_process_ledger_entries:
      value: 104
      owner: "@bioetl-data-model"
      reason: "Run-manifest ledger diagnostics still batch multiple ledger-shaping branches in one transitional helper."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Split ledger-entry aggregation and state-derivation branches into dedicated helpers until the function drops under the default limit."
    src/bioetl/application/services/control_plane/_run_manifest_diagnostics_persistence.py::build_persistence_profile:
      value: 107
      owner: "@bioetl-data-model"
      reason: "Persistence-profile classification still combines multiple diagnostic derivations in one service helper pending the next control-plane cleanup wave."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Continue extracting persistence-profile derivation helpers until the function returns under the default limit."
    src/bioetl/application/services/control_plane/_run_manifest_diagnostics_summary.py::_build_final_summary:
      value: 187
      owner: "@bioetl-data-model"
      reason: "Run-manifest final summary assembly remains a large compatibility surface while report shaping is still centralized."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Peel summary sections into dedicated formatter helpers until the final summary builder returns under the default limit."
    src/bioetl/application/services/control_plane/run_manifest_diagnostics.py::_build_base_summary:
      value: 121
      owner: "@bioetl-data-model"
      reason: "Base run-manifest diagnostics still aggregate multiple control-plane slices in a single orchestration helper."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Split base-summary assembly into smaller diagnostics helpers until the function drops below the default limit."
    src/bioetl/application/services/control_plane/run_manifest_inspection_service.py::_build_identity_graph:
      value: 113
      owner: "@bioetl-data-model"
      reason: "Identity-graph assembly still centralizes multiple node and edge shaping branches in one inspection helper."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Extract identity-graph node and edge builders into dedicated helpers until the function returns under the default limit."
    src/bioetl/infrastructure/storage/silver/operations/metadata_operations.py::_build_silver_metadata:
      value: 109
      owner: "@bioetl-platform"
      reason: "Silver metadata assembly still combines multiple metadata derivation branches while storage helper extraction is in progress."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Split silver metadata derivation into smaller helpers until the function drops under the default limit."
    src/bioetl/infrastructure/storage/silver/runtime_helpers.py::build_silver_writer_runtime_services:
      value: 136
      owner: "@bioetl-platform"
      reason: "Silver writer runtime service wiring remains a broad transitional factory while Delta/storage seams are still being decomposed."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Extract runtime dependency groups into dedicated factory helpers until the function returns under the default limit."
    src/bioetl/infrastructure/storage/silver_writer.py::__init__:
      value: 142
      owner: "@bioetl-platform"
      reason: "SilverWriter constructor still accepts and normalizes many transitional storage dependencies while the facade is being reduced."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Move constructor normalization branches into dedicated setup helpers until the constructor drops below the default limit."
  class_size:
    src/bioetl/application/composite/_lifecycle_observer_tracing_mixin.py::CompositeLifecycleTracingMixin:
      value: 312
      owner: "@bioetl-architecture"
      reason: "Composite lifecycle tracing still centralizes transitional observer wiring and emission helpers in one mixin."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Continue extracting lifecycle emission branches into smaller tracing helpers until the mixin drops below the default limit."
    src/bioetl/application/observability/observer.py::_ObserverLifecycleEmissionMixin:
      value: 371
      owner: "@bioetl-architecture"
      reason: "Observer lifecycle emission remains a large observability mixin while compatibility hooks are still centralized."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Split lifecycle emission helpers into smaller observer mixins until the class drops below the default limit."
    src/bioetl/application/services/_quarantine_service_sync_mixin.py::QuarantineServiceSyncMixin:
      value: 373
      owner: "@bioetl-platform"
      reason: "Quarantine sync support still combines multiple synchronization branches in one transitional mixin."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Extract quarantine sync helpers into smaller mixins until the class returns under the default limit."
    src/bioetl/application/services/control_plane/run_manifest_inspection_service.py::RunManifestInspectionService:
      value: 328
      owner: "@bioetl-data-model"
      reason: "Run manifest inspection still centralizes multiple graph-building and presentation responsibilities."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Continue splitting identity graph and inspection formatting helpers until the service drops below the default limit."
    src/bioetl/application/services/control_plane/run_manifest_service.py::RunManifestService:
      value: 322
      owner: "@bioetl-data-model"
      reason: "Run manifest lifecycle operations remain grouped in one transitional control-plane service."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Extract manifest subflows into dedicated helpers until the service returns under the default limit."
    src/bioetl/application/services/data_quality_service.py::DataQualityService:
      value: 388
      owner: "@bioetl-platform"
      reason: "Data quality orchestration still carries multiple report and validation branches in one service."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Continue extracting DQ analysis/reporting helpers until the service drops below the default limit."
    src/bioetl/application/services/metrics_service.py::MetricsService:
      value: 357
      owner: "@bioetl-platform"
      reason: "Metrics orchestration still centralizes multiple metric-publication branches in one transitional service."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Extract metric publication helpers until the service drops below the default limit."
    src/bioetl/infrastructure/storage/silver/operations/metadata_operations.py::SilverMetadataOperations:
      value: 555
      owner: "@bioetl-platform"
      reason: "Silver metadata operations remain a large infrastructure operation host while metadata and lineage helpers are still being extracted."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Continue peeling metadata and lineage subflows into dedicated operation helpers until the class returns under the default limit."
    src/bioetl/infrastructure/storage/silver_writer.py::SilverWriter:
      value: 1061
      owner: "@bioetl-platform"
      reason: "SilverWriter remains a large façade coordinating legacy write-path responsibilities during the storage decomposition wave."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Continue extracting write-path orchestration into dedicated storage helpers until the class drops below the default limit."
  class_method_count: {}
  god_object:
    src/bioetl/application/services/_quarantine_service_sync_mixin.py::QuarantineServiceSyncMixin:
      value: 0
      owner: "@bioetl-platform"
      reason: "Quarantine sync mixin remains a large compatibility surface with internal orchestration branches not yet delegated to injected collaborators."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Extract quarantine sync responsibilities into dedicated collaborators or shrink the mixin below the large-class threshold."
    src/bioetl/application/services/control_plane/run_manifest_inspection_service.py::RunManifestInspectionService:
      value: 0
      owner: "@bioetl-data-model"
      reason: "Run manifest inspection remains a large read-model assembler with low explicit delegation while graph and summary builders are still being separated."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Continue extracting identity graph and inspection rendering collaborators until the class no longer trips the god-object heuristic."
    src/bioetl/application/services/control_plane/run_manifest_service.py::RunManifestService:
      value: 0
      owner: "@bioetl-data-model"
      reason: "Run manifest service remains a transitional control-plane façade with low observable delegation while manifest subflows are still centralized."
      classification: "technical_debt"
      linked_rf: "RF-023"
      expires_on: "2026-06-30"
      removal_step: "Split manifest lifecycle responsibilities into dedicated collaborators until the class no longer triggers the god-object heuristic."
  domain_complexity: {}

================================================================================
File: ci_coverage_surface_matrix.yaml
Path: quality\ci_coverage_surface_matrix.yaml
================================================================================
version: 1
policy_scope: ci_coverage_surface_mapping
workflow_path: .github/workflows/tests.yml
threshold_policy:
  hard_coverage_threshold: 85
  enforced_in_job: coverage-verify
  notes: >-
    Coverage enforcement is centralized in the dedicated coverage-verify job.
    Other jobs may contribute shard data or execution confidence without
    directly enforcing the threshold.
lanes:
  - job: smoke-check
    lane_type: coverage_shard
    emits_coverage_artifact: true
    coverage_artifact: coverage-data-smoke
    participates_in_hard_threshold: true
    threshold_enforced_in_job: false
    execution_confidence_role: dependency_smoke
    notes: >-
      Smoke check contributes a coverage shard and minimal dependency/import
      confidence before heavier lanes start.
  - job: control-plane-e2e
    lane_type: execution_only
    emits_coverage_artifact: false
    participates_in_hard_threshold: false
    threshold_enforced_in_job: false
    execution_confidence_role: e2e_control_plane
    notes: >-
      Control-plane completeness smoke gives execution confidence only; it does
      not feed the combined hard coverage threshold.
  - job: track-d-gates
    lane_type: execution_only
    emits_coverage_artifact: false
    participates_in_hard_threshold: false
    threshold_enforced_in_job: false
    execution_confidence_role: fixture_and_linkage_gate
    notes: >-
      Track D linkage and fixture gates are execution-focused and remain outside
      the hard coverage combine path.
  - job: memory-tests
    lane_type: execution_only
    emits_coverage_artifact: false
    participates_in_hard_threshold: false
    threshold_enforced_in_job: false
    execution_confidence_role: neo4j_memory_isolated_execution
    notes: >-
      Neo4j project-memory and MCP tests run in a dedicated execution lane so
      the main coverage-enforced path excludes environment-sensitive memory
      tooling without losing regression visibility.
  - job: test-fast
    lane_type: coverage_shard
    emits_coverage_artifact: true
    coverage_artifact: coverage-data-fast
    participates_in_hard_threshold: true
    threshold_enforced_in_job: false
    execution_confidence_role: fast_parallel_feedback
    notes: >-
      Fast unit and architecture execution contributes a coverage shard and
      quick execution feedback, but threshold enforcement remains centralized.
  - job: test-matrix
    lane_type: coverage_shard
    emits_coverage_artifact: true
    coverage_artifact: coverage-data-${matrix.test-group.name}
    coverage_python_versions:
      - "3.11"
    participates_in_hard_threshold: true
    threshold_enforced_in_job: false
    execution_confidence_role: breadth_parallel_execution
    notes: >-
      The matrix broadens execution confidence across unit, integration, and
      security suites, but only Python 3.11 legs emit coverage shards for the
      combined threshold.
  - job: coverage-verify
    lane_type: hard_threshold_gate
    emits_coverage_artifact: false
    downloads_coverage_artifacts: true
    participates_in_hard_threshold: true
    threshold_enforced_in_job: true
    execution_confidence_role: serial_plus_combined_threshold
    known_exclusions:
      - tests/e2e
      - tests/contract
    notes: >-
      Coverage verification combines shard artifacts, runs the canonical serial
      subset, and is the only lane that enforces the hard 85 percent coverage
      threshold. Contract, e2e, and dedicated memory tests are explicitly
      excluded from the serial pass here.
  - job: duration-telemetry
    lane_type: telemetry_only
    emits_coverage_artifact: false
    participates_in_hard_threshold: false
    threshold_enforced_in_job: false
    execution_confidence_role: slow_test_reporting
    notes: >-
      Duration telemetry consumes JUnit artifacts to build slow-test reports; it
      is informational and does not change hard coverage semantics.

================================================================================
File: compatibility_facade_inventory.yaml
Path: quality\compatibility_facade_inventory.yaml
================================================================================
version: 1
policy_scope: compatibility_facades
tracked_docstring_prefixes:
  - "Backward-compatible "
  - "Compatibility "
  - "Compatibility-"
  - "Deprecated compatibility"
  - "Composition-level compatibility"
  - "Pipeline factory compatibility-only facade"
  - "Storage compatibility-only facade"
transition_debt: []
retained_entrypoints:
  - path: "src/bioetl/interfaces/cli/commands/run.py"
    compatibility_role: "Retained public run command seam that shields the split internal owner module `bioetl.interfaces.cli.commands.domains.run.command`."
    canonical_target: "bioetl.interfaces.cli.commands.run"
    status: "retained-entrypoint"
    owner: "bioetl.interfaces.cli.commands"
    introduced_in: "2026-03 RF-024"
    review_date: "2026-09-30"
    allowed_call_sites: >-
      `src`: use `bioetl.interfaces.cli.commands.run` as the public seam; direct internal-owner imports stay confined to `src/bioetl/interfaces/cli/commands/domains/run/__init__.py`; `tests`: patch/import coverage may target `bioetl.interfaces.cli.commands.run`, while direct `bioetl.interfaces.cli.commands.domains.run.command` imports stay confined to dedicated boundary coverage
    migration_path: >-
      Use `bioetl.interfaces.cli.commands.run` for public CLI wiring and patch targets; do not import `bioetl.interfaces.cli.commands.domains.run.command` directly outside the owning package or dedicated boundary tests.
    exit_criteria: >-
      First-party src reaches the run command only through the retained public seam, and direct internal-owner imports remain confined to the owning package plus dedicated boundary tests.
  - path: "src/bioetl/interfaces/cli/commands/run_all.py"
    compatibility_role: "Retained public run-all command seam that shields the internal owner module `bioetl.interfaces.cli.commands.domains.run_all.command`."
    canonical_target: "bioetl.interfaces.cli.commands.run_all"
    status: "retained-entrypoint"
    owner: "bioetl.interfaces.cli.commands"
    introduced_in: "2026-03 RF-024"
    review_date: "2026-09-30"
    allowed_call_sites: >-
      `src`: use `bioetl.interfaces.cli.commands.run_all` as the public seam; direct internal-owner imports stay confined to `src/bioetl/interfaces/cli/commands/domains/run_all/__init__.py`; `tests`: patch/import coverage may target `bioetl.interfaces.cli.commands.run_all`, while direct `bioetl.interfaces.cli.commands.domains.run_all.command` imports stay confined to dedicated boundary coverage
    migration_path: >-
      Use `bioetl.interfaces.cli.commands.run_all` for public CLI wiring and patch targets; do not import `bioetl.interfaces.cli.commands.domains.run_all.command` directly outside the owning package or dedicated boundary tests.
    exit_criteria: >-
      First-party src reaches the run-all command only through the retained public seam, and direct internal-owner imports remain confined to the owning package plus dedicated boundary tests.
  - path: "src/bioetl/interfaces/cli/commands/run_composite.py"
    compatibility_role: "Retained public run-composite command seam that shields the internal owner module `bioetl.interfaces.cli.commands.domains.composite.command`."
    canonical_target: "bioetl.interfaces.cli.commands.run_composite"
    status: "retained-entrypoint"
    owner: "bioetl.interfaces.cli.commands"
    introduced_in: "2026-03 RF-024"
    review_date: "2026-09-30"
    allowed_call_sites: >-
      `src`: use `bioetl.interfaces.cli.commands.run_composite` as the public seam; direct internal-owner imports stay confined to `src/bioetl/interfaces/cli/commands/domains/composite/__init__.py`; `tests`: patch/import coverage may target `bioetl.interfaces.cli.commands.run_composite`, while direct `bioetl.interfaces.cli.commands.domains.composite.command` imports stay confined to dedicated boundary coverage
    migration_path: >-
      Use `bioetl.interfaces.cli.commands.run_composite` for public CLI wiring and patch targets; do not import `bioetl.interfaces.cli.commands.domains.composite.command` directly outside the owning package or dedicated boundary tests.
    exit_criteria: >-
      First-party src reaches the run-composite command only through the retained public seam, and direct internal-owner imports remain confined to the owning package plus dedicated boundary tests.
  - path: "src/bioetl/interfaces/cli/commands/health.py"
    compatibility_role: "Retained public health command seam that shields the internal owner module `bioetl.interfaces.cli.commands.domains.health.command`."
    canonical_target: "bioetl.interfaces.cli.commands.health"
    status: "retained-entrypoint"
    owner: "bioetl.interfaces.cli.commands"
    introduced_in: "2026-03 RF-024"
    review_date: "2026-09-30"
    allowed_call_sites: >-
      `src`: use `bioetl.interfaces.cli.commands.health` as the public seam; direct internal-owner imports stay confined to `src/bioetl/interfaces/cli/commands/domains/health/__init__.py`; `tests`: patch/import coverage may target `bioetl.interfaces.cli.commands.health`, while direct `bioetl.interfaces.cli.commands.domains.health.command` imports stay confined to dedicated boundary coverage
    migration_path: >-
      Use `bioetl.interfaces.cli.commands.health` for public CLI wiring and patch targets; do not import `bioetl.interfaces.cli.commands.domains.health.command` directly outside the owning package or dedicated boundary tests.
    exit_criteria: >-
      First-party src reaches the health command only through the retained public seam, and direct internal-owner imports remain confined to the owning package plus dedicated boundary tests.
  - path: "src/bioetl/interfaces/cli/commands/quarantine.py"
    compatibility_role: "Retained public quarantine command seam that shields the internal owner module `bioetl.interfaces.cli.commands.domains.quarantine.command`."
    canonical_target: "bioetl.interfaces.cli.commands.quarantine"
    status: "retained-entrypoint"
    owner: "bioetl.interfaces.cli.commands"
    introduced_in: "2026-03 RF-024"
    review_date: "2026-09-30"
    allowed_call_sites: >-
      `src`: use `bioetl.interfaces.cli.commands.quarantine` as the public seam; direct internal-owner imports stay confined to `src/bioetl/interfaces/cli/commands/domains/quarantine/__init__.py`; `tests`: patch/import coverage may target `bioetl.interfaces.cli.commands.quarantine`, while direct `bioetl.interfaces.cli.commands.domains.quarantine.command` imports stay confined to dedicated boundary coverage
    migration_path: >-
      Use `bioetl.interfaces.cli.commands.quarantine` for public CLI wiring and patch targets; do not import `bioetl.interfaces.cli.commands.domains.quarantine.command` directly outside the owning package or dedicated boundary tests.
    exit_criteria: >-
      First-party src reaches the quarantine command only through the retained public seam, and direct internal-owner imports remain confined to the owning package plus dedicated boundary tests.
  - path: "src/bioetl/interfaces/cli/commands/maintenance.py"
    compatibility_role: "Retained public maintenance command seam that shields the internal owner module `bioetl.interfaces.cli.commands.domains.maintenance.command`."
    canonical_target: "bioetl.interfaces.cli.commands.maintenance"
    status: "retained-entrypoint"
    owner: "bioetl.interfaces.cli.commands"
    introduced_in: "2026-03 RF-024"
    review_date: "2026-09-30"
    allowed_call_sites: >-
      `src`: use `bioetl.interfaces.cli.commands.maintenance` as the public seam; direct internal-owner imports stay confined to `src/bioetl/interfaces/cli/commands/domains/maintenance/__init__.py`; `tests`: import coverage may target `bioetl.interfaces.cli.commands.maintenance`, while direct `bioetl.interfaces.cli.commands.domains.maintenance.command` imports stay confined to dedicated boundary coverage
    migration_path: >-
      Use `bioetl.interfaces.cli.commands.maintenance` for public CLI wiring; do not import `bioetl.interfaces.cli.commands.domains.maintenance.command` directly outside the owning package or dedicated boundary tests.
    exit_criteria: >-
      First-party src reaches the maintenance command only through the retained public seam, and direct internal-owner imports remain confined to the owning package plus dedicated boundary tests.
  - path: "src/bioetl/interfaces/cli/commands/archive.py"
    compatibility_role: "Retained public archive command seam that shields the internal owner module `bioetl.interfaces.cli.commands.domains.maintenance.archive`."
    canonical_target: "bioetl.interfaces.cli.commands.archive"
    status: "retained-entrypoint"
    owner: "bioetl.interfaces.cli.commands"
    introduced_in: "2026-03 RF-024"
    review_date: "2026-09-30"
    allowed_call_sites: >-
      `src`: use `bioetl.interfaces.cli.commands.archive` only as the public seam for import/patch stability; direct internal-owner imports stay confined to `src/bioetl/interfaces/cli/commands/domains/maintenance/command.py`; `tests`: patch/import coverage may target `bioetl.interfaces.cli.commands.archive`, while direct `bioetl.interfaces.cli.commands.domains.maintenance.archive` imports stay confined to dedicated boundary coverage
    migration_path: >-
      Use `bioetl.interfaces.cli.commands.archive` for public patch targets; do not import `bioetl.interfaces.cli.commands.domains.maintenance.archive` directly outside the owning maintenance package or dedicated boundary tests.
    exit_criteria: >-
      First-party src keeps direct archive-owner imports confined to the owning maintenance package, and public patch/import coverage remains on the retained top-level seam.
  - path: "src/bioetl/interfaces/cli/commands/cleanup.py"
    compatibility_role: "Retained public cleanup command seam that shields the internal owner module `bioetl.interfaces.cli.commands.domains.maintenance.cleanup`."
    canonical_target: "bioetl.interfaces.cli.commands.cleanup"
    status: "retained-entrypoint"
    owner: "bioetl.interfaces.cli.commands"
    introduced_in: "2026-03 RF-024"
    review_date: "2026-09-30"
    allowed_call_sites: >-
      `src`: use `bioetl.interfaces.cli.commands.cleanup` only as the public seam for import/patch stability; direct internal-owner imports stay confined to `src/bioetl/interfaces/cli/commands/domains/maintenance/command.py`; `tests`: patch/import coverage may target `bioetl.interfaces.cli.commands.cleanup`, while direct `bioetl.interfaces.cli.commands.domains.maintenance.cleanup` imports stay confined to dedicated boundary coverage
    migration_path: >-
      Use `bioetl.interfaces.cli.commands.cleanup` for public patch targets; do not import `bioetl.interfaces.cli.commands.domains.maintenance.cleanup` directly outside the owning maintenance package or dedicated boundary tests.
    exit_criteria: >-
      First-party src keeps direct cleanup-owner imports confined to the owning maintenance package, and public patch/import coverage remains on the retained top-level seam.
  - path: "src/bioetl/interfaces/cli/commands/vacuum.py"
    compatibility_role: "Retained public vacuum command seam that shields the internal owner module `bioetl.interfaces.cli.commands.domains.maintenance.vacuum`."
    canonical_target: "bioetl.interfaces.cli.commands.vacuum"
    status: "retained-entrypoint"
    owner: "bioetl.interfaces.cli.commands"
    introduced_in: "2026-03 RF-024"
    review_date: "2026-09-30"
    allowed_call_sites: >-
      `src`: use `bioetl.interfaces.cli.commands.vacuum` only as the public seam for import/patch stability; direct internal-owner imports stay confined to `src/bioetl/interfaces/cli/commands/domains/maintenance/command.py`; `tests`: patch/import coverage may target `bioetl.interfaces.cli.commands.vacuum`, while direct `bioetl.interfaces.cli.commands.domains.maintenance.vacuum` imports stay confined to dedicated boundary coverage
    migration_path: >-
      Use `bioetl.interfaces.cli.commands.vacuum` for public patch targets; do not import `bioetl.interfaces.cli.commands.domains.maintenance.vacuum` directly outside the owning maintenance package or dedicated boundary tests.
    exit_criteria: >-
      First-party src keeps direct vacuum-owner imports confined to the owning maintenance package, and public patch/import coverage remains on the retained top-level seam.
  - path: "src/bioetl/composition/entrypoints.py"
    compatibility_role: "Canonical composition entrypoint that intentionally shields internal `_pipeline_execution`, `_resource_management`, and `_services` module paths."
    canonical_target: "bioetl.composition.entrypoints"
    status: "retained-entrypoint"
    owner: "bioetl.composition"
    introduced_in: "2026-03 entrypoint freeze"
    review_date: "2026-09-30"
    allowed_call_sites: >-
      `src`: canonical entrypoint usage allowed; `tests`: public entrypoint imports may appear in interface/composition boundary coverage, but direct internal-module patch targets stay confined to `tests/unit/composition/test_entrypoints.py`, `tests/unit/composition/test_resource_management.py`, and `tests/unit/composition/test_services_entrypoints.py`
    migration_path: >-
      Use `bioetl.composition.entrypoints` as the public seam; do not import `bioetl.composition._pipeline_execution`, `bioetl.composition._resource_management`, or `bioetl.composition._services` directly outside dedicated entrypoint-boundary coverage.
    exit_criteria: >-
      Internal implementation-module imports outside `composition/` stay at zero and internal-module patch coverage remains confined to the dedicated entrypoint-boundary tests.
  - path: "src/bioetl/domain/composite/config.py"
    compatibility_role: "Canonical public entrypoint for composite config models that shields split config internals."
    canonical_target: "bioetl.domain.composite.config"
    status: "retained-entrypoint"
    owner: "bioetl.domain.composite"
    introduced_in: "legacy-pre-2026-03"
    review_date: "2026-09-30"
    allowed_call_sites: >-
      `src`: canonical entrypoint usage allowed; internal split modules stay inside `src/bioetl/domain/composite/`; `tests`: direct split-internal coverage stays confined to `tests/unit/domain/composite/test_composite_config_facade.py` and `tests/unit/domain/composite/test_composite_config_edge_cases.py`, while ordinary tests keep importing the root config entrypoint
    migration_path: >-
      Keep using `bioetl.domain.composite.config`; do not import split `config_*` internals outside the owning package or the dedicated composite-config coverage tests.
    exit_criteria: >-
      Direct imports of split config internals remain confined to the owning package plus the dedicated composite-config coverage tests, and the root config entrypoint stays the stable public path.
  - path: "src/bioetl/domain/value_objects/activity_values.py"
    compatibility_role: "Canonical public entrypoint for activity-related value objects that shields split concentration/type/pChEMBL modules."
    canonical_target: "bioetl.domain.value_objects.activity_values"
    status: "retained-entrypoint"
    owner: "bioetl.domain.value_objects"
    introduced_in: "legacy-pre-2026-03"
    review_date: "2026-09-30"
    allowed_call_sites: >-
      `src`: canonical entrypoint usage allowed; internal split modules stay inside `src/bioetl/domain/value_objects/`; `tests`: direct split-internal coverage stays confined to `tests/unit/domain/value_objects/test_value_object_facade_reexports.py`, while ordinary tests keep importing the public entrypoint
    migration_path: >-
      Keep using `bioetl.domain.value_objects.activity_values`; do not import split value-object internals outside the owning package or the dedicated facade-coverage test.
    exit_criteria: >-
      Direct imports of split activity-value internals remain confined to the owning package plus the dedicated facade-coverage test, and the facade stays the stable public path.
  - path: "src/bioetl/domain/value_objects/publication_field_groups.py"
    compatibility_role: "Canonical public entrypoint for publication field-group definitions that shields private split config/type modules."
    canonical_target: "bioetl.domain.value_objects.publication_field_groups"
    status: "retained-entrypoint"
    owner: "bioetl.domain.value_objects"
    introduced_in: "legacy-pre-2026-03"
    review_date: "2026-09-30"
    allowed_call_sites: >-
      `src`: canonical entrypoint usage allowed; private split modules stay inside `src/bioetl/domain/value_objects/`; `tests`: direct split-internal coverage stays confined to `tests/unit/domain/value_objects/test_value_object_facade_reexports.py`, while ordinary tests keep importing the public entrypoint
    migration_path: >-
      Keep using `bioetl.domain.value_objects.publication_field_groups`; do not import split value-object internals outside the owning package or the dedicated facade-coverage test.
    exit_criteria: >-
      Direct imports of private publication-field-group internals remain confined to the owning package plus the dedicated facade-coverage test, and the facade stays the stable public path.
  - path: "src/bioetl/application/composite/merger.py"
    compatibility_role: "Canonical composite merge module that requires `MergeCollaboratorGroup` bundle; legacy per-collaborator keyword wiring removed in RF-009.2."
    canonical_target: "bioetl.application.composite.merger"
    status: "retained-entrypoint"
    owner: "bioetl.application.composite"
    introduced_in: "2026-03 merge collaborator migration"
    review_date: "2026-09-30"
    allowed_call_sites: >-
      `src`: all wiring passes `collaborators=MergeCollaboratorGroup(...)`; `tests`: `tests/unit/application/composite/test_merger.py`, `tests/unit/application/composite/merge_test_support.py`, `tests/unit/composition/bootstrap/runtime/test_composite_support_services_factory.py`
    migration_path: >-
      Use `bioetl.application.composite.merger` with `collaborators=MergeCollaboratorGroup(...)`.
    exit_criteria: >-
      All composition paths use collaborator bundles; legacy keyword wiring fully removed.
  - path: "src/bioetl/infrastructure/adapters/pubmed/client.py"
    compatibility_role: "Retained client entrypoint that shields older `pubmed_client` imports while exporting the current adapter surface and public `create_pubmed_adapter` factory alias."
    canonical_target: "bioetl.infrastructure.adapters.pubmed.client"
    status: "retained-entrypoint"
    owner: "bioetl.infrastructure.adapters.pubmed"
    introduced_in: "2026-03 pubmed entrypoint hardening"
    review_date: "2026-09-30"
    allowed_call_sites: >-
      `src`: direct `bioetl.infrastructure.adapters.pubmed.client` imports stay confined to `src/bioetl/infrastructure/adapters/pubmed/__init__.py`; first-party code imports the provider package root; `tests`: `tests/unit/infrastructure/adapters/test_provider_entrypoints.py`, `tests/architecture/test_adapter_contracts.py`, `tests/architecture/test_retained_adapter_entrypoint_policy.py`
    migration_path: >-
      Use the provider package root `bioetl.infrastructure.adapters.pubmed` in new first-party code; keep `bioetl.infrastructure.adapters.pubmed.client` only as the retained public seam and do not import `bioetl.infrastructure.adapters.pubmed.pubmed_client` directly.
    exit_criteria: >-
      RF-035 decision is `retain`: direct `client.py` imports stay confined to the provider package root plus dedicated compatibility coverage, and private `_create_pubmed_adapter` remains unexported from the retained entrypoint.
  - path: "src/bioetl/infrastructure/adapters/semanticscholar/client.py"
    compatibility_role: "Retained client entrypoint that shields older `adapter` imports."
    canonical_target: "bioetl.infrastructure.adapters.semanticscholar.client"
    status: "retained-entrypoint"
    owner: "bioetl.infrastructure.adapters.semanticscholar"
    introduced_in: "legacy-pre-2026-03"
    review_date: "2026-09-30"
    allowed_call_sites: >-
      `src`: direct `bioetl.infrastructure.adapters.semanticscholar.client` imports stay confined to `src/bioetl/infrastructure/adapters/semanticscholar/__init__.py`; first-party code imports the provider package root; `tests`: `tests/unit/infrastructure/adapters/test_provider_entrypoints.py`, `tests/architecture/test_adapter_contracts.py`, `tests/architecture/test_retained_adapter_entrypoint_policy.py`
    migration_path: >-
      Use the provider package root `bioetl.infrastructure.adapters.semanticscholar` in new first-party code; keep `bioetl.infrastructure.adapters.semanticscholar.client` only as the retained public seam and do not import `bioetl.infrastructure.adapters.semanticscholar.adapter` directly.
    exit_criteria: >-
      RF-035 decision is `retain`: direct `client.py` imports stay confined to the provider package root plus dedicated compatibility coverage, and legacy-path references remain reduced to that retained seam.
measured_only_ratchet:
  max_total_modules: 31
  scoped_limits:
    - path_prefix: "src/bioetl/application/services/"
      max_modules: 15
    - path_prefix: "src/bioetl/interfaces/cli/commands/"
      max_modules: 6
measured_only_review_workflow:
  review_cadence: "quarterly"
  required_checks:
    - "verify no first-party src imports remain"
    - "confirm measured-only docstring tracking stays aligned with the YAML allowlist"
    - "run targeted owner tests before deciding retain, promote, or remove"
    - "refresh the generated compatibility snapshot after lifecycle changes"
  allowed_outcomes:
    - "retain"
    - "promote"
    - "remove"
  promotion_requires_curated_row: true
measured_only_modules:
  - path: "src/bioetl/application/pipelines/chembl/_pipelines.py"
    owner: "bioetl.application.pipelines.chembl"
    reason: "Compatibility re-export surface for ChEMBL pipeline marker classes."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/interfaces/cli/commands/quarantine_execution.py"
    owner: "bioetl.interfaces.cli.commands"
    reason: "Compatibility support seam for quarantine execution helper imports; first-party src should keep importing the canonical domains.quarantine.execution module directly."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/interfaces/cli/commands/quarantine_rendering.py"
    owner: "bioetl.interfaces.cli.commands"
    reason: "Compatibility support seam for quarantine rendering helper imports; first-party src should keep importing the canonical domains.quarantine.rendering module directly."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/interfaces/cli/commands/quarantine_support.py"
    owner: "bioetl.interfaces.cli.commands"
    reason: "Compatibility support seam for test-facing quarantine helper imports; first-party src should keep importing the canonical domains.quarantine.support module directly."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/interfaces/cli/commands/health_rendering.py"
    owner: "bioetl.interfaces.cli.commands"
    reason: "Compatibility support seam for health rendering helper imports; first-party src should keep importing the canonical domains.health.rendering module directly."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/interfaces/cli/commands/health_server_integration.py"
    owner: "bioetl.interfaces.cli.commands"
    reason: "Compatibility support seam for test-facing health-server integration imports; first-party src should keep importing the canonical domains.health.server_integration module directly."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/domain/normalization_authors.py"
    owner: "bioetl.domain"
    reason: "Deprecated compatibility wrapper for author normalization imports while callers migrate to bioetl.domain.normalization.authors."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/domain/normalization_chembl.py"
    owner: "bioetl.domain"
    reason: "Deprecated compatibility wrapper for ChEMBL normalization imports while callers migrate to bioetl.domain.normalization.chembl."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/domain/normalization_dates.py"
    owner: "bioetl.domain"
    reason: "Deprecated compatibility wrapper for date normalization imports while callers migrate to bioetl.domain.normalization.dates."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/domain/normalization_pages.py"
    owner: "bioetl.domain"
    reason: "Deprecated compatibility wrapper for page-range normalization imports while callers migrate to bioetl.domain.normalization.pages."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/domain/services/_date_helpers.py"
    owner: "bioetl.domain.services"
    reason: "Compatibility helper seam for legacy date-service imports that now delegate to bioetl.domain.normalization.dates."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/interfaces/cli/commands/metrics_server_integration.py"
    owner: "bioetl.interfaces.cli.commands"
    reason: "Compatibility support seam for test-facing metrics-server integration imports; first-party src should keep importing the canonical domains.health.metrics_server_integration module directly."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/application/services/cli_run_orchestration_contracts.py"
    owner: "bioetl.application.services.execution"
    reason: "Compatibility facade for legacy CLI orchestration contract imports while first-party code keeps using bioetl.application.services.execution.cli_run_orchestration_contracts."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/application/services/cli_run_orchestration_models.py"
    owner: "bioetl.application.services.execution"
    reason: "Compatibility facade for legacy CLI orchestration model imports while first-party code keeps using bioetl.application.services.execution.cli_run_orchestration_models."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/application/services/cli_run_orchestration_service.py"
    owner: "bioetl.application.services.execution"
    reason: "Compatibility facade for legacy CLI orchestration service imports while first-party code keeps using bioetl.application.services.execution.cli_run_orchestration_service."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/application/services/effective_config_service.py"
    owner: "bioetl.application.services.control_plane"
    reason: "Compatibility facade for effective-config service imports while first-party code keeps using bioetl.application.services.control_plane.effective_config_service."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/application/services/lineage_inspection_service.py"
    owner: "bioetl.application.services.lineage"
    reason: "Compatibility facade for lineage inspection imports while first-party code keeps using bioetl.application.services.lineage.lineage_inspection_service."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/application/services/metadata_coordinator.py"
    owner: "bioetl.application.services.lineage"
    reason: "Compatibility facade for metadata coordinator imports while first-party code keeps using bioetl.application.services.lineage.metadata_coordinator."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/application/services/pipeline_run_context_service.py"
    owner: "bioetl.application.services.execution"
    reason: "Compatibility facade for pipeline run-context imports while first-party code keeps using bioetl.application.services.execution.pipeline_run_context_service."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/application/services/pipeline_run_execution_service.py"
    owner: "bioetl.application.services.execution"
    reason: "Compatibility facade for pipeline execution service imports while first-party code keeps using bioetl.application.services.execution.pipeline_run_execution_service."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/application/services/pipeline_run_lifecycle_service.py"
    owner: "bioetl.application.services.execution"
    reason: "Compatibility facade for pipeline lifecycle service imports while first-party code keeps using bioetl.application.services.execution.pipeline_run_lifecycle_service."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/application/services/pipeline_runner_models.py"
    owner: "bioetl.application.services.execution"
    reason: "Compatibility facade for pipeline runner model imports while first-party code keeps using bioetl.application.services.execution.pipeline_runner_models."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/application/services/pipeline_runner_service.py"
    owner: "bioetl.application.services.execution"
    reason: "Compatibility facade for pipeline runner service imports while first-party code keeps using bioetl.application.services.execution.pipeline_runner_service."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/application/services/run_ledger_service.py"
    owner: "bioetl.application.services.control_plane"
    reason: "Compatibility facade for run-ledger service imports while first-party code keeps using bioetl.application.services.control_plane.run_ledger_service."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/application/services/run_manifest_diagnostics.py"
    owner: "bioetl.application.services.control_plane"
    reason: "Compatibility facade for run-manifest diagnostics imports while first-party code keeps using bioetl.application.services.control_plane.run_manifest_diagnostics."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/application/services/run_manifest_inspection_service.py"
    owner: "bioetl.application.services.control_plane"
    reason: "Compatibility facade for run-manifest inspection imports while first-party code keeps using bioetl.application.services.control_plane.run_manifest_inspection_service."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/application/services/run_manifest_service.py"
    owner: "bioetl.application.services.control_plane"
    reason: "Compatibility facade for run-manifest service imports while first-party code keeps using bioetl.application.services.control_plane.run_manifest_service."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/composition/bootstrap/runtime/composite_infrastructure_context.py"
    owner: "bioetl.composition.bootstrap.runtime"
    reason: "Compatibility shim for runtime bootstrap imports that still target the legacy composite infrastructure context path while the canonical owner lives under bioetl.composition.bootstrap."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/domain/transformations/_hashing_normalization.py"
    owner: "bioetl.domain.transformations"
    reason: "Compatibility shim for hash-normalization imports while first-party code keeps using bioetl.domain.transformations.hashing."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/infrastructure/adapters/crossref/batch.py"
    owner: "bioetl.infrastructure.adapters.crossref"
    reason: "Compatibility facade for CrossRef batch and pagination collaborators."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"
  - path: "src/bioetl/infrastructure/storage/_audit_normalization.py"
    owner: "bioetl.infrastructure.storage"
    reason: "Compatibility shim for audit normalization helper imports while first-party code keeps using bioetl.infrastructure.storage.audit_normalization."
    review_date: "2026-09-30"
    new_code_policy: "no-new-first-party-imports"
    promotion_trigger: "sanctioned-public-seam"

================================================================================
File: constructor_waivers.yaml
Path: quality\constructor_waivers.yaml
================================================================================
# RF-017 Constructor Waivers
# Policy:
# - Max TTL for waivers is 6 months from current date.
# - All out-of-scope classes must have a documented reason, owner, and expiry.
# - Temporary waivers for Wave 1 classes will be removed at the end of RF-017.

# --- Wave 2: Out-of-Scope (Infrastructure & Domain Aggregates) ---

QuarantineEntry:
  allowed_args: 9
  reason: "Domain aggregate; wide state constructor is valid."
  owner: "@core-team"
  expiry_date: "2026-09-15"

PubChemAdapter:
  allowed_args: 10
  reason: "Requires separate infrastructure wave."
  owner: "@bioetl-platform"
  expiry_date: "2026-06-01"

PubChemFetchStrategies:
  allowed_args: 9
  reason: "Adapter refactoring out of scope."
  owner: "@bioetl-platform"
  expiry_date: "2026-06-01"

UniProtAdapter:
  allowed_args: 10
  reason: "Adapter refactoring out of scope."
  owner: "@bioetl-platform"
  expiry_date: "2026-06-01"

================================================================================
File: debt_scorecard.yaml
Path: quality\debt_scorecard.yaml
================================================================================
schema_version: 1
baseline:
  total_exemptions: 24
  by_registry:
    file_size_limits: 2
    function_complexity: 0
    function_length: 10
    class_size: 9
    class_method_count: 0
    god_object: 3
    domain_complexity: 0
historical_baseline:
  total_exemptions: 44
  by_registry:
    file_size_limits: 6
    function_complexity: 6
    function_length: 10
    class_size: 13
    class_method_count: 0
    god_object: 3
    domain_complexity: 6
  snapshot_date: '2025-12-31'
  source_report: reports/architecture/2025-Q4-final.json
governance:
  baseline_policy:
    enforceable_section: baseline
    historical_section: historical_baseline
    registry_sync_source: baseline
    rationale: Stabilizing architecture metrics through baseline ratcheting.
  coarse_budgets:
    ruff_error_count:
      max_count: 0
      owner: '@bioetl-architecture'
      linked_rf: RF-ARCH-009
      rationale: Ruff backlog for src/bioetl has been retired; CI now enforces zero
        source-level lint debt.
      ratchet_policy: ratchet only downward from zero
    mypy_error_count:
      max_count: 0
      owner: '@bioetl-architecture'
      linked_rf: RF-ARCH-015
      rationale: Strict typing is already stabilized repo-wide and stays zero-budget.
      ratchet_policy: ratchet only downward from zero
    architecture_skip_count:
      max_count: 7
      owner: '@bioetl-architecture'
      linked_rf: RF-ARCH-015
      rationale: Marker-skip budget remains explicit until historical skip debt is
        fully retired.
      ratchet_policy: ratchet only after skip inventory shrinks
  review_policy:
    new_exemption_requires:
    - value
    - owner
    - reason
    - classification
    - linked_rf
    - expires_on
    - removal_step
    reviewer_checks:
    - classification is technical_debt or intentional_exception
    - linked_rf points to active
    - placeholder exemptions require concrete technical follow-up
    - '2026-06-30'
  owner_diversification:
    starts_quarter: 2026-Q2
    min_distinct_owners: 3
  owner_registry_q2_subsystems:
    architecture:
      owner: '@bioetl-architecture'
    platform:
      owner: '@bioetl-platform'
    data_model:
      owner: '@bioetl-data-model'
  temporary_exemptions:
    window_policy: budget-only
    max_window_days: 30
  growth_section_gate_rollout:
    default_mode: block
    warn_until_by_section:
      registry:file_size_limits: '2026-06-30'
  burn_down_priorities:
    registries:
    - file_size_limits
    - class_size
    - god_object
  allow_grace_windows_only_for_rf: true
  review_cycle: 90
  quarterly_burndown_target: 2
  allowed_classifications:
  - architectural_debt
  - interface_debt
  - domain_complexity
  - technical_debt
  - transitional_compat
  - legacy_artifact
  - intentional_exception
registry_groups:
  size_metrics:
    registries:
    - file_size_limits
    - function_length
    - class_size
  complexity_metrics:
    registries:
    - function_complexity
    - domain_complexity
  structural_debt:
    registries:
    - god_object
    - class_method_count
registries:
  file_size_limits:
    target_count: 10
    total_loc_budget: 20000
  class_size:
    target_count: 5
  function_complexity:
    max_cc_threshold: 15
  god_object:
    max_count: 2
hotspot_budgets:
- name: core_orchestration
  rationale: Critical orchestration logic hotspot.
  path_prefixes:
  - src/bioetl/application/core/
  registry_budgets:
    file_size_limits: 1
    class_size: 3
    god_object: 1
- name: composite_orchestration
  rationale: Composite runtime orchestration hotspot spanning join, checkpoint, and
    runner support seams.
  path_prefixes:
  - src/bioetl/application/composite/
  registry_budgets:
    file_size_limits: 1
    class_size: 1
    god_object: 1
report_only_hotspot_families:
  snapshot_date: '2026-03-24'
  mode: report-only
  artifact_policy:
    duplication_command: make qa-hotspot-report
    baseline_artifact: reports/quality/hotspot-duplication-baseline.json
    history_artifact: reports/quality/hotspot-duplication-history.jsonl
    latest_reviewed_snapshot: '2026-03-24'
    confirming_clean_snapshots_required: 2
    expected_direction: downward
    ratchet_policy: Keep the hotspot layer report-only at the repo level; once a zero-duplication
      family has two confirming clean snapshots, activate bounded family-level duplication,
      file-growth, and fan-in ratchets from reviewed scorecard baselines.
  families:
  - name: application_core
    owner: '@bioetl-architecture'
    linked_rf: RF-023
    ratchet_stage: active
    ratchet_scope: duplication-only
    expected_action: Hold duplication at zero via an active family-level ratchet and
      cap both file-growth and fan-in at the reviewed baseline during core orchestration
      changes.
    path_prefixes:
    - src/bioetl/application/core/
    bounded_growth_budgets:
      files_ge_250_loc: 18
      max_internal_fan_in: 22
    metrics:
      duplication_clusters: 0
      files: 81
      total_loc: 12259
      files_ge_250_loc: 18
      helper_function_ratio: 0.46
      max_internal_fan_in: 22
      max_internal_fan_in_module: bioetl.application.core.base_transformer
    trend:
      status: down_vs_2026-03-23
      next_action: 2026-04-08 adds bounded files_ge_250_loc and max_internal_fan_in
        caps at the reviewed baseline for application/core while keeping the family
        duplication ratchet active.
  - name: composition_bootstrap_runtime
    owner: '@bioetl-platform'
    linked_rf: RF-023
    ratchet_stage: active
    ratchet_scope: duplication-only
    expected_action: Hold duplication at zero via an active family-level ratchet and
      cap both file-growth and fan-in at the reviewed baseline during runtime/bootstrap
      changes.
    path_prefixes:
    - src/bioetl/composition/bootstrap/runtime/
    bounded_growth_budgets:
      files_ge_250_loc: 6
      max_internal_fan_in: 6
    metrics:
      duplication_clusters: 0
      files: 27
      total_loc: 3163
      files_ge_250_loc: 6
      helper_function_ratio: 0.333
      max_internal_fan_in: 5
      max_internal_fan_in_module: bioetl.composition.bootstrap.runtime.observability
    trend:
      status: down_vs_2026-03-23
      next_action: 2026-04-08 adds bounded files_ge_250_loc and max_internal_fan_in
        caps at the current reviewed baseline for composition/bootstrap/runtime.
  - name: composition_factories_pipeline
    owner: '@bioetl-platform'
    linked_rf: RF-023
    ratchet_stage: active
    ratchet_scope: duplication-only
    expected_action: Hold duplication at zero via an active family-level ratchet and
      cap both file-growth and fan-in at the reviewed baseline during pipeline-factory
      changes.
    path_prefixes:
    - src/bioetl/composition/factories/pipeline/
    bounded_growth_budgets:
      files_ge_250_loc: 4
      max_internal_fan_in: 6
    metrics:
      duplication_clusters: 0
      files: 22
      total_loc: 2589
      files_ge_250_loc: 4
      helper_function_ratio: 0.469
      max_internal_fan_in: 6
      max_internal_fan_in_module: bioetl.composition.factories.pipeline.registry
    trend:
      status: down_vs_2026-03-23
      next_action: 2026-04-08 adds bounded files_ge_250_loc and max_internal_fan_in
        caps at the current reviewed baseline for composition/factories/pipeline.
removable_complexity_family_ratchets:
  snapshot_date: '2026-04-13'
  update_policy: Only raise budgets after an intentional reviewed baseline refresh
    tied to a closed cleanup issue.
  families:
  - name: adapter_layer
    owner: '@bioetl-platform'
    linked_issue: '2910'
    path_prefixes:
    - src/bioetl/infrastructure/adapters/
    family_budgets:
      files_ge_250_loc: 19
      max_internal_fan_in: 31
    tracked_seams:
    - path: src/bioetl/infrastructure/adapters/http/_health_monitor_support.py
      max_lines: 40
      required_modules:
      - bioetl.infrastructure.adapters.http._health_monitor_observability
      - bioetl.infrastructure.adapters.http._health_monitor_transitions
  - name: composite_layer
    owner: '@bioetl-architecture'
    linked_issue: '2910'
    path_prefixes:
    - src/bioetl/application/composite/
    family_budgets:
      files_ge_250_loc: 19
      max_internal_fan_in: 25
    tracked_seams:
    - path: src/bioetl/application/composite/runner_pkg/runner_summary_helpers.py
      max_lines: 130
      required_symbols:
      - EnrichmentSummary
      - _summarize_enrichment_results
    - path: src/bioetl/application/composite/fsm_helper.py
      max_lines: 260
      required_symbols:
      - ResumePhaseInfo
      - _resolve_resume_phase
neo4j_memory_calibration:
  snapshot_date: '2026-04-13'
  update_policy: When Neo4j memory refresh flags zero-anchor retirement or complexity
    hotspots, record the reviewed expectation here and keep retirement_candidate_triage.yaml
    aligned.
  families:
  - name: adapter_layer
    linked_issue: '2943'
    candidates:
    - module_path: src/bioetl/infrastructure/adapters/_cached_bronze_support.py
      expected_disposition: retain_active
    - module_path: src/bioetl/infrastructure/adapters/_circuit_breaker_contract.py
      expected_disposition: retain_active
    - module_path: src/bioetl/infrastructure/adapters/_error_handling_support.py
      expected_disposition: retain_active
    - module_path: src/bioetl/infrastructure/adapters/_health_check_observability.py
      expected_disposition: retain_active
    - module_path: src/bioetl/infrastructure/adapters/_health_check_policy.py
      expected_disposition: retain_active
  - name: composite_layer
    linked_issue: '2943'
    candidates:
    - module_path: src/bioetl/application/composite/runner_pkg/runner_merge_stage_flow.py
      expected_disposition: removed
    - module_path: src/bioetl/application/composite/runner_pkg/runner_support_flow.py
      expected_disposition: retain_active
    - module_path: src/bioetl/application/composite/runner_pkg/runner_support_mixin.py
      expected_disposition: retain_active
    - module_path: src/bioetl/application/composite/runner_pkg/runner_support_policy.py
      expected_disposition: retain_active
    - module_path: src/bioetl/application/composite/runner_pkg/runner_support_runtime.py
      expected_disposition: retain_active
    - module_path: src/bioetl/application/composite/runner_pkg/runner_support_types.py
      expected_disposition: retain_active
    - module_path: src/bioetl/application/composite/runtime_models.py
      expected_disposition: retain_active
    - module_path: src/bioetl/application/composite/runtime_wiring_api.py
      expected_disposition: retain_active
quarterly_targets:
- quarter: 2026-Q1
  max_total_exemptions: 29
  min_integral_score: 65
  group_budgets:
    size_metrics: 26
    complexity_metrics: 1
    structural_debt: 4
  registry_budgets:
    file_size_limits: 4
    function_complexity: 1
    function_length: 11
    class_size: 14
    class_method_count: 0
    god_object: 4
    domain_complexity: 6
- quarter: 2026-Q2
  max_total_exemptions: 28
  min_integral_score: 70
  group_budgets:
    size_metrics: 25
    complexity_metrics: 0
    structural_debt: 3
  registry_budgets:
    file_size_limits: 3
    function_complexity: 0
    function_length: 10
    class_size: 13
    class_method_count: 0
    god_object: 3
    domain_complexity: 0
owner_decomposition_targets:
- quarter: 2026-Q1
  allocations:
    '@bioetl-architecture': 3
    '@bioetl-platform': 17
    '@bioetl-data-model': 9
- quarter: 2026-Q2
  allocations:
    '@bioetl-architecture': 2
    '@bioetl-platform': 17
    '@bioetl-data-model': 9
expiry_decomposition_targets:
- quarter: 2026-Q1
  max_entries_expiring_in_quarter: 29
- quarter: 2026-Q2
  max_entries_expiring_in_quarter: 28
program_done_criteria:
  deadline_quarter: 2027-Q1
  max_total_exemptions: 0
  min_integral_score: 100
  max_expired_entries: 0

================================================================================
File: activity.yaml
Path: quality\entities\composite\activity.yaml
================================================================================
# Composite DQ stub: relaxed thresholds (0.10/0.30 vs default 0.05/0.20)
# for multi-source composite pipelines where data quality varies by provider.
# Keep even if empty — DQConfigLoader reads these at runtime.
version: "1.0.0"
provider: composite
entity: activity

dq_overrides:
  soft_fail_threshold: 0.10
  hard_fail_threshold: 0.30
  required_fields: []

================================================================================
File: assay.yaml
Path: quality\entities\composite\assay.yaml
================================================================================
# Composite DQ stub: relaxed thresholds (0.10/0.30 vs default 0.05/0.20)
# for multi-source composite pipelines where data quality varies by provider.
# Keep even if empty — DQConfigLoader reads these at runtime.
version: "1.0.0"
provider: composite
entity: assay

dq_overrides:
  soft_fail_threshold: 0.10
  hard_fail_threshold: 0.30
  required_fields: []

================================================================================
File: molecule.yaml
Path: quality\entities\composite\molecule.yaml
================================================================================
# Composite DQ stub: relaxed thresholds (0.10/0.30 vs default 0.05/0.20)
# for multi-source composite pipelines where data quality varies by provider.
# Keep even if empty — DQConfigLoader reads these at runtime.
version: "1.0.0"
provider: composite
entity: molecule

dq_overrides:
  soft_fail_threshold: 0.10
  hard_fail_threshold: 0.30
  required_fields: []

================================================================================
File: publication.yaml
Path: quality\entities\composite\publication.yaml
================================================================================
version: "1.0.0"
provider: composite
entity: publication

dq_overrides:
  soft_fail_threshold: 0.10
  hard_fail_threshold: 0.30
  required_fields:
    - publication_id
    - title

  entity_field_validations:
    # === Quality Indicators (CRITICAL) ===
    is_retracted:
      type: boolean
      nullable: false  # OpenAlex always provides this
      description: "Retraction status - CRITICAL for data integrity"

    # === Citation Metrics ===
    influential_citation_count:
      type: integer
      nullable: true
      min_value: 0
      description: "SemanticScholar influential citations (non-negative)"

    fwci:
      type: float
      nullable: true
      min_value: 0.0
      description: "OpenAlex Field-Weighted Citation Impact (non-negative)"

    # === JSON Array Fields (schema validation) ===
    author_orcids:
      type: json_array
      nullable: true
      description: "JSON array of ORCID identifiers"

    author_details:
      type: json_array
      nullable: true
      description: "JSON array of author objects (CrossRef)"

    author_s2_ids:
      type: json_array
      nullable: true
      description: "JSON array of S2 author IDs (40-char hex)"

    author_openalex_ids:
      type: json_array
      nullable: true
      description: "JSON array of OpenAlex author IDs (e.g., A1234567890)"

    author_h_indices:
      type: json_array
      nullable: true
      description: "JSON array of author h-index values"

    subject_topics:
      type: json_array
      nullable: true
      description: "OpenAlex hierarchical topics"

    primary_topic:
      type: json_object
      nullable: true
      description: "OpenAlex primary topic (single object)"

    grants:
      type: json_array
      nullable: true
      description: "OpenAlex funding/grant information"

    references:
      type: json_array
      nullable: true
      description: "CrossRef cited references"

    citation_contexts:
      type: json_array
      nullable: true
      description: "SemanticScholar citation context sentences"

    chemicals:
      type: json_array
      nullable: true
      description: "PubMed chemical substances"

    databanks:
      type: json_array
      nullable: true
      description: "PubMed databank accessions"

    gene_symbols:
      type: json_array
      nullable: true
      description: "PubMed gene symbols"

    affiliation_list:
      type: json_array
      nullable: true
      description: "Author affiliations (multiple providers)"

    institution_ids:
      type: json_array
      nullable: true
      description: "OpenAlex institution IDs (e.g., I1234567890)"

    institution_country_codes:
      type: json_array
      nullable: true
      description: "OpenAlex institution country codes (ISO 2-letter, e.g., US, GB)"

    # === String Identifiers ===
    pii:
      type: string
      nullable: true
      description: "PubMed Publisher Item Identifier"

    mid:
      type: string
      nullable: true
      description: "PubMed Manuscript ID"

    publisher_id:
      type: string
      nullable: true
      description: "PubMed publisher-specific identifier"

    dblp_id:
      type: string
      nullable: true
      description: "SemanticScholar DBLP key"

    mag_id:
      type: string
      nullable: true
      description: "OpenAlex MAG legacy ID"

================================================================================
File: target.yaml
Path: quality\entities\composite\target.yaml
================================================================================
# Composite DQ stub: relaxed thresholds (0.10/0.30 vs default 0.05/0.20)
# for multi-source composite pipelines where data quality varies by provider.
# Keep even if empty — DQConfigLoader reads these at runtime.
version: "1.0.0"
provider: composite
entity: target

dq_overrides:
  soft_fail_threshold: 0.10
  hard_fail_threshold: 0.30
  required_fields: []

================================================================================
File: environment_limited_green_policy.yaml
Path: quality\environment_limited_green_policy.yaml
================================================================================
version: 1
policy_scope: environment_limited_green_interpretation
taxonomy_path: configs/quality/test_health_reporting.yaml
classifier_source: scripts/engineering/ci/quality_integral_gate.py
current_baseline:
  enforced_provider_count: 7
  accepted_steady_state_reasons:
    - live_network_opt_in_gate
    - live_api_gate_mode_non_always
  transitional_reasons:
    - architecture_suite_skips
  disallowed_reopened_gap_reasons:
    - pilot_provider_count
    - vcr_only_provider_count
  architecture_skip_budget_reference:
    scorecard_path: configs/quality/debt_scorecard.yaml
    coarse_budget_key: architecture_skip_count
  interpretation_note: >-
    An enforced seven-provider live baseline does not imply fully exercised
    green. The current baseline may still classify as environment-limited when
    live execution is intentionally network-gated or scheduled, while pilot or
    VCR-only provider counts would represent a reopened baseline gap rather than
    acceptable steady-state posture.
reason_policy:
  - skip_class: architecture_suite_skips
    posture: transitional_debt
    allowed_in_current_baseline: true
    rationale: >-
      Historical architecture skips still have an explicit coarse budget, but
      they remain debt to retire rather than the target steady state.
    next_hardening_target: retire skip inventory and ratchet budget downward
  - skip_class: live_network_opt_in_gate
    posture: accepted_steady_state_policy
    allowed_in_current_baseline: true
    rationale: >-
      Live or networked execution remains intentionally opt-in for ordinary runs
      and should not be misread as a broken enforced-provider baseline.
    next_hardening_target: keep explicit at reporting layers; do not silently
      convert into a second merge gate
  - skip_class: live_api_gate_mode_non_always
    posture: accepted_steady_state_policy
    allowed_in_current_baseline: true
    rationale: >-
      Scheduled live execution remains an intentional policy boundary for the
      current baseline and therefore still maps to environment-limited green.
    next_hardening_target: revisit only if policy shifts from scheduled to always-on
  - skip_class: pilot_provider_count
    posture: reopened_baseline_gap
    allowed_in_current_baseline: false
    rationale: >-
      Pilot providers would mean the enforced live baseline is no longer closed
      for the current provider set.
    next_hardening_target: keep pilot count at zero in the active baseline
  - skip_class: vcr_only_provider_count
    posture: reopened_baseline_gap
    allowed_in_current_baseline: false
    rationale: >-
      VCR-only providers would reintroduce baseline exclusion rather than a
      stable environment-limited edge.
    next_hardening_target: keep VCR-only count at zero in the active baseline

================================================================================
File: fixture_governance_ledger.yaml
Path: quality\fixture_governance_ledger.yaml
================================================================================
version: 1
policy_scope: fixture_governance_rollout
source_of_truth:
  matrix_path: configs/quality/test_matrix.yaml
  matrix_rollout_path: fixture_governance.rollout
backlog_reference: docs/reports/evidence/residual-test-ci-debt/06-backlog/BACKLOG-residual-test-ci-debt-implementation-2026-04-01.md
entries:
  - field: cassette_metadata
    status: partial
    owner: "@bioetl-platform"
    blocking_classification: missing_metadata_backfill
    current_evidence_paths:
      - configs/quality/test_matrix.yaml
      - tests/architecture/test_test_matrix_coverage.py
      - tests/architecture/test_vcr_metadata_seed_registry.py
      - reports/quality/vcr-metadata-catalog.json
    artifact_paths:
      - tests/fixtures/vcr
      - reports/quality/vcr-metadata-catalog.json
      - scripts/ops/migrations/active/backfill_vcr_metadata_sidecars.py
    next_step: >-
      Expand *_meta.yaml coverage from the matrix-declared seeded sidecar slice
      into the managed VCR inventory and ratchet cassette_metadata_required only
      after repo-wide metadata coverage is stable.
    promotion_criteria: >-
      Canonical cassette metadata sidecars exist for the managed VCR inventory
      and architecture coverage can require metadata without introducing an
      allowlist-only exception path.
  - field: cassette_staleness_age
    status: partial
    owner: "@bioetl-platform"
    blocking_classification: missing_metadata_backfill
    current_evidence_paths:
      - configs/quality/test_matrix.yaml
      - tests/architecture/test_test_matrix_coverage.py
      - tests/fixtures/vcr/chembl/test_all_chembl_pipelines_chain_meta.yaml
    artifact_paths:
      - tests/fixtures/vcr
      - scripts/ops/migrations/active/backfill_vcr_metadata_sidecars.py
      - .github/workflows/tests.yml
    next_step: >-
      Move stale-age checking from seeded metadata proof to canonical managed
      inventory coverage so the max-age policy can be enforced consistently.
    promotion_criteria: >-
      Staleness checks run against canonical cassette metadata for the managed
      inventory and the rollout can switch from partial evidence to enforced
      policy.
  - field: cassette_metadata_catalog
    status: partial
    owner: "@bioetl-platform"
    blocking_classification: missing_policy_test_ratchet
    current_evidence_paths:
      - reports/quality/vcr-metadata-catalog.json
      - scripts/engineering/qa/report_vcr_metadata_catalog.py
      - tests/architecture/test_vcr_metadata_catalog_drift.py
      - tests/architecture/test_test_matrix_coverage.py
    artifact_paths:
      - reports/quality/vcr-metadata-catalog.json
      - scripts/engineering/qa/report_vcr_metadata_catalog.py
      - tests/fixtures/vcr
    next_step: >-
      Treat the metadata catalog as the canonical inventory artifact in repeatable
      checks instead of only as a present-on-disk proof point.
    promotion_criteria: >-
      The metadata catalog is regenerated and validated in a repeatable check
      path, and rollout status can be justified by an enforced inventory ratchet.
  - field: cassette_metadata_backfill
    status: partial
    owner: "@bioetl-platform"
    blocking_classification: missing_metadata_backfill
    current_evidence_paths:
      - scripts/ops/migrations/active/backfill_vcr_metadata_sidecars.py
      - tests/architecture/test_vcr_metadata_seed_registry.py
      - tests/fixtures/vcr/chembl/test_all_chembl_pipelines_chain_meta.yaml
      - tests/architecture/test_test_matrix_coverage.py
    artifact_paths:
      - scripts/ops/migrations/active/backfill_vcr_metadata_sidecars.py
      - tests/fixtures/vcr
      - .github/workflows/tests.yml
    next_step: >-
      Promote the sidecar backfill path from a seeded script plus
      matrix-declared partial inventory into an explicit managed migration
      workflow for the remaining cassette set.
    promotion_criteria: >-
      The repo has a canonical backfill path for the managed cassette inventory
      and rollout status no longer depends on a seeded subset of metadata files.
  - field: contract_snapshots
    status: partial
    owner: "@bioetl-data-model"
    blocking_classification: representative_scope_gap
    current_evidence_paths:
      - configs/quality/test_matrix.yaml
      - tests/architecture/test_test_matrix_coverage.py
      - tests/contract/test_chembl_contract.py
      - tests/contract/test_provider_contract_snapshot_registry.py
      - tests/contract/test_crossref_contract.py
      - tests/contract/test_openalex_contract.py
      - tests/contract/test_pubchem_contract.py
      - tests/contract/test_pubmed_contract.py
      - tests/contract/test_semanticscholar_contract.py
      - tests/contract/test_uniprot_contract.py
      - tests/fixtures/contracts/README.md
      - tests/fixtures/contracts/chembl/v1.json
      - tests/fixtures/contracts/crossref/v1.json
      - tests/fixtures/contracts/openalex/v1.json
      - tests/fixtures/contracts/pubchem/v1.json
      - tests/fixtures/contracts/pubmed/v1.json
      - tests/fixtures/contracts/semanticscholar/v1.json
      - tests/fixtures/contracts/uniprot/v1.json
    artifact_paths:
      - tests/fixtures/contracts
      - tests/fixtures/contracts/README.md
      - tests/contract/_provider_contract_drift.py
      - tests/contract/test_chembl_contract.py
      - tests/contract/test_crossref_contract.py
      - tests/contract/test_openalex_contract.py
      - tests/contract/test_pubchem_contract.py
      - tests/contract/test_pubmed_contract.py
      - tests/contract/test_semanticscholar_contract.py
      - tests/contract/test_uniprot_contract.py
      - tests/contract/test_provider_contract_snapshot_registry.py
    next_step: >-
      Keep the bounded matrix-declared snapshot registry aligned with the
      current live-provider baseline and extend it only when a new provider or
      probe family graduates into the enforced live contract surface with the
      same documented update path and CI-visible drift diagnostics.
    promotion_criteria: >-
      The matrix-declared snapshot registry covers every provider in the current
      enforced live-contract baseline, every adopted provider keeps documented
      update guidance and drift tests, and rollout remains intentionally bounded
      without depending on silver schema snapshots as the only external drift
      signal.
  - field: golden_masters
    status: partial
    owner: "@bioetl-data-model"
    blocking_classification: representative_scope_gap
    current_evidence_paths:
      - tests/fixtures/golden
      - tests/architecture/test_config_golden_master.py
      - tests/architecture/test_test_matrix_coverage.py
    artifact_paths:
      - tests/fixtures/golden
      - tests/architecture/test_config_golden_master.py
      - configs/quality/test_matrix.yaml
    next_step: >-
      Expand the representative golden-master set so provider-level SHOULD/MAY
      coverage is explained by a stable selection policy instead of a sparse
      partial inventory.
    promotion_criteria: >-
      The representative golden-master set is intentionally mapped to provider
      policy and the partial rollout no longer hides unexplained scope gaps.
  - field: extensionless_filenames
    status: enforced
    owner: "@bioetl-platform"
    blocking_classification: legacy_filename_inventory
    current_evidence_paths:
      - .github/vcr-noext-allowlist.txt
      - tests/architecture/test_test_matrix_coverage.py
      - .github/workflows/tests.yml
    artifact_paths:
      - .github/vcr-noext-allowlist.txt
      - tests/fixtures/vcr
      - scripts/engineering/qa/vcr/check_vcr_filename_policy.py
    next_step: >-
      Keep the root VCR guard and filename policy checks active so extensionless
      cassettes cannot regress back into the repository.
    promotion_criteria: >-
      Extensionless cassette inventory stays at zero while CI filename policy
      checks continue to enforce the canonical .yaml naming convention.

================================================================================
File: integration_vcr_policy.yaml
Path: quality\integration_vcr_policy.yaml
================================================================================
version: 1
policy_scope: integration_and_vcr_execution_policy
issue_reference: 2598
source_of_truth:
  test_matrix_path: configs/quality/test_matrix.yaml
  fixture_governance_ledger_path: configs/quality/fixture_governance_ledger.yaml
  ci_coverage_surface_matrix_path: configs/quality/ci_coverage_surface_matrix.yaml
  testing_guide_path: docs/03-guides/testing.md
supported_scopes:
  integration:
    canonical_test_roots:
    - tests/integration/adapters/
    - tests/integration/chembl/
    - tests/integration/composite/
    - tests/integration/config/
    - tests/integration/infrastructure/
    - tests/integration/interfaces/
    - tests/integration/pipelines/
    - tests/integration/validation/
    - tests/integration/ci/
    purpose: Adapter-, pipeline-, config-, and storage-facing integration checks that
      use either VCR-backed HTTP replay or local temporary artifacts rather than live
      network execution by default.
    supported_pipeline_families:
      provider_adapter_replay:
      - chembl
      - pubchem
      - pubmed
      - semanticscholar
      - uniprot
      provider_adapter_mixed_mode:
      - crossref
      - openalex
      pipeline_replay_smoke:
      - chembl_activity
      - chembl_cell_line
      - chembl_compound_record
      - chembl_target_component
      - pubchem_compound
      - uniprot_protein
      governance_and_runtime_surfaces:
      - control_plane
      - data_quality
      - grafana
      - prometheus
  e2e:
    canonical_test_root: tests/e2e/
    required_marker: e2e
    purpose: End-to-end local-only pipeline execution with memory/file-system control
      plane components and provider I/O constrained by VCR replay unless an explicit
      recording refresh path is being used.
    ci_smoke_workflow_job: control-plane-e2e
    ci_smoke_target: tests/e2e/test_pubchem_compound_e2e.py::test_pubchem_compound_full_cycle
    representative_pipeline_families:
      provider_runs:
      - chembl_activity
      - chembl_assay
      - chembl_molecule
      - chembl_publication
      - chembl_publication_term
      - chembl_target
      - crossref_publication
      - openalex_publication
      - pubchem_compound
      - pubmed_publication
      - semanticscholar_publication
      - uniprot_protein
      scenario_runs:
      - advanced_scenarios
      - checkpoint
      - full_pipeline
      - full_pipeline_chain
      - run_types
tracked_suite_inventory:
  integration:
    adapter_provider_surfaces:
      chembl:
      - tests/integration/adapters/test_chembl.py
      crossref:
      - tests/integration/adapters/test_crossref.py
      - tests/integration/adapters/test_crossref_vcr_rebalance.py
      openalex:
      - tests/integration/adapters/openalex/test_adapter.py
      - tests/integration/adapters/openalex/test_pipeline.py
      - tests/integration/adapters/test_openalex_vcr_rebalance.py
      pubchem:
      - tests/integration/adapters/test_pubchem.py
      pubmed:
      - tests/integration/adapters/test_pubmed.py
      - tests/integration/adapters/test_pubmed_coverage.py
      - tests/integration/adapters/test_pubmed_edge_cases.py
      - tests/integration/adapters/test_pubmed_vcr_rebalance.py
      semanticscholar:
      - tests/integration/adapters/test_semanticscholar.py
      - tests/integration/adapters/test_semanticscholar_vcr_rebalance.py
      uniprot:
      - tests/integration/adapters/test_uniprot.py
      - tests/integration/adapters/test_uniprot_idmapping.py
      shared_http_behavior:
      - tests/integration/adapters/test_http_retry_semantics.py
    chembl_parameter_extraction_surfaces:
    - tests/integration/chembl/test_activity_extraction_params.py
    - tests/integration/chembl/test_assay_extraction_params.py
    - tests/integration/chembl/test_molecule_extraction_params.py
    - tests/integration/chembl/test_publication_extraction_params.py
    - tests/integration/chembl/test_target_extraction_params.py
    pipeline_replay_smoke:
      chembl_activity: tests/integration/pipelines/test_chembl_activity.py
      chembl_cell_line: tests/integration/pipelines/test_chembl_cell_line.py
      chembl_compound_record: tests/integration/pipelines/test_chembl_compound_record.py
      chembl_target_component: tests/integration/pipelines/test_chembl_target_component.py
      pubchem_compound: tests/integration/test_pubchem_pipeline.py
      uniprot_protein: tests/integration/test_uniprot_pipeline.py
    normalization_and_pipeline_support:
    - tests/integration/pipelines/test_crossref_date_normalization.py
    - tests/integration/pipelines/test_pubmed_date_normalization.py
    - tests/integration/test_cross_pipeline_normalization.py
    - tests/integration/test_cross_provider_doi_normalization.py
    - tests/integration/test_json_hash_stability.py
    governance_and_runtime_surfaces:
      control_plane:
      - tests/integration/ci/test_reproducibility_contract_suite.py
      - tests/integration/ci/test_track_d_fixture_control_plane_linkage.py
      - tests/integration/test_preflight_health_modes.py
      - tests/integration/test_runner_lifecycle.py
      data_quality:
      - tests/integration/test_dq_monitor_integration.py
      - tests/integration/test_dq_report_integration.py
      grafana:
      - tests/integration/test_grafana_config.py
      - tests/integration/test_grafana_datasource_provisioning.py
      prometheus:
      - tests/integration/test_prometheus_rules_config.py
    composite_config_and_merge:
    - tests/integration/composite/test_column_naming_integration.py
    - tests/integration/composite/test_composite_config_backward_compatibility.py
    - tests/integration/composite/test_molecule_pipeline.py
    config_and_storage_surfaces:
    - tests/integration/ci/test_config_stability.py
    - tests/integration/config/test_dq_config_loading.py
    - tests/integration/infrastructure/storage/test_export_reader_version_fallback.py
    - tests/integration/infrastructure/storage/test_gold_writer_versioning.py
    - tests/integration/infrastructure/storage/test_silver_writer.py
    - tests/integration/infrastructure/storage/test_storage_factory_audit.py
    interface_cli_surfaces:
    - tests/integration/interfaces/test_cli_checkpoint_list.py
    - tests/integration/interfaces/test_cli_config_dq.py
    - tests/integration/interfaces/test_cli_exit_code_matrix.py
    - tests/integration/interfaces/test_cli_maintenance_archive.py
    - tests/integration/interfaces/test_cli_maintenance_vacuum.py
    - tests/integration/interfaces/test_cli_quarantine_inspect.py
    - tests/integration/interfaces/test_cli_run_dry_run.py
    - tests/integration/interfaces/test_cli_run_incremental.py
    - tests/integration/interfaces/test_cli_run_manifest.py
    - tests/integration/interfaces/test_cli_shutdown_integration.py
    external_validation_surfaces:
    - tests/integration/validation/test_external_verification.py
  e2e:
    provider_runs:
      chembl_activity: tests/e2e/test_chembl_activity_e2e.py
      chembl_assay: tests/e2e/test_chembl_assay_e2e.py
      chembl_molecule: tests/e2e/test_chembl_molecule_e2e.py
      chembl_publication: tests/e2e/test_chembl_publication_e2e.py
      chembl_publication_term: tests/e2e/test_chembl_publication_term_e2e.py
      chembl_target: tests/e2e/test_chembl_target_e2e.py
      crossref_publication: tests/e2e/test_crossref_publication_e2e.py
      openalex_publication: tests/e2e/test_openalex_publication_e2e.py
      pubchem_compound: tests/e2e/test_pubchem_compound_e2e.py
      pubmed_publication: tests/e2e/test_pubmed_publication_e2e.py
      semanticscholar_publication: tests/e2e/test_semanticscholar_publication_e2e.py
      uniprot_protein: tests/e2e/test_uniprot_protein_e2e.py
    scenario_runs:
      advanced_scenarios: tests/e2e/test_advanced_scenarios_e2e.py
      checkpoint: tests/e2e/test_checkpoint_e2e.py
      full_pipeline: tests/e2e/test_full_pipeline.py
      full_pipeline_chain: tests/e2e/test_full_pipeline_chain_e2e.py
      run_types: tests/e2e/test_run_types_e2e.py
    operational_and_governance_surfaces:
    - tests/e2e/test_cli_safety.py
    - tests/e2e/test_contract_rollout_e2e.py
    - tests/e2e/test_contract_rollout_runtime_e2e.py
    - tests/e2e/test_e2e_stability_policy.py
    - tests/e2e/test_gold_layer_e2e.py
    - tests/e2e/test_pipeline_matrix_e2e.py
    resilience_and_failure_surfaces:
    - tests/e2e/test_network_failure_e2e.py
    - tests/e2e/test_pipeline_circuit_breaker_e2e.py
    - tests/e2e/test_pipeline_graceful_shutdown_e2e.py
    - tests/e2e/test_pipeline_with_dq_errors_e2e.py
    - tests/e2e/test_pipeline_with_schema_drift_e2e.py
    - tests/e2e/test_resilience_scenarios_e2e.py
execution_paths:
  local:
    windows:
      bootstrap: scripts/engineering/dev/setup_env_windows.ps1
      pytest_runner: scripts/engineering/dev/run_pytest.ps1
      supported_targets:
        integration: tests\integration\
        e2e: tests\e2e\
      replay_examples:
        integration: .\scripts\engineering\dev\run_pytest.ps1 tests\integration\ --vcr-record=none
          -m "integration and not e2e"
        e2e: .\scripts\engineering\dev\run_pytest.ps1 tests\e2e\ -m e2e --vcr-record=none
      refresh_examples:
        targeted_integration: .\scripts\engineering\dev\run_pytest.ps1 tests\integration\adapters\test_pubmed.py
          --vcr-record=new_episodes -v
        targeted_e2e: .\scripts\engineering\dev\run_pytest.ps1 tests\e2e\test_pubchem_compound_e2e.py
          -m e2e --vcr-record=new_episodes -v
    wsl:
      bootstrap: scripts/engineering/dev/setup_env_wsl.sh
      pytest_runner: scripts/engineering/dev/run_pytest.sh
      supported_targets:
        integration: tests/integration/
        e2e: tests/e2e/
      replay_examples:
        integration: bash scripts/engineering/dev/run_pytest.sh tests/integration/
          --vcr-record=none -m "integration and not e2e"
        e2e: bash scripts/engineering/dev/run_pytest.sh tests/e2e/ -m e2e --vcr-record=none
      refresh_examples:
        targeted_integration: bash scripts/engineering/dev/run_pytest.sh tests/integration/adapters/test_pubmed.py
          --vcr-record=new_episodes -v
        targeted_e2e: bash scripts/engineering/dev/run_pytest.sh tests/e2e/test_pubchem_compound_e2e.py
          -m e2e --vcr-record=new_episodes -v
    ci_uv:
      workflow_path: .github/workflows/tests.yml
      preferred_command_family:
      - uv run pytest
      - uv run python -m pytest
      standard_replay_examples:
        smoke_check: uv run pytest tests/smoke/ -v --tb=short
        control_plane_e2e: VCR_RECORD_MODE=none uv run pytest tests/e2e/test_pubchem_compound_e2e.py::test_pubchem_compound_full_cycle
          --vcr-record=none -q --tb=short
  live_contract:
    workflow_path: .github/workflows/contract-tests.yml
    gate_mode: scheduled
    repository_guard: SatoryKono/BioactivityDataAcquisition
    required_env:
      BIOETL_LIVE_API_TESTS: 'true'
      BIOETL_NETWORK_TESTS: 'true'
    required_pytest_flag: --network
    failure_issue_runbook_path: docs/03-guides/testing.md
    manual_command_example: uv run pytest tests/contract/ -v --tb=short --network
vcr_policy:
  canonical_root: tests/fixtures/vcr/{provider}/
  forbidden_locations:
  - tests/fixtures/vcr_cassettes/
  placement_checks:
  - scripts/engineering/qa/vcr/check_root_vcr_cassettes.py
  - scripts/engineering/qa/vcr/check_vcr_filename_policy.py
  - scripts/engineering/qa/vcr/check_vcr_secrets.py
  default_record_modes:
    ci: none
    local: once
  supported_refresh_record_modes:
  - new_episodes
  legacy_compatibility_record_modes:
  - all
  extensionless_allowlist: .github/vcr-noext-allowlist.txt
  stale_age_days: 90
  stale_age_requires_metadata: true
  fixture_governance_rollout_source: configs/quality/fixture_governance_ledger.yaml
  metadata_catalog_path: reports/quality/vcr-metadata-catalog.json
  metadata_catalog_script: scripts/engineering/qa/report_vcr_metadata_catalog.py
  metadata_backfill_script: scripts/ops/migrations/active/backfill_vcr_metadata_sidecars.py
  refresh_protocol:
    pre_refresh_checks:
    - python -m scripts.data check-vcr-placement
    - python -m scripts.data check-vcr-naming
    targeted_recording_only: true
    preferred_refresh_mode: new_episodes
    post_refresh_checks:
    - python -m scripts.data check-vcr-placement
    - python -m scripts.data check-vcr-naming
    - python -m scripts.data check-vcr-secrets
    - python -m scripts.engineering.qa report-vcr-metadata --check
governance_rules:
  refresh_triggers:
  - missing cassette for an already-supported integration or e2e path
  - intentional adapter request-shape or endpoint change
  - contract failure or schema-drift investigation that proves replay divergence
  review_required_after_refresh:
  - cassette diff changes request parameters, headers, or pagination shape
  - cassette diff changes sanitized fields or redaction coverage
  - cassette refresh introduces or removes extensionless filenames
  ci_behavior:
  - standard CI paths must run with VCR replay locked to none
  - scheduled live contract coverage is separate from standard integration and e2e
    replay
  stale_signals:
  - cassette sidecar age exceeds 90 days where metadata exists
  - canonical provider or pipeline path moved without policy artifact update
  - cassette refresh changes sanitized request or pagination shape without review
    note
incremental_extension_model:
  add_new_provider_or_pipeline_family:
  - add tests under canonical integration or e2e roots
  - store cassettes only under tests/fixtures/vcr/{provider}/
  - update configs/quality/test_matrix.yaml for policy ownership
  - update configs/quality/fixture_governance_ledger.yaml if rollout status changes
  - prefer tightening tracked policy artifacts over adding ad hoc doc-only exceptions

================================================================================
File: neo4j_memory_mapping.yaml
Path: quality\neo4j_memory_mapping.yaml
================================================================================
version: "1.0.0"

file_structure:
  repo_zones:
    src:
      - "src"
    configs:
      - "configs"
    tests:
      - "tests"
    docs:
      - "docs"
    scripts:
      - "scripts"
    grafana:
      - "grafana"
    ".github":
      - ".github"
  excluded_dir_names:
    - "__pycache__"
  excluded_prefixes:
    - "docs/99-archive"
    - "docs/exports"
    - "docs/reports/generated"
    - "docs/02-architecture/generated"
    - "docs/02-architecture/diagrams/bundles"
    - "docs/02-architecture/diagrams/manifests"
    - "docs/02-architecture/diagrams/tooling"
    - "docs/02-architecture/diagrams/architecture/png"
    - "docs/02-architecture/diagrams/architecture/svg"
    - "docs/02-architecture/diagrams/class-diagrams/png"
    - "docs/02-architecture/diagrams/class-diagrams/svg"
    - "docs/02-architecture/diagrams/foundation/png"
    - "docs/02-architecture/diagrams/foundation/svg"
    - "docs/02-architecture/diagrams/views/png"
    - "docs/02-architecture/diagrams/views/svg"
    - "docs/02-architecture/diagrams/descriptions/legacy"
    - "scripts/diagrams/svg2png.mjs"
    - "scripts/archive"
  promoted_hubs:
    - "docs/03-guides"
    - "docs/03-guides/dashboards"
    - "docs/04-reference"
    - "docs/04-reference/contracts"
    - "docs/04-reference/pipelines"
    - "docs/04-reference/providers"
    - "docs/05-operations"
    - "docs/05-operations/runbooks"
    - "docs/05-operations/verification"
    - "configs/contracts"
    - "configs/contracts/chembl"
    - "configs/contracts/crossref"
    - "configs/contracts/pubchem"
    - "configs/contracts/pubmed"
    - "configs/quality"
    - "tests/architecture"
    - "grafana/dashboards"

adapters:
  fine_grained_enabled: true

duplication_analysis:
  enabled: true
  min_cluster_size: 2
  min_ast_nodes: 12
  families:
    normalization_profiles:
      roots:
        - "src/bioetl/domain/normalization/profiles"
      package_family: "domain/normalization"
      excluded_paths:
        - "src/bioetl/domain/normalization/profiles/registry.py"
      promotion_targets:
        - label: "module_surface"
          name: "src/bioetl/domain/normalization/profiles/base.py"
    adapter_layer:
      roots:
        - "src/bioetl/infrastructure/adapters"
      package_family: "infrastructure/adapters"
      promotion_targets:
        - label: "class_surface"
          name: "bioetl.infrastructure.adapters.base.BaseHttpAdapter"
        - label: "module_surface"
          name: "src/bioetl/infrastructure/adapters/base.py"
    composite_layer:
      roots:
        - "src/bioetl/application/composite"
      package_family: "application/composite"
      promotion_targets:
        - label: "package_family"
          name: "application/composite"

retirement_analysis:
  enabled: true
  families:
    - "normalization_profiles"
    - "adapter_layer"
    - "composite_layer"
  current_cycle_age_days: 45
  stale_age_days: 180
  dead_score_threshold: 6
  wip_markers:
    - "todo"
    - "wip"
    - "follow-up"
    - "phase 2"
    - "spike"
    - "temporary"
  deprecation_markers:
    - "deprecated"
    - "legacy"
    - "obsolete"
    - "compat"
    - "remove after"
    - "migration shim"

complexity_analysis:
  enabled: true
  families:
    - "normalization_profiles"
    - "adapter_layer"
    - "composite_layer"
  complexity_score_threshold: 4
  removable_score_threshold: 7
  blocker_anchor_limit: 3
  indirection_markers:
    - "helper"
    - "helpers"
    - "mixin"
    - "policy"
    - "codec"
    - "compat"
    - "legacy"
    - "wrapper"
    - "shim"
  stateful_markers:
    - "checkpoint"
    - "resume"
    - "state"
    - "fsm"
    - "transition"
    - "runner"

pipeline_operational:
  runtime_paths:
    - "uv run python -m bioetl run --pipeline"
    - "\"${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python\" -m bioetl run --pipeline"
    - ".\\.venv-win\\Scripts\\python.exe -m bioetl run --pipeline"
  validation_gates:
    - "pytest"
    - "config validation"
  dashboards:
    common:
      - "bioetl-overview-v2"
      - "bioetl-runtime"
    by_kind:
      entity:
        - "bioetl-dq-v2"
        - "bioetl-silver-reject-explorer"
      composite:
        - "bioetl-control-plane-v1"

pipeline_tests:
  relation_type: "TESTED_BY"
  ownership_config: "configs/quality/test_matrix.yaml"
  provider_regression_suites: true

normalization:
  relation_type: "DEPENDS_ON"
  entity_relation_type: "DEPENDS_ON"
  defaults:
    entity:
      modules:
        - "src/bioetl/application/core/record_normalization_processor.py"
        - "src/bioetl/domain/normalization/text.py"
        - "src/bioetl/domain/normalization/identifiers.py"
        - "src/bioetl/domain/normalization/dates.py"
        - "src/bioetl/domain/normalization/json.py"
    composite:
      modules:
        - "src/bioetl/application/composite/join_key_normalization.py"
        - "src/bioetl/application/composite/join_key_resolution.py"
        - "src/bioetl/application/composite/key_extractor.py"
  pipelines:
    chembl_activity:
      modules:
        - "src/bioetl/application/core/record_normalization_processor.py"
        - "src/bioetl/domain/normalization/profiles/_chembl_activity_fields.py"
        - "src/bioetl/domain/normalization/chembl.py"
        - "src/bioetl/domain/normalization/control_plane.py"
        - "src/bioetl/domain/normalization/identifiers.py"
        - "src/bioetl/domain/normalization/dates.py"
        - "src/bioetl/domain/normalization/text.py"

contracts:
  registry_source_prefixes:
    - "bioetl.domain.contracts.gold"
    - "bioetl.domain.schemas"
  control_plane_modules:
    - "src/bioetl/application/services/run_manifest_service.py"
    - "src/bioetl/application/services/run_ledger_service.py"
    - "src/bioetl/application/services/effective_config_service.py"
    - "src/bioetl/application/services/config_dq_service.py"
    - "src/bioetl/composition/runtime_builders/control_plane.py"
    - "src/bioetl/composition/runtime_builders/run_manifest_builder.py"
    - "src/bioetl/composition/runtime_builders/effective_config_artifact_builder.py"
  control_plane_runtime_modules:
    - "src/bioetl/interfaces/cli/commands/run_manifest.py"
    - "src/bioetl/infrastructure/control_plane/file_run_manifest_store.py"
    - "src/bioetl/infrastructure/control_plane/file_run_ledger_store.py"
    - "src/bioetl/infrastructure/control_plane/file_effective_config_artifact_store.py"
    - "src/bioetl/infrastructure/control_plane/file_lineage_store.py"
  control_plane_docs:
    - "docs/04-reference/contracts/run-manifest-ledger.md"
    - "docs/05-operations/runbooks/run-manifest-inspection.md"
    - "docs/05-operations/runbooks/traceability-signal-ownership.md"
    - "docs/05-operations/runbooks/observability-checklist.md"
  control_plane_anchor_fields:
    - "contract_ref"
    - "dq_policy_ref"
    - "rule_bundle_version"
    - "effective_config_artifact_id"
    - "dq_contract_compatibility_hash"
  lineage_modules:
    - "src/bioetl/application/services/lineage_inspection_service.py"
    - "src/bioetl/application/services/run_manifest_diagnostics.py"
  lineage_runtime_modules:
    - "src/bioetl/composition/bootstrap/cli/lineage.py"
    - "src/bioetl/interfaces/cli/commands/lineage.py"
    - "src/bioetl/infrastructure/control_plane/file_lineage_store.py"
  lineage_docs:
    - "docs/05-operations/runbooks/traceability-signal-ownership.md"
    - "docs/05-operations/runbooks/run-manifest-inspection.md"
    - "docs/03-guides/running-pipelines.md"
  lineage_anchor_fields:
    - "dataset_ref"
    - "lineage_fragment_id"
    - "contract_ref"
    - "effective_config_artifact_id"
    - "dq_policy_ref"
    - "rule_bundle_version"

alerts:
  dashboard_fallbacks:
    common:
      - "bioetl-overview-v2"
    groups:
      bioetl_pipeline_runtime_observability:
        - "bioetl-runtime"
      bioetl_control_plane_traceability_observability:
        - "bioetl-control-plane-v1"
        - "bioetl-runtime"
      bioetl_dq_observability:
        - "bioetl-dq-v2"
        - "bioetl-silver-reject-explorer"
      bioetl_provider_health_observability:
        - "bioetl-provider-health-v2"
  groups:
    bioetl_pipeline_runtime_observability:
      pipelines: "all"
      pipeline_kind: "any"
      providers: "none"
      contracts: "mapped"
    bioetl_control_plane_traceability_observability:
      pipelines: "all"
      pipeline_kind: "any"
      providers: "none"
      contracts: "all"
    bioetl_dq_observability:
      pipelines: "all"
      pipeline_kind: "entity"
      providers: "none"
      contracts: "mapped"
    bioetl_provider_health_observability:
      pipelines: "none"
      pipeline_kind: "any"
      providers: "all"
      contracts: "none"
  rules:
    BioETLControlPlaneReadFailureRate:
      pipelines: "none"
      providers: "none"
      contracts: "all"
    BioETLCheckpointCompatibilityBlocked:
      pipelines: "all"
      pipeline_kind: "any"
      contracts: "all"
    BioETLLineageFragmentPersistenceFailed:
      pipelines: "all"
      pipeline_kind: "any"
      contracts: "all"
    BioETLLineageRefsMissing:
      pipelines: "all"
      pipeline_kind: "any"
      contracts: "all"
    BioETLDataFreshnessLagHigh:
      pipelines: "all"
      pipeline_kind: "entity"
      contracts: "mapped"
    BioETLDataFreshnessLagCritical:
      pipelines: "all"
      pipeline_kind: "entity"
      contracts: "mapped"
      dashboards:
        - "bioetl-dq-v2"
        - "bioetl-overview-v2"

================================================================================
File: pretest_guardrails.yaml
Path: quality\pretest_guardrails.yaml
================================================================================
version: 1
profiles:
  light:
    run_cleanup: true
    run_auto_fix: true
    run_repo_checks: true
    run_docs_identity_checks: true
    run_docs_verify: false
    strict_docs: false
    architecture_group: ""
  governance:
    run_cleanup: true
    run_auto_fix: true
    run_repo_checks: true
    run_docs_identity_checks: true
    run_docs_verify: false
    strict_docs: false
    architecture_group: governance
  full:
    run_cleanup: true
    run_auto_fix: true
    run_repo_checks: true
    run_docs_identity_checks: true
    run_docs_verify: true
    strict_docs: false
    architecture_group: full
  strict:
    run_cleanup: true
    run_auto_fix: true
    run_repo_checks: true
    run_docs_identity_checks: true
    run_docs_verify: true
    strict_docs: true
    architecture_group: full
architecture_groups:
  governance:
    - tests/architecture/test_integration_vcr_policy.py::TestIntegrationVcrPolicy::test_every_test_surface_under_integration_and_e2e_is_in_tracked_inventory
    - tests/architecture/test_integration_vcr_policy.py::TestIntegrationVcrPolicy::test_testing_guide_matches_current_fixture_governance_and_live_contract_policy
    - tests/architecture/test_documentation_sync.py::test_no_legacy_repo_slug_in_active_docs_and_workflows
    - tests/architecture/test_documentation_sync.py::test_no_legacy_contract_path_in_active_docs
    - tests/architecture/test_scripts_catalog_governance.py::test_scripts_catalog_governance_check_passes
    - tests/architecture/test_scripts_inventory_manifest.py::test_scripts_inventory_manifest_drift_check_passes
  full:
    - tests/architecture/test_integration_vcr_policy.py::TestIntegrationVcrPolicy::test_every_test_surface_under_integration_and_e2e_is_in_tracked_inventory
    - tests/architecture/test_integration_vcr_policy.py::TestIntegrationVcrPolicy::test_testing_guide_matches_current_fixture_governance_and_live_contract_policy
    - tests/architecture/test_documentation_sync.py::test_no_legacy_repo_slug_in_active_docs_and_workflows
    - tests/architecture/test_documentation_sync.py::test_no_legacy_contract_path_in_active_docs
    - tests/architecture/test_scripts_catalog_governance.py::test_scripts_catalog_governance_check_passes
    - tests/architecture/test_scripts_inventory_manifest.py::test_scripts_inventory_manifest_drift_check_passes
    - tests/architecture/test_any_budget.py::test_any_budget_threshold
    - tests/architecture/test_type_checking_density.py
    - tests/architecture/test_hotspot_growth_family_ratchets.py
    - tests/architecture/test_hotspot_fan_in_family_ratchets.py

================================================================================
File: retirement_candidate_triage.yaml
Path: quality\retirement_candidate_triage.yaml
================================================================================
schema_version: 1
snapshot_date: "2026-04-13"
source:
  query: "python -m scripts.memory query dead-code-candidates all --json"
  focus: "zero-anchor retirement tranche after the 2026-04-13 cleanup wave and post-refactor false-positive triage"
  owner: "@bioetl-architecture"
policy:
  dispositions:
    - "removed"
    - "retain_active"
  review_cycle_days: 90
families:
  - name: "adapter_layer"
    owner: "@bioetl-platform"
    linked_issue: "2941"
    entries:
      - id: "cached_bronze_support_active"
        disposition: "retain_active"
        rationale: "Cached Bronze helper still backs the cached bronze datasource facade and remains an intentional extracted IO seam."
        reviewed_on: "2026-04-13"
        review_by: "2026-07-12"
        linked_issue: "2941"
        target:
          label: "module_surface"
          name: "src/bioetl/infrastructure/adapters/_cached_bronze_support.py"
          module_path: "src/bioetl/infrastructure/adapters/_cached_bronze_support.py"
          module_name: "bioetl.infrastructure.adapters._cached_bronze_support"
        verification:
          min_src_importers: 1
      - id: "circuit_breaker_contract_active"
        disposition: "retain_active"
        rationale: "The typed circuit-breaker contract is still re-exported through the public adapter seam and should not be treated as dead code."
        reviewed_on: "2026-04-13"
        review_by: "2026-07-12"
        linked_issue: "2941"
        target:
          label: "module_surface"
          name: "src/bioetl/infrastructure/adapters/_circuit_breaker_contract.py"
          module_path: "src/bioetl/infrastructure/adapters/_circuit_breaker_contract.py"
          module_name: "bioetl.infrastructure.adapters._circuit_breaker_contract"
        verification:
          min_src_importers: 1
      - id: "error_handling_support_active"
        disposition: "retain_active"
        rationale: "Adapter error-handling support still holds the extracted context/telemetry helpers behind the public ErrorService facade."
        reviewed_on: "2026-04-13"
        review_by: "2026-07-12"
        linked_issue: "2941"
        target:
          label: "module_surface"
          name: "src/bioetl/infrastructure/adapters/_error_handling_support.py"
          module_path: "src/bioetl/infrastructure/adapters/_error_handling_support.py"
          module_name: "bioetl.infrastructure.adapters._error_handling_support"
        verification:
          min_src_importers: 1
      - id: "health_check_observability_active"
        disposition: "retain_active"
        rationale: "Health-check observability helpers remain the canonical extracted seam behind HealthCheckMixin."
        reviewed_on: "2026-04-13"
        review_by: "2026-07-12"
        linked_issue: "2941"
        target:
          label: "module_surface"
          name: "src/bioetl/infrastructure/adapters/_health_check_observability.py"
          module_path: "src/bioetl/infrastructure/adapters/_health_check_observability.py"
          module_name: "bioetl.infrastructure.adapters._health_check_observability"
        verification:
          min_src_importers: 1
      - id: "health_check_policy_active"
        disposition: "retain_active"
        rationale: "Health-check policy helpers still back the shared mixin and are a live extracted seam rather than removable dead code."
        reviewed_on: "2026-04-13"
        review_by: "2026-07-12"
        linked_issue: "2941"
        target:
          label: "module_surface"
          name: "src/bioetl/infrastructure/adapters/_health_check_policy.py"
          module_path: "src/bioetl/infrastructure/adapters/_health_check_policy.py"
          module_name: "bioetl.infrastructure.adapters._health_check_policy"
        verification:
          min_src_importers: 1
  - name: "composite_layer"
    owner: "@bioetl-architecture"
    linked_issue: "2940"
    entries:
      - id: "preflight_rules_removed"
        disposition: "removed"
        rationale: "Legacy compat mixin was folded into CompositePreflightValidationService."
        reviewed_on: "2026-04-13"
        linked_issue: "2903"
        target:
          label: "module_surface"
          name: "src/bioetl/application/composite/_preflight_rules.py"
          module_path: "src/bioetl/application/composite/_preflight_rules.py"
      - id: "checkpoint_service_support_removed"
        disposition: "removed"
        rationale: "Checkpoint support facade was replaced by direct imports from extracted canonical helper modules."
        reviewed_on: "2026-04-13"
        linked_issue: "2907"
        target:
          label: "module_surface"
          name: "src/bioetl/application/composite/checkpoint/_service_support.py"
          module_path: "src/bioetl/application/composite/checkpoint/_service_support.py"
      - id: "checkpoint_state_codec_removed"
        disposition: "removed"
        rationale: "Checkpoint state serialization was folded into CompositeCheckpointState after the codec stopped having independent first-party callers."
        reviewed_on: "2026-04-13"
        linked_issue: "2938"
        target:
          label: "module_surface"
          name: "src/bioetl/application/composite/checkpoint/_state_codec.py"
          module_path: "src/bioetl/application/composite/checkpoint/_state_codec.py"
          module_name: "bioetl.application.composite.checkpoint._state_codec"
      - id: "fsm_helper_active"
        disposition: "retain_active"
        rationale: "FSM helper is still part of runtime wiring and resume handling; missing memory anchors reflect stale analysis rather than dead code."
        reviewed_on: "2026-04-13"
        review_by: "2026-07-12"
        linked_issue: "2908"
        target:
          label: "module_surface"
          name: "src/bioetl/application/composite/fsm_helper.py"
          module_path: "src/bioetl/application/composite/fsm_helper.py"
          module_name: "bioetl.application.composite.fsm_helper"
        verification:
          min_src_importers: 5
      - id: "runner_merge_stage_flow_removed"
        disposition: "removed"
        rationale: "The separate merge-stage flow hotspot was folded back into CompositeRunnerMergeStageMixin after the helper seam stopped carrying independent first-party value."
        reviewed_on: "2026-04-13"
        linked_issue: "2939"
        target:
          label: "module_surface"
          name: "src/bioetl/application/composite/runner_pkg/runner_merge_stage_flow.py"
          module_path: "src/bioetl/application/composite/runner_pkg/runner_merge_stage_flow.py"
      - id: "column_priority_orderer_active"
        disposition: "retain_active"
        rationale: "Column priority ordering is used by runtime wiring, coalesce policy, and merge support. The zero-anchor signal is a memory false positive."
        reviewed_on: "2026-04-13"
        review_by: "2026-07-12"
        linked_issue: "2909"
        target:
          label: "module_surface"
          name: "src/bioetl/application/composite/column_priority_orderer.py"
          module_path: "src/bioetl/application/composite/column_priority_orderer.py"
          module_name: "bioetl.application.composite.column_priority_orderer"
        verification:
          min_src_importers: 3
      - id: "merger_input_mixin_active"
        disposition: "retain_active"
        rationale: "Merge input loading still powers merger IO/orchestration paths and has active first-party imports."
        reviewed_on: "2026-04-13"
        review_by: "2026-07-12"
        linked_issue: "2909"
        target:
          label: "module_surface"
          name: "src/bioetl/application/composite/merger_input_mixin.py"
          module_path: "src/bioetl/application/composite/merger_input_mixin.py"
          module_name: "bioetl.application.composite.merger_input_mixin"
        verification:
          min_src_importers: 2
      - id: "runner_support_flow_active"
        disposition: "retain_active"
        rationale: "Runner support flow still centralizes correlation context and preflight orchestration behind the support mixin."
        reviewed_on: "2026-04-13"
        review_by: "2026-07-12"
        linked_issue: "2940"
        target:
          label: "module_surface"
          name: "src/bioetl/application/composite/runner_pkg/runner_support_flow.py"
          module_path: "src/bioetl/application/composite/runner_pkg/runner_support_flow.py"
          module_name: "bioetl.application.composite.runner_pkg.runner_support_flow"
        verification:
          min_src_importers: 1
      - id: "runner_support_mixin_active"
        disposition: "retain_active"
        rationale: "Runner support mixin remains a live façade layer for canonical support/runtime policies and should stay triaged as active."
        reviewed_on: "2026-04-13"
        review_by: "2026-07-12"
        linked_issue: "2940"
        target:
          label: "module_surface"
          name: "src/bioetl/application/composite/runner_pkg/runner_support_mixin.py"
          module_path: "src/bioetl/application/composite/runner_pkg/runner_support_mixin.py"
          module_name: "bioetl.application.composite.runner_pkg.runner_support_mixin"
        verification:
          min_src_importers: 1
      - id: "runner_support_policy_active"
        disposition: "retain_active"
        rationale: "Runner support policy still supplies the canonical build/selection helpers behind the support façade."
        reviewed_on: "2026-04-13"
        review_by: "2026-07-12"
        linked_issue: "2940"
        target:
          label: "module_surface"
          name: "src/bioetl/application/composite/runner_pkg/runner_support_policy.py"
          module_path: "src/bioetl/application/composite/runner_pkg/runner_support_policy.py"
          module_name: "bioetl.application.composite.runner_pkg.runner_support_policy"
        verification:
          min_src_importers: 1
      - id: "runner_support_runtime_active"
        disposition: "retain_active"
        rationale: "Runner support runtime still contains canonical checkpoint/save/seed runtime logic for composite execution."
        reviewed_on: "2026-04-13"
        review_by: "2026-07-12"
        linked_issue: "2940"
        target:
          label: "module_surface"
          name: "src/bioetl/application/composite/runner_pkg/runner_support_runtime.py"
          module_path: "src/bioetl/application/composite/runner_pkg/runner_support_runtime.py"
          module_name: "bioetl.application.composite.runner_pkg.runner_support_runtime"
        verification:
          min_src_importers: 1
      - id: "runner_support_types_active"
        disposition: "retain_active"
        rationale: "Runner support types remain the shared protocol surface binding support/runtime helpers together."
        reviewed_on: "2026-04-13"
        review_by: "2026-07-12"
        linked_issue: "2940"
        target:
          label: "module_surface"
          name: "src/bioetl/application/composite/runner_pkg/runner_support_types.py"
          module_path: "src/bioetl/application/composite/runner_pkg/runner_support_types.py"
          module_name: "bioetl.application.composite.runner_pkg.runner_support_types"
        verification:
          min_src_importers: 1
      - id: "runtime_models_active"
        disposition: "retain_active"
        rationale: "Runtime models remain a high-fan-in canonical contract surface across composition, CLI, and composite execution."
        reviewed_on: "2026-04-13"
        review_by: "2026-07-12"
        linked_issue: "2940"
        target:
          label: "module_surface"
          name: "src/bioetl/application/composite/runtime_models.py"
          module_path: "src/bioetl/application/composite/runtime_models.py"
          module_name: "bioetl.application.composite.runtime_models"
        verification:
          min_src_importers: 3
      - id: "runtime_wiring_api_active"
        disposition: "retain_active"
        rationale: "Runtime wiring API is still the sanctioned bootstrap/runtime seam and should be retained as an active extracted surface."
        reviewed_on: "2026-04-13"
        review_by: "2026-07-12"
        linked_issue: "2940"
        target:
          label: "module_surface"
          name: "src/bioetl/application/composite/runtime_wiring_api.py"
          module_path: "src/bioetl/application/composite/runtime_wiring_api.py"
          module_name: "bioetl.application.composite.runtime_wiring_api"
        verification:
          min_src_importers: 2

================================================================================
File: source_test_facade_inventory.yaml
Path: quality\source_test_facade_inventory.yaml
================================================================================
version: "1.0.0"
policy_scope: "facade_modules"
description: >
  Canonical ownership inventory for stable facade modules that intentionally do
  not use mirror-path unit tests. Rows here are reserved for package facades,
  retained canonical entrypoints, and compatibility facades whose public seam is
  verified through contract or architecture suites.

modules:
  - source: src/bioetl/application/composite/checkpoint/__init__.py
    ownership: facade_contract
    rationale: >
      Composite checkpoint package is a stable facade consumed through package-root
      imports across runner and bootstrap tests rather than a mirror-path module test.
    owner_tests:
      - tests/unit/application/composite/test_checkpoint.py
      - tests/unit/composition/bootstrap/runtime/test_composite_support_services_factory.py

  - source: src/bioetl/application/composite/runner_pkg/__init__.py
    ownership: facade_contract
    rationale: >
      Runner subpackage is a stable public facade for runtime config and runner
      types; ownership stays on package-root contract tests and runtime boundary checks.
    owner_tests:
      - tests/unit/application/composite/test_runner.py
      - tests/unit/interfaces/cli/commands/test_run_composite.py
      - tests/architecture/test_composite_cli_runtime_config_boundaries.py

  - source: src/bioetl/infrastructure/adapters/pubmed/client.py
    ownership: facade_contract
    rationale: >
      Retained canonical PubMed client entrypoint is a stable facade over the
      legacy implementation and is governed by dedicated entrypoint tests.
    owner_tests:
      - tests/unit/infrastructure/adapters/test_provider_entrypoints.py
      - tests/architecture/test_retained_adapter_entrypoint_policy.py

  - source: src/bioetl/infrastructure/adapters/semanticscholar/client.py
    ownership: facade_contract
    rationale: >
      Retained Semantic Scholar client entrypoint is a canonical facade over the
      decomposed adapter surface and is governed by dedicated entrypoint tests.
    owner_tests:
      - tests/unit/infrastructure/adapters/test_provider_entrypoints.py
      - tests/architecture/test_retained_adapter_entrypoint_policy.py

  - source: src/bioetl/infrastructure/adapters/pubmed/__init__.py
    ownership: facade_contract
    rationale: >
      PubMed package root is the canonical adapter import seam and is covered by
      provider contract and request-metadata tests.
    owner_tests:
      - tests/unit/infrastructure/adapters/test_provider_fetch_contracts.py
      - tests/unit/infrastructure/adapters/pubmed/test_request_metadata.py

  - source: src/bioetl/infrastructure/adapters/semanticscholar/__init__.py
    ownership: facade_contract
    rationale: >
      Semantic Scholar package root stays adapter-first and is owned through
      provider contract and adapter behavior suites.
    owner_tests:
      - tests/unit/infrastructure/adapters/test_provider_fetch_contracts.py
      - tests/unit/infrastructure/adapters/semanticscholar/test_adapter.py

  - source: src/bioetl/infrastructure/adapters/openalex/__init__.py
    ownership: facade_contract
    rationale: >
      OpenAlex package root is intentionally adapter-first and owned through the
      package-root entrypoint contract plus adapter tests.
    owner_tests:
      - tests/unit/infrastructure/adapters/test_provider_entrypoints.py
      - tests/unit/infrastructure/adapters/openalex/test_adapter.py

  - source: src/bioetl/infrastructure/adapters/crossref/__init__.py
    ownership: facade_contract
    rationale: >
      CrossRef package root remains the canonical adapter seam and is covered by
      package-root entrypoint and request-metadata tests.
    owner_tests:
      - tests/unit/infrastructure/adapters/test_provider_entrypoints.py
      - tests/unit/infrastructure/adapters/crossref/test_request_metadata.py

  - source: src/bioetl/infrastructure/adapters/crossref/client.py
    ownership: facade_contract
    rationale: >
      CrossRef client module is a thin compatibility facade over decomposed flow
      helpers, so ownership stays on the compatibility contract suite.
    owner_tests:
      - tests/unit/infrastructure/adapters/crossref/test_compatibility.py

  - source: src/bioetl/infrastructure/adapters/uniprot/__init__.py
    ownership: facade_contract
    rationale: >
      UniProt package root is the sanctioned adapter-first seam and is covered by
      entrypoint, adapter, and metadata tests rather than a mirror-path facade test.
    owner_tests:
      - tests/unit/infrastructure/adapters/test_provider_entrypoints.py
      - tests/unit/infrastructure/adapters/uniprot/test_adapter.py

  - source: src/bioetl/infrastructure/adapters/chembl/__init__.py
    ownership: facade_contract
    rationale: >
      ChEMBL package root is a public adapter facade owned through adapter and
      metadata-focused package-root tests.
    owner_tests:
      - tests/unit/infrastructure/test_adapters.py
      - tests/unit/infrastructure/adapters/chembl/test_request_metadata.py

  - source: src/bioetl/infrastructure/adapters/pubchem/__init__.py
    ownership: facade_contract
    rationale: >
      PubChem package root stays canonical for first-party imports and is owned
      through adapter and provider-name tests rather than a mirror facade file.
    owner_tests:
      - tests/unit/infrastructure/test_adapters.py
      - tests/unit/infrastructure/adapters/test_provider_names.py

================================================================================
File: source_test_mapping_exceptions.yaml
Path: quality\source_test_mapping_exceptions.yaml
================================================================================
version: "1.0.0"
policy_scope: "thin_packages"
description: >
  Machine-readable exceptions for source-to-test same-path ownership policy.
  Thin packages under src/bioetl/ MUST have a same-path tests/unit/.../test_<module>.py
  sibling unless explicitly exempted here with canonical owner tests.

exemptions:
  - source: src/bioetl/__main__.py
    policy: aggregate_owner
    reason: >
      Package entrypoint is exercised through CLI-facing tests rather than a
      mirrored unit module. It stays exempt from same-path thin-package policy.
    owner_tests:
      - tests/unit/interfaces/cli/test_cli_helpers.py
      - tests/unit/interfaces/cli/test_cli_commands_basic.py
  - source: src/bioetl/infrastructure/compat/pandera_compat.py
    policy: aggregate_owner
    reason: >
      Pandera compat seam is exercised through the infrastructure owner test
      module rather than a mirrored thin-package sibling test file.
    owner_tests:
      - tests/unit/infrastructure/test_pandera_compat.py

================================================================================
File: source_test_owner_inventory.yaml
Path: quality\source_test_owner_inventory.yaml
================================================================================
version: "1.0.0"
policy_scope: "curated_behavior_heavy_modules"
description: >
  Canonical source-to-test ownership inventory for high-signal behavior-heavy
  modules. Entries may use direct same-path tests or sanctioned cluster-owner
  suites where one module is intentionally owned by a broader focused test file.

modules:
  - source: src/bioetl/application/core/subcellular_fraction_data_source.py
    ownership: direct_test
    rationale: "Standalone wrapper module with dedicated same-path owner suite."
    owner_tests:
      - tests/unit/application/core/test_subcellular_fraction_data_source.py

  - source: src/bioetl/application/core/batch_executor_loop_helpers.py
    ownership: cluster_owner
    rationale: >
      Loop helpers are owned through the focused batch executor suite that covers
      extraction loop state, progress payloads, flushing, and checkpoint payloads.
    owner_tests:
      - tests/unit/application/core/test_batch_executor.py

  - source: src/bioetl/application/composite/dependency_joiner.py
    ownership: cluster_owner
    rationale: >
      Join routing is verified through a focused service-level suite rather than
      a same-path mirror name.
    owner_tests:
      - tests/unit/application/composite/test_dependency_joiner_service.py

  - source: src/bioetl/application/composite/coordinator.py
    ownership: cluster_owner
    rationale: >
      Coordinator execution policy is owned by focused coordinator edge and
      logging suites rather than a strict same-path mirror file.
    owner_tests:
      - tests/unit/application/composite/test_coordinator_edges.py
      - tests/unit/application/composite/test_coordinator_logging.py

  - source: src/bioetl/application/composite/preflight_validator.py
    ownership: direct_test
    rationale: "Preflight validation seam already has a dedicated same-path owner suite."
    owner_tests:
      - tests/unit/application/composite/test_preflight_validator.py

  - source: src/bioetl/application/composite/protocols.py
    ownership: cluster_owner
    rationale: >
      Composite protocol contracts are intentionally owned by a structural suite
      with explicit contract assertions rather than a mirror-path test name.
    owner_tests:
      - tests/unit/application/composite/test_protocols_structural.py

  - source: src/bioetl/application/composite/runtime_models.py
    ownership: direct_test
    rationale: "Runtime facade ownership stays on the direct same-path suite."
    owner_tests:
      - tests/unit/application/composite/test_runtime_models.py

  - source: src/bioetl/application/composite/checkpoint/service.py
    ownership: cluster_owner
    rationale: >
      Checkpoint service behavior is intentionally owned by the package-aware
      checkpoint suite rather than a strict mirror-path file name.
    owner_tests:
      - tests/unit/application/composite/checkpoint/test_checkpoint_service.py

  - source: src/bioetl/application/composite/checkpoint/state.py
    ownership: cluster_owner
    rationale: >
      Checkpoint state coverage stays on the package-aware checkpoint suite
      instead of a strict mirror-path test name.
    owner_tests:
      - tests/unit/application/composite/checkpoint/test_checkpoint_state.py

  - source: src/bioetl/application/composite/runner_pkg/runner.py
    ownership: cluster_owner
    rationale: >
      Runner facade behavior is owned through focused FSM and lifecycle suites
      that exercise the public orchestration surface.
    owner_tests:
      - tests/unit/application/composite/test_runner.py
      - tests/unit/application/composite/test_runner_fsm.py

  - source: src/bioetl/application/composite/runner_pkg/runner_completion_helpers.py
    ownership: direct_test
    rationale: "Completion helper seam already has a dedicated same-path owner suite."
    owner_tests:
      - tests/unit/application/composite/runner_pkg/test_runner_completion_helpers.py

  - source: src/bioetl/application/composite/runner_pkg/runner_execution_orchestrator.py
    ownership: direct_test
    rationale: "Locked execution phase orchestration has a direct same-path owner suite."
    owner_tests:
      - tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py

  - source: src/bioetl/application/composite/runner_pkg/runner_helpers.py
    ownership: direct_test
    rationale: "Runner helper surface is owned by a dedicated same-path test file."
    owner_tests:
      - tests/unit/application/composite/runner_pkg/test_runner_helpers.py

  - source: src/bioetl/application/composite/runner_pkg/runner_key_flow.py
    ownership: direct_test
    rationale: "Key extraction flow is covered by a direct same-path owner suite."
    owner_tests:
      - tests/unit/application/composite/runner_pkg/test_runner_key_flow.py

  - source: src/bioetl/application/composite/runner_pkg/runner_runtime_helpers.py
    ownership: direct_test
    rationale: "Runtime helper seam has a dedicated same-path owner suite."
    owner_tests:
      - tests/unit/application/composite/runner_pkg/test_runner_runtime_helpers.py

  - source: src/bioetl/infrastructure/adapters/cached_bronze_data_source.py
    ownership: direct_test
    rationale: "Cached bronze source wrapper already has a direct same-path owner test."
    owner_tests:
      - tests/unit/infrastructure/adapters/test_cached_bronze_data_source.py

  - source: src/bioetl/infrastructure/adapters/filterable_mixin.py
    ownership: direct_test
    rationale: "Filterable adapter mixin keeps a direct same-path owner suite."
    owner_tests:
      - tests/unit/infrastructure/adapters/test_filterable_mixin.py

  - source: src/bioetl/infrastructure/adapters/health_probe_policy.py
    ownership: direct_test
    rationale: "Health probe policy remains owned by a direct same-path test."
    owner_tests:
      - tests/unit/infrastructure/adapters/test_health_probe_policy.py

  - source: src/bioetl/infrastructure/adapters/common/fallback_fetch_service.py
    ownership: direct_test
    rationale: "Fallback fetch orchestration has a dedicated same-path owner suite."
    owner_tests:
      - tests/unit/infrastructure/adapters/common/test_fallback_fetch_service.py

  - source: src/bioetl/infrastructure/adapters/http/client.py
    ownership: cluster_owner
    rationale: >
      Unified HTTP facade behavior is owned by focused HTTP client suites rather
      than a mirror-path test file.
    owner_tests:
      - tests/unit/infrastructure/adapters/http/test_http_client.py
      - tests/unit/infrastructure/adapters/http/test_client_retries.py

  - source: src/bioetl/infrastructure/adapters/http/client_context_mixin.py
    ownership: direct_test
    rationale: "Context-management mixin already has a direct same-path owner suite."
    owner_tests:
      - tests/unit/infrastructure/adapters/http/test_client_context_mixin.py

  - source: src/bioetl/infrastructure/adapters/openalex/response_parser.py
    ownership: direct_test
    rationale: "OpenAlex response parsing helper has a dedicated same-path owner suite."
    owner_tests:
      - tests/unit/infrastructure/adapters/openalex/test_response_parser.py

  - source: src/bioetl/infrastructure/adapters/pubchem/fetch_flow.py
    ownership: direct_test
    rationale: "PubChem fetch flow behavior is owned by a direct same-path test."
    owner_tests:
      - tests/unit/infrastructure/adapters/pubchem/test_fetch_flow.py

  - source: src/bioetl/infrastructure/adapters/pubchem/query_builder.py
    ownership: direct_test
    rationale: "PubChem query-building logic already has a direct same-path owner suite."
    owner_tests:
      - tests/unit/infrastructure/adapters/pubchem/test_query_builder.py

  - source: src/bioetl/infrastructure/storage/silver/runtime_helpers.py
    ownership: cluster_owner
    rationale: >
      Runtime helper defaults are intentionally covered by the focused SilverWriter
      core suite rather than a separate mirror file.
    owner_tests:
      - tests/unit/infrastructure/storage/silver_writer/test_silver_writer_core.py

  - source: src/bioetl/infrastructure/storage/gold/io_delta_mixins.py
    ownership: cluster_owner
    rationale: >-
      Gold Delta I/O mixins are owned by the focused GoldWriter I/O suite rather
      than a strict same-path mirror file.
    owner_tests:
      - tests/unit/infrastructure/storage/test_gold_writer_io_delta_mixins.py

  - source: src/bioetl/infrastructure/storage/bronze/pipeline_helpers.py
    ownership: cluster_owner
    rationale: >-
      Bronze pipeline helper behavior is owned by the focused BronzeWriter
      pipeline-helper suite rather than a strict same-path mirror file.
    owner_tests:
      - tests/unit/infrastructure/storage/test_bronze_writer_pipeline_helpers.py

================================================================================
File: test_health_reporting.yaml
Path: quality\test_health_reporting.yaml
================================================================================
schema_version: "1.0"
classification_mode: informational
merge_blocking_source: ci_pass_fail_and_quality_gate
merge_blocking_note: >
  Descriptive test-health classes inform confidence posture and prioritization.
  Merge blocking remains governed by ordinary CI pass/fail and the quality gate.
statuses:
  fully_exercised_green:
    short_label: Fully Exercised Green
    definition: >
      Green result with no detected staged rollout or environment-gated limitation
      in the classified surface.
    merge_semantics: informational
  staged_green:
    short_label: Staged Green
    definition: >
      Green result where at least one confidence surface is still staged,
      partial, or not fully enforced.
    merge_semantics: informational
  environment_limited_green:
    short_label: Environment-Limited Green
    definition: >
      Green result whose confidence is reduced by skips, network opt-in gates,
      scheduled live checks, or VCR-only provider tiers.
    merge_semantics: informational
  non_green:
    short_label: Non-Green
    definition: >
      Failing or non-passing result where active regressions take precedence over
      descriptive confidence classification.
    merge_semantics: derived_from_blocking_ci
skip_classes:
  architecture_suite_skips:
    short_label: Architecture Suite Skips
    definition: >
      Skips reported directly by the architecture test run used by the quality
      gate.
  live_network_opt_in_gate:
    short_label: Network Opt-In Gate
    definition: >
      Live or networked test surfaces require explicit opt-in and therefore can
      remain unexercised in ordinary runs.
  live_api_gate_mode_non_always:
    short_label: Scheduled Live Gate
    definition: >
      Live-provider execution is policy-gated and not treated as always-on in
      the current baseline.
  pilot_provider_count:
    short_label: Pilot Providers
    definition: >
      Providers still staged as live pilots rather than fully enforced live
      coverage.
  vcr_only_provider_count:
    short_label: VCR-Only Providers
    definition: >
      Providers still outside the live baseline and covered through replay-first
      governance.

================================================================================
File: test_matrix.yaml
Path: quality\test_matrix.yaml
================================================================================
# Test Coverage Matrix — ADR-042
# Tracks required test types per provider and layer.
# CI uses this to validate minimum test coverage requirements.
#
# Levels: MUST (required), SHOULD (recommended), MAY (optional)
# Types: unit, integration, contract, property, e2e, smoke

version: "1.0.0"
adr_ref: ADR-042

# ── Layer-level requirements ─────────────────────────────────

layers:
  domain:
    unit: MUST
    property: SHOULD
    description: "Pure logic, value objects, ports. No I/O."

  application:
    unit: MUST
    integration: SHOULD
    property: SHOULD  # transformers, normalization only
    description: "Pipelines, services, orchestration."

  infrastructure:
    unit: MUST
    integration: MUST  # VCR-backed
    contract: MUST
    description: "HTTP adapters, storage, observability."

  composition:
    unit: SHOULD
    integration: SHOULD
    e2e: MUST
    description: "DI wiring, factories, bootstrap."

  interfaces:
    unit: SHOULD
    e2e: MUST
    description: "CLI commands, entry points."

# ── Provider-level requirements ──────────────────────────────

providers:
  chembl:
    entities:
      [
        activity,
        assay,
        assay_parameters,
        cell_line,
        compound_record,
        publication,
        publication_similarity,
        publication_term,
        molecule,
        protein_class,
        subcellular_fraction,
        target,
        target_component,
        tissue,
      ]
    vcr_cassettes: MUST
    contract_tests: MUST
    golden_masters: SHOULD

  pubchem:
    entities: [compound]
    vcr_cassettes: MUST
    contract_tests: MUST
    golden_masters: SHOULD

  uniprot:
    entities: [protein, idmapping]
    vcr_cassettes: MUST
    contract_tests: MUST
    golden_masters: SHOULD

  pubmed:
    entities: [publication]
    vcr_cassettes: MUST
    contract_tests: MUST
    golden_masters: SHOULD

  crossref:
    entities: [publication]
    vcr_cassettes: MUST
    contract_tests: MUST
    golden_masters: MAY

  openalex:
    entities: [publication]
    vcr_cassettes: MUST
    contract_tests: MUST
    golden_masters: MAY

  semanticscholar:
    entities: [publication]
    vcr_cassettes: MUST
    contract_tests: SHOULD
    golden_masters: MAY

# ── Entity-level test ownership ──────────────────────────────

entity_test_ownership:
  chembl.activity:
    - tests/integration/pipelines/test_chembl_activity.py
  chembl.assay:
    - tests/e2e/test_chembl_assay_e2e.py
  chembl.assay_parameters:
    - tests/unit/application/pipelines/test_chembl_assay_parameters.py
  chembl.cell_line:
    - tests/integration/pipelines/test_chembl_cell_line.py
  chembl.compound_record:
    - tests/integration/pipelines/test_chembl_compound_record.py
  chembl.molecule:
    - tests/e2e/test_chembl_molecule_e2e.py
  chembl.protein_class:
    - tests/unit/application/pipelines/test_chembl_pipelines.py
  chembl.publication:
    - tests/e2e/test_chembl_publication_e2e.py
  chembl.publication_similarity:
    - tests/unit/application/pipelines/test_chembl_pipelines.py
  chembl.publication_term:
    - tests/e2e/test_chembl_publication_term_e2e.py
  chembl.subcellular_fraction:
    - tests/unit/application/pipelines/chembl/test_subcellular_fraction_transformer.py
  chembl.target:
    - tests/e2e/test_chembl_target_e2e.py
  chembl.target_component:
    - tests/integration/pipelines/test_chembl_target_component.py
  chembl.tissue:
    - tests/unit/application/pipelines/chembl/test_tissue_transformer.py
  crossref.publication:
    - tests/e2e/test_crossref_publication_e2e.py
  openalex.publication:
    - tests/e2e/test_openalex_publication_e2e.py
  pubchem.compound:
    - tests/e2e/test_pubchem_compound_e2e.py
  pubmed.publication:
    - tests/e2e/test_pubmed_publication_e2e.py
  semanticscholar.publication:
    - tests/e2e/test_semanticscholar_publication_e2e.py
  uniprot.idmapping:
    - tests/integration/adapters/test_uniprot_idmapping.py
  uniprot.protein:
    - tests/e2e/test_uniprot_protein_e2e.py

# ── Canonical regression suites for shared provider capabilities ─────────────

provider_regression_suites:
  metadata_request_capability:
    description: "Canonical provider suites for request-metadata snapshot, clear, and count paths."
    providers:
      chembl: tests/unit/infrastructure/adapters/chembl/test_request_metadata.py
      crossref: tests/unit/infrastructure/adapters/crossref/test_request_metadata.py
      openalex: tests/unit/infrastructure/adapters/openalex/test_request_metadata.py
      pubchem: tests/unit/infrastructure/adapters/pubchem/test_request_metadata.py
      pubmed: tests/unit/infrastructure/adapters/pubmed/test_request_metadata.py
      semanticscholar: tests/unit/infrastructure/adapters/semanticscholar/test_request_metadata.py
      uniprot: tests/unit/infrastructure/adapters/uniprot/test_request_metadata.py

  slow_health_probe_policy:
    description: "Canonical provider suites for shared slow-health degradation policy."
    providers:
      crossref: tests/unit/infrastructure/adapters/crossref/test_crossref_client.py
      openalex: tests/unit/infrastructure/adapters/openalex/test_adapter.py
      pubmed: tests/unit/infrastructure/adapters/pubmed/test_pubmed_client.py
      semanticscholar: tests/unit/infrastructure/adapters/semanticscholar/test_adapter.py

# ── Test boundaries (ADR-042 §Property-Based Testing) ───────

property_test_boundaries:
  allowed:
    - domain/entities
    - domain/policies
    - domain/value_objects
    - application/pipelines/*/transformer*
    - application/core/normalization*
    - domain/services/schema*
  forbidden:
    - infrastructure/storage  # Use fixtures instead
    - interfaces/cli  # Use e2e instead
  # Note: infrastructure/adapters/common is exempt — retry/fallback
  # policies are pure logic tested with property-based approaches.

# ── Mutation testing (ADR-042 §Mutation Gate) ────────────────

mutation_testing:
  enabled: true
  workflow_present: true
  ci_gate_mode: partial  # Domain enforced in dedicated workflow; application target staged
  tool: mutmut
  targets:
    domain:
      min_score: 70
      enforced: true
    application:
      min_score: 60
      enforced: false
  excluded:
    - infrastructure  # I/O-heavy, low mutation value
    - composition  # Wiring code, tested via e2e
    - interfaces  # CLI tested via e2e

# ── Fixture governance ───────────────────────────────────────

fixture_governance:
  governance_ledger_location: configs/quality/fixture_governance_ledger.yaml
  vcr_cassette_max_age_days: 90
  golden_master_location: tests/fixtures/golden/{provider}/
  current_silver_schema_snapshot_location: tests/contract/silver_schemas/snapshots/
  contract_snapshot_location: tests/fixtures/contracts/{provider}/v{version}.json
  cassette_metadata_catalog_location: reports/quality/vcr-metadata-catalog.json
  cassette_metadata_catalog_script: scripts/engineering/qa/report_vcr_metadata_catalog.py
  cassette_metadata_required: false
  cassette_staleness_requires_metadata: true
  canonical_vcr_location: tests/fixtures/vcr/{provider}/
  extensionless_allowlist: .github/vcr-noext-allowlist.txt
  root_vcr_policy_enforced: true
  cassette_metadata_backfill_workflow_present: false
  cassette_metadata_backfill_script: scripts/ops/migrations/active/backfill_vcr_metadata_sidecars.py
  cassette_metadata_seed_registry:
    scope: bounded_provider_seed_slice
    provider_coverage_mode: at_least_one_per_vcr_provider
    provider_expected_sidecar_counts:
      chembl: 1
      crossref: 1
      openalex: 1
      pubchem: 1
      pubmed: 1
      semanticscholar: 1
      uniprot: 1
    tracked_sidecars:
      - tests/fixtures/vcr/chembl/test_all_chembl_pipelines_chain_meta.yaml
      - tests/fixtures/vcr/crossref/rf013_crossref_health_case_01_meta.yaml
      - tests/fixtures/vcr/openalex/rf013_openalex_health_case_01_meta.yaml
      - tests/fixtures/vcr/pubchem/test_pubchem_compound_full_cycle_meta.yaml
      - tests/fixtures/vcr/pubmed/rf013_pubmed_health_case_01_meta.yaml
      - tests/fixtures/vcr/semanticscholar/rf013_semanticscholar_health_case_01_meta.yaml
      - tests/fixtures/vcr/uniprot/test_uniprot_protein_full_cycle_meta.yaml
  rollout:
    cassette_metadata: partial
    cassette_staleness_age: partial
    cassette_metadata_catalog: partial
    cassette_metadata_backfill: partial
    contract_snapshots: partial
    golden_masters: partial
    extensionless_filenames: enforced
  contract_snapshot_registry:
    scope: bounded_live_provider_baseline
    documentation: tests/fixtures/contracts/README.md
    helper_module: tests/contract/_provider_contract_drift.py
    replay_registry_module: tests/contract/_provider_contract_replay.py
    registry_test_module: tests/contract/test_provider_contract_snapshot_registry.py
    replay_test_module: tests/contract/test_provider_contract_drift_replay.py
    replay_report_command: python -m scripts.engineering.qa report-provider-contract-drift
    update_env_var: UPDATE_SNAPSHOTS
    providers:
      chembl:
        version: 1
        test_module: tests/contract/test_chembl_contract.py
        required_probes:
          - activity_endpoint_schema
          - molecule_endpoint_schema
          - target_endpoint_schema
      crossref:
        version: 1
        test_module: tests/contract/test_crossref_contract.py
        required_probes:
          - work_lookup_by_doi
          - works_query_endpoint
          - agency_lookup_for_doi
      openalex:
        version: 1
        test_module: tests/contract/test_openalex_contract.py
        required_probes:
          - works_filter_by_doi
          - works_search_endpoint
          - health_probe_shape
      pubchem:
        version: 1
        test_module: tests/contract/test_pubchem_contract.py
        required_probes:
          - compound_by_molecule_id
          - compound_property_endpoint
          - smiles_search
      pubmed:
        version: 1
        test_module: tests/contract/test_pubmed_contract.py
        required_probes:
          - esearch_endpoint
          - esummary_endpoint
          - einfo_database_list
      semanticscholar:
        version: 1
        test_module: tests/contract/test_semanticscholar_contract.py
        required_probes:
          - paper_search_endpoint
          - paper_batch_lookup_by_doi
      uniprot:
        version: 1
        test_module: tests/contract/test_uniprot_contract.py
        required_probes:
          - uniprotkb_search_endpoint
          - specific_protein_lookup
          - taxonomy_endpoint

contract_testing:
  workflow_present: true
  replay_gate_workflow: .github/workflows/provider-contract-drift.yml
  live_api_gate_mode: scheduled
  replay_gate_mode: ci
  network_opt_in_required: true
  live_api_minimum_baseline:
    enforced_providers: [chembl, pubchem, uniprot, pubmed, crossref, openalex, semanticscholar]
    pilot_providers: []
    vcr_only_providers: []
  provider_live_api:
    chembl: enforced
    pubchem: enforced
    uniprot: enforced
    pubmed: enforced
    crossref: enforced
    openalex: enforced
    semanticscholar: enforced

================================================================================
File: test_structural_watchlist_map.yaml
Path: quality\test_structural_watchlist_map.yaml
================================================================================
version: 1
policy_scope: residual_test_ci_to_structural_watchlist_mapping
source_artifacts:
  - configs/quality/fixture_governance_ledger.yaml
  - configs/quality/ci_coverage_surface_matrix.yaml
  - configs/quality/environment_limited_green_policy.yaml
  - configs/quality/integration_vcr_policy.yaml
  - configs/quality/debt_scorecard.yaml
  - docs/reports/evidence/project-package-topology/04-decisions/DECISIONS.yaml
ranking_rule: >-
  Rank by shared blast radius first, then by governance maturity gap, then by how
  directly the weak confidence surface overlaps a family-level structural watchlist.
watchlist_families:
  - family: infrastructure_adapters
    status: candidate_family
    owner: "@bioetl-platform"
    evidence_anchor: docs/reports/evidence/project-package-topology/04-decisions/DECISIONS.yaml
    path_prefixes:
      - src/bioetl/infrastructure/adapters/
    representative_modules:
      - src/bioetl/infrastructure/adapters/health_check_mixin.py
      - src/bioetl/infrastructure/adapters/chembl/fetch_resilience_mixin.py
      - src/bioetl/infrastructure/adapters/error_handling.py
    rationale: >-
      Provider live execution, replay governance, and residual environment-limited
      behavior land most directly on adapter families rather than broad infrastructure
      as a whole.
  - family: infrastructure_storage
    status: candidate_family
    owner: "@bioetl-data-model"
    evidence_anchor: docs/reports/evidence/project-package-topology/04-decisions/DECISIONS.yaml
    path_prefixes:
      - src/bioetl/infrastructure/storage/
    representative_modules:
      - src/bioetl/infrastructure/storage/metadata_builder.py
      - src/bioetl/infrastructure/storage/silver/runtime_helpers.py
      - src/bioetl/infrastructure/storage/bronze/pipeline_helpers.py
    rationale: >-
      Contract snapshots, schema snapshots, and replay-confidence promotion all
      intersect storage-facing artifact governance and fixture-derived confidence.
  - family: composition_bootstrap_runtime
    status: active_family
    owner: "@bioetl-platform"
    evidence_anchor: configs/quality/debt_scorecard.yaml
    path_prefixes:
      - src/bioetl/composition/bootstrap/runtime/
    representative_modules:
      - src/bioetl/composition/bootstrap/runtime/observability.py
    rationale: >-
      Runtime/bootstrap governance is already an active family-level watchlist and
      remains the composition-side bridge for CI/test confidence reporting.
ranked_intersections:
  - rank: 1
    weak_surface: replay_fixture_governance
    primary_family: infrastructure_adapters
    secondary_families:
      - infrastructure_storage
    priority_band: P0
    blast_radius: high
    governance_maturity: partial
    linked_artifacts:
      - configs/quality/fixture_governance_ledger.yaml
      - configs/quality/test_matrix.yaml
      - docs/reports/evidence/residual-test-ci-debt/06-backlog/BACKLOG-residual-test-ci-debt-implementation-2026-04-01.md
    rationale: >-
      Replay governance is the strongest unfinished shared confidence surface and it
      touches provider adapter behavior first, with storage artifacts as the secondary
      contract for snapshots and fixture-derived outputs.
    next_wave_entrypoint: >-
      Start with adapter-facing metadata/backfill promotion, then tighten storage-side
      snapshot and golden-master promotion criteria.
  - rank: 2
    weak_surface: centralized_coverage_threshold_vs_ci_breadth
    primary_family: infrastructure_storage
    secondary_families:
      - infrastructure_adapters
      - composition_bootstrap_runtime
    priority_band: P1
    blast_radius: medium
    governance_maturity: partial
    linked_artifacts:
      - configs/quality/ci_coverage_surface_matrix.yaml
      - configs/quality/test_matrix.yaml
      - .github/workflows/tests.yml
    rationale: >-
      The main gap is not missing execution, but understanding which broad execution
      surfaces stay outside the hard threshold path. Storage and contract-shaped outputs
      are the clearest downstream confidence consumers, while adapters and runtime policy
      remain secondary overlap points.
    next_wave_entrypoint: >-
      Keep the mapping informational, then use it to choose whether any future hard gate
      should target storage-facing contract confidence rather than generic repo coverage.
  - rank: 3
    weak_surface: environment_limited_green_live_policy
    primary_family: infrastructure_adapters
    secondary_families:
      - composition_bootstrap_runtime
    priority_band: P1
    blast_radius: medium
    governance_maturity: policy_stabilized
    linked_artifacts:
      - configs/quality/environment_limited_green_policy.yaml
      - configs/quality/test_health_reporting.yaml
      - scripts/engineering/ci/quality_integral_gate.py
    rationale: >-
      The remaining environment-limited posture is mostly about live adapter execution
      policy, with runtime/bootstrap acting as the reporting and orchestration bridge.
    next_wave_entrypoint: >-
      Only reopen this as implementation work if accepted steady-state policy changes or
      if adapter-specific instability escapes the current informational classification.
selection_outcome:
  recommended_next_family: infrastructure_adapters
  recommended_next_surface: replay_fixture_governance
  why: >-
    It has the highest shared blast radius, remains only partially governed, and is the
    clearest overlap between unresolved confidence debt and a concrete structural family.
  defer_until_after_mapping:
    - broad infrastructure reorganization
    - new whole-layer hotspot programs
    - coverage-threshold expansion beyond coverage-verify

================================================================================
File: example_activity_refresh.yaml
Path: workflows\example_activity_refresh.yaml
================================================================================
schema_version: "1.0.0"
workflow:
  name: example_activity_refresh
  version: "1.0.0"
  defaults:
    run_options:
      run_type: backfill
      dry_run: false
      log_level: INFO
  steps:
    - kind: pipeline
      step_id: chembl_activity_ingest
      pipeline_name: chembl_activity
      run_options:
        limit: 500
    - kind: transform
      step_id: normalize_activity_snapshot
      transform_name: normalize_activity_snapshot
      depends_on:
        - chembl_activity_ingest

