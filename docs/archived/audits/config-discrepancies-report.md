# Config Discrepancies Report

Generated: 2026-01-23T09:37:25.950380

Total configs: 21
Total unique parameters: 176

## 1. Parameters by Category

### batch_size

| Parameter | Presence |
|-----------|----------|
| `batch_size` | 1/21 |

### checkpoint_interval

| Parameter | Presence |
|-----------|----------|
| `checkpoint_interval` | 1/21 |

### circuit_breaker

| Parameter | Presence |
|-----------|----------|
| `circuit_breaker` | 1/21 |
| `circuit_breaker.failure_threshold` | 1/21 |
| `circuit_breaker.recovery_timeout` | 1/21 |

### composite

| Parameter | Presence |
|-----------|----------|
| `composite` | 1/21 |
| `composite.dq_rules` | 1/21 |
| `composite.enrichers` | 1/21 |
| `composite.execution` | 1/21 |
| `composite.lineage` | 1/21 |
| `composite.merge` | 1/21 |
| `composite.name` | 1/21 |
| `composite.seed` | 1/21 |
| `composite.version` | 1/21 |
| `composite.dq_rules.enricher_overrides` | 1/21 |
| `composite.dq_rules.hard_fail_threshold` | 1/21 |
| `composite.dq_rules.required_fields` | 1/21 |
| `composite.dq_rules.soft_fail_threshold` | 1/21 |
| `composite.execution.checkpoint_enabled` | 1/21 |
| `composite.execution.max_concurrency` | 1/21 |
| `composite.execution.retry` | 1/21 |
| `composite.lineage.track_field_sources` | 1/21 |
| `composite.lineage.track_status` | 1/21 |
| `composite.lineage.track_timestamps` | 1/21 |
| `composite.merge.conflict_resolution` | 1/21 |
| `composite.merge.field_priorities` | 1/21 |
| `composite.merge.output` | 1/21 |
| `composite.merge.strategy` | 1/21 |
| `composite.seed.output_keys` | 1/21 |
| `composite.seed.pipeline` | 1/21 |
| `composite.seed.silver_table` | 1/21 |
| `composite.dq_rules.enricher_overrides.pubmed_publication` | 1/21 |
| `composite.dq_rules.enricher_overrides.semanticscholar_publication` | 1/21 |
| `composite.execution.retry.backoff_multiplier` | 1/21 |
| `composite.execution.retry.max_attempts` | 1/21 |
| `composite.merge.field_priorities.abstract` | 1/21 |
| `composite.merge.field_priorities.citations_count` | 1/21 |
| `composite.merge.field_priorities.concepts` | 1/21 |
| `composite.merge.field_priorities.mesh_terms` | 1/21 |
| `composite.merge.field_priorities.title` | 1/21 |
| `composite.merge.field_priorities.tldr` | 1/21 |
| `composite.merge.output.gold` | 1/21 |
| `composite.merge.output.silver` | 1/21 |
| `composite.dq_rules.enricher_overrides.pubmed_publication.hard_fail_threshold` | 1/21 |
| `composite.dq_rules.enricher_overrides.pubmed_publication.soft_fail_threshold` | 1/21 |
| `composite.dq_rules.enricher_overrides.semanticscholar_publication.hard_fail_threshold` | 1/21 |
| `composite.dq_rules.enricher_overrides.semanticscholar_publication.soft_fail_threshold` | 1/21 |

### description

| Parameter | Presence |
|-----------|----------|
| `description` | 19/21 |

### dq_config_file

| Parameter | Presence |
|-----------|----------|
| `dq_config_file` | 15/21 |

### dq_rules

| Parameter | Presence |
|-----------|----------|
| `dq_rules` | 6/21 |
| `dq_rules.conditional_validations` | 2/21 |
| `dq_rules.cross_field_validations` | 6/21 |
| `dq_rules.field_validations` | 6/21 |
| `dq_rules.hard_fail_threshold` | 1/21 |
| `dq_rules.invalid_record_policy` | 1/21 |
| `dq_rules.report` | 1/21 |
| `dq_rules.soft_fail_threshold` | 1/21 |
| `dq_rules.strict_validation` | 1/21 |
| `dq_rules.report.enabled` | 1/21 |
| `dq_rules.report.format` | 1/21 |
| `dq_rules.report.include_sample_failures` | 1/21 |
| `dq_rules.report.sample_size` | 1/21 |

### entity_type

