================================================================================
File: publication.yaml
Path: composite\field_groups\publication.yaml
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

      - base_name: publication_type
        columns:
          - chembl.publication.publication_type
          - pubmed.publication.publication_type

      - base_name: document_chembl_id
        columns:
          - chembl.publication.document_chembl_id

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

      - base_name: fields_of_study
        columns:
          - semanticscholar.publication.fields_of_study

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

      - base_name: content_hash
        columns:
          - chembl.publication.content_hash
          - crossref.publication.content_hash
          - openalex.publication.content_hash
          - pubmed.publication.content_hash
          - semanticscholar.publication.content_hash

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
File: activity.yaml
Path: data_schema\chembl\activity.yaml
================================================================================
column_groups: []

================================================================================
File: assay.yaml
Path: data_schema\chembl\assay.yaml
================================================================================
column_groups: []

================================================================================
File: assay_parameters.yaml
Path: data_schema\chembl\assay_parameters.yaml
================================================================================
column_groups: []

================================================================================
File: cell_line.yaml
Path: data_schema\chembl\cell_line.yaml
================================================================================
column_groups: []

================================================================================
File: compound_record.yaml
Path: data_schema\chembl\compound_record.yaml
================================================================================
column_groups: []

================================================================================
File: molecule.yaml
Path: data_schema\chembl\molecule.yaml
================================================================================
column_groups: []

================================================================================
File: protein_class.yaml
Path: data_schema\chembl\protein_class.yaml
================================================================================
column_groups: []

================================================================================
File: publication.yaml
Path: data_schema\chembl\publication.yaml
================================================================================
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
      - document_chembl_id
      - doi
      - pmid

  - name: title
    fields:
      - title

  - name: abstract
    fields:
      - abstract

  - name: authors
    fields:
      - authors

  - name: journal
    fields:
      - journal

  - name: year
    fields:
      - publication_year

  - name: pagination
    fields:
      - volume
      - issue
      - page_first
      - page_last

  - name: doc_type
    fields:
      - publication_type

  - name: provider_ids
    fields:
      - src_id
      - chembl_release
      - creation_date

  - name: dq
    pattern: "^_dq_"

# Field aliases for backward compatibility
field_aliases:
  year: publication_year
  first_page: page_first
  last_page: page_last
  doc_type: publication_type

# Layer-specific column filtering
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

================================================================================
File: publication_similarity.yaml
Path: data_schema\chembl\publication_similarity.yaml
================================================================================
column_groups: []

================================================================================
File: publication_term.yaml
Path: data_schema\chembl\publication_term.yaml
================================================================================
column_groups: []

================================================================================
File: target.yaml
Path: data_schema\chembl\target.yaml
================================================================================
column_groups: []

================================================================================
File: target_component.yaml
Path: data_schema\chembl\target_component.yaml
================================================================================
column_groups: []

================================================================================
File: tissue.yaml
Path: data_schema\chembl\tissue.yaml
================================================================================
# configs/data_schema/chembl/tissue.yaml
# Column group definitions for ChEMBL Tissue entity

version: "1.0.0"
entity: tissue

# Column groups must be a list of {name, fields} objects
column_groups:
  - name: identifiers
    fields:
      - tissue_chembl_id
  - name: core_metadata
    fields:
      - pref_name
  - name: ontology_references
    fields:
      - bto_id
      - caloha_id
      - efo_id
      - uberon_id

# All business fields for Gold layer
gold_columns:
  - tissue_chembl_id
  - pref_name
  - bto_id
  - caloha_id
  - efo_id
  - uberon_id

================================================================================
File: assay.yaml
Path: data_schema\composite\assay.yaml
================================================================================
# configs/data_schema/composite/assay.yaml
# =============================================================================
# Data Schema for Composite Assay Pipeline
# =============================================================================
#
# Defines field mappings between ChEMBL assay, cell_line, and tissue schemas.
# Used for column ordering, field renaming, and merge configuration.
#
# Source Entities:
#   - ChEMBL Assay: seed fields (AssaySchema)
#   - ChEMBL Cell Line: enricher fields (CellLineSchema)
#   - ChEMBL Tissue: enricher fields (TissueSchema)
#
# Reference: ADR-029 (Data Schema Externalization)
# Version: 1.0.0
# Last Updated: 2026-02-04
#
# =============================================================================

version: "1.0.0"
entity: assay

# =============================================================================
# Field Conflict Resolution Table
# =============================================================================
#
# | Source Entity | Original Field | Renamed Field     | Reason              |
# |---------------|----------------|-------------------|---------------------|
# | cell_line     | efo_id         | cell_efo_id       | Conflicts tissue    |
# | tissue        | efo_id         | tissue_efo_id     | Conflicts cell_line |
# | tissue        | pref_name      | tissue_pref_name  | Clarity             |
# | tissue        | uberon_id      | tissue_uberon_id  | Namespace clarity   |
# | tissue        | bto_id         | tissue_bto_id     | Namespace clarity   |
# | tissue        | caloha_id      | tissue_caloha_id  | Namespace clarity   |
#
# =============================================================================

# Field renaming rules for enrichers
field_renames:
  "chembl.cell_line.efo_id": "cell_efo_id"
  "chembl.tissue.efo_id": "tissue_efo_id"
  "chembl.tissue.pref_name": "tissue_pref_name"
  "chembl.tissue.uberon_id": "tissue_uberon_id"
  "chembl.tissue.bto_id": "tissue_bto_id"
  "chembl.tissue.caloha_id": "tissue_caloha_id"

# Column groups for semantic ordering
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

  # 2. Lineage metadata
  - name: lineage
    pattern: "^_composite_|^_source_providers|^_enrichment_|^_lineage_|^_dq_"

  # 3. Primary identifiers (assay)
  - name: identifiers
    fields:
      - assay_chembl_id
      - cell_chembl_id
      - tissue_chembl_id
      - target_chembl_id
      - document_chembl_id
      - src_id
      - src_assay_id
      - aidx
    provider_order: [chembl]

  # 4. Assay classification
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

  # 5. Biological context (from seed)
  - name: biological_context
    fields:
      - assay_organism
      - assay_taxonomy_id
      - assay_strain
      - assay_tissue
      - assay_cell_type
      - assay_subcellular_fraction
    provider_order: [chembl]

  # 6. Assay description
  - name: description
    fields:
      - description
      - score
    provider_order: [chembl]

  # 7. BAO ontology
  - name: ontology
    fields:
      - bao_format
      - bao_label
    provider_order: [chembl]

  # 8. Cell line context (enricher)
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

  # 9. Tissue context (enricher)
  - name: tissue
    fields:
      - tissue_pref_name
      - tissue_uberon_id
      - tissue_bto_id
      - tissue_caloha_id
      - tissue_efo_id
    provider_order: [chembl]

  # 10. Variant information
  - name: variant
    fields:
      - variant_accession
      - variant_isoform
      - variant_mutation
      - variant_organism
      - variant_sequence
      - variant_taxonomy_id
    provider_order: [chembl]

  # 11. Complex JSON fields
  - name: complex
    fields:
      - assay_classifications
      - assay_parameters
      - variant_sequence_json
    provider_order: [chembl]

# Layer-specific overrides
silver:
  include_all_groups: true
  exclude_groups: []

gold:
  exclude_groups: []
  exclude_fields:
    # Exclude large JSON fields from Gold
    - assay_parameters
    - assay_classifications
    - variant_sequence_json
    # Exclude rarely used cell line field
    - clo_id

# Join Key Configuration
join_keys:
  cell_line:
    seed_field: cell_chembl_id
    enricher_field: cell_chembl_id
    description: "ChEMBL cell line ID for cell line enrichment"
    validation: "^CHEMBL\\d+$"
    nullable: true
    # Cardinality: one_to_one (each assay FK points to at most one cell line)

  tissue:
    seed_field: tissue_chembl_id
    enricher_field: tissue_chembl_id
    description: "ChEMBL tissue ID for tissue enrichment"
    validation: "^CHEMBL\\d+$"
    nullable: true
    # Cardinality: one_to_one (each assay FK points to at most one tissue)

# All business fields for Gold layer (excluding system/lineage)
gold_columns:
  # Identifiers
  - assay_chembl_id
  - cell_chembl_id
  - tissue_chembl_id
  - target_chembl_id
  - document_chembl_id
  - src_id
  - src_assay_id
  - aidx
  # Classification
  - assay_type
  - assay_category
  - assay_test_type
  - assay_group
  - assay_pref_name
  - relationship_type
  - relationship_description
  - confidence_score
  - confidence_description
  # Biological context
  - assay_organism
  - assay_taxonomy_id
  - assay_strain
  - assay_tissue
  - assay_cell_type
  - assay_subcellular_fraction
  # Description
  - description
  - score
  # Ontology
  - bao_format
  - bao_label
  # Cell line (enricher)
  - cell_name
  - cell_description
  - cell_type
  - cell_source_tissue
  - cell_source_organism
  - cell_source_taxonomy_id
  - cellosaurus_id
  - cl_lincs_id
  - cell_efo_id
  # Tissue (enricher)
  - tissue_pref_name
  - tissue_uberon_id
  - tissue_bto_id
  - tissue_caloha_id
  - tissue_efo_id
  # Variant
  - variant_accession
  - variant_isoform
  - variant_mutation
  - variant_organism
  - variant_sequence
  - variant_taxonomy_id

================================================================================
File: molecule.yaml
Path: data_schema\composite\molecule.yaml
================================================================================
# configs/data_schema/composite/molecule.yaml
# =============================================================================
# Data Schema for Composite Molecule Pipeline
# =============================================================================
#
# Defines field mappings between ChEMBL molecule and PubChem compound schemas.
# Used for column ordering and merge configuration.
#
# Field Mapping Legend:
#   - ChEMBL fields: From CHEMBL_MOLECULE_SCHEMA (silver.py)
#   - PubChem fields: From PUBCHEM_COMPOUND_SCHEMA (silver.py)
#   - Priority: Which provider's value is preferred in merge
#
# Reference: ADR-029 (Data Schema Externalization)
# =============================================================================

# =============================================================================
# Field Mapping Table
# =============================================================================
#
# | ChEMBL Field            | PubChem Field      | Unified Field     | Priority |
# |-------------------------|--------------------|--------------------|----------|
# | molecule_chembl_id      | —                  | molecule_chembl_id | chembl   |
# | —                       | cid                | cid                | pubchem  |
# | inchi_key               | inchikey           | inchikey           | chembl   |
# | standard_inchi          | inchi              | inchi              | chembl   |
# | canonical_smiles        | canonical_smiles   | canonical_smiles   | chembl   |
# | —                       | isomeric_smiles    | isomeric_smiles    | pubchem  |
# | property_full_mwt       | molecular_weight   | molecular_weight   | pubchem  |
# | property_full_molformula| molecular_formula  | molecular_formula  | pubchem  |
# | property_alogp          | —                  | alogp              | chembl   |
# | —                       | xlogp              | xlogp              | pubchem  |
# | property_psa            | tpsa               | tpsa               | pubchem  |
# | property_hba            | —                  | hba                | pubchem  |
# | property_hbd            | —                  | hbd                | pubchem  |
# | property_rtb            | —                  | rotatable_bonds    | pubchem  |
# | property_heavy_atoms    | —                  | heavy_atom_count   | pubchem  |
# | property_aromatic_rings | —                  | aromatic_rings     | pubchem  |
# | property_qed_weighted   | —                  | qed_weighted       | chembl   |
# | pref_name               | —                  | pref_name          | chembl   |
# | —                       | iupac_name         | iupac_name         | pubchem  |
# | molecule_synonyms       | —                  | synonyms           | merge    |
# | max_phase               | —                  | max_phase          | chembl   |
# | first_approval          | —                  | first_approval     | chembl   |
# | therapeutic_flag        | —                  | therapeutic_flag   | chembl   |
# | withdrawn_flag          | —                  | withdrawn_flag     | chembl   |
# | black_box_warning       | —                  | black_box_warning  | chembl   |
#
# =============================================================================

