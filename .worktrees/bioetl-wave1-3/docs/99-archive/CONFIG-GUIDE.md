# Pipeline Configuration Guide

## Overview

`configs/pipelines/-base.yaml` defines the canonical schema for all BioETL pipeline configs. Entity configs inherit defaults from `-base.yaml` and override only entity-specific values.

Inheritance chain:

`-base.yaml` → `configs/pipelines/<provider>/<entity>.yaml`

Recommended minimal fields in entity configs:

- `pipeline-name`, `provider`, `entity-type`, `version`
- `primary-keys`, `silver-table`, `gold-table`
- DQ overrides only when different from entity DQ defaults
- Explicit path/config overrides only when conventions are insufficient

Configuration styles:

1. **Convention-based minimal (recommended)**
   - Use standard conventions and auto-computed paths.
1. **Explicit full**
   - Use when you need non-standard paths or explicit behavior.
1. **Hybrid**
   - Keep conventions, override only special cases.

Migration table (Gold write mode):

| Entity                                                                                                                                | Current Mode         | Recommended Mode     | Breaking | Migration                                             |
| ------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | -------------------- | -------- | ----------------------------------------------------- |
| publication (chembl/pubmed/crossref/openalex/semanticscholar)                                                                         | implicit `overwrite` | `scd2`               | Yes      | Bootstrap snapshot, затем SCD2 + backfill интервалов  |
| reference dictionaries (chembl: assay, assay-parameters, cell-line, tissue, protein-class, subcellular-fraction)                      | implicit `overwrite` | `scd2`               | Yes      | Rebuild и включить versioned updates                  |
| slowly evolving records (chembl: target, target-component, molecule, compound-record; uniprot: protein, idmapping; pubchem: compound) | implicit `overwrite` | `scd2`               | Yes      | Инициализировать version=1, далее писать новые версии |
| high-volume facts (chembl: activity)                                                                                                  | implicit `overwrite` | `append`             | No       | Явно указать append                                   |
| recomputed derived outputs (chembl: publication-similarity, publication-term)                                                         | implicit `overwrite` | explicit `overwrite` | No       | Явно указать overwrite                                |

Related ADRs:

- [ADR-025: Pipeline Config Unification](../02-architecture/decisions/ADR-025-pipeline-config-unification.md)
- [ADR-027: DQ Rules Externalization](../02-architecture/decisions/ADR-027-dq-rules-externalization.md)
- [ADR-028: Filter Rules Externalization](../02-architecture/decisions/ADR-028-filter-rules-externalization.md)
- [ADR-029: Output Metadata Unification](../02-architecture/decisions/ADR-029-output-metadata-unification.md)

## Pipeline Config

### Identification

Entity configs must define:

- `pipeline-name`: unique identifier (`<provider>-<entity>`)
- `provider`: source provider (`chembl`, `pubchem`, `uniprot`, ...)
- `entity-type`: entity (`activity`, `assay`, `molecule`, ...)
- `version`: semantic version

### Source

- `source.type`: default `api`
- `source.load-strategy`: `full` (default) or `incremental`
- `source.watermark-field`: should be defined for incremental mode

Provider-level source settings (`type`, `load-strategy`, rate limits, circuit breaker) are maintained in `configs/sources/<provider>.yaml`.

### Transform

- `transform.steps`: optional list of transformation steps (default empty)
- `transform.version` should align with config version (if explicitly set)

Typical step names used in documentation:

- `normalize-units`
- `validate-smiles`
- `deduplicate`
- `enrich-metadata`

### Circuit Breaker

Defaults:

- `failure-threshold`: `5`
- `recovery-timeout`: `300` seconds

Provider-specific overrides are defined in source configs.

### Maintenance

- `maintenance.auto-vacuum`: default `false`
- `maintenance.vacuum-retention-days`: default `7`

## DQ

Default DQ thresholds:

- `soft-fail-threshold`: `0.05` (warning)
- `hard-fail-threshold`: `0.20` (batch failure)
- `strict-validation`: `false`

Deviations from defaults should be documented in entity config rationale.

### Field-level validations

`dq-overrides.field-validations` supports:

- `range`: numeric min/max
- `pattern`: regex validation
- `enum`: allowed values
- `custom`: named validator function

### Cross-field validations

`dq-overrides.cross-field-validations` supports conditions:

- `all-present`
- `any-present`
- `mutually-exclusive`
- `conditional-required`
- `custom`

### Conditional validations

`dq-overrides.conditional-validations` applies checks when condition is met.

Supported operators:

- `eq`
- `ne`
- `in`
- `not-in`

### Invalid record policy

`dq-overrides.invalid-record-policy` values:

- `quarantine` (default)
- `skip`
- `fail`

### DQ report

`dq-overrides.report` defaults:

- `enabled: true`
- `format: json` (`json | yaml | csv`)
- `include-sample-failures: true`
- `sample-size: 10`

## Filters

### Input filter

`input-filter` controls CSV-driven selective processing:

