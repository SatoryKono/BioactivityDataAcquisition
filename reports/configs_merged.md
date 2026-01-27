================================================================================
File: publication_enrichment.yaml
Path: composite\publication_enrichment.yaml
================================================================================
# =============================================================================
# Composite Pipeline: Publication Enrichment
# =============================================================================
# Column Naming Convention (ADR-026 v2)
# =============================================================================
# All business columns are renamed to: {provider}.{entity}.{field}
#
# Examples:
#   - seed (chembl_publication):      chembl.publication.title
#   - enricher (crossref_publication): crossref.publication.title
#   - enricher (pubmed_publication):   pubmed.publication.abstract
#
# EXCLUDED from renaming:
#   - Join keys: doi, pmid, pmc_id (для совместимости с join операциями)
#   - System columns: _run_id, _ingestion_ts, etc.
#
# COLUMN ORDERING:
#   Output columns are ordered by semantic groups:
#   1. System (entity_id, content_hash, _run_id, ...)
#   2. Identifiers (doi, pmid, document_chembl_id, ...)
#   3. Title (chembl.publication.title, crossref.publication.title, ...)
#   4. Abstract
#   5. Authors
#   6. Journal/Source
#   7. Dates
#   8. Metrics
#   9. Classification
#   10. URLs
#   11. Other
#
#   Within each group, columns are ordered by provider priority:
#   chembl → crossref → pubmed → openalex → semantic_scholar
#
# PRIORITY CONFIGURATION:
#   field_priorities uses source identifiers:
#   - 'seed' - refers to seed pipeline (resolved to chembl.publication.*)
#   - '{provider}' - matches {provider}.{seed_entity}.{field}
#   - '{provider}.{entity}' - explicit full match
# =============================================================================

name: composite_publication
version: "2.0"

seed:
  pipeline: chembl_publication
  silver_table: silver/chembl/publication

enrichers:
  - pipeline: crossref_publication
    join_keys: [doi]
    optional: false
    timeout_seconds: 300

  - pipeline: pubmed_publication
    join_keys: [pmid, pmc_id]
    optional: true
    timeout_seconds: 180

merge:
  strategy: left_outer
  conflict_resolution: explicit_rules

  # Priority: first source wins for each field
  # 'seed' resolves to chembl (since seed.pipeline = chembl_publication)
  field_priorities:
    title:
      - seed          # chembl.publication.title
      - crossref      # crossref.publication.title
      - pubmed        # pubmed.publication.title

    abstract:
      - crossref
      - pubmed
      - seed

    citation_count:
      - crossref      # Only crossref has this

    journal:
      - seed
      - crossref

  # Column ordering configuration (optional, uses defaults if not specified)
  column_order:
    provider_priority:
      - chembl
      - crossref
      - pubmed
      - openalex
      - semantic_scholar

  output:
    silver: silver/composite/publication
    gold: gold/composite/publication

================================================================================
File: _defaults.yaml
Path: dq\_defaults.yaml
================================================================================
 # configs/dq/_defaults.yaml
# Global DQ defaults for all BioETL pipelines
# RULES.md §3.1.2: DQ Thresholds
#
# Merge priority (lowest to highest):
# 1. This file (_defaults.yaml)
# 2. providers/{provider}.yaml
# 3. entities/{provider}/{entity}.yaml
# 4. Inline overrides in pipeline config

version: "1.0.0"

# =============================================================================
# Threshold Configuration (RULES.md §3.1.2)
# =============================================================================
thresholds:
  soft_fail: 0.05      # >5% errors → Warning
  hard_fail: 0.20      # >20% errors → Fail Batch

# =============================================================================
# Validation Mode
# =============================================================================
strict_validation: false  # Feature flag for stricter rules

# =============================================================================
# Invalid Record Handling
# =============================================================================
invalid_record_policy: quarantine  # quarantine | skip | fail

# =============================================================================
# Report Configuration
# =============================================================================
report:
  enabled: true
  format: json           # json | yaml | csv
  include_sample_failures: true
  sample_size: 10
  output_path: null      # null = use pipeline output dir

# =============================================================================
# Common Field Validations (applied to ALL entities)
# =============================================================================
common_field_validations:
  # Content hash must be present after transform
  - field: _content_hash
    type: required
    nullable: false
    error_message: "Content hash is required for deduplication"

  # Ingestion timestamp must be valid ISO format
  - field: _ingestion_ts
    type: pattern
    pattern: '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
    nullable: false
    error_message: "Ingestion timestamp must be ISO 8601 format"

# =============================================================================
# Common Cross-Field Validations
# =============================================================================
common_cross_field_validations: []

================================================================================
File: activity.yaml
Path: dq\entities\chembl\activity.yaml
================================================================================
# configs/dq/entities/chembl/activity.yaml
# ChEMBL Activity-specific DQ rules
# Inherits from: _defaults.yaml → providers/chembl.yaml

version: "1.0.0"
provider: chembl
entity: activity

# Thresholds: inherit from provider

# =============================================================================
# Activity-Specific Field Validations
# =============================================================================
entity_field_validations:
  # Activity ID is required
  - field: activity_id
    type: required
    nullable: false
    error_message: "Activity ID is required"

  # Standard value must be non-negative when present
  - field: standard_value
    type: range
    min: 0
    nullable: true
    error_message: "Standard value must be non-negative"

  # pChEMBL value must be in valid range (0-15)
  - field: pchembl_value
    type: range
    min: 0
    max: 15
    nullable: true
    error_message: "pChEMBL value must be between 0 and 15"

  # Standard type validation
  - field: standard_type
    type: enum
    allowed:
      - IC50
      - Ki
      - Kd
      - EC50
      - AC50
      - GI50
      - Potency
      - Activity
      - Inhibition
    nullable: true
    error_message: "Invalid standard_type value"

  # Standard units validation
  - field: standard_units
    type: enum
    allowed:
      - nM
      - uM
      - mM
      - pM
      - M
      - "%"
    nullable: true
    error_message: "Invalid standard_units value"

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations:
  # If standard_value present, standard_units should be present
  - name: value_requires_units
    fields:
      - standard_value
      - standard_units
    condition: conditional_required
    trigger_field: standard_value
    required_field: standard_units
    error_message: "standard_units required when standard_value is present"

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations:
  # When assay_type is 'B' (Binding), target should be present
  - name: binding_requires_target
    condition_field: assay_type
    condition_value: B
    condition_operator: eq
    then_validations:
      - field: target_chembl_id
        type: required
        nullable: false
        error_message: "Binding assays must have a target"

================================================================================
File: assay.yaml
Path: dq\entities\chembl\assay.yaml
================================================================================
# configs/dq/entities/chembl/assay.yaml
# ChEMBL Assay-specific DQ rules
# Inherits from: _defaults.yaml → providers/chembl.yaml

version: "1.0.0"
provider: chembl
entity: assay

# Thresholds: inherit from provider

# =============================================================================
# Assay-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: assay_chembl_id
    type: required
    nullable: false
    error_message: "Assay ChEMBL ID is required"

  - field: assay_type
    type: enum
    allowed:
      - B  # Binding
      - F  # Functional
      - A  # ADMET
      - T  # Toxicity
      - P  # Physicochemical
      - U  # Unclassified
    nullable: true
    error_message: "Invalid assay_type value"

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations: []

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations: []

================================================================================
File: assay_parameters.yaml
Path: dq\entities\chembl\assay_parameters.yaml
================================================================================
# configs/dq/entities/chembl/assay_parameters.yaml
# ChEMBL Assay Parameters-specific DQ rules
# Inherits from: _defaults.yaml → providers/chembl.yaml

version: "1.0.0"
provider: chembl
entity: assay_parameters

# Thresholds: inherit from provider

# =============================================================================
# Assay Parameters-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: assay_param_id
    type: range
    min: 1
    nullable: false
    error_message: "Assay parameter ID is required and must be positive"

  - field: assay_chembl_id
    type: pattern
    pattern: '^CHEMBL\d+$'
    nullable: false
    error_message: "assay_chembl_id must match CHEMBL format"

  - field: type
    type: pattern
    pattern: '^.{1,100}$'
    nullable: false
    error_message: "Parameter type is required"

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations:
  - name: param_linkage
    fields:
      - assay_param_id
      - assay_chembl_id
    condition: all_present
    error_message: "Both param ID and assay ID are required"

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations: []

================================================================================
File: cell_line.yaml
Path: dq\entities\chembl\cell_line.yaml
================================================================================
# configs/dq/entities/chembl/cell_line.yaml
# ChEMBL Cell Line-specific DQ rules
# Inherits from: _defaults.yaml → providers/chembl.yaml

version: "1.0.0"
provider: chembl
entity: cell_line

# Thresholds: inherit from provider

# =============================================================================
# Cell Line-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: cell_chembl_id
    type: pattern
    pattern: '^CHEMBL\d+$'
    nullable: false
    error_message: "cell_chembl_id must match CHEMBL format"

  - field: cell_name
    type: pattern
    pattern: '^.{1,200}$'
    nullable: false
    error_message: "cell_name is required and must not exceed 200 chars"

  - field: cellosaurus_id
    type: pattern
    pattern: '^CVCL_[A-Z0-9]+$'
    nullable: true
    error_message: "cellosaurus_id must match CVCL format"

  - field: cell_source_tax_id
    type: range
    min: 1
    max: 10000000
    nullable: true

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations: []

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations: []

================================================================================
File: compound_record.yaml
Path: dq\entities\chembl\compound_record.yaml
================================================================================
# configs/dq/entities/chembl/compound_record.yaml
# ChEMBL Compound Record-specific DQ rules
# Inherits from: _defaults.yaml → providers/chembl.yaml

version: "1.0.0"
provider: chembl
entity: compound_record

# Thresholds: inherit from provider

# =============================================================================
# Compound Record-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: record_id
    type: range
    min: 1
    nullable: false
    error_message: "Record ID is required and must be positive"

  - field: molecule_chembl_id
    type: pattern
    pattern: '^CHEMBL\d+$'
    nullable: false
    error_message: "molecule_chembl_id must match CHEMBL format"

  - field: document_chembl_id
    type: pattern
    pattern: '^CHEMBL\d+$'
    nullable: false
    error_message: "document_chembl_id must match CHEMBL format"

  - field: src_id
    type: range
    min: 1
    nullable: true

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations:
  - name: record_linkage
    fields:
      - molecule_chembl_id
      - document_chembl_id
    condition: all_present
    error_message: "Both molecule and document IDs are required"

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations: []

================================================================================
File: molecule.yaml
Path: dq\entities\chembl\molecule.yaml
================================================================================
# configs/dq/entities/chembl/molecule.yaml
# ChEMBL Molecule-specific DQ rules
# Inherits from: _defaults.yaml → providers/chembl.yaml

version: "1.0.0"
provider: chembl
entity: molecule

# Thresholds: inherit from provider

# =============================================================================
# Molecule-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: molecule_chembl_id
    type: required
    nullable: false
    error_message: "Molecule ChEMBL ID is required"

  # Molecular weight must be positive
  - field: full_mwt
    type: range
    min: 0
    nullable: true
    error_message: "Molecular weight must be non-negative"

  # ALogP typically between -10 and 10
  - field: alogp
    type: range
    min: -15
    max: 20
    nullable: true
    error_message: "ALogP value out of expected range"

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations: []

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations: []

================================================================================
File: protein_class.yaml
Path: dq\entities\chembl\protein_class.yaml
================================================================================
# configs/dq/entities/chembl/protein_class.yaml
# ChEMBL Protein Classification-specific DQ rules
# Inherits from: _defaults.yaml → providers/chembl.yaml

version: "1.0.0"
provider: chembl
entity: protein_class

# Thresholds: inherit from provider

# =============================================================================
# Protein Class-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: protein_class_id
    type: range
    min: 1
    nullable: false
    error_message: "Protein class ID is required and must be positive"

  - field: class_level
    type: range
    min: 1
    max: 10
    nullable: true
    error_message: "Class level must be between 1 and 10"

  - field: pref_name
    type: pattern
    pattern: '^.{1,500}$'
    nullable: false
    error_message: "pref_name is required"

  - field: parent_id
    type: range
    min: 1
    nullable: true
    error_message: "parent_id must be positive when present"

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations:
  - name: hierarchy_valid
    fields:
      - protein_class_id
      - parent_id
    condition: custom
    validator: validate_hierarchy_no_self_reference
    error_message: "parent_id cannot equal protein_class_id"

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations: []

================================================================================
File: publication.yaml
Path: dq\entities\chembl\publication.yaml
================================================================================
# configs/dq/entities/chembl/publication.yaml
# ChEMBL Publication (Document)-specific DQ rules
# Inherits from: _defaults.yaml → providers/chembl.yaml

version: "1.0.0"
provider: chembl
entity: publication

# Thresholds: inherit from provider

# =============================================================================
# Publication-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: document_chembl_id
    type: pattern
    pattern: '^CHEMBL\d+$'
    nullable: false
    error_message: "document_chembl_id must match CHEMBL format"

  - field: doc_type
    type: enum
    allowed:
      - PUBLICATION
      - BOOK
      - DATASET
      - PATENT
    nullable: true

  - field: year
    type: range
    min: 1800
    max: 2100
    nullable: true
    error_message: "Publication year must be between 1800 and 2100"

  - field: pubmed_id
    type: range
    min: 1
    max: 100000000
    nullable: true
    error_message: "PubMed ID must be a positive integer"

  - field: doi
    type: pattern
    pattern: '^10\.\d{4,}/.*$'
    nullable: true
    error_message: "DOI must start with 10. prefix"

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations:
  - name: publication_identifiable
    fields:
      - pubmed_id
      - doi
      - title
    condition: any_present
    error_message: "Publication must have at least one identifier"

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations: []

================================================================================
File: publication_similarity.yaml
Path: dq\entities\chembl\publication_similarity.yaml
================================================================================
# configs/dq/entities/chembl/publication_similarity.yaml
# ChEMBL Publication Similarity (Document Similarity)-specific DQ rules
# Inherits from: _defaults.yaml → providers/chembl.yaml

version: "1.0.0"
provider: chembl
entity: publication_similarity

# Thresholds: inherit from provider

# =============================================================================
# Publication Similarity-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: sim_id
    type: range
    min: 1
    nullable: false
    error_message: "Similarity ID is required and must be positive"

  - field: doc_1
    type: range
    min: 1
    nullable: false
    error_message: "First document ID is required"

  - field: doc_2
    type: range
    min: 1
    nullable: false
    error_message: "Second document ID is required"

  - field: max_tani
    type: range
    min: 0
    max: 1
    nullable: true
    error_message: "Tanimoto coefficient must be between 0 and 1"

  - field: avg_tani
    type: range
    min: 0
    max: 1
    nullable: true
    error_message: "Average Tanimoto must be between 0 and 1"

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations:
  - name: similarity_pair
    fields:
      - doc_1
      - doc_2
    condition: all_present
    error_message: "Both document IDs are required"

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations: []

================================================================================
File: publication_term.yaml
Path: dq\entities\chembl\publication_term.yaml
================================================================================
# configs/dq/entities/chembl/publication_term.yaml
# ChEMBL Publication Term (Document Term)-specific DQ rules
# Inherits from: _defaults.yaml → providers/chembl.yaml

version: "1.0.0"
provider: chembl
entity: publication_term

# Thresholds: inherit from provider

# =============================================================================
# Publication Term-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: entity_id
    type: pattern
    pattern: '^[a-f0-9]{64}$'
    nullable: false
    error_message: "entity_id must be a 64-char SHA256 hash"

  - field: document_chembl_id
    type: pattern
    pattern: '^CHEMBL\d+$'
    nullable: false
    error_message: "document_chembl_id must match CHEMBL format"

  - field: term_type
    type: enum
    allowed:
      - MESH_HEADING
      - KEYWORD
      - AUTHOR
      - INSTITUTION
    nullable: false
    error_message: "term_type is required and must be valid"

  - field: term
    type: pattern
    pattern: '^.{1,500}$'
    nullable: false
    error_message: "term is required and must not exceed 500 chars"

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations:
  - name: term_completeness
    fields:
      - document_chembl_id
      - term
      - term_type
    condition: all_present
    error_message: "All term fields are required"

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations: []

================================================================================
File: target.yaml
Path: dq\entities\chembl\target.yaml
================================================================================
# configs/dq/entities/chembl/target.yaml
# ChEMBL Target-specific DQ rules
# Inherits from: _defaults.yaml → providers/chembl.yaml

version: "1.0.0"
provider: chembl
entity: target

# Thresholds: inherit from provider

# =============================================================================
# Target-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: target_chembl_id
    type: required
    nullable: false
    error_message: "Target ChEMBL ID is required"

  - field: target_type
    type: enum
    allowed:
      - SINGLE PROTEIN
      - PROTEIN COMPLEX
      - PROTEIN FAMILY
      - ORGANISM
      - TISSUE
      - CELL-LINE
      - SELECTIVITY GROUP
      - UNKNOWN
    nullable: true
    error_message: "Invalid target_type value"

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations: []

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations: []

================================================================================
File: target_component.yaml
Path: dq\entities\chembl\target_component.yaml
================================================================================
# configs/dq/entities/chembl/target_component.yaml
# ChEMBL Target Component-specific DQ rules
# Inherits from: _defaults.yaml → providers/chembl.yaml

version: "1.0.0"
provider: chembl
entity: target_component

# Thresholds: inherit from provider