# Shared column groups (used by both Silver and Gold unless overridden)
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

  # 2. Lineage metadata (added by MergeService)
  - name: lineage
    pattern: "^_composite_|^_source_providers|^_enrichment_|^_lineage_"

  # 3. Primary identifiers
  - name: identifiers_chembl
    fields:
      - molecule_chembl_id
    provider_order: [chembl]

  - name: identifiers_pubchem
    fields:
      - cid
    provider_order: [pubchem]

  # 4. Structural identifiers (join keys)
  - name: structural_identifiers
    fields:
      - inchi_key           # ChEMBL field name
      - inchikey            # PubChem field name (alias)
      - standard_inchi      # ChEMBL
      - inchi               # PubChem
    provider_order: [chembl, pubchem]

  # 5. Structure representations
  - name: structure
    fields:
      - canonical_smiles
      - isomeric_smiles
      - helm_notation
      - structure_type
    provider_order: [chembl, pubchem]

  # 6. Molecular weight and formula
  - name: weight_formula
    fields:
      - molecular_weight     # Unified (PubChem priority)
      - molecular_formula    # Unified (PubChem priority)
      - property_full_mwt    # ChEMBL specific
      - property_mw_freebase # ChEMBL specific
      - property_full_molformula  # ChEMBL specific
    provider_order: [pubchem, chembl]

  # 7. Lipophilicity and polarity
  - name: lipophilicity
    fields:
      - property_alogp       # ChEMBL ALogP
      - xlogp                # PubChem XLogP3
      - property_psa         # ChEMBL PSA
      - tpsa                 # PubChem TPSA
    provider_order: [pubchem, chembl]

  # 8. Hydrogen bonding
  - name: hbond
    fields:
      - property_hba         # ChEMBL
      - property_hbd         # ChEMBL
    provider_order: [pubchem, chembl]

  # 9. Molecular complexity
  - name: complexity
    fields:
      - property_rtb         # ChEMBL rotatable bonds
      - property_heavy_atoms # ChEMBL
      - property_aromatic_rings  # ChEMBL
    provider_order: [pubchem, chembl]

  # 10. Drug-likeness metrics
  - name: druglikeness
    fields:
      - property_qed_weighted    # ChEMBL QED
      - property_ro5_violations  # ChEMBL Lipinski violations
      - property_ro3_pass        # ChEMBL Rule of 3
    provider_order: [chembl]

  # 11. Names and synonyms
  - name: names
    fields:
      - pref_name           # ChEMBL preferred name
      - iupac_name          # PubChem IUPAC name
      - molecule_synonyms   # ChEMBL synonyms (JSON)
    provider_order: [chembl, pubchem]

  # 12. Clinical development (ChEMBL only)
  - name: clinical
    fields:
      - max_phase
      - first_approval
      - therapeutic_flag
      - black_box_warning
      - withdrawn_flag
    provider_order: [chembl]

  # 13. Administration routes (ChEMBL only)
  - name: administration
    fields:
      - oral
      - parenteral
      - topical
    provider_order: [chembl]

  # 14. Regulatory flags (ChEMBL only)
  - name: regulatory
    fields:
      - first_in_class
      - prodrug
      - natural_product
      - dosed_ingredient
      - availability_type
    provider_order: [chembl]

  # 15. Molecular hierarchy (ChEMBL only)
  - name: hierarchy
    fields:
      - hierarchy_parent_chembl_id
      - hierarchy_active_chembl_id
      - hierarchy_child_chembl_id
      - molecule_hierarchy
    provider_order: [chembl]

  # 16. Molecular classification (ChEMBL only)
  - name: classification
    fields:
      - molecule_type
      - atc_classifications
      - chirality
      - inorganic_flag
      - polymer_flag
      - molecule_species
    provider_order: [chembl]

  # 17. USAN nomenclature (ChEMBL only)
  - name: usan
    fields:
      - usan_year
      - usan_stem
      - usan_substem
      - usan_stem_definition
    provider_order: [chembl]

  # 18. Cross-references
  - name: xrefs
    fields:
      - cross_references
    provider_order: [chembl, pubchem]

  # 19. Complex JSON fields
  - name: complex_fields
    fields:
      - molecule_properties
      - molecule_structures
    provider_order: [chembl]

# =============================================================================
# Layer-specific overrides
# =============================================================================

# Silver layer: Include all fields for forensic purposes
silver:
  include_all_groups: true
  exclude_groups: []

# Gold layer: Exclude internal JSON fields
gold:
  exclude_groups:
    - complex_fields
  exclude_fields:
    - molecule_properties
    - molecule_structures
    - molecule_hierarchy

# =============================================================================
# Join Key Configuration
# =============================================================================
join_keys:
  primary:
    field: inchikey
    chembl_name: inchi_key
    pubchem_name: inchikey
    description: "InChIKey - IUPAC standard structural identifier (27 chars)"
    validation: "^[A-Z]{14}-[A-Z]{10}-[A-Z]$"

  fallback:
    field: canonical_smiles
    chembl_name: canonical_smiles
    pubchem_name: canonical_smiles
    description: "Canonical SMILES (fallback - less reliable due to canonization differences)"
    validation: null  # SMILES validation is complex

# =============================================================================
# Field Normalization Rules
# =============================================================================
normalization:
  # InChIKey normalization (should already be uppercase)
  inchikey:
    uppercase: true
    strip: true

  # SMILES normalization (preserve case for canonization)
  canonical_smiles:
    strip: true

  # Molecular weight: ensure float
  molecular_weight:
    type: float
    precision: 4

================================================================================
File: publication.yaml
Path: data_schema\composite\publication.yaml
================================================================================
# Layer-specific column configuration (ADR-029: Data Schema Externalization)
# This file demonstrates Variant 2 approach: filtering shared column_groups by layer

# Shared column groups (used by both Silver and Gold unless overridden)
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
  - name: identifiers_document_chembl_id
    fields:
      - document_chembl_id
    provider_order: [chembl]

  # 3.2 doi identifiers
  - name: identifiers_doi
    fields:
      - doi
    provider_order: [chembl, crossref, openalex, pubmed, semanticscholar]

  # 3.3 pmid identifiers
  - name: identifiers_pmid
    fields:
      - pmid
    provider_order: [chembl, openalex, pubmed, semanticscholar]

  # 4. PMC IDs (separate group - not in seed)
  # Note: Only PubMed provides pmc_id (removed from OpenAlex, SemanticScholar)
  - name: pmc_identifiers
    fields:
      - pmc_id
    provider_order: [pubmed]

  # 5. Title group
  # Note: vernacular_title removed (PubMed no longer provides it)
  - name: title
    fields:
      - title
    provider_order: [chembl, crossref, openalex, pubmed, semanticscholar]

  # 6. Abstract group
  - name: abstract
    fields:
      - abstract
      - abstract_structured
    provider_order: [chembl, pubmed, crossref, openalex, semanticscholar]

  # 7. Authors group
  - name: authors
    fields:
      - authors
      - author_count
      - authors_with_affiliations
    provider_order: [chembl, crossref, openalex, pubmed, semanticscholar]

  # 7a. Author identifiers (for author-level analytics)
  - name: author_identifiers
    fields:
      - author_orcids          # CrossRef, SemanticScholar
      - author_details         # CrossRef-unique (JSON: given, family, orcid, sequence, affiliations)
      - author_openalex_ids    # OpenAlex-unique author IDs
      - author_s2_ids          # SemanticScholar-unique author IDs
      - author_h_indices       # SemanticScholar-unique h-index values
    provider_order: [crossref, openalex, semanticscholar]

  # 7b. Author affiliations
  # Note: PubMed structured_affiliations contains ROR/GRID identifiers
  - name: affiliations
    fields:
      - affiliation_structured     # PubMed (preferred, with ROR/GRID identifiers)
      - affiliation_list           # PubMed, OpenAlex, SemanticScholar (raw)
      - institution_ids            # OpenAlex institution IDs
      - institution_country_codes  # OpenAlex institution country codes
      - ror_ids                    # OpenAlex ROR identifiers
    provider_order: [pubmed, openalex, semanticscholar]

  # 8. Journal group
  - name: journal
    fields:
      - journal                 # Canonical field (all providers use journal or venue→journal)
      - journal_name
      - journal_name_short
      - journal_iso_abbrev
    provider_order: [chembl, crossref, openalex, pubmed, semanticscholar]

  # 9. Year group
  - name: year
    fields:
      - publication_year
    provider_order: [chembl, crossref, openalex, pubmed, semanticscholar]

  # 10. Publication dates
  # Note: Legacy fields normalized (year → publication_year, pub_date → publication_date)
  # Note: epub_date, accepted_date, received_date, revised_date removed
  # (PubMed no longer provides these fields)
  - name: dates
    fields:
      - publication_date       # Canonical field (YYYY-MM-DD)
      - published
      - published_print
      - published_online
      - pub_month
      - pub_day
      - date_completed
      - date_revised
    provider_order: [crossref, openalex, pubmed, semanticscholar]

  # 11. Volume/Issue/Pages
  - name: pagination
    fields:
      - volume
      - issue
      - page_first
      - page_last
      - page_range
      - medline_pgn
    provider_order: [chembl, crossref, openalex, pubmed, semanticscholar]

  # 12. Citation metrics
  - name: citations
    fields:
      - citations_received
      - citations_made
      - influential_citation_count  # SemanticScholar-unique
    provider_order: [crossref, openalex, semanticscholar, pubmed]

  # 12a. Citation references (detailed reference data)
  - name: citation_references
    fields:
      - references               # CrossRef-unique (JSON: DOI, title, author, year)
      - citation_contexts        # SemanticScholar-unique (JSON: context sentences)
    provider_order: [crossref, semanticscholar]

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
  # Note: CrossRef and OpenAlex use raw 'source_type' field instead of mapped 'doc_type'
  - name: doc_type
    fields:
      - publication_type
      - publication_type_unified
      - publication_subclass
      - publication_class
      - source_type       # CrossRef, OpenAlex raw type (journal-article, article, etc.)
    provider_order: [chembl, crossref, openalex, pubmed, semanticscholar]

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
  # NOTE: 'subject_topics' replaces deprecated 'concepts' per OpenAlex 2024 migration
  - name: subjects
    fields:
      - subject_topics
      - primary_topic            # OpenAlex primary topic classification
      - subject_fields
      - subject_mesh
      - mesh_heading_count
      - subject_keywords
      - keyword_count
      - publication_types
      - publication_type_list
    provider_order: [crossref, openalex, pubmed, semanticscholar]

  # 19. Provider-specific IDs
  # Note: arxiv_id removed (SemanticScholar no longer provides it)
  - name: provider_ids
    fields:
      - openalex_id
      - paper_id
      - corpus_id
      - src_id
      - chembl_release
      - creation_date
      - nlm_unique_id
      - mag_id                   # OpenAlex MAG legacy ID
      - dblp_id                  # SemanticScholar DBLP key
    provider_order: [chembl, openalex, semanticscholar, pubmed]

  # 19a. Alternative publication identifiers
  - name: alternative_ids
    fields:
      - pii                      # PubMed Publisher Item Identifier
      - mid                      # PubMed Manuscript ID
      - publisher_id             # PubMed publisher-specific identifier
    provider_order: [pubmed]

  # 20. Quality indicators (CRITICAL for data integrity)
  - name: quality
    fields:
      - is_retracted             # OpenAlex-unique (CRITICAL: must flag retracted papers)
    provider_order: [openalex]

  # 21. Advanced metrics
  - name: metrics
    fields:
      - fwci                     # OpenAlex Field-Weighted Citation Impact
    provider_order: [openalex]

  # 22. Funding/Grants
  - name: funding
    fields:
      - grants                   # OpenAlex-unique (JSON: funder, award info)
      - grant_count              # PubMed grant count
    provider_order: [openalex, pubmed]

  # 23. PubMed-specific chemical and gene data
  - name: chemicals_genes
    fields:
      - chemicals                # PubMed-unique (JSON: name/registry pairs)
      - chemical_count           # PubMed chemical count
      - gene_symbols             # PubMed-unique gene symbols
      - databanks                # PubMed-unique databank accessions
    provider_order: [pubmed]

  # 24. Miscellaneous fields
  - name: misc
    fields:
      - license_url
      - alternative_id
      - content_domain_domains
      - content_domain_crossmark_restriction
      - country
      - citation_subset
      - publication_status
    provider_order: [crossref, pubmed]

  # 25. DQ fields (always last)
  # Note: _source is a system field in the 'system' group
  - name: dq
    pattern: "^_dq_"

# Field aliases for backward compatibility
field_aliases:
  year: publication_year
  doc_type: publication_type
  first_page: page_first
  last_page: page_last
  citation_count: citations_received
  reference_count: citations_made
  affiliations: affiliation_list
  mesh_terms: subject_mesh
  keywords: subject_keywords
  topics: subject_topics
  journal_title: journal_name
  journal_abbrev: journal_name_short
  pages: page_range
  fields_of_study: subject_fields