| Parameter | Presence |
|-----------|----------|
| `entity_type` | 19/21 |

### filter_config_file

| Parameter | Presence |
|-----------|----------|
| `filter_config_file` | 5/21 |

### gold_filters

| Parameter | Presence |
|-----------|----------|
| `gold_filters` | 1/21 |
| `gold_filters.required_fields` | 1/21 |

### gold_table

| Parameter | Presence |
|-----------|----------|
| `gold_table` | 19/21 |

### input_filter

| Parameter | Presence |
|-----------|----------|
| `input_filter` | 1/21 |
| `input_filter.batch_size` | 1/21 |
| `input_filter.enabled` | 1/21 |

### maintenance

| Parameter | Presence |
|-----------|----------|
| `maintenance` | 1/21 |
| `maintenance.auto_vacuum` | 1/21 |
| `maintenance.vacuum_retention_days` | 1/21 |

### pipeline_name

| Parameter | Presence |
|-----------|----------|
| `pipeline_name` | 19/21 |

### primary_keys

| Parameter | Presence |
|-----------|----------|
| `primary_keys` | 19/21 |

### provider

| Parameter | Presence |
|-----------|----------|
| `provider` | 19/21 |

### schema_version

| Parameter | Presence |
|-----------|----------|
| `schema_version` | 1/21 |

### silver_table

| Parameter | Presence |
|-----------|----------|
| `silver_table` | 19/21 |

### sink

| Parameter | Presence |
|-----------|----------|
| `sink` | 19/21 |
| `sink.bronze` | 17/21 |
| `sink.gold` | 17/21 |
| `sink.silver` | 19/21 |
| `sink.bronze.deterministic` | 1/21 |
| `sink.bronze.dq_report` | 1/21 |
| `sink.bronze.flat_structure` | 6/21 |
| `sink.bronze.format` | 1/21 |
| `sink.bronze.metadata` | 1/21 |
| `sink.bronze.path` | 16/21 |
| `sink.bronze.save_json` | 1/21 |
| `sink.bronze.save_metadata` | 1/21 |
| `sink.gold.csv_export` | 17/21 |
| `sink.gold.deterministic` | 1/21 |
| `sink.gold.dq_report` | 1/21 |
| `sink.gold.enabled` | 1/21 |
| `sink.gold.flat_structure` | 6/21 |
| `sink.gold.format` | 1/21 |
| `sink.gold.metadata` | 1/21 |
| `sink.gold.mode` | 1/21 |
| `sink.gold.path` | 16/21 |
| `sink.gold.save_metadata` | 1/21 |
| `sink.gold.sort_by` | 16/21 |
| `sink.gold.validation` | 1/21 |
| `sink.silver.classification` | 1/21 |
| `sink.silver.csv_export` | 17/21 |
| `sink.silver.deterministic` | 1/21 |
| `sink.silver.dq_report` | 1/21 |
| `sink.silver.flat_structure` | 6/21 |
| `sink.silver.forensic_retention` | 1/21 |
| `sink.silver.format` | 1/21 |
| `sink.silver.metadata` | 1/21 |
| `sink.silver.mode` | 1/21 |
| `sink.silver.on_schema_mismatch` | 1/21 |
| `sink.silver.partition_by` | 16/21 |
| `sink.silver.path` | 16/21 |
| `sink.silver.primary_key` | 15/21 |
| `sink.silver.save_metadata` | 1/21 |
| `sink.silver.sort_by` | 16/21 |
| `sink.bronze.dq_report.enabled` | 1/21 |
| `sink.bronze.metadata.description` | 1/21 |
| `sink.bronze.metadata.lineage` | 1/21 |
| `sink.bronze.metadata.owner` | 1/21 |
| `sink.bronze.metadata.retention_days` | 1/21 |
| `sink.bronze.metadata.sla_freshness_hours` | 1/21 |
| `sink.bronze.metadata.steward` | 1/21 |
| `sink.bronze.metadata.tags` | 1/21 |
| `sink.gold.csv_export.delimiter` | 1/21 |
| `sink.gold.csv_export.enabled` | 1/21 |
| `sink.gold.csv_export.encoding` | 1/21 |
| `sink.gold.csv_export.header` | 1/21 |
| `sink.gold.csv_export.path` | 16/21 |
| `sink.gold.dq_report.enabled` | 1/21 |
| `sink.gold.metadata.business_domain` | 1/21 |
| `sink.gold.metadata.description` | 1/21 |
| `sink.gold.metadata.lineage` | 1/21 |
| `sink.gold.metadata.tags` | 1/21 |
| `sink.gold.metadata.use_cases` | 1/21 |
| `sink.gold.sort_by.ascending` | 16/21 |
| `sink.gold.sort_by.columns` | 15/21 |
| `sink.gold.validation.strict` | 1/21 |
| `sink.silver.csv_export.delimiter` | 1/21 |
| `sink.silver.csv_export.enabled` | 1/21 |
| `sink.silver.csv_export.encoding` | 1/21 |
| `sink.silver.csv_export.header` | 1/21 |
| `sink.silver.csv_export.path` | 16/21 |
| `sink.silver.dq_report.enabled` | 1/21 |
| `sink.silver.metadata.description` | 1/21 |
| `sink.silver.metadata.lineage` | 1/21 |
| `sink.silver.metadata.quality_expectations` | 1/21 |
| `sink.silver.metadata.tags` | 1/21 |
| `sink.silver.sort_by.ascending` | 16/21 |
| `sink.silver.sort_by.columns` | 15/21 |
| `sink.bronze.metadata.lineage.extraction_method` | 1/21 |
| `sink.bronze.metadata.lineage.source_system` | 1/21 |
| `sink.bronze.metadata.lineage.source_version` | 1/21 |
| `sink.gold.metadata.lineage.filters_applied` | 1/21 |
| `sink.gold.metadata.lineage.source_layer` | 1/21 |
| `sink.silver.metadata.lineage.source_layer` | 1/21 |
| `sink.silver.metadata.lineage.transformations` | 1/21 |
| `sink.silver.metadata.quality_expectations.accuracy` | 1/21 |
| `sink.silver.metadata.quality_expectations.completeness` | 1/21 |

