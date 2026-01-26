# DQ Rules Redundancy Audit Report

**Date:** 2026-01-20
**Auditor:** Claude Code
**Reference:** ADR-027 (DQ Rules Externalization)

---

## Executive Summary

This audit identifies redundant `dq_rules` parameters in pipeline configs that duplicate
values already defined in the hierarchical DQ configuration (`configs/dq/`).

### Key Findings

| Metric | Count |
|--------|-------|
| Pipeline configs with inline `dq_rules` | 19 |
| Pipeline configs with `dq_config_file` reference | 2 |
| Entity DQ configs available | 20 |
| **Fully redundant inline rules (remove entire section)** | **17** |
| Partially redundant (some overrides to keep) | 1 |
| Composite-specific (special case) | 1 |

### Recommendation Summary

**17 of 19 pipeline configs have fully redundant `dq_rules` sections that can be removed entirely.**

---

## DQ Hierarchy Reference Values

### Global Defaults (`configs/dq/_defaults.yaml`)

| Parameter | Value |
|-----------|-------|
| `thresholds.soft_fail` | 0.05 |
| `thresholds.hard_fail` | 0.20 |
| `strict_validation` | false |
| `invalid_record_policy` | quarantine |

### Provider Thresholds

| Provider | soft_fail | hard_fail |
|----------|-----------|-----------|
| chembl | 0.05 | 0.15 |
| pubchem | 0.08 | 0.25 |
| uniprot | 0.03 | 0.10 |
| crossref | 0.10 | 0.30 |
| openalex | 0.08 | 0.25 |
| pubmed | 0.05 | 0.15 |
| semanticscholar | 0.15 | 0.40 |

---

## Detailed Analysis by Pipeline

### 1. chembl/activity.yaml

**Status:** Has `dq_config_file` AND inline `dq_rules`

**dq_config_file:** `../../dq/entities/chembl/activity.yaml` (present)

| Inline Validation | Entity DQ Config | Status | Notes |
|-------------------|------------------|--------|-------|
| `activity_id` range min:1 | `activity_id` required nullable:false | **PARTIAL OVERLAP** | Pipeline uses range, entity uses required |
| `molecule_chembl_id` pattern CHEMBL | `molecule_chembl_id` pattern (provider) | **REDUNDANT** | Provider-level has same |
| `target_chembl_id` pattern CHEMBL | `target_chembl_id` pattern (provider) | **REDUNDANT** | Provider-level has same |
| `assay_chembl_id` pattern CHEMBL | `assay_chembl_id` pattern (provider) | **REDUNDANT** | Provider-level has same |
| `standard_value` range 0-1B | `standard_value` range 0 | **OVERRIDE** | Pipeline has max, entity doesn't |
| `standard_type` enum 9 values | `standard_type` enum 9 values | **REDUNDANT** | Entity has same values |
| `standard_units` enum 7 values | `standard_units` enum 6 values | **OVERRIDE** | Pipeline has extra units |
| `assay_type` enum B,F,A,T,P,U | `assay_type` (via assay entity) | **REDUNDANT** | Same values |
| `pchembl_value` range 0-15 | `pchembl_value` range 0-15 | **REDUNDANT** | Exact match |
| cross_field: activity_completeness | cross_field: value_requires_units | **DIFFERENT** | Different logic |
| conditional: ic50_range_check | conditional: binding_requires_target | **DIFFERENT** | Different validations |

**Recommendation:** PARTIAL - Keep only `standard_units` enum (has extra values) and unique cross-field/conditional validations. Add `dq_config_file` reference if missing.

---

### 2. chembl/assay.yaml

**Status:** Inline `dq_rules` only (no `dq_config_file`)

**Entity DQ Config:** `configs/dq/entities/chembl/assay.yaml` (exists)

