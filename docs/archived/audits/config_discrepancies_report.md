# Config Discrepancies Report

Generated: 2026-01-06T18:30:06.183527

Total configs: 20
Total unique parameters: 129

## 1. Parameters by Category

### batch_size

| Parameter | Presence |
|-----------|----------|
| `batch_size` | 2/20 |

### checkpoint_interval

| Parameter | Presence |
|-----------|----------|
| `checkpoint_interval` | 2/20 |

### circuit_breaker

| Parameter | Presence |
|-----------|----------|
| `circuit_breaker` | 2/20 |
| `circuit_breaker.failure_threshold` | 2/20 |
| `circuit_breaker.recovery_timeout` | 2/20 |

### defaults_version

| Parameter | Presence |
|-----------|----------|
| `defaults_version` | 1/20 |

### description

| Parameter | Presence |
|-----------|----------|
| `description` | 19/20 |

### dq_rules

| Parameter | Presence |
|-----------|----------|
| `dq_rules` | 2/20 |
| `dq_rules.hard_fail_threshold` | 2/20 |
| `dq_rules.soft_fail_threshold` | 2/20 |

### entity_type

| Parameter | Presence |
|-----------|----------|
| `entity_type` | 19/20 |

### gold_filters

| Parameter | Presence |
|-----------|----------|
| `gold_filters` | 19/20 |
| `gold_filters.columns` | 11/20 |
| `gold_filters.list_contains` | 1/20 |
| `gold_filters.list_lengths` | 1/20 |
| `gold_filters.ranges` | 6/20 |
| `gold_filters.required_fields` | 19/20 |
| `gold_filters.columns.assay_type` | 2/20 |
| `gold_filters.columns.component_type` | 1/20 |
| `gold_filters.columns.confidence_score` | 1/20 |
| `gold_filters.columns.doc_type` | 1/20 |
| `gold_filters.columns.downgraded` | 1/20 |
| `gold_filters.columns.inorganic_flag` | 1/20 |
| `gold_filters.columns.molecule_type` | 1/20 |
| `gold_filters.columns.potential_duplicate` | 1/20 |
| `gold_filters.columns.relationship_type` | 1/20 |
| `gold_filters.columns.reviewed` | 1/20 |
| `gold_filters.columns.standard_relation` | 1/20 |
| `gold_filters.columns.standard_type` | 1/20 |
| `gold_filters.columns.standard_units` | 1/20 |
| `gold_filters.columns.structure_type` | 1/20 |
| `gold_filters.columns.target_type` | 1/20 |
| `gold_filters.columns.term_type` | 1/20 |
| `gold_filters.list_contains.component_types` | 1/20 |
| `gold_filters.list_lengths.component_accessions` | 1/20 |
| `gold_filters.list_lengths.component_ids` | 1/20 |
| `gold_filters.ranges.max_tani` | 1/20 |
| `gold_filters.ranges.standard_value` | 1/20 |
| `gold_filters.ranges.year` | 4/20 |
| `gold_filters.list_contains.component_types.mode` | 1/20 |
| `gold_filters.list_contains.component_types.values` | 1/20 |
| `gold_filters.list_lengths.component_accessions.max` | 1/20 |
| `gold_filters.list_lengths.component_accessions.min` | 1/20 |
| `gold_filters.list_lengths.component_ids.min` | 1/20 |
| `gold_filters.ranges.max_tani.include_min` | 1/20 |
| `gold_filters.ranges.max_tani.min` | 1/20 |
| `gold_filters.ranges.standard_value.include_min` | 1/20 |
| `gold_filters.ranges.standard_value.min` | 1/20 |
| `gold_filters.ranges.year.include_min` | 1/20 |
| `gold_filters.ranges.year.max` | 3/20 |
| `gold_filters.ranges.year.min` | 4/20 |

### gold_table

| Parameter | Presence |
|-----------|----------|
| `gold_table` | 8/20 |

### input_filter

| Parameter | Presence |
|-----------|----------|
| `input_filter` | 20/20 |
| `input_filter.batch_size` | 17/20 |
| `input_filter.column_name` | 16/20 |
| `input_filter.enabled` | 20/20 |
| `input_filter.fallback_column` | 3/20 |
| `input_filter.filter_field` | 16/20 |
| `input_filter.source_path` | 16/20 |