# =============================================================================
# Target Component-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: component_id
    type: range
    min: 1
    nullable: false
    error_message: "Component ID is required and must be positive"

  - field: component_type
    type: enum
    allowed:
      - PROTEIN
      - DNA
      - RNA
    nullable: true

  - field: accession
    type: pattern
    pattern: '^[A-Z0-9]{6,10}$'
    nullable: true
    error_message: "accession should be UniProt format (6-10 alphanumeric chars)"

  - field: tax_id
    type: range
    min: 1
    max: 10000000
    nullable: true
    error_message: "Taxonomy ID must be between 1 and 10,000,000"

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations:
  - name: component_identifiable
    fields:
      - component_id
      - accession
    condition: any_present
    error_message: "Component must have ID or accession"

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations: []

================================================================================
File: publication.yaml
Path: dq\entities\crossref\publication.yaml
================================================================================
# configs/dq/entities/crossref/publication.yaml
# CrossRef Publication (Work)-specific DQ rules
# Inherits from: _defaults.yaml → providers/crossref.yaml

version: "1.0.0"
provider: crossref
entity: publication

# Thresholds: inherit from provider (soft 0.10, hard 0.30)

# =============================================================================
# Publication-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: doi
    type: pattern
    pattern: '^10\.\d{4,}/.*$'
    nullable: false
    error_message: "DOI is required and must start with 10. prefix"

  - field: title
    type: pattern
    pattern: '^.{1,2000}$'
    nullable: true
    error_message: "Title must not exceed 2000 chars"

  - field: year
    type: range
    min: 1800
    max: 2100
    nullable: true
    error_message: "Publication year out of valid range"

  - field: type
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

  - field: is_referenced_by_count
    type: range
    min: 0
    nullable: true
    error_message: "Citation count must be non-negative"

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations:
  - name: publication_identifiable
    fields:
      - doi
      - title
    condition: all_present
    error_message: "Publication must have DOI and title"

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations: []

================================================================================
File: publication.yaml
Path: dq\entities\openalex\publication.yaml
================================================================================
# configs/dq/entities/openalex/publication.yaml
# OpenAlex Publication-specific DQ rules
# Inherits from: _defaults.yaml → providers/openalex.yaml

version: "1.0.0"
provider: openalex
entity: publication

# Thresholds: inherit from provider (soft 0.08, hard 0.25)

# =============================================================================
# Publication-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: openalex_id
    type: pattern
    pattern: '^W\d+$'
    nullable: false
    error_message: "OpenAlex ID is required and must start with W followed by digits"

  - field: doi
    type: pattern
    pattern: '^10\.\d{4,}/.*$'
    nullable: true
    error_message: "DOI must start with 10. prefix"

  - field: title
    type: pattern
    pattern: '^.{1,2000}$'
    nullable: true
    error_message: "Title must not exceed 2000 chars"

  - field: year
    type: range
    min: 1500
    max: 2100
    nullable: true
    error_message: "Publication year out of valid range"

  - field: type
    type: enum
    allowed:
      - article
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

  - field: cited_by_count
    type: range
    min: 0
    nullable: true
    error_message: "Citation count must be non-negative"

  - field: fwci
    type: range
    min: 0
    nullable: true
    error_message: "FWCI must be non-negative"

  - field: referenced_works_count
    type: range
    min: 0
    nullable: true
    error_message: "Reference count must be non-negative"

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations:
  - name: publication_identifiable
    fields:
      - openalex_id
      - title
    condition: all_present
    error_message: "Publication must have OpenAlex ID and title"

  - name: retracted_publication_warning
    fields:
      - is_retracted
    condition: "is_retracted == true"
    severity: warn
    error_message: "Publication has been retracted"

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations: []

================================================================================
File: compound.yaml
Path: dq\entities\pubchem\compound.yaml
================================================================================
# configs/dq/entities/pubchem/compound.yaml
# PubChem Compound-specific DQ rules
# Inherits from: _defaults.yaml → providers/pubchem.yaml

version: "1.0.0"
provider: pubchem
entity: compound

# Thresholds: inherit from provider

# =============================================================================
# Compound-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: cid
    type: required
    nullable: false
    error_message: "CID is required"

  # Molecular weight validation
  - field: molecular_weight
    type: range
    min: 0
    nullable: true
    error_message: "Molecular weight must be non-negative"

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations: []

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations: []

================================================================================
File: publication.yaml
Path: dq\entities\pubmed\publication.yaml
================================================================================
# configs/dq/entities/pubmed/publication.yaml
# PubMed Publication-specific DQ rules
# Inherits from: _defaults.yaml → providers/pubmed.yaml

version: "1.0.0"
provider: pubmed
entity: publication

# Thresholds: inherit from provider (soft 0.05, hard 0.15)

# =============================================================================
# Publication-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: pmid
    type: range
    min: 1
    max: 100000000
    nullable: false
    error_message: "PMID is required and must be a positive integer"

  - field: title
    type: pattern
    pattern: '^.{1,2000}$'
    nullable: true
    error_message: "Title must not exceed 2000 chars"

  - field: doi
    type: pattern
    pattern: '^10\.\d{4,}/.*$'
    nullable: true
    error_message: "DOI must start with 10. prefix"

  - field: pub_year
    type: range
    min: 1800
    max: 2100
    nullable: true
    error_message: "Publication year out of valid range"

  - field: pub_type
    type: enum
    allowed:
      - Journal Article
      - Review
      - Letter
      - Editorial
      - Clinical Trial
      - Meta-Analysis
      - Case Reports
      - Comparative Study
      - Evaluation Study
    nullable: true

  - field: pmc_id
    type: pattern
    pattern: '^PMC\d+$'
    nullable: true
    error_message: "PMC ID must start with PMC followed by digits"

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations:
  - name: publication_identifiable
    fields:
      - pmid
      - title
    condition: all_present
    error_message: "Publication must have PMID and title"

  - name: has_identifier
    fields:
      - pmid
      - doi
      - pmc_id
    condition: any_present
    error_message: "At least one identifier required"

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations: []

================================================================================
File: publication.yaml
Path: dq\entities\semanticscholar\publication.yaml
================================================================================
# configs/dq/entities/semanticscholar/publication.yaml
# Semantic Scholar Publication-specific DQ rules
# Inherits from: _defaults.yaml → providers/semanticscholar.yaml

version: "1.0.0"
provider: semanticscholar
entity: publication

# Thresholds: inherit from provider (soft 0.15, hard 0.40)

# =============================================================================
# Publication-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: paper_id
    type: pattern
    pattern: '^[a-f0-9]{40}$'
    nullable: false
    error_message: "paper_id is required and must be a 40-char hex string"

  - field: doi
    type: pattern
    pattern: '^10\.\d{4,}/.*$'
    nullable: true
    error_message: "DOI must start with 10. prefix"

  - field: title
    type: pattern
    pattern: '^.{1,2000}$'
    nullable: true
    error_message: "Title must not exceed 2000 chars"

  - field: year
    type: range
    min: 1500
    max: 2100
    nullable: true
    error_message: "Publication year out of valid range"

  - field: citation_count
    type: range
    min: 0
    nullable: true
    error_message: "Citation count must be non-negative"

  - field: reference_count
    type: range
    min: 0
    nullable: true
    error_message: "Reference count must be non-negative"

  - field: influential_citation_count
    type: range
    min: 0
    nullable: true
    error_message: "Influential citation count must be non-negative"

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations:
  - name: publication_identifiable
    fields:
      - paper_id
      - title
    condition: all_present
    error_message: "Publication must have paper_id and title"

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations: []

================================================================================
File: idmapping.yaml
Path: dq\entities\uniprot\idmapping.yaml
================================================================================
# configs/dq/entities/uniprot/idmapping.yaml
# UniProt ID Mapping-specific DQ rules
# Inherits from: _defaults.yaml → providers/uniprot.yaml

version: "1.0.0"
provider: uniprot
entity: idmapping

# =============================================================================
# Elevated thresholds for ID mapping
# Many ChEMBL targets may not have UniProt mappings (expected behavior)
# =============================================================================
thresholds:
  soft_fail: 0.30  # 30% not_found is acceptable
  hard_fail: 0.80  # 80% not_found triggers hard failure

# =============================================================================
# ID Mapping-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: target_chembl_id
    type: pattern
    pattern: '^CHEMBL\d+$'
    nullable: false
    error_message: "target_chembl_id must match CHEMBL format"

  - field: mapping_status
    type: enum
    allowed:
      - found
      - not_found
      - error
    nullable: false
    error_message: "mapping_status is required and must be valid"

  - field: uniprot_accession
    type: pattern
    pattern: '^[A-Z0-9]{6,10}$'
    nullable: true
    error_message: "UniProt accession must be 6-10 alphanumeric chars"

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations: []

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations:
  # When mapping_status is 'found', accession should be present
  - name: found_has_accession
    condition_field: mapping_status
    condition_value: found
    condition_operator: eq
    then_validations:
      - field: uniprot_accession
        type: pattern
        pattern: '^[A-Z0-9]{6,10}$'
        nullable: false
        error_message: "Found mappings must have UniProt accession"

================================================================================
File: protein.yaml
Path: dq\entities\uniprot\protein.yaml
================================================================================
# configs/dq/entities/uniprot/protein.yaml
# UniProt Protein-specific DQ rules
# Inherits from: _defaults.yaml → providers/uniprot.yaml

version: "1.0.0"
provider: uniprot
entity: protein

# Thresholds: inherit from provider (stricter: soft 0.03, hard 0.10)

# =============================================================================
# Protein-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: accession
    type: pattern
    pattern: '^[A-Z0-9]{6,10}$'
    nullable: false
    error_message: "UniProt accession must be 6-10 alphanumeric chars"

  - field: entry_name
    type: pattern
    pattern: '^[A-Z0-9_]+$'
    nullable: true
    error_message: "Entry name must be alphanumeric with underscores"

  - field: organism
    type: pattern
    pattern: '^[A-Z][a-z]+ [a-z]+.*$'
    nullable: true
    error_message: "Organism should be in binomial nomenclature"

  - field: taxonomy_id
    type: range
    min: 1
    max: 10000000
    nullable: true
    error_message: "Taxonomy ID must be positive"

  - field: sequence_length
    type: range
    min: 1
    max: 100000
    nullable: true
    error_message: "Sequence length must be between 1 and 100,000"

  - field: mass
    type: range
    min: 100
    max: 10000000
    nullable: true
    error_message: "Molecular mass must be between 100 and 10,000,000 Da"

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations:
  - name: protein_identifiable
    fields:
      - accession
      - entry_name
    condition: all_present
    error_message: "Protein must have accession and entry name"

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations: []

================================================================================
File: target.yaml
Path: dq\entities\uniprot\target.yaml
================================================================================
# configs/dq/entities/uniprot/target.yaml
# UniProt Target-specific DQ rules
# Inherits from: _defaults.yaml → providers/uniprot.yaml

version: "1.0.0"
provider: uniprot
entity: target

# Thresholds: inherit from provider

# =============================================================================
# Target-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: accession
    type: required
    nullable: false
    error_message: "UniProt accession is required"

  - field: sequence_length
    type: range
    min: 1
    nullable: true
    error_message: "Sequence length must be positive"

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations: []

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations: []

================================================================================
File: chembl.yaml
Path: dq\providers\chembl.yaml
================================================================================
# configs/dq/providers/chembl.yaml
# ChEMBL-specific DQ rules
# Inherits from: _defaults.yaml

version: "1.0.0"
provider: chembl

# =============================================================================
# Provider-Specific Thresholds
# =============================================================================
thresholds:
  soft_fail: 0.05
  hard_fail: 0.15      # Stricter: ChEMBL data should be cleaner

# =============================================================================
# ChEMBL Common Field Validations
# =============================================================================
provider_field_validations:
  # ChEMBL ID format validation (applies to all ChEMBL entities)
  - field: molecule_chembl_id
    type: pattern
    pattern: '^CHEMBL\d+$'
    nullable: true
    error_message: "Invalid ChEMBL molecule ID format"

  - field: target_chembl_id
    type: pattern
    pattern: '^CHEMBL\d+$'
    nullable: true
    error_message: "Invalid ChEMBL target ID format"

  - field: assay_chembl_id
    type: pattern
    pattern: '^CHEMBL\d+$'
    nullable: true
    error_message: "Invalid ChEMBL assay ID format"

  - field: document_chembl_id
    type: pattern
    pattern: '^CHEMBL\d+$'
    nullable: true
    error_message: "Invalid ChEMBL document ID format"

================================================================================
File: crossref.yaml
Path: dq\providers\crossref.yaml
================================================================================
# configs/dq/providers/crossref.yaml
# CrossRef-specific DQ rules
# Inherits from: _defaults.yaml

version: "1.0.0"
provider: crossref

# =============================================================================
# Provider-Specific Thresholds
# =============================================================================
thresholds:
  soft_fail: 0.10  # CrossRef has variable data completeness
  hard_fail: 0.30

# =============================================================================
# CrossRef Common Field Validations
# =============================================================================
provider_field_validations:
  # DOI format validation (applies to all CrossRef entities)
  - field: doi
    type: pattern
    pattern: '^10\.\d{4,}/.*$'
    nullable: true
    error_message: "Invalid DOI format (must start with 10. prefix)"

  # Year range validation
  - field: year
    type: range
    min: 1800
    max: 2100
    nullable: true
    error_message: "Publication year out of valid range"

================================================================================
File: openalex.yaml
Path: dq\providers\openalex.yaml
================================================================================
# configs/dq/providers/openalex.yaml
# OpenAlex-specific DQ rules
# Inherits from: _defaults.yaml

version: "1.0.0"
provider: openalex

# =============================================================================
# Provider-Specific Thresholds
# =============================================================================
thresholds:
  soft_fail: 0.08  # OpenAlex has good data quality
  hard_fail: 0.25

# =============================================================================
# OpenAlex Common Field Validations
# =============================================================================
provider_field_validations:
  # OpenAlex ID format validation
  - field: openalex_id
    type: pattern
    pattern: '^W\d+$'
    nullable: true
    error_message: "Invalid OpenAlex ID format (must start with W followed by digits)"

  # DOI format validation
  - field: doi
    type: pattern
    pattern: '^10\.\d{4,}/.*$'
    nullable: true
    error_message: "Invalid DOI format (must start with 10. prefix)"

  # Year range validation
  - field: year
    type: range
    min: 1500
    max: 2100
    nullable: true
    error_message: "Publication year out of valid range"

================================================================================
File: pubchem.yaml
Path: dq\providers\pubchem.yaml
================================================================================
# configs/dq/providers/pubchem.yaml
# PubChem-specific DQ rules
# Inherits from: _defaults.yaml

version: "1.0.0"
provider: pubchem

# =============================================================================
# Provider-Specific Thresholds
# =============================================================================
thresholds:
  soft_fail: 0.08      # PubChem has more variability
  hard_fail: 0.25

# =============================================================================
# PubChem Common Field Validations
# =============================================================================
provider_field_validations:
  # CID must be positive integer
  - field: cid
    type: range
    min: 1
    nullable: true
    error_message: "CID must be a positive integer"

================================================================================
File: pubmed.yaml
Path: dq\providers\pubmed.yaml
================================================================================
# configs/dq/providers/pubmed.yaml
# PubMed-specific DQ rules
# Inherits from: _defaults.yaml

version: "1.0.0"
provider: pubmed

# =============================================================================
# Provider-Specific Thresholds
# =============================================================================
thresholds:
  soft_fail: 0.05  # PubMed has high quality curated data
  hard_fail: 0.15

# =============================================================================
# PubMed Common Field Validations
# =============================================================================
provider_field_validations:
  # PMID format validation
  - field: pmid
    type: range
    min: 1
    max: 100000000
    nullable: true
    error_message: "PMID must be a positive integer"

  # PMC ID format validation
  - field: pmc_id
    type: pattern
    pattern: '^PMC\d+$'
    nullable: true
    error_message: "PMC ID must start with PMC followed by digits"

  # DOI format validation
  - field: doi
    type: pattern
    pattern: '^10\.\d{4,}/.*$'
    nullable: true
    error_message: "Invalid DOI format (must start with 10. prefix)"

  # Year range validation
  - field: pub_year
    type: range
    min: 1800
    max: 2100
    nullable: true
    error_message: "Publication year out of valid range"

================================================================================
File: semanticscholar.yaml
Path: dq\providers\semanticscholar.yaml
================================================================================
# configs/dq/providers/semanticscholar.yaml
# Semantic Scholar-specific DQ rules
# Inherits from: _defaults.yaml

version: "1.0.0"
provider: semanticscholar

# =============================================================================
# Provider-Specific Thresholds
# Semantic Scholar has higher rate limits and more variable data
# =============================================================================
thresholds:
  soft_fail: 0.15  # Higher tolerance due to rate limit issues
  hard_fail: 0.40

# =============================================================================
# Semantic Scholar Common Field Validations
# =============================================================================
provider_field_validations:
  # Paper ID format validation (40-char hex string)
  - field: paper_id
    type: pattern
    pattern: '^[a-f0-9]{40}$'
    nullable: true
    error_message: "Invalid paper_id format (must be 40-char hex string)"

  # DOI format validation
  - field: doi
    type: pattern
    pattern: '^10\.\d{4,}/.*$'
    nullable: true
    error_message: "Invalid DOI format (must start with 10. prefix)"

  # Year range validation
  - field: year
    type: range
    min: 1500
    max: 2100
    nullable: true
    error_message: "Publication year out of valid range"

  # Citation counts must be non-negative
  - field: citation_count
    type: range
    min: 0
    nullable: true
    error_message: "Citation count must be non-negative"