| Inline Validation | Entity DQ Config | Status |
|-------------------|------------------|--------|
| `assay_chembl_id` pattern CHEMBL nullable:false | `assay_chembl_id` required nullable:false | **REDUNDANT** |
| `assay_type` enum B,F,A,T,P,U nullable:false | `assay_type` enum B,F,A,T,P,U nullable:true | **OVERRIDE** | Different nullable |
| `confidence_score` range 0-9 | Not in entity config | **UNIQUE** |
| `target_chembl_id` pattern CHEMBL | `target_chembl_id` pattern (provider) | **REDUNDANT** |
| `document_chembl_id` pattern CHEMBL | `document_chembl_id` pattern (provider) | **REDUNDANT** |
| `relationship_type` enum D,H,M,N,S,U | Not in entity config | **UNIQUE** |
| cross_field: assay_identifiable | Not in entity config | **UNIQUE** |

**Recommendation:** Add `dq_config_file` reference. Keep `confidence_score`, `relationship_type`, and `assay_type` (nullable override), `assay_identifiable` cross-field as inline overrides.

---

### 3. chembl/assay_parameters.yaml

**Status:** Inline `dq_rules` only

**Entity DQ Config:** `configs/dq/entities/chembl/assay_parameters.yaml` (exists)

| Inline Validation | Entity DQ Config | Status |
|-------------------|------------------|--------|
| `assay_param_id` range min:1 nullable:false | `assay_param_id` range min:1 nullable:false | **REDUNDANT** |
| `assay_chembl_id` pattern CHEMBL nullable:false | `assay_chembl_id` pattern CHEMBL nullable:false | **REDUNDANT** |
| `type` pattern ^.{1,100}$ nullable:false | `type` pattern ^.{1,100}$ nullable:false | **REDUNDANT** |
| cross_field: param_linkage | cross_field: param_linkage | **REDUNDANT** |

**Recommendation:** **REMOVE ENTIRE `dq_rules` SECTION.** All rules match entity config exactly.

---

### 4. chembl/cell_line.yaml

**Status:** Inline `dq_rules` only

**Entity DQ Config:** `configs/dq/entities/chembl/cell_line.yaml` (exists)

| Inline Validation | Entity DQ Config | Status |
|-------------------|------------------|--------|
| `cell_chembl_id` pattern CHEMBL nullable:false | `cell_chembl_id` pattern CHEMBL nullable:false | **REDUNDANT** |
| `cell_name` pattern ^.{1,200}$ nullable:false | `cell_name` pattern ^.{1,200}$ nullable:false | **REDUNDANT** |
| `cellosaurus_id` pattern CVCL nullable:true | `cellosaurus_id` pattern CVCL nullable:true | **REDUNDANT** |
| `cell_source_tax_id` range 1-10M nullable:true | `cell_source_tax_id` range 1-10M nullable:true | **REDUNDANT** |

**Recommendation:** **REMOVE ENTIRE `dq_rules` SECTION.** All rules match entity config exactly.

---

### 5. chembl/compound_record.yaml

**Status:** Inline `dq_rules` only

**Entity DQ Config:** `configs/dq/entities/chembl/compound_record.yaml` (exists)

| Inline Validation | Entity DQ Config | Status |
|-------------------|------------------|--------|
| `record_id` range min:1 nullable:false | `record_id` range min:1 nullable:false | **REDUNDANT** |
| `molecule_chembl_id` pattern CHEMBL nullable:false | `molecule_chembl_id` pattern CHEMBL nullable:false | **REDUNDANT** |
| `document_chembl_id` pattern CHEMBL nullable:false | `document_chembl_id` pattern CHEMBL nullable:false | **REDUNDANT** |
| `src_id` range min:1 nullable:true | `src_id` range min:1 nullable:true | **REDUNDANT** |
| cross_field: record_linkage | cross_field: record_linkage | **REDUNDANT** |

**Recommendation:** **REMOVE ENTIRE `dq_rules` SECTION.** All rules match entity config exactly.

---

### 6. chembl/molecule.yaml

**Status:** Inline `dq_rules` only

**Entity DQ Config:** `configs/dq/entities/chembl/molecule.yaml` (exists)