### maintenance

| Parameter | Presence |
|-----------|----------|
| `maintenance` | 1/20 |
| `maintenance.auto_vacuum` | 1/20 |
| `maintenance.vacuum_retention_days` | 1/20 |

### pipeline_name

| Parameter | Presence |
|-----------|----------|
| `pipeline_name` | 19/20 |

### primary_keys

| Parameter | Presence |
|-----------|----------|
| `primary_keys` | 19/20 |

### provider

| Parameter | Presence |
|-----------|----------|
| `provider` | 19/20 |

### rate_limit

| Parameter | Presence |
|-----------|----------|
| `rate_limit` | 1/20 |
| `rate_limit.burst` | 1/20 |
| `rate_limit.requests_per_second` | 1/20 |

### silver_table

| Parameter | Presence |
|-----------|----------|
| `silver_table` | 19/20 |

### sink

| Parameter | Presence |
|-----------|----------|
| `sink` | 20/20 |
| `sink.bronze` | 20/20 |
| `sink.gold` | 20/20 |
| `sink.silver` | 20/20 |
| `sink.bronze.deterministic` | 1/20 |
| `sink.bronze.enabled` | 1/20 |
| `sink.bronze.format` | 1/20 |
| `sink.bronze.path` | 18/20 |
| `sink.bronze.save_json` | 1/20 |
| `sink.gold.csv_export` | 20/20 |
| `sink.gold.deterministic` | 1/20 |
| `sink.gold.enabled` | 2/20 |
| `sink.gold.format` | 2/20 |
| `sink.gold.mode` | 2/20 |
| `sink.gold.path` | 19/20 |
| `sink.gold.sort_by` | 4/20 |
| `sink.gold.validation` | 1/20 |
| `sink.silver.classification` | 2/20 |
| `sink.silver.csv_export` | 20/20 |
| `sink.silver.deterministic` | 1/20 |
| `sink.silver.forensic_retention` | 1/20 |
| `sink.silver.format` | 2/20 |
| `sink.silver.mode` | 2/20 |
| `sink.silver.on_schema_mismatch` | 1/20 |
| `sink.silver.partition_by` | 16/20 |
| `sink.silver.path` | 19/20 |
| `sink.silver.primary_key` | 17/20 |
| `sink.silver.sort_by` | 4/20 |
| `sink.gold.csv_export.delimiter` | 1/20 |
| `sink.gold.csv_export.enabled` | 2/20 |
| `sink.gold.csv_export.encoding` | 1/20 |
| `sink.gold.csv_export.header` | 1/20 |
| `sink.gold.csv_export.path` | 19/20 |
| `sink.gold.sort_by.ascending` | 4/20 |
| `sink.gold.sort_by.columns` | 4/20 |
| `sink.gold.validation.strict` | 1/20 |
| `sink.silver.csv_export.delimiter` | 2/20 |
| `sink.silver.csv_export.enabled` | 2/20 |
| `sink.silver.csv_export.encoding` | 2/20 |
| `sink.silver.csv_export.header` | 2/20 |
| `sink.silver.csv_export.path` | 19/20 |
| `sink.silver.sort_by.ascending` | 4/20 |
| `sink.silver.sort_by.columns` | 4/20 |

### source

| Parameter | Presence |
|-----------|----------|
| `source` | 3/20 |
| `source.api` | 1/20 |
| `source.api_key` | 1/20 |
| `source.batch_size` | 1/20 |
| `source.email` | 2/20 |
| `source.input_path` | 1/20 |
| `source.load_strategy` | 1/20 |
| `source.search_term` | 1/20 |
| `source.type` | 1/20 |
| `source.api.base_url` | 1/20 |
| `source.api.from_db` | 1/20 |
| `source.api.to_db` | 1/20 |

### source_file

| Parameter | Presence |
|-----------|----------|
| `source_file` | 18/20 |

### transform

| Parameter | Presence |
|-----------|----------|
| `transform` | 7/20 |
| `transform.steps` | 7/20 |
| `transform.version` | 7/20 |

### version

| Parameter | Presence |
|-----------|----------|
| `version` | 19/20 |

## 2. Entity Config Comparison