================================================================================
File: uniprot.yaml
Path: dq\providers\uniprot.yaml
================================================================================
# configs/dq/providers/uniprot.yaml
# UniProt-specific DQ rules
# Inherits from: _defaults.yaml

version: "1.0.0"
provider: uniprot

# =============================================================================
# Provider-Specific Thresholds
# =============================================================================
thresholds:
  soft_fail: 0.03      # UniProt data is high quality
  hard_fail: 0.10

# =============================================================================
# UniProt Common Field Validations
# =============================================================================
provider_field_validations:
  # UniProt accession format
  - field: accession
    type: pattern
    pattern: '^[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$'
    nullable: true
    error_message: "Invalid UniProt accession format"

================================================================================
File: _defaults.yaml
Path: filter\_defaults.yaml
================================================================================
# configs/filter/_defaults.yaml
# =============================================================================
# Global Filter Configuration Defaults
# =============================================================================
# Version: 1.0.0
# Reference: ADR-028 (Filter Rules Externalization)
#
# Merge priority (lowest to highest):
# 1. This file (_defaults.yaml)
# 2. providers/{provider}.yaml
# 3. entities/{provider}/{entity}.yaml
# 4. Inline overrides in pipeline config (filter_rules)

version: "1.0.0"

# =============================================================================
# Input Filter Defaults
# =============================================================================
# Input filters control which records to fetch from external APIs.
# Typically used for targeted data acquisition from CSV files.
input_filter:
  # Whether input filtering is enabled (must be set per-entity)
  enabled: false

  # Default batch size for API requests
  # Providers may override based on their API limits
  batch_size: 100

  # Source path and columns MUST be defined in entity config:
  # source_path: "data/input/<entity>.csv"
  # column_name: "<id_column>"
  # filter_field: "<api_field>"
  # fallback_column: "<fallback_field>"  # Optional: search by title if ID not found

# =============================================================================
# Gold Filter Defaults
# =============================================================================
# Gold filters control which records pass from Silver to Gold layer.
# Filters are applied AFTER transformation in BaseTransformer.
gold_filters:
  # Required fields - records missing these fields are excluded
  # Entity-specific; empty by default
  required_fields: []

  # Column value filters - inclusion lists
  # Format: field_name: [allowed_value1, allowed_value2, ...]
  columns: {}

  # Numeric range filters
  # Format: field_name: {min: X, max: Y, include_min: true, include_max: true}
  ranges: {}

  # List length filters
  # Format: field_name: {min: X, max: Y}
  list_lengths: {}

  # List contains filters
  # Format: field_name: {values: [v1, v2], mode: "all"|"any"}
  list_contains: {}

  # Exclude if present - fields that should NOT have values
  exclude_if_present: []

================================================================================
File: activity.yaml
Path: filter\entities\chembl\activity.yaml
================================================================================
# configs/filter/entities/chembl/activity.yaml
# =============================================================================
# ChEMBL Activity Filter Configuration
# =============================================================================
# Entity-specific filter rules for biological activity data.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: chembl
entity: activity

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# Filter activities by activity_id from CSV
input_filter:
  enabled: true
  source_path: "data/input/activity.csv"
  column_name: "activity_id"
  filter_field: "activity_id"
  batch_size: 20

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Strict criteria for high-quality activity data
gold_filters:
  # Column value filters - inclusion lists
  columns:
    # Only IC50 and Ki measurements
    standard_type: [IC50, Ki]
    # Only nanoMolar units for consistency
    standard_units: [nM]
    # Only exact values (no inequalities)
    standard_relation: ["="]
    # Binding (B) and Functional (F) assays only
    assay_type: [B, F]
    # Exclude potential duplicates
    potential_duplicate: ["0"]

  # Numeric range filters
  ranges:
    standard_value:
      min: 0
      include_min: false  # Exclude exactly 0 (invalid)

  # Required fields - must be non-null
  required_fields:
    - standard_type
    - standard_value
    - standard_units
    - target_chembl_id

================================================================================
File: assay.yaml
Path: filter\entities\chembl\assay.yaml
================================================================================
# configs/filter/entities/chembl/assay.yaml
# =============================================================================
# ChEMBL Assay Filter Configuration
# =============================================================================
# Entity-specific filter rules for bioassay data.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: chembl
entity: assay

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# Filter assays by assay_chembl_id from CSV
input_filter:
  enabled: true
  source_path: "data/input/assay.csv"
  column_name: "assay_chembl_id"
  filter_field: "assay_chembl_id"
  batch_size: 20

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for high-quality assay data
gold_filters:
  # Column value filters
  columns:
    # Binding (B) and Functional (F) assays
    assay_type: [B, F]
    # High confidence scores only (8 or 9 on 0-9 scale)
    confidence_score: ["8", "9"]
    # Direct interaction only
    relationship_type: [D]

  # Required fields
  required_fields:
    - assay_type
    - description

================================================================================
File: assay_parameters.yaml
Path: filter\entities\chembl\assay_parameters.yaml
================================================================================
# configs/filter/entities/chembl/assay_parameters.yaml
# =============================================================================
# ChEMBL Assay Parameters Filter Configuration
# =============================================================================
# Entity-specific filter rules for assay parameter data.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: chembl
entity: assay_parameters

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# Filter assay parameters by assay_param_id from CSV
# Reference table - high batch size for speed
input_filter:
  enabled: true
  source_path: "data/input/assay_parameters.csv"
  column_name: "assay_param_id"
  filter_field: "assay_param_id"
  batch_size: 1000

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for valid assay parameters
gold_filters:
  # Required fields
  required_fields:
    - assay_chembl_id
    - type

================================================================================
File: cell_line.yaml
Path: filter\entities\chembl\cell_line.yaml
================================================================================
# configs/filter/entities/chembl/cell_line.yaml
# =============================================================================
# ChEMBL Cell Line Filter Configuration
# =============================================================================
# Entity-specific filter rules for cell line data.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: chembl
entity: cell_line

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# Filter cell lines by cell_chembl_id from CSV
input_filter:
  enabled: true
  source_path: "data/input/cell.csv"
  column_name: "cell_chembl_id"
  filter_field: "cell_chembl_id"
  batch_size: 20

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for valid cell lines
gold_filters:
  # Required fields
  required_fields:
    - cell_name

================================================================================
File: compound_record.yaml
Path: filter\entities\chembl\compound_record.yaml
================================================================================
# configs/filter/entities/chembl/compound_record.yaml
# =============================================================================
# ChEMBL Compound Record Filter Configuration
# =============================================================================
# Entity-specific filter rules for compound records linking molecules to documents.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: chembl
entity: compound_record

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# Filter by molecule_chembl_id from molecule CSV
# NOTE: ChEMBL API doesn't support filtering by record_id directly
input_filter:
  enabled: true
  source_path: "data/input/molecule.csv"
  column_name: "molecule_chembl_id"
  filter_field: "molecule_chembl_id"
  batch_size: 20

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for valid compound records
gold_filters:
  # Required fields - must have both molecule and document references
  required_fields:
    - molecule_chembl_id
    - document_chembl_id

================================================================================
File: molecule.yaml
Path: filter\entities\chembl\molecule.yaml
================================================================================
# configs/filter/entities/chembl/molecule.yaml
# =============================================================================
# ChEMBL Molecule Filter Configuration
# =============================================================================
# Entity-specific filter rules for molecule/compound data.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: chembl
entity: molecule

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# Filter molecules by molecule_chembl_id from CSV
input_filter:
  enabled: true
  source_path: "data/input/molecule.csv"
  column_name: "molecule_chembl_id"
  filter_field: "molecule_chembl_id"
  batch_size: 20

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for drug-like small molecules
gold_filters:
  # Column value filters
  columns:
    # Small molecules only (exclude biologics)
    molecule_type: [Small molecule]
    # Must have MOL structure
    structure_type: [MOL]
    # Exclude inorganic compounds
    inorganic_flag: ["0"]

  # Required fields
  required_fields:
    - molecule_chembl_id

================================================================================
File: protein_class.yaml
Path: filter\entities\chembl\protein_class.yaml
================================================================================
# configs/filter/entities/chembl/protein_class.yaml
# =============================================================================
# ChEMBL Protein Class Filter Configuration
# =============================================================================
# Entity-specific filter rules for protein classification hierarchy.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: chembl
entity: protein_class

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# Reference table - full load, no input filtering
input_filter:
  enabled: false

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for valid protein classes
gold_filters:
  # Column value filters
  columns:
    # Exclude downgraded classifications
    downgraded: ["0"]

  # Required fields
  required_fields:
    - pref_name

================================================================================
File: publication.yaml
Path: filter\entities\chembl\publication.yaml
================================================================================
# configs/filter/entities/chembl/publication.yaml
# =============================================================================
# ChEMBL Publication Filter Configuration
# =============================================================================
# Entity-specific filter rules for scientific publication data.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: chembl
entity: publication

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# Filter publications by document_chembl_id from CSV
input_filter:
  enabled: true
  source_path: "data/input/publication.csv"
  column_name: "document_chembl_id"
  filter_field: "document_chembl_id"
  batch_size: 20

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for valid publications
gold_filters:
  # Column value filters
  columns:
    # Publications only (exclude patents, books, etc.)
    doc_type: [PUBLICATION]

  # Numeric range filters
  ranges:
    # Reasonable year range
    year:
      min: 1950
      include_min: false

  # Required fields (pubmed_id and doi are optional - not all publications have them)
  required_fields:
    - document_chembl_id
    - doc_type
    - title

================================================================================
File: publication_similarity.yaml
Path: filter\entities\chembl\publication_similarity.yaml
================================================================================
# configs/filter/entities/chembl/publication_similarity.yaml
# =============================================================================
# ChEMBL Publication Similarity Filter Configuration
# =============================================================================
# Entity-specific filter rules for document similarity data.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: chembl
entity: publication_similarity

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# No input filtering - process all similarity records
input_filter:
  enabled: false

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for significant similarities
gold_filters:
  # Numeric range filters
  ranges:
    # Filter to significant similarities only
    max_tani:
      min: 0.5
      include_min: true

  # Required fields
  required_fields:
    - sim_id
    - doc_1
    - doc_2

================================================================================
File: publication_term.yaml
Path: filter\entities\chembl\publication_term.yaml
================================================================================
# configs/filter/entities/chembl/publication_term.yaml
# =============================================================================
# ChEMBL Publication Term Filter Configuration
# =============================================================================
# Entity-specific filter rules for document terms (MeSH, keywords).
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: chembl
entity: publication_term

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# Filter by document_chembl_id from publication CSV
input_filter:
  enabled: true
  source_path: "data/input/publication.csv"
  column_name: "document_chembl_id"
  filter_field: "document_chembl_id"
  batch_size: 20

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for valid terms
gold_filters:
  # Column value filters
  columns:
    # Filter to main term types
    term_type: [MESH_HEADING, KEYWORD]

  # Required fields
  required_fields:
    - document_chembl_id
    - term
    - term_type

================================================================================
File: target.yaml
Path: filter\entities\chembl\target.yaml
================================================================================
# configs/filter/entities/chembl/target.yaml
# =============================================================================
# ChEMBL Target Filter Configuration
# =============================================================================
# Entity-specific filter rules for drug target data.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: chembl
entity: target

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# Filter targets by target_chembl_id from CSV
input_filter:
  enabled: true
  source_path: "data/input/target.csv"
  column_name: "target_chembl_id"
  filter_field: "target_chembl_id"
  batch_size: 20

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for single protein targets
gold_filters:
  # Column value filters
  columns:
    # Single protein targets only
    target_type: [SINGLE PROTEIN]

  # List length filters
  list_lengths:
    # Exactly one accession (single protein)
    component_accessions:
      min: 1
      max: 1
    # At least one component ID
    component_ids:
      min: 1

  # List contains filters
  list_contains:
    # Must be protein components
    component_types:
      values: [PROTEIN]
      mode: all

  # Required fields
  required_fields:
    - pref_name
    - organism

================================================================================
File: target_component.yaml
Path: filter\entities\chembl\target_component.yaml
================================================================================
# configs/filter/entities/chembl/target_component.yaml
# =============================================================================
# ChEMBL Target Component Filter Configuration
# =============================================================================
# Entity-specific filter rules for target component (protein) data.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: chembl
entity: target_component

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# Filter components by component_id from CSV
input_filter:
  enabled: true
  source_path: "data/input/target_component.csv"
  column_name: "component_id"
  filter_field: "component_id"
  batch_size: 100

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for protein components
gold_filters:
  # Column value filters
  columns:
    # Protein components only
    component_type: ["PROTEIN"]

  # Required fields
  required_fields:
    - accession

================================================================================
File: publication.yaml
Path: filter\entities\composite\publication.yaml
================================================================================
# configs/filter/entities/composite/publication.yaml
# =============================================================================
# Composite Publication Filter Configuration
# =============================================================================
# Entity-specific filter rules for composite publication pipeline.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: composite
entity: publication

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# No input filter for composite pipeline
# Composite pipeline aggregates from multiple sources internally
input_filter:
  enabled: false

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for valid publications
gold_filters:
  # Only include publications with title
  required_fields:
    - title

================================================================================
File: publication.yaml
Path: filter\entities\crossref\publication.yaml
================================================================================
# configs/filter/entities/crossref/publication.yaml
# =============================================================================
# CrossRef Publication Filter Configuration
# =============================================================================
# Entity-specific filter rules for CrossRef publication data.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: crossref
entity: publication

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# Filter publications by DOI from CSV
# Supports fallback to title search if DOI not found (404)
input_filter:
  enabled: true
  source_path: "data/input/dois.csv"
  column_name: "doi"
  filter_field: "doi"
  batch_size: 50  # Polite pool API - conservative batch size
  fallback_column: "title"  # Search by title if DOI not found (404)

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for valid publications
gold_filters:
  # Numeric range filters
  ranges:
    # Reasonable year range
    year:
      min: 1900
      max: 2100

  # Required fields
  required_fields:
    - doi
    - title

================================================================================
File: publication.yaml
Path: filter\entities\openalex\publication.yaml
================================================================================
# configs/filter/entities/openalex/publication.yaml
# =============================================================================
# OpenAlex Publication Filter Configuration
# =============================================================================
# Entity-specific filter rules for OpenAlex publication data.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: openalex
entity: publication

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# Filter publications by DOI from CSV
# Supports fallback to title search if DOI not found or empty
input_filter:
  enabled: true
  source_path: "data/input/dois.csv"
  column_name: "doi"
  filter_field: "doi"
  batch_size: 50  # Polite pool API - conservative batch size
  fallback_column: "title"  # Search by title if DOI not found or empty

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for valid publications
gold_filters:
  # Numeric range filters
  ranges:
    # Reasonable year range
    year:
      min: 1900
      max: 2100

  # Required fields
  required_fields:
    - openalex_id
    - title

================================================================================
File: compound.yaml
Path: filter\entities\pubchem\compound.yaml
================================================================================
# configs/filter/entities/pubchem/compound.yaml
# =============================================================================
# PubChem Compound Filter Configuration
# =============================================================================
# Entity-specific filter rules for PubChem compound data.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: pubchem
entity: compound

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# Filter compounds by SMILES from CSV
# NOTE: PubChem SMILES search is per-compound due to API limitations
input_filter:
  enabled: true
  source_path: "data/input/molecule.csv"
  column_name: "canonical_smiles"
  filter_field: "smiles"
  batch_size: 1  # SMILES search is per-compound

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for valid compounds
gold_filters:
  # Required fields
  required_fields:
    - cid
    - molecular_formula

  # Empty columns filter (use defaults)
  columns: {}

================================================================================
File: publication.yaml
Path: filter\entities\pubmed\publication.yaml
================================================================================
# configs/filter/entities/pubmed/publication.yaml
# =============================================================================
# PubMed Publication Filter Configuration
# =============================================================================
# Entity-specific filter rules for PubMed publication data.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: pubmed
entity: publication

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# Filter publications by PMID from CSV
# Supports fallback to title search if PMID not found
input_filter:
  enabled: true
  source_path: "data/input/pubmed.csv"
  column_name: "pubmed_id"
  filter_field: "pmid"
  batch_size: 100
  fallback_column: "title"  # Search by title if PMID not found or empty

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for valid publications
gold_filters:
  # Required fields
  required_fields:
    - pmid
    - title

  # Empty columns filter (use defaults)
  columns: {}

================================================================================
File: publication.yaml
Path: filter\entities\semanticscholar\publication.yaml
================================================================================
# configs/filter/entities/semanticscholar/publication.yaml
# =============================================================================
# Semantic Scholar Publication Filter Configuration
# =============================================================================
# Entity-specific filter rules for Semantic Scholar publication data.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: semanticscholar
entity: publication

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# Filter publications by DOI from CSV
# Supports fallback to title search if DOI not found or empty
input_filter:
  enabled: true
  source_path: "data/input/dois.csv"
  column_name: "doi"
  filter_field: "doi"
  batch_size: 100
  fallback_column: "title"  # Search by title if DOI not found or empty

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for valid publications
gold_filters:
  # Numeric range filters
  ranges:
    # Reasonable year range
    year:
      min: 1900
      max: 2100

  # Required fields
  required_fields:
    - paper_id
    - title

================================================================================
File: idmapping.yaml
Path: filter\entities\uniprot\idmapping.yaml
================================================================================
# configs/filter/entities/uniprot/idmapping.yaml
# =============================================================================
# UniProt ID Mapping Filter Configuration
# =============================================================================
# Entity-specific filter rules for UniProt ID mapping results.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: uniprot
entity: idmapping

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# Disabled - ID Mapping reads directly from source.input_path
# The adapter handles filtering internally via the ID Mapping API
input_filter:
  enabled: false
  source_path: "data/input/target.csv"
  column_name: "target_chembl_id"
  filter_field: "target_chembl_id"
  batch_size: 100

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for valid ID mappings
gold_filters:
  # Required fields
  required_fields:
    - target_chembl_id
    - mapping_status

