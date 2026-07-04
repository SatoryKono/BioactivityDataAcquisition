# GitHub Issues для снижения compatibility_test_files

## Issue #1: Удалить устаревший silver_writer compatibility retirement test

**Title:** Remove obsolete silver_writer_compatibility_retirement.py guard

**Priority:** P1 (Low risk, high impact)

**Labels:** `test-governance`, `compatibility-debt`, `good-first-issue`

**Description:**
The test `tests/architecture/test_silver_writer_compatibility_retirement.py` verifies that retired SilverWriter compatibility mixin files are deleted. Since these files are already deleted and will not return, the guard test itself is obsolete and can be removed.

**Context:**
- Current compatibility_test_files: 37
- Target after this issue: 36
- The test checks for non-existence of already-deleted files
- No functional code depends on this guard

**Steps:**
1. Delete `tests/architecture/test_silver_writer_compatibility_retirement.py`
2. Update `configs/quality/test_governance_audit.yaml`:
   - Remove entry from `compatibility_test_inventory.entries`
   - Update `total_files: 36`
   - Update `budgets.compatibility_test_file_max: 36`
   - Add note to `stream_g_owner_notes`
3. Regenerate `reports/quality/test-governance-current.json`
4. Regenerate `reports/quality/test-duplicate-name-inventory.json`
5. Run `pytest tests/architecture/test_test_governance_audit.py` to verify

**Acceptance Criteria:**
- [ ] File deleted
- [ ] Configuration updated (total_files: 36, budget: 36)
- [ ] Governance note added
- [ ] Artifacts regenerated
- [ ] All architecture tests pass

**Risk:** Low - removes obsolete guard only

---

## Issue #2: Устранить Pandera compatibility stubs

**Title:** Remove Pandera compatibility layer if unused

**Priority:** P2 (Medium risk, requires analysis)

**Labels:** `test-governance`, `compatibility-debt`, `requires-investigation`

**Description:**
The test `tests/unit/infrastructure/test_pandera_compat.py` contains stub functions for Pandera compatibility. Need to verify if Pandera is still used in the project and if this compatibility layer is still required.