| Config | pipeline_name | provider | entity_type | version | description | primary_keys | silver_table | gold_table | source_file | source | transform | dq_rules | circuit_breaker | rate_limit | gold_filters | sink | input_filter |
|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|
| chembl/activity | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — | — | — | — | ✓ | ✓ | ✓ |
| chembl/assay | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — | — | — | — | ✓ | ✓ | ✓ |
| chembl/assay_parameters | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — | — | — | — | ✓ | ✓ | ✓ |
| chembl/cell_line | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — | — | — | — | ✓ | ✓ | ✓ |
| chembl/compound_record | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — | — | — | — | ✓ | ✓ | ✓ |
| chembl/document | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — | — | — | — | ✓ | ✓ | ✓ |
| chembl/document_similarity | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — | — | — | — | ✓ | ✓ | ✓ |
| chembl/document_term | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — | — | — | — | ✓ | ✓ | ✓ |
| chembl/molecule | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — | — | — | — | ✓ | ✓ | ✓ |
| chembl/protein_class | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | ✓ | ✓ | ✓ |
| chembl/target | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — | — | — | — | ✓ | ✓ | ✓ |
| chembl/target_component | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | ✓ | ✓ | ✓ |
| crossref/publication_enrichment | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | ✓ | — | — | — | ✓ | ✓ | ✓ |
| openalex/publication | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | ✓ | ✓ | ✓ |
| pubchem/compound | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — | — | ✓ | ✓ | ✓ |
| pubmed/publications | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | ✓ | ✓ | ✓ |
| semanticscholar/publication | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — | — | ✓ | ✓ | ✓ |
| uniprot/idmapping | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| uniprot/protein | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — | — | ✓ | ✓ | ✓ |

## 3. Discrepancy Categories

### A. Missing in _defaults (should be added)

- `batch_size` - present in: chembl/protein_class, chembl/target_component
- `checkpoint_interval` - present in: chembl/protein_class, chembl/target_component
- `description` - present in: chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/document, chembl/document_similarity, chembl/document_term, chembl/molecule, chembl/protein_class, chembl/target, chembl/target_component, crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- `entity_type` - present in: chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/document, chembl/document_similarity, chembl/document_term, chembl/molecule, chembl/protein_class, chembl/target, chembl/target_component, crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- `gold_filters` - present in: chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/document, chembl/document_similarity, chembl/document_term, chembl/molecule, chembl/protein_class, chembl/target, chembl/target_component, crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- `gold_table` - present in: chembl/protein_class, chembl/target_component, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- `pipeline_name` - present in: chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/document, chembl/document_similarity, chembl/document_term, chembl/molecule, chembl/protein_class, chembl/target, chembl/target_component, crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- `primary_keys` - present in: chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/document, chembl/document_similarity, chembl/document_term, chembl/molecule, chembl/protein_class, chembl/target, chembl/target_component, crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- `provider` - present in: chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/document, chembl/document_similarity, chembl/document_term, chembl/molecule, chembl/protein_class, chembl/target, chembl/target_component, crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- `rate_limit` - present in: uniprot/idmapping
- `rate_limit.burst` - present in: uniprot/idmapping
- `rate_limit.requests_per_second` - present in: uniprot/idmapping
- `silver_table` - present in: chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/document, chembl/document_similarity, chembl/document_term, chembl/molecule, chembl/protein_class, chembl/target, chembl/target_component, crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- `source` - present in: openalex/publication, pubmed/publications, uniprot/idmapping
- `source.api` - present in: uniprot/idmapping
- `source.api.base_url` - present in: uniprot/idmapping
- `source.api.from_db` - present in: uniprot/idmapping
- `source.api.to_db` - present in: uniprot/idmapping
- `source.api_key` - present in: pubmed/publications
- `source.batch_size` - present in: openalex/publication
- `source.email` - present in: openalex/publication, pubmed/publications
- `source.input_path` - present in: uniprot/idmapping
- `source.load_strategy` - present in: uniprot/idmapping
- `source.search_term` - present in: pubmed/publications
- `source.type` - present in: uniprot/idmapping
- `source_file` - present in: chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/document, chembl/document_similarity, chembl/document_term, chembl/molecule, chembl/protein_class, chembl/target, chembl/target_component, crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/protein
- `transform` - present in: crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- `transform.steps` - present in: crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- `transform.version` - present in: crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- `version` - present in: chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/document, chembl/document_similarity, chembl/document_term, chembl/molecule, chembl/protein_class, chembl/target, chembl/target_component, crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein

### B. Inconsistent presence across entity configs

- `batch_size`
  - Present in (2): chembl/protein_class, chembl/target_component
  - Missing in (17): chembl/document_similarity, pubchem/compound, crossref/publication_enrichment, chembl/document_term, chembl/assay_parameters, semanticscholar/publication, chembl/target, chembl/activity, chembl/molecule, openalex/publication, pubmed/publications, chembl/assay, chembl/cell_line, chembl/document, chembl/compound_record, uniprot/idmapping, uniprot/protein
- `checkpoint_interval`
  - Present in (2): chembl/protein_class, chembl/target_component
  - Missing in (17): chembl/document_similarity, pubchem/compound, crossref/publication_enrichment, chembl/document_term, chembl/assay_parameters, semanticscholar/publication, chembl/target, chembl/activity, chembl/molecule, openalex/publication, pubmed/publications, chembl/assay, chembl/cell_line, chembl/document, chembl/compound_record, uniprot/idmapping, uniprot/protein
- `gold_filters.columns`
  - Present in (11): chembl/activity, chembl/assay, chembl/document, chembl/document_term, chembl/molecule, chembl/protein_class, chembl/target, chembl/target_component, pubchem/compound, pubmed/publications, uniprot/protein
  - Missing in (8): openalex/publication, chembl/document_similarity, crossref/publication_enrichment, chembl/cell_line, chembl/compound_record, chembl/assay_parameters, uniprot/idmapping, semanticscholar/publication
- `gold_filters.columns.assay_type`
  - Present in (2): chembl/activity, chembl/assay
  - Missing in (17): chembl/protein_class, chembl/document_similarity, pubchem/compound, crossref/publication_enrichment, chembl/document_term, chembl/assay_parameters, semanticscholar/publication, chembl/target, chembl/molecule, openalex/publication, pubmed/publications, chembl/target_component, chembl/cell_line, chembl/document, chembl/compound_record, uniprot/idmapping, uniprot/protein
- `gold_filters.ranges`
  - Present in (6): chembl/activity, chembl/document, chembl/document_similarity, crossref/publication_enrichment, openalex/publication, semanticscholar/publication
  - Missing in (13): pubmed/publications, chembl/assay, chembl/protein_class, chembl/target_component, pubchem/compound, chembl/document_term, chembl/cell_line, chembl/compound_record, chembl/assay_parameters, uniprot/idmapping, uniprot/protein, chembl/target, chembl/molecule
- `gold_filters.ranges.year`
  - Present in (4): chembl/document, crossref/publication_enrichment, openalex/publication, semanticscholar/publication
  - Missing in (15): pubmed/publications, chembl/assay, chembl/protein_class, chembl/document_similarity, chembl/target_component, pubchem/compound, chembl/document_term, chembl/cell_line, chembl/compound_record, chembl/assay_parameters, uniprot/idmapping, uniprot/protein, chembl/target, chembl/activity, chembl/molecule
- `gold_filters.ranges.year.max`
  - Present in (3): crossref/publication_enrichment, openalex/publication, semanticscholar/publication
  - Missing in (16): chembl/protein_class, chembl/document_similarity, pubchem/compound, chembl/document_term, chembl/assay_parameters, chembl/target, chembl/activity, chembl/molecule, pubmed/publications, chembl/assay, chembl/target_component, chembl/cell_line, chembl/document, chembl/compound_record, uniprot/idmapping, uniprot/protein
- `gold_filters.ranges.year.min`
  - Present in (4): chembl/document, crossref/publication_enrichment, openalex/publication, semanticscholar/publication
  - Missing in (15): pubmed/publications, chembl/assay, chembl/protein_class, chembl/document_similarity, chembl/target_component, pubchem/compound, chembl/document_term, chembl/cell_line, chembl/compound_record, chembl/assay_parameters, uniprot/idmapping, uniprot/protein, chembl/target, chembl/activity, chembl/molecule
- `gold_table`
  - Present in (8): chembl/protein_class, chembl/target_component, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
  - Missing in (11): chembl/assay, chembl/document_similarity, crossref/publication_enrichment, chembl/document_term, chembl/cell_line, chembl/document, chembl/compound_record, chembl/assay_parameters, chembl/target, chembl/activity, chembl/molecule