# Layer-specific column filtering (Variant 2 approach)
# Silver: Include most fields for intermediate processing
# NOTE: rename_fields can be used to standardize column names between layers
# Example: rename_fields: {"_run_id": "pipeline_run_id", "pmid": "pubmed_id"}
silver:
  include_groups:
    - system
    - lineage
    - identifiers_document_chembl_id
    - identifiers_doi
    - identifiers_pmid
    - pmc_identifiers
    - title
    - abstract
    - authors
    - author_identifiers
    - affiliations
    - journal
    - year
    - dates
    - pagination
    - citations
    - citation_references
    - issn
    - open_access
    - doc_type
    - language
    - publisher
    - subjects
    - provider_ids
    - alternative_ids
    - quality
    - metrics
    - funding
    - chemicals_genes
    - misc
    - dq
  # Keep DQ fields in Silver for monitoring
  # exclude_fields: []

# Gold: Minimal curated dataset for analytics
gold:
  include_groups:
    - system              # entity_id, content_hash, _run_id (essential)
    - identifiers_doi     # Primary identifier
    - identifiers_pmid    # Secondary identifier
    - title               # Core metadata
    - abstract            # Core content
    - authors             # Authorship (authors, author_count)
    - journal             # Publication venue
    - year                # Temporal dimension
    - citations           # Impact metrics
    - open_access         # Access status
    - quality             # Data integrity (is_retracted)
  exclude_fields:
    - _dq_*               # Remove DQ fields from Gold
    - _composite_*        # Remove internal composite metadata
    - _source_batch_id    # Remove internal batch tracking
    - _index              # Remove internal indexing
    - _lookup_method      # Remove internal lookup metadata

# Output paths

================================================================================
File: publication.yaml
Path: data_schema\crossref\publication.yaml
================================================================================
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
      - doi
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
    pattern: "^_dq_"

# Field aliases for backward compatibility
field_aliases:
  short_container_title: journal_name_short
  year: publication_year
  first_page: page_first
  last_page: page_last
  citation_count: citations_received
  reference_count: citations_made
  subjects: subject_keywords
  source_type: publication_type
  # author_orcids: now native field name (was: author_orcid_list)

# Layer-specific column filtering
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

================================================================================
File: publication_with_renames.yaml
Path: data_schema\examples\publication_with_renames.yaml
================================================================================
# Example: Layer-specific column configuration with rename chains
# This demonstrates how to use rename_fields across Silver and Gold layers.
#
# IMPORTANT: Gold rename_fields MUST use column names AFTER silver.rename_fields!
# Gold reads from Silver, so it sees Silver's output schema, not original names.

column_groups:
  - name: system
    fields:
      - entity_id
      - content_hash
      - _run_id
      - _run_type
      - _source_batch_id
      - _ingestion_ts

  - name: identifiers
    fields:
      - doi
      - pmid
      - pmc_id

  - name: title
    fields:
      - title

  - name: abstract
    fields:
      - abstract

  - name: dq
    pattern: "^_dq_"

# Silver layer: Optionally rename to standardized internal names
silver:
  include_groups:
    - system
    - identifiers
    - title
    - abstract
    - dq
  # Optional: Standardize internal names in Silver
  rename_fields:
    entity_id: document_id         # Rename for internal consistency
    content_hash: content_version  # More descriptive name

# Gold layer: Rename to user-friendly names
# IMPORTANT: Use column names AFTER silver.rename_fields!
gold:
  include_groups:
    - system
    - identifiers
    - title
    - abstract
  exclude_fields:
    - _dq_*
    - _source_batch_id
  # Rename from Silver output schema (not original names!)
  rename_fields:
    # System fields (using Silver output names!)
    document_id: publication_id          # Silver renamed entity_id → document_id
    content_version: version_hash        # Silver renamed content_hash → content_version
    _run_id: pipeline_run_id             # Original name (not renamed in Silver)
    _run_type: pipeline_run_type         # Original name
    _ingestion_ts: ingestion_timestamp   # Original name
    # Identifiers (original names, not renamed in Silver)
    pmid: pubmed_id
    pmc_id: pubmed_central_id
    doi: digital_object_identifier

# Rename chain visualization:
# ┌──────────────────┬───────────────────┬─────────────────────────┐
# │ Original         │ Silver            │ Gold                    │
# ├──────────────────┼───────────────────┼─────────────────────────┤
# │ entity_id        │ document_id       │ publication_id          │
# │ content_hash     │ content_version   │ version_hash            │
# │ _run_id          │ _run_id           │ pipeline_run_id         │
# │ pmid             │ pmid              │ pubmed_id               │
# │ doi              │ doi               │ digital_object_identifier│
# │ title            │ title             │ title                   │
# └──────────────────┴───────────────────┴─────────────────────────┘

# Result:
# Silver columns: document_id, content_version, _run_id, doi, pmid, title, abstract, _dq_*
# Gold columns: publication_id, version_hash, pipeline_run_id,
#               digital_object_identifier, pubmed_id, title, abstract

================================================================================
File: publication.yaml
Path: data_schema\openalex\publication.yaml
================================================================================
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
      - doi
      - pmid
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
    pattern: "^_dq_"

# Field aliases for backward compatibility
field_aliases:
  affiliations: affiliation_list
  year: publication_year
  first_page: page_first
  last_page: page_last
  citation_count: citations_received
  reference_count: citations_made
  topics: subject_topics
  keywords: subject_keywords
  mesh_terms: subject_mesh
  source_type: publication_type

# Layer-specific column filtering
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

================================================================================
File: compound.yaml
Path: data_schema\pubchem\compound.yaml
================================================================================
column_groups: []

================================================================================
File: publication.yaml
Path: data_schema\pubmed\publication.yaml
================================================================================
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
    pattern: "^_dq_"

# Field aliases for backward compatibility
field_aliases:
  affiliations: affiliation_list
  structured_affiliations: affiliation_structured
  journal_title: journal_name
  journal_abbrev: journal_name_short
  year: publication_year
  first_page: page_first
  last_page: page_last
  pages: page_range
  reference_count: citations_made
  mesh_terms: subject_mesh
  keywords: subject_keywords

# Layer-specific column filtering
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

================================================================================
File: publication.yaml
Path: data_schema\semanticscholar\publication.yaml
================================================================================
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
      - doi
      - pmid
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
    pattern: "^_dq_"

# Field aliases for backward compatibility
field_aliases:
  affiliations: affiliation_list
  year: publication_year
  first_page: page_first
  last_page: page_last
  pages: page_range
  citation_count: citations_received
  reference_count: citations_made
  fields_of_study: subject_fields

# Layer-specific column filtering
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

================================================================================
File: idmapping.yaml
Path: data_schema\uniprot\idmapping.yaml
================================================================================
column_groups: []

================================================================================
File: protein.yaml
Path: data_schema\uniprot\protein.yaml
================================================================================
column_groups: []

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

  - field: publication_year
    type: range
    min: 1500
    max: 2100
    nullable: true
    error_message: "Publication year must be between 1500 and 2100"

  - field: pmid
    type: range
    min: 1
    max: 10000000000
    nullable: true
    error_message: "PubMed ID must be a positive integer"

  - field: doi
    type: pattern
    pattern: '^10\.\d{4,}/\S+$'
    nullable: true
    error_message: "DOI must match format 10.XXXX/suffix (no whitespace)"

  - field: title
    type: max_length
    max_length: 2000
    nullable: true
    error_message: "Title must not exceed 2000 characters"

  - field: title
    type: not_null
    nullable: true
    severity: warn
    error_message: "Missing title — record will be filtered before Gold"

  - field: title
    type: pattern
    pattern: '\S'
    nullable: true
    severity: warn
    error_message: "Title should not be empty or whitespace-only"

  - field: citations_received
    type: range
    min: 0
    nullable: true
    error_message: "Citation count must be non-negative"

  - field: citations_received
    type: range
    min: 0
    max: 10000000
    nullable: true
    severity: warn
    error_message: "Unusually high citation count"

  - field: citations_made
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
      - document_chembl_id
      - title
    condition: all_present
    error_message: "Publication must have document_chembl_id and title"

  - name: has_cross_reference
    fields:
      - pmid
      - doi
    condition: any_present
    severity: warn
    error_message: "Publication should have at least one external identifier (PMID or DOI)"

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations:
  - name: publication_requires_title
    condition_field: doc_type
    condition_value: PUBLICATION
    condition_operator: eq
    then_validations:
      - field: title
        type: not_null
        nullable: false
        error_message: "Publications of type PUBLICATION must have a title"

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
File: subcellular_fraction.yaml
Path: dq\entities\chembl\subcellular_fraction.yaml
================================================================================
# configs/dq/entities/chembl/subcellular_fraction.yaml
# ChEMBL Subcellular Fraction-specific DQ rules
# Inherits from: _defaults.yaml → providers/chembl.yaml

version: "1.0.0"
provider: chembl
entity: subcellular_fraction

# Thresholds: inherit from provider

# =============================================================================
# Subcellular Fraction-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: entity_id
    type: pattern
    pattern: '^[a-f0-9]{16}$'
    nullable: false
    error_message: "entity_id must be a 16-char SHA256 hash prefix"

  - field: subcellular_fraction
    type: pattern
    pattern: '^.{1,200}$'
    nullable: false
    error_message: "subcellular_fraction is required and must not exceed 200 chars"

  - field: assay_count
    type: numeric_range
    min_value: 0
    nullable: true
    error_message: "assay_count must be non-negative"

  - field: example_assay_chembl_id
    type: pattern
    pattern: '^CHEMBL\d+$'
    nullable: true
    error_message: "example_assay_chembl_id must match CHEMBL format if present"

# =============================================================================
# Cross-Field Validations
# =============================================================================
entity_cross_field_validations: []

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
File: tissue.yaml
Path: dq\entities\chembl\tissue.yaml
================================================================================
# configs/dq/entities/chembl/tissue.yaml
# ChEMBL Tissue-specific DQ rules
# Inherits from: _defaults.yaml → providers/chembl.yaml

version: "1.0.0"
provider: chembl
entity: tissue

# Thresholds: inherit from provider

# =============================================================================
# Tissue-Specific Field Validations
# =============================================================================
entity_field_validations:
  - field: tissue_chembl_id
    type: pattern
    pattern: '^CHEMBL\d+$'
    nullable: false
    error_message: "tissue_chembl_id must match CHEMBL format"

  - field: pref_name
    type: pattern
    pattern: '^.{1,200}$'
    nullable: false
    error_message: "pref_name is required and must not exceed 200 chars"

  - field: bto_id
    type: pattern
    pattern: '^BTO:\d{7}$'
    nullable: true
    error_message: "bto_id must match BTO format (BTO:0000000)"

  - field: caloha_id
    type: pattern
    pattern: '^TS-\d{4}$'
    nullable: true
    error_message: "caloha_id must match CALIPHO format (TS-0000)"

  - field: efo_id
    type: pattern
    pattern: '^EFO:\d{7}$'
    nullable: true
    error_message: "efo_id must match EFO format (EFO:0000000)"

  - field: uberon_id
    type: pattern
    pattern: '^UBERON:\d{7}$'
    nullable: true
    error_message: "uberon_id must match UBERON format (UBERON:0000000)"

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
    pattern: '^10\.\d{4,}/\S+$'
    nullable: false
    error_message: "DOI is required and must match format 10.XXXX/suffix (no whitespace)"

  - field: title
    type: max_length
    max_length: 2000
    nullable: true
    error_message: "Title must not exceed 2000 characters"

  - field: title
    type: not_null
    nullable: true
    severity: warn
    error_message: "Missing title — record will be filtered before Gold"

  - field: title
    type: pattern
    pattern: '\S'
    nullable: true
    severity: warn
    error_message: "Title should not be empty or whitespace-only"

  - field: publication_year
    type: range
    min: 1500
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

  - field: citations_received
    type: range
    min: 0
    nullable: true
    error_message: "Citation count must be non-negative"

  - field: citations_received
    type: range
    min: 0
    max: 10000000
    nullable: true
    severity: warn
    error_message: "Unusually high citation count"

  - field: citations_made
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
      - doi
      - title
    condition: all_present
    error_message: "Publication must have DOI and title"

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations:
  - name: article_requires_title
    condition_field: type
    condition_value:
      - journal-article
      - proceedings-article
    condition_operator: in
    then_validations:
      - field: title
        type: not_null
        nullable: false
        error_message: "Journal and proceedings articles must have a title"

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

  - field: pmid
    type: range
    min: 1
    max: 10000000000
    nullable: true
    error_message: "PubMed ID must be a positive integer"

  - field: doi
    type: pattern
    pattern: '^10\.\d{4,}/\S+$'
    nullable: true
    error_message: "DOI must match format 10.XXXX/suffix (no whitespace)"

  - field: title
    type: max_length
    max_length: 2000
    nullable: true
    error_message: "Title must not exceed 2000 characters"

  - field: title
    type: not_null
    nullable: true
    severity: warn
    error_message: "Missing title — record will be filtered before Gold"

  - field: title
    type: pattern
    pattern: '\S'
    nullable: true
    severity: warn
    error_message: "Title should not be empty or whitespace-only"

  - field: publication_year
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

  - field: citations_received
    type: range
    min: 0
    nullable: true
    error_message: "Citation count must be non-negative"

  - field: citations_received
    type: range
    min: 0
    max: 10000000
    nullable: true
    severity: warn
    error_message: "Unusually high citation count"

  - field: fwci
    type: range
    min: 0
    nullable: true
    error_message: "FWCI must be non-negative"

  - field: citations_made
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

  # NOTE: retracted_publication_warning moved to conditional_validations
  # (cross-field condition "is_retracted == true" was invalid syntax)

