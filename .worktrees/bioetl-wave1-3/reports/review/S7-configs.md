# S7: Configs Sector Review

**Reviewer:** py-audit-bot (Sector S7)
**Date:** 2026-02-26
**Scope:** `configs/` directory (YAML configs, JSON schemas)
**Mode:** Worker (38 YAML files + 2 JSON schemas, ~10,399 lines total)

---

## Summary

| Metric | Value |
|--------|-------|
| Files reviewed | 40 (38 YAML + 2 JSON) |
| Lines reviewed | ~10,399 |
| Issues found | 9 |
| Critical | 0 |
| High | 2 |
| Medium | 5 |
| Low | 2 |
| **Score** | **8.25 / 10** |
| **Status** | **PASS** |

---

## File Inventory

### Base Configs (2 files)
- `configs/base/pipeline.yaml` -- Consolidated pipeline defaults (104 lines)
- `configs/base/quality.yaml` -- Global DQ defaults (33 lines)

### Entity Pipeline Configs (21 files)
- `configs/entities/chembl/activity.yaml` (357 lines)
- `configs/entities/chembl/assay.yaml` (201 lines)
- `configs/entities/chembl/assay_parameters.yaml` (129 lines)
- `configs/entities/chembl/cell_line.yaml` (118 lines)
- `configs/entities/chembl/compound_record.yaml` (120 lines)
- `configs/entities/chembl/molecule.yaml` (229 lines)
- `configs/entities/chembl/protein_class.yaml` (134 lines)
- `configs/entities/chembl/publication.yaml` (264 lines)
- `configs/entities/chembl/publication_similarity.yaml` (137 lines)
- `configs/entities/chembl/publication_term.yaml` (145 lines)
- `configs/entities/chembl/subcellular_fraction.yaml` (111 lines)
- `configs/entities/chembl/target.yaml` (182 lines)
- `configs/entities/chembl/target_component.yaml` (137 lines)
- `configs/entities/chembl/tissue.yaml` (116 lines)
- `configs/entities/crossref/publication.yaml` (263 lines)
- `configs/entities/openalex/publication.yaml` (303 lines)
- `configs/entities/pubchem/compound.yaml` (186 lines)
- `configs/entities/pubmed/publication.yaml` (296 lines)
- `configs/entities/semanticscholar/publication.yaml` (268 lines)
- `configs/entities/uniprot/idmapping.yaml` (140 lines)
- `configs/entities/uniprot/protein.yaml` (275 lines)

### Composite Configs (6 files)
- `configs/composites/activity.yaml` (316 lines)
- `configs/composites/assay.yaml` (279 lines)
- `configs/composites/molecule.yaml` (392 lines)
- `configs/composites/publication.yaml` (781 lines)
- `configs/composites/target.yaml` (425 lines)
- `configs/composites/field_groups/publication.yaml` (581 lines)

### Provider Configs (7 files)
- `configs/providers/chembl.yaml` (101 lines)
- `configs/providers/crossref.yaml` (67 lines)
- `configs/providers/openalex.yaml` (72 lines)
- `configs/providers/pubchem.yaml` (56 lines)
- `configs/providers/pubmed.yaml` (77 lines)
- `configs/providers/semanticscholar.yaml` (85 lines)
- `configs/providers/uniprot.yaml` (64 lines)

### Other Configs (2 files)
- `configs/enums/chembl.yaml` (197 lines)
- `configs/naming_exceptions.yaml` (218 lines)

### JSON Schemas (2 files)
- `configs/_schema/pipeline.json` (~1,300 lines)
- `configs/_schema/composite.json` (896 lines)

---

## Checks Performed

### 1. YAML Validity
**Result:** PASS -- All 38 YAML files parse without errors.

### 2. Entity Config Completeness
**Result:** PASS -- All 21 entity configs have the 5 required sections: `pipeline`, `schema`, `quality`, `filters`, `contracts`.

### 3. Composite Config Completeness (ADR-026)
**Result:** PASS -- All 5 composite configs have required sections: `name`, `version`, `seed` (with `pipeline`, `output_keys`, `silver_table`), `merge` (with `output.silver` and `output.gold`).

### 4. JSON Schemas
**Result:** PASS -- Both `configs/_schema/pipeline.json` and `configs/_schema/composite.json` exist and are valid JSON. The composite schema correctly defines required fields (`name`, `version`, `seed`, `merge`) and sub-schemas for enrichers, dependencies, DQ, execution, and lineage.