### source

| Parameter | Presence |
|-----------|----------|
| `source` | 4/21 |
| `source.api` | 1/21 |
| `source.api_key` | 1/21 |
| `source.batch_size` | 1/21 |
| `source.email` | 2/21 |
| `source.input_path` | 1/21 |
| `source.load_strategy` | 2/21 |
| `source.search_term` | 1/21 |
| `source.type` | 2/21 |
| `source.api.base_url` | 1/21 |
| `source.api.from_db` | 1/21 |
| `source.api.to_db` | 1/21 |

### source_file

| Parameter | Presence |
|-----------|----------|
| `source_file` | 15/21 |

### transform

| Parameter | Presence |
|-----------|----------|
| `transform` | 1/21 |
| `transform.steps` | 1/21 |

### version

| Parameter | Presence |
|-----------|----------|
| `version` | 19/21 |

## 2. Entity Config Comparison

| Config | pipeline_name | provider | entity_type | version | description | primary_keys | silver_table | gold_table | source_file | source | transform | dq_rules | circuit_breaker | rate_limit | gold_filters | sink | input_filter |
|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|
| _base | — | — | — | — | — | — | — | — | — | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | ✓ |
| chembl/activity | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | ✓ | — | — | — | — | — |
| chembl/assay | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | ✓ | — | — | — | ✓ | — |
| chembl/assay_parameters | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | — | ✓ | — |
| chembl/cell_line | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | — | ✓ | — |
| chembl/compound_record | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | — | ✓ | — |
| chembl/molecule | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | — | — | — | ✓ | — |
| chembl/protein_class | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | — | ✓ | — |
| chembl/publication | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | — | ✓ | — |
| chembl/publication_similarity | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | — | ✓ | — |
| chembl/publication_term | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | — | ✓ | — |
| chembl/target | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | — | — | — | ✓ | — |
| chembl/target_component | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | — | ✓ | — |
| composite/publication | — | — | — | — | — | — | — | — | — | — | — | — | — | — | ✓ | — | — |
| crossref/publication | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | — | ✓ | — |
| openalex/publication | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | ✓ | — |
| pubchem/compound | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | — | — | — | ✓ | — |
| pubmed/publications | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — | — | — | — | ✓ | — |
| semanticscholar/publication | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | — | ✓ | — |
| uniprot/idmapping | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | ✓ | — |
| uniprot/protein | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | — | — | ✓ | — |

## 3. Discrepancy Categories

### A. Missing in _defaults (should be added)