# =============================================================================
# Conditional Validations
# =============================================================================
entity_conditional_validations:
  - name: article_requires_title
    condition_field: type
    condition_value:
      - article
      - review
    condition_operator: in
    then_validations:
      - field: title
        type: not_null
        nullable: false
        error_message: "Articles and reviews must have a title"

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
    max: 10000000000
    nullable: false
    error_message: "PMID is required and must be a positive integer"

  - field: title
    type: max_length
    max_length: 2000
    nullable: true
    error_message: "Title must not exceed 2000 characters"

  - field: title
    type: not_null
    nullable: true
    severity: warn
    error_message: "Missing title — record will be filtered before Gold"

  - field: title
    type: pattern
    pattern: '\S'
    nullable: true
    severity: warn
    error_message: "Title should not be empty or whitespace-only"

  - field: doi
    type: pattern
    pattern: '^10\.\d{4,}/\S+$'
    nullable: true
    error_message: "DOI must match format 10.XXXX/suffix (no whitespace)"

  - field: publication_year
    type: range
    min: 1500
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

  - field: citations_received
    type: range
    min: 0
    nullable: true
    error_message: "Citation count must be non-negative"

  - field: citations_received
    type: range
    min: 0
    max: 10000000
    nullable: true
    severity: warn
    error_message: "Unusually high citation count"

  - field: citations_made
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

  - field: pmid
    type: range
    min: 1
    max: 10000000000
    nullable: true
    error_message: "PubMed ID must be a positive integer"

  - field: doi
    type: pattern
    pattern: '^10\.\d{4,}/\S+$'
    nullable: true
    error_message: "DOI must match format 10.XXXX/suffix (no whitespace)"

  - field: title
    type: max_length
    max_length: 2000
    nullable: true
    error_message: "Title must not exceed 2000 characters"

  - field: title
    type: not_null
    nullable: true
    severity: warn
    error_message: "Missing title — record will be filtered before Gold"

  - field: title
    type: pattern
    pattern: '\S'
    nullable: true
    severity: warn
    error_message: "Title should not be empty or whitespace-only"

  - field: publication_year
    type: range
    min: 1500
    max: 2100
    nullable: true
    error_message: "Publication year out of valid range"

  - field: citations_received
    type: range
    min: 0
    nullable: true
    error_message: "Citation count must be non-negative"

  - field: citations_received
    type: range
    min: 0
    max: 10000000
    nullable: true
    severity: warn
    error_message: "Unusually high citation count"

  - field: citations_made
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
entity_conditional_validations:
  - name: journal_article_requires_title
    condition_field: publication_type
    condition_value: JournalArticle
    condition_operator: eq
    then_validations:
      - field: title
        type: not_null
        nullable: false
        error_message: "Journal articles must have a title"

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

  # Quality metrics (added for extended schema)
  - field: annotation_score
    type: range
    min: 1
    max: 5
    nullable: true
    error_message: "Annotation score must be between 1 and 5"

  - field: protein_existence
    type: range
    min: 1
    max: 5
    nullable: true
    error_message: "Protein existence level must be between 1 and 5"

  # Cross-reference validations
  - field: go_terms
    type: not_empty_list
    nullable: true
    error_message: "GO terms list cannot be empty if present"

  - field: pdb_xrefs
    type: not_empty_list
    nullable: true
    error_message: "PDB xrefs list cannot be empty if present"

  # === GO Components (JSON arrays) ===
  - field: molecular_function
    type: pattern
    pattern: '^\[.*\]$'
    nullable: true
    error_message: "molecular_function must be JSON array"

  - field: cellular_component
    type: pattern
    pattern: '^\[.*\]$'
    nullable: true
    error_message: "cellular_component must be JSON array"

  # === Isoform Details (JSON arrays) ===
  - field: isoform_ids
    type: pattern
    pattern: '^\[.*\]$'
    nullable: true
    error_message: "isoform_ids must be JSON array"

  - field: isoform_names
    type: pattern
    pattern: '^\[.*\]$'
    nullable: true
    error_message: "isoform_names must be JSON array"

  - field: isoform_synonyms
    type: pattern
    pattern: '^\[.*\]$'
    nullable: true
    error_message: "isoform_synonyms must be JSON array"

  # === Reaction Data (JSON arrays) ===
  - field: reactions
    type: pattern
    pattern: '^\[.*\]$'
    nullable: true
    error_message: "reactions must be JSON array"

  - field: reaction_ec_numbers
    type: pattern
    pattern: '^\[.*\]$'
    nullable: true
    error_message: "reaction_ec_numbers must be JSON array"

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
    pattern: '^10\.\d{4,}/\S+$'
    nullable: true
    error_message: "Invalid DOI format (must match 10.XXXX/suffix, no whitespace)"

  # Year range validation
  - field: publication_year
    type: range
    min: 1500
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
    pattern: '^10\.\d{4,}/\S+$'
    nullable: true
    error_message: "Invalid DOI format (must match 10.XXXX/suffix, no whitespace)"

  # Year range validation
  - field: publication_year
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
    max: 10000000000
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
    pattern: '^10\.\d{4,}/\S+$'
    nullable: true
    error_message: "Invalid DOI format (must match 10.XXXX/suffix, no whitespace)"

  # Year range validation
  - field: publication_year
    type: range
    min: 1500
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
    pattern: '^10\.\d{4,}/\S+$'
    nullable: true
    error_message: "Invalid DOI format (must match 10.XXXX/suffix, no whitespace)"

  # Year range validation
  - field: publication_year
    type: range
    min: 1500
    max: 2100
    nullable: true
    error_message: "Publication year out of valid range"

  # Citation counts must be non-negative
  - field: citations_received
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
# Silver Filter Defaults
# =============================================================================
# Silver filters control which records pass domain-level quality gates
# AFTER transformation but BEFORE writing to Silver layer.
# Uses the same filter engine as gold_filters.
silver_filters:
  required_fields: []
  columns: {}
  ranges: {}
  list_lengths: {}
  list_contains: {}
  exclude_if_present: []

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

# ---------------------------------------------------------------------------
# Extraction-Level Filtering (ADR-028 §3)
# ---------------------------------------------------------------------------
# Server-side query parameters appended to every ChEMBL Activity API request.
# Syntax: ChEMBL django-style lookups (__in, __isnull, __gt, __lt, etc.)
# Reference: https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services
#
# These params reduce API traffic from ~20M to ~2-5M records.
# Does NOT affect content_hash (ADR-014).
# Logged in SourceMetadata.query_string for audit/reproducibility.
#
# Resulting API URL pattern:
#   /chembl/api/data/activity?format=json&limit=1000&offset=0
#     &standard_type__in=IC50,Ki
#     &standard_units=nM
#     &standard_relation==
#     &assay_type__in=B,F
#     &potential_duplicate=0
#     &data_validity_comment__isnull=true
#     &pchembl_value__isnull=false
#     &standard_flag=1
extraction_params:
  # Measurement types: IC50 (inhibitor concentration) and Ki (inhibition constant)
  standard_type__in: "IC50,Ki"

  # Standardized units: nanomolar only
  standard_units: "nM"

  # Exact measurements only (exclude censored: >, <, ~)
  standard_relation: "="

  # Assay types: Binding and Functional (exclude ADMET, Toxicity, etc.)
  assay_type__in: "B,F"

  # Exclude potential duplicate records
  potential_duplicate: 0

  # Exclude records flagged with data validity issues
  data_validity_comment__isnull: true

  # Only records with standardized pChEMBL value
  pchembl_value__isnull: false

  # Only ChEMBL-standardized values (manual curation flag)
  standard_flag: 1

# -----------------------------------------------------------------------------
# Silver Filters — Domain-level quality gates (applied BEFORE Silver write)
# -----------------------------------------------------------------------------
# Records that fail these filters are excluded from the Silver layer entirely.
# These enforce domain invariants and physically plausible value ranges.
silver_filters:
  # Column value filters — strict inclusion lists
  columns:
    # Only IC50 and Ki measurements
    standard_type: [IC50, Ki]
    # Only exact measurements (no censored: >, <, ~)
    standard_relation: ["="]
    # Only nanoMolar units
    standard_units: [nM]
    # Binding (B) and Functional (F) assays only
    assay_type: [B, F]
    # Exclude potential duplicates (0 = not duplicate)
    potential_duplicate: ["0"]

  # Numeric range filters
  ranges:
    activity_id:
      min: 1
      max: 10000000000  # 10^10
    standard_value:
      min: 0
      include_min: false  # Exclude exactly 0
    pchembl_value:
      min: 3
      max: 10
    document_year:
      min: 1950
      max: 2050

  # Required fields — must be non-null for silver
  required_fields:
    - activity_id
    - molecule_chembl_id
    - target_chembl_id
    - document_chembl_id
    - standard_value
    - pchembl_value

  # Exclude records with data validity issues (field must be null / absent)
  exclude_if_present:
    - data_validity_comment

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
  batch_size: 10

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
  batch_size: 16

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
    # Standardized publication year filter (1950..2050 inclusive)
    publication_year:
      min: 1950
      max: 2050

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
File: subcellular_fraction.yaml
Path: filter\entities\chembl\subcellular_fraction.yaml
================================================================================
# configs/filter/entities/chembl/subcellular_fraction.yaml
# =============================================================================
# ChEMBL Subcellular Fraction Filter Configuration
# =============================================================================
# Entity-specific filter rules for subcellular fractions (derived from assays).
# Reference: ADR-028 (Filter Rules Externalization)

version: "1.0.0"
provider: chembl
entity: subcellular_fraction

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# No input filter - extract all unique subcellular fractions from assays
input_filter:
  enabled: false

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Minimal filtering for lookup table
gold_filters:
  # Required fields for valid subcellular fraction
  required_fields:
    - subcellular_fraction

  # No column filters - include all valid fractions
  columns: {}

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
File: activity.yaml
Path: filter\entities\composite\activity.yaml
================================================================================
# configs/filter/entities/composite/activity.yaml
# =============================================================================
# Composite Activity Filter Configuration
# =============================================================================
# Entity-specific filter rules for composite activity pipeline.
# Reference: ADR-028 (Filter Rules Externalization)
#
# This composite combines:
# - chembl_activity (seed)
# - chembl_compound_record (dependency)
#
# Version: 1.0.0
# Last Updated: 2026-02-04
#
# =============================================================================

version: "1.0.0"
provider: composite
entity: activity

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# No input filter for composite pipeline.
# Composite pipeline aggregates from seed pipeline internally.
input_filter:
  enabled: false

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for valid activities in Gold layer.
# Note: Composite uses qualified column names ({provider}.{entity}.{field})
# Filter rules apply to either qualified or coalesced column names.
gold_filters:
  # Required fields - records missing these are excluded from Gold
  required_fields:
    - activity_id          # Primary key from seed
    - molecule_chembl_id   # FK to molecule (join key)
    - assay_chembl_id      # FK to assay

  # Field-specific validation (applied before Gold write)
  columns:
    activity_id:
      type: string
      nullable: false
      description: "ChEMBL activity ID (primary key)"

    molecule_chembl_id:
      type: string
      nullable: false
      pattern: "^CHEMBL\\d+$"
      description: "ChEMBL molecule identifier (FK)"

    assay_chembl_id:
      type: string
      nullable: false
      pattern: "^CHEMBL\\d+$"
      description: "ChEMBL assay identifier (FK)"

    target_chembl_id:
      type: string
      nullable: true
      pattern: "^CHEMBL\\d+$"
      description: "ChEMBL target identifier (FK, optional)"

    document_chembl_id:
      type: string
      nullable: true
      pattern: "^CHEMBL\\d+$"
      description: "ChEMBL document identifier (FK, optional)"

    standard_type:
      type: string
      nullable: true
      description: "Standardized activity type (IC50, Ki, EC50, etc.)"

    standard_relation:
      type: string
      nullable: true
      enum: ["=", "<", "<=", ">", ">="]
      description: "Standardized relation operator"

    standard_value:
      type: float
      nullable: true
      min_value: 0
      description: "Standardized activity value (non-negative)"

    standard_units:
      type: string
      nullable: true
      description: "Standardized activity units (nM, uM, etc.)"

    pchembl_value:
      type: float
      nullable: true
      min_value: 0
      max_value: 14
      description: "-log10 molar activity value (0-14 range)"

    # Compound record fields (from dependency)
    record_id:
      type: integer
      nullable: true
      min_value: 1
      description: "Compound record ID (from chembl_compound_record)"

    compound_name:
      type: string
      nullable: true
      description: "Original compound name from publication"

    compound_key:
      type: string
      nullable: true
      description: "Original compound key from source"

