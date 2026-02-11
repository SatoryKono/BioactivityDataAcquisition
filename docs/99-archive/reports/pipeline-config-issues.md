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

**Overall Assessment**: The BioETL pipeline configurations are **well-structured** and follow a consistent pattern. The project has already implemented a sensible inheritance mechanism via `_defaults.yaml` and source-specific configs in `configs/sources/`. No critical violations were found.

---

## Schema Structure Analysis

### Current vs Reference Schema

The project uses a **flat schema** rather than the **nested schema** proposed in RULES.md Appendix D:

| Reference Schema | Current Implementation | Assessment |
|-----------------|------------------------|------------|
| `pipeline.name` | `pipeline_name` | **Equivalent** - flat key |
| `pipeline.provider` | `provider` | **Equivalent** - flat key |
| `pipeline.entity` | `entity_type` | **Equivalent** - flat key |
| `source.type` | Inherited from source config | **OK** - separation of concerns |
| `source.load_strategy` | Inherited from source config | **OK** - separation of concerns |
| `source.watermark_field` | N/A (all use `full` load) | **N/A** - not applicable |
| `transform.version` | `version` | **Equivalent** - root level |
| `transform.steps` | Not implemented | **SHOULD** - optional |
| `sink.silver.*` | `sink.silver.*` | **Matching** |
| `dq_rules.*` | Inherited from `_defaults.yaml` | **OK** - DRY principle |
| `circuit_breaker.*` | Inherited from `_defaults.yaml`/source | **OK** - DRY principle |
| `rate_limit.*` | In source configs | **OK** - separation of concerns |

### Key Architectural Decision

The project has made a **deliberate architectural choice** to separate:
1. **Pipeline configs** (`configs/pipelines/`) - entity-specific settings, gold filters, sink paths
2. **Source configs** (`configs/sources/`) - provider-level settings, rate limits, circuit breaker
3. **Defaults** (`_defaults.yaml`) - cross-cutting defaults for all pipelines

This separation follows the **DRY principle** and avoids duplication of common settings.

---

## Critical Violations (MUST) - NONE FOUND

No critical violations were detected. All MUST requirements are satisfied:

| Requirement | Status | Notes |
|-------------|--------|-------|
| `pipeline.name` (or equivalent) | PASS | All configs have `pipeline_name` |
| `pipeline.provider` | PASS | All configs have `provider` |
| `pipeline.entity` | PASS | All configs have `entity_type` |
| `source.type` | PASS | Inherited from source configs |
| `source.load_strategy` | PASS | Inherited from source configs |
| `transform.version` | PASS | All configs have `version: "1.1.0"` |
| `sink.silver.format: delta` | PASS | Inherited from `_defaults.yaml` |
| `sink.silver.mode` | PASS | Inherited as `merge` |
| `sink.silver.primary_key` | PASS | All configs define `primary_key` |
| `dq_rules.soft_fail_threshold` | PASS | 0.05 in `_defaults.yaml` |
| `dq_rules.hard_fail_threshold` | PASS | 0.20 in `_defaults.yaml` |
| `circuit_breaker.failure_threshold` | PASS | 5 in `_defaults.yaml` |
| `circuit_breaker.recovery_timeout` | PASS | 300 in `_defaults.yaml` |
| `rate_limit.requests_per_second` | PASS | In source configs |

---

## Warnings (SHOULD) - 2 Configs

### 1. `uniprot/idmapping.yaml` - Custom DQ Thresholds

**Issue**: Uses non-standard DQ thresholds
- `soft_fail_threshold: 0.30` (vs default 0.05)
- `hard_fail_threshold: 0.80` (vs default 0.20)

**Assessment**: **ACCEPTABLE** - This is a documented deviation with clear justification:
> "Many ChEMBL targets may not have UniProt mappings (expected behavior)"

**Recommendation**: No action required. The deviation is justified and documented in the config.

### 2. `semanticscholar/publication.yaml` (via source config)

**Issue**: Uses custom circuit breaker settings in source config:
- `failure_threshold: 10` (vs default 5)
- `recovery_timeout: 600` (vs default 300)
- `rate_limit.requests_per_second: 0.1` (very conservative)

**Assessment**: **ACCEPTABLE** - Documented as intentional for Semantic Scholar's aggressive rate limiting.

**Recommendation**: No action required. The settings are provider-specific and documented.

---

## Missing SHOULD Parameters

### `transform.steps` - Missing in All Configs

The reference schema includes:
```yaml
transform:
  steps:
    - normalize_units
    - validate_smiles
    - deduplicate
```

**Current State**: No pipeline config includes `transform.steps`.