**Context:**
- Current compatibility_test_files: 36 (after #1)
- Target after this issue: 35 (if Pandera unused) or 36 (if still needed)
- File contains stub functions like `_get_origin_stub`, `_get_args_stub`, `_compat_disabled`, etc.

**Steps:**
1. Search codebase for Pandera usage:
   ```bash
   rg -i "pandera" --type py
   ```
2. Check if `test_pandera_compat.py` is actually testing real functionality or just stubs
3. If Pandera is unused:
   - Delete `tests/unit/infrastructure/test_pandera_compat.py`
   - Remove any Pandera-related compatibility code from source
   - Update configuration (total_files: 35, budget: 35)
   - Add governance note
4. If Pandera is still used:
   - Rename test to canonical name (remove `_compat` suffix)
   - Update inventory classification if needed
   - Close issue as "won't fix" with rationale

**Acceptance Criteria:**
- [ ] Pandera usage analyzed
- [ ] Either: test deleted OR test renamed with rationale
- [ ] Configuration updated (if deleted)
- [ ] All tests pass

**Risk:** Medium - requires careful analysis of dependencies

---

## Issue #3: Устранить memory legacy module aliases

**Title:** Remove memory legacy module aliases and tests

**Priority:** P2 (Medium risk, potential external dependencies)

**Labels:** `test-governance`, `compatibility-debt`, `requires-investigation`

**Description:**
The test `tests/unit/scripts/ops/test_memory_legacy_aliases.py` verifies that legacy module aliases point to canonical modules. Need to check if these legacy aliases are still used by external code or can be safely removed.

**Context:**
- Current compatibility_test_files: 35 (after #2, assuming Pandera removed)
- Target after this issue: 34 (if aliases unused) or 35 (if still needed)
- Legacy aliases tested:
  - `scripts.memory.sync` → `memory.graph.sync`
  - `scripts.ops.neo4j_memory_sync` → `memory.graph.sync`
  - `scripts.memory.query` → `memory.graph.query`

**Steps:**
1. Search codebase for usage of legacy aliases:
   ```bash
   rg "scripts.memory.sync|scripts.ops.neo4j_memory_sync|scripts.memory.query" --type py
   ```
2. Check if any external documentation or scripts reference these aliases
3. If aliases are unused:
   - Delete `tests/unit/scripts/ops/test_memory_legacy_aliases.py`
   - Remove legacy alias definitions from source
   - Update configuration (total_files: 34, budget: 34)
   - Add governance note
4. If aliases are still used:
   - Document why they're needed
   - Update review date in inventory
   - Close issue with rationale

**Acceptance Criteria:**
- [ ] Legacy alias usage analyzed
- [ ] Either: test and aliases deleted OR documented with rationale
- [ ] Configuration updated (if deleted)
- [ ] All tests pass

**Risk:** Medium - potential external dependencies on aliases

---

## Issue #4: Устранить legacy config normalization

**Title:** Migrate from legacy to canonical config normalization

**Priority:** P2 (Medium risk, requires migration)

**Labels:** `test-governance`, `compatibility-debt`, `refactor`

**Description:**
Two tests verify legacy config normalization: `test_pipeline_config_legacy_normalization.py` and `test_source_config_legacy_normalization.py`. Need to migrate to canonical normalization and remove legacy code.

**Context:**
- Current compatibility_test_files: 34 (after #3)
- Target after this issue: 32 (both tests removed)
- Legacy normalization paths may be used by old configs

**Steps:**
1. Analyze legacy normalization implementation
2. Search for usage of legacy normalization:
   ```bash
   rg "legacy_normalization|LegacyNormalization" --type py
   ```
3. If unused:
   - Delete both test files
   - Remove legacy normalization code
   - Update configuration (total_files: 32, budget: 32)
4. If used:
   - Identify all configs using legacy normalization
   - Migrate configs to canonical normalization
   - Delete legacy code and tests
   - Update configuration
5. Add migration guide to docs if needed

**Acceptance Criteria:**
- [ ] Legacy normalization usage analyzed
- [ ] Configs migrated to canonical normalization (if needed)
- [ ] Legacy code and tests deleted
- [ ] Configuration updated (total_files: 32, budget: 32)
- [ ] All tests pass
- [ ] Migration guide added (if configs migrated)

**Risk:** Medium - may affect existing configurations

---

## Issue #5: Устранить adapter compatibility layers

**Title:** Remove adapter compatibility layers for crossref/pubchem/pubmed

**Priority:** P2 (Medium risk, adapter-specific)

**Labels:** `test-governance`, `compatibility-debt`, `requires-investigation`

**Description:**
Three adapter compatibility tests exist:
- `test_crossref_compatibility.py`
- `test_pubchem_fetch_strategies_compat.py`
- `test_pubmed_models_compat.py`

Need to verify if these compatibility layers are still required.

**Context:**
- Current compatibility_test_files: 32 (after #4)
- Target after this issue: 29 (all three removed)
- Each adapter may have different compatibility requirements

**Steps:**
1. For each adapter:
   - Analyze compatibility layer implementation
   - Search for usage of compatibility code
   - Check if adapter has breaking changes that require compatibility
2. If compatibility unused:
   - Delete test file
   - Remove compatibility code from adapter
   - Update configuration
3. If compatibility still needed:
   - Document why
   - Update review date
   - Consider if it can be refactored to canonical pattern
4. Update configuration for each removed test

**Acceptance Criteria:**
- [ ] All three adapters analyzed
- [ ] Unused compatibility layers removed
- [ ] Tests deleted for removed layers
- [ ] Configuration updated (target: 29 or based on analysis)
- [ ] All tests pass

**Risk:** Medium - adapter-specific, may affect integration tests

---

## Issue #6: Устранить deprecated gold contract compatibility

**Title:** Remove deprecated gold contract registry and nullable numeric compatibility

**Priority:** P2 (Medium risk, data contract impact)

**Labels:** `test-governance`, `compatibility-debt`, `data-contracts`

**Description:**
Two integration tests verify deprecated gold contract compatibility:
- `test_deprecated_gold_contract_registry_inventory.py`
- `test_gold_nullable_numeric_compatibility.py`

Need to verify if deprecated contracts are still needed.

**Context:**
- Current compatibility_test_files: 29 (after #5)
- Target after this issue: 27 (both removed)
- Gold contracts are critical data contracts

**Steps:**
1. Analyze deprecated gold contract registry
2. Check if any production code uses deprecated contracts
3. Check if nullable numeric compatibility is still needed
4. If unused:
   - Delete both test files
   - Remove deprecated contract definitions
   - Update configuration (total_files: 27, budget: 27)
5. If still needed:
   - Document why deprecated contracts must be retained
   - Plan migration path from deprecated to canonical
   - Update review date
6. Add governance note

**Acceptance Criteria:**
- [ ] Deprecated contract usage analyzed
- [ ] Unused contracts removed (if safe)
- [ ] Tests deleted for removed contracts
- [ ] Configuration updated (target: 27 or based on analysis)
- [ ] Migration path documented (if contracts retained)
- [ ] All tests pass

**Risk:** Medium - data contracts are critical

---

## Issue #7: Анализировать и очистить architecture shim guards

**Title:** Analyze and clean up architecture shim usage guards

**Priority:** P3 (High risk, requires deep analysis)

**Labels:** `test-governance`, `compatibility-debt`, `architecture`, `requires-deep-analysis`

**Description:**
25 architecture compatibility tests protect shim usage, deprecated imports, and freeze guards. Need to analyze each to determine if the protected legacy code still exists.

**Context:**
- Current compatibility_test_files: 27 (after #6)
- Target after this issue: 0-10 (realistic) or 0 (optimistic)
- Tests protect critical architectural boundaries
- Each test needs individual analysis

**Steps:**
1. For each architecture compatibility test:
   - Read the test to understand what it protects
   - Check if the protected legacy code still exists
   - If code deleted: delete the test
   - If code exists: evaluate if it's critical or can be removed
2. Group tests by protected surface:
   - Shim usage guards (lifecycle, transformer helpers, etc.)
   - Deprecated import guards
   - Freeze guards
   - Compatibility policy surface guards
3. For each group:
   - Determine if the protected surface is still needed
   - If not: delete tests and remove legacy code
   - If yes: document why and update review date
4. Update configuration incrementally
5. Add governance notes for each batch

**Architecture compatibility tests to analyze:**
```
tests/architecture/test_application_composite_compat_surface_usage.py
tests/architecture/test_application_core_lifecycle_shim_usage.py
tests/architecture/test_batch_transformer_helpers_shim_usage.py
tests/architecture/test_checkpoint_compatibility_runtime_facade_usage.py
tests/architecture/test_compatibility_facade_inventory.py
tests/architecture/test_compatibility_freeze_guards.py
tests/architecture/test_compatibility_freeze_guards_config_pipeline.py
tests/architecture/test_compatibility_freeze_guards_provider_datasource.py
tests/architecture/test_compatibility_importer_census_governance.py
tests/architecture/test_compatibility_telemetry_reporting.py
tests/architecture/test_composition_entrypoints_deprecated_imports.py
tests/architecture/test_config_compatibility_registry.py
tests/architecture/test_degraded_runtime_anchor_legacy_boundary.py
tests/architecture/test_docs_compat_shim_governance.py
tests/architecture/test_domain_normalization_compat_usage.py
tests/architecture/test_domain_service_normalization_compat_usage.py
tests/architecture/test_infrastructure_adapter_compat_shim_usage.py
tests/architecture/test_metadata_service_shim_usage.py
tests/architecture/test_pipeline_storage_compat_shim_usage.py
tests/architecture/test_project_legacy_compatibility_remediation_evidence_surface.py
tests/architecture/test_root_script_compatibility_surfaces.py
tests/architecture/test_run_execution_context_compat_shim_usage.py
tests/architecture/test_silver_filter_identity_surface.py
```

**Acceptance Criteria:**
- [ ] All 25 tests analyzed
- [ ] Tests for deleted legacy code removed
- [ ] Critical tests documented with rationale
- [ ] Configuration updated (target based on analysis)
- [ ] All architecture tests pass
- [ ] Governance notes added for each batch

**Risk:** High - requires deep architectural knowledge, may expose hidden dependencies

**Recommendation:** Split into sub-issues by protected surface group if this becomes too large.

---

## Summary

**Total Issues:** 7

**Expected Reduction:**
- Issue #1: 37 → 36 (-1)
- Issue #2: 36 → 35 (-1) or 36 (no change)
- Issue #3: 35 → 34 (-1) or 35 (no change)
- Issue #4: 34 → 32 (-2)
- Issue #5: 32 → 29 (-3)
- Issue #6: 29 → 27 (-2)
- Issue #7: 27 → 0-10 (-17 to -27)

**Final Target:** 0 compatibility_test_files (optimistic) or 5-10 (realistic)

**Execution Order:**
1. #1 (quick win)
2. #2 (analysis)
3. #3 (analysis)
4. #4 (migration)
5. #5 (analysis)
6. #6 (analysis)
7. #7 (deep analysis - split if needed)

**Total Estimated Effort:** 2-3 weeks (assuming 1-2 days per issue for #2-#6, 1 week for #7)