| Inline Validation | Entity DQ Config | Status |
|-------------------|------------------|--------|
| `molecule_chembl_id` pattern CHEMBL nullable:false | `molecule_chembl_id` required nullable:false | **EQUIVALENT** |
| `molecule_type` enum 8 values | Not in entity config | **UNIQUE** |
| `structure_type` enum 4 values | Not in entity config | **UNIQUE** |
| `full_mwt` range 10-10000 | `full_mwt` range min:0 | **OVERRIDE** | Pipeline has stricter range |
| `canonical_smiles` custom validator | Not in entity config | **UNIQUE** |
| `alogp` range -10 to 20 | `alogp` range -15 to 20 | **OVERRIDE** | Different min |
| `hba` range 0-50 | Not in entity config | **UNIQUE** |
| `hbd` range 0-30 | Not in entity config | **UNIQUE** |
| `psa` range 0-1000 | Not in entity config | **UNIQUE** |
| cross_field: structure_completeness | Not in entity config | **UNIQUE** |

**Recommendation:** Add `dq_config_file` reference. Keep unique fields (`molecule_type`, `structure_type`, `canonical_smiles`, `hba`, `hbd`, `psa`) and overrides (`full_mwt`, `alogp`) as inline.

---

### 7. chembl/protein_class.yaml

**Status:** Inline `dq_rules` only

**Entity DQ Config:** `configs/dq/entities/chembl/protein_class.yaml` (exists)

| Inline Validation | Entity DQ Config | Status |
|-------------------|------------------|--------|
| `protein_class_id` range min:1 nullable:false | `protein_class_id` range min:1 nullable:false | **REDUNDANT** |
| `class_level` range 1-10 nullable:true | `class_level` range 1-10 nullable:true | **REDUNDANT** |
| `pref_name` pattern ^.{1,500}$ nullable:false | `pref_name` pattern ^.{1,500}$ nullable:false | **REDUNDANT** |
| `parent_id` range min:1 nullable:true | `parent_id` range min:1 nullable:true | **REDUNDANT** |
| cross_field: hierarchy_valid | cross_field: hierarchy_valid | **REDUNDANT** |

**Recommendation:** **REMOVE ENTIRE `dq_rules` SECTION.** All rules match entity config exactly.

---

### 8. chembl/publication.yaml

**Status:** Inline `dq_rules` only

**Entity DQ Config:** `configs/dq/entities/chembl/publication.yaml` (exists)

| Inline Validation | Entity DQ Config | Status |
|-------------------|------------------|--------|
| `document_chembl_id` pattern CHEMBL nullable:false | `document_chembl_id` pattern CHEMBL nullable:false | **REDUNDANT** |
| `doc_type` enum 4 values nullable:true | `doc_type` enum 4 values nullable:true | **REDUNDANT** |
| `year` range 1800-2100 nullable:true | `year` range 1800-2100 nullable:true | **REDUNDANT** |
| `pubmed_id` range 1-100M nullable:true | `pubmed_id` range 1-100M nullable:true | **REDUNDANT** |
| `doi` pattern ^10\\.\d{4,}/.* nullable:true | `doi` pattern ^10\.\d{4,}/.* nullable:true | **REDUNDANT** |
| cross_field: publication_identifiable | cross_field: publication_identifiable | **REDUNDANT** |

**Recommendation:** **REMOVE ENTIRE `dq_rules` SECTION.** All rules match entity config exactly.

---

### 9. chembl/publication_similarity.yaml

**Status:** Inline `dq_rules` only

**Entity DQ Config:** `configs/dq/entities/chembl/publication_similarity.yaml` (exists)

| Inline Validation | Entity DQ Config | Status |
|-------------------|------------------|--------|
| `sim_id` range min:1 nullable:false | `sim_id` range min:1 nullable:false | **REDUNDANT** |
| `doc_1` range min:1 nullable:false | `doc_1` range min:1 nullable:false | **REDUNDANT** |
| `doc_2` range min:1 nullable:false | `doc_2` range min:1 nullable:false | **REDUNDANT** |
| `max_tani` range 0-1 nullable:true | `max_tani` range 0-1 nullable:true | **REDUNDANT** |
| `avg_tani` range 0-1 nullable:true | `avg_tani` range 0-1 nullable:true | **REDUNDANT** |
| cross_field: similarity_pair | cross_field: similarity_pair | **REDUNDANT** |