**Assessment**: This is a **documentation gap**, not a functional issue. Transformations are implemented in code (transformers) but not declared in configs.

**Recommendation**: Consider adding `transform.steps` for documentation purposes, OR document that transformations are code-defined rather than config-defined.

### `sink.silver.partition_by` - Empty in 5 Configs

| Config | `partition_by` | Reason |
|--------|---------------|--------|
| `chembl/activity.yaml` | `[]` | Large dataset, no clear partition key |
| `chembl/cell_line.yaml` | `[]` | Small reference dataset |
| `chembl/compound_record.yaml` | `[]` | Junction table |
| `chembl/document_similarity.yaml` | `[]` | Commented: "No good partition key" |
| `crossref/publication.yaml` | `[]` | DOI-based, no natural partition |
| `uniprot/idmapping.yaml` | `[]` | Small dataset |

**Assessment**: Empty `partition_by` is acceptable for small datasets or when no natural partition key exists.

**Recommendation**: Document the rationale in each config (some already do).

---

## Prohibited Patterns Check (MUST NOT)

| Pattern | Status | Files Checked |
|---------|--------|---------------|
| `format: parquet` in Silver | NOT FOUND | All use `delta` |
| Hardcoded secrets | NOT FOUND | All use `${ENV_VAR}` syntax |
| Sentinel values (`-1`, `"N/A"`) | NOT FOUND | N/A |
| Absolute paths without env vars | NOT FOUND | Relative paths used |

---

## Consistency Analysis

### Pipeline Naming Convention

| Expected Pattern | Actual Pattern | Status |
|-----------------|----------------|--------|
| `<entity>_<provider>` | `<provider>_<entity>` | **INVERTED** |

**Current Naming**: `chembl_activity`, `pubchem_compound`, etc.
**Reference Schema**: `activity_chembl`, `compound_pubchem`, etc.

**Assessment**: The current naming is **consistent across all configs** and follows a logical `<provider>_<entity>` pattern. This is a **stylistic difference**, not a violation.

**Recommendation**: Document the chosen convention. No migration needed as current pattern is consistent.

### DQ Thresholds Consistency

| Config | `soft_fail` | `hard_fail` | Notes |
|--------|-------------|-------------|-------|
| All (via defaults) | 0.05 | 0.20 | Standard |
| `uniprot/idmapping.yaml` | 0.30 | 0.80 | Justified deviation |

**Status**: CONSISTENT (with documented exception)

### Circuit Breaker Consistency

| Provider | `failure_threshold` | `recovery_timeout` | Notes |
|----------|--------------------|--------------------|-------|
| All (via defaults) | 5 | 300 | Standard |
| Semantic Scholar (source) | 10 | 600 | Rate limit sensitive |

**Status**: CONSISTENT (with documented exception)

### Version Consistency

All pipeline configs use `version: "1.1.0"`.

**Status**: FULLY CONSISTENT

---

## Source Config Analysis

| Source | `rate_limit.rps` | `rate_limit.burst` | Notes |
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
- `source.load_strategy: full`
- `circuit_breaker` settings
- `rate_limit` settings
- `provider_config` with base URL and client settings

**Status**: WELL-STRUCTURED

---

## Recommendations Summary

### Priority 0 (Critical) - NONE

No critical issues requiring immediate action.

### Priority 1 (High) - Schema Documentation

1. **Document the flat vs nested schema choice** in ADR
2. **Document the naming convention** (`<provider>_<entity>` vs `<entity>_<provider>`)

### Priority 2 (Medium) - Optional Enhancements

1. Consider adding `transform.steps` for documentation
2. Add comments explaining empty `partition_by` where missing

### Priority 3 (Low) - Nice to Have

1. Create JSON Schema for config validation
2. Add automated config validation tests

---

## Appendix: Files Analyzed

### Pipeline Configs (19)
- `configs/pipelines/_defaults.yaml`
- `configs/pipelines/chembl/activity.yaml`
- `configs/pipelines/chembl/assay.yaml`
- `configs/pipelines/chembl/assay_parameters.yaml`
- `configs/pipelines/chembl/cell_line.yaml`
- `configs/pipelines/chembl/compound_record.yaml`
- `configs/pipelines/chembl/document.yaml`
- `configs/pipelines/chembl/document_similarity.yaml`
- `configs/pipelines/chembl/document_term.yaml`
- `configs/pipelines/chembl/molecule.yaml`
- `configs/pipelines/chembl/protein_class.yaml`
- `configs/pipelines/chembl/target.yaml`
- `configs/pipelines/chembl/target_component.yaml`
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
