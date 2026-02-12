# Configuration Issues Report (Enhanced)

Generated: 2026-02-03T15:30:00Z
Analyzer: Claude Config Audit Agent v2.1

---

## Summary

### Config Counts

| Category | Count |
|----------|-------|
| **Total Configs** | 97 |
| Pipeline configs (regular) | 19 |
| Composite configs | 2 |
| DQ configs | 29 |
| Filter configs | 28 |
| Source configs | 7 |
| Data schema configs | 22 |

### Issue Summary

| Severity | Count | Status |
|----------|-------|--------|
| **CRITICAL** | 0 | - |
| **HIGH** | 0 | - |
| **MEDIUM** | 3 | Style recommendations |
| **LOW** | 2 | Documentation notes |
| **Total** | 5 | No breaking issues |

---

## ADR Compliance Status

| ADR | Status | Notes |
|-----|--------|-------|
| **ADR-014** (Deterministic Writes) | COMPLIANT | `sort_by.columns` auto-propagated from `primary_keys` |
| **ADR-025** (Config Unification) | COMPLIANT | `_base.yaml` v2.0.0 inheritance working |
| **ADR-027** (DQ Externalization) | COMPLIANT | Hierarchical DQ merge working |
| **ADR-028** (Filter Externalization) | COMPLIANT | Hierarchical filter merge working |
| **ADR-029** (Convention Paths) | COMPLIANT | Auto-computation verified in `config_loader.py` |

---

## Issues by Priority

### P3 - Style Recommendations (MEDIUM)

#### STYLE-001: Mixed Configuration Styles in ChEMBL Provider

**Files Affected:**
- `configs/pipelines/chembl/activity.yaml` (convention-based)
- `configs/pipelines/chembl/assay.yaml` (convention-based)
- `configs/pipelines/chembl/molecule.yaml` (fully explicit)
- ... and 9 other ChEMBL configs (explicit)

**Observation:**
ChEMBL provider uses mixed styles - some configs rely on ADR-029 convention defaults while others specify everything explicitly. Both approaches are valid, but consistency within a provider aids maintainability.

**Recommendation:**
Consider standardizing all ChEMBL configs to use the same style. Suggested: convention-based minimal (reduces duplication).

**Impact:** Low - both styles produce correct results.

---

#### STYLE-002: Two Naming Conventions for Column Schema Files

**Variants:**
1. `column_groups_file` (14 configs) - original naming
2. `data_schema_file` (6 configs) - newer naming with layer-specific support

**Files using `data_schema_file`:**
- `configs/pipelines/chembl/publication.yaml`
- `configs/pipelines/pubmed/publication.yaml`
- `configs/pipelines/crossref/publication.yaml`
- `configs/pipelines/openalex/publication.yaml`
- `configs/pipelines/semanticscholar/publication.yaml`

**Recommendation:**
Both work correctly. Prefer `data_schema_file` for new configs as it supports layer-specific column definitions (silver/gold).

**Impact:** None - both names are supported by `config_loader.py:299-325`.

---

#### STYLE-003: Undocumented Parameters in Use

**Parameters found in configs but not in `_schema.json`:**

| Parameter | Files | Type | Usage |
|-----------|-------|------|-------|
| `force_full_scan` | 7 publication configs | boolean | Disable checkpoint resume |
| `loading_strategy` | 7 publication configs | string | "full_scan_only" |
| `batch_size` | protein_class.yaml | integer | Override default batch |
| `checkpoint_interval` | protein_class.yaml | integer | Checkpoint frequency |

**Recommendation:**
Add these parameters to `configs/pipelines/_schema.json` for validation.

**Impact:** None - parameters work correctly, just not schema-validated.

---

### P4 - Documentation Notes (LOW)

#### DOC-001: CrossRef entity_type Convention

`crossref/publication.yaml` uses `entity_type: work` instead of `publication`.

**Reason:** CrossRef API uses "Works" terminology for publications.
**Status:** By design, not an issue.
**Recommendation:** Add comment in config explaining the naming.

---

#### DOC-002: Version Number Variations

| Version | Count | Usage |
|---------|-------|-------|
| 1.2.0 | 14 | Standard entity pipelines |
| 2.1.0 | 4 | Publication entities with full_scan |
| 1.1.0 | 1 | uniprot_idmapping |

**Status:** Intentional - different versions reflect different loading strategies.
**Recommendation:** Document versioning policy in `_base.yaml` header.

---

## Verified Correct Configurations

The following concerns were investigated and found to be NON-ISSUES:

| Concern | Investigation Result |
|---------|---------------------|
| "pubmed_publication missing sink.silver.primary_key" | Auto-propagated by convention (`config_loader.py:167-168`) |
| "pubmed_publication missing sink.silver.sort_by" | Auto-propagated by convention (`config_loader.py:170-172`) |
| "uniprot_protein missing explicit sink paths" | Auto-computed by convention (`config_loader.py:163`) |
| "activity.yaml missing source_file" | Auto-computed as `../../sources/chembl.yaml` |

---

## Conclusion

**No breaking issues found.** All configurations are valid and ADR-compliant.

The convention-based path resolution system (ADR-029) implemented in `config_loader.py` correctly auto-computes:
- File references (`source_file`, `dq_config_file`, `filter_config_file`)
- Sink paths for bronze/silver/gold layers
- Primary key and sort_by propagation

Recommendations are style improvements, not functional fixes.