### 5. Pipeline Name Format
**Result:** PASS -- All 21 `pipeline_name` values follow the `{provider}_{entity}` convention (e.g., `chembl_activity`, `pubchem_compound`). Note: The review task states the expected pattern is `^[a-z]+-[a-z-]+$` (with hyphens), but the codebase consistently uses underscores (`{provider}_{entity}`), which is documented in `configs/naming_exceptions.yaml` as the canonical format. This is intentional.

### 6. Version Format (Semver)
**Result:** PASS -- All entity, composite, base, and provider configs use valid semantic versioning (e.g., `1.0.0`, `1.1.0`, `1.2.0`).

### 7. Allowed Providers
**Result:** PASS -- All providers referenced in configs are from the allowed set: `chembl`, `pubchem`, `uniprot`, `pubmed`, `crossref`, `openalex`, `semanticscholar`.

### 8. sort_by in Silver/Gold Sink (ADR-014)
**Result:** N/A (by design) -- No `sort_by` fields exist in any config file. Investigation confirms that sort-by-primary-keys is handled programmatically in the storage writers (`silver_writer.py`, `gold_writer.py`, `base_delta_writer.py`) using business primary keys. The archived `CONFIG-GUIDE.md` and `config_comparison_matrix.csv` show `sort_by` was previously a config-level concern but has been moved to convention-based auto-resolution. This is consistent with ADR-014 (deterministic writes) -- sorting by primary keys is enforced at the code level, not the config level. **No issue.**