- `input_filter.batch_size`
  - Present in (16): chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/document, chembl/document_term, chembl/molecule, chembl/target, chembl/target_component, crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/protein
  - Missing in (3): uniprot/idmapping, chembl/protein_class, chembl/document_similarity
- `input_filter.column_name`
  - Present in (16): chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/document, chembl/document_term, chembl/molecule, chembl/target, chembl/target_component, crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/protein
  - Missing in (3): uniprot/idmapping, chembl/protein_class, chembl/document_similarity
- `input_filter.fallback_column`
  - Present in (3): crossref/publication_enrichment, openalex/publication, semanticscholar/publication
  - Missing in (16): chembl/protein_class, chembl/document_similarity, pubchem/compound, chembl/document_term, chembl/assay_parameters, chembl/target, chembl/activity, chembl/molecule, pubmed/publications, chembl/assay, chembl/target_component, chembl/cell_line, chembl/document, chembl/compound_record, uniprot/idmapping, uniprot/protein
- `input_filter.filter_field`
  - Present in (16): chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/document, chembl/document_term, chembl/molecule, chembl/target, chembl/target_component, crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/protein
  - Missing in (3): uniprot/idmapping, chembl/protein_class, chembl/document_similarity
- `input_filter.source_path`
  - Present in (16): chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/document, chembl/document_term, chembl/molecule, chembl/target, chembl/target_component, crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/protein
  - Missing in (3): uniprot/idmapping, chembl/protein_class, chembl/document_similarity
- `sink.bronze.path`
  - Present in (18): chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/document, chembl/document_similarity, chembl/document_term, chembl/molecule, chembl/protein_class, chembl/target, chembl/target_component, crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/protein
  - Missing in (1): uniprot/idmapping
- `sink.gold.sort_by`
  - Present in (4): chembl/cell_line, chembl/compound_record, chembl/protein_class, chembl/target
  - Missing in (15): openalex/publication, pubmed/publications, chembl/assay, chembl/document_similarity, chembl/target_component, pubchem/compound, crossref/publication_enrichment, chembl/document_term, chembl/document, chembl/assay_parameters, uniprot/idmapping, uniprot/protein, semanticscholar/publication, chembl/activity, chembl/molecule
- `sink.gold.sort_by.ascending`
  - Present in (4): chembl/cell_line, chembl/compound_record, chembl/protein_class, chembl/target
  - Missing in (15): openalex/publication, pubmed/publications, chembl/assay, chembl/document_similarity, chembl/target_component, pubchem/compound, crossref/publication_enrichment, chembl/document_term, chembl/document, chembl/assay_parameters, uniprot/idmapping, uniprot/protein, semanticscholar/publication, chembl/activity, chembl/molecule
- `sink.gold.sort_by.columns`
  - Present in (4): chembl/cell_line, chembl/compound_record, chembl/protein_class, chembl/target
  - Missing in (15): openalex/publication, pubmed/publications, chembl/assay, chembl/document_similarity, chembl/target_component, pubchem/compound, crossref/publication_enrichment, chembl/document_term, chembl/document, chembl/assay_parameters, uniprot/idmapping, uniprot/protein, semanticscholar/publication, chembl/activity, chembl/molecule
- `sink.silver.partition_by`
  - Present in (16): chembl/assay, chembl/assay_parameters, chembl/compound_record, chembl/document, chembl/document_similarity, chembl/document_term, chembl/molecule, chembl/protein_class, chembl/target, chembl/target_component, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
  - Missing in (3): crossref/publication_enrichment, chembl/cell_line, chembl/activity
- `sink.silver.primary_key`
  - Present in (17): chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/document, chembl/document_similarity, chembl/document_term, chembl/molecule, chembl/target, crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
  - Missing in (2): chembl/protein_class, chembl/target_component
- `sink.silver.sort_by`
  - Present in (4): chembl/cell_line, chembl/compound_record, chembl/protein_class, chembl/target
  - Missing in (15): openalex/publication, pubmed/publications, chembl/assay, chembl/document_similarity, chembl/target_component, pubchem/compound, crossref/publication_enrichment, chembl/document_term, chembl/document, chembl/assay_parameters, uniprot/idmapping, uniprot/protein, semanticscholar/publication, chembl/activity, chembl/molecule