# -----------------------------------------------------------------------------
# DQ Thresholds (from composite config)
# -----------------------------------------------------------------------------
# These thresholds are applied during composite merge:
# - soft_fail_threshold: 0.10 (10% errors = warning)
# - hard_fail_threshold: 0.30 (30% errors = failure)
#
# Per-dependency overrides defined in composite config:
# - chembl_compound_record: soft=0.30, hard=0.70
#   (Many activities may not have matching compound records)

# -----------------------------------------------------------------------------
# Notes on Join Semantics
# -----------------------------------------------------------------------------
# Activity → CompoundRecord join is M:N:
# - One activity has one molecule_chembl_id
# - One molecule can have many compound records (from different documents)
# - Merge uses left_outer to preserve all activities
# - Missing compound_record fields will be null

================================================================================
File: assay.yaml
Path: filter\entities\composite\assay.yaml
================================================================================
# configs/filter/entities/composite/assay.yaml
# =============================================================================
# Composite Assay Filter Configuration
# =============================================================================
# Entity-specific filter rules for composite assay pipeline.
# Reference: ADR-028 (Filter Rules Externalization)
#
# This composite combines:
# - chembl_assay (seed)
# - chembl_cell_line (enricher)
# - chembl_tissue (enricher)
#
# Version: 1.0.0
# Last Updated: 2026-02-04
#
# =============================================================================

version: "1.0.0"
provider: composite
entity: assay

# -----------------------------------------------------------------------------
# Input Filter
# -----------------------------------------------------------------------------
# No input filter for composite pipeline.
# Composite pipeline aggregates from seed pipeline internally.
input_filter:
  enabled: false

# -----------------------------------------------------------------------------
# Gold Filters
# -----------------------------------------------------------------------------
# Criteria for valid assays in Gold layer.
# Note: Composite uses qualified column names ({provider}.{entity}.{field})
# Filter rules apply to either qualified or coalesced column names.
gold_filters:
  # Required fields - records missing these are excluded from Gold
  required_fields:
    - assay_chembl_id      # Primary key from seed
    - assay_type           # Classification (required for analysis)

  # Field-specific validation (applied before Gold write)
  columns:
    # === Primary Key ===
    assay_chembl_id:
      type: string
      nullable: false
      pattern: "^CHEMBL\\d+$"
      description: "ChEMBL assay ID (primary key)"

    # === Foreign Keys (nullable) ===
    cell_chembl_id:
      type: string
      nullable: true
      pattern: "^CHEMBL\\d+$"
      description: "ChEMBL cell line ID (FK, ~70% null)"

    tissue_chembl_id:
      type: string
      nullable: true
      pattern: "^CHEMBL\\d+$"
      description: "ChEMBL tissue ID (FK, ~70% null)"

    target_chembl_id:
      type: string
      nullable: true
      pattern: "^CHEMBL\\d+$"
      description: "ChEMBL target ID (FK)"

    document_chembl_id:
      type: string
      nullable: true
      pattern: "^CHEMBL\\d+$"
      description: "ChEMBL document ID (FK)"

    # === Assay Classification ===
    assay_type:
      type: string
      nullable: false
      enum: ["B", "F", "A", "T", "P", "U"]
      description: "Assay type (B=Binding, F=Functional, A=ADMET, T=Toxicity, P=Physicochemical, U=Unknown)"

    assay_category:
      type: string
      nullable: true
      enum: ["screening", "confirmatory", "panel", "summary", "other"]
      description: "Assay category"

    assay_test_type:
      type: string
      nullable: true
      enum: ["In vivo", "In vitro", "Ex vivo"]
      description: "Assay test type"

    relationship_type:
      type: string
      nullable: true
      enum: ["D", "H", "M", "N", "S", "U"]
      description: "Assay-target relationship type"

    confidence_score:
      type: integer
      nullable: true
      min_value: 0
      max_value: 9
      description: "Target assignment confidence score (0-9)"

    # === Biological Context ===
    assay_taxonomy_id:
      type: integer
      nullable: true
      min_value: 1
      description: "NCBI Taxonomy ID for assay organism"

    # === BAO Ontology ===
    bao_format:
      type: string
      nullable: true
      pattern: "^BAO:\\d+$"
      description: "BioAssay Ontology format ID"

    # === Cell Line Fields (from enricher) ===
    cell_name:
      type: string
      nullable: true
      description: "Cell line name (e.g., HeLa, MCF7)"

    cell_source_taxonomy_id:
      type: integer
      nullable: true
      min_value: 1
      description: "Cell line source organism taxonomy ID"

    cellosaurus_id:
      type: string
      nullable: true
      pattern: "^CVCL_[A-Z0-9]+$"
      description: "Cellosaurus cross-reference ID"

    cell_efo_id:
      type: string
      nullable: true
      pattern: "^EFO_\\d+$"
      description: "Cell line EFO ID (renamed from efo_id)"

    clo_id:
      type: string
      nullable: true
      pattern: "^CLO_\\d+$"
      description: "Cell Line Ontology ID"

    # === Tissue Fields (from enricher) ===
    tissue_pref_name:
      type: string
      nullable: true
      description: "Tissue preferred name (renamed from pref_name)"

    tissue_efo_id:
      type: string
      nullable: true
      pattern: "^EFO_\\d+$"
      description: "Tissue EFO ID (renamed from efo_id)"

    tissue_uberon_id:
      type: string
      nullable: true
      description: "Uberon multi-species anatomy ontology ID"

    tissue_bto_id:
      type: string
      nullable: true
      description: "BRENDA Tissue Ontology ID"

    tissue_caloha_id:
      type: string
      nullable: true
      description: "CALIPHO tissue ontology ID"

    # === Variant Fields ===
    variant_taxonomy_id:
      type: integer
      nullable: true
      min_value: 1
      description: "Variant sequence taxonomy ID"

# -----------------------------------------------------------------------------
# DQ Thresholds (from composite config)
# -----------------------------------------------------------------------------
# These thresholds are applied during composite merge:
# - soft_fail_threshold: 0.10 (10% errors = warning)
# - hard_fail_threshold: 0.30 (30% errors = failure)
#
# Per-enricher overrides defined in composite config:
# - chembl_cell_line: soft=0.70, hard=0.95 (~70% assays lack cell line)
# - chembl_tissue: soft=0.70, hard=0.95 (~70% assays lack tissue)

# -----------------------------------------------------------------------------
# Notes on Join Semantics
# -----------------------------------------------------------------------------
# Assay -> CellLine join is M:N:
# - One assay has one cell_chembl_id (nullable FK)
# - One cell line can be used in many assays
# - ~70% of assays have NULL cell_chembl_id
#
# Assay -> Tissue join is M:N:
# - One assay has one tissue_chembl_id (nullable FK)
# - One tissue can be referenced by many assays
# - ~70% of assays have NULL tissue_chembl_id
#
# Merge uses left_outer to preserve all assays.
# Missing enricher fields will be null.

================================================================================
File: molecule.yaml
Path: filter\entities\composite\molecule.yaml
================================================================================
# configs/filter/entities/composite/molecule.yaml
# =============================================================================
# Composite Molecule Filter Configuration
# =============================================================================
# Entity-specific filter rules for composite molecule pipeline.
# Reference: ADR-028 (Filter Rules Externalization)
#
# Gold Contract: CompositeMoleculeGoldSchema
#
# Version: 1.0.0
# Last Updated: 2026-02-03
#
# =============================================================================

version: "1.0.0"
provider: composite
entity: molecule

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
# Criteria for valid molecules in Gold layer
# Note: Composite uses qualified column names ({provider}.{entity}.{field})
# Filter rules apply to either qualified or coalesced column names
gold_filters:
  # Required fields - records missing these are excluded from Gold
  required_fields:
    - molecule_chembl_id  # Primary key from seed (ChEMBL)

  # Field-specific validation (applied before Gold write)
  columns:
    molecule_chembl_id:
      type: string
      nullable: false
      pattern: "^CHEMBL\\d+$"
      description: "ChEMBL molecule identifier"

    inchi_key:
      type: string
      nullable: true
      pattern: "^[A-Z]{14}-[A-Z]{10}-[A-Z]$"
      description: "InChIKey - IUPAC standard structural identifier (27 chars)"

    inchikey:
      type: string
      nullable: true
      pattern: "^[A-Z]{14}-[A-Z]{10}-[A-Z]$"
      description: "InChIKey - PubChem field name (alias)"

    canonical_smiles:
      type: string
      nullable: true
      description: "Canonical SMILES representation"

    cid:
      type: string
      nullable: true
      pattern: "^\\d+$"
      description: "PubChem Compound ID"

    molecular_weight:
      type: float
      nullable: true
      min_value: 1.0
      max_value: 50000.0
      description: "Molecular weight in Daltons"

    xlogp:
      type: float
      nullable: true
      min_value: -20.0
      max_value: 30.0
      description: "XLogP (lipophilicity estimate)"

    tpsa:
      type: float
      nullable: true
      min_value: 0.0
      max_value: 2000.0
      description: "Topological Polar Surface Area"

    max_phase:
      type: float
      nullable: true
      min_value: -1.0
      max_value: 4.0
      description: "Maximum clinical phase reached (0-4, -1 for unknown)"

    pref_name:
      type: string
      nullable: true
      description: "Preferred compound name"

# -----------------------------------------------------------------------------
# DQ Thresholds (from composite config)
# -----------------------------------------------------------------------------
# These thresholds are applied during composite merge:
# - soft_fail_threshold: 0.10 (10% errors = warning)
# - hard_fail_threshold: 0.30 (30% errors = failure)
#
# Per-enricher overrides defined in composite config:
# - pubchem_compound: soft=0.20, hard=0.50
#   (PubChem may have many records without InChIKey match)

# -----------------------------------------------------------------------------
# Gold Contract Reference
# -----------------------------------------------------------------------------
# Required system fields (from CompositeMoleculeGoldSchema):
#   - entity_id (not null)
#   - content_hash (not null)
#   - _dq_warn (not null, bool)
#   - _dq_error (not null, bool)
#   - _run_id (not null)
#   - _run_type (not null)
#   - _ingestion_ts (not null)
#   - _index (not null)
#
# Required lineage fields (added by MergeService):
#   - _composite_run_id (not null)
#   - _source_providers (not null, JSON list)
#   - _enrichment_status (not null, JSON dict)
#   - _lineage_created_at (not null, ISO timestamp)
#
# Optional seed fields:
#   - _source (nullable)
#   - _source_batch_id (nullable)
#
# Business fields use qualified names:
#   - chembl.molecule.molecule_chembl_id (seed primary key)
#   - chembl.molecule.canonical_smiles, pubchem.compound.canonical_smiles, etc.
#   - Additional columns depend on enricher success

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
#
# Gold Contract: CompositePublicationGoldSchema
# JSON Schema: docs/contracts/gold/composite_publication_v1.0.json
#
# Version: 1.1.0
# Last Updated: 2026-01-27
#
# =============================================================================

version: "1.1.0"
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
# Criteria for valid publications in Gold layer
# Note: Composite uses qualified column names ({provider}.{entity}.{field})
# Filter rules apply to either qualified or coalesced column names
gold_filters:
  # Required fields - records missing these are excluded from Gold
  # Note: Title may appear as chembl.publication.title (qualified) or title (coalesced)
  required_fields:
    - title

  # Field-specific validation (applied before Gold write)
  # Note: Since composite has variable columns, only validate core fields
  columns: {}

# -----------------------------------------------------------------------------
# DQ Thresholds (from composite config)
# -----------------------------------------------------------------------------
# These thresholds are applied during composite merge:
# - soft_fail_threshold: 0.10 (10% errors = warning)
# - hard_fail_threshold: 0.30 (30% errors = failure)
#
# Per-enricher overrides defined in composite config:
# - semanticscholar_publication: soft=0.20, hard=0.50
# - pubmed_publication: soft=0.15, hard=0.40

