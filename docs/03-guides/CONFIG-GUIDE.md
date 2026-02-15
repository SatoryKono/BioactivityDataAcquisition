# Pipeline Configuration Guide

## Overview

`configs/pipelines/_base.yaml` defines the canonical schema for all BioETL pipeline configs. Entity configs inherit defaults from `_base.yaml` and override only entity-specific values.

Inheritance chain:

`_base.yaml` → `configs/pipelines/<provider>/<entity>.yaml`

Recommended minimal fields in entity configs:

- `pipeline_name`, `provider`, `entity_type`, `version`
- `primary_keys`, `silver_table`, `gold_table`
- DQ overrides only when different from entity DQ defaults
- Explicit path/config overrides only when conventions are insufficient

Configuration styles:

1. **Convention-based minimal (recommended)**
   - Use standard conventions and auto-computed paths.
1. **Explicit full**
   - Use when you need non-standard paths or explicit behavior.
1. **Hybrid**
   - Keep conventions, override only special cases.

Related ADRs:

- [ADR-025: Pipeline Config Unification](../02-architecture/decisions/ADR-025-pipeline-config-unification.md)
- [ADR-027: DQ Rules Externalization](../02-architecture/decisions/ADR-027-dq-rules-externalization.md)
- [ADR-028: Filter Rules Externalization](../02-architecture/decisions/ADR-028-filter-rules-externalization.md)
- [ADR-029: Output Metadata Unification](../02-architecture/decisions/ADR-029-output-metadata-unification.md)

## Pipeline Config

### Identification

Entity configs must define:

- `pipeline_name`: unique identifier (`<provider>_<entity>`)
- `provider`: source provider (`chembl`, `pubchem`, `uniprot`, ...)
- `entity_type`: entity (`activity`, `assay`, `molecule`, ...)
- `version`: semantic version

### Source

- `source.type`: default `api`
- `source.load_strategy`: `full` (default) or `incremental`
- `source.watermark_field`: should be defined for incremental mode

Provider-level source settings (`type`, `load_strategy`, rate limits, circuit breaker) are maintained in `configs/sources/<provider>.yaml`.

### Transform

- `transform.steps`: optional list of transformation steps (default empty)
- `transform.version` should align with config version (if explicitly set)

Typical step names used in documentation:

- `normalize_units`
- `validate_smiles`
- `deduplicate`
- `enrich_metadata`

### Circuit Breaker

Defaults:

- `failure_threshold`: `5`
- `recovery_timeout`: `300` seconds

Provider-specific overrides are defined in source configs.

### Maintenance

- `maintenance.auto_vacuum`: default `false`
- `maintenance.vacuum_retention_days`: default `7`

## DQ

Default DQ thresholds:

- `soft_fail_threshold`: `0.05` (warning)
- `hard_fail_threshold`: `0.20` (batch failure)
- `strict_validation`: `false`

Deviations from defaults should be documented in entity config rationale.

### Field-level validations

`dq_rules.field_validations` supports:

- `range`: numeric min/max
- `pattern`: regex validation
- `enum`: allowed values
- `custom`: named validator function

### Cross-field validations

`dq_rules.cross_field_validations` supports conditions:

- `all_present`
- `any_present`
- `mutually_exclusive`
- `conditional_required`
- `custom`

### Conditional validations

`dq_rules.conditional_validations` applies checks when condition is met.

Supported operators:

- `eq`
- `ne`
- `in`
- `not_in`

### Invalid record policy

`dq_rules.invalid_record_policy` values:

- `quarantine` (default)
- `skip`
- `fail`

### DQ report

`dq_rules.report` defaults:

- `enabled: true`
- `format: json` (`json | yaml | csv`)
- `include_sample_failures: true`
- `sample_size: 10`

## Filters

### Input filter

`input_filter` controls CSV-driven selective processing:

- `enabled`: default `false`
- `batch_size`: default `100`
- Entity-specific fields when enabled:
  - `source_path`
  - `column_name`
  - `filter_field`
  - `fallback_column` (optional)

### Gold filters

Gold filters are typically entity-specific and can include:

- `columns`: allowed values per field
- `ranges`: min/max with `include_min` / `include_max`
- `required_fields`
- `list_lengths`
- `list_contains` (`mode: any|all`)

Related ADR:

- [ADR-028: Filter Rules Externalization](../02-architecture/decisions/ADR-028-filter-rules-externalization.md)

## Sink

### Bronze

Defaults:

- `format: jsonl`
- `save_json: true`
- `deterministic: true`
- `save_metadata: true`
- `dq_report.enabled: true`
- `flat_structure: true`

Metadata block includes lineage, ownership, tags, retention and SLA placeholders.

### Silver

Defaults:

- `format: delta` (Delta Lake required)
- `mode: merge`
- `on_schema_mismatch: evolve`
- `classification: public`
- `forensic_retention: false` (true for critical tables with rationale)
- `deterministic: true`
- `save_metadata: true`
- `dq_report.enabled: true`
- `csv_export.enabled: true`
- `partition_by: []`
- `sort_by.ascending: true`
- `flat_structure: true`

Entity config should define:

- `path`
- `primary_key`
- `sort_by.columns`

### Gold

Defaults:

- `enabled: true`
- `validation.strict: true`
- `format: delta`
- `mode: overwrite`
- `deterministic: true`
- `save_metadata: true`
- `dq_report.enabled: true`
- `csv_export.enabled: true`
- `sort_by.ascending: true`
- `flat_structure: true`

Entity config should define:

- `path`
- `sort_by.columns`

Related ADRs:

- [ADR-014: Deterministic Writes](../02-architecture/decisions/ADR-014-deterministic-writes.md)
- [ADR-018: Gold Strict Validation](../02-architecture/decisions/ADR-018-gold-strict-validation.md)
- [ADR-029: Output Metadata Unification](../02-architecture/decisions/ADR-029-output-metadata-unification.md)

## Convention Defaults

When `provider` and `entity_type` are set, config loader can auto-compute references and sink defaults.

Auto-computed file references:

- `source_file` → `../../sources/{provider}.yaml`
- `dq_config_file` → `../../dq/entities/{provider}/{entity_type}.yaml`
- `filter_config_file` → `../../filter/entities/{provider}/{entity_type}.yaml`

Auto-computed sink paths:

- `sink.bronze.path` → `data/output/bronze/{provider}/{entity_type}`
- `sink.silver.path` → `data/output/silver/{provider}/{entity_type}`
- `sink.gold.path` → `data/output/gold/{provider}/{entity_type}`
- `sink.silver.csv_export.path` → `{sink.silver.path}`
- `sink.gold.csv_export.path` → `{sink.gold.path}`

Auto-propagated primary keys:

- `sink.silver.primary_key` ← `primary_keys`
- `sink.silver.sort_by.columns` ← `primary_keys`
- `sink.gold.sort_by.columns` ← `primary_keys`

Rule loading:

- `input_filter` and `gold_filters` are loaded from `filter_config_file`
- `dq_rules` are loaded from `dq_config_file`
- Inline pipeline values are merged on top of file-based defaults
