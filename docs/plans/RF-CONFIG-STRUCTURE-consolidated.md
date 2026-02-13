# RF-CONFIG-STRUCTURE: Consolidated Refactoring Plan

**Version:** 2.0.0
**Date:** 2026-02-13
**Status:** PROPOSED
**Sources:**
- Branch `claude/study-bioetl-config-structure-dljZv` — code-level audit (8 steps, ~25 files)
- Branch `claude/refactor-config-structure-vyRIX` — YAML config structure plan (6 phases, ~126 files)
- Plus 4 earlier codex branches analyzed in the audit

---

## 1. Executive Summary

Two independent analysis efforts produced **complementary but non-overlapping** plans:

| Aspect | Branch `dljZv` (Code Audit) | Branch `vyRIX` (Config Structure) |
|--------|----------------------------|-----------------------------------|
| **Scope** | Python domain/application/infra code | YAML config files + config loaders |
| **Focus** | Type safety, DI, convenience properties | Naming unification, deduplication, directory structure |
| **Files** | ~25 `.py` files | ~126 `.yaml` files + ~10 `.py` loaders |
| **Risk** | HIGH (runtime breakage if caller migration incomplete) | MEDIUM (backward-compat via alias support) |
| **Overlap** | Infrastructure config loaders | Infrastructure config loaders |

This document merges both into a single execution plan with correct ordering,
dependency management, and a set of actionable prompts.

---

## 2. Current State Verified Against Codebase

Verified on `master` branch (commit `a68e177`):

### 2.1 Confirmed Issues

| ID | Description | Location | Verified |
|----|-------------|----------|----------|
| **TYPE-1** | `silver_filters: SilverFilterConfig \| GoldFilterConfig \| None` — union type leak | `domain/config/pipeline.py:49` | YES |
| **TYPE-2** | `SilverFilterConfig(GoldFilterConfig)` — inheritance breaks nominal typing | `domain/filtering/silver_config.py:17` | YES |
| **TYPE-3** | `TableConfig.silver_write_mode: SilverWriteMode \| str` — `\| str` vestige | `domain/config/table.py:31` | YES |
| **DUP-1** | `primary_keys` duplicated in ~50% pipeline configs (top-level, sink.silver.primary_key, sort_by) | `configs/pipelines/` | YES |
| **DUP-2** | Explicit `source_file`, `dq_config_file`, `data_schema_file` in explicit-style configs | `configs/pipelines/chembl/molecule.yaml` | YES |
| **DUP-3** | Explicit `sink.*.path` duplicating convention-computed paths | Same | YES |
| **NAME-1** | 4 different DQ field naming keys (`common_*`, `provider_*`, `entity_*`, `field_*`) | `infrastructure/config/dq_config_loader.py` | YES |
| **NAME-2** | `document` entity in source configs instead of `publication` | `configs/sources/chembl.yaml` | YES |
| **NAME-3** | `batch_size` duplicated at 2-3 levels in source configs | `configs/sources/*.yaml` | YES |
| **STRUCT-1** | Source configs have non-uniform field structure across providers | `configs/sources/` | YES |
| **STRUCT-2** | `data_schema/` contains 11+ stub files (18 lines, `column_groups: []`) | `configs/data_schema/chembl/` | YES |

### 2.2 Corrected Claims from Branch `dljZv`

| Claim | Actual |
|-------|--------|
| `write_mode` returns `object` | Returns `SilverWriteMode \| str` (already fixed) |
| `gold_write_mode` returns `object` | Returns `GoldWriteMode \| str` (already fixed) |

Step 2 from `dljZv` (fix write_mode return types) is **already done** on master.
The remaining issue is `| str` vestige in `TableConfig` field declarations.

---

## 3. Consolidated Plan — 6 Phases

### Dependency Graph

```
Phase 1: Code-Level Type Fixes (non-breaking)
    │
    ├──▶ Phase 2: Infrastructure Loader Enhancements (backward-compat)
    │       │
    │       └──▶ Phase 4: YAML Config Migration
    │               │
    │               └──▶ Phase 5: Directory Reorganization
    │                       │
    │                       └──▶ Phase 6: Cleanup & Finalization
    │
    └──▶ Phase 3: Caller Migration & Property Removal
```

Phases 1, 2 can be parallelized.
Phase 3 depends on Phase 1 (type fixes).
Phase 4 depends on Phase 2 (loader aliases).
Phase 5 depends on Phase 4.
Phase 6 depends on all.