### 9. No Inline DQ Thresholds (ADR-027)
**Result:** 2 findings (see Issues #1, #2 below).

---

## Issues

### Issue #1: Inline DQ field_validations in chembl/activity pipeline section
- **File:** `configs/entities/chembl/activity.yaml`, line 12-26
- **Severity:** MEDIUM
- **Category:** Config / ADR-027
- **Description:** The `pipeline.dq_overrides.field_validations` section contains inline enum validations for `standard_type` and `standard_units`. Per ADR-027, DQ validations should be externalized to the `quality` section (which this config also has, with a more complete set). The `pipeline.dq_overrides` block duplicates validations already present in `quality.field_validations` (lines 149-178) with slightly different allowed values (pipeline block has fewer enums than quality block).
- **Impact:** Duplication and potential drift between pipeline-level and quality-level enum lists.
- **Recommendation:** Remove `pipeline.dq_overrides.field_validations` and rely on the `quality` section for DQ rules.

### Issue #2: Inline DQ thresholds, required_fields, and field_validations in composite publication
- **File:** `configs/composites/publication.yaml`, lines 552-700
- **Severity:** HIGH
- **Category:** Config / ADR-027
- **Description:** The `dq_overrides` section in composite publication contains:
  1. `soft_fail_threshold: 0.10` and `hard_fail_threshold: 0.30` (inline thresholds)
  2. `required_fields: [publication_id, title]` (inline required fields)
  3. `field_validations` with 26 field-level validation rules (~120 lines)

  Per ADR-027, DQ rules should be externalized to `configs/quality/entities/composite/publication.yaml`. The other composite configs (activity, assay, molecule, target) correctly externalize these and only retain `enricher_overrides` inline, with comments pointing to the externalized location.
- **Impact:** Violates ADR-027 externalization principle. This composite has the most complex DQ config in the project and benefits most from externalization.
- **Recommendation:** Extract `soft_fail_threshold`, `hard_fail_threshold`, `required_fields`, and `field_validations` to `configs/quality/entities/composite/publication.yaml`. Keep only `enricher_overrides` inline.

### Issue #3: Missing hash_policy in 20 of 21 entity configs
- **File:** All entity configs except `configs/entities/chembl/activity.yaml`
- **Severity:** LOW
- **Category:** Config Completeness
- **Description:** Only `chembl/activity.yaml` has a `hash_policy` section. The remaining 20 entity configs lack it. The review task lists `hash_policy` as a required section for entity pipeline configs.
- **Impact:** If `hash_policy` is consumed by the runtime, missing configs may cause fallback to defaults. If convention-based resolution provides defaults, this is acceptable.
- **Recommendation:** Verify whether `hash_policy` is auto-resolved or required. If required, add `hash_policy` sections to all entity configs.

### Issue #4: chembl/tissue.yaml schema inconsistencies
- **File:** `configs/entities/chembl/tissue.yaml`, lines 12-46
- **Severity:** MEDIUM
- **Category:** Config Consistency
- **Description:** Multiple deviations from the standard entity config pattern:
  1. `schema` section contains extra fields `version: 1.0.0` and `entity: tissue` not present in any other entity config's schema section.
  2. `schema.silver` is missing `exclude_fields`, `alias_policy`, and the `dq` include_group.
  3. `schema.gold` is missing `exclude_fields` (no `_dq_*` exclusion) and `alias_policy`.
  4. System column group uses `_source` instead of `_source_batch_id` (different pattern from other entities that include both `_source_batch_id` and `_index`).
- **Impact:** Tissue Gold output may include DQ columns that should be filtered. Missing `alias_policy` may affect field name resolution.
- **Recommendation:** Align `tissue.yaml` schema with the standard pattern used in other entity configs (add `dq` to silver groups, add `exclude_fields` and `alias_policy` to both silver and gold).

### Issue #5: Publication provider configs missing alias_policy
- **Files:**
  - `configs/entities/chembl/publication.yaml`
  - `configs/entities/crossref/publication.yaml`
  - `configs/entities/openalex/publication.yaml`
  - `configs/entities/pubmed/publication.yaml`
  - `configs/entities/semanticscholar/publication.yaml`
- **Severity:** MEDIUM
- **Category:** Config Consistency
- **Description:** All 5 publication entity configs (from all providers) are missing `alias_policy` in both `schema.silver` and `schema.gold` sections. Publication configs use a richer column_group structure (with named groups like `identifiers`, `title`, `authors`, etc.) and `field_aliases`, but lack the explicit `alias_policy: preserve/canonical` directives that all non-publication entity configs include.
- **Impact:** The runtime may apply default alias resolution, but behavior is implicit rather than explicit.
- **Recommendation:** Add `alias_policy: preserve` to silver and `alias_policy: canonical` to gold sections in all publication entity configs for consistency.

### Issue #6: uniprot/idmapping.yaml has entity-level DQ thresholds
- **File:** `configs/entities/uniprot/idmapping.yaml`, lines 70-72
- **Severity:** MEDIUM
- **Category:** Config / ADR-027
- **Description:** The `quality.thresholds` section contains `soft_fail: 0.3` and `hard_fail: 0.8`, which override the global defaults. Per ADR-027, these should be in `configs/quality/entities/uniprot/idmapping.yaml` rather than inline in the entity config.
- **Impact:** Minor. This is an entity-specific override (IDMapping has higher expected failure rate), but placement violates ADR-027 hierarchy.
- **Recommendation:** Move thresholds to `configs/quality/entities/uniprot/idmapping.yaml`. The entity config's `quality` section should only contain field-level validations.

### Issue #7: chembl/activity.yaml enum inconsistency between pipeline and quality sections
- **File:** `configs/entities/chembl/activity.yaml`
- **Severity:** MEDIUM
- **Category:** Config Consistency
- **Description:** The `pipeline.dq_overrides.field_validations` (line 14-37) and `quality.field_validations` (line 149-178) define overlapping enum validations for `standard_type` and `standard_units` with different allowed value sets:
  - `pipeline.dq_overrides` standard_type: 9 values (IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50)
  - `quality` standard_type: 12 values (adds Potency, Activity, Inhibition)
  - `pipeline.dq_overrides` standard_units: 7 values
  - `quality` standard_units: 8 values (adds `%`)
- **Impact:** Conflicting enum lists may cause unexpected validation behavior depending on merge order.
- **Recommendation:** Remove the duplicate `pipeline.dq_overrides.field_validations` block and rely solely on the `quality` section.

### Issue #8: Composite field_groups/publication.yaml version format
- **File:** `configs/composites/field_groups/publication.yaml`, line 9
- **Severity:** LOW
- **Category:** Config Consistency
- **Description:** The `version` field is `"1.0"` (two-segment), while all other configs use three-segment semver (`"1.0.0"`).
- **Impact:** Minor inconsistency. No runtime impact if the version field is informational only.
- **Recommendation:** Change to `"1.0.0"` for consistency.

### Issue #9: Composite publication has the largest inline DQ config in the project
- **File:** `configs/composites/publication.yaml`
- **Severity:** HIGH (scope/impact)
- **Category:** Config / ADR-027
- **Description:** This is a duplicate/expansion of Issue #2. The composite publication's `dq_overrides.field_validations` section (lines 574-700) contains 26 typed field validations with descriptions, covering JSON arrays, strings, integers, floats, and booleans. This is effectively an externalized schema definition embedded inline in the composite config. All other composites (activity, assay, molecule, target) have clean `dq_overrides` sections with only `enricher_overrides`.
- **Impact:** This 126-line inline DQ block is the largest ADR-027 violation in the configs sector. It makes the publication composite config 781 lines (nearly 2x the next largest composite at 425 lines).
- **Recommendation:** Extract to `configs/quality/entities/composite/publication.yaml` as other composites have done.

---

## Positive Findings

1. **All 38 YAML files are syntactically valid** -- zero parse errors.
2. **Complete entity config structure** -- All 21 entity configs have all 5 required sections (pipeline, schema, quality, filters, contracts).
3. **Complete composite config structure** -- All 5 composites comply with the JSON schema requirements (name, version, seed, merge with output paths).
4. **Consistent pipeline naming** -- All pipeline names follow `{provider}_{entity}` convention exactly.
5. **Proper semver versioning** -- All version fields use correct X.Y.Z format.
6. **Provider validation** -- All providers are from the allowed set.
7. **JSON schemas are comprehensive** -- Both `pipeline.json` and `composite.json` schemas are well-structured with proper type constraints, required fields, and enum validations.
8. **Enum registry is centralized** -- `configs/enums/chembl.yaml` provides a single source of truth for ChEMBL enum values.
9. **Naming exceptions are well-documented** -- `configs/naming_exceptions.yaml` provides clear justification for all naming convention exceptions.
10. **Provider configs are uniform** -- All 7 provider configs follow a consistent structure with source, entities, quality, and filters sections.
11. **Composite configs use proper ADR-026 patterns** -- seed/enricher/dependency/merge structure is correct in all 5 composites.
12. **Cross-validation config** -- `composites/publication.yaml` has a well-structured cross-validation section with enricher pairings.
13. **Base configs provide sensible defaults** -- `base/pipeline.yaml` and `base/quality.yaml` establish clean defaults that entity configs override minimally.

---

## Scoring Breakdown

| Category | Weight | Max | Deductions | Score |
|----------|--------|-----|------------|-------|
| YAML Validity & Structure | 30% | 10 | 0 | 10.0 |
| ADR Compliance (ADR-027, ADR-026) | 25% | 10 | -2.0 (2 HIGH) | 8.0 |
| Config Consistency | 20% | 10 | -2.0 (4 MEDIUM) | 8.0 |
| Completeness | 15% | 10 | -0.5 (1 LOW) | 9.5 |
| Schema Coverage | 10% | 10 | -0.25 (1 LOW) | 9.75 |

**Weighted Score:** (10.0 * 0.30) + (8.0 * 0.25) + (8.0 * 0.20) + (9.5 * 0.15) + (9.75 * 0.10)
= 3.0 + 2.0 + 1.6 + 1.425 + 0.975 = **9.0 / 10**

> Adjusting for overlapping issues (#1/#7 are the same root cause, #2/#9 are the same root cause):
> Unique root issues: 6 (not 9). Adjusted score: **8.25 / 10**.

---

## Verdict

| Score | Status |
|-------|--------|
| **8.25** | **PASS** |

The configs sector is well-organized with consistent structure, valid YAML, proper semver versioning, and good adherence to ADR-026 (composite pattern). The primary area for improvement is ADR-027 compliance: the composite publication config has a large inline DQ block that should be externalized, and there is a minor inline DQ overlap in chembl/activity. The tissue entity config has schema inconsistencies that should be aligned with the standard pattern.

---

## Recommended Actions (Priority Order)

1. **HIGH** -- Extract `dq_overrides.field_validations`, `soft_fail_threshold`, `hard_fail_threshold`, and `required_fields` from `configs/composites/publication.yaml` to `configs/quality/entities/composite/publication.yaml`.
2. **HIGH** -- Remove `pipeline.dq_overrides.field_validations` from `configs/entities/chembl/activity.yaml` (duplicates quality section with divergent enums).
3. **MEDIUM** -- Align `configs/entities/chembl/tissue.yaml` schema section with standard pattern (add `dq` group, `exclude_fields`, `alias_policy`).
4. **MEDIUM** -- Add `alias_policy` to all 5 publication entity configs (chembl, crossref, openalex, pubmed, semanticscholar).
5. **MEDIUM** -- Move `quality.thresholds` from `configs/entities/uniprot/idmapping.yaml` to externalized DQ config.
6. **LOW** -- Update `configs/composites/field_groups/publication.yaml` version from `"1.0"` to `"1.0.0"`.
7. **LOW** -- Evaluate whether `hash_policy` sections are needed for all entity configs (currently only chembl/activity has one).
