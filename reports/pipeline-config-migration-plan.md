# Pipeline Configuration Migration Plan

*Version: 1.0.0*
*Date: 2026-01-13*
*Status: APPROVED*

---

## Executive Summary

This document outlines the migration plan to unify BioETL pipeline configurations.
The analysis revealed that the **current configuration structure is well-designed**
and requires only minor enhancements rather than major restructuring.

**Key Finding**: The existing inheritance mechanism (`_defaults.yaml` + source configs)
already implements the DRY principle effectively. No critical violations were found.

---

## Migration Phases

### Phase 0: Documentation (Priority: P0) - COMPLETED

**Objective**: Document the current configuration architecture and design decisions.

**Deliverables**:
- [x] Compliance matrix (`reports/pipeline-config-matrix.csv`)
- [x] Discrepancy report (`reports/pipeline-config-issues.md`)
- [x] Unified base schema (`configs/pipelines/_base.yaml`)
- [x] Provider-specific documentation (`configs/pipelines/_providers/`)
- [x] ADR-025: Pipeline Configuration Unification

**Status**: COMPLETED

---

### Phase 1: Critical Fixes (Priority: P0) - NO ACTION REQUIRED

**Objective**: Fix any critical schema violations.

**Assessment**: No critical violations found.

| Issue | Status |
|-------|--------|
| `format: parquet` in Silver | NOT FOUND |
| Missing pipeline identifiers | NOT FOUND |
| Hardcoded secrets | NOT FOUND |
| Missing DQ thresholds | NOT FOUND (inherited) |

**Status**: NO ACTION REQUIRED

---

### Phase 2: Schema Validation (Priority: P1)

**Objective**: Add automated schema validation for pipeline configs.

#### Tasks

- [ ] **2.1** Create JSON Schema for pipeline configs
  ```
  configs/schemas/pipeline.schema.json
  ```

- [ ] **2.2** Create JSON Schema for source configs
  ```
  configs/schemas/source.schema.json
  ```

- [ ] **2.3** Add schema validation test
  ```
  tests/unit/configs/test_pipeline_config_schema.py
  ```

- [ ] **2.4** Add CI check for config validation
  ```yaml
  # .github/workflows/tests.yml
  - name: Validate pipeline configs
    run: make validate-configs
  ```

#### Schema Definition (Draft)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "BioETL Pipeline Configuration",
  "type": "object",
  "required": ["pipeline_name", "provider", "entity_type", "version", "primary_keys"],
  "properties": {
    "pipeline_name": {
      "type": "string",
      "pattern": "^[a-z]+_[a-z_]+$"
    },
    "provider": {
      "type": "string",
      "enum": ["chembl", "pubchem", "uniprot", "crossref", "openalex", "pubmed", "semanticscholar"]
    },
    "entity_type": {
      "type": "string"
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$"
    },
    "sink": {
      "type": "object",
      "properties": {
        "silver": {
          "type": "object",
          "required": ["primary_key"],
          "properties": {
            "format": {
              "type": "string",
              "const": "delta"
            }
          }
        }
      }
    }
  }
}
```

---

### Phase 3: Optional Enhancements (Priority: P2)

**Objective**: Add recommended (SHOULD) parameters where missing.

#### 3.1 Add `transform.steps` Documentation

For pipelines with complex transformations, add documentation of steps:

- [ ] `chembl/activity.yaml` - add transform.steps
- [ ] `chembl/molecule.yaml` - add transform.steps (SMILES validation)
- [ ] `pubchem/compound.yaml` - add transform.steps
- [ ] Other pipelines as needed

**Example**:
```yaml
transform:
  steps:
    - normalize_units      # Convert to standard units (nM)
    - validate_smiles      # Check SMILES syntax
    - deduplicate          # Remove duplicates by content_hash
```

#### 3.2 Document Empty `partition_by`

Add comments explaining empty partition_by where not already documented:

- [ ] `chembl/activity.yaml` - add comment
- [ ] `chembl/cell_line.yaml` - add comment
- [ ] `chembl/compound_record.yaml` - add comment

**Example**:
```yaml
sink:
  silver:
    # partition_by: []  # No natural partition key for this entity
    partition_by: []
```

---

### Phase 4: Future Considerations (Priority: P3)

**Objective**: Long-term improvements for consideration.

#### 4.1 Config Inheritance via YAML Anchors

Consider using YAML anchors for cleaner inheritance:

```yaml
# _base.yaml
defaults: &defaults
  sink:
    silver:
      format: delta
      mode: merge

# chembl/activity.yaml
<<: *defaults
pipeline_name: chembl_activity
```

**Note**: This requires config loader changes. Current approach is functional.

#### 4.2 Environment-Specific Configs

Consider adding environment overrides:

```
configs/
  pipelines/
    chembl/
      activity.yaml          # Base config
      activity.dev.yaml      # Development overrides
      activity.prod.yaml     # Production overrides
```

**Note**: Not needed for current local-only architecture.

---

## Rollback Plan

If migration causes issues:

1. **Revert commits**: `git revert <migration-commit>`
2. **No config changes required**: New files are additive only
3. **Tests validate**: `make test` before and after

---

## Acceptance Criteria

### Phase 1 (Critical)
- [x] No `format: parquet` in Silver configs
- [x] All configs have required fields
- [x] No hardcoded secrets

### Phase 2 (Validation)
- [ ] JSON Schema created and documented
- [ ] `make validate-configs` passes
- [ ] CI includes config validation

### Phase 3 (Documentation)
- [ ] `transform.steps` documented where applicable
- [ ] Empty `partition_by` commented
- [ ] All deviations from defaults documented

---

## Timeline

| Phase | Priority | Effort | Status |
|-------|----------|--------|--------|
| Phase 0 | P0 | 4h | COMPLETED |
| Phase 1 | P0 | 0h | NO ACTION |
| Phase 2 | P1 | 8h | PLANNED |
| Phase 3 | P2 | 4h | PLANNED |
| Phase 4 | P3 | TBD | BACKLOG |

---

## Appendix: File Changes Summary

### New Files Created

| File | Purpose |
|------|---------|
| `configs/pipelines/_base.yaml` | Unified base schema documentation |
| `configs/pipelines/_providers/chembl.yaml` | ChEMBL provider documentation |
| `configs/pipelines/_providers/pubchem.yaml` | PubChem provider documentation |
| `configs/pipelines/_providers/uniprot.yaml` | UniProt provider documentation |
| `configs/pipelines/_providers/crossref.yaml` | CrossRef provider documentation |
| `configs/pipelines/_providers/openalex.yaml` | OpenAlex provider documentation |
| `configs/pipelines/_providers/pubmed.yaml` | PubMed provider documentation |
| `configs/pipelines/_providers/semanticscholar.yaml` | Semantic Scholar provider documentation |
| `reports/pipeline-config-matrix.csv` | Compliance matrix |
| `reports/pipeline-config-issues.md` | Discrepancy report |
| `reports/pipeline-config-migration-plan.md` | This document |
| `docs/02-architecture/decisions/ADR-025-pipeline-config-unification.md` | ADR |

### Existing Files - No Changes Required

All existing pipeline configs are compliant and require no modifications.