---

### Phase 1: Code-Level Type Fixes

**Goal:** Fix type safety issues in domain layer without changing behavior.
**Risk:** LOW | **Tests must pass after each step.**

#### Step 1.1: Narrow `silver_filters` type
**Files:** 13
**Change:** `SilverFilterConfig | GoldFilterConfig | None` → `SilverFilterConfig | None`

Target files:
- `domain/config/pipeline.py` — field declaration (line 49)
- `application/core/base_transformer.py` — constructor signature
- `application/pipelines/*/transformer.py` — 10 transformer files
- `composition/factories/pipeline_factory.py`
- `composition/factories/transformer_factory.py`

**Verification:** `mypy --strict src/bioetl/`

#### Step 1.2: Separate SilverFilterConfig via BaseFilterConfig
**Files:** 4 new/modified
**Change:** Break inheritance `SilverFilterConfig(GoldFilterConfig)` → both inherit `BaseFilterConfig`

```
domain/filtering/
├── _base_filter_config.py   # NEW — shared logic (moved from gold_config.py)
├── gold_config.py           # MODIFIED — GoldFilterConfig(BaseFilterConfig)
├── silver_config.py         # MODIFIED — SilverFilterConfig(BaseFilterConfig)
└── __init__.py              # MODIFIED — re-export BaseFilterConfig
```

**Key design decision:** Shared base class, NOT code duplication.
- `BaseFilterConfig` contains `should_include()`, all check methods, `_OPERATOR_CHECKERS`
- `GoldFilterConfig` and `SilverFilterConfig` are empty subclasses for nominal typing
- `isinstance(silver, GoldFilterConfig)` becomes `False`
- `from_gold_filter_config` → `from_base(other: BaseFilterConfig) -> Self`

Infrastructure updates:
- `infrastructure/schemas/filter_config.py` — add `to_silver_domain() -> SilverFilterConfig`
- `infrastructure/config/filter_config_loader.py` — update return type
- `infrastructure/config/_base.py` — update factory call

**Verification:** `mypy --strict` + filter unit tests

#### Step 1.3: Narrow TableConfig write mode types (optional)
**Files:** 2-3
**Change:** `SilverWriteMode | str` → `SilverWriteMode` in `TableConfig`

Only if all string→enum conversion is confirmed in infrastructure boundary.
Move conversion to `infrastructure/config/_base.py` in `yaml_config_to_domain()`.

**Verification:** All config loading integration tests

---

### Phase 2: Infrastructure Loader Enhancements

**Goal:** Add backward-compatible alias support in config loaders
so that new YAML field names work alongside old ones.
**Risk:** MEDIUM | **Zero breaking changes — old configs continue to work.**

#### Step 2.1: DQ Config Loader — unified field names
**File:** `infrastructure/config/dq_config_loader.py`
**Change:** Accept both old keys (`common_field_validations`, `provider_field_validations`,
`entity_field_validations`) and new unified key (`field_validations`) at all hierarchy levels.

```python
# Normalization in loader:
# If file is at defaults level and has "field_validations" → treat as "common_field_validations"
# If file is at provider level and has "field_validations" → treat as "provider_field_validations"
# If file is at entity level and has "field_validations" → treat as "entity_field_validations"
# Old keys still work for backward compatibility.
```

Same for `cross_field_validations` and `conditional_validations`.

#### Step 2.2: DQ Config Loader — `dq_overrides` alias
**File:** `infrastructure/config/pipeline_config_loader.py`
**Change:** Accept `dq_overrides` as alias for `dq_rules` in pipeline configs.

#### Step 2.3: Source Config — normalized structure support
**File:** `composition/providers/_config_helpers.py`
**Change:** Support both old nested structure and new flat structure.

Old: `source.provider_config.base_url`
New: `api.base_url`

Use Pydantic `model_validator` or manual normalization to accept both.

#### Step 2.4: Filter Config Loader — path alias
**File:** `infrastructure/config/filter_config_loader.py`
**Change:** Accept `configs/filters/` path alongside `configs/filter/`.

#### Step 2.5: Data Schema Loader — path alias
Accept `configs/schemas/` alongside `configs/data_schema/`.

**Verification:** Existing tests pass unchanged (old format still works).

---

### Phase 3: Caller Migration & Property Removal

**Goal:** Migrate all callers from convenience properties to `config.table.*`
and remove the properties.
**Risk:** HIGH | **Must verify ALL callers before removal.**