================================================================================
File: protein.yaml
Path: filter\entities\uniprot\protein.yaml
================================================================================
# configs/filter/entities/uniprot/protein.yaml
# =============================================================================
# UniProt Protein Filter Configuration
# =============================================================================
# Entity-specific filter rules for UniProt protein data.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: uniprot
entity: protein

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# Filter proteins by UniProt accession from CSV
# UniProt adapter implements FilterableDataSourcePort with OR-query batching
input_filter:
  enabled: true
  source_path: "data/input/protein.csv"
  column_name: "uniprot_id"
  filter_field: "accession"
  batch_size: 100

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for high-quality protein entries
gold_filters:
  # Column value filters
  columns:
    # Swiss-Prot (reviewed) entries only
    reviewed: ["true"]

  # Required fields
  required_fields:
    - accession
    - entry_name
    - organism

================================================================================
File: chembl.yaml
Path: filter\providers\chembl.yaml
================================================================================
# configs/filter/providers/chembl.yaml
# =============================================================================
# ChEMBL Provider Filter Configuration
# =============================================================================
# Provider-level defaults for all ChEMBL entities.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: chembl

# -----------------------------------------------------------------------------
# Input Filter Defaults
# -----------------------------------------------------------------------------
# ChEMBL API optimal batch size for most endpoints
input_filter:
  batch_size: 20

# -----------------------------------------------------------------------------
# Gold Filter Defaults
# -----------------------------------------------------------------------------
# Common patterns across ChEMBL entities
# (Entity-specific overrides in entities/chembl/*.yaml)
gold_filters:
  # Most ChEMBL entities use these fields
  required_fields: []

  # Common columns filter patterns
  # (Entity-specific values in entity configs)
  columns: {}

================================================================================
File: crossref.yaml
Path: filter\providers\crossref.yaml
================================================================================
# configs/filter/providers/crossref.yaml
# =============================================================================
# CrossRef Provider Filter Configuration
# =============================================================================
# Provider-level defaults for CrossRef entities.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: crossref

# -----------------------------------------------------------------------------
# Input Filter Defaults
# -----------------------------------------------------------------------------
# CrossRef Polite pool - conservative batch size
input_filter:
  batch_size: 50

# -----------------------------------------------------------------------------
# Gold Filter Defaults
# -----------------------------------------------------------------------------
gold_filters:
  required_fields: []
  columns: {}

================================================================================
File: openalex.yaml
Path: filter\providers\openalex.yaml
================================================================================
# configs/filter/providers/openalex.yaml
# =============================================================================
# OpenAlex Provider Filter Configuration
# =============================================================================
# Provider-level defaults for OpenAlex entities.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: openalex

# -----------------------------------------------------------------------------
# Input Filter Defaults
# -----------------------------------------------------------------------------
# OpenAlex Polite pool - conservative batch size
input_filter:
  batch_size: 50

# -----------------------------------------------------------------------------
# Gold Filter Defaults
# -----------------------------------------------------------------------------
gold_filters:
  required_fields: []
  columns: {}

================================================================================
File: pubchem.yaml
Path: filter\providers\pubchem.yaml
================================================================================
# configs/filter/providers/pubchem.yaml
# =============================================================================
# PubChem Provider Filter Configuration
# =============================================================================
# Provider-level defaults for PubChem entities.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: pubchem

# -----------------------------------------------------------------------------
# Input Filter Defaults
# -----------------------------------------------------------------------------
# PubChem SMILES search requires per-compound queries
# due to API limitations (no batch SMILES search)
input_filter:
  batch_size: 1

# -----------------------------------------------------------------------------
# Gold Filter Defaults
# -----------------------------------------------------------------------------
gold_filters:
  required_fields: []
  columns: {}

================================================================================
File: pubmed.yaml
Path: filter\providers\pubmed.yaml
================================================================================
# configs/filter/providers/pubmed.yaml
# =============================================================================
# PubMed Provider Filter Configuration
# =============================================================================
# Provider-level defaults for PubMed entities.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: pubmed

# -----------------------------------------------------------------------------
# Input Filter Defaults
# -----------------------------------------------------------------------------
# NCBI E-utilities supports batch PMID lookups
input_filter:
  batch_size: 100

# -----------------------------------------------------------------------------
# Gold Filter Defaults
# -----------------------------------------------------------------------------
gold_filters:
  required_fields: []
  columns: {}

================================================================================
File: semanticscholar.yaml
Path: filter\providers\semanticscholar.yaml
================================================================================
# configs/filter/providers/semanticscholar.yaml
# =============================================================================
# Semantic Scholar Provider Filter Configuration
# =============================================================================
# Provider-level defaults for Semantic Scholar entities.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: semanticscholar

# -----------------------------------------------------------------------------
# Input Filter Defaults
# -----------------------------------------------------------------------------
# Semantic Scholar paper lookup batch size
input_filter:
  batch_size: 100

# -----------------------------------------------------------------------------
# Gold Filter Defaults
# -----------------------------------------------------------------------------
gold_filters:
  required_fields: []
  columns: {}

================================================================================
File: uniprot.yaml
Path: filter\providers\uniprot.yaml
================================================================================
# configs/filter/providers/uniprot.yaml
# =============================================================================
# UniProt Provider Filter Configuration
# =============================================================================
# Provider-level defaults for UniProt entities.
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: uniprot

# -----------------------------------------------------------------------------
# Input Filter Defaults
# -----------------------------------------------------------------------------
# UniProt adapter uses OR-query batching for efficient lookups
input_filter:
  batch_size: 100

# -----------------------------------------------------------------------------
# Gold Filter Defaults
# -----------------------------------------------------------------------------
gold_filters:
  required_fields: []
  columns: {}

================================================================================
File: naming_exceptions.yaml
Path: naming_exceptions.yaml
================================================================================
# Naming Convention Exceptions
# This file documents allowed exceptions to the naming conventions in RULES.md §2.
# Version: 2.1
# Last Updated: 2026-01-21

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
# This is an exception to general snake_case for uniqueness
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

# Notes on enforcement
# - The naming_audit.py tool uses this file's content as reference
# - Violations against these exceptions should NOT be flagged
# - Add new exceptions here with justification

================================================================================
File: _base.yaml
Path: pipelines\_base.yaml
================================================================================
# configs/pipelines/_base.yaml
# =============================================================================
# Unified Base Schema for BioETL Pipeline Configurations
# =============================================================================
#
# This file defines the canonical schema for all pipeline configurations.
# All entity-specific configs MUST inherit these defaults unless explicitly
# overriding with documented justification.
#
# Version: 2.1.0
# Reference: RULES.md v5.10, Appendix D; ADR-029 (Convention-based Paths)
# Last Updated: 2026-01-21
#
# Usage:
#   Entity configs specify only entity-specific fields:
#   - pipeline_name, provider, entity_type
#   - primary_keys, silver_table, gold_table
#   - DQ overrides (only fields that DIFFER from entity DQ config)
#   - Explicit overrides for paths/configs that differ from convention
#
# Inheritance Chain:
#   _base.yaml (this file) -> <provider>/<entity>.yaml
#
# =============================================================================
#
# Convention-Based Path Resolution (ADR-029)
# =============================================================================
#
# The config loader auto-computes paths/references from provider and entity_type
# when not explicitly specified. This reduces duplication across configs.
#
# Auto-computed File References:
#   source_file       -> ../../sources/{provider}.yaml
#   dq_config_file    -> ../../dq/entities/{provider}/{entity_type}.yaml
#   filter_config_file -> ../../filter/entities/{provider}/{entity_type}.yaml
#
# Auto-computed Sink Paths:
#   sink.bronze.path           -> data/output/bronze/{provider}/{entity_type}
#   sink.silver.path           -> data/output/silver/{provider}/{entity_type}
#   sink.gold.path             -> data/output/gold/{provider}/{entity_type}
#   sink.silver.csv_export.path -> {sink.silver.path}
#   sink.gold.csv_export.path   -> {sink.gold.path}
#
# Auto-propagated Primary Keys:
#   sink.silver.primary_key    -> {primary_keys}
#   sink.silver.sort_by.columns -> {primary_keys}
#   sink.gold.sort_by.columns   -> {primary_keys}
#
# Filter/DQ Rules:
#   - input_filter and gold_filters are loaded from filter_config_file
#   - dq_rules are loaded from dq_config_file
#   - Inline overrides in pipeline config are merged on top
#
# Minimal Pipeline Config Example:
#   pipeline_name: chembl_activity
#   provider: chembl
#   entity_type: activity
#   version: "1.2.0"
#   description: "Extract biological activity records from ChEMBL API"
#   primary_keys: ["activity_id"]
#   silver_table: "chembl_activity"
#   gold_table: "chembl_activity"
#   # All paths, filters, DQ rules inherited by convention
#
# =============================================================================

# -----------------------------------------------------------------------------
# Schema Version
# -----------------------------------------------------------------------------
schema_version: "2.0.0"

# -----------------------------------------------------------------------------
# Pipeline Identification (MUST be overridden in entity config)
# -----------------------------------------------------------------------------
# pipeline_name: <provider>_<entity>  # MUST: Unique identifier
# provider: <provider>                 # MUST: chembl | pubchem | uniprot | ...
# entity_type: <entity>                # MUST: activity | assay | molecule | ...
# version: "1.0.0"                     # MUST: Semantic version of config

# -----------------------------------------------------------------------------
# Source Configuration
# -----------------------------------------------------------------------------
# NOTE: Source settings (type, load_strategy, rate_limit, circuit_breaker)
# are defined in configs/sources/<provider>.yaml for DRY compliance.
# Pipeline configs reference source via: source_file: ../../sources/<provider>.yaml

source:
  # Default source type (can be overridden for file-based pipelines)
  type: api

  # Load strategy
  # - full: Complete dataset refresh (default for most pipelines)
  # - incremental: Delta loads using watermark_field (future enhancement)
  load_strategy: full

  # Watermark field for incremental loads (SHOULD specify when using incremental)
  # watermark_field: updated_at

# -----------------------------------------------------------------------------
# Transformation Configuration
# -----------------------------------------------------------------------------
transform:
  # Version of transformation logic (MUST match config version)
  # version: "1.0.0"  # Inherited from root `version` field

  # Transformation steps (SHOULD document for complex pipelines)
  # These are implemented in code but documented here for clarity
  steps: []
  # Example steps:
  #   - normalize_units      # Standardize measurement units
  #   - validate_smiles      # Validate SMILES notation
  #   - deduplicate          # Remove duplicate records
  #   - enrich_metadata      # Add computed fields

# -----------------------------------------------------------------------------
# Data Quality Rules
# -----------------------------------------------------------------------------
dq_rules:
  # Soft threshold - triggers WARNING but continues processing
  # MUST: Default 5% error rate before warning
  soft_fail_threshold: 0.05

  # Hard threshold - triggers FAILURE and stops batch
  # MUST: Default 20% error rate before failure
  hard_fail_threshold: 0.20

  # Apply stricter validation rules (feature flag)
  strict_validation: false

  # Deviations from defaults MUST be documented with justification
  # Example: ID mapping may have higher not_found rates (0.30/0.80)

  # ---------------------------------------------------------------------------
  # Field-Level Validations (Extended DQ)
  # ---------------------------------------------------------------------------
  # Define validation rules for specific fields. Types:
  # - range: Numeric range validation (min/max)
  # - pattern: Regex pattern matching
  # - enum: Allowed values validation
  # - custom: Custom validator function reference
  #
  # Example:
  # field_validations:
  #   - field: "standard_value"
  #     type: "range"
  #     min: 0
  #     max: 1000000000
  #     nullable: false
  #   - field: "molecule_chembl_id"
  #     type: "pattern"
  #     pattern: "^CHEMBL\\d+$"
  #     nullable: false
  #   - field: "assay_type"
  #     type: "enum"
  #     allowed: ["B", "F", "A", "T", "P"]
  #     nullable: true
  #   - field: "smiles"
  #     type: "custom"
  #     validator: "smiles_validator"
  #     nullable: true
  field_validations: []

  # ---------------------------------------------------------------------------
  # Cross-Field Validations
  # ---------------------------------------------------------------------------
  # Validate relationships between multiple fields. Conditions:
  # - all_present: All fields must be non-null
  # - any_present: At least one field must be non-null
  # - mutually_exclusive: Only one field can be non-null
  # - conditional_required: If field A present, field B required
  # - custom: Custom validation function
  #
  # Example:
  # cross_field_validations:
  #   - name: "activity_completeness"
  #     fields: ["standard_value", "standard_units", "standard_type"]
  #     condition: "all_present"
  #   - name: "identifier_present"
  #     fields: ["doi", "pmid", "title"]
  #     condition: "any_present"
  cross_field_validations: []

  # ---------------------------------------------------------------------------
  # Conditional Validations
  # ---------------------------------------------------------------------------
  # Apply validations only when a condition is met.
  # Operators: eq, ne, in, not_in
  #
  # Example:
  # conditional_validations:
  #   - name: "ic50_range_check"
  #     condition_field: "standard_type"
  #     condition_value: "IC50"
  #     condition_operator: "eq"
  #     then_validations:
  #       - field: "standard_value"
  #         type: "range"
  #         min: 0.001
  #         max: 100000
  #         nullable: false
  conditional_validations: []

  # ---------------------------------------------------------------------------
  # Invalid Record Policy
  # ---------------------------------------------------------------------------
  # Policy for handling records that fail validation:
  # - quarantine: Send to quarantine for manual review (default)
  # - skip: Log and skip the record silently
  # - fail: Fail the batch immediately
  invalid_record_policy: "quarantine"

  # ---------------------------------------------------------------------------
  # DQ Report Configuration
  # ---------------------------------------------------------------------------
  # Configuration for DQ report generation
  report:
    enabled: true
    format: "json"  # json | yaml | csv
    include_sample_failures: true
    sample_size: 10

# -----------------------------------------------------------------------------
# Circuit Breaker Configuration
# -----------------------------------------------------------------------------
circuit_breaker:
  # Number of consecutive failures before circuit opens
  # MUST: Default 5 failures
  failure_threshold: 5

  # Seconds to wait before attempting recovery (Half-Open state)
  # MUST: Default 300 seconds (5 minutes)
  recovery_timeout: 300

  # Provider-specific overrides are defined in source configs

# -----------------------------------------------------------------------------
# Sink Configuration
# -----------------------------------------------------------------------------
sink:
  # ---------------------------------------------------------------------------
  # Bronze Layer - Raw Data
  # ---------------------------------------------------------------------------
  bronze:
    # Output format
    format: jsonl

    # Preserve original JSON structure
    save_json: true

    # MUST: No random elements in writes (ADR-014)
    deterministic: true

    # Save _metadata.yaml sidecar file (disabled by default)
    save_metadata: true

    # DQ report configuration for Bronze layer
    dq_report:
      enabled: true

    # Metadata configuration (when save_metadata: true)
    metadata:
       lineage:
         source_system: "<provider>"
         source_version: "<version>"
         extraction_method: "api"
       owner: "data-team"
       steward: "<pipeline>-owner"
       description: "Raw <provider> <entity> data"
       tags: ["<provider>", "<entity>", "raw"]
       retention_days: 90
       sla_freshness_hours: 24

    # Flat structure mode (default: false)
    # When enabled, data is written directly to {path}/{date}/ without {provider}/{entity}/ prefix:
    # - Normal (false): {path}/{provider}/{entity}/{date}/batch_...
    # - Flat (true):    {path}/{date}/batch_...
    # Use flat_structure=true when path already includes provider/entity segments.
    flat_structure: false

    # Path template (overridden per entity)
    # path: data/output/bronze

  # ---------------------------------------------------------------------------
  # Silver Layer - Cleansed Data
  # ---------------------------------------------------------------------------
  silver:
    # MUST: Use Delta Lake format (not parquet)
    format: delta

    # Write mode
    # - merge: Upsert based on primary_key (default)
    # - overwrite: Full table replacement
    mode: merge

    # Schema evolution strategy
    on_schema_mismatch: evolve

    # Data classification
    # - public: No access restrictions
    # - internal: Organization-internal only
    # - restricted: PII or sensitive data
    classification: public

    # Forensic data retention
    # false: 7-day default retention (default)
    # true: 30-day retention for critical tables (requires justification)
    forensic_retention: false  # true только для Critical tables (требует обоснования)

    # MUST: No random elements in writes (ADR-014)
    deterministic: true

    # Save _metadata.yaml sidecar file (disabled by default)
    save_metadata: true

    # DQ report configuration for Silver layer
    dq_report:
      enabled: true

    # Metadata configuration (when save_metadata: true)
    metadata:
       lineage:
         source_layer: "bronze"
         transformations: ["deduplication", "normalization", "dq_validation"]
       quality_expectations:
         completeness: 0.95
         accuracy: 0.99
       description: "Cleansed <provider> <entity> data"
       tags: ["<provider>", "<entity>", "silver", "validated"]

    # CSV export configuration
    csv_export:
      enabled: true
      delimiter: ","
      header: true
      encoding: "utf-8"

    # Partitioning (default: no partitioning)
    # Override in entity config when partitioning is needed
    partition_by: []

    # Sort configuration (ADR-014: deterministic writes)
    # ascending: true is the default for all entity configs
    sort_by:
      ascending: true
      # columns: [<entity_id>]  # MUST be overridden in entity config

    # Flat structure mode (default: false)
    # When enabled, data is written directly to the path without table_name subdirectory:
    # - Delta: data written directly to {path}/ (instead of {path}/{table_name}/)
    # - CSV: {table_name}.csv at {path} (unchanged)
    # - Metadata: {table_name}_metadata.yaml (instead of {path}/{table_name}/_metadata.yaml)
    # - DQ Report: {table_name}_dq_report.json (instead of {path}/{table_name}/_dq_reports/...)
    flat_structure: false

    # Entity-specific (MUST be overridden):
    # path: data/output/silver
    # primary_key: [<entity_id>]

  # ---------------------------------------------------------------------------
  # Gold Layer - Business-Ready Data
  # ---------------------------------------------------------------------------
  gold:
    # Enable Gold layer processing
    enabled: true

    # Strict validation for Gold layer (ADR-018)
    validation:
      strict: true

    # MUST: Use Delta Lake format
    format: delta

    # Write mode (overwrite is common for aggregated Gold tables)
    mode: overwrite

    # MUST: No random elements in writes (ADR-014)
    deterministic: true

    # Save _metadata.yaml sidecar file (disabled by default)
    save_metadata: true

    # DQ report configuration for Gold layer
    dq_report:
      enabled: true

    # Metadata configuration (when save_metadata: true)
    metadata:
        lineage:
          source_layer: "silver"
          filters_applied: true
        business_domain: "drug-discovery"
        use_cases: ["ml-training", "reporting", "analytics"]
        description: "Business-ready <provider> <entity> data"
        tags: ["<provider>", "<entity>", "gold", "ml-ready"]

    # CSV export configuration
    csv_export:
      enabled: true
      delimiter: ","
      header: true
      encoding: "utf-8"

    # Sort configuration (ADR-014: deterministic writes)
    # ascending: true is the default for all entity configs
    sort_by:
      ascending: true
      # columns: [<entity_id>]  # MUST be overridden in entity config

    # Flat structure mode (default: false)
    # When enabled, data is written directly to the path without table_name subdirectory:
    # - Delta: data written directly to {path}/ (instead of {path}/{table_name}/)
    # - CSV: {table_name}.csv at {path} (unchanged)
    # - Metadata: {table_name}_metadata.yaml (instead of {path}/{table_name}/_metadata.yaml)
    # - DQ Report: {table_name}_dq_report.json (instead of {path}/{table_name}/_dq_reports/...)
    flat_structure: false

    # Entity-specific (MUST be overridden):
    # path: data/output/gold