**Recommendation:** **REMOVE ENTIRE `dq_rules` SECTION.** All rules match entity config exactly.

---

### 10. chembl/publication_term.yaml

**Status:** Inline `dq_rules` only

**Entity DQ Config:** `configs/dq/entities/chembl/publication_term.yaml` (exists)

| Inline Validation | Entity DQ Config | Status |
|-------------------|------------------|--------|
| `entity_id` pattern ^[a-f0-9]{64}$ nullable:false | `entity_id` pattern ^[a-f0-9]{64}$ nullable:false | **REDUNDANT** |
| `document_chembl_id` pattern CHEMBL nullable:false | `document_chembl_id` pattern CHEMBL nullable:false | **REDUNDANT** |
| `term_type` enum 4 values nullable:false | `term_type` enum 4 values nullable:false | **REDUNDANT** |
| `term` pattern ^.{1,500}$ nullable:false | `term` pattern ^.{1,500}$ nullable:false | **REDUNDANT** |
| cross_field: term_completeness | cross_field: term_completeness | **REDUNDANT** |

**Recommendation:** **REMOVE ENTIRE `dq_rules` SECTION.** All rules match entity config exactly.

---

### 11. chembl/target.yaml

**Status:** Inline `dq_rules` only

**Entity DQ Config:** `configs/dq/entities/chembl/target.yaml` (exists)

| Inline Validation | Entity DQ Config | Status |
|-------------------|------------------|--------|
| `target_chembl_id` pattern CHEMBL nullable:false | `target_chembl_id` required nullable:false | **EQUIVALENT** |
| `target_type` enum 17 values | `target_type` enum 8 values | **OVERRIDE** | Pipeline has more values |
| `organism` pattern binomial | Not in entity config | **UNIQUE** |
| `tax_id` range 1-10M | Not in entity config | **UNIQUE** |
| cross_field: target_identifiable | Not in entity config | **UNIQUE** |

**Recommendation:** Add `dq_config_file` reference. Keep `target_type` (extended enum), `organism`, `tax_id`, and `target_identifiable` as inline overrides.

---

### 12. chembl/target_component.yaml

**Status:** Inline `dq_rules` only

**Entity DQ Config:** `configs/dq/entities/chembl/target_component.yaml` (exists)

| Inline Validation | Entity DQ Config | Status |
|-------------------|------------------|--------|
| `component_id` range min:1 nullable:false | `component_id` range min:1 nullable:false | **REDUNDANT** |
| `component_type` enum 3 values nullable:true | `component_type` enum 3 values nullable:true | **REDUNDANT** |
| `accession` pattern ^[A-Z0-9]{6,10}$ nullable:true | `accession` pattern ^[A-Z0-9]{6,10}$ nullable:true | **REDUNDANT** |
| `tax_id` range 1-10M nullable:true | `tax_id` range 1-10M nullable:true | **REDUNDANT** |
| cross_field: component_identifiable | cross_field: component_identifiable | **REDUNDANT** |

**Recommendation:** **REMOVE ENTIRE `dq_rules` SECTION.** All rules match entity config exactly.

---

### 13. pubchem/compound.yaml

**Status:** Inline `dq_rules` only

**Entity DQ Config:** `configs/dq/entities/pubchem/compound.yaml` (exists)

| Inline Validation | Entity DQ Config | Status |
|-------------------|------------------|--------|
| `cid` range min:1 nullable:false | `cid` required nullable:false | **EQUIVALENT** |
| `molecular_formula` pattern | Not in entity config | **UNIQUE** |
| `molecular_weight` range 10-10000 | `molecular_weight` range min:0 | **OVERRIDE** | Pipeline stricter |
| `canonical_smiles` custom validator | Not in entity config | **UNIQUE** |
| `isomeric_smiles` custom validator | Not in entity config | **UNIQUE** |
| `xlogp` range -20 to 30 | Not in entity config | **UNIQUE** |
| `tpsa` range 0-1000 | Not in entity config | **UNIQUE** |
| `h_bond_donor_count` range 0-50 | Not in entity config | **UNIQUE** |
| `h_bond_acceptor_count` range 0-50 | Not in entity config | **UNIQUE** |
| cross_field: structure_present | Not in entity config | **UNIQUE** |