#### Step 3.1: Add `effective_silver_table` / `effective_gold_table`
**File:** `domain/config/pipeline.py`
**Change:** Add two centralized fallback properties:

```python
@property
def effective_silver_table(self) -> str:
    return self.table.silver_table or f"{self.provider}.{self.entity_type}"

@property
def effective_gold_table(self) -> str:
    return self.table.gold_table or f"{self.provider}.{self.entity_type}"
```

#### Step 3.2: Migrate ALL callers
**Complete inventory (verified by grep):**

| File | Old Usage | New Usage |
|------|-----------|-----------|
| `application/services/medallion_lifecycle.py` | `config.silver_table`, `config.gold_table` | `config.effective_silver_table`, `config.effective_gold_table` |
| `application/core/preflight_service.py` | `config.write_mode`, `config.gold_write_mode` | `config.table.silver_write_mode`, `config.table.gold_write_mode` |
| `composition/factories/services_factory.py` | All 7 properties | `config.table.*` / `config.effective_*` |
| `composition/_resource_management.py` | `config.silver_table`, `config.gold_table` | `config.effective_silver_table`, `config.effective_gold_table` |
| `composition/bootstrap/cli/storage.py` | `config.silver_table`, `config.gold_table` | `config.effective_silver_table`, `config.effective_gold_table` |
| `application/composite/dependency_coordinator.py` | `source_config.silver_table` (8x) | `source_config.effective_silver_table` |

**Verification:** `grep -rn 'config\.\(silver_table\|gold_table\|write_mode\|gold_write_mode\|primary_keys\|partition_cols\|on_schema_mismatch\)' src/bioetl/ --include="*.py"` returns 0 results (besides the properties themselves and tests).

#### Step 3.3: Remove convenience properties
**File:** `domain/config/pipeline.py`
**Remove:** `primary_keys`, `silver_table`, `gold_table`, `write_mode`,
`gold_write_mode`, `partition_cols`, `on_schema_mismatch` properties.

**Keep:** `effective_silver_table`, `effective_gold_table`, `lock_key`.

#### Step 3.4: Update tests
Update all test files that reference removed properties.

---

### Phase 4: YAML Config Migration

**Goal:** Simplify YAML configs: remove duplication, unify naming, convention-based minimal style.
**Risk:** MEDIUM | **Loaders from Phase 2 ensure backward compat during migration.**

#### Step 4.1: Fix entity names in source configs
**Files:** `configs/sources/chembl.yaml` (and others with `document`)
**Change:** `document` → `publication`, `document_similarity` → `publication_similarity`, etc.

#### Step 4.2: Simplify pipeline configs — remove duplicated fields
**Files:** ~30 pipeline YAML files
**Remove from each:**
- `source_file` (convention-computed)
- `dq_config_file` (convention-computed)
- `data_schema_file` (convention-computed)
- `sink.*.path` (convention-computed)
- `sink.silver.primary_key` (auto-propagated from `primary_keys`)
- `sink.*.sort_by.columns` (auto-propagated)
- `sink.*.csv_export.path` (auto-computed from sink path)

**Rename:** `dq_rules` → `dq_overrides`

#### Step 4.3: Unify DQ field naming
**Files:** ~39 DQ YAML files
**Change in all files:** Use `field_validations` everywhere instead of
`common_field_validations` / `provider_field_validations` / `entity_field_validations`.
Same for `cross_field_validations` and `conditional_validations`.

#### Step 4.4: Normalize source configs
**Files:** 7 source YAML files
**Change:** Restructure to uniform schema:

```yaml
version: "1.0.0"
api:
  base_url: ...
  auth_type: public | email | api_key
client:
  timeout_sec: 60.0
  max_retries: 3
batch:
  api_batch_size: 10
  page_size: 100
rate_limit:
  default:
    requests_per_second: 3
    burst: 10
  authenticated: ...  # optional
health_check:
  endpoint: ...
  timeout_sec: 5
entities:
  - activity
  - publication  # canonical names
```

#### Step 4.5: Slim down `_base.yaml`
**File:** `configs/pipelines/_base.yaml` (491 → ~150 lines)
**Change:** Move documentation to `docs/03-guides/CONFIG-GUIDE.md`, keep only defaults + brief comments.

#### Step 4.6: Clean up `data_schema/` stubs
**Remove:** All 18-line stub files with `column_groups: []`
Config loaders should handle missing file gracefully (empty config).