# -----------------------------------------------------------------------------
# Maintenance Configuration
# -----------------------------------------------------------------------------
maintenance:
  # Automatic VACUUM execution
  auto_vacuum: false

  # Retention period for VACUUM (days)
  vacuum_retention_days: 7

# -----------------------------------------------------------------------------
# Input Filter Configuration
# -----------------------------------------------------------------------------
input_filter:
  # Enable filtering by input CSV
  enabled: false

  # Default batch size for filtered processing
  batch_size: 100

  # Entity-specific (when enabled):
  # source_path: data/input/<entity>.csv
  # column_name: <id_column>
  # filter_field: <api_field>
  # fallback_column: <fallback_field>  # Optional: for DOI resolution

# -----------------------------------------------------------------------------
# Gold Filters Configuration
# -----------------------------------------------------------------------------
# Entity-specific gold filters are defined in each pipeline config.
# Common patterns:
#
# gold_filters:
#   columns:
#     <field>: [<allowed_values>]
#   ranges:
#     <field>:
#       min: <value>
#       max: <value>
#       include_min: true/false
#       include_max: true/false
#   required_fields:
#     - <field1>
#     - <field2>
#   list_lengths:
#     <list_field>:
#       min: <value>
#       max: <value>
#   list_contains:
#     <list_field>:
#       values: [<value>]
#       mode: any/all

================================================================================
File: activity.yaml
Path: pipelines\chembl\activity.yaml
================================================================================
# configs/pipelines/chembl/activity.yaml
# =============================================================================
# ChEMBL Activity Pipeline Configuration
# =============================================================================
# Minimal config using convention-based path resolution (ADR-029).
# Inherits from _base.yaml with paths/filters auto-computed from provider/entity.
#
# Auto-computed by convention:
#   - source_file: ../../sources/chembl.yaml
#   - dq_config_file: ../../dq/entities/chembl/activity.yaml
#   - filter_config_file: ../../filter/entities/chembl/activity.yaml
#   - input_filter: loaded from filter_config_file
#   - gold_filters: loaded from filter_config_file
#   - sink paths: data/output/{layer}/chembl/activity
#   - sink.silver.primary_key: ["activity_id"]
#   - sink.*.sort_by.columns: ["activity_id"]

pipeline_name: chembl_activity
provider: chembl
entity_type: activity
version: "1.2.0"
description: "Extract biological activity records from ChEMBL API"

primary_keys: ["activity_id"]
silver_table: "chembl_activity"
gold_table: "chembl_activity"

# -----------------------------------------------------------------------------
# DQ Overrides (applied on top of entity DQ config)
# -----------------------------------------------------------------------------
# Only rules that EXTEND or DIFFER from configs/dq/entities/chembl/activity.yaml
# Redundant rules (same as entity config) have been removed per ADR-027.
dq_rules:
  field_validations:
    # Override: Entity has min:0 only, pipeline adds max for extreme outliers
    - field: "standard_value"
      type: "range"
      min: 0
      max: 1000000000
      nullable: true
      error_message: "standard_value must be non-negative and below 1B"
    # Override: Extended enum with additional types (ED50, MIC, CC50)
    - field: "standard_type"
      type: "enum"
      allowed: ["IC50", "Ki", "Kd", "EC50", "AC50", "GI50", "ED50", "MIC", "CC50"]
      nullable: true
    # Override: Extended enum with additional units (ug.mL-1, mg.kg-1)
    - field: "standard_units"
      type: "enum"
      allowed: ["nM", "uM", "mM", "pM", "M", "ug.mL-1", "mg.kg-1"]
      nullable: true

  # Unique cross-field validations (different from entity's value_requires_units)
  cross_field_validations:
    - name: "activity_completeness"
      fields: ["standard_value", "standard_units", "standard_type"]
      condition: "all_present"
      error_message: "Complete activity data requires value, units, and type"

  # Unique conditional validations (entity has binding_requires_target)
  conditional_validations:
    - name: "ic50_range_check"
      condition_field: "standard_type"
      condition_value: "IC50"
      condition_operator: "eq"
      then_validations:
        - field: "standard_value"
          type: "range"
          min: 0.001
          max: 100000
          nullable: false

================================================================================
File: assay.yaml
Path: pipelines\chembl\assay.yaml
================================================================================
# configs/pipelines/chembl/assay.yaml
# =============================================================================
# ChEMBL Assay Pipeline Configuration
# =============================================================================
# Minimal config using convention-based path resolution (ADR-029).
# Inherits from _base.yaml with paths/filters auto-computed from provider/entity.
#
# Auto-computed by convention (see _base.yaml for full list)

pipeline_name: chembl_assay
provider: chembl
entity_type: assay
version: "1.2.0"
description: "Extract bioassay definitions from ChEMBL API"

primary_keys: ["assay_chembl_id"]
silver_table: "chembl_assay"
gold_table: "chembl_assay"

# -----------------------------------------------------------------------------
# DQ Overrides (applied on top of entity DQ config)
# -----------------------------------------------------------------------------
dq_rules:
  field_validations:
    # Override: Entity has nullable:true, pipeline requires non-null
    - field: "assay_type"
      type: "enum"
      allowed: ["B", "F", "A", "T", "P", "U"]
      nullable: false
      error_message: "assay_type must be one of B, F, A, T, P, U"
    # Unique: Not in entity config
    - field: "confidence_score"
      type: "range"
      min: 0
      max: 9
      nullable: true
    # Unique: Not in entity config
    - field: "relationship_type"
      type: "enum"
      allowed: ["D", "H", "M", "N", "S", "U"]
      nullable: true

  cross_field_validations:
    - name: "assay_identifiable"
      fields: ["assay_chembl_id", "description"]
      condition: "all_present"
      error_message: "Assay must have ID and description"

# -----------------------------------------------------------------------------
# Sink Overrides (only non-convention values)
# -----------------------------------------------------------------------------
# Note: partition_by is entity-specific and differs from convention
sink:
  silver:
    partition_by: ["assay_type"]

================================================================================
File: assay_parameters.yaml
Path: pipelines\chembl\assay_parameters.yaml
================================================================================
# configs/pipelines/chembl/assay_parameters.yaml
# Pipeline configuration for ChEMBL AssayParameters entity.
#
# Inherits defaults from ../_base.yaml
# Endpoint: /assay_parameters

pipeline_name: chembl_assay_parameters
provider: chembl
entity_type: assay_parameters
version: "1.2.0"
description: "Extract experimental assay parameters from ChEMBL API"

primary_keys: ["assay_param_id"]
silver_table: "chembl_assay_parameters"
gold_table: "chembl_assay_parameters"

source_file: ../../sources/chembl.yaml

# -----------------------------------------------------------------------------
# Data Quality Configuration (ADR-027)
# -----------------------------------------------------------------------------
# DQ rules are loaded from hierarchical config files:
#   1. configs/dq/_defaults.yaml (global defaults)
#   2. configs/dq/providers/chembl.yaml (provider-specific)
#   3. configs/dq/entities/chembl/assay_parameters.yaml (entity-specific)
dq_config_file: ../../dq/entities/chembl/assay_parameters.yaml

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filters loaded from hierarchical config files via convention (ADR-029):
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/chembl.yaml (provider-specific)
#   3. configs/filter/entities/chembl/assay_parameters.yaml (entity-specific)
# Add inline overrides below only when extending/differing from entity filter config.

# Entity-specific sink overrides
sink:
  bronze:
    path: "data/output/bronze/chembl/assay_parameters"
  silver:
    path: "data/output/silver/chembl/assay_parameters"
    primary_key: ["assay_param_id"]
    partition_by: ["type"]
    sort_by:
      columns: ["assay_param_id"]
      ascending: true
    csv_export:
      path: "data/output/silver/chembl/assay_parameters"
  gold:
    path: "data/output/gold/chembl/assay_parameters"
    sort_by:
      columns: ["assay_param_id"]
      ascending: true
    csv_export:
      path: "data/output/gold/chembl/assay_parameters"


================================================================================
File: cell_line.yaml
Path: pipelines\chembl\cell_line.yaml
================================================================================
# configs/pipelines/chembl/cell_line.yaml
# Pipeline configuration for ChEMBL Cell Line entity.
#
# Inherits defaults from ../_base.yaml

pipeline_name: chembl_cell_line
provider: chembl
entity_type: cell_line
version: "1.2.0"
description: "Extract cell lines from ChEMBL API"

primary_keys: ["cell_chembl_id"]
silver_table: "chembl_cell_line"
gold_table: "chembl_cell_line"

source_file: ../../sources/chembl.yaml

# -----------------------------------------------------------------------------
# Data Quality Configuration (ADR-027)
# -----------------------------------------------------------------------------
# DQ rules are loaded from hierarchical config files:
#   1. configs/dq/_defaults.yaml (global defaults)
#   2. configs/dq/providers/chembl.yaml (provider-specific)
#   3. configs/dq/entities/chembl/cell_line.yaml (entity-specific)
dq_config_file: ../../dq/entities/chembl/cell_line.yaml

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filters loaded from hierarchical config files via convention (ADR-029):
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/chembl.yaml (provider-specific)
#   3. configs/filter/entities/chembl/cell_line.yaml (entity-specific)
# Add inline overrides below only when extending/differing from entity filter config.

# Entity-specific sink overrides
sink:
  bronze:
    path: "data/output/bronze/chembl/cell_line"
  silver:
    path: "data/output/silver/chembl/cell_line"
    primary_key: ["cell_chembl_id"]
    sort_by:
      columns: ["cell_chembl_id"]
      ascending: true
    csv_export:
      path: "data/output/silver/chembl/cell_line"
  gold:
    path: "data/output/gold/chembl/cell_line"
    sort_by:
      columns: ["cell_chembl_id", "cell_name"]
      ascending: true
    csv_export:
      path: "data/output/gold/chembl/cell_line"


================================================================================
File: compound_record.yaml
Path: pipelines\chembl\compound_record.yaml
================================================================================
# configs/pipelines/chembl/compound_record.yaml
# Pipeline configuration for ChEMBL Compound Record entity.
#
# Compound records link molecules to documents. Contains the original
# compound name as it appears in the publication.
#
# Inherits defaults from ../_base.yaml

pipeline_name: chembl_compound_record
provider: chembl
entity_type: compound_record
version: "1.2.0"
description: "Extract compound records from ChEMBL API"

primary_keys: ["record_id"]
silver_table: "chembl_compound_record"
gold_table: "chembl_compound_record"

source_file: ../../sources/chembl.yaml

# -----------------------------------------------------------------------------
# Data Quality Configuration (ADR-027)
# -----------------------------------------------------------------------------
# DQ rules are loaded from hierarchical config files:
#   1. configs/dq/_defaults.yaml (global defaults)
#   2. configs/dq/providers/chembl.yaml (provider-specific)
#   3. configs/dq/entities/chembl/compound_record.yaml (entity-specific)
dq_config_file: ../../dq/entities/chembl/compound_record.yaml

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filters loaded from hierarchical config files via convention (ADR-029):
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/chembl.yaml (provider-specific)
#   3. configs/filter/entities/chembl/compound_record.yaml (entity-specific)
# Add inline overrides below only when extending/differing from entity filter config.

# Entity-specific sink overrides
sink:
  bronze:
    path: "data/output/bronze/chembl/compound_record"
  silver:
    path: "data/output/silver/chembl/compound_record"
    primary_key: ["record_id"]
    sort_by:
      columns: ["record_id"]
      ascending: true
    csv_export:
      path: "data/output/silver/chembl/compound_record"
  gold:
    path: "data/output/gold/chembl/compound_record"
    sort_by:
      columns: ["molecule_chembl_id", "document_chembl_id", "record_id"]
      ascending: true
    csv_export:
      path: "data/output/gold/chembl/compound_record"


================================================================================
File: molecule.yaml
Path: pipelines\chembl\molecule.yaml
================================================================================
# configs/pipelines/chembl/molecule.yaml
# Pipeline configuration for ChEMBL Molecule entity.
#
# Inherits defaults from ../_base.yaml

pipeline_name: chembl_molecule
provider: chembl
entity_type: molecule
version: "1.2.0"
description: "Extract molecules/compounds from ChEMBL API"

primary_keys: ["molecule_chembl_id"]
silver_table: "chembl_molecule"
gold_table: "chembl_molecule"

source_file: ../../sources/chembl.yaml

# -----------------------------------------------------------------------------
# Data Quality Configuration (ADR-027)
# -----------------------------------------------------------------------------
# DQ rules are loaded from hierarchical config files:
#   1. configs/dq/_defaults.yaml (global defaults)
#   2. configs/dq/providers/chembl.yaml (provider-specific)
#   3. configs/dq/entities/chembl/molecule.yaml (entity-specific)
dq_config_file: ../../dq/entities/chembl/molecule.yaml

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filters loaded from hierarchical config files via convention (ADR-029):
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/chembl.yaml (provider-specific)
#   3. configs/filter/entities/chembl/molecule.yaml (entity-specific)
# Add inline overrides below only when extending/differing from entity filter config.

# -----------------------------------------------------------------------------
# Inline DQ Overrides (applied on top of dq_config_file)
# -----------------------------------------------------------------------------
# Only overrides that EXTEND or DIFFER from entity DQ config are kept here.
dq_rules:
  field_validations:
    # Unique: Not in entity config
    - field: "molecule_type"
      type: "enum"
      allowed: ["Small molecule", "Protein", "Antibody", "Oligosaccharide", "Oligonucleotide", "Cell", "Enzyme", "Unknown"]
      nullable: true
    # Unique: Not in entity config
    - field: "structure_type"
      type: "enum"
      allowed: ["MOL", "SEQ", "NONE", "BOTH"]
      nullable: true
    # Override: Entity has min:0 only, pipeline has stricter range 10-10000
    - field: "full_mwt"
      type: "range"
      min: 10
      max: 10000
      nullable: true
      error_message: "Molecular weight must be between 10 and 10000 Da"
    # Unique: SMILES validation not in entity config
    - field: "canonical_smiles"
      type: "custom"
      validator: "smiles_validator"
      nullable: true
    # Override: Entity has min:-15, pipeline uses min:-10 (stricter)
    - field: "alogp"
      type: "range"
      min: -10
      max: 20
      nullable: true
    # Unique: Not in entity config
    - field: "hba"
      type: "range"
      min: 0
      max: 50
      nullable: true
    # Unique: Not in entity config
    - field: "hbd"
      type: "range"
      min: 0
      max: 30
      nullable: true
    # Unique: Not in entity config
    - field: "psa"
      type: "range"
      min: 0
      max: 1000
      nullable: true

  # Unique cross-field validation (not in entity config)
  cross_field_validations:
    - name: "structure_completeness"
      fields: ["canonical_smiles", "standard_inchi", "standard_inchi_key"]
      condition: "any_present"
      error_message: "At least one structure identifier required"

# Entity-specific sink overrides
sink:
  bronze:
    path: "data/output/bronze/chembl/molecule"
  silver:
    path: "data/output/silver/chembl/molecule"
    primary_key: ["molecule_chembl_id"]
    partition_by: ["molecule_type"]
    sort_by:
      columns: ["molecule_chembl_id"]
      ascending: true
    csv_export:
      path: "data/output/silver/chembl/molecule"
  gold:
    path: "data/output/gold/chembl/molecule"
    sort_by:
      columns: ["molecule_chembl_id"]
      ascending: true
    csv_export:
      path: "data/output/gold/chembl/molecule"


