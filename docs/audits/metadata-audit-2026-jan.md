# Metadata Audit: BioETL Pipelines

Generated on: Thu Jan 22 12:41:17 UTC 2026

## Executive Summary

Total Pipelines: 19


## Table of Contents
- [CHEMBL / activity: chembl_activity](#chembl-activity)
- [CHEMBL / assay: chembl_assay](#chembl-assay)
- [CHEMBL / assay_parameters: chembl_assay_parameters](#chembl-assay_parameters)
- [CHEMBL / cell_line: chembl_cell_line](#chembl-cell_line)
- [CHEMBL / compound_record: chembl_compound_record](#chembl-compound_record)
- [CHEMBL / document: chembl_publication](#chembl-document)
- [CHEMBL / document_similarity: chembl_publication_similarity](#chembl-document_similarity)
- [CHEMBL / document_term: chembl_publication_term](#chembl-document_term)
- [CHEMBL / molecule: chembl_molecule](#chembl-molecule)
- [CHEMBL / protein_class: chembl_protein_class](#chembl-protein_class)
- [CHEMBL / target: chembl_target](#chembl-target)
- [CHEMBL / target_component: chembl_target_component](#chembl-target_component)
- [CROSSREF / work: crossref_publication](#crossref-work)
- [OPENALEX / publication: openalex_publication](#openalex-publication)
- [PUBCHEM / compound: pubchem_compound](#pubchem-compound)
- [PUBMED / publication: pubmed_publication](#pubmed-publication)
- [SEMANTICSCHOLAR / publication: semanticscholar_publication](#semanticscholar-publication)
- [UNIPROT / idmapping: uniprot_idmapping](#uniprot-idmapping)
- [UNIPROT / protein: uniprot_protein](#uniprot-protein)

---

## CHEMBL / activity: chembl_activity <a name='chembl-activity'></a>

- **Config**: `configs/pipelines/chembl/activity.yaml`
- **Schema Class**: `ActivitySchema`

### Field Specifications (Silver/Gold)

| Field | Type | Nullable | Description | Constraints |
|---|---|---|---|---|
| `entity_id` | `str` | False | Unique business identifier for the entity. | - |
| `content_hash` | `str` | False | SHA256 hash of canonical record representation (64 hex chars). | <Check str_matches: str_matches('^[a-f0-9]{64}$')> |
| `_run_id` | `object` | False | Correlation ID for the pipeline run. | - |
| `_run_type` | `str` | False | Type of pipeline run. | <Check isin: isin(['incremental', 'backfill', 'rebuild'])> |
| `_source_batch_id` | `object` | True | Batch context ID from the source. | - |
| `_ingestion_ts` | `str` | False | Timestamp when the record was ingested (UTC, ISO 8601 format). | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$')> |
| `_dq_warn` | `bool` | False | Flag for data quality warnings. | - |
| `_dq_error` | `bool` | False | Flag for data quality errors. | - |
| `_index` | `int64` | False | Sequential index of the record in the pipeline run. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `activity_id` | `str` | False | Primary key. | - |
| `assay_chembl_id` | `str` | False | Foreign key to assay. | <Check str_matches: str_matches('^CHEMBL\d+$')> |
| `molecule_chembl_id` | `str` | False | Foreign key to molecule. | <Check str_matches: str_matches('^CHEMBL\d+$')> |
| `target_chembl_id` | `str` | True | Foreign key to target. | <Check str_matches: str_matches('^CHEMBL\d+$')> |
| `document_chembl_id` | `str` | True | Foreign key to document. | <Check str_matches: str_matches('^CHEMBL\d+$')> |
| `standard_relation` | `str` | True | Standardized operator. | <Check isin: isin(['=', '<', '<=', '>', '>='])> |
| `standard_value` | `float64` | True | Standardized value. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `standard_units` | `str` | True | Standardized units. | - |
| `standard_type` | `str` | True | Standardized measurement type. | <Check isin: isin(['IC50', 'EC50', 'Ki', 'Kd', 'AC50', 'GI50', 'Potency', 'Inhibition', '% Inhibition', 'Activity', 'Ratio', 'ED50', 'ID50'])> |
| `standard_flag` | `int64` | True | Standardization flag. | <Check isin: isin([0, 1])> |
| `pchembl_value` | `float64` | True | -log10 of molar activity. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)><br><Check less_than_or_equal_to: less_than_or_equal_to(14)> |
| `data_validity_comment` | `str` | True | Data quality comment. | <Check isin: isin(['Potential missing data', 'Potential author error', 'Manually validated', 'Potential transcription error', 'Outside typical range', 'Non standard unit for type', 'Author confirmed error'])> |
| `activity_comment` | `str` | True | Textual comment. | - |
| `potential_duplicate` | `int64` | True | Duplicate flag. | <Check isin: isin([0, 1])> |
| `bao_endpoint` | `str` | True | BAO ID. | <Check str_matches: str_matches('^BAO:\d+$')> |
| `uo_units` | `str` | True | Units Ontology ID. | <Check str_matches: str_matches('^UO:\d+$')> |
| `qudt_units` | `str` | True | QUDT unit. | - |
| `src_id` | `int64` | True | Source ID. | - |
| `record_id` | `int64` | True | FK to compound_record. | - |
| `type` | `str` | True | Original type. | - |
| `relation` | `str` | True | Original operator. | - |
| `value` | `float64` | True | Original value. | - |
| `units` | `str` | True | Original units. | - |
| `text_value` | `str` | True | Text value. | - |
| `standard_text_value` | `str` | True | Standardized text value. | - |
| `upper_value` | `float64` | True | Upper bound. | - |
| `standard_upper_value` | `float64` | True | Standardized upper bound. | - |
| `toid` | `int64` | True | Test Occasion ID. | - |
| `ligand_efficiency_bei` | `float64` | True |  | - |
| `ligand_efficiency_le` | `float64` | True |  | - |
| `ligand_efficiency_lle` | `float64` | True |  | - |
| `ligand_efficiency_sei` | `float64` | True |  | - |
| `action_type_action_type` | `str` | True |  | - |
| `action_type_description` | `str` | True |  | - |
| `action_type_parent_type` | `str` | True |  | - |
| `activity_properties` | `str` | True | JSON string of activity properties. | - |
| `canonical_smiles` | `str` | True |  | - |
| `molecule_pref_name` | `str` | True |  | - |
| `parent_molecule_chembl_id` | `str` | True |  | - |
| `target_pref_name` | `str` | True |  | - |
| `target_organism` | `str` | True |  | - |
| `target_taxonomy_id` | `str` | True | Target taxonomy ID. Standardized name (was target_tax_id). | - |
| `assay_type` | `str` | True |  | - |
| `assay_description` | `str` | True |  | - |
| `assay_variant_accession` | `str` | True |  | - |
| `assay_variant_mutation` | `str` | True |  | - |
| `bao_format` | `str` | True |  | - |
| `bao_label` | `str` | True |  | - |
| `document_journal` | `str` | True |  | - |
| `document_year` | `float64` | True |  | - |

[Back to Top](#table-of-contents)


---

## CHEMBL / assay: chembl_assay <a name='chembl-assay'></a>

- **Config**: `configs/pipelines/chembl/assay.yaml`
- **Schema Class**: `AssaySchema`

### Field Specifications (Silver/Gold)

| Field | Type | Nullable | Description | Constraints |
|---|---|---|---|---|
| `entity_id` | `str` | False | Unique business identifier for the entity. | - |
| `content_hash` | `str` | False | SHA256 hash of canonical record representation (64 hex chars). | <Check str_matches: str_matches('^[a-f0-9]{64}$')> |
| `_run_id` | `object` | False | Correlation ID for the pipeline run. | - |
| `_run_type` | `str` | False | Type of pipeline run. | <Check isin: isin(['incremental', 'backfill', 'rebuild'])> |
| `_source_batch_id` | `object` | True | Batch context ID from the source. | - |
| `_ingestion_ts` | `str` | False | Timestamp when the record was ingested (UTC, ISO 8601 format). | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$')> |
| `_dq_warn` | `bool` | False | Flag for data quality warnings. | - |
| `_dq_error` | `bool` | False | Flag for data quality errors. | - |
| `_index` | `int64` | False | Sequential index of the record in the pipeline run. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `assay_chembl_id` | `str` | False | ChEMBL ID. | <Check str_matches: str_matches('^CHEMBL\d+$')> |
| `description` | `str` | True | Assay description. | - |
| `assay_type` | `str` | True | Assay type. | <Check isin: isin(['B', 'F', 'A', 'T', 'P', 'U'])> |
| `assay_test_type` | `str` | True | Assay test type. | <Check isin: isin(['In vivo', 'In vitro', 'Ex vivo'])> |
| `assay_category` | `str` | True | Assay category. | <Check isin: isin(['screening', 'confirmatory', 'panel', 'summary', 'other'])> |
| `assay_group` | `str` | True | Assay group. | - |
| `assay_organism` | `str` | True | Organism. | - |
| `assay_taxonomy_id` | `int64` | True | NCBI Taxonomy ID. Standardized name (was assay_tax_id). | - |
| `assay_strain` | `str` | True | Strain. | - |
| `assay_tissue` | `str` | True | Tissue. | - |
| `assay_cell_type` | `str` | True | Cell type. | - |
| `assay_subcellular_fraction` | `str` | True | Subcellular fraction. | - |
| `target_chembl_id` | `str` | True | Target ChEMBL ID. | <Check str_matches: str_matches('^CHEMBL\d+$')> |
| `relationship_type` | `str` | True | Relationship type. | <Check isin: isin(['D', 'H', 'M', 'N', 'S', 'U'])> |
| `relationship_description` | `str` | True | Relationship description. | - |
| `confidence_score` | `int64` | True | Confidence score. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)><br><Check less_than_or_equal_to: less_than_or_equal_to(9)> |
| `confidence_description` | `str` | True | Confidence description. | - |
| `src_id` | `int64` | True | Source ID. | - |
| `src_assay_id` | `str` | True | Source Assay ID. | - |
| `document_chembl_id` | `str` | True | Document ChEMBL ID. | <Check str_matches: str_matches('^CHEMBL\d+$')> |
| `assay_pref_name` | `str` | True | Preferred name. | - |
| `score` | `float64` | True | Score. | - |
| `cell_chembl_id` | `str` | True | FK to cell_line. | - |
| `tissue_chembl_id` | `str` | True | FK to tissue. | - |
| `bao_format` | `str` | True | BAO format. | <Check str_matches: str_matches('^BAO:\d+$')> |
| `bao_label` | `str` | True | BAO label. | - |
| `aidx` | `str` | True | Assay index. | - |
| `variant_accession` | `str` | True |  | - |
| `variant_isoform` | `str` | True |  | - |
| `variant_mutation` | `str` | True |  | - |
| `variant_organism` | `str` | True |  | - |
| `variant_sequence` | `str` | True |  | - |
| `variant_taxonomy_id` | `int64` | True | Variant taxonomy ID. Standardized name (was variant_tax_id). | - |
| `variant_sequence_json` | `str` | True |  | - |
| `assay_classifications` | `str` | True | JSON string of assay classifications. | - |
| `assay_parameters` | `str` | True | JSON string of assay parameters. | - |

[Back to Top](#table-of-contents)


---

## CHEMBL / assay_parameters: chembl_assay_parameters <a name='chembl-assay_parameters'></a>

- **Config**: `configs/pipelines/chembl/assay_parameters.yaml`
- **Schema Class**: `AssayParametersSchema`

### Field Specifications (Silver/Gold)

| Field | Type | Nullable | Description | Constraints |
|---|---|---|---|---|
| `entity_id` | `str` | False | Unique business identifier for the entity. | - |
| `content_hash` | `str` | False | SHA256 hash of canonical record representation (64 hex chars). | <Check str_matches: str_matches('^[a-f0-9]{64}$')> |
| `_run_id` | `object` | False | Correlation ID for the pipeline run. | - |
| `_run_type` | `str` | False | Type of pipeline run. | <Check isin: isin(['incremental', 'backfill', 'rebuild'])> |
| `_source_batch_id` | `object` | True | Batch context ID from the source. | - |
| `_ingestion_ts` | `str` | False | Timestamp when the record was ingested (UTC, ISO 8601 format). | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$')> |
| `_dq_warn` | `bool` | False | Flag for data quality warnings. | - |
| `_dq_error` | `bool` | False | Flag for data quality errors. | - |
| `_index` | `int64` | False | Sequential index of the record in the pipeline run. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `assay_param_id` | `int64` | False | Parameter ID (PK, surrogate integer). | <Check greater_than_or_equal_to: greater_than_or_equal_to(1)> |
| `assay_chembl_id` | `str` | False | FK → Assay (ChEMBL ID format). | <Check str_matches: str_matches('^CHEMBL\d+$')> |
| `type` | `str` | False | Parameter type (e.g., CONC, PH, TEMP, TIME). | - |
| `relation` | `str` | True | Relation operator (=, <, >, ~, >=, <=). | - |
| `value` | `float64` | True | Numeric value. | - |
| `units` | `str` | True | Original units (e.g., uM, nM, %). | - |
| `text_value` | `str` | True | Text value for non-numeric parameters. | - |
| `comments` | `str` | True | Additional comments. | - |
| `standard_type` | `str` | True | Standardized type. | - |
| `standard_relation` | `str` | True | Standardized relation. | - |
| `standard_value` | `float64` | True | Standardized value. | - |
| `standard_units` | `str` | True | Standardized units. | - |
| `standard_text_value` | `str` | True | Standardized text value. | - |

[Back to Top](#table-of-contents)


---

## CHEMBL / cell_line: chembl_cell_line <a name='chembl-cell_line'></a>

- **Config**: `configs/pipelines/chembl/cell_line.yaml`
- **Schema Class**: `CellLineSchema`

### Field Specifications (Silver/Gold)

| Field | Type | Nullable | Description | Constraints |
|---|---|---|---|---|
| `entity_id` | `str` | False | Unique business identifier for the entity. | - |
| `content_hash` | `str` | False | SHA256 hash of canonical record representation (64 hex chars). | <Check str_matches: str_matches('^[a-f0-9]{64}$')> |
| `_run_id` | `object` | False | Correlation ID for the pipeline run. | - |
| `_run_type` | `str` | False | Type of pipeline run. | <Check isin: isin(['incremental', 'backfill', 'rebuild'])> |
| `_source_batch_id` | `object` | True | Batch context ID from the source. | - |
| `_ingestion_ts` | `str` | False | Timestamp when the record was ingested (UTC, ISO 8601 format). | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$')> |
| `_dq_warn` | `bool` | False | Flag for data quality warnings. | - |
| `_dq_error` | `bool` | False | Flag for data quality errors. | - |
| `_index` | `int64` | False | Sequential index of the record in the pipeline run. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `cell_chembl_id` | `str` | False | ChEMBL ID for cell line (PK). | <Check str_matches: str_matches('^CHEMBL\d+$')> |
| `cell_name` | `str` | False | Cell line name (e.g., HeLa, MCF7). | - |
| `cell_description` | `str` | True | Cell line description. | - |
| `cell_source_tissue` | `str` | True | Source tissue (e.g., Cervix, Breast). | - |
| `cell_source_organism` | `str` | True | Source organism (e.g., Homo sapiens). | - |
| `cell_source_taxonomy_id` | `int64` | True | NCBI Taxonomy ID for source organism. Standardized name (was cell_source_tax_id). | <Check greater_than_or_equal_to: greater_than_or_equal_to(1)> |
| `cell_type` | `str` | True | Cell type classification (e.g., Cancer cell line). | - |
| `cellosaurus_id` | `str` | True | Cellosaurus ID (external reference). | <Check str_matches: str_matches('^CVCL_[A-Z0-9]+$')> |
| `clo_id` | `str` | True | Cell Line Ontology ID. | <Check str_matches: str_matches('^CLO_\d+$')> |
| `cl_lincs_id` | `str` | True | LINCS ID (Library of Integrated Network-Based Cellular Signatures). | - |
| `efo_id` | `str` | True | EFO ontology ID. | <Check str_matches: str_matches('^EFO_\d+$')> |

[Back to Top](#table-of-contents)


---

## CHEMBL / compound_record: chembl_compound_record <a name='chembl-compound_record'></a>

- **Config**: `configs/pipelines/chembl/compound_record.yaml`
- **Schema Class**: `CompoundRecordSchema`

### Field Specifications (Silver/Gold)

| Field | Type | Nullable | Description | Constraints |
|---|---|---|---|---|
| `entity_id` | `str` | False | Unique business identifier for the entity. | - |
| `content_hash` | `str` | False | SHA256 hash of canonical record representation (64 hex chars). | <Check str_matches: str_matches('^[a-f0-9]{64}$')> |
| `_run_id` | `object` | False | Correlation ID for the pipeline run. | - |
| `_run_type` | `str` | False | Type of pipeline run. | <Check isin: isin(['incremental', 'backfill', 'rebuild'])> |
| `_source_batch_id` | `object` | True | Batch context ID from the source. | - |
| `_ingestion_ts` | `str` | False | Timestamp when the record was ingested (UTC, ISO 8601 format). | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$')> |
| `_dq_warn` | `bool` | False | Flag for data quality warnings. | - |
| `_dq_error` | `bool` | False | Flag for data quality errors. | - |
| `_index` | `int64` | False | Sequential index of the record in the pipeline run. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `record_id` | `int64` | False | ChEMBL record ID (PK). | <Check greater_than_or_equal_to: greater_than_or_equal_to(1)> |
| `molecule_chembl_id` | `str` | False | FK → Molecule. | <Check str_matches: str_matches('^CHEMBL\d+$')> |
| `document_chembl_id` | `str` | False | FK → Publication. | <Check str_matches: str_matches('^CHEMBL\d+$')> |
| `src_id` | `int64` | False | FK → Source (data source). | <Check greater_than_or_equal_to: greater_than_or_equal_to(1)> |
| `compound_key` | `str` | True | Original compound key in source document. | - |
| `compound_name` | `str` | True | Original compound name in source document. | - |
| `src_compound_id` | `str` | True | Compound ID in original data source. | - |

[Back to Top](#table-of-contents)


---

## CHEMBL / document: chembl_publication <a name='chembl-document'></a>

- **Config**: `configs/pipelines/chembl/publication.yaml`
- **Schema Class**: `ChemblPublicationSchema`

### Field Specifications (Silver/Gold)

| Field | Type | Nullable | Description | Constraints |
|---|---|---|---|---|
| `entity_id` | `str` | False | Unique business identifier for the entity. | - |
| `content_hash` | `str` | False | SHA256 hash of canonical record representation (64 hex chars). | <Check str_matches: str_matches('^[a-f0-9]{64}$')> |
| `_run_id` | `object` | False | Correlation ID for the pipeline run. | - |
| `_run_type` | `str` | False | Type of pipeline run. | <Check isin: isin(['incremental', 'backfill', 'rebuild'])> |
| `_source_batch_id` | `object` | True | Batch context ID from the source. | - |
| `_ingestion_ts` | `str` | False | Timestamp when the record was ingested (UTC, ISO 8601 format). | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$')> |
| `_dq_warn` | `bool` | False | Flag for data quality warnings. | - |
| `_dq_error` | `bool` | False | Flag for data quality errors. | - |
| `_index` | `int64` | False | Sequential index of the record in the pipeline run. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `pmid` | `str` | True | PubMed ID (numeric string) | <Check str_matches: str_matches('^\d+$')> |
| `doi` | `str` | True | Digital Object Identifier (lowercase) | <Check str_matches: str_matches('^10\.\d{4,}/.+$')> |
| `pmc_id` | `str` | True | PubMed Central ID | <Check str_matches: str_matches('^PMC\d+$')> |
| `title` | `str` | True | Publication title | - |
| `abstract` | `str` | True | Publication abstract | - |
| `authors` | `str` | True | JSON array of author names (PII hashed) | - |
| `journal` | `str` | True | Journal name | - |
| `year` | `int64` | True | Publication year | <Check greater_than_or_equal_to: greater_than_or_equal_to(1800)><br><Check less_than_or_equal_to: less_than_or_equal_to(2100)> |
| `publication_date` | `str` | True | Publication date (YYYY-MM-DD) | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}$')> |
| `doc_type` | `str` | True | Document type. | <Check isin: isin(['PUBLICATION', 'PATENT', 'DATASET', 'BOOK'])> |
| `language` | `str` | True | Language code (ISO 639-1 or MARC) | - |
| `citation_count` | `Int64` | True | Number of citations (provider-dependent availability) | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `is_oa` | `bool` | True | Is Open Access (provider-dependent availability) | - |
| `_lookup_method` | `str` | False | How record was resolved: direct for ChEMBL ID lookup | <Check isin: isin(['direct', 'doi', 'pmid', 'title_fallback', 'title_only', 'unknown'])> |
| `_original_id` | `str` | True | Original identifier from input (for fallback records) | - |
| `source` | `str` | True | Data source identifier (e.g., pubmed, crossref, openalex) | - |
| `document_chembl_id` | `str` | False | ChEMBL Document ID. | <Check str_matches: str_matches('^CHEMBL\d+$')> |
| `patent_id` | `str` | True | Patent ID. | - |
| `src_id` | `int64` | True | Source ID. | - |
| `journal_full_title` | `str` | True | Full journal title. | - |
| `volume` | `str` | True | Volume. | - |
| `issue` | `str` | True | Issue. | - |
| `first_page` | `str` | True | First page. | - |
| `last_page` | `str` | True | Last page. | - |

[Back to Top](#table-of-contents)


---

## CHEMBL / document_similarity: chembl_publication_similarity <a name='chembl-document_similarity'></a>

- **Config**: `configs/pipelines/chembl/publication_similarity.yaml`
- **Schema Class**: `PublicationSimilaritySchema`

### Field Specifications (Silver/Gold)

| Field | Type | Nullable | Description | Constraints |
|---|---|---|---|---|
| `entity_id` | `str` | False | Unique business identifier for the entity. | - |
| `content_hash` | `str` | False | SHA256 hash of canonical record representation (64 hex chars). | <Check str_matches: str_matches('^[a-f0-9]{64}$')> |
| `_run_id` | `object` | False | Correlation ID for the pipeline run. | - |
| `_run_type` | `str` | False | Type of pipeline run. | <Check isin: isin(['incremental', 'backfill', 'rebuild'])> |
| `_source_batch_id` | `object` | True | Batch context ID from the source. | - |
| `_ingestion_ts` | `str` | False | Timestamp when the record was ingested (UTC, ISO 8601 format). | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$')> |
| `_dq_warn` | `bool` | False | Flag for data quality warnings. | - |
| `_dq_error` | `bool` | False | Flag for data quality errors. | - |
| `_index` | `int64` | False | Sequential index of the record in the pipeline run. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `sim_id` | `int64` | False | Primary key. | - |
| `doc_1` | `int64` | False | FK to document 1. | - |
| `doc_2` | `int64` | False | FK to document 2. | - |
| `pubmed_id1` | `str` | True | PubMed identifier 1 (numeric string). | <Check str_matches: str_matches('^\d+$')> |
| `pubmed_id2` | `str` | True | PubMed identifier 2 (numeric string). | <Check str_matches: str_matches('^\d+$')> |
| `tid_tani` | `float64` | True | Tanimoto coefficient (TID). | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)><br><Check less_than_or_equal_to: less_than_or_equal_to(1)> |
| `mol_tani` | `float64` | True | Tanimoto coefficient (MOL). | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)><br><Check less_than_or_equal_to: less_than_or_equal_to(1)> |
| `avg_tani` | `float64` | True | Average Tanimoto coefficient. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)><br><Check less_than_or_equal_to: less_than_or_equal_to(1)> |
| `max_tani` | `float64` | True | Max Tanimoto coefficient. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)><br><Check less_than_or_equal_to: less_than_or_equal_to(1)> |

[Back to Top](#table-of-contents)


---

## CHEMBL / document_term: chembl_publication_term <a name='chembl-document_term'></a>

- **Config**: `configs/pipelines/chembl/publication_term.yaml`
- **Schema Class**: `PublicationTermSchema`

### Field Specifications (Silver/Gold)

| Field | Type | Nullable | Description | Constraints |
|---|---|---|---|---|
| `entity_id` | `str` | False | Unique business identifier for the entity. | - |
| `content_hash` | `str` | False | SHA256 hash of canonical record representation (64 hex chars). | <Check str_matches: str_matches('^[a-f0-9]{64}$')> |
| `_run_id` | `object` | False | Correlation ID for the pipeline run. | - |
| `_run_type` | `str` | False | Type of pipeline run. | <Check isin: isin(['incremental', 'backfill', 'rebuild'])> |
| `_source_batch_id` | `object` | True | Batch context ID from the source. | - |
| `_ingestion_ts` | `str` | False | Timestamp when the record was ingested (UTC, ISO 8601 format). | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$')> |
| `_dq_warn` | `bool` | False | Flag for data quality warnings. | - |
| `_dq_error` | `bool` | False | Flag for data quality errors. | - |
| `_index` | `int64` | False | Sequential index of the record in the pipeline run. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `document_chembl_id` | `str` | False | FK → Document ChEMBL ID. | <Check str_matches: str_matches('^CHEMBL\d+$')> |
| `term` | `str` | False | Term text (e.g., 'Aspirin', 'kinase inhibitor'). | <Check str_length: str_length(1, None)> |
| `term_type` | `str` | False | Term type classification. | <Check isin: isin(['MESH_HEADING', 'MESH_QUALIFIER', 'KEYWORD', 'CONCEPT'])> |
| `mesh_id` | `str` | True | MeSH identifier (e.g., 'D001241'). | - |
| `qualifier` | `str` | True | MeSH qualifier (e.g., 'pharmacology'). | - |

[Back to Top](#table-of-contents)


---

## CHEMBL / molecule: chembl_molecule <a name='chembl-molecule'></a>

- **Config**: `configs/pipelines/chembl/molecule.yaml`
- **Schema Class**: `MoleculeSchema`

### Field Specifications (Silver/Gold)

| Field | Type | Nullable | Description | Constraints |
|---|---|---|---|---|
| `entity_id` | `str` | False | Unique business identifier for the entity. | - |
| `content_hash` | `str` | False | SHA256 hash of canonical record representation (64 hex chars). | <Check str_matches: str_matches('^[a-f0-9]{64}$')> |
| `_run_id` | `object` | False | Correlation ID for the pipeline run. | - |
| `_run_type` | `str` | False | Type of pipeline run. | <Check isin: isin(['incremental', 'backfill', 'rebuild'])> |
| `_source_batch_id` | `object` | True | Batch context ID from the source. | - |
| `_ingestion_ts` | `str` | False | Timestamp when the record was ingested (UTC, ISO 8601 format). | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$')> |
| `_dq_warn` | `bool` | False | Flag for data quality warnings. | - |
| `_dq_error` | `bool` | False | Flag for data quality errors. | - |
| `_index` | `int64` | False | Sequential index of the record in the pipeline run. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `molecule_chembl_id` | `str` | False | ChEMBL ID. | <Check str_matches: str_matches('^CHEMBL\d+$')> |
| `structure_standard_inchi_key` | `str` | True | Standard InChI Key (27 characters, format: XXXX-YYYY-Z). | <Check str_matches: str_matches('^[A-Z]{14}-[A-Z]{10}-[A-Z]$')> |
| `pref_name` | `str` | True | Preferred name. | - |
| `max_phase` | `float64` | True | Maximum clinical phase. | <Check isin: isin([-1, 0, 0.5, 1, 2, 3, 4])> |
| `structure_type` | `str` | True | Structure type. | <Check isin: isin(['MOL', 'SEQ', 'BOTH', 'NONE'])> |
| `molecule_type` | `str` | True | Molecule type. | <Check isin: isin(['Small molecule', 'Inorganic small molecule', 'Polymeric small molecule', 'Antibody', 'Antibody drug conjugate', 'Protein', 'Oligonucleotide', 'Oligosaccharide', 'Cell', 'Enzyme', 'Unknown', 'Unclassified'])> |
| `first_approval` | `int64` | True | Year of first approval. | - |
| `therapeutic_flag` | `bool` | True | Therapeutic flag. | - |
| `oral` | `bool` | True | Oral administration flag. | - |
| `parenteral` | `bool` | True | Parenteral administration flag. | - |
| `topical` | `bool` | True | Topical administration flag. | - |
| `black_box_warning` | `int64` | True | Black box warning flag. | <Check isin: isin([0, 1])> |
| `natural_product` | `int64` | True | Natural product flag. | <Check isin: isin([-1, 0, 1])> |
| `first_in_class` | `int64` | True | First in class flag. | <Check isin: isin([0, 1])> |
| `prodrug` | `int64` | True | Prodrug flag. | <Check isin: isin([0, 1])> |
| `inorganic_flag` | `int64` | True | Inorganic flag. | <Check isin: isin([0, 1])> |
| `polymer_flag` | `int64` | True | Polymer flag. | <Check isin: isin([0, 1])> |
| `withdrawn_flag` | `bool` | True | Withdrawn flag. | - |
| `chirality` | `int64` | True | Chirality flag: -1=unknown, 0=achiral, 1=single, 2=racemic. | <Check isin: isin([-1, 0, 1, 2])> |
| `dosed_ingredient` | `int64` | True | Dosed ingredient flag. | <Check isin: isin([0, 1])> |
| `availability_type` | `int64` | True | Availability type. | <Check isin: isin([-2, -1, 0, 1, 2])> |
| `usan_year` | `int64` | True | USAN approval year. | - |
| `usan_stem` | `str` | True | USAN stem name. | - |
| `usan_substem` | `str` | True | USAN substem name. | - |
| `usan_stem_definition` | `str` | True | USAN stem definition. | - |
| `helm_notation` | `str` | True | HELM notation for biopolymers. | - |
| `molecule_species` | `str` | True | Species for biologics. | - |
| `hierarchy_parent_chembl_id` | `str` | True | Parent molecule ChEMBL ID in hierarchy. | <Check str_matches: str_matches('^CHEMBL\d+$')> |
| `hierarchy_active_chembl_id` | `str` | True | Active molecule ChEMBL ID in hierarchy. | <Check str_matches: str_matches('^CHEMBL\d+$')> |
| `hierarchy_child_chembl_id` | `str` | True | Child molecule ChEMBL ID in hierarchy. | <Check str_matches: str_matches('^CHEMBL\d+$')> |
| `property_alogp` | `float64` | True | Calculated ALogP (partition coefficient). | - |
| `property_mw_freebase` | `float64` | True | Molecular weight of parent compound. | - |
| `property_full_mwt` | `float64` | True | Full molecular weight including salts. | - |
| `property_hba` | `int64` | True | Hydrogen bond acceptors count. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `property_hbd` | `int64` | True | Hydrogen bond donors count. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `property_psa` | `float64` | True | Polar surface area (PSA). | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `property_rtb` | `int64` | True | Rotatable bonds count. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `property_ro5_violations` | `int64` | True | Number of Lipinski rule-of-5 violations. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)><br><Check less_than_or_equal_to: less_than_or_equal_to(4)> |
| `property_heavy_atoms` | `int64` | True | Heavy (non-hydrogen) atoms count. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `property_aromatic_rings` | `int64` | True | Aromatic rings count. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `property_qed_weighted` | `float64` | True | Quantitative Estimate of Drug-likeness. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)><br><Check less_than_or_equal_to: less_than_or_equal_to(1)> |
| `property_full_molformula` | `str` | True | Full molecular formula. | - |
| `property_ro3_pass` | `str` | True | Rule-of-3 compliance (Y/N). | <Check isin: isin(['Y', 'N'])> |
| `canonical_smiles` | `str` | True | Canonical SMILES representation. | - |
| `standard_inchi` | `str` | True | Standard InChI representation. | - |
| `inchikey` | `str` | True | Standard InChI Key (27 characters, XXXX-YYYY-Z format). | <Check str_matches: str_matches('^[A-Z]{14}-[A-Z]{10}-[A-Z]$')> |
| `molecule_hierarchy` | `str` | True | JSON string of molecule hierarchy. | - |
| `molecule_properties` | `str` | True | JSON string of molecule properties. | - |
| `molecule_structures` | `str` | True | JSON string of molecule structures. | - |
| `molecule_synonyms` | `str` | True | JSON string of molecule synonyms. | - |
| `cross_references` | `str` | True | JSON string of cross references. | - |
| `atc_classifications` | `str` | True | JSON string of ATC classifications. | - |

[Back to Top](#table-of-contents)


---

## CHEMBL / protein_class: chembl_protein_class <a name='chembl-protein_class'></a>

- **Config**: `configs/pipelines/chembl/protein_class.yaml`
- **Schema Class**: `ProteinClassificationSchema`

### Field Specifications (Silver/Gold)

| Field | Type | Nullable | Description | Constraints |
|---|---|---|---|---|
| `entity_id` | `str` | False | Unique business identifier for the entity. | - |
| `content_hash` | `str` | False | SHA256 hash of canonical record representation (64 hex chars). | <Check str_matches: str_matches('^[a-f0-9]{64}$')> |
| `_run_id` | `object` | False | Correlation ID for the pipeline run. | - |
| `_run_type` | `str` | False | Type of pipeline run. | <Check isin: isin(['incremental', 'backfill', 'rebuild'])> |
| `_source_batch_id` | `object` | True | Batch context ID from the source. | - |
| `_ingestion_ts` | `str` | False | Timestamp when the record was ingested (UTC, ISO 8601 format). | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$')> |
| `_dq_warn` | `bool` | False | Flag for data quality warnings. | - |
| `_dq_error` | `bool` | False | Flag for data quality errors. | - |
| `_index` | `int64` | False | Sequential index of the record in the pipeline run. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `protein_class_id` | `int64` | False | Primary key. | - |
| `parent_id` | `int64` | True | FK to parent classification. | - |
| `replaced_by` | `int64` | True | FK to replacement classification. | - |
| `pref_name` | `str` | True | Preferred name. | - |
| `short_name` | `str` | True | Short name. | - |
| `protein_class_desc` | `str` | True | Description. | - |
| `definition` | `str` | True | Definition. | - |
| `class_level` | `int64` | True | Class level. | <Check greater_than_or_equal_to: greater_than_or_equal_to(1)> |
| `sort_order` | `int64` | True | Sort order. | - |
| `downgraded` | `int64` | True | Downgraded flag. | <Check isin: isin([0, 1])> |

[Back to Top](#table-of-contents)


---

## CHEMBL / target: chembl_target <a name='chembl-target'></a>

- **Config**: `configs/pipelines/chembl/target.yaml`
- **Schema Class**: `TargetSchema`

### Field Specifications (Silver/Gold)

| Field | Type | Nullable | Description | Constraints |
|---|---|---|---|---|
| `entity_id` | `str` | False | Unique business identifier for the entity. | - |
| `content_hash` | `str` | False | SHA256 hash of canonical record representation (64 hex chars). | <Check str_matches: str_matches('^[a-f0-9]{64}$')> |
| `_run_id` | `object` | False | Correlation ID for the pipeline run. | - |
| `_run_type` | `str` | False | Type of pipeline run. | <Check isin: isin(['incremental', 'backfill', 'rebuild'])> |
| `_source_batch_id` | `object` | True | Batch context ID from the source. | - |
| `_ingestion_ts` | `str` | False | Timestamp when the record was ingested (UTC, ISO 8601 format). | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$')> |
| `_dq_warn` | `bool` | False | Flag for data quality warnings. | - |
| `_dq_error` | `bool` | False | Flag for data quality errors. | - |
| `_index` | `int64` | False | Sequential index of the record in the pipeline run. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `target_chembl_id` | `str` | False | ChEMBL ID. | <Check str_matches: str_matches('^CHEMBL\d+$')> |
| `target_type` | `str` | True | Target type. | <Check isin: isin(['SINGLE PROTEIN', 'PROTEIN FAMILY', 'PROTEIN COMPLEX', 'PROTEIN COMPLEX GROUP', 'SELECTIVITY GROUP', 'CHIMERIC PROTEIN', 'CELL-LINE', 'TISSUE', 'ORGANISM', 'MACROMOLECULE', 'SMALL MOLECULE', 'LIPID', 'METAL', 'UNKNOWN'])> |
| `pref_name` | `str` | True | Preferred name. | - |
| `description` | `str` | True | Target description. | - |
| `taxonomy_id` | `int64` | True | NCBI Taxonomy ID. Standardized name (was tax_id). | - |
| `organism` | `str` | True | Organism. | - |
| `species_group_flag` | `bool` | True | Species group flag. | - |
| `downgraded` | `bool` | True | Downgraded flag. | - |
| `dap_id` | `int64` | True | Drug affinity prediction ID. | - |
| `target_components` | `str` | True | JSON string of target components. | - |
| `cross_references` | `str` | True | JSON string of cross references. | - |
| `pipeline_stages` | `str` | True | JSON string of pipeline stages. | - |
| `target_constraints` | `str` | True | JSON string of target constraints. | - |
| `target_component_synonyms` | `str` | True | JSON string of aggregated component synonyms. | - |
| `component_accessions` | `object` | True | List of component accessions. | - |
| `component_ids` | `object` | True | List of component IDs. | - |
| `component_types` | `object` | True | List of component types. | - |
| `component_relationships` | `object` | True | List of component relationships. | - |
| `component_descriptions` | `object` | True | List of component descriptions. | - |
| `component_organisms` | `object` | True | List of component organisms. | - |
| `component_taxonomy_ids` | `object` | True | List of component NCBI taxonomy IDs. | - |

[Back to Top](#table-of-contents)


---

## CHEMBL / target_component: chembl_target_component <a name='chembl-target_component'></a>

- **Config**: `configs/pipelines/chembl/target_component.yaml`
- **Schema Class**: `TargetComponentSchema`

### Field Specifications (Silver/Gold)

| Field | Type | Nullable | Description | Constraints |
|---|---|---|---|---|
| `entity_id` | `str` | False | Unique business identifier for the entity. | - |
| `content_hash` | `str` | False | SHA256 hash of canonical record representation (64 hex chars). | <Check str_matches: str_matches('^[a-f0-9]{64}$')> |
| `_run_id` | `object` | False | Correlation ID for the pipeline run. | - |
| `_run_type` | `str` | False | Type of pipeline run. | <Check isin: isin(['incremental', 'backfill', 'rebuild'])> |
| `_source_batch_id` | `object` | True | Batch context ID from the source. | - |
| `_ingestion_ts` | `str` | False | Timestamp when the record was ingested (UTC, ISO 8601 format). | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$')> |
| `_dq_warn` | `bool` | False | Flag for data quality warnings. | - |
| `_dq_error` | `bool` | False | Flag for data quality errors. | - |
| `_index` | `int64` | False | Sequential index of the record in the pipeline run. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `targcomp_id` | `int64` | False | Primary key. | - |
| `tid` | `int64` | False | FK to target. | - |
| `component_id` | `int64` | False | FK to component_sequences. | - |
| `relationship` | `str` | True | Relationship type. | <Check isin: isin(['SINGLE PROTEIN', 'PROTEIN SUBUNIT', 'RNA', 'INTERACTING PROTEIN'])> |
| `stoichiometry` | `int64` | True | Stoichiometry. | <Check greater_than_or_equal_to: greater_than_or_equal_to(1)> |
| `homologue` | `int64` | True | Homologue flag. | <Check isin: isin([0, 1, 2])> |

[Back to Top](#table-of-contents)


---

## CROSSREF / work: crossref_publication <a name='crossref-work'></a>

- **Config**: `configs/pipelines/crossref/publication.yaml`
- **Schema Class**: `PublicationSchema`

### Field Specifications (Silver/Gold)

| Field | Type | Nullable | Description | Constraints |
|---|---|---|---|---|
| `entity_id` | `str` | False | Unique business identifier for the entity. | - |
| `content_hash` | `str` | False | SHA256 hash of canonical record representation (64 hex chars). | <Check str_matches: str_matches('^[a-f0-9]{64}$')> |
| `_run_id` | `object` | False | Correlation ID for the pipeline run. | - |
| `_run_type` | `str` | False | Type of pipeline run. | <Check isin: isin(['incremental', 'backfill', 'rebuild'])> |
| `_source_batch_id` | `object` | True | Batch context ID from the source. | - |
| `_ingestion_ts` | `str` | False | Timestamp when the record was ingested (UTC, ISO 8601 format). | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$')> |
| `_dq_warn` | `bool` | False | Flag for data quality warnings. | - |
| `_dq_error` | `bool` | False | Flag for data quality errors. | - |
| `_index` | `int64` | False | Sequential index of the record in the pipeline run. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `doi` | `str` | False | Digital Object Identifier (PK) | <Check str_matches: str_matches('^10\.\d{4,}/.+$')> |
| `type` | `str` | False | Publication type (journal-article, book-chapter, etc.) | <Check isin: isin(['journal-article', 'book-chapter', 'proceedings-article', 'book', 'dataset', 'report', 'standard', 'peer-review', 'component', 'posted-content', 'monograph', 'reference-entry', 'dissertation', 'other', 'journal-issue', 'journal', 'reference-book', 'book-series', 'edited-book', 'book-set', 'book-part', 'book-section', 'book-track', 'proceedings', 'proceedings-series', 'report-series', 'report-component', 'grant'])> |
| `title` | `str` | False | Publication title (first element of title array) | <Check str_length: str_length(1, None)> |
| `container_title` | `str` | True | Journal or book name | - |
| `publisher` | `str` | True | Publisher name | - |
| `issn` | `str` | True | ISSN (print preferred) | <Check str_matches: str_matches('^\d{4}-\d{3}[\dX]$')> |
| `isbn` | `str` | True | ISBN (first from list) | - |
| `volume` | `str` | True | Volume number | - |
| `issue` | `str` | True | Issue number | - |
| `page` | `str` | True | Page range (format: start-end) | - |
| `published_date` | `date` | True | Publication date (from issued or published-print) | - |
| `created_date` | `date` | True | Record creation date in CrossRef | - |
| `deposited_date` | `date` | True | Last update date in CrossRef | - |
| `abstract` | `str` | True | Abstract text (may contain HTML entities) | - |
| `language` | `str` | True | Language code (ISO 639-1) | <Check str_matches: str_matches('^[a-z]{2}$')> |
| `subject` | `str` | True | Subject areas (joined with '; ') | - |
| `license_url` | `str` | True | License URL (first from list) | - |
| `is_referenced_by_count` | `int64` | True | Citation count (times referenced) | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `references_count` | `int64` | True | Reference count (bibliography size) | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `funder_names` | `str` | True | Funder names (joined with '; ') | - |
| `clinical_trial_numbers` | `str` | True | Clinical trial identifiers (joined with '; ') | - |
| `update_policy` | `str` | True | DOI of update policy | - |

[Back to Top](#table-of-contents)


---

## OPENALEX / publication: openalex_publication <a name='openalex-publication'></a>

- **Config**: `configs/pipelines/openalex/publication.yaml`
- **Schema Class**: `OpenAlexPublicationSchema`

### Field Specifications (Silver/Gold)

| Field | Type | Nullable | Description | Constraints |
|---|---|---|---|---|
| `entity_id` | `str` | False | Unique business identifier for the entity. | - |
| `content_hash` | `str` | False | SHA256 hash of canonical record representation (64 hex chars). | <Check str_matches: str_matches('^[a-f0-9]{64}$')> |
| `_run_id` | `object` | False | Correlation ID for the pipeline run. | - |
| `_run_type` | `str` | False | Type of pipeline run. | <Check isin: isin(['incremental', 'backfill', 'rebuild'])> |
| `_source_batch_id` | `object` | True | Batch context ID from the source. | - |
| `_ingestion_ts` | `str` | False | Timestamp when the record was ingested (UTC, ISO 8601 format). | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$')> |
| `_dq_warn` | `bool` | False | Flag for data quality warnings. | - |
| `_dq_error` | `bool` | False | Flag for data quality errors. | - |
| `_index` | `int64` | False | Sequential index of the record in the pipeline run. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `pmid` | `str` | True | PubMed ID (numeric string) | <Check str_matches: str_matches('^\d+$')> |
| `doi` | `str` | True | Digital Object Identifier (lowercase) | <Check str_matches: str_matches('^10\.\d{4,}/.+$')> |
| `pmc_id` | `str` | True | PubMed Central ID | <Check str_matches: str_matches('^PMC\d+$')> |
| `title` | `str` | True | Publication title | - |
| `abstract` | `str` | True | Publication abstract | - |
| `authors` | `str` | True | JSON array of author names (PII hashed) | - |
| `journal` | `str` | True | Journal name | - |
| `year` | `Int64` | True | Publication year (1800-2100). | <Check greater_than_or_equal_to: greater_than_or_equal_to(1800)><br><Check less_than_or_equal_to: less_than_or_equal_to(2100)> |
| `publication_date` | `str` | True | Publication date (YYYY-MM-DD) | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}$')> |
| `doc_type` | `str` | False | Publication type (PUBLICATION, PREPRINT, etc.) | - |
| `language` | `str` | True | Language code (ISO 639-1 or MARC) | - |
| `citation_count` | `Int64` | True | Number of citations (from OpenAlex cited_by_count). | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `is_oa` | `bool` | True | Is Open Access (provider-dependent availability) | - |
| `_lookup_method` | `str` | False | How record was resolved: doi, title_fallback, title_only | <Check isin: isin(['direct', 'doi', 'pmid', 'title_fallback', 'title_only', 'unknown'])> |
| `_original_id` | `str` | True | Original identifier from input (for fallback records) | - |
| `source` | `str` | False | Data source identifier | - |
| `openalex_id` | `str` | False | OpenAlex Work ID (e.g., W2148763428) | <Check str_matches: str_matches('^W\d+$')> |
| `issn` | `str` | True | ISSN-L | - |
| `publisher` | `str` | True | Publisher name | - |
| `oa_status` | `str` | True | OA status (gold, green, hybrid, bronze, closed) | <Check isin: isin(['gold', 'green', 'hybrid', 'bronze', 'closed'])> |

[Back to Top](#table-of-contents)


---

## PUBCHEM / compound: pubchem_compound <a name='pubchem-compound'></a>

- **Config**: `configs/pipelines/pubchem/compound.yaml`
- **Schema Class**: `PubchemMoleculeSchema`

### Field Specifications (Silver/Gold)

| Field | Type | Nullable | Description | Constraints |
|---|---|---|---|---|
| `entity_id` | `str` | False | Unique business identifier for the entity. | - |
| `content_hash` | `str` | False | SHA256 hash of canonical record representation (64 hex chars). | <Check str_matches: str_matches('^[a-f0-9]{64}$')> |
| `_run_id` | `object` | False | Correlation ID for the pipeline run. | - |
| `_run_type` | `str` | False | Type of pipeline run. | <Check isin: isin(['incremental', 'backfill', 'rebuild'])> |
| `_source_batch_id` | `object` | True | Batch context ID from the source. | - |
| `_ingestion_ts` | `str` | False | Timestamp when the record was ingested (UTC, ISO 8601 format). | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$')> |
| `_dq_warn` | `bool` | False | Flag for data quality warnings. | - |
| `_dq_error` | `bool` | False | Flag for data quality errors. | - |
| `_index` | `int64` | False | Sequential index of the record in the pipeline run. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `cid` | `int64` | False | PubChem Compound ID (PK) | <Check cid_positive> |
| `canonical_smiles` | `str` | True | Canonical SMILES string | <Check canonical_smiles_length> |
| `isomeric_smiles` | `str` | True | SMILES with stereochemistry | <Check isomeric_smiles_length> |
| `inchi` | `str` | True | IUPAC InChI identifier | <Check inchi_format> |
| `inchi_key` | `str` | True | InChI hash key (27 chars) | <Check inchi_key_format> |
| `molecular_formula` | `str` | True | Molecular formula (e.g., C6H12O6) | - |
| `iupac_name` | `str` | True | IUPAC systematic name | - |
| `molecular_weight` | `float64` | True | Molecular weight in g/mol | <Check greater_than_or_equal_to: greater_than_or_equal_to(0.0)><br><Check less_than_or_equal_to: less_than_or_equal_to(100000.0)> |
| `exact_mass` | `float64` | True | Monoisotopic exact mass (Da) | <Check exact_mass_non_negative> |
| `xlogp` | `float64` | True | Computed octanol-water partition coefficient | <Check xlogp_range> |
| `tpsa` | `float64` | True | Topological polar surface area (Å²) | <Check tpsa_non_negative> |
| `complexity` | `float64` | True | Structural complexity score | <Check complexity_non_negative> |
| `charge` | `int64` | True | Formal charge | <Check charge_range> |
| `heavy_atom_count` | `int64` | True | Non-hydrogen atom count | <Check heavy_atom_count_range> |
| `h_bond_donor_count` | `int64` | True | Hydrogen bond donor count | <Check h_bond_donor_count_range> |
| `h_bond_acceptor_count` | `int64` | True | Hydrogen bond acceptor count | <Check h_bond_acceptor_count_range> |
| `rotatable_bond_count` | `int64` | True | Rotatable bond count | <Check rotatable_bond_count_range> |
| `atom_stereo_count` | `int64` | True | Total stereocenters | <Check atom_stereo_count_non_negative> |
| `defined_atom_stereo_count` | `int64` | True | Defined stereocenters | <Check defined_atom_stereo_count_non_negative> |
| `undefined_atom_stereo_count` | `int64` | True | Undefined stereocenters | <Check undefined_atom_stereo_count_non_negative> |
| `bond_stereo_count` | `int64` | True | Total E/Z bonds | <Check bond_stereo_count_non_negative> |
| `defined_bond_stereo_count` | `int64` | True | Defined E/Z bonds | <Check defined_bond_stereo_count_non_negative> |
| `undefined_bond_stereo_count` | `int64` | True | Undefined E/Z bonds | <Check undefined_bond_stereo_count_non_negative> |
| `isotope_atom_count` | `int64` | True | Isotopic atom count | <Check isotope_atom_count_non_negative> |
| `covalent_unit_count` | `int64` | True | Number of covalent units | <Check covalent_unit_count_positive> |
| `volume_3d` | `float64` | True | 3D molecular volume (Å³) | <Check volume_3d_non_negative> |
| `conformer_count_3d` | `int64` | True | Number of 3D conformers | <Check conformer_count_3d_non_negative> |
| `feature_acceptor_count_3d` | `int64` | True | 3D H-bond acceptor features | <Check feature_acceptor_count_3d_non_negative> |
| `feature_donor_count_3d` | `int64` | True | 3D H-bond donor features | <Check feature_donor_count_3d_non_negative> |
| `feature_anion_count_3d` | `int64` | True | 3D anion features | <Check feature_anion_count_3d_non_negative> |
| `feature_cation_count_3d` | `int64` | True | 3D cation features | <Check feature_cation_count_3d_non_negative> |
| `feature_ring_count_3d` | `int64` | True | 3D ring features | <Check feature_ring_count_3d_non_negative> |
| `feature_hydrophobe_count_3d` | `int64` | True | 3D hydrophobic features | <Check feature_hydrophobe_count_3d_non_negative> |
| `effective_rotor_count_3d` | `float64` | True | Effective rotatable bonds (3D) | <Check effective_rotor_count_3d_non_negative> |
| `conformer_rmsd_3d` | `float64` | True | Conformer model RMSD | <Check conformer_rmsd_3d_non_negative> |

[Back to Top](#table-of-contents)


---

## PUBMED / publication: pubmed_publication <a name='pubmed-publication'></a>

- **Config**: `configs/pipelines/pubmed/publication.yaml`
- **Schema Class**: `ArticleSchema`

### Field Specifications (Silver/Gold)

| Field | Type | Nullable | Description | Constraints |
|---|---|---|---|---|
| `entity_id` | `str` | False | Unique business identifier for the entity. | - |
| `content_hash` | `str` | False | SHA256 hash of canonical record representation (64 hex chars). | <Check str_matches: str_matches('^[a-f0-9]{64}$')> |
| `_run_id` | `object` | False | Correlation ID for the pipeline run. | - |
| `_run_type` | `str` | False | Type of pipeline run. | <Check isin: isin(['incremental', 'backfill', 'rebuild'])> |
| `_source_batch_id` | `object` | True | Batch context ID from the source. | - |
| `_ingestion_ts` | `str` | False | Timestamp when the record was ingested (UTC, ISO 8601 format). | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$')> |
| `_dq_warn` | `bool` | False | Flag for data quality warnings. | - |
| `_dq_error` | `bool` | False | Flag for data quality errors. | - |
| `_index` | `int64` | False | Sequential index of the record in the pipeline run. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `pmid` | `str` | False | PubMed ID (PK, numeric string) | <Check str_matches: str_matches('^\d+$')><br><Check pmid_positive> |
| `doi` | `str` | True | Digital Object Identifier | <Check doi_format> |
| `pmc_id` | `str` | True | PubMed Central ID | <Check str_matches: str_matches('^PMC\d+$')><br><Check pmc_id_format> |
| `title` | `str` | False | Article title (required) | <Check title_not_empty> |
| `abstract` | `str` | True | Publication abstract | - |
| `authors` | `str` | True | JSON array of author names (PII hashed) | - |
| `journal` | `str` | True | Journal name | - |
| `year` | `int64` | True | Publication year | <Check greater_than_or_equal_to: greater_than_or_equal_to(1800)><br><Check less_than_or_equal_to: less_than_or_equal_to(2100)><br><Check year_range> |
| `publication_date` | `str` | True | Publication date (YYYY-MM-DD) | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}$')> |
| `doc_type` | `str` | True | Document type (PUBLICATION, PREPRINT, PATENT, etc.) | - |
| `language` | `str` | True | MARC language code (e.g., 'eng') | <Check language_length> |
| `citation_count` | `Int64` | True | Number of citations (provider-dependent availability) | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `is_oa` | `bool` | True | Is Open Access (provider-dependent availability) | - |
| `_lookup_method` | `str` | True | How record was resolved: direct, doi, pmid, title_fallback, title_only | <Check isin: isin(['direct', 'doi', 'pmid', 'title_fallback', 'title_only', 'unknown'])> |
| `_original_id` | `str` | True | Original identifier from input (for fallback records) | - |
| `source` | `str` | True | Data source identifier (e.g., pubmed, crossref, openalex) | - |
| `abstract_structured` | `bool` | True | Whether abstract has NLM sections | - |
| `vernacular_title` | `str` | True | Original non-English title | - |
| `journal_title` | `str` | True | Full journal name | - |
| `journal_iso_abbrev` | `str` | True | ISO journal abbreviation | - |
| `journal_issn` | `str` | True | ISSN (print or electronic) | <Check journal_issn_format> |
| `journal_issn_type` | `str` | True | ISSN type | <Check journal_issn_type_values> |
| `nlm_unique_id` | `str` | True | NLM catalog ID | - |
| `country` | `str` | True | Journal country of publication | - |
| `medline_pgn` | `str` | True | Page numbers (MEDLINE format) | - |
| `pub_month` | `int64` | True | Publication month | <Check pub_month_range> |
| `pub_day` | `int64` | True | Publication day | <Check pub_day_range> |
| `publication_status` | `str` | True | Publication status | <Check publication_status_values> |
| `publication_type_list` | `str` | True | JSON array of publication types | - |
| `date_completed` | `date` | True | MEDLINE processing completion date | - |
| `date_revised` | `date` | True | Record revision date | - |
| `citation_subset` | `str` | True | Citation subset codes (e.g., 'AIM') | - |
| `author_count` | `int64` | True | Number of authors | <Check author_count_non_negative> |
| `mesh_heading_count` | `int64` | True | Number of MeSH headings | <Check mesh_heading_count_non_negative> |
| `keyword_count` | `int64` | True | Number of keywords | <Check keyword_count_non_negative> |
| `grant_count` | `int64` | True | Number of grants | <Check grant_count_non_negative> |
| `reference_count` | `int64` | True | Number of references | <Check reference_count_non_negative> |
| `chemical_count` | `int64` | True | Number of chemicals | <Check chemical_count_non_negative> |

[Back to Top](#table-of-contents)


---

## SEMANTICSCHOLAR / publication: semanticscholar_publication <a name='semanticscholar-publication'></a>

- **Config**: `configs/pipelines/semanticscholar/publication.yaml`
- **Schema Class**: `PublicationBaseSchema`

### Field Specifications (Silver/Gold)

| Field | Type | Nullable | Description | Constraints |
|---|---|---|---|---|
| `entity_id` | `str` | False | Unique business identifier for the entity. | - |
| `content_hash` | `str` | False | SHA256 hash of canonical record representation (64 hex chars). | <Check str_matches: str_matches('^[a-f0-9]{64}$')> |
| `_run_id` | `object` | False | Correlation ID for the pipeline run. | - |
| `_run_type` | `str` | False | Type of pipeline run. | <Check isin: isin(['incremental', 'backfill', 'rebuild'])> |
| `_source_batch_id` | `object` | True | Batch context ID from the source. | - |
| `_ingestion_ts` | `str` | False | Timestamp when the record was ingested (UTC, ISO 8601 format). | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$')> |
| `_dq_warn` | `bool` | False | Flag for data quality warnings. | - |
| `_dq_error` | `bool` | False | Flag for data quality errors. | - |
| `_index` | `int64` | False | Sequential index of the record in the pipeline run. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `pmid` | `str` | True | PubMed ID (numeric string) | <Check str_matches: str_matches('^\d+$')> |
| `doi` | `str` | True | Digital Object Identifier (lowercase) | <Check str_matches: str_matches('^10\.\d{4,}/.+$')> |
| `pmc_id` | `str` | True | PubMed Central ID | <Check str_matches: str_matches('^PMC\d+$')> |
| `title` | `str` | True | Publication title | - |
| `abstract` | `str` | True | Publication abstract | - |
| `authors` | `str` | True | JSON array of author names (PII hashed) | - |
| `journal` | `str` | True | Journal name | - |
| `year` | `int64` | True | Publication year | <Check greater_than_or_equal_to: greater_than_or_equal_to(1800)><br><Check less_than_or_equal_to: less_than_or_equal_to(2100)> |
| `publication_date` | `str` | True | Publication date (YYYY-MM-DD) | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}$')> |
| `doc_type` | `str` | True | Document type (PUBLICATION, PREPRINT, PATENT, etc.) | - |
| `language` | `str` | True | Language code (ISO 639-1 or MARC) | - |
| `citation_count` | `Int64` | True | Number of citations (provider-dependent availability) | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `is_oa` | `bool` | True | Is Open Access (provider-dependent availability) | - |
| `_lookup_method` | `str` | True | How record was resolved: direct, doi, pmid, title_fallback, title_only | <Check isin: isin(['direct', 'doi', 'pmid', 'title_fallback', 'title_only', 'unknown'])> |
| `_original_id` | `str` | True | Original identifier from input (for fallback records) | - |
| `source` | `str` | True | Data source identifier (e.g., pubmed, crossref, openalex) | - |

[Back to Top](#table-of-contents)


---

## UNIPROT / idmapping: uniprot_idmapping <a name='uniprot-idmapping'></a>

- **Config**: `configs/pipelines/uniprot/idmapping.yaml`

**⚠️ Warning: No Schema Class Found**

## UNIPROT / protein: uniprot_protein <a name='uniprot-protein'></a>

- **Config**: `configs/pipelines/uniprot/protein.yaml`
- **Schema Class**: `UniprotTargetSchema`

### Field Specifications (Silver/Gold)

| Field | Type | Nullable | Description | Constraints |
|---|---|---|---|---|
| `entity_id` | `str` | False | Unique business identifier for the entity. | - |
| `content_hash` | `str` | False | SHA256 hash of canonical record representation (64 hex chars). | <Check str_matches: str_matches('^[a-f0-9]{64}$')> |
| `_run_id` | `object` | False | Correlation ID for the pipeline run. | - |
| `_run_type` | `str` | False | Type of pipeline run. | <Check isin: isin(['incremental', 'backfill', 'rebuild'])> |
| `_source_batch_id` | `object` | True | Batch context ID from the source. | - |
| `_ingestion_ts` | `str` | False | Timestamp when the record was ingested (UTC, ISO 8601 format). | <Check str_matches: str_matches('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$')> |
| `_dq_warn` | `bool` | False | Flag for data quality warnings. | - |
| `_dq_error` | `bool` | False | Flag for data quality errors. | - |
| `_index` | `int64` | False | Sequential index of the record in the pipeline run. | <Check greater_than_or_equal_to: greater_than_or_equal_to(0)> |
| `accession` | `str` | False | UniProt primary accession (PK) | <Check accession_format> |
| `entry_name` | `str` | False | Entry name (e.g., MK01_HUMAN) | <Check entry_name_format> |
| `entry_type` | `str` | True | Entry type (Swiss-Prot reviewed / TrEMBL unreviewed) | <Check entry_type_values> |
| `secondary_accessions` | `str` | True | JSON array of secondary accessions | - |
| `protein_name` | `str` | True | Recommended protein name | - |
| `protein_short_names` | `str` | True | JSON array of short names | - |
| `protein_alternative_names` | `str` | True | JSON array of alternative protein names | - |
| `protein_ec_numbers` | `str` | True | JSON array of EC numbers | - |
| `flag` | `str` | True | Protein sequence completeness flag (Fragment/Precursor) | <Check flag_values> |
| `gene_primary` | `str` | True | Primary gene name | - |
| `gene_synonyms` | `str` | True | JSON array of gene synonyms | - |
| `gene_orf_names` | `str` | True | JSON array of ORF names | - |
| `organism_scientific` | `str` | True | Scientific organism name | - |
| `organism_common` | `str` | True | Common organism name | - |
| `taxonomy_id` | `int64` | True | NCBI Taxonomy ID | <Check taxonomy_id_positive> |
| `lineage` | `str` | True | JSON array of taxonomic lineage | - |
| `protein_existence` | `str` | True | Evidence level for existence | <Check protein_existence_values> |
| `annotation_score` | `int64` | True | Annotation quality (1-5 stars) | <Check annotation_score_range> |
| `reviewed` | `bool` | False | Swiss-Prot (True) vs TrEMBL (False) | - |
| `sequence` | `str` | False | Amino acid sequence | <Check sequence_format> |
| `sequence_length` | `int64` | False | Sequence length | <Check sequence_length_positive> |
| `sequence_mass` | `int64` | True | Molecular mass (Da) | <Check sequence_mass_positive> |
| `sequence_checksum` | `str` | True | CRC64 checksum | - |
| `sequence_modified` | `date` | True | Sequence last modified date | - |
| `entry_version` | `int64` | True | Entry version number | <Check entry_version_positive> |
| `entry_created` | `date` | True | Entry creation date | - |
| `entry_modified` | `date` | True | Entry last modified date | - |
| `function_comment` | `str` | True | JSON array of function descriptions | - |
| `catalytic_activity` | `str` | True | JSON array of catalytic reactions | - |
| `activity_regulation` | `str` | True | JSON array of activity regulation info | - |
| `subunit` | `str` | True | JSON array of subunit structure info | - |
| `pathway` | `str` | True | JSON array of pathways | - |
| `subcellular_location` | `str` | True | JSON array of subcellular locations | - |
| `tissue_specificity` | `str` | True | Tissue expression pattern | - |
| `alternative_products` | `str` | True | JSON array of alternative splicing/isoforms | - |
| `disease_involvement` | `str` | True | JSON array of disease associations | - |
| `pharmaceutical_use` | `str` | True | Pharmaceutical applications | - |
| `similarity_comment` | `str` | True | Family and domain information | - |
| `caution` | `str` | True | Warnings about this entry | - |
| `go_terms` | `str` | True | JSON array of GO terms with evidence codes | - |
| `drugbank_ids` | `str` | True | JSON array of DrugBank identifiers | - |
| `chembl_ids` | `str` | True | JSON array of ChEMBL target identifiers | - |
| `guidetopharmacology_ids` | `str` | True | JSON array of Guide to Pharmacology identifiers | - |
| `features` | `str` | True | JSON array of sequence features | - |
| `keywords` | `str` | True | JSON array of UniProt keywords | - |
| `cross_reference_count` | `int64` | True | Number of database cross-references | <Check cross_reference_count_non_negative> |
| `feature_count` | `int64` | True | Number of sequence features | <Check feature_count_non_negative> |
| `keyword_count` | `int64` | True | Number of keywords | <Check keyword_count_non_negative> |
| `publication_count` | `int64` | True | Number of publications | <Check publication_count_non_negative> |
| `isoform_count` | `int64` | True | Number of isoforms | <Check isoform_count_non_negative> |

[Back to Top](#table-of-contents)


---

## Findings & Recommendations

### 1. Schema Fragmentation (Publication Entity)
Multiple independent schema definitions exist for the "Publication" concept, leading to field divergence.

*   **ChEMBL**: `ChemblPublicationSchema` (fields: `document_chembl_id`, `journal_full_title`, `document_year` as float)
*   **Crossref**: `PublicationSchema` (fields: `published_date` as date, `type` enum differs)
*   **OpenAlex**: `OpenAlexPublicationSchema` (fields: `publication_date` as str, `year` as Int64)
*   **PubMed**: `ArticleSchema` (fields: `pub_day`, `pub_month`, `medline_pgn`)
*   **SemanticScholar**: `PublicationBaseSchema` (fields: `year` as int64)

**Recommendation**: Consolidate into a `UnifiedPublicationSchema` in the domain layer, with provider-specific extensions only where necessary. Enforce `PublicationBaseSchema` inheritance strictly.

### 2. Data Type Inconsistencies
Common fields have different types across schemas:

*   **Year**:
    *   `int64` (SemanticScholar, PubMed)
    *   `Int64` (OpenAlex - nullable)
    *   `float64` (ChEMBL `document_year` in ActivitySchema)
*   **Dates**:
    *   `str` (YYYY-MM-DD): OpenAlex, SemanticScholar, PubMed (`publication_date`)
    *   `date`: Crossref (`published_date`)
*   **Counts**:
    *   `int64` vs `Int64` (nullable integer)

**Recommendation**: Standardize on `Int64` (nullable) for optional integer fields and ISO 8601 strings for dates to ensure serialization compatibility.

### 3. Naming Conventions
Discrepancies exist between Pipeline Config `entity_type` and Schema Class names:

*   `chembl/document` -> `ChemblPublicationSchema`
*   `chembl/protein_class` -> `ProteinClassificationSchema`
*   `pubmed/publication` -> `ArticleSchema`

**Recommendation**: Align configuration `entity_type` with domain vocabulary or implement a strict mapping registry to avoid implicit convention failures.

### 4. Missing Schemas
*   `uniprot/idmapping`: No explicit schema definition found.

**Recommendation**: Define `IdMappingSchema` to ensure data quality contracts for this pipeline.
