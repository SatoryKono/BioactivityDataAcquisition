# Pipeline Configuration Discrepancy Report

*Generated: 2026-01-13*
*Reference Schema: RULES.md v5.10, Appendix D*
*Total Configurations Analyzed: 19 pipeline configs + 1 defaults file + 7 source configs*

---

## Executive Summary

| Category | Count | Status |
|----------|-------|--------|
| **Total Pipeline Configs** | 19 | - |
| **Fully Compliant** | 17 | OK |
| **With Warnings** | 2 | WARN |
| **Critical Violations** | 0 | - |
| **Missing MUST Parameters** | 0 | - |

**Overall Assessment**: The BioETL pipeline configurations are **well-structured** and follow a consistent pattern. The project has already implemented a sensible inheritance mechanism via `-defaults.yaml` and source-specific configs in `configs/sources/`. No critical violations were found.

---

## Schema Structure Analysis

### Current vs Reference Schema

The project uses a **flat schema** rather than the **nested schema** proposed in RULES.md Appendix D:

| Reference Schema | Current Implementation | Assessment |
|-----------------|------------------------|------------|
| `pipeline.name` | `pipeline-name` | **Equivalent** - flat key |
| `pipeline.provider` | `provider` | **Equivalent** - flat key |
| `pipeline.entity` | `entity-type` | **Equivalent** - flat key |
| `source.type` | Inherited from source config | **OK** - separation of concerns |
| `source.load-strategy` | Inherited from source config | **OK** - separation of concerns |
| `source.watermark-field` | N/A (all use `full` load) | **N/A** - not applicable |
| `transform.version` | `version` | **Equivalent** - root level |
| `transform.steps` | Not implemented | **SHOULD** - optional |
| `sink.silver.*` | `sink.silver.*` | **Matching** |
| `dq-overrides.*` | Inherited from `-defaults.yaml` | **OK** - DRY principle |
| `circuit-breaker.*` | Inherited from `-defaults.yaml`/source | **OK** - DRY principle |
| `rate-limit.*` | In source configs | **OK** - separation of concerns |

### Key Architectural Decision

The project has made a **deliberate architectural choice** to separate:
1. **Pipeline configs** (`configs/pipelines/`) - entity-specific settings, gold filters, sink paths
2. **Source configs** (`configs/sources/`) - provider-level settings, rate limits, circuit breaker
3. **Defaults** (`-defaults.yaml`) - cross-cutting defaults for all pipelines

This separation follows the **DRY principle** and avoids duplication of common settings.

---

## Critical Violations (MUST) - NONE FOUND

No critical violations were detected. All MUST requirements are satisfied:

| Requirement | Status | Notes |
|-------------|--------|-------|
| `pipeline.name` (or equivalent) | PASS | All configs have `pipeline-name` |
| `pipeline.provider` | PASS | All configs have `provider` |
| `pipeline.entity` | PASS | All configs have `entity-type` |
| `source.type` | PASS | Inherited from source configs |
| `source.load-strategy` | PASS | Inherited from source configs |
| `transform.version` | PASS | All configs have `version: "1.1.0"` |
| `sink.silver.format: delta` | PASS | Inherited from `-defaults.yaml` |
| `sink.silver.mode` | PASS | Inherited as `merge` |
| `sink.silver.primary-key` | PASS | All configs define `primary-key` |
| `dq-overrides.soft-fail-threshold` | PASS | 0.05 in `-defaults.yaml` |
| `dq-overrides.hard-fail-threshold` | PASS | 0.20 in `-defaults.yaml` |
| `circuit-breaker.failure-threshold` | PASS | 5 in `-defaults.yaml` |
| `circuit-breaker.recovery-timeout` | PASS | 300 in `-defaults.yaml` |
| `rate-limit.requests-per-second` | PASS | In source configs |

---

## Warnings (SHOULD) - 2 Configs

### 1. `uniprot/idmapping.yaml` - Custom DQ Thresholds

**Issue**: Uses non-standard DQ thresholds
- `soft-fail-threshold: 0.30` (vs default 0.05)
- `hard-fail-threshold: 0.80` (vs default 0.20)

**Assessment**: **ACCEPTABLE** - This is a documented deviation with clear justification:
> "Many ChEMBL targets may not have UniProt mappings (expected behavior)"

**Recommendation**: No action required. The deviation is justified and documented in the config.

### 2. `semanticscholar/publication.yaml` (via source config)

**Issue**: Uses custom circuit breaker settings in source config:
- `failure-threshold: 10` (vs default 5)
- `recovery-timeout: 600` (vs default 300)
- `rate-limit.requests-per-second: 0.1` (very conservative)

**Assessment**: **ACCEPTABLE** - Documented as intentional for Semantic Scholar's aggressive rate limiting.

**Recommendation**: No action required. The settings are provider-specific and documented.

---

## Missing SHOULD Parameters

### `transform.steps` - Missing in All Configs

The reference schema includes:
```yaml
transform:
  steps:
    - normalize-units
    - validate-smiles
    - deduplicate
```

**Current State**: No pipeline config includes `transform.steps`.

**Assessment**: This is a **documentation gap**, not a functional issue. Transformations are implemented in code (transformers) but not declared in configs.

**Recommendation**: Consider adding `transform.steps` for documentation purposes, OR document that transformations are code-defined rather than config-defined.

### `sink.silver.partition-by` - Empty in 5 Configs