# -----------------------------------------------------------------------------
# Gold Contract Reference
# -----------------------------------------------------------------------------
# Required system fields (from CompositePublicationGoldSchema):
#   - entity_id (not null)
#   - content_hash (not null)
#   - _dq_warn (not null, bool)
#   - _dq_error (not null, bool)
#   - _run_id (not null)
#   - _run_type (not null)
#   - _ingestion_ts (not null)
#   - _index (not null)
#
# Required lineage fields (added by MergeService):
#   - _composite_run_id (not null)
#   - _source_providers (not null, JSON list)
#   - _enrichment_status (not null, JSON dict)
#   - _lineage_created_at (not null, ISO timestamp)
#
# Optional seed fields:
#   - _source (nullable)
#   - _lookup_method (nullable)
#   - _original_id (nullable)
#   - _source_batch_id (nullable)
#
# Business fields use qualified names:
#   - chembl.publication.document_chembl_id (seed primary key)
#   - chembl.publication.title, crossref.publication.title, etc.
#   - Additional columns depend on enricher success

================================================================================
File: target.yaml
Path: filter\entities\composite\target.yaml
================================================================================
# configs/filter/entities/composite/target.yaml
# =============================================================================
# Composite Target Filter Configuration
# =============================================================================
# Entity-specific filter rules for composite target pipeline.
# Reference: ADR-028 (Filter Rules Externalization)
#
# Version: 1.0.0
# Last Updated: 2026-02-02
#
# =============================================================================

version: "1.0.0"
provider: composite
entity: target

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
# Criteria for valid targets in Gold layer
gold_filters:
  # Required fields - records missing these are excluded from Gold
  required_fields:
    - target_chembl_id  # Primary key
    - pref_name         # Target name (critical for usability)

  # Field-specific validation (applied before Gold write)
  columns:
    target_chembl_id:
      type: string
      nullable: false
      pattern: "^CHEMBL\\d+$"

    pref_name:
      type: string
      nullable: false
      min_length: 1

    target_type:
      type: string
      nullable: true

    uniprot_accession:
      type: string
      nullable: true
      pattern: "^[A-Z0-9]{6,10}$"

    mapping_status:
      type: enum
      nullable: true
      allowed: ["found", "not_found", "error"]

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
    # Standardized publication year filter (1950..2050 inclusive)
    publication_year:
      min: 1950
      max: 2050

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
    # Standardized publication year filter (1950..2050 inclusive)
    publication_year:
      min: 1950
      max: 2050

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
  # Numeric range filters
  ranges:
    # Standardized publication year filter (1950..2050 inclusive)
    publication_year:
      min: 1950
      max: 2050

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
    # Standardized publication year filter (1950..2050 inclusive)
    publication_year:
      min: 1950
      max: 2050

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
# =============================================================================
#
# Configuration Style Guide
# =============================================================================
#
# Two styles are supported. Choose based on your needs:
#
# 1. CONVENTION-BASED MINIMAL (Recommended for new configs)
#    Use when: Standard paths, no special overrides needed
#    Benefits: Less duplication, easier maintenance
#    Example:
#      pipeline_name: chembl_activity
#      provider: chembl
#      entity_type: activity
#      version: "1.2.0"
#      primary_keys: ["activity_id"]
#      silver_table: "chembl_activity"
#      gold_table: "chembl_activity"
#      # All paths auto-computed by convention
#
# 2. EXPLICIT FULL
#    Use when: Non-standard paths, complex DQ rules, special overrides
#    Benefits: Self-documenting, no hidden behavior
#    Example: See chembl/molecule.yaml, chembl/target.yaml
#
# 3. HYBRID (For special cases)
#    Use when: Mostly convention but need specific overrides
#    Example: pubmed/publication.yaml (explicit sink paths, convention DQ)
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

    # Flat structure mode (default: true)
    # Controls whether writer appends {provider}/{entity}/ to path:
    # - true:  {path}/{date}/batch_...  (path already includes provider/entity)
    # - false: {path}/{provider}/{entity}/{date}/batch_...
    # Default is true because all pipeline paths (both convention-based and explicit)
    # already include provider/entity segments per ADR-029.
    # Override to false only if path does NOT include provider/entity.
    flat_structure: true

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

    # Flat structure mode (default: true)
    # Controls whether writer appends table_name subdirectory to path:
    # - true:  Delta written directly to {path}/ (path already includes provider/entity)
    # - false: Delta written to {path}/{table_name}/
    # Default is true because all pipeline paths already include provider/entity per ADR-029.
    # CSV: {table_name}.csv at {path} (unchanged regardless of flat_structure)
    flat_structure: true

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

    # Flat structure mode (default: true)
    # Controls whether writer appends table_name subdirectory to path:
    # - true:  Delta written directly to {path}/ (path already includes provider/entity)
    # - false: Delta written to {path}/{table_name}/
    # Default is true because all pipeline paths already include provider/entity per ADR-029.
    # CSV: {table_name}.csv at {path} (unchanged regardless of flat_structure)
    flat_structure: true

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
data_schema_file: ../../data_schema/chembl/activity.yaml
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
# Sink Configuration (ADR-014, ADR-025)
# -----------------------------------------------------------------------------
sink:
  silver:
    primary_key: ["activity_id"]
    sort_by:
      columns: ["activity_id"]
  gold:
    sort_by:
      columns: ["activity_id"]

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
data_schema_file: ../../data_schema/chembl/assay.yaml
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
    primary_key: ["assay_chembl_id"]
    sort_by:
      columns: ["assay_chembl_id"]
    partition_by: ["assay_type"]
  gold:
    sort_by:
      columns: ["assay_chembl_id"]

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
data_schema_file: ../../data_schema/chembl/assay_parameters.yaml

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
data_schema_file: ../../data_schema/chembl/cell_line.yaml

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
data_schema_file: ../../data_schema/chembl/compound_record.yaml

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
data_schema_file: ../../data_schema/chembl/molecule.yaml

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
data_schema_file: ../../data_schema/chembl/protein_class.yaml

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

source:
  batch_size: 16

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

# -----------------------------------------------------------------------------
# Data Schema Configuration (Column Ordering)
# -----------------------------------------------------------------------------
# Use data_schema_file for layer-specific column configuration (silver/gold).
# Falls back to column_groups_file if data_schema_file not specified.
data_schema_file: ../../data_schema/chembl/publication.yaml

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
data_schema_file: ../../data_schema/chembl/publication_similarity.yaml

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
data_schema_file: ../../data_schema/chembl/publication_term.yaml

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
File: subcellular_fraction.yaml
Path: pipelines\chembl\subcellular_fraction.yaml
================================================================================
# configs/pipelines/chembl/subcellular_fraction.yaml
# Pipeline configuration for ChEMBL Subcellular Fraction entity.
#
# Derived entity: Extracts unique subcellular fractions from Assay records.
# Creates a lookup/reference table for biological context normalization.
# Inherits defaults from ../_base.yaml
# Note: entity_type=subcellular_fraction maps to ChEMBL API /assay endpoint (derived entity)

pipeline_name: chembl_subcellular_fraction
provider: chembl
entity_type: subcellular_fraction
version: "1.0.0"
description: "Extract unique subcellular fractions from ChEMBL Assay records"

# Loading strategy (ADR-030, ADR-031)
# Derived entity requires full scan to ensure comprehensive deduplication.
# Deduplication is handled both at DataSource level and on Silver layer via content_hash.
force_full_scan: true
loading_strategy: full_scan_only

# Primary key is the normalized subcellular_fraction name
# entity_id is generated as SHA256 hash of normalized name
primary_keys: ["entity_id"]
silver_table: "chembl_subcellular_fraction"
gold_table: "chembl_subcellular_fraction"

source_file: ../../sources/chembl.yaml

# -----------------------------------------------------------------------------
# Data Quality Configuration (ADR-027)
# -----------------------------------------------------------------------------
# DQ rules are loaded from hierarchical config files:
#   1. configs/dq/_defaults.yaml (global defaults)
#   2. configs/dq/providers/chembl.yaml (provider-specific)
#   3. configs/dq/entities/chembl/subcellular_fraction.yaml (entity-specific)
dq_config_file: ../../dq/entities/chembl/subcellular_fraction.yaml

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filters loaded from hierarchical config files via convention (ADR-029):
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/chembl.yaml (provider-specific)
#   3. configs/filter/entities/chembl/subcellular_fraction.yaml (entity-specific)
filter_config_file: ../../filter/entities/chembl/subcellular_fraction.yaml
data_schema_file: ../../data_schema/chembl/subcellular_fraction.yaml

# Entity-specific sink overrides
sink:
  bronze:
    path: "data/output/bronze/chembl/subcellular_fraction"
  silver:
    path: "data/output/silver/chembl/subcellular_fraction"
    primary_key: ["entity_id"]
    sort_by:
      columns: ["subcellular_fraction"]
      ascending: true
    csv_export:
      path: "data/output/silver/chembl/subcellular_fraction"
  gold:
    path: "data/output/gold/chembl/subcellular_fraction"
    sort_by:
      columns: ["subcellular_fraction"]
      ascending: true
    csv_export:
      path: "data/output/gold/chembl/subcellular_fraction"

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
data_schema_file: ../../data_schema/chembl/target.yaml

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
data_schema_file: ../../data_schema/chembl/target_component.yaml

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
File: tissue.yaml
Path: pipelines\chembl\tissue.yaml
================================================================================
# configs/pipelines/chembl/tissue.yaml
# Pipeline configuration for ChEMBL Tissue entity.
#
# Inherits defaults from ../_base.yaml

pipeline_name: chembl_tissue
provider: chembl
entity_type: tissue
version: "1.0.0"
description: "Extract tissues from ChEMBL API"

primary_keys: ["tissue_chembl_id"]
silver_table: "chembl_tissue"
gold_table: "chembl_tissue"

source_file: ../../sources/chembl.yaml

# -----------------------------------------------------------------------------
# Data Quality Configuration (ADR-027)
# -----------------------------------------------------------------------------
dq_config_file: ../../dq/entities/chembl/tissue.yaml
data_schema_file: ../../data_schema/chembl/tissue.yaml

# Entity-specific sink overrides
sink:
  bronze:
    path: "data/output/bronze/chembl/tissue"
  silver:
    path: "data/output/silver/chembl/tissue"
    primary_key: ["tissue_chembl_id"]
    sort_by:
      columns: ["tissue_chembl_id"]
      ascending: true
    csv_export:
      path: "data/output/silver/chembl/tissue"
  gold:
    path: "data/output/gold/chembl/tissue"
    sort_by:
      columns: ["tissue_chembl_id", "pref_name"]
      ascending: true
    csv_export:
      path: "data/output/gold/chembl/tissue"