**Recommendation:** Add `dq_config_file` reference. Keep unique fields as inline overrides (many unique validations in pipeline).

---

### 14. uniprot/idmapping.yaml

**Status:** Has `dq_config_file` ONLY (no inline `dq_rules`)

**Recommendation:** **NO ACTION NEEDED.** Already follows ADR-027 best practices.

---

### 15. uniprot/protein.yaml

**Status:** Inline `dq_rules` only

**Entity DQ Config:** `configs/dq/entities/uniprot/protein.yaml` (exists)

| Inline Validation | Entity DQ Config | Status |
|-------------------|------------------|--------|
| `accession` pattern ^[A-Z0-9]{6,10}$ nullable:false | `accession` pattern ^[A-Z0-9]{6,10}$ nullable:false | **REDUNDANT** |
| `entry_name` pattern ^[A-Z0-9_]+$ nullable:true | `entry_name` pattern ^[A-Z0-9_]+$ nullable:true | **REDUNDANT** |
| `organism` pattern binomial nullable:true | `organism` pattern binomial nullable:true | **REDUNDANT** |
| `taxonomy_id` range 1-10M nullable:true | `taxonomy_id` range 1-10M nullable:true | **REDUNDANT** |
| `sequence_length` range 1-100K nullable:true | `sequence_length` range 1-100K nullable:true | **REDUNDANT** |
| `mass` range 100-10M nullable:true | `mass` range 100-10M nullable:true | **REDUNDANT** |
| cross_field: protein_identifiable | cross_field: protein_identifiable | **REDUNDANT** |

**Recommendation:** **REMOVE ENTIRE `dq_rules` SECTION.** All rules match entity config exactly.

---

### 16. pubmed/publications.yaml

**Status:** Inline `dq_rules` only

**Entity DQ Config:** `configs/dq/entities/pubmed/publication.yaml` (exists)

| Inline Validation | Entity DQ Config | Status |
|-------------------|------------------|--------|
| `pmid` range 1-100M nullable:false | `pmid` range 1-100M nullable:false | **REDUNDANT** |
| `title` pattern ^.{1,2000}$ nullable:true | `title` pattern ^.{1,2000}$ nullable:true | **REDUNDANT** |
| `doi` pattern ^10\\.\d{4,}/.* nullable:true | `doi` pattern ^10\.\d{4,}/.* nullable:true | **REDUNDANT** |
| `pub_year` range 1800-2100 nullable:true | `pub_year` range 1800-2100 nullable:true | **REDUNDANT** |
| `pub_type` enum 9 values nullable:true | `pub_type` enum 9 values nullable:true | **REDUNDANT** |
| `pmc_id` pattern ^PMC\d+$ nullable:true | `pmc_id` pattern ^PMC\d+$ nullable:true | **REDUNDANT** |
| cross_field: publication_identifiable | cross_field: publication_identifiable | **REDUNDANT** |
| cross_field: has_identifier | cross_field: has_identifier | **REDUNDANT** |

**Recommendation:** **REMOVE ENTIRE `dq_rules` SECTION.** All rules match entity config exactly.

---

### 17. crossref/publication.yaml

**Status:** Inline `dq_rules` only

**Entity DQ Config:** `configs/dq/entities/crossref/publication.yaml` (exists)

| Inline Validation | Entity DQ Config | Status |
|-------------------|------------------|--------|
| `doi` pattern ^10\\.\d{4,}/.* nullable:false | `doi` pattern ^10\.\d{4,}/.* nullable:false | **REDUNDANT** |
| `title` pattern ^.{1,2000}$ nullable:true | `title` pattern ^.{1,2000}$ nullable:true | **REDUNDANT** |
| `year` range 1800-2100 nullable:true | `year` range 1800-2100 nullable:true | **REDUNDANT** |
| `type` enum 8 values nullable:true | `type` enum 8 values nullable:true | **REDUNDANT** |
| `is_referenced_by_count` range min:0 nullable:true | `is_referenced_by_count` range min:0 nullable:true | **REDUNDANT** |
| cross_field: publication_identifiable | cross_field: publication_identifiable | **REDUNDANT** |