================================================================================
File: protein_class.yaml
Path: pipelines\chembl\protein_class.yaml
================================================================================
# configs/pipelines/chembl/protein_class.yaml
# Pipeline configuration for ChEMBL Protein Classification entity.
#
# Reference table (~1,500 records) - full load strategy.
# Hierarchical structure: parent_id -> protein_class_id

pipeline_name: chembl_protein_class
provider: chembl
entity_type: protein_class
version: "1.2.0"
description: "ChEMBL Protein Classification hierarchy (enzyme classes, receptor types, etc.)"

primary_keys: ["protein_class_id"]
silver_table: chembl_protein_class
gold_table: chembl_protein_class

source_file: ../../sources/chembl.yaml

# Full load for reference table
batch_size: 500  # Reference table (~1.5K records), full load
checkpoint_interval: 500

# -----------------------------------------------------------------------------
# Data Quality Configuration (ADR-027)
# -----------------------------------------------------------------------------
# DQ rules are loaded from hierarchical config files:
#   1. configs/dq/_defaults.yaml (global defaults)
#   2. configs/dq/providers/chembl.yaml (provider-specific)
#   3. configs/dq/entities/chembl/protein_class.yaml (entity-specific)
dq_config_file: ../../dq/entities/chembl/protein_class.yaml

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filters loaded from hierarchical config files via convention (ADR-029):
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/chembl.yaml (provider-specific)
#   3. configs/filter/entities/chembl/protein_class.yaml (entity-specific)
# Add inline overrides below only when extending/differing from entity filter config.

# Entity-specific sink overrides
sink:
  bronze:
    path: "data/output/bronze/chembl/protein_class"
  silver:
    path: "data/output/silver/chembl/protein_class"
    primary_key: ["protein_class_id"]
    partition_by: ["class_level"]
    sort_by:
      columns: ["protein_class_id"]
      ascending: true
    csv_export:
      path: "data/output/silver/chembl/protein_class"
  gold:
    path: "data/output/gold/chembl/protein_class"
    sort_by:
      columns: ["class_level", "sort_order", "protein_class_id"]
      ascending: true
    csv_export:
      path: "data/output/gold/chembl/protein_class"


================================================================================
File: publication.yaml
Path: pipelines\chembl\publication.yaml
================================================================================
# configs/pipelines/chembl/publication.yaml
# Pipeline configuration for ChEMBL Publication entity.
#
# Inherits defaults from ../_base.yaml
# Note: entity_type=publication maps to ChEMBL API /document endpoint (ADR-024 naming)

pipeline_name: chembl_publication
provider: chembl
entity_type: publication
version: "2.1.0"
description: "Extract scientific publications from ChEMBL API"

# Loading strategy (ADR-030, ADR-031)
# Publication entities require full scan on each run due to API offset instability.
# Deduplication is handled on Silver layer via content_hash.
# - full_scan_only: Explicit strategy disabling checkpoint resume
# - watermark_based: Placeholder for future incremental loading (not implemented)
force_full_scan: true
loading_strategy: full_scan_only

primary_keys: ["document_chembl_id"]
silver_table: "chembl_publication"
gold_table: "chembl_publication"

source_file: ../../sources/chembl.yaml

# -----------------------------------------------------------------------------
# Data Quality Configuration (ADR-027)
# -----------------------------------------------------------------------------
# DQ rules are loaded from hierarchical config files:
#   1. configs/dq/_defaults.yaml (global defaults)
#   2. configs/dq/providers/chembl.yaml (provider-specific)
#   3. configs/dq/entities/chembl/publication.yaml (entity-specific)
dq_config_file: ../../dq/entities/chembl/publication.yaml

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filters loaded from hierarchical config files via convention (ADR-029):
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/chembl.yaml (provider-specific)
#   3. configs/filter/entities/chembl/publication.yaml (entity-specific)
# Add inline overrides below only when extending/differing from entity filter config.
filter_config_file: ../../filter/entities/chembl/publication.yaml

# Entity-specific sink overrides
# Note: dq_report.enabled inherited from _base.yaml for all layers
sink:
  bronze:
    path: "data/output/bronze/chembl/publication"
    flat_structure: true  # Files written directly under path/{date}/, without provider/entity subdirs
  silver:
    path: "data/output/silver/chembl/publication"
    primary_key: ["document_chembl_id"]
    partition_by: ["doc_type"]
    sort_by:
      columns: ["document_chembl_id"]
      ascending: true
    csv_export:
      path: "data/output/silver/chembl/publication"
    flat_structure: true  # Delta directly in path, files named {table}_*.ext
  gold:
    path: "data/output/gold/chembl/publication"
    sort_by:
      columns: ["document_chembl_id"]
      ascending: true
    csv_export:
      path: "data/output/gold/chembl/publication"
    flat_structure: true  # Delta directly in path, files named {table}_*.ext


================================================================================
File: publication_similarity.yaml
Path: pipelines\chembl\publication_similarity.yaml
================================================================================
# configs/pipelines/chembl/publication_similarity.yaml
# Pipeline configuration for ChEMBL Publication Similarity entity.
#
# Inherits defaults from ../_base.yaml
# Note: entity_type=publication_similarity maps to ChEMBL API /document_similarity endpoint (ADR-024)

pipeline_name: chembl_publication_similarity
provider: chembl
entity_type: publication_similarity
version: "2.1.0"
description: "Extract publication similarity data (Tanimoto coefficients) from ChEMBL API"

# Loading strategy (ADR-030, ADR-031)
# Publication entities require full scan on each run due to API offset instability.
# Deduplication is handled on Silver layer via content_hash.
force_full_scan: true
loading_strategy: full_scan_only

primary_keys: ["sim_id"]
silver_table: "chembl_publication_similarity"
gold_table: "chembl_publication_similarity"

source_file: ../../sources/chembl.yaml

# -----------------------------------------------------------------------------
# Data Quality Configuration (ADR-027)
# -----------------------------------------------------------------------------
# DQ rules are loaded from hierarchical config files:
#   1. configs/dq/_defaults.yaml (global defaults)
#   2. configs/dq/providers/chembl.yaml (provider-specific)
#   3. configs/dq/entities/chembl/publication_similarity.yaml (entity-specific)
dq_config_file: ../../dq/entities/chembl/publication_similarity.yaml

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filters loaded from hierarchical config files via convention (ADR-029):
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/chembl.yaml (provider-specific)
#   3. configs/filter/entities/chembl/publication_similarity.yaml (entity-specific)
# Add inline overrides below only when extending/differing from entity filter config.
filter_config_file: ../../filter/entities/chembl/publication_similarity.yaml

# Entity-specific sink overrides
sink:
  bronze:
    path: "data/output/bronze/chembl/publication_similarity"
  silver:
    path: "data/output/silver/chembl/publication_similarity"
    primary_key: ["sim_id"]
    partition_by: []  # No good partition key
    sort_by:
      columns: ["sim_id"]
      ascending: true
    csv_export:
      path: "data/output/silver/chembl/publication_similarity"
  gold:
    path: "data/output/gold/chembl/publication_similarity"
    sort_by:
      columns: ["sim_id"]
      ascending: true
    csv_export:
      path: "data/output/gold/chembl/publication_similarity"


================================================================================
File: publication_term.yaml
Path: pipelines\chembl\publication_term.yaml
================================================================================
# configs/pipelines/chembl/publication_term.yaml
# Pipeline configuration for ChEMBL Publication Term entity.
#
# Derived entity: Extracts and flattens terms from Publication records.
# Inherits defaults from ../_base.yaml
# Note: entity_type=publication_term maps to ChEMBL API /document endpoint (derived entity, ADR-024)

pipeline_name: chembl_publication_term
provider: chembl
entity_type: publication_term
version: "2.1.0"
description: "Extract publication terms (MeSH, keywords) from ChEMBL Publication records"

# Loading strategy (ADR-030, ADR-031)
# Publication entities require full scan on each run due to API offset instability.
# Deduplication is handled on Silver layer via content_hash.
force_full_scan: true
loading_strategy: full_scan_only

# Composite primary key (document_chembl_id + term_type + term)
# entity_id is generated as SHA256 hash of composite key
primary_keys: ["entity_id"]
silver_table: "chembl_publication_term"
gold_table: "chembl_publication_term"

source_file: ../../sources/chembl.yaml

# -----------------------------------------------------------------------------
# Data Quality Configuration (ADR-027)
# -----------------------------------------------------------------------------
# DQ rules are loaded from hierarchical config files:
#   1. configs/dq/_defaults.yaml (global defaults)
#   2. configs/dq/providers/chembl.yaml (provider-specific)
#   3. configs/dq/entities/chembl/publication_term.yaml (entity-specific)
dq_config_file: ../../dq/entities/chembl/publication_term.yaml

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filters loaded from hierarchical config files via convention (ADR-029):
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/chembl.yaml (provider-specific)
#   3. configs/filter/entities/chembl/publication_term.yaml (entity-specific)
# Add inline overrides below only when extending/differing from entity filter config.
filter_config_file: ../../filter/entities/chembl/publication_term.yaml

# Entity-specific sink overrides
sink:
  bronze:
    path: "data/output/bronze/chembl/publication_term"
  silver:
    path: "data/output/silver/chembl/publication_term"
    primary_key: ["entity_id"]
    partition_by: ["term_type"]
    sort_by:
      columns: ["entity_id"]
      ascending: true
    csv_export:
      path: "data/output/silver/chembl/publication_term"
  gold:
    path: "data/output/gold/chembl/publication_term"
    sort_by:
      columns: ["entity_id"]
      ascending: true
    csv_export:
      path: "data/output/gold/chembl/publication_term"


================================================================================
File: target.yaml
Path: pipelines\chembl\target.yaml
================================================================================
# configs/pipelines/chembl/target.yaml
# Pipeline configuration for ChEMBL Target entity.
#
# Inherits defaults from ../_base.yaml

pipeline_name: chembl_target
provider: chembl
entity_type: target
version: "1.2.0"
description: "Extract biological targets from ChEMBL API"

primary_keys: ["target_chembl_id"]
silver_table: "chembl_target"
gold_table: "chembl_target"

source_file: ../../sources/chembl.yaml

# -----------------------------------------------------------------------------
# Data Quality Configuration (ADR-027)
# -----------------------------------------------------------------------------
# DQ rules are loaded from hierarchical config files:
#   1. configs/dq/_defaults.yaml (global defaults)
#   2. configs/dq/providers/chembl.yaml (provider-specific)
#   3. configs/dq/entities/chembl/target.yaml (entity-specific)
dq_config_file: ../../dq/entities/chembl/target.yaml

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filters loaded from hierarchical config files via convention (ADR-029):
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/chembl.yaml (provider-specific)
#   3. configs/filter/entities/chembl/target.yaml (entity-specific)
# Add inline overrides below only when extending/differing from entity filter config.

# -----------------------------------------------------------------------------
# Inline DQ Overrides (applied on top of dq_config_file)
# -----------------------------------------------------------------------------
# Only overrides that EXTEND or DIFFER from entity DQ config are kept here.
dq_rules:
  field_validations:
    # Override: Extended enum with more target types than entity config (17 vs 8)
    - field: "target_type"
      type: "enum"
      allowed: ["SINGLE PROTEIN", "PROTEIN COMPLEX", "PROTEIN FAMILY", "SELECTIVITY GROUP", "ORGANISM", "TISSUE", "CELL-LINE", "SUBCELLULAR", "UNKNOWN", "CHIMERIC PROTEIN", "PROTEIN-PROTEIN INTERACTION", "NUCLEIC-ACID", "METAL", "LIPID", "MACROMOLECULE", "PHENOTYPE", "ADMET"]
      nullable: true
    # Unique: Not in entity config
    - field: "organism"
      type: "pattern"
      pattern: "^[A-Z][a-z]+ [a-z]+.*$"
      nullable: true
      error_message: "organism should be in binomial nomenclature"
    # Unique: Not in entity config
    - field: "tax_id"
      type: "range"
      min: 1
      max: 10000000
      nullable: true

  # Unique cross-field validation (not in entity config)
  cross_field_validations:
    - name: "target_identifiable"
      fields: ["target_chembl_id", "pref_name"]
      condition: "all_present"
      error_message: "Target must have ID and preferred name"

# Entity-specific sink overrides
sink:
  bronze:
    path: "data/output/bronze/chembl/target"
  silver:
    path: "data/output/silver/chembl/target"
    primary_key: ["target_chembl_id"]
    partition_by: ["target_type"]
    sort_by:
      columns: ["target_chembl_id"]
      ascending: true
    csv_export:
      path: "data/output/silver/chembl/target"
  gold:
    path: "data/output/gold/chembl/target"
    sort_by:
      columns: ["target_chembl_id", "pref_name"]
      ascending: true
    csv_export:
      path: "data/output/gold/chembl/target"


================================================================================
File: target_component.yaml
Path: pipelines\chembl\target_component.yaml
================================================================================
# configs/pipelines/chembl/target_component.yaml
# Pipeline configuration for ChEMBL Target Component entity.
#
# Inherits defaults from ../_base.yaml

pipeline_name: chembl_target_component
provider: chembl
entity_type: target_component
version: "1.2.0"
description: "ChEMBL Target Components (protein sequences, etc.)"

primary_keys: ["component_id"]
silver_table: chembl_target_component
gold_table: chembl_target_component

source_file: ../../sources/chembl.yaml

# -----------------------------------------------------------------------------
# Data Quality Configuration (ADR-027)
# -----------------------------------------------------------------------------
# DQ rules are loaded from hierarchical config files:
#   1. configs/dq/_defaults.yaml (global defaults)
#   2. configs/dq/providers/chembl.yaml (provider-specific)
#   3. configs/dq/entities/chembl/target_component.yaml (entity-specific)
dq_config_file: ../../dq/entities/chembl/target_component.yaml

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filters loaded from hierarchical config files via convention (ADR-029):
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/chembl.yaml (provider-specific)
#   3. configs/filter/entities/chembl/target_component.yaml (entity-specific)
# Add inline overrides below only when extending/differing from entity filter config.

# Entity-specific sink overrides
sink:
  bronze:
    path: "data/output/bronze/chembl/target_component"
  silver:
    path: "data/output/silver/chembl/target_component"
    primary_key: ["component_id"]
    partition_by: ["organism"]
    sort_by:
      columns: ["component_id"]
      ascending: true
    csv_export:
      path: "data/output/silver/chembl/target_component"
  gold:
    path: "data/output/gold/chembl/target_component"
    sort_by:
      columns: ["component_id"]
      ascending: true
    csv_export:
      path: "data/output/gold/chembl/target_component"


================================================================================
File: publication.yaml
Path: pipelines\composite\publication.yaml
================================================================================
# configs/pipelines/composite/publication.yaml
# =============================================================================
# Composite Publication Pipeline Configuration
# =============================================================================
#
# Combines publication data from multiple sources:
# - Seed: ChEMBL publications
# - Enrichers: CrossRef (citations), OpenAlex (concepts), PubMed (MeSH),
#              SemanticScholar (embeddings)
#
# NOTE: chembl_publication_term was removed because ChEMBL API no longer
# provides mesh_terms/keywords fields in /document endpoint, and the
# /document_term endpoint has been deprecated (returns 404).
#
# Version: 1.0.0
# Reference: ADR-026 Composite Pipeline Pattern
# Last Updated: 2026-01-15
#
# =============================================================================