**Verification:** Full pipeline test suite, `bioetl config validate` (if exists).

---

### Phase 5: Directory Reorganization

**Goal:** Consistent naming and logical grouping.
**Risk:** MEDIUM | **Loaders with path aliases from Phase 2 ensure no breakage.**

| Old Path | New Path | Rationale |
|----------|----------|-----------|
| `configs/dq/` | `configs/quality/` | Clearer name |
| `configs/filter/` | `configs/filters/` | Plural consistency |
| `configs/data_schema/` | `configs/schemas/` | Shorter, standard |
| `configs/composite/field_groups/` | `configs/schemas/composite/field_groups/` | Collocate with schemas |
| `configs/pipelines/_schema.json` | `configs/_schema/pipeline.json` | Separate from YAML |
| `configs/pipelines/_composite_schema.json` | `configs/_schema/composite.json` | Same |

**Execution:**
1. Create new directories
2. Copy files (not move — old paths still work via aliases)
3. Run full test suite
4. Remove old directories

**Verification:** All integration tests + `find configs/ -name '*.yaml' | wc -l` unchanged.

---

### Phase 6: Cleanup & Finalization

#### Step 6.1: Remove backward-compat aliases from loaders
Remove old key aliases, old path fallbacks.

#### Step 6.2: Update documentation
- ADR-027 (DQ externalization) — new paths
- ADR-028 (Filter externalization) — new paths
- ADR-029 (Convention-based paths) — new directory names
- RULES.md — config references

#### Step 6.3: Clean up `validation.py`
**File:** `domain/config/validation.py`
**Remove:** Section divider comments (`# ============`), redundant module docstring verbosity.
**Preserve:** Attribute docstrings (publication year ranges, molecular weight ranges), validation type explanations, condition variant comments.

#### Step 6.4: Architecture tests
New tests:
- `SilverFilterConfig` is NOT a subclass of `GoldFilterConfig`
- `isinstance(SilverFilterConfig(...), GoldFilterConfig)` is `False`
- Import boundary: no direct `_base_filter_config` imports from outside `domain/filtering/`
- Config loading: old format → new format produces identical domain objects
- `effective_silver_table` / `effective_gold_table` fallback logic

#### Step 6.5: Optional — `bioetl config show <pipeline>`
CLI command showing resolved config after all merges — useful for debugging.

---

## 4. Risk Matrix

| Phase | Risk | Impact if Wrong | Mitigation |
|-------|------|-----------------|------------|
| 1 (Type Fixes) | LOW | mypy errors only | `mypy --strict` after each step |
| 2 (Loader Aliases) | MEDIUM | Config loading regression | Integration tests, dual-format support |
| 3 (Caller Migration) | **HIGH** | Runtime `AttributeError` | Exhaustive grep, staged removal |
| 4 (YAML Migration) | MEDIUM | Incorrect resolved configs | Migration tests, Phase 2 aliases as safety net |
| 5 (Directory Reorg) | MEDIUM | File-not-found errors | Path aliases as safety net |
| 6 (Cleanup) | LOW | Documentation drift | Review checklist |

---

## 5. Metrics

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Total YAML LOC in `configs/` | ~4,500 | ~3,000 | -30% |
| Max pipeline config LOC | 117 (molecule) | ~40 | -60% |
| Duplicated primary_keys | ~50 pairs | 0 | 0 |
| DQ validation key variants | 4 | 1 | 1 |
| Pipeline config styles | 3 | 1 (convention-based) | 1 |
| `isinstance(silver, GoldFilter)` | `True` (wrong) | `False` (correct) | Fixed |
| Convenience properties on PipelineConfig | 7 | 2 (`effective_*`) | Minimal |

---

## 6. Files Changed Summary

| Phase | New Files | Modified Files | Deleted Files |
|-------|-----------|----------------|---------------|
| 1 | 1 (`_base_filter_config.py`) | ~18 | 0 |
| 2 | 0 | ~6 loaders | 0 |
| 3 | 0 | ~8 callers + pipeline.py | 0 |
| 4 | 1 (`CONFIG-GUIDE.md`) | ~100 YAML + 0 .py | ~11 stubs |
| 5 | 0 | ~6 loaders (path updates) | old dirs |
| 6 | 3-5 test files | ~5 docs | alias code |
| **Total** | **~6** | **~130** | **~15** |