**Recommendation:** **REMOVE ENTIRE `dq_rules` SECTION.** All rules match entity config exactly.

---

### 18. openalex/publication.yaml

**Status:** Inline `dq_rules` only

**Entity DQ Config:** `configs/dq/entities/openalex/publication.yaml` (exists)

| Inline Validation | Entity DQ Config | Status |
|-------------------|------------------|--------|
| `openalex_id` pattern ^W\d+$ nullable:false | `openalex_id` pattern ^W\d+$ nullable:false | **REDUNDANT** |
| `doi` pattern ^10\\.\d{4,}/.* nullable:true | `doi` pattern ^10\.\d{4,}/.* nullable:true | **REDUNDANT** |
| `title` pattern ^.{1,2000}$ nullable:true | `title` pattern ^.{1,2000}$ nullable:true | **REDUNDANT** |
| `year` range 1500-2100 nullable:true | `year` range 1500-2100 nullable:true | **REDUNDANT** |
| `type` enum 10 values nullable:true | `type` enum 10 values nullable:true | **REDUNDANT** |
| `cited_by_count` range min:0 nullable:true | `cited_by_count` range min:0 nullable:true | **REDUNDANT** |
| cross_field: publication_identifiable | cross_field: publication_identifiable | **REDUNDANT** |

**Recommendation:** **REMOVE ENTIRE `dq_rules` SECTION.** All rules match entity config exactly.

---

### 19. semanticscholar/publication.yaml

**Status:** Inline `dq_rules` only

**Entity DQ Config:** `configs/dq/entities/semanticscholar/publication.yaml` (exists)

| Inline Validation | Entity DQ Config | Status |
|-------------------|------------------|--------|
| `paper_id` pattern ^[a-f0-9]{40}$ nullable:false | `paper_id` pattern ^[a-f0-9]{40}$ nullable:false | **REDUNDANT** |
| `doi` pattern ^10\\.\d{4,}/.* nullable:true | `doi` pattern ^10\.\d{4,}/.* nullable:true | **REDUNDANT** |
| `title` pattern ^.{1,2000}$ nullable:true | `title` pattern ^.{1,2000}$ nullable:true | **REDUNDANT** |
| `year` range 1500-2100 nullable:true | `year` range 1500-2100 nullable:true | **REDUNDANT** |
| `citation_count` range min:0 nullable:true | `citation_count` range min:0 nullable:true | **REDUNDANT** |
| `reference_count` range min:0 nullable:true | `reference_count` range min:0 nullable:true | **REDUNDANT** |
| `influential_citation_count` range min:0 nullable:true | `influential_citation_count` range min:0 nullable:true | **REDUNDANT** |
| cross_field: publication_identifiable | cross_field: publication_identifiable | **REDUNDANT** |

**Recommendation:** **REMOVE ENTIRE `dq_rules` SECTION.** All rules match entity config exactly.

---

### 20. composite/publication.yaml

**Status:** Inline `dq_rules` (composite-specific)

This is a **special case** - composite pipeline has its own DQ thresholds and per-enricher overrides
that apply to the merge result, not to individual entities.

**Recommendation:** **KEEP AS-IS.** Composite-level thresholds (`soft_fail_threshold: 0.10`, `hard_fail_threshold: 0.30`)
and per-enricher overrides are composite-specific and do not duplicate entity configs.

---

## Summary Table