================================================================================
File: activity.yaml
Path: pipelines\composite\activity.yaml
================================================================================
# configs/pipelines/composite/activity.yaml
# =============================================================================
# Composite Activity Pipeline Configuration
# =============================================================================
#
# Combines bioactivity data from ChEMBL with compound record metadata:
# - Seed: ChEMBL activities (activity_id, molecule_chembl_id, ...)
# - Dependencies:
#   1. chembl_compound_record: compound records filtered by
#      molecule_chembl_id AND document_chembl_id (dual-key enrichment)
#
# This pipeline enables correlation of activity measurements with their
# original compound names and document references from compound records.
#
# Join Strategy:
# - Composite key: (molecule_chembl_id, document_chembl_id)
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
  # Its output provides join keys (molecule_chembl_id, document_chembl_id)
  # for dependency dual-key filtering and composite join.
  seed:
    pipeline: chembl_activity
    output_keys:
      - activity_id           # Primary key
      - molecule_chembl_id    # FK for compound_record join (key 1)
      - assay_chembl_id       # FK for future assay enrichment
      - target_chembl_id      # FK for future target enrichment
      - document_chembl_id    # FK for compound_record join (key 2)
    silver_table: silver/chembl/activity

  # ---------------------------------------------------------------------------
  # Dependency Pipelines (sequential execution)
  # ---------------------------------------------------------------------------
  # compound_record is a dependency (not enricher) because:
  # 1. It requires API calls (not just Silver table lookup)
  # 2. It should be filtered by molecule_chembl_id AND document_chembl_id
  # 3. It must complete before any merge can occur
  dependencies:
    # ChEMBL Compound Record: original compound names from publications
    # Fetches compound records filtered by BOTH molecule_chembl_id AND
    # document_chembl_id from seed (dual-key enrichment).
    # API call: /compound_record?molecule_chembl_id__in=...&document_chembl_id__in=...
    # This produces ~1:1 mapping (one record per molecule-document pair).
    - pipeline: chembl_compound_record
      join_keys:
        - molecule_chembl_id   # Composite join key 1
        - document_chembl_id   # Composite join key 2
      filter_fields:           # Multi-field API filtering (AND logic)
        - molecule_chembl_id
        - document_chembl_id
      required: false          # Optional - missing records don't block composite
      timeout_seconds: 600
      silver_table: silver/chembl/compound_record

  # ---------------------------------------------------------------------------
  # Enricher Pipelines
  # ---------------------------------------------------------------------------
  # Currently empty. Future expansion could include:
  # - PubChem compound properties (via molecule_chembl_id → inchikey → PubChem)
  # - UniProt target data (via target_chembl_id → UniProt accession)
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
    # molecule_chembl_id appears in both sources, keep both for lineage
    preserve_all_sources: false

    # Output paths for merged data
    output:
      silver: data/output/silver/composite/activity
      gold: data/output/gold/composite/activity

    # Field-level priority for overlapping fields
    field_priorities:
      molecule_chembl_id:
        - chembl.activity     # Activity FK is authoritative
      document_chembl_id:
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
          - molecule_chembl_id
          - assay_chembl_id
          - target_chembl_id
          - document_chembl_id
          - record_id
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
          - parent_molecule_chembl_id
        provider_order: [chembl]

      # === Target context (denormalized from activity) ===
      - name: target_context
        fields:
          - target_pref_name
          - target_organism
          - target_taxonomy_id
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
  dq_rules:
    # Composite-level thresholds (applied to merge result)
    soft_fail_threshold: 0.10  # 10% errors = warning
    hard_fail_threshold: 0.30  # 30% errors = failure

    # Per-dependency threshold overrides
    enricher_overrides:
      # compound_record may not exist for all molecules
      chembl_compound_record:
        soft_fail_threshold: 0.30  # 30% missing is acceptable
        hard_fail_threshold: 0.70  # Only fail if >70% errors

    # Required fields in final Gold output
    required_fields:
      - activity_id
      - molecule_chembl_id
      - assay_chembl_id

    # Field-level validation rules
    field_validations:
      activity_id:
        type: string
        nullable: false
        description: "ChEMBL activity ID (primary key)"

      molecule_chembl_id:
        type: string
        nullable: false
        pattern: "^CHEMBL\\d+$"
        description: "ChEMBL molecule ID (FK)"

      assay_chembl_id:
        type: string
        nullable: false
        pattern: "^CHEMBL\\d+$"
        description: "ChEMBL assay ID (FK)"

      target_chembl_id:
        type: string
        nullable: true
        pattern: "^CHEMBL\\d+$"
        description: "ChEMBL target ID (FK, optional)"

      standard_value:
        type: float
        nullable: true
        min_value: 0
        description: "Standardized activity value (non-negative)"

      pchembl_value:
        type: float
        nullable: true
        min_value: 0
        max_value: 14
        description: "-log10 molar activity (0-14 range)"

      record_id:
        type: integer
        nullable: true
        min_value: 1
        description: "Compound record ID (from dependency)"

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
      - molecule_chembl_id
      - document_chembl_id
      - src_id

# -----------------------------------------------------------------------------
# Gold Filters (applied to merged output)
# -----------------------------------------------------------------------------
gold_filters:
  # Only include activities with required keys
  required_fields:
    - activity_id
    - molecule_chembl_id
    - assay_chembl_id

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filter rules are loaded from hierarchical config files:
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/composite.yaml (provider-specific)
#   3. configs/filter/entities/composite/activity.yaml (entity-specific)
filter_config_file: ../../filter/entities/composite/activity.yaml

================================================================================
File: assay.yaml
Path: pipelines\composite\assay.yaml
================================================================================
# configs/pipelines/composite/assay.yaml
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
      - assay_chembl_id      # Primary key
      - cell_chembl_id       # FK for cell_line enrichment (nullable)
      - tissue_chembl_id     # FK for tissue enrichment (nullable)
      - target_chembl_id     # FK to target (for context)
      - document_chembl_id   # FK to document (for context)
      - assay_type           # Classification
      - description          # For logging/debugging
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
        - cell_chembl_id       # Direct FK match
      required: false          # Many assays lack cell line (~70%)
      filter_condition: "cell_chembl_id IS NOT NULL"
      timeout_seconds: 300
      silver_table: silver/chembl/cell_line

    # ChEMBL Tissue: tissue context metadata
    # Provides: pref_name (tissue_name), uberon_id, bto_id, efo_id, etc.
    # Cardinality: one_to_one (each assay FK points to at most one tissue)
    - pipeline: chembl_tissue
      join_keys:
        - tissue_chembl_id     # Direct FK match
      required: false          # Many assays lack tissue (~70%)
      filter_condition: "tissue_chembl_id IS NOT NULL"
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

    # Field-level priority overrides
    field_priorities:
      # FKs from seed are authoritative (prevent enricher overwrite)
      cell_chembl_id:
        - chembl.assay
      tissue_chembl_id:
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
          - assay_chembl_id
          - cell_chembl_id
          - tissue_chembl_id
          - target_chembl_id
          - document_chembl_id
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
      - chembl.cell_line.cell_chembl_id
      # Exclude tissue PK (already have FK in seed)
      - chembl.tissue.tissue_chembl_id

  # ---------------------------------------------------------------------------
  # Data Quality Configuration
  # ---------------------------------------------------------------------------
  dq_rules:
    soft_fail_threshold: 0.10   # 10% errors = warning
    hard_fail_threshold: 0.30   # 30% errors = failure

    # Per-enricher threshold overrides (lenient - many nulls expected)
    enricher_overrides:
      chembl_cell_line:
        soft_fail_threshold: 0.70   # ~70% assays lack cell line
        hard_fail_threshold: 0.95
      chembl_tissue:
        soft_fail_threshold: 0.70   # ~70% assays lack tissue
        hard_fail_threshold: 0.95

    # Required fields in final Gold output
    required_fields:
      - assay_chembl_id
      - assay_type

    # Field-level validation rules
    field_validations:
      assay_chembl_id:
        type: string
        nullable: false
        pattern: "^CHEMBL\\d+$"
        description: "ChEMBL assay ID (primary key)"

      cell_chembl_id:
        type: string
        nullable: true
        pattern: "^CHEMBL\\d+$"
        description: "FK to cell_line (nullable)"

      tissue_chembl_id:
        type: string
        nullable: true
        pattern: "^CHEMBL\\d+$"
        description: "FK to tissue (nullable)"

      target_chembl_id:
        type: string
        nullable: true
        pattern: "^CHEMBL\\d+$"
        description: "FK to target"

      assay_type:
        type: string
        nullable: false
        allowed: ["B", "F", "A", "T", "P", "U"]
        description: "Assay type classification"

      confidence_score:
        type: integer
        nullable: true
        min_value: 0
        max_value: 9
        description: "Target confidence score (0-9)"

      assay_taxonomy_id:
        type: integer
        nullable: true
        min_value: 1
        description: "NCBI Taxonomy ID"

      cell_source_taxonomy_id:
        type: integer
        nullable: true
        min_value: 1
        description: "Cell line source organism taxonomy ID"

      bao_format:
        type: string
        nullable: true
        pattern: "^BAO:\\d+$"
        description: "BioAssay Ontology format ID"

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
# Gold Filters (applied to merged output)
# -----------------------------------------------------------------------------
gold_filters:
  required_fields:
    - assay_chembl_id
    - assay_type

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
filter_config_file: ../../filter/entities/composite/assay.yaml

================================================================================
File: molecule.yaml
Path: pipelines\composite\molecule.yaml
================================================================================
# configs/pipelines/composite/molecule.yaml
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
  # Its output provides join keys (inchikey, canonical_smiles) for enrichment.
  seed:
    pipeline: chembl_molecule
    output_keys:
      - molecule_chembl_id  # Primary key
      - inchikey            # Join key 1 (IUPAC standard, preferred)
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
        - inchikey           # Primary join key (IUPAC standard) - uses seed field name
        - canonical_smiles   # Fallback key (less reliable)
      required: false        # Graceful degradation - seed data preserved on failure
      filter_condition: "inchikey IS NOT NULL"  # Only join records with structure
      timeout_seconds: 3600
      silver_table: silver/pubchem/compound

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

    # Field-level priority overrides
    # Maps field name to ordered list of source preferences
    field_priorities:
      # === Structural Identifiers (ChEMBL authoritative) ===
      # ChEMBL has curated structures from medicinal chemistry literature
      canonical_smiles:
        - chembl           # ChEMBL structures are manually curated
        - pubchem
      inchikey:
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
      xlogp:
        - pubchem          # PubChem uses XLogP3
        - chembl           # ChEMBL uses ALogP
      tpsa:
        - pubchem          # PubChem TPSA (Topological Polar Surface Area)
        - chembl           # ChEMBL PSA
      hba:
        - pubchem          # H-bond acceptors
        - chembl
      hbd:
        - pubchem          # H-bond donors
        - chembl
      rotatable_bonds:
        - pubchem
        - chembl
      heavy_atom_count:
        - pubchem
        - chembl
      aromatic_rings:
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
          - molecule_chembl_id   # ChEMBL primary key
          - cid                  # PubChem CID
          - inchikey             # Standard InChIKey (both ChEMBL and PubChem)
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
          - property_full_mwt
          - property_mw_freebase
          - property_alogp
          - xlogp
          - property_psa
          - tpsa
          - property_hba
          - hba
          - property_hbd
          - hbd
          - property_rtb
          - rotatable_bonds
          - property_heavy_atoms
          - heavy_atom_count
          - property_aromatic_rings
          - aromatic_rings
          - property_qed_weighted
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
  dq_rules:
    # Composite-level thresholds (applied to merge result)
    soft_fail_threshold: 0.10  # 10% errors = warning
    hard_fail_threshold: 0.30  # 30% errors = failure

    # Per-enricher threshold overrides
    enricher_overrides:
      # PubChem may have many records without InChIKey match
      pubchem_compound:
        soft_fail_threshold: 0.20
        hard_fail_threshold: 0.50

    # Required fields in final Gold output
    required_fields:
      - molecule_chembl_id
      - entity_id

    # Field-level validation rules
    field_validations:
      # === Structural Identifiers ===
      inchikey:
        type: string
        nullable: true
        pattern: "^[A-Z]{14}-[A-Z]{10}-[A-Z]$"
        description: "InChIKey (27 characters, XXXXX-YYYYY-Z format)"

      canonical_smiles:
        type: string
        nullable: true
        description: "Canonical SMILES representation"

      # === Numeric Properties ===
      molecular_weight:
        type: float
        nullable: true
        min_value: 1.0
        max_value: 50000.0
        description: "Molecular weight in Daltons"

      xlogp:
        type: float
        nullable: true
        min_value: -20.0
        max_value: 30.0
        description: "XLogP (lipophilicity estimate)"

      tpsa:
        type: float
        nullable: true
        min_value: 0.0
        max_value: 2000.0
        description: "Topological Polar Surface Area"

      # === Clinical Data ===
      max_phase:
        type: float
        nullable: true
        description: "Maximum clinical phase reached (0-4)"

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
      - inchikey
      - molecular_weight
      - xlogp
      - tpsa
      - hba
      - hbd

# -----------------------------------------------------------------------------
# Gold Filters (applied to merged output)
# -----------------------------------------------------------------------------
gold_filters:
  # Only include molecules with primary key
  required_fields:
    - molecule_chembl_id

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filter rules loaded from hierarchical config files
filter_config_file: ../../filter/entities/composite/molecule.yaml