| Config | `partition-by` | Reason |
|--------|---------------|--------|
| `chembl/activity.yaml` | `[]` | Large dataset, no clear partition key |
| `chembl/cell-line.yaml` | `[]` | Small reference dataset |
| `chembl/compound-record.yaml` | `[]` | Junction table |
| `chembl/document-similarity.yaml` | `[]` | Commented: "No good partition key" |
| `crossref/publication.yaml` | `[]` | DOI-based, no natural partition |
| `uniprot/idmapping.yaml` | `[]` | Small dataset |

**Assessment**: Empty `partition-by` is acceptable for small datasets or when no natural partition key exists.

**Recommendation**: Document the rationale in each config (some already do).

---

## Prohibited Patterns Check (MUST NOT)

| Pattern | Status | Files Checked |
|---------|--------|---------------|
| `format: parquet` in Silver | NOT FOUND | All use `delta` |
| Hardcoded secrets | NOT FOUND | All use `${ENV-VAR}` syntax |
| Sentinel values (`-1`, `"N/A"`) | NOT FOUND | N/A |
| Absolute paths without env vars | NOT FOUND | Relative paths used |

---

## Consistency Analysis

### Pipeline Naming Convention

| Expected Pattern | Actual Pattern | Status |
|-----------------|----------------|--------|
| `<entity>-<provider>` | `<provider>-<entity>` | **INVERTED** |

**Current Naming**: `chembl-activity`, `pubchem-compound`, etc.
**Reference Schema**: `activity-chembl`, `compound-pubchem`, etc.

**Assessment**: The current naming is **consistent across all configs** and follows a logical `<provider>-<entity>` pattern. This is a **stylistic difference**, not a violation.

**Recommendation**: Document the chosen convention. No migration needed as current pattern is consistent.

### DQ Thresholds Consistency

| Config | `soft-fail` | `hard-fail` | Notes |
|--------|-------------|-------------|-------|
| All (via defaults) | 0.05 | 0.20 | Standard |
| `uniprot/idmapping.yaml` | 0.30 | 0.80 | Justified deviation |

**Status**: CONSISTENT (with documented exception)

### Circuit Breaker Consistency

| Provider | `failure-threshold` | `recovery-timeout` | Notes |
|----------|--------------------|--------------------|-------|
| All (via defaults) | 5 | 300 | Standard |
| Semantic Scholar (source) | 10 | 600 | Rate limit sensitive |

**Status**: CONSISTENT (with documented exception)

### Version Consistency

All pipeline configs use `version: "1.1.0"`.

**Status**: FULLY CONSISTENT

---

## Source Config Analysis

| Source | `rate-limit.rps` | `rate-limit.burst` | Notes |
|--------|------------------|-------------------|-------|
| ChEMBL | 5 | 10 | Conservative |
| PubChem | 5 | 10 | Per API docs |
| UniProt | 10 | 20 | With API key |
| OpenAlex | 10 | 20 | Polite pool |
| PubMed | 3 | 5 | Default without key |
| Semantic Scholar | 0.1 | 1 | Very conservative |
| CrossRef | 50 | 100 | Polite pool |

All source configs include:
- `source.type: api`
- `source.load-strategy: full`
- `circuit-breaker` settings
- `rate-limit` settings
- `provider-config` with base URL and client settings

**Status**: WELL-STRUCTURED

---

## Recommendations Summary

### Priority 0 (Critical) - NONE

No critical issues requiring immediate action.

### Priority 1 (High) - Schema Documentation

1. **Document the flat vs nested schema choice** in ADR
2. **Document the naming convention** (`<provider>-<entity>` vs `<entity>-<provider>`)

### Priority 2 (Medium) - Optional Enhancements

1. Consider adding `transform.steps` for documentation
2. Add comments explaining empty `partition-by` where missing

### Priority 3 (Low) - Nice to Have

1. Create JSON Schema for config validation
2. Add automated config validation tests

---

## Appendix: Files Analyzed

### Pipeline Configs (19)
- `configs/pipelines/-defaults.yaml`
- `configs/pipelines/chembl/activity.yaml`
- `configs/pipelines/chembl/assay.yaml`
- `configs/pipelines/chembl/assay-parameters.yaml`
- `configs/pipelines/chembl/cell-line.yaml`
- `configs/pipelines/chembl/compound-record.yaml`
- `configs/pipelines/chembl/document.yaml`
- `configs/pipelines/chembl/document-similarity.yaml`
- `configs/pipelines/chembl/document-term.yaml`
- `configs/pipelines/chembl/molecule.yaml`
- `configs/pipelines/chembl/protein-class.yaml`
- `configs/pipelines/chembl/target.yaml`
- `configs/pipelines/chembl/target-component.yaml`
- `configs/pipelines/crossref/publication.yaml`
- `configs/pipelines/openalex/publication.yaml`
- `configs/pipelines/pubchem/compound.yaml`
- `configs/pipelines/pubmed/publications.yaml`
- `configs/pipelines/semanticscholar/publication.yaml`
- `configs/pipelines/uniprot/idmapping.yaml`
- `configs/pipelines/uniprot/protein.yaml`

### Source Configs (7)
- `configs/sources/chembl.yaml`
- `configs/sources/crossref.yaml`
- `configs/sources/openalex.yaml`
- `configs/sources/pubchem.yaml`
- `configs/sources/pubmed.yaml`
- `configs/sources/semanticscholar.yaml`
- `configs/sources/uniprot.yaml`