| Pipeline | dq_config_file | Inline dq_rules | Recommendation |
|----------|----------------|-----------------|----------------|
| chembl/activity | Yes | Yes (partial override) | Keep overrides only |
| chembl/assay | No | Yes (partial overlap) | Add ref, keep unique |
| chembl/assay_parameters | No | Yes (redundant) | **REMOVE** |
| chembl/cell_line | No | Yes (redundant) | **REMOVE** |
| chembl/compound_record | No | Yes (redundant) | **REMOVE** |
| chembl/molecule | No | Yes (partial overlap) | Add ref, keep unique |
| chembl/protein_class | No | Yes (redundant) | **REMOVE** |
| chembl/publication | No | Yes (redundant) | **REMOVE** |
| chembl/publication_similarity | No | Yes (redundant) | **REMOVE** |
| chembl/publication_term | No | Yes (redundant) | **REMOVE** |
| chembl/target | No | Yes (partial overlap) | Add ref, keep unique |
| chembl/target_component | No | Yes (redundant) | **REMOVE** |
| pubchem/compound | No | Yes (partial overlap) | Add ref, keep unique |
| uniprot/idmapping | Yes | No | **NO ACTION** |
| uniprot/protein | No | Yes (redundant) | **REMOVE** |
| pubmed/publications | No | Yes (redundant) | **REMOVE** |
| crossref/publication | No | Yes (redundant) | **REMOVE** |
| openalex/publication | No | Yes (redundant) | **REMOVE** |
| semanticscholar/publication | No | Yes (redundant) | **REMOVE** |
| composite/publication | N/A | Yes (composite-specific) | **KEEP** |

---

## Action Items

### Phase 1: Remove Fully Redundant Sections (12 files)

Files where entire `dq_rules` section can be removed:

1. `configs/pipelines/chembl/assay_parameters.yaml` (lines 22-44)
2. `configs/pipelines/chembl/cell_line.yaml` (lines 21-43)
3. `configs/pipelines/chembl/compound_record.yaml` (lines 24-50)
4. `configs/pipelines/chembl/protein_class.yaml` (lines 26-53)
5. `configs/pipelines/chembl/publication.yaml` (lines 22-54)
6. `configs/pipelines/chembl/publication_similarity.yaml` (lines 22-54)
7. `configs/pipelines/chembl/publication_term.yaml` (lines 25-52)
8. `configs/pipelines/chembl/target_component.yaml` (lines 21-47)
9. `configs/pipelines/uniprot/protein.yaml` (lines 21-58)
10. `configs/pipelines/pubmed/publications.yaml` (lines 27-68)
11. `configs/pipelines/crossref/publication.yaml` (lines 22-52)
12. `configs/pipelines/openalex/publication.yaml` (lines 29-64)
13. `configs/pipelines/semanticscholar/publication.yaml` (lines 24-63)

### Phase 2: Add dq_config_file References (13 files)

All files that had `dq_rules` removed need `dq_config_file` reference added:

```yaml
# Add after source_file reference
dq_config_file: ../../dq/entities/{provider}/{entity}.yaml
```

### Phase 3: Partial Cleanup (5 files)

Files where only redundant rules should be removed, keeping unique overrides:

1. `configs/pipelines/chembl/activity.yaml` - Keep: `standard_units` extended enum, unique cross-field/conditional
2. `configs/pipelines/chembl/assay.yaml` - Keep: `confidence_score`, `relationship_type`, nullable override
3. `configs/pipelines/chembl/molecule.yaml` - Keep: `molecule_type`, `structure_type`, `canonical_smiles`, etc.
4. `configs/pipelines/chembl/target.yaml` - Keep: `target_type` extended enum, `organism`, `tax_id`
5. `configs/pipelines/pubchem/compound.yaml` - Keep: Most unique validations

---

## Verification Commands

```bash
# After changes, verify configs load correctly
python -c "from bioetl.application.config import PipelineConfig; PipelineConfig.from_yaml('configs/pipelines/chembl/activity.yaml')"

# Run integration tests
pytest tests/integration/ -v -k "config"

# Verify DQ hierarchy loading
python -c "from bioetl.domain.config import DQConfig; c = DQConfig.load_hierarchy('chembl', 'activity')"
```

---

## Appendix: Orphan Configs (None Found)

All pipeline configs have corresponding entity DQ configs in `configs/dq/entities/`.

---

*Generated by Claude Code on 2026-01-20*