- `batch_size` - present in: chembl/protein_class
- `checkpoint_interval` - present in: chembl/protein_class
- `circuit_breaker` - present in: _base
- `circuit_breaker.failure_threshold` - present in: _base
- `circuit_breaker.recovery_timeout` - present in: _base
- `composite` - present in: composite/publication
- `composite.dq_rules` - present in: composite/publication
- `composite.dq_rules.enricher_overrides` - present in: composite/publication
- `composite.dq_rules.enricher_overrides.pubmed_publication` - present in: composite/publication
- `composite.dq_rules.enricher_overrides.pubmed_publication.hard_fail_threshold` - present in: composite/publication
- `composite.dq_rules.enricher_overrides.pubmed_publication.soft_fail_threshold` - present in: composite/publication
- `composite.dq_rules.enricher_overrides.semanticscholar_publication` - present in: composite/publication
- `composite.dq_rules.enricher_overrides.semanticscholar_publication.hard_fail_threshold` - present in: composite/publication
- `composite.dq_rules.enricher_overrides.semanticscholar_publication.soft_fail_threshold` - present in: composite/publication
- `composite.dq_rules.hard_fail_threshold` - present in: composite/publication
- `composite.dq_rules.required_fields` - present in: composite/publication
- `composite.dq_rules.soft_fail_threshold` - present in: composite/publication
- `composite.enrichers` - present in: composite/publication
- `composite.execution` - present in: composite/publication
- `composite.execution.checkpoint_enabled` - present in: composite/publication
- `composite.execution.max_concurrency` - present in: composite/publication
- `composite.execution.retry` - present in: composite/publication
- `composite.execution.retry.backoff_multiplier` - present in: composite/publication
- `composite.execution.retry.max_attempts` - present in: composite/publication
- `composite.lineage` - present in: composite/publication
- `composite.lineage.track_field_sources` - present in: composite/publication
- `composite.lineage.track_status` - present in: composite/publication
- `composite.lineage.track_timestamps` - present in: composite/publication
- `composite.merge` - present in: composite/publication
- `composite.merge.conflict_resolution` - present in: composite/publication
- `composite.merge.field_priorities` - present in: composite/publication
- `composite.merge.field_priorities.abstract` - present in: composite/publication
- `composite.merge.field_priorities.citations_count` - present in: composite/publication
- `composite.merge.field_priorities.concepts` - present in: composite/publication
- `composite.merge.field_priorities.mesh_terms` - present in: composite/publication
- `composite.merge.field_priorities.title` - present in: composite/publication
- `composite.merge.field_priorities.tldr` - present in: composite/publication
- `composite.merge.output` - present in: composite/publication
- `composite.merge.output.gold` - present in: composite/publication
- `composite.merge.output.silver` - present in: composite/publication
- `composite.merge.strategy` - present in: composite/publication
- `composite.name` - present in: composite/publication
- `composite.seed` - present in: composite/publication
- `composite.seed.output_keys` - present in: composite/publication
- `composite.seed.pipeline` - present in: composite/publication
- `composite.seed.silver_table` - present in: composite/publication
- `composite.version` - present in: composite/publication
- `description` - present in: chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- `dq_config_file` - present in: chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, semanticscholar/publication, uniprot/idmapping
- `dq_rules` - present in: _base, chembl/activity, chembl/assay, chembl/molecule, chembl/target, pubchem/compound
- `dq_rules.conditional_validations` - present in: _base, chembl/activity
- `dq_rules.cross_field_validations` - present in: _base, chembl/activity, chembl/assay, chembl/molecule, chembl/target, pubchem/compound
- `dq_rules.field_validations` - present in: _base, chembl/activity, chembl/assay, chembl/molecule, chembl/target, pubchem/compound
- `dq_rules.hard_fail_threshold` - present in: _base
- `dq_rules.invalid_record_policy` - present in: _base
- `dq_rules.report` - present in: _base
- `dq_rules.report.enabled` - present in: _base
- `dq_rules.report.format` - present in: _base
- `dq_rules.report.include_sample_failures` - present in: _base
- `dq_rules.report.sample_size` - present in: _base
- `dq_rules.soft_fail_threshold` - present in: _base
- `dq_rules.strict_validation` - present in: _base
- `entity_type` - present in: chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- `filter_config_file` - present in: chembl/publication, chembl/publication_similarity, chembl/publication_term, composite/publication, pubmed/publications
- `gold_filters` - present in: composite/publication
- `gold_table` - present in: chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- `input_filter` - present in: _base
- `maintenance` - present in: _base
- `maintenance.auto_vacuum` - present in: _base
- `maintenance.vacuum_retention_days` - present in: _base
- `pipeline_name` - present in: chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- `primary_keys` - present in: chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- `provider` - present in: chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- `schema_version` - present in: _base
- `silver_table` - present in: chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- `sink` - present in: _base, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- `source` - present in: _base, openalex/publication, pubmed/publications, uniprot/idmapping
- `source.api` - present in: uniprot/idmapping
- `source.api.base_url` - present in: uniprot/idmapping
- `source.api.from_db` - present in: uniprot/idmapping
- `source.api.to_db` - present in: uniprot/idmapping
- `source.api_key` - present in: pubmed/publications
- `source.batch_size` - present in: openalex/publication
- `source.email` - present in: openalex/publication, pubmed/publications
- `source.input_path` - present in: uniprot/idmapping
- `source.load_strategy` - present in: _base, uniprot/idmapping
- `source.search_term` - present in: pubmed/publications
- `source.type` - present in: _base, uniprot/idmapping
- `source_file` - present in: chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, semanticscholar/publication, uniprot/idmapping
- `transform` - present in: _base
- `transform.steps` - present in: _base
- `version` - present in: chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein

### B. Inconsistent presence across entity configs

- `description`
  - Present in (19): chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
  - Missing in (2): composite/publication, _base
- `dq_config_file`
  - Present in (15): chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, semanticscholar/publication, uniprot/idmapping
  - Missing in (6): composite/publication, _base, chembl/assay, pubmed/publications, chembl/activity, uniprot/protein
- `dq_rules`
  - Present in (6): _base, chembl/activity, chembl/assay, chembl/molecule, chembl/target, pubchem/compound
  - Missing in (15): composite/publication, uniprot/idmapping, chembl/protein_class, chembl/compound_record, crossref/publication, chembl/publication_similarity, chembl/target_component, chembl/cell_line, chembl/assay_parameters, chembl/publication_term, pubmed/publications, openalex/publication, uniprot/protein, semanticscholar/publication, chembl/publication
- `dq_rules.conditional_validations`
  - Present in (2): _base, chembl/activity
  - Missing in (19): composite/publication, chembl/publication_similarity, chembl/target_component, chembl/cell_line, chembl/assay_parameters, chembl/publication_term, uniprot/protein, pubchem/compound, chembl/publication, semanticscholar/publication, chembl/protein_class, chembl/compound_record, uniprot/idmapping, chembl/target, crossref/publication, chembl/molecule, chembl/assay, pubmed/publications, openalex/publication
- `dq_rules.cross_field_validations`
  - Present in (6): _base, chembl/activity, chembl/assay, chembl/molecule, chembl/target, pubchem/compound
  - Missing in (15): composite/publication, uniprot/idmapping, chembl/protein_class, chembl/compound_record, crossref/publication, chembl/publication_similarity, chembl/target_component, chembl/cell_line, chembl/assay_parameters, chembl/publication_term, pubmed/publications, openalex/publication, uniprot/protein, semanticscholar/publication, chembl/publication
- `dq_rules.field_validations`
  - Present in (6): _base, chembl/activity, chembl/assay, chembl/molecule, chembl/target, pubchem/compound
  - Missing in (15): composite/publication, uniprot/idmapping, chembl/protein_class, chembl/compound_record, crossref/publication, chembl/publication_similarity, chembl/target_component, chembl/cell_line, chembl/assay_parameters, chembl/publication_term, pubmed/publications, openalex/publication, uniprot/protein, semanticscholar/publication, chembl/publication
- `entity_type`
  - Present in (19): chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
  - Missing in (2): composite/publication, _base
- `filter_config_file`
  - Present in (5): chembl/publication, chembl/publication_similarity, chembl/publication_term, composite/publication, pubmed/publications
  - Missing in (16): chembl/target, uniprot/idmapping, _base, chembl/protein_class, semanticscholar/publication, crossref/publication, chembl/molecule, chembl/target_component, chembl/cell_line, chembl/assay_parameters, chembl/assay, chembl/activity, openalex/publication, uniprot/protein, pubchem/compound, chembl/compound_record
- `gold_table`
  - Present in (19): chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
  - Missing in (2): composite/publication, _base
- `pipeline_name`
  - Present in (19): chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
  - Missing in (2): composite/publication, _base