# -----------------------------------------------------------------------------
# Composite Pipeline Configuration
# -----------------------------------------------------------------------------
composite:
  name: composite_publication
  version: "1.0.0"

  # ---------------------------------------------------------------------------
  # Seed Pipeline Configuration
  # ---------------------------------------------------------------------------
  # The seed pipeline extracts primary entities from ChEMBL.
  # Its output provides join keys (doi, pmid) for enrichment.
  seed:
    pipeline: chembl_publication
    output_keys:
      - document_chembl_id  # ChEMBL document ID (primary key)
      - doi                 # Digital Object Identifier
      - pmid                # PubMed ID
      - title               # Publication title (for fallback joins)
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
  # - Pipelines with force_full_scan that don't work with enricher filtering
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
    - pipeline: crossref_publication
      join_keys:
        - doi            # Primary join key
        - title
      required: false    # Optional - seed may not have DOIs
      filter_condition: "doi IS NOT NULL"
      timeout_seconds: 900
      silver_table: silver/crossref/publication

    # OpenAlex: Academic concepts and institutions
    # OPTIONAL: Failure logged, composite continues
    - pipeline: openalex_publication
      join_keys:
        - doi            # Primary key
        - title          # Fallback key if doi not found
      required: false    # Optional - needs doi or pmid
      filter_condition: "doi IS NOT NULL OR pmid IS NOT NULL"
      timeout_seconds: 600
      silver_table: silver/openalex/publication

    # PubMed: MeSH terms and medical metadata
    # OPTIONAL: Only processes records with pmid
    - pipeline: pubmed_publication
      join_keys:
        - pmid           # PubMed-specific identifier
        - doi
      required: false    # Optional - only for records with pmid
      filter_condition: "pmid IS NOT NULL"
      timeout_seconds: 600
      silver_table: silver/pubmed/publication

    # Semantic Scholar: AI/ML embeddings and TLDR
    # OPTIONAL: Higher rate limits, ok to skip
    - pipeline: semanticscholar_publication
      join_keys:
        - doi
        - title
      required: false    # Optional - high rate limits, ok to skip
      filter_condition: "doi IS NOT NULL OR pmid IS NOT NULL"
      timeout_seconds: 1200
      fallback_strategy: skip  # Skip on failure (high rate limits)
      silver_table: silver/semanticscholar/publication

  # ---------------------------------------------------------------------------
  # Merge Configuration
  # ---------------------------------------------------------------------------
  # Defines how enriched data is combined into the final output.
  merge:
    # Join strategy: left_outer preserves all seed records
    strategy: left_outer

    # Conflict resolution: seed values take priority
    conflict_resolution: seed_priority

    # Field-level priority overrides (when using explicit_rules)
    # Maps field name to ordered list of source preferences
    field_priorities:
      title:
        - chembl         # ChEMBL title is authoritative
        - crossref
        - openalex
      abstract:
        - pubmed         # PubMed has best abstracts
        - openalex
        - chembl
      citations_count:
        - crossref       # CrossRef is citation authority
        - openalex
      mesh_terms:
        - pubmed         # PubMed MeSH is authoritative
      concepts:
        - openalex       # OpenAlex concepts are unique
      tldr:
        - semanticscholar  # S2-only field

    # -------------------------------------------------------------------------
    # Column Ordering by Semantic Groups
    # -------------------------------------------------------------------------
    # Defines the order of columns in the merged output.
    # Columns are grouped semantically, with seed columns first within each group.
    column_groups:
      # 1. System fields (always first)
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

      # 2. Lineage metadata (added by MergeService)
      - name: lineage
        pattern: "^_composite_|^_source_providers|^_enrichment_|^_lineage_"

      # 3. Primary identifiers
      - name: identifiers
        fields:
          - document_chembl_id
          - doi
          - pmid
        provider_order: [chembl, openalex, pubmed, semanticscholar]

      # 4. PMC IDs (separate group - not in seed)
      - name: pmc_identifiers
        fields:
          - pmc_id
        provider_order: [openalex, pubmed, semanticscholar]

      # 5. Title group
      - name: title
        fields:
          - title
          - vernacular_title
        provider_order: [chembl, crossref, openalex, pubmed, semanticscholar]

      # 6. Abstract group
      - name: abstract
        fields:
          - abstract
          - abstract_structured
          - tldr
        provider_order: [chembl, pubmed, crossref, openalex, semanticscholar]

      # 7. Authors group
      - name: authors
        fields:
          - authors
          - author_count
        provider_order: [chembl, crossref, openalex, pubmed, semanticscholar]

      # 8. Journal group
      - name: journal
        fields:
          - journal
          - journal_full_title
          - journal_title
          - journal_abbrev
          - journal_iso_abbrev
          - short_container_title
          - venue
        provider_order: [chembl, crossref, openalex, pubmed, semanticscholar]

      # 9. Year group
      - name: year
        fields:
          - year
          - publication_year
        provider_order: [chembl, crossref, openalex, pubmed, semanticscholar]

      # 10. Publication dates
      - name: dates
        fields:
          - publication_date
          - published
          - published_print
          - published_online
          - pub_date
          - pub_month
          - pub_day
          - epub_date
          - accepted_date
          - received_date
          - revised_date
          - date_completed
          - date_revised
        provider_order: [crossref, openalex, pubmed, semanticscholar]

      # 11. Volume/Issue/Pages
      - name: pagination
        fields:
          - volume
          - issue
          - first_page
          - last_page
          - pages
          - medline_pgn
        provider_order: [chembl, crossref, pubmed, semanticscholar]

      # 12. Citation metrics
      - name: citations
        fields:
          - citation_count
          - reference_count
        provider_order: [crossref, openalex, semanticscholar, pubmed]

      # 13. ISSN group
      - name: issn
        fields:
          - issn
          - issn_print
          - issn_electronic
          - journal_issn_type
        provider_order: [crossref, openalex, pubmed]

      # 14. Open Access
      - name: open_access
        fields:
          - is_oa
          - oa_status
          - open_access_url
        provider_order: [openalex, semanticscholar]

      # 15. Document type
      - name: doc_type
        fields:
          - doc_type
        provider_order: [chembl, crossref, openalex]

      # 16. Language
      - name: language
        fields:
          - language
        provider_order: [crossref, openalex, pubmed]

      # 17. Publisher
      - name: publisher
        fields:
          - publisher
        provider_order: [crossref, openalex]

      # 18. Subject/Classification
      - name: subjects
        fields:
          - subjects
          - concepts
          - fields_of_study
          - mesh_terms
          - mesh_heading_count
          - keywords
          - keyword_count
          - publication_types
          - publication_type_list
        provider_order: [crossref, openalex, pubmed, semanticscholar]

      # 19. Provider-specific IDs
      - name: provider_ids
        fields:
          - openalex_id
          - paper_id
          - corpus_id
          - arxiv_id
          - src_id
          - chembl_release
          - creation_date
          - nlm_unique_id
        provider_order: [chembl, openalex, semanticscholar, pubmed]

      # 20. Miscellaneous fields
      - name: misc
        fields:
          - license_url
          - alternative_id
          - content_domain_domains
          - content_domain_crossmark_restriction
          - country
          - citation_subset
          - publication_status
          - grant_count
          - chemical_count
        provider_order: [crossref, pubmed]

      # 21. DQ fields (always last)
      # Note: _source is a system field in the 'system' group
      - name: dq
        pattern: "^_dq_"

    # Output paths
    output:
      silver: data/output/silver/composite/publication
      gold: data/output/gold/composite/publication

  # ---------------------------------------------------------------------------
  # Data Quality Configuration
  # ---------------------------------------------------------------------------
  dq_rules:
    # Composite-level thresholds (applied to merge result)
    soft_fail_threshold: 0.10  # 10% errors = warning
    hard_fail_threshold: 0.30  # 30% errors = failure

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

    # Required fields in final Gold output
    required_fields:
      - document_chembl_id
      - title

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
# Filter rules are loaded from hierarchical config files:
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/composite.yaml (provider-specific)
#   3. configs/filter/entities/composite/publication.yaml (entity-specific)
filter_config_file: ../../filter/entities/composite/publication.yaml

# -----------------------------------------------------------------------------
# Maintenance Configuration
# -----------------------------------------------------------------------------

================================================================================
File: publication.yaml
Path: pipelines\crossref\publication.yaml
================================================================================
# configs/pipelines/crossref/publication.yaml
# Pipeline for enriching publication records with CrossRef metadata.
# Resolves DOIs from Bronze (PubMed/ChEMBL docs) to enrich with citations.
#
# Inherits defaults from ../_base.yaml

pipeline_name: crossref_publication
provider: crossref
entity_type: work
version: "1.2.0"
description: "Enrich publication records with CrossRef metadata via DOI resolution"

# Loading strategy (ADR-030, ADR-031)
# Publication entities require full scan on each run due to API offset instability.
# Deduplication is handled on Silver layer via content_hash.
force_full_scan: true
loading_strategy: full_scan_only

primary_keys: ["doi"]
silver_table: "crossref_publication"
gold_table: "crossref_publication"

source_file: ../../sources/crossref.yaml

# -----------------------------------------------------------------------------
# Data Quality Configuration (ADR-027)
# -----------------------------------------------------------------------------
# DQ rules are loaded from hierarchical config files:
#   1. configs/dq/_defaults.yaml (global defaults)
#   2. configs/dq/providers/crossref.yaml (provider-specific)
#   3. configs/dq/entities/crossref/publication.yaml (entity-specific)
dq_config_file: ../../dq/entities/crossref/publication.yaml

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filters loaded from hierarchical config files via convention (ADR-029):
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/crossref.yaml (provider-specific)
#   3. configs/filter/entities/crossref/publication.yaml (entity-specific)
# Add inline overrides below only when extending/differing from entity filter config.

# Entity-specific sink overrides
# Note: flat_structure=true because paths already include provider/entity
sink:
  bronze:
    path: "data/output/bronze/crossref/publication"
    flat_structure: true  # Path already includes provider/entity
  silver:
    path: "data/output/silver/crossref/publication"
    primary_key: ["doi"]
    sort_by:
      columns: ["doi"]
      ascending: true
    csv_export:
      path: "data/output/silver/crossref/publication"
    flat_structure: true
  gold:
    path: "data/output/gold/crossref/publication"
    sort_by:
      columns: ["doi"]
      ascending: true
    csv_export:
      path: "data/output/gold/crossref/publication"
    flat_structure: true


================================================================================
File: publication.yaml
Path: pipelines\openalex\publication.yaml
================================================================================
# configs/pipelines/openalex/publication.yaml
# Pipeline for batch DOI resolution via OpenAlex with title fallback.
#
# Reads DOIs from CSV input file, resolves metadata from OpenAlex Works API.
# Falls back to title search when DOI resolution fails.
#
# Inherits defaults from ../_base.yaml

pipeline_name: openalex_publication
provider: openalex
entity_type: publication
version: "1.2.0"
description: "Batch DOI resolution via OpenAlex with title fallback"

# Loading strategy (ADR-030, ADR-031)
# Publication entities require full scan on each run due to API offset instability.
# Deduplication is handled on Silver layer via content_hash.
force_full_scan: true
loading_strategy: full_scan_only

primary_keys: ["openalex_id"]
silver_table: "openalex_publication"
gold_table: "openalex_publication"

source_file: ../../sources/openalex.yaml

# Pipeline-specific source configuration
source:
  email: "${BIOETL_OPENALEX_EMAIL}"  # Required for polite pool
  batch_size: 50  # Polite pool API - conservative batch size

# -----------------------------------------------------------------------------
# Data Quality Configuration (ADR-027)
# -----------------------------------------------------------------------------
# DQ rules are loaded from hierarchical config files:
#   1. configs/dq/_defaults.yaml (global defaults)
#   2. configs/dq/providers/openalex.yaml (provider-specific)
#   3. configs/dq/entities/openalex/publication.yaml (entity-specific)
dq_config_file: ../../dq/entities/openalex/publication.yaml

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filters loaded from hierarchical config files via convention (ADR-029):
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/openalex.yaml (provider-specific)
#   3. configs/filter/entities/openalex/publication.yaml (entity-specific)
# Add inline overrides below only when extending/differing from entity filter config.

# Entity-specific sink overrides
# Note: flat_structure=true means Delta data is written directly to path
# without table_name subdirectory, matching chembl_publication pattern
sink:
  bronze:
    path: "data/output/bronze/openalex/publication"
    flat_structure: true  # Path already includes provider/entity
  silver:
    path: "data/output/silver/openalex/publication"
    primary_key: ["openalex_id"]
    partition_by: ["year"]
    sort_by:
      columns: ["openalex_id"]
      ascending: true
    csv_export:
      path: "data/output/silver/openalex/publication"
    flat_structure: true
  gold:
    path: "data/output/gold/openalex/publication"
    sort_by:
      columns: ["openalex_id"]
      ascending: true
    csv_export:
      path: "data/output/gold/openalex/publication"
    flat_structure: true


================================================================================
File: compound.yaml
Path: pipelines\pubchem\compound.yaml
================================================================================
# configs/pipelines/pubchem/compound.yaml
# Pipeline configuration for PubChem Compound entity.
#
# Inherits defaults from ../_base.yaml

pipeline_name: pubchem_compound
provider: pubchem
entity_type: compound
version: "1.2.0"
description: "Pipeline for ingesting PubChem compounds"

primary_keys: ["cid"]
silver_table: "pubchem_compound"
gold_table: "pubchem_compound"

source_file: ../../sources/pubchem.yaml

# -----------------------------------------------------------------------------
# Data Quality Configuration (ADR-027)
# -----------------------------------------------------------------------------
# DQ rules are loaded from hierarchical config files:
#   1. configs/dq/_defaults.yaml (global defaults)
#   2. configs/dq/providers/pubchem.yaml (provider-specific)
#   3. configs/dq/entities/pubchem/compound.yaml (entity-specific)
dq_config_file: ../../dq/entities/pubchem/compound.yaml

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filters loaded from hierarchical config files via convention (ADR-029):
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/pubchem.yaml (provider-specific)
#   3. configs/filter/entities/pubchem/compound.yaml (entity-specific)
# Add inline overrides below only when extending/differing from entity filter config.

# -----------------------------------------------------------------------------
# Inline DQ Overrides (applied on top of dq_config_file)
# -----------------------------------------------------------------------------
# Only overrides that EXTEND or DIFFER from entity DQ config are kept here.
dq_rules:
  field_validations:
    # Unique: Not in entity config
    - field: "molecular_formula"
      type: "pattern"
      pattern: "^[A-Z][A-Za-z0-9]*$"
      nullable: true
      error_message: "Molecular formula must start with uppercase letter"
    # Override: Entity has min:0 only, pipeline has stricter range 10-10000
    - field: "molecular_weight"
      type: "range"
      min: 10
      max: 10000
      nullable: true
    # Unique: SMILES validation not in entity config
    - field: "canonical_smiles"
      type: "custom"
      validator: "smiles_validator"
      nullable: true
    # Unique: SMILES validation not in entity config
    - field: "isomeric_smiles"
      type: "custom"
      validator: "smiles_validator"
      nullable: true
    # Unique: Not in entity config
    - field: "xlogp"
      type: "range"
      min: -20
      max: 30
      nullable: true
    # Unique: Not in entity config
    - field: "tpsa"
      type: "range"
      min: 0
      max: 1000
      nullable: true
    # Unique: Not in entity config
    - field: "h_bond_donor_count"
      type: "range"
      min: 0
      max: 50
      nullable: true
    # Unique: Not in entity config
    - field: "h_bond_acceptor_count"
      type: "range"
      min: 0
      max: 50
      nullable: true

  # Unique cross-field validation (not in entity config)
  cross_field_validations:
    - name: "structure_present"
      fields: ["canonical_smiles", "inchi", "inchikey"]
      condition: "any_present"
      error_message: "At least one structure identifier required"

# Entity-specific sink overrides
sink:
  bronze:
    path: "data/output/bronze/pubchem/compound"
  silver:
    path: "data/output/silver/pubchem/compound"
    primary_key: ["cid"]
    partition_by: ["batch_date"]
    sort_by:
      columns: ["cid"]
      ascending: true
    csv_export:
      path: "data/output/silver/pubchem/compound"
  gold:
    path: "data/output/gold/pubchem/compound"
    sort_by:
      columns: ["cid"]
      ascending: true
    csv_export:
      path: "data/output/gold/pubchem/compound"


================================================================================
File: publication.yaml
Path: pipelines\pubmed\publication.yaml
================================================================================
# configs/pipelines/pubmed/publication.yaml
# =============================================================================
# PubMed Publication Pipeline Configuration
# =============================================================================
# Minimal config using convention-based path resolution (ADR-029).
# Inherits from _base.yaml with most paths/filters auto-computed.

pipeline_name: pubmed_publication
provider: pubmed
entity_type: publication
version: "1.2.0"
description: "Extract publication metadata from PubMed via Entrez API"

# Loading strategy (ADR-030, ADR-031)
# Publication entities require full scan on each run due to API offset instability.
# Deduplication is handled on Silver layer via content_hash.
force_full_scan: true
loading_strategy: full_scan_only

primary_keys: ["pmid"]
silver_table: "pubmed_publication"
gold_table: "pubmed_publication"

# -----------------------------------------------------------------------------
# Source Configuration (provider-specific API settings)
# -----------------------------------------------------------------------------
source:
  search_term: "bioinformatics[Title/Abstract] AND drug discovery[Title/Abstract]"
  email: "${BIOETL_NCBI_EMAIL}"
  api_key: "${BIOETL_NCBI_API_KEY}"

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
filter_config_file: ../../filter/entities/pubmed/publication.yaml

# -----------------------------------------------------------------------------
# Sink Overrides
# -----------------------------------------------------------------------------
# Note: flat_structure=true means Delta data is written directly to path
# without table_name subdirectory, matching chembl_publication pattern
sink:
  bronze:
    path: "data/output/bronze/pubmed/publication"
    flat_structure: true  # Path already includes provider/entity
  silver:
    path: "data/output/silver/pubmed/publication"
    partition_by: ["pub_year"]
    csv_export:
      path: "data/output/silver/pubmed/publication"
    flat_structure: true
  gold:
    path: "data/output/gold/pubmed/publication"
    csv_export:
      path: "data/output/gold/pubmed/publication"
    flat_structure: true

================================================================================
File: publication.yaml
Path: pipelines\semanticscholar\publication.yaml
================================================================================
# configs/pipelines/semanticscholar/publication.yaml
# Pipeline for batch DOI resolution via Semantic Scholar with title fallback.
#
# Resolves DOIs from input CSV to enrich with publication metadata.
# Falls back to title search when DOI is not found or empty.
#
# Inherits defaults from ../_base.yaml

pipeline_name: semanticscholar_publication
provider: semanticscholar
entity_type: publication
version: "1.2.0"
description: "Batch DOI resolution via Semantic Scholar with title fallback"

# Loading strategy (ADR-030, ADR-031)
# Publication entities require full scan on each run due to API offset instability.
# Deduplication is handled on Silver layer via content_hash.
force_full_scan: true
loading_strategy: full_scan_only

primary_keys: ["paper_id"]
silver_table: "semanticscholar_publication"
gold_table: "semanticscholar_publication"

source_file: ../../sources/semanticscholar.yaml

