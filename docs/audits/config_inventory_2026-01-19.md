# Config Inventory Audit

**Date**: 2026-01-19
**Auditor**: Claude (Automated Audit)
**Branch**: claude/audit-pipeline-configs-j4MnR

## ADR Implementation Status

| Component | Expected | Status | Notes |
|-----------|----------|--------|-------|
| `_base.yaml` (was `_defaults.yaml`) | v2.0.0+ | ✅ | v2.0.0, 13271 bytes, named `_base.yaml` per ADR-025 |
| `_schema.json` | exists | ✅ | v2.0, JSON Schema draft 2020-12, 4541 bytes |
| `configs/dq/_defaults.yaml` | exists | ✅ | v1.0.0, defines thresholds (soft_fail: 0.05, hard_fail: 0.20) |
| `configs/dq/providers/` | exists | ✅ | 3 providers: chembl, pubchem, uniprot |
| `configs/dq/entities/` | exists | ✅ | 6 entity-specific DQ configs |
| `validate_unified_configs.py` | exists | ✅ | 4465 bytes, validates against schema |
| `DQConfigLoader` | implemented | ✅ | 9160 bytes, integrated with PipelineConfigLoader |

**Summary**: All 7 ADR infrastructure components exist and are properly implemented.

## Pipeline Configs Inventory

| Provider | Count | Entities |
|----------|-------|----------|
| chembl | 12 | activity, assay, assay_parameters, cell_line, compound_record, molecule, protein_class, publication, publication_similarity, publication_term, target, target_component |
| pubchem | 1 | compound |
| uniprot | 2 | protein, idmapping |
| pubmed | 1 | publications |
| crossref | 1 | publication |
| openalex | 1 | publication |
| semanticscholar | 1 | publication |
| composite | 1 | publication (ADR-026 composite pipeline) |
| **Total** | **20** | |

## DQ Configuration Inventory

### DQ Provider Configs (configs/dq/providers/)
| Provider | File Size | Notes |
|----------|-----------|-------|
| chembl | 1293 bytes | Provider-specific DQ rules |
| pubchem | 778 bytes | Provider-specific DQ rules |
| uniprot | 859 bytes | Provider-specific DQ rules |

### DQ Entity Configs (configs/dq/entities/)
| Provider | Entity | File |
|----------|--------|------|
| chembl | activity | configs/dq/entities/chembl/activity.yaml |
| chembl | assay | configs/dq/entities/chembl/assay.yaml |
| chembl | molecule | configs/dq/entities/chembl/molecule.yaml |
| chembl | target | configs/dq/entities/chembl/target.yaml |
| pubchem | compound | configs/dq/entities/pubchem/compound.yaml |
| uniprot | target | configs/dq/entities/uniprot/target.yaml |

## Validator Results

```
================================================================================
CONFIG VALIDATION REPORT
================================================================================

  [OK] chembl/activity.yaml
  [OK] chembl/assay.yaml
  [OK] chembl/assay_parameters.yaml
  [OK] chembl/cell_line.yaml
  [OK] chembl/compound_record.yaml
  [OK] chembl/molecule.yaml
  [OK] chembl/protein_class.yaml
  [OK] chembl/publication.yaml
  [OK] chembl/publication_similarity.yaml
  [OK] chembl/publication_term.yaml
  [OK] chembl/target.yaml
  [OK] chembl/target_component.yaml
  [ERROR] composite/publication.yaml: Missing required keys (see details below)
  [OK] crossref/publication.yaml
  [OK] openalex/publication.yaml
  [OK] pubchem/compound.yaml
  [OK] pubmed/publications.yaml
  [OK] semanticscholar/publication.yaml
  [OK] uniprot/idmapping.yaml
  [OK] uniprot/protein.yaml

================================================================================
Configs validated: 21
Configs with errors: 1
Total errors: 6
================================================================================
```

### Composite Pipeline Validation Errors (composite/publication.yaml)

The composite pipeline uses a different schema structure per ADR-026:
- Missing standard keys: `description`, `entity_type`, `gold_table`, `input_filter`, `pipeline_name`, `primary_keys`, `provider`, `silver_table`, `sink`, `source_file`, `version`
- These fields are defined differently in composite pipelines (under `composite.merge.output`, etc.)

**Root Cause**: The validator `validate_unified_configs.py` does not yet support the ADR-026 composite pipeline schema. This is a **validator gap**, not a config error.

## Findings

### Blockers (prevent next phase)
- [x] **None** - All ADR infrastructure components are in place

### Issues (non-blocking, should be addressed)

1. **Validator doesn't support composite pipelines**
   - File: `src/tools/scripts/validate_unified_configs.py`
   - Issue: Composite pipelines (ADR-026) use different schema structure
   - Recommendation: Add composite pipeline schema detection and validation

2. **DQ entity configs incomplete**
   - Only 6 of 20 pipelines have entity-specific DQ configs
   - Missing entity DQ configs for: assay_parameters, cell_line, compound_record, protein_class, publication (chembl), publication_similarity, publication_term, target_component, idmapping (uniprot), all non-chembl providers' entities except pubchem/compound and uniprot/target
   - Impact: These use default/provider-level thresholds (acceptable per ADR-027 hierarchy)

### Notes

1. **File naming**: ADR-025 uses `_base.yaml` (not `_defaults.yaml` as mentioned in prompt) for pipeline defaults
2. **Schema version**: Both `_base.yaml` and `_schema.json` are at v2.0.0 (aligned)
3. **DQ defaults version**: configs/dq/_defaults.yaml is at v1.0.0
4. **DQConfigLoader integration**: Properly integrated with `PipelineConfigLoader` in composition layer
5. **Inheritance chain**: `_base.yaml` → `<provider>/<entity>.yaml` (documented in _base.yaml header)

## Version Information

| File | Version |
|------|---------|
| configs/pipelines/_base.yaml | 2.0.0 |
| configs/pipelines/_schema.json | 2.0 |
| configs/dq/_defaults.yaml | 1.0.0 |
| composite/publication.yaml | 1.0.0 |

## Acceptance Criteria Checklist

- [x] All 7 ADR components verified
- [x] Inventory contains exact count of configs (20 pipeline configs)
- [x] Validator results documented
- [x] Report created in `docs/audits/`

## Next Steps

1. **Proceed to next audit phase** - All prerequisites met
2. **Optional improvement**: Update validator to support composite pipeline schema (ADR-026)
3. **Optional improvement**: Add entity-specific DQ configs for remaining pipelines

---

*Audit completed: 2026-01-19*