- `primary_keys`
  - Present in (19): chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
  - Missing in (2): composite/publication, _base
- `provider`
  - Present in (19): chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
  - Missing in (2): composite/publication, _base
- `silver_table`
  - Present in (19): chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
  - Missing in (2): composite/publication, _base
- `sink`
  - Present in (19): _base, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
  - Missing in (2): composite/publication, chembl/activity
- `sink.bronze`
  - Present in (17): _base, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping
  - Missing in (4): composite/publication, chembl/assay, uniprot/protein, chembl/activity
- `sink.bronze.flat_structure`
  - Present in (6): _base, chembl/publication, crossref/publication, openalex/publication, pubmed/publications, semanticscholar/publication
  - Missing in (15): composite/publication, chembl/target, uniprot/idmapping, chembl/protein_class, chembl/publication_similarity, chembl/molecule, chembl/target_component, chembl/cell_line, chembl/assay_parameters, chembl/assay, chembl/activity, chembl/publication_term, uniprot/protein, pubchem/compound, chembl/compound_record
- `sink.bronze.path`
  - Present in (16): chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping
  - Missing in (5): composite/publication, _base, chembl/assay, chembl/activity, uniprot/protein
- `sink.gold`
  - Present in (17): _base, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping
  - Missing in (4): composite/publication, chembl/assay, uniprot/protein, chembl/activity
- `sink.gold.csv_export`
  - Present in (17): _base, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping
  - Missing in (4): composite/publication, chembl/assay, uniprot/protein, chembl/activity
- `sink.gold.csv_export.path`
  - Present in (16): chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping
  - Missing in (5): composite/publication, _base, chembl/assay, chembl/activity, uniprot/protein
- `sink.gold.flat_structure`
  - Present in (6): _base, chembl/publication, crossref/publication, openalex/publication, pubmed/publications, semanticscholar/publication
  - Missing in (15): composite/publication, chembl/target, uniprot/idmapping, chembl/protein_class, chembl/publication_similarity, chembl/molecule, chembl/target_component, chembl/cell_line, chembl/assay_parameters, chembl/assay, chembl/activity, chembl/publication_term, uniprot/protein, pubchem/compound, chembl/compound_record
- `sink.gold.path`
  - Present in (16): chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping
  - Missing in (5): composite/publication, _base, chembl/assay, chembl/activity, uniprot/protein
- `sink.gold.sort_by`
  - Present in (16): _base, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, semanticscholar/publication, uniprot/idmapping
  - Missing in (5): composite/publication, chembl/assay, pubmed/publications, chembl/activity, uniprot/protein
- `sink.gold.sort_by.ascending`
  - Present in (16): _base, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, semanticscholar/publication, uniprot/idmapping
  - Missing in (5): composite/publication, chembl/assay, pubmed/publications, chembl/activity, uniprot/protein
- `sink.gold.sort_by.columns`
  - Present in (15): chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, semanticscholar/publication, uniprot/idmapping
  - Missing in (6): composite/publication, _base, chembl/assay, pubmed/publications, chembl/activity, uniprot/protein
- `sink.silver`
  - Present in (19): _base, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
  - Missing in (2): composite/publication, chembl/activity
- `sink.silver.csv_export`
  - Present in (17): _base, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping
  - Missing in (4): composite/publication, chembl/assay, uniprot/protein, chembl/activity
- `sink.silver.csv_export.path`
  - Present in (16): chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping
  - Missing in (5): composite/publication, _base, chembl/assay, chembl/activity, uniprot/protein
- `sink.silver.flat_structure`
  - Present in (6): _base, chembl/publication, crossref/publication, openalex/publication, pubmed/publications, semanticscholar/publication
  - Missing in (15): composite/publication, chembl/target, uniprot/idmapping, chembl/protein_class, chembl/publication_similarity, chembl/molecule, chembl/target_component, chembl/cell_line, chembl/assay_parameters, chembl/assay, chembl/activity, chembl/publication_term, uniprot/protein, pubchem/compound, chembl/compound_record
- `sink.silver.partition_by`
  - Present in (16): _base, chembl/assay, chembl/assay_parameters, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
  - Missing in (5): composite/publication, crossref/publication, chembl/cell_line, chembl/activity, chembl/compound_record
- `sink.silver.path`
  - Present in (16): chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping
  - Missing in (5): composite/publication, _base, chembl/assay, chembl/activity, uniprot/protein