- `enabled`: default `false`
- `batch-size`: default `100`
- Entity-specific fields when enabled:
  - `source-path`
  - `column-name`
  - `filter-field`
  - `fallback-column` (optional)

### Gold filters

Gold filters are typically entity-specific and can include:

- `columns`: allowed values per field
- `ranges`: min/max with `include-min` / `include-max`
- `required-fields`
- `list-lengths`
- `list-contains` (`mode: any|all`)

Related ADR:

- [ADR-028: Filter Rules Externalization](../02-architecture/decisions/ADR-028-filter-rules-externalization.md)

## Sink

### Bronze

Defaults:

- `format: jsonl`
- `save-json: true`
- `deterministic: true`
- `save-metadata: true`
- `dq-report.enabled: true`
- `flat-structure: true`

Metadata block includes lineage, ownership, tags, retention and SLA placeholders.

### Silver

Defaults:

- `format: delta` (Delta Lake required)
- `mode: merge`
- `on-schema-mismatch: evolve`
- `classification: public`
- `forensic-retention: false` (true for critical tables with rationale)
- `deterministic: true`
- `save-metadata: true`
- `dq-report.enabled: true`
- `csv-export.enabled: true`
- `partition-by: []`
- `sort-by.ascending: true`
- `flat-structure: true`

Entity config should define:

- `path`
- `primary-key`
- `sort-by.columns`

### Gold

Defaults:

- `enabled: true`
- `validation.strict: true`
- `format: delta`
- `mode: append`
- `deterministic: true`
- `save-metadata: true`
- `dq-report.enabled: true`
- `csv-export.enabled: true`
- `sort-by.ascending: true`
- `flat-structure: true`

History retention criteria for Gold mode selection:

- Reference dictionaries -> `mode: scd2`
- Slowly evolving records -> `mode: scd2`
- Publication metadata -> `mode: scd2`
- Recomputed aggregates -> `mode: overwrite`

For `mode: scd2`, configure mandatory `scd-config` fields:

```yaml
sink:
  gold:
    mode: scd2
    scd-config:
      valid-from: -valid-from
      valid-to: -valid-to
      is-current: -is-current
      version: -version
```

Entity config should define:

- `path`
- `sort-by.columns`

Migration table (Gold write mode):

| Entity                                                                                                                                | Current Mode         | Recommended Mode     | Breaking | Migration                                             |
| ------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | -------------------- | -------- | ----------------------------------------------------- |
| publication (chembl/pubmed/crossref/openalex/semanticscholar)                                                                         | implicit `overwrite` | `scd2`               | Yes      | Bootstrap snapshot, затем SCD2 + backfill интервалов  |
| reference dictionaries (chembl: assay, assay-parameters, cell-line, tissue, protein-class, subcellular-fraction)                      | implicit `overwrite` | `scd2`               | Yes      | Rebuild и включить versioned updates                  |
| slowly evolving records (chembl: target, target-component, molecule, compound-record; uniprot: protein, idmapping; pubchem: compound) | implicit `overwrite` | `scd2`               | Yes      | Инициализировать version=1, далее писать новые версии |
| high-volume facts (chembl: activity)                                                                                                  | implicit `overwrite` | `append`             | No       | Явно указать append                                   |
| recomputed derived outputs (chembl: publication-similarity, publication-term)                                                         | implicit `overwrite` | explicit `overwrite` | No       | Явно указать overwrite                                |

Related ADRs:

- [ADR-014: Deterministic Writes](../02-architecture/decisions/ADR-014-deterministic-writes.md)
- [ADR-018: Gold Strict Validation](../02-architecture/decisions/ADR-018-gold-strict-validation.md)
- [ADR-029: Output Metadata Unification](../02-architecture/decisions/ADR-029-output-metadata-unification.md)

## Convention Defaults

When `provider` and `entity-type` are set, config loader can auto-compute references and sink defaults.

Auto-computed file references:

- `source-file` → `../../sources/{provider}.yaml`
- `dq-config-file` → `../../quality/entities/{provider}/{entity-type}.yaml`
- `filter-config-file` → `../../filters/entities/{provider}/{entity-type}.yaml`

Auto-computed sink paths:

- `sink.bronze.path` → `data/output/bronze/{provider}/{entity-type}`
- `sink.silver.path` → `data/output/silver/{provider}/{entity-type}`
- `sink.gold.path` → `data/output/gold/{provider}/{entity-type}`
- `sink.silver.csv-export.path` → `{sink.silver.path}`
- `sink.gold.csv-export.path` → `{sink.gold.path}`

Auto-propagated primary keys:

- `sink.silver.primary-key` ← `primary-keys`
- `sink.silver.sort-by.columns` ← `primary-keys`
- `sink.gold.sort-by.columns` ← `primary-keys`

Rule loading:

- `input-filter` and `gold-filters` are loaded from `filter-config-file`
- `dq-overrides` are loaded from `dq-config-file`
- Inline pipeline values are merged on top of file-based defaults