# -----------------------------------------------------------------------------
# Data Quality Configuration (ADR-027)
# -----------------------------------------------------------------------------
# DQ rules are loaded from hierarchical config files:
#   1. configs/dq/_defaults.yaml (global defaults)
#   2. configs/dq/providers/semanticscholar.yaml (provider-specific)
#   3. configs/dq/entities/semanticscholar/publication.yaml (entity-specific)
dq_config_file: ../../dq/entities/semanticscholar/publication.yaml

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filters loaded from hierarchical config files via convention (ADR-029):
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/semanticscholar.yaml (provider-specific)
#   3. configs/filter/entities/semanticscholar/publication.yaml (entity-specific)
# Add inline overrides below only when extending/differing from entity filter config.

# Entity-specific sink configuration
# Note: flat_structure=true means Delta data is written directly to path
# without table_name subdirectory, matching chembl_publication pattern
sink:
  bronze:
    path: "data/output/bronze/semanticscholar/publication"
    flat_structure: true  # Path already includes provider/entity
  silver:
    path: "data/output/silver/semanticscholar/publication"
    primary_key: ["paper_id"]
    partition_by: ["year"]
    sort_by:
      columns: ["paper_id"]
      ascending: true
    csv_export:
      path: "data/output/silver/semanticscholar/publication"
    flat_structure: true
  gold:
    path: "data/output/gold/semanticscholar/publication"
    sort_by:
      columns: ["paper_id"]
      ascending: true
    csv_export:
      path: "data/output/gold/semanticscholar/publication"
    flat_structure: true


================================================================================
File: idmapping.yaml
Path: pipelines\uniprot\idmapping.yaml
================================================================================
# configs/pipelines/uniprot/idmapping.yaml
# Pipeline configuration for UniProt ID Mapping (ChEMBL → UniProt).
#
# Maps ChEMBL target IDs to UniProt accessions using UniProt ID Mapping REST API.
# Input: CSV file with target_chembl_id column
# Output: Silver/Gold records with mapping results (null for not_found)
#
# Inherits defaults from ../_base.yaml

pipeline_name: uniprot_idmapping
provider: uniprot
entity_type: idmapping
version: "1.1.0"
description: "Maps ChEMBL target IDs to UniProt accessions via UniProt ID Mapping API"

primary_keys: ["target_chembl_id"]
silver_table: "uniprot_idmapping"
gold_table: "uniprot_idmapping"

# Reference to provider source config (common UniProt settings)
source_file: ../../sources/uniprot.yaml

# Entity-specific source overrides for ID Mapping
source:
  type: file
  load_strategy: full
  # Input CSV file containing ChEMBL target IDs
  input_path: data/input/target.csv

  # ID Mapping API configuration
  api:
    base_url: https://rest.uniprot.org
    # Database names as recognized by UniProt ID Mapping API
    from_db: ChEMBL
    to_db: UniProtKB

# -----------------------------------------------------------------------------
# Data Quality Configuration (ADR-027)
# -----------------------------------------------------------------------------
# DQ config is loaded from hierarchical files:
#   1. configs/dq/_defaults.yaml (global defaults)
#   2. configs/dq/providers/uniprot.yaml (provider-specific)
#   3. configs/dq/entities/uniprot/idmapping.yaml (entity-specific)
#
# Entity-specific config contains:
#   - Elevated thresholds: soft_fail=0.30, hard_fail=0.80 (ID mapping may have many not_found)
#   - Field validations: target_chembl_id, mapping_status, uniprot_accession
#   - Conditional validations: found_has_accession
dq_config_file: ../../dq/entities/uniprot/idmapping.yaml

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filters loaded from hierarchical config files via convention (ADR-029):
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/uniprot.yaml (provider-specific)
#   3. configs/filter/entities/uniprot/idmapping.yaml (entity-specific)
# Add inline overrides below only when extending/differing from entity filter config.

# Sink configuration
sink:
  bronze:
    # ID Mapping doesn't write Bronze (data comes from API, not raw files)
    # NOTE: enabled: false is not yet implemented in code, so Bronze is still written
    path: "data/output/bronze/uniprot/idmapping"
  silver:
    path: "data/output/silver/uniprot/idmapping"
    primary_key: ["target_chembl_id"]
    partition_by: []  # No partitioning - small dataset
    sort_by:
      columns: ["target_chembl_id"]
      ascending: true
    csv_export:
      path: "data/output/silver/uniprot/idmapping"
  gold:
    path: "data/output/gold/uniprot/idmapping"
    sort_by:
      columns: ["target_chembl_id"]
      ascending: true
    csv_export:
      path: "data/output/gold/uniprot/idmapping"


================================================================================
File: protein.yaml
Path: pipelines\uniprot\protein.yaml
================================================================================
# configs/pipelines/uniprot/protein.yaml
# =============================================================================
# UniProt Protein Pipeline Configuration
# =============================================================================
# Minimal config using convention-based path resolution (ADR-029).
# Inherits from _base.yaml with paths/filters auto-computed from the provider/entity.
#
# Auto-computed by convention (see _base.yaml for a full list)

pipeline_name: uniprot_protein
provider: uniprot
entity_type: protein
version: "1.2.0"
description: "Pipeline for ingesting UniProt proteins"

primary_keys: ["accession"]
silver_table: "uniprot_protein"
gold_table: "uniprot_protein"

# -----------------------------------------------------------------------------
# Sink Overrides (only non-convention values)
# -----------------------------------------------------------------------------
# Note: partition_by is entity-specific and differs from convention
sink:
  silver:
    partition_by: ["organism"]

================================================================================
File: chembl.yaml
Path: sources\chembl.yaml
================================================================================
# configs/sources/chembl.yaml
# Configuration for ChEMBL API data source.
#
# Provider: European Bioinformatics Institute (EBI) ChEMBL
# API Documentation: https://www.ebi.ac.uk/chembl/ws
# Data License: CC BY-SA 3.0

source:
    type: api
    load_strategy: full
    batch_size: 20
    provider_config:
        provider: chembl
        base_url: https://www.ebi.ac.uk/chembl/api/data
        auth_type: public  # No authentication required
        client:
            timeout_sec: 60.0
            max_retries: 3
        max_url_length: 2000
        batch_size: 20
        page_size: 1000
        api_version: null

    circuit_breaker:
        failure_threshold: 5
        recovery_timeout: 300

    # ChEMBL has no official rate limit but recommends reasonable usage.
    # Conservative defaults to be a good API citizen.
    rate_limit:
        requests_per_second: 5
        burst: 10

    health_check:
        endpoint: /chembl/api/data/status.json
        timeout: 5

    retry:
        use_retry_after: false  # ChEMBL doesn't return Retry-After headers

# Available entities for this provider
entities:
    - activity           # Biological activity measurements
    - assay              # Bioassay definitions
    - assay_parameters   # Experimental parameters
    - cell_line          # Cell line reference data
    - compound_record    # Molecule-document links
    - document           # Scientific publications
    - document_similarity  # Document Tanimoto coefficients
    - document_term      # MeSH headings and keywords
    - molecule           # Chemical compounds
    - protein_class      # Protein classification hierarchy
    - target             # Biological targets
    - target_component   # Target protein components

# Entity-specific notes for documentation
entity_notes:
    activity:
        description: "Primary bioactivity data with IC50, Ki, etc."
        typical_volume: "~20M records"
    assay:
        description: "Bioassay definitions and metadata"
        typical_volume: "~1.5M records"
    molecule:
        description: "Chemical compounds with structures"
        typical_volume: "~2.5M records"
    target:
        description: "Biological targets (proteins, genes)"
        typical_volume: "~15K records"
    protein_class:
        description: "Reference table for protein classification"
        typical_volume: "~1.5K records"
    document_term:
        description: "Derived entity - extracted from document records"
        derived_from: "document"

================================================================================
File: crossref.yaml
Path: sources\crossref.yaml
================================================================================
# configs/sources/crossref.yaml
# Configuration for CrossRef API data source.
# Provides publication metadata via DOI resolution.
#
# Provider: CrossRef
# API Documentation: https://api.crossref.org/swagger-ui/index.html
# Data License: CC0 metadata, varies for full text

source:
    type: api
    load_strategy: full
    batch_size: 50  # Max DOIs per batch request
    provider_config:
        provider: crossref
        base_url: https://api.crossref.org
        auth_type: email  # Email for polite pool access
        mailto: ${BIOETL_CROSSREF_EMAIL}  # Required for polite pool access
        client:
            timeout_sec: 30.0
            max_retries: 3
        batch_size: 50  # DOIs per batch
        cursor_pagination: true  # Uses cursor-based pagination

    circuit_breaker:
        failure_threshold: 5
        recovery_timeout: 300

    # CrossRef polite pool: 50 req/sec with mailto parameter.
    # Set BIOETL_CROSSREF_EMAIL to access higher rate limits.
    # Without email: shared pool with aggressive rate limiting.
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

# Available entities for this provider
entities:
    - publication  # CrossRef works (DOI metadata)

# Entity-specific notes for documentation
entity_notes:
    publication:
        description: "Publication metadata via DOI resolution"
        input_mode: "CSV file with DOIs"
        fallback: "Title search when DOI not found (404)"
        batch_size: 50

================================================================================
File: openalex.yaml
Path: sources\openalex.yaml
================================================================================
# configs/sources/openalex.yaml
# Configuration for OpenAlex API data source.
# Provides open scholarly metadata via Works API.
#
# Provider: OpenAlex (OurResearch)
# API Documentation: https://docs.openalex.org
# Data License: CC0 (Public Domain)

source:
    type: api
    load_strategy: full
    batch_size: 50  # Max DOIs per batch request (recommended)
    provider_config:
        provider: openalex
        base_url: https://api.openalex.org
        auth_type: email  # Email for polite pool access
        mailto: ${BIOETL_OPENALEX_EMAIL}  # Required for polite pool access
        client:
            timeout_sec: 30.0
            max_retries: 3
        batch_size: 50  # DOIs per batch
        cursor_pagination: true  # Uses cursor-based pagination

    circuit_breaker:
        failure_threshold: 5
        recovery_timeout: 300

    # OpenAlex polite pool: 10 req/sec with mailto parameter.
    # Set BIOETL_OPENALEX_EMAIL to get higher rate limits.
    # Without email: shared pool with lower priority.
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

# Available entities for this provider
entities:
    - publication  # Scholarly works (papers, articles)

# Entity-specific notes for documentation
entity_notes:
    publication:
        description: "Scholarly works metadata via DOI resolution"
        input_mode: "CSV file with DOIs"
        fallback: "Title search when DOI not found"
        batch_size: 50  # Recommended by OpenAlex

================================================================================
File: pubchem.yaml
Path: sources\pubchem.yaml
================================================================================
# configs/sources/pubchem.yaml
# Configuration for PubChem PUG REST API data source.
#
# Provider: NCBI PubChem
# API Documentation: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
# Data License: Public Domain

source:
    type: api
    load_strategy: full
    batch_size: 50
    provider_config:
        provider: pubchem
        base_url: https://pubchem.ncbi.nlm.nih.gov/rest/pug
        auth_type: public  # No authentication required
        client:
            timeout_sec: 30.0
            max_retries: 3
        batch_size: 50  # PUG REST often limits batch sizes

    circuit_breaker:
        failure_threshold: 5
        recovery_timeout: 300

    # PubChem enforces 5 requests/second for PUG REST API.
    # Exceeding this limit results in temporary IP blocking.
    rate_limit:
        requests_per_second: 5.0
        burst: 10

    health_check:
        method: "Lightweight compound query"
        timeout: 10

    retry:
        use_retry_after: true  # PubChem returns Retry-After on 429

# Available entities for this provider
entities:
    - compound  # Chemical compounds with properties

# Entity-specific notes for documentation
entity_notes:
    compound:
        description: "Chemical compounds with computed properties"
        typical_volume: "Depends on input filter (SMILES-based)"
        input_mode: "SMILES-based search"
        batch_size: 1  # SMILES search is per-compound

================================================================================
File: pubmed.yaml
Path: sources\pubmed.yaml
================================================================================
# configs/sources/pubmed.yaml
# Configuration for PubMed (NCBI Entrez E-utilities) data source.
#
# Provider: NCBI PubMed (Entrez E-utilities)
# API Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25500/
# Data License: Public Domain (US Government)

source:
    type: api
    load_strategy: full
    batch_size: 100
    provider_config:
        provider: pubmed
        base_url: https://eutils.ncbi.nlm.nih.gov/entrez/eutils
        auth_type: api_key  # Optional API key for higher rate limits
        api_key_env: BIOETL_NCBI_API_KEY
        email_env: BIOETL_NCBI_EMAIL  # Required by NCBI guidelines
        client:
            timeout_sec: 60.0
            max_retries: 3
        default_email: "bioetl-bot@example.com"

    circuit_breaker:
        failure_threshold: 5
        recovery_timeout: 300

    # PubMed E-utilities: 3 req/sec without key, 10 req/sec with key.
    # NCBI requires email identification for all E-utilities requests.
    # API key (free) increases rate limit from 3 to 10 req/sec.
    # Register at: https://www.ncbi.nlm.nih.gov/account/
    rate_limit:
        requests_per_second: 3.0  # Default without API key
        burst: 5
        with_api_key:
            requests_per_second: 10
            burst: 20

    health_check:
        endpoint: /einfo.fcgi
        timeout: 10

    retry:
        use_retry_after: true

# Available entities for this provider
entities:
    - publication  # PubMed article metadata

# Entity-specific notes for documentation
entity_notes:
    publication:
        description: "PubMed article metadata via Entrez"
        input_mode: "Search term or PMID list"
        search_syntax: "PubMed boolean queries supported"

================================================================================
File: semanticscholar.yaml
Path: sources\semanticscholar.yaml
================================================================================
# configs/sources/semanticscholar.yaml
# Configuration for Semantic Scholar Academic Graph API data source.
# Provides publication metadata via DOI resolution and title search.
#
# Provider: Semantic Scholar (Allen Institute for AI)
# API Documentation: https://api.semanticscholar.org/api-docs/
# Data License: Semantic Scholar Dataset License
#
# IMPORTANT: Semantic Scholar API is highly rate-limited!
# - Without API key: Shared pool with aggressive throttling, frequent 429 errors
# - With API key: Guaranteed 1 req/sec per endpoint (stable, recommended)
#
# Get API key at: https://www.semanticscholar.org/product/api

source:
    type: api
    load_strategy: full
    batch_size: 50  # Reduced batch size for rate limit safety
    provider_config:
        provider: semanticscholar
        base_url: https://api.semanticscholar.org/graph/v1
        auth_type: api_key  # Recommended for stable access
        api_key: ${BIOETL_SEMANTICSCHOLAR_API_KEY}
        client:
            timeout_sec: 60.0       # Increased timeout for slow responses
            max_retries: 5          # More retries for 429 recovery
            retry_delay_sec: 10.0   # Longer delay between retries
        batch_size: 50  # Reduced for rate limit safety
        page_size: 100  # Minimum allowed by schema

    # More tolerant circuit breaker for S2's rate limit behavior.
    # Extended settings to handle frequent 429 responses.
    circuit_breaker:
        failure_threshold: 10      # More failures before opening
        recovery_timeout: 600      # 10 min recovery (rate limit cooldown)

    # Rate limits WITHOUT API key (very conservative).
    # S2 shared pool is unstable, use slow rate to avoid 429.
    rate_limit:
        requests_per_second: 0.1   # 1 request per 10 seconds
        burst: 1
        window: 300  # 5-minute sliding window
        with_api_key:
            requests_per_second: 1.0
            burst: 5

    health_check:
        endpoint: /paper/search
        params:
            query: test
            limit: 1
            fields: paperId
        timeout: 30                 # Longer timeout for health check
        skip_on_429: true           # Don't fail health check on rate limit

    retry:
        use_retry_after: true

# Available entities for this provider
entities:
    - publication  # Semantic Scholar papers

# Entity-specific notes for documentation
entity_notes:
    publication:
        description: "Semantic Scholar paper metadata via DOI resolution"
        input_mode: "CSV file with DOIs"
        fallback: "Title search when DOI not found"
        batch_size: 100  # Reduced for rate limit safety

================================================================================
File: uniprot.yaml
Path: sources\uniprot.yaml
================================================================================
# configs/sources/uniprot.yaml
# Configuration for UniProt REST API data source.
#
# Provider: UniProt Consortium
# API Documentation: https://www.uniprot.org/help/api
# Data License: CC BY 4.0

source:
    type: api
    load_strategy: full
    batch_size: 200  # UniProt handles slightly larger batches well
    provider_config:
        provider: uniprot
        base_url: https://rest.uniprot.org
        auth_type: api_key  # Optional API key for higher rate limits
        api_key_env: BIOETL_UNIPROT_API_KEY
        client:
            timeout_sec: 30.0
            max_retries: 3

    circuit_breaker:
        failure_threshold: 5
        recovery_timeout: 300

    # UniProt allows 100 requests/second with API key.
    # Without key, use conservative limits to avoid blocking.
    rate_limit:
        requests_per_second: 10.0
        burst: 20
        with_api_key:
            requests_per_second: 100
            burst: 200

    health_check:
        method: "Search probe query"
        timeout: 10

    retry:
        use_retry_after: true

# Available entities for this provider
entities:
    - protein     # UniProt protein entries
    - idmapping   # ChEMBL -> UniProt ID mapping

# Entity-specific notes for documentation
entity_notes:
    protein:
        description: "UniProt protein entries (Swiss-Prot reviewed)"
        typical_volume: "~570K reviewed entries"
    idmapping:
        description: "Maps ChEMBL target IDs to UniProt accessions"
        input_mode: "CSV file with target_chembl_id"
        dq_thresholds:
            soft_fail: 0.30  # Higher threshold - many targets lack UniProt mapping
            hard_fail: 0.80