- `sink.silver.primary_key`
  - Present in (15): chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, semanticscholar/publication, uniprot/idmapping
  - Missing in (6): composite/publication, _base, chembl/assay, pubmed/publications, chembl/activity, uniprot/protein
- `sink.silver.sort_by`
  - Present in (16): _base, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, semanticscholar/publication, uniprot/idmapping
  - Missing in (5): composite/publication, chembl/assay, pubmed/publications, chembl/activity, uniprot/protein
- `sink.silver.sort_by.ascending`
  - Present in (16): _base, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, semanticscholar/publication, uniprot/idmapping
  - Missing in (5): composite/publication, chembl/assay, pubmed/publications, chembl/activity, uniprot/protein
- `sink.silver.sort_by.columns`
  - Present in (15): chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, semanticscholar/publication, uniprot/idmapping
  - Missing in (6): composite/publication, _base, chembl/assay, pubmed/publications, chembl/activity, uniprot/protein
- `source`
  - Present in (4): _base, openalex/publication, pubmed/publications, uniprot/idmapping
  - Missing in (17): composite/publication, chembl/publication_similarity, chembl/target_component, chembl/cell_line, chembl/assay_parameters, chembl/activity, chembl/publication_term, uniprot/protein, pubchem/compound, chembl/publication, semanticscholar/publication, chembl/protein_class, chembl/compound_record, chembl/target, crossref/publication, chembl/molecule, chembl/assay
- `source.email`
  - Present in (2): openalex/publication, pubmed/publications
  - Missing in (19): composite/publication, _base, chembl/publication_similarity, chembl/target_component, chembl/cell_line, chembl/assay_parameters, chembl/activity, chembl/publication_term, uniprot/protein, pubchem/compound, chembl/publication, semanticscholar/publication, chembl/protein_class, chembl/compound_record, uniprot/idmapping, chembl/target, crossref/publication, chembl/molecule, chembl/assay
- `source.load_strategy`
  - Present in (2): _base, uniprot/idmapping
  - Missing in (19): composite/publication, chembl/publication_similarity, chembl/target_component, chembl/cell_line, chembl/assay_parameters, chembl/activity, chembl/publication_term, uniprot/protein, pubchem/compound, chembl/publication, semanticscholar/publication, chembl/protein_class, chembl/compound_record, chembl/target, crossref/publication, chembl/molecule, chembl/assay, pubmed/publications, openalex/publication
- `source.type`
  - Present in (2): _base, uniprot/idmapping
  - Missing in (19): composite/publication, chembl/publication_similarity, chembl/target_component, chembl/cell_line, chembl/assay_parameters, chembl/activity, chembl/publication_term, uniprot/protein, pubchem/compound, chembl/publication, semanticscholar/publication, chembl/protein_class, chembl/compound_record, chembl/target, crossref/publication, chembl/molecule, chembl/assay, pubmed/publications, openalex/publication
- `source_file`
  - Present in (15): chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, semanticscholar/publication, uniprot/idmapping
  - Missing in (6): composite/publication, _base, chembl/assay, pubmed/publications, chembl/activity, uniprot/protein
- `version`
  - Present in (19): chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
  - Missing in (2): composite/publication, _base

### C. Structural inconsistencies

#### source vs source_file

- Using `source`: _base, openalex/publication, pubmed/publications, uniprot/idmapping
- Using `source_file`: chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, semanticscholar/publication, uniprot/idmapping

#### transform block

- Has `transform`: _base
- No `transform`: composite/publication, chembl/publication_similarity, chembl/target_component, chembl/cell_line, chembl/assay_parameters, chembl/activity, chembl/publication_term, uniprot/protein, pubchem/compound, chembl/publication, semanticscholar/publication, chembl/protein_class, chembl/compound_record, uniprot/idmapping, chembl/target, crossref/publication, chembl/molecule, chembl/assay, pubmed/publications, openalex/publication

#### gold_table presence

- Has `gold_table`: chembl/activity, chembl/assay, chembl/assay_parameters, chembl/cell_line, chembl/compound_record, chembl/molecule, chembl/protein_class, chembl/publication, chembl/publication_similarity, chembl/publication_term, chembl/target, chembl/target_component, crossref/publication, openalex/publication, pubchem/compound, pubmed/publications, semanticscholar/publication, uniprot/idmapping, uniprot/protein
- Missing `gold_table`: composite/publication, _base