# -----------------------------------------------------------------------------
# Maintenance Configuration
# -----------------------------------------------------------------------------

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
# See config/data_schema/composite/publication.yaml for complete field mappings.
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
      timeout_seconds: 3600
      silver_table: silver/crossref/publication

    # OpenAlex: Academic topics and institutions
    # OPTIONAL: Failure logged, composite continues
    - pipeline: openalex_publication
      join_keys:
        - doi            # Primary key
        - title          # Fallback key if doi not found
      required: false    # Optional - needs doi or pmid
      filter_condition: "doi IS NOT NULL OR pmid IS NOT NULL"
      timeout_seconds: 3600
      silver_table: silver/openalex/publication

    # PubMed: MeSH terms and medical metadata
    # OPTIONAL: Only processes records with pmid
    - pipeline: pubmed_publication
      join_keys:
        - pmid           # PubMed-specific identifier
        - doi
      required: false    # Optional - only for records with pmid
      filter_condition: "pmid IS NOT NULL"
      timeout_seconds: 3600
      silver_table: silver/pubmed/publication

    # Semantic Scholar: AI/ML embeddings and TLDR (mapped to abstract)
    # OPTIONAL: Higher rate limits, ok to skip
    - pipeline: semanticscholar_publication
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

    # Output paths for merged data
    output:
      silver: data/output/silver/composite/publication
      gold: data/output/gold/composite/publication

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
    # Categories and field order follow docs/schemas/publication_field_order.csv
    # (6 canonical categories, 167 fully-qualified fields).
    #
    # The "system" group MUST be first: it captures ETL metadata columns
    # (entity_id, content_hash, _run_id, etc.) that would otherwise fall
    # into the "remaining" bucket at the end of the output.
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
        provider_order: [chembl, crossref, openalex, pubmed, semanticscholar]

      # === Provider identifiers ===
      - name: provider_ids
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
          - src_id
        provider_order: [semanticscholar, openalex, pubmed, chembl, crossref]

      # === Journal / Venue information ===
      - name: journal
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
          - publisher
          - title
          - venue
          - volume
        provider_order: [pubmed, semanticscholar, chembl, crossref, openalex]

      # === Pagination ===
      - name: pagination
        fields:
          - medline_pgn
          - page_first
          - page_last
          - page_range
        provider_order: [pubmed, chembl, crossref, openalex, semanticscholar]

      # === Authors ===
      - name: authors
        fields:
          - author_count
          - author_details
          - author_h_indices
          - author_openalex_ids
          - author_orcids
          - author_s2_ids
          - authors
          - authors_with_affiliations
        provider_order: [pubmed, semanticscholar, openalex, chembl, crossref]

      # === Affiliations ===
      - name: affiliations
        fields:
          - affiliation_list
          - affiliation_structured
          - institution_country_codes
          - institution_ids
          - ror_ids
          - country
        provider_order: [pubmed, openalex, semanticscholar, chembl, crossref]

      # === Date ===
      - name: date
        fields:
          - creation_date
          - date_completed
          - date_revised
          - pub_date
          - pub_day
          - pub_month
          - publication_date
          - publication_year
        provider_order: [chembl, crossref, openalex, pubmed, semanticscholar]

      # === Subjects / Topics ===
      - name: subjects
        fields:
          - keyword_count
          - mesh_heading_count
          - primary_topic
          - subject_fields
          - subject_keywords
          - subject_mesh
          - subject_topics
          - tldr
        provider_order: [pubmed, openalex, semanticscholar, crossref, chembl]

      # === Biomedical (NEW) ===
      - name: biomedical
        fields:
          - chemicals
          - chemical_count
          - gene_symbols
          - databanks
          - grants
          - grant_count
        provider_order: [pubmed, openalex, chembl]

      # === Citations / Metrics ===
      - name: citations
        fields:
          - citation_contexts
          - citation_subset
          - citations_made
          - citations_received
          - fwci
          - influential_citation_count
          - references
        provider_order: [semanticscholar, crossref, openalex, pubmed, chembl]

      # === Document type and status ===
      - name: doc_type
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
        provider_order: [semanticscholar, pubmed, chembl, crossref, openalex]

    # Note: output paths auto-computed per ADR-029 convention-based resolution
    # silver: data/output/silver/composite/publication (auto)
    # gold: data/output/gold/composite/publication (auto)

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

    # Field-level validation rules for new fields
    field_validations:
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
# Filter rules are loaded from hierarchical config files:
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/composite.yaml (provider-specific)
#   3. configs/filter/entities/composite/publication.yaml (entity-specific)
filter_config_file: ../../filter/entities/composite/publication.yaml

# -----------------------------------------------------------------------------
# Maintenance Configuration
# -----------------------------------------------------------------------------

================================================================================
File: target.yaml
Path: pipelines\composite\target.yaml
================================================================================
# configs/pipelines/composite/target.yaml
# =============================================================================
# Composite Target Pipeline Configuration
# =============================================================================
#
# Combines biological target data from multiple sources:
# - Seed: ChEMBL targets (target_chembl_id, target_type, pref_name, ...)
# - Dependencies (ordered, chained):
#   1. chembl_target_component: fetches component data using component_id from seed
#   2. chembl_protein_class: fetches protein classifications using
#      protein_classification_id from target_component Silver table (chained dep)
#   3. uniprot_idmapping: maps ChEMBL target IDs to UniProt accessions
#   4. uniprot_protein: fetches detailed protein data using uniprot_accession
#      from idmapping Silver table (chained dep)
#
# Dependency chaining (key_source):
# - chembl_target_component uses component_id from seed (standard)
# - chembl_protein_class uses protein_classification_id from target_component
#   Silver table via key_source field (chained dependency)
# - uniprot_idmapping uses target_chembl_id from seed (standard)
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
  # Its output provides join keys (target_chembl_id) for enrichment.
  seed:
    pipeline: chembl_target
    output_keys:
      - target_chembl_id  # ChEMBL target ID (primary key, join key for idmapping)
      - component_id      # Primary component ID (join key for target_component)
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
  # 1. chembl_target_component runs first (uses component_id from seed)
  # 2. chembl_protein_class runs second (uses protein_classification_id from
  #    target_component Silver table via key_source)
  # 3. uniprot_idmapping runs third (uses target_chembl_id from seed)
  # 4. uniprot_protein runs fourth (uses uniprot_accession from idmapping
  #    Silver table via key_source - CHAINED)
  dependencies:
    # ChEMBL Target Component: detailed per-component data
    # Fetches protein_classifications, xrefs for each component.
    # Uses component_id from seed to filter API requests.
    - pipeline: chembl_target_component
      join_keys:
        - component_id      # Scalar join key from seed (int)
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
    - pipeline: uniprot_idmapping
      join_keys:
        - target_chembl_id  # Direct join key from seed
      required: false       # Optional - many targets lack UniProt accessions
      filter_condition: "target_chembl_id IS NOT NULL"
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

    # Output paths for merged data
    output:
      silver: data/output/silver/composite/target
      gold: data/output/gold/composite/target

    # Field-level priority for overlapping fields
    # seed_priority applies globally; these are explicit overrides per field.
    field_priorities:
      target_chembl_id:
        - chembl  # Seed is authoritative for PK
      component_id:
        - chembl  # Seed component_id (from component_ids[0]) is authoritative
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
          - target_chembl_id
          - component_id
          - dap_id
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
          - target_constraints
        provider_order: [chembl]

    # Fields excluded from merged output (Silver + Gold)
    exclude_fields:
      # --- ChEMBL target exclusions ---
      - chembl.target.target_components
      - chembl.target.cross_references
      # --- ChEMBL target_component exclusions ---
      - chembl.target_component.accession
      - chembl.target_component.component_id
      - chembl.target_component.component_type
      - chembl.target_component.description
      - chembl.target_component.organism
      - chembl.target_component.protein_classifications
      - chembl.target_component.taxonomy_id
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
      - uniprot.idmapping.target_chembl_id
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
  dq_rules:
    # Composite-level thresholds (applied to merge result)
    soft_fail_threshold: 0.10  # 10% errors = warning
    hard_fail_threshold: 0.30  # 30% errors = failure

    # Per-dependency threshold overrides
    enricher_overrides:
      # Many non-protein targets -> UniProt mapping_status="not_found" is expected
      uniprot_idmapping:
        soft_fail_threshold: 0.30  # 30% not_found is acceptable
        hard_fail_threshold: 0.80  # Only fail if >80% errors
      # UniProt protein: chained from idmapping, some accessions may not resolve
      uniprot_protein:
        soft_fail_threshold: 0.20  # 20% missing is acceptable
        hard_fail_threshold: 0.60  # Only fail if >60% errors

    # Required fields in final Gold output
    required_fields:
      - target_chembl_id
      - pref_name

    # Field-level validation rules
    field_validations:
      target_chembl_id:
        type: string
        nullable: false
        pattern: "^CHEMBL\\d+$"
        description: "ChEMBL target ID (primary key)"

      uniprot_accession:
        type: string
        nullable: true
        pattern: "^[A-Z0-9]{6,10}$"
        description: "UniProt accession (null if not_found)"

      mapping_status:
        type: enum
        nullable: true
        allowed: ["found", "not_found", "error"]
        description: "UniProt ID mapping resolution status"

      target_type:
        type: string
        nullable: true
        description: "Target classification (SINGLE PROTEIN, ORGANISM, etc.)"

      taxonomy_id:
        type: integer
        nullable: true
        min_value: 1
        description: "NCBI Taxonomy ID"

      function_comment:
        type: string
        nullable: true
        description: "Functional description from UniProt FUNCTION comment"

      go_terms:
        type: string
        nullable: true
        description: "Gene Ontology terms (JSON-serialized list)"

      disease_involvement:
        type: string
        nullable: true
        description: "Disease associations from UniProt DISEASE comment"

      subcellular_location:
        type: string
        nullable: true
        description: "Subcellular localization from UniProt"

      annotation_score:
        type: integer
        nullable: true
        min_value: 1
        max_value: 5
        description: "UniProt annotation score (1-5)"

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
      - target_chembl_id  # Overlapping field between seed and idmapping
      - component_id      # Overlapping field between seed and target_component
      - taxonomy_id       # Overlapping between ChEMBL and UniProt
      - organism          # Overlapping between ChEMBL and UniProt

# -----------------------------------------------------------------------------
# Gold Filters (applied to merged output)
# -----------------------------------------------------------------------------
gold_filters:
  # Only include targets with primary key and name
  required_fields:
    - target_chembl_id
    - pref_name

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filter rules are loaded from hierarchical config files:
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/composite.yaml (provider-specific)
#   3. configs/filter/entities/composite/target.yaml (entity-specific)
filter_config_file: ../../filter/entities/composite/target.yaml

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
# Data Schema Configuration (Column Ordering)
# -----------------------------------------------------------------------------
# Use data_schema_file for layer-specific column configuration (silver/gold).
data_schema_file: ../../data_schema/crossref/publication.yaml

# -----------------------------------------------------------------------------
# Filter Configuration (ADR-028)
# -----------------------------------------------------------------------------
# Filters loaded from hierarchical config files via convention (ADR-029):
#   1. configs/filter/_defaults.yaml (global defaults)
#   2. configs/filter/providers/crossref.yaml (provider-specific)
#   3. configs/filter/entities/crossref/publication.yaml (entity-specific)
# Explicit path needed because entity_type is 'work' (CrossRef API term)
# but filter file uses project entity name 'publication'.
filter_config_file: ../../filter/entities/crossref/publication.yaml
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
# Data Schema Configuration (Column Ordering)
# -----------------------------------------------------------------------------
# Use data_schema_file for layer-specific column configuration (silver/gold).
data_schema_file: ../../data_schema/openalex/publication.yaml

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
data_schema_file: ../../data_schema/pubchem/compound.yaml

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
  email: "${BIOETL_PUBMED_EMAIL}"
  api_key: "${BIOETL_PUBMED_API_KEY}"

# -----------------------------------------------------------------------------
# Data Schema Configuration (Column Ordering)
# -----------------------------------------------------------------------------
# Use data_schema_file for layer-specific column configuration (silver/gold).
data_schema_file: ../../data_schema/pubmed/publication.yaml

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
    primary_key: ["pmid"]
    sort_by:
      columns: ["pmid"]
    partition_by: ["pub_year"]
    csv_export:
      path: "data/output/silver/pubmed/publication"
    flat_structure: true
  gold:
    path: "data/output/gold/pubmed/publication"
    sort_by:
      columns: ["pmid"]
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
# Data Schema Configuration (Column Ordering)
# -----------------------------------------------------------------------------
# Use data_schema_file for layer-specific column configuration (silver/gold).
data_schema_file: ../../data_schema/semanticscholar/publication.yaml

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
data_schema_file: ../../data_schema/uniprot/idmapping.yaml

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
data_schema_file: ../../data_schema/uniprot/protein.yaml
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
    primary_key: ["accession"]
    sort_by:
      columns: ["accession"]
    partition_by: ["organism"]
  gold:
    sort_by:
      columns: ["accession"]

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
    batch_size: 10
    provider_config:
        provider: chembl
        base_url: https://www.ebi.ac.uk/chembl/api/data
        auth_type: public  # No authentication required
        client:
            timeout_sec: 60.0
            max_retries: 3
        max_url_length: 2000
        batch_size: 10
        page_size: 100  # Minimum allowed by schema (ge=100)
        api_version: null

    circuit_breaker:
        failure_threshold: 5
        recovery_timeout: 300

    # ChEMBL has no official rate limit but recommends reasonable usage.
    # Conservative defaults to be a good API citizen.
    rate_limit:
        requests_per_second: 3
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
        api_key_env: BIOETL_PUBMED_API_KEY
        email_env: BIOETL_PUBMED_EMAIL  # Required by NCBI guidelines
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
            timeout_sec: 60.0          # Increased timeout for slow responses
            max_retries: 5             # More retries for 429 recovery
            retry_base_delay: 30.0     # 30s initial delay for rate limit cooldown
            retry_max_delay: 300.0     # 5 min max delay between retries
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