- `sink.silver.sort_by.ascending`
  - Present in (4): chembl/cell_line, chembl/compound_record, chembl/protein_class, chembl/target
  - Missing in (15): openalex/publication, pubmed/publications, chembl/assay, chembl/document_similarity, chembl/target_component, pubchem/compound, crossref/publication_enrichment, chembl/document_term, chembl/document, chembl/assay_parameters, uniprot/idmapping, uniprot/protein, semanticscholar/publication, chembl/activity, chembl/molecule
- `sink.silver.sort_by.columns`
  - Present in (4): chembl/cell_line, chembl/compound_record, chembl/protein_class, chembl/target
  - Missing in (15): openalex/publication, pubmed/publications, chembl/assay, chembl/document_similarity, chembl/target_component, pubchem/compound, crossref/publication_enrichment, chembl/document_term, chembl/document, chembl/assay_parameters, uniprot/idmapping, uniprot/protein, semanticscholar/publication, chembl/activity, chembl/molecule
- `source`
  - Present in (3): openalex/publication, pubmed/publications, uniprot/idmapping
  - Missing in (16): chembl/protein_class, chembl/document_similarity, pubchem/compound, crossref/publication_enrichment, chembl/document_term, chembl/assay_parameters, semanticscholar/publication, chembl/target, chembl/activity, chembl/molecule, chembl/assay, chembl/target_component, chembl/cell_line, chembl/document, chembl/compound_record, uniprot/protein
- `source.email`
  - Present in (2): openalex/publication, pubmed/publications
  - Missing in (17): chembl/protein_class, chembl/document_similarity, pubchem/compound, crossref/publication_enrichment, chembl/document_term, chembl/assay_parameters, semanticscholar/publication, chembl/target, chembl/activity, chembl/molecule, chembl/assay, chembl/target_component, chembl/cell_line, chembl/document, chembl/compound_record, uniprot/idmapping, uniprot/protein
- `source_file`
  - Present in (18): chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/document, chembl/document_similarity, chembl/document_term, chembl/molecule, chembl/protein_class, chembl/target, chembl/target_component, crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/protein
  - Missing in (1): uniprot/idmapping
- `transform`
  - Present in (7): crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
  - Missing in (12): chembl/assay, chembl/protein_class, chembl/document_similarity, chembl/target_component, chembl/document_term, chembl/cell_line, chembl/document, chembl/compound_record, chembl/assay_parameters, chembl/target, chembl/activity, chembl/molecule
- `transform.steps`
  - Present in (7): crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
  - Missing in (12): chembl/assay, chembl/protein_class, chembl/document_similarity, chembl/target_component, chembl/document_term, chembl/cell_line, chembl/document, chembl/compound_record, chembl/assay_parameters, chembl/target, chembl/activity, chembl/molecule
- `transform.version`
  - Present in (7): crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
  - Missing in (12): chembl/assay, chembl/protein_class, chembl/document_similarity, chembl/target_component, chembl/document_term, chembl/cell_line, chembl/document, chembl/compound_record, chembl/assay_parameters, chembl/target, chembl/activity, chembl/molecule

### C. Structural inconsistencies

#### source vs source_file

- Using `source`: openalex/publication, pubmed/publications, uniprot/idmapping
- Using `source_file`: chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/document, chembl/document_similarity, chembl/document_term, chembl/molecule, chembl/protein_class, chembl/target, chembl/target_component, crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/protein

#### transform block

- Has `transform`: crossref/publication_enrichment, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- No `transform`: chembl/assay, chembl/protein_class, chembl/document_similarity, chembl/target_component, chembl/document_term, chembl/cell_line, chembl/document, chembl/compound_record, chembl/assay_parameters, chembl/target, chembl/activity, chembl/molecule

#### gold_table presence

- Has `gold_table`: chembl/protein_class, chembl/target_component, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- Missing `gold_table`: chembl/assay, chembl/document_similarity, crossref/publication_enrichment, chembl/document_term, chembl/cell_line, chembl/document, chembl/compound_record, chembl/assay_parameters, chembl/target, chembl/activity, chembl/molecule
