# RF-CONFIG-STRUCTURE: Consolidated Refactoring Plan

**Version:** 1.0.0
**Date:** 2026-02-13
**Status:** PROPOSED
**Based on analysis of branches:**
- `codex/refactor-bioetl-configuration-structure-3znbpy`
- `codex/refactor-bioetl-configuration-structure-3i5df9`
- `codex/refactor-bioetl-configuration-structure`
- `codex/refactor-bioetl-configuration-structure-jl7hsb`

---

## 1. Summary of Branch Approaches

### Branch `3znbpy` — "narrow silver filter typing"
**Scope:** Minimal. Changes only the `silver_filters` type annotation from
`SilverFilterConfig | GoldFilterConfig | None` to `SilverFilterConfig | None`
across 13 files.

**Verdict:** Correct but insufficient. Fixes only one symptom of the type leak.

---

### Branch `3i5df9` — "refactor config typing and streamline validation"
**Scope:** `silver_filters` type narrowing + `write_mode`/`gold_write_mode`
return type fix via `cast()` + aggressive validation.py docstring removal.

**Verdict:** Partially correct, but introduces workarounds instead of proper fixes.

---

### Branch `codex/refactor-bioetl-configuration-structure` — "split silver filter"
**Scope:** `silver_filters` type narrowing + breaks inheritance between
`SilverFilterConfig` and `GoldFilterConfig` (makes Silver standalone) +
validation.py docstring removal + infrastructure type updates.

**Verdict:** Right direction for filter separation, but the execution has critical
issues (full code duplication, copy-paste errors in docs).

---

### Branch `jl7hsb` — "table composition"
**Scope:** `silver_filters` type narrowing + removes ALL convenience properties
from PipelineConfig + partially updates callers to `config.table.*` form.

**Verdict:** Right intention, but **breaks production code** — not all callers
are updated, leading to `AttributeError` at runtime.

---

## 2. Identified Errors and Inaccuracies

### 2.1 CRITICAL Errors

#### ERR-001: Incomplete Caller Migration (branch `jl7hsb`)
**Severity:** CRITICAL — runtime breakage

Branch `jl7hsb` removes all convenience properties from `PipelineConfig`
(`primary_keys`, `silver_table`, `gold_table`, `write_mode`, `gold_write_mode`,
`partition_cols`, `on_schema_mismatch`) but **fails to update** the following
callers that still use them:

| File | Line(s) | Property Used |
|------|---------|---------------|
| `composition/_resource_management.py` | 154-155 | `config.silver_table`, `config.gold_table` |
| `composition/bootstrap/cli/storage.py` | 160-163 | `config.silver_table`, `config.gold_table` |
| `application/composite/dependency_coordinator.py` | 208-302 | `source_config.silver_table` (8 occurrences) |

Removing the properties without updating these files will cause
`AttributeError` at runtime in production CLI commands and composite pipeline
dependency resolution.

#### ERR-002: Full Code Duplication of Filter Logic (branch `codex/...main`)
**Severity:** HIGH — maintenance, DRY violation

The main codex branch replaces `SilverFilterConfig(GoldFilterConfig)` inheritance
with a fully standalone class that **copy-pastes ~230 lines** including:
- `should_include()` and all 6 check methods
- All 6 operator checker methods (`_check_op_in`, `_check_op_not_in`, etc.)
- All range/list/contains validation helpers
- A separate `_OPERATOR_CHECKERS` dispatch table

This creates two identical implementations that must be maintained in sync.
Any bug fix or feature addition to filtering must be applied in two places.

### 2.2 HIGH Errors

#### ERR-003: Copy-Paste Docstring Errors (branch `codex/...main`)
**Severity:** HIGH — misleading documentation

1. `silver_config.py` class docstring says `"Полная конфигурация Gold фильтров"`
   (should be "Silver фильтров")
2. `SilverFiltersFileConfig.to_silver_domain()` docstring says
   `"Returns: GoldFilterConfig"` (should be "SilverFilterConfig")

#### ERR-004: `cast()` Workaround Instead of Proper Type Fix (branch `3i5df9`)
**Severity:** MEDIUM — tech debt

The `write_mode` property returns `self.table.silver_write_mode`. In `TableConfig`,
the field is declared as `SilverWriteMode | str` but `__post_init__` always
converts it to `SilverWriteMode` via `convert_write_mode()`. Using `cast()` at
the property level masks the underlying type declaration issue rather than
fixing it. The proper fix is either:
- Narrow the field type in `TableConfig` to just `SilverWriteMode` (after
  ensuring `__post_init__` always converts), or
- Use `@property` in `TableConfig` to expose typed read-only access

#### ERR-005: Fallback Logic Duplication (branch `jl7hsb`)
**Severity:** MEDIUM — code smell

After removing convenience properties, the fallback pattern
`config.table.silver_table or f"{config.provider}.{config.entity_type}"`
is scattered across 4+ locations in `medallion_lifecycle.py` and
`services_factory.py`. This should be centralized.

### 2.3 MEDIUM Errors

#### ERR-006: Over-Aggressive Docstring Removal (branches `3i5df9`, `codex/...main`)
**Severity:** MEDIUM — information loss

Both branches strip ALL docstrings from `validation.py` including useful
attribute descriptions (`min_publication_year: Minimum valid publication year.
Default 1500 covers historical scientific publications`) and validation type
explanations (`required: Field must be present and non-null`, etc.). The inline
comments on `CrossFieldValidation.condition` Literal values
(`"all_present",  # All fields must be non-null`) are also removed.

These comments serve as inline API documentation. Removing them without
providing alternative documentation (e.g., in a docs file) degrades
developer experience. Section-divider comments (`# ====`, `# Range validation`,
etc.) can reasonably be removed, but attribute-level documentation should
be preserved.

#### ERR-007: No Test Updates (all branches)
**Severity:** MEDIUM — incomplete

None of the branches include test updates for:
- Architecture tests validating the new import relationships
- Unit tests for the new standalone `SilverFilterConfig` (codex main)
- Integration tests verifying `config.table.*` access patterns work end-to-end

#### ERR-008: Convenience Property `write_mode` Returns `object` (not fixed by `3znbpy`, `codex/...main`, `jl7hsb`)
**Severity:** MEDIUM — type safety

On main, `PipelineConfig.write_mode` and `gold_write_mode` both return `object`
instead of their actual enum types (`SilverWriteMode`, `GoldWriteMode`).
Branches `3znbpy`, `codex/...main`, and `jl7hsb` do not address this.
Only `3i5df9` attempts a fix (via `cast()`).

---

## 3. Corrected Consolidated Refactoring Plan

### 3.0 Principles

1. **Incremental steps** — each step must leave the codebase in a working state
2. **No code duplication** — use composition/mixin instead of copy-paste
3. **Complete caller migration** — verify ALL callers before removing properties
4. **Preserve useful documentation** — remove only structural noise, keep semantics

### 3.1 Step 1: Narrow `silver_filters` Type (from `3znbpy`)
**Risk:** LOW | **Files:** 13

Change `silver_filters: SilverFilterConfig | GoldFilterConfig | None` to
`silver_filters: SilverFilterConfig | None` everywhere.

**Files to modify:**
- `domain/config/pipeline.py` — field declaration
- `application/core/base_transformer.py` — constructor signature
- `application/pipelines/*/transformer.py` — 10 transformer files
- `composition/factories/pipeline_factory.py`
- `composition/factories/transformer_factory.py`

**Verification:** `mypy --strict src/bioetl/` must pass.

This is correct and identical across all four branches.

### 3.2 Step 2: Fix `write_mode` / `gold_write_mode` Return Types
**Risk:** LOW | **Files:** 1

In `domain/config/pipeline.py`, change convenience property return types:

```python
# BEFORE
@property
def write_mode(self) -> object:
    return self.table.silver_write_mode

@property
def gold_write_mode(self) -> object:
    return self.table.gold_write_mode

# AFTER
@property
def write_mode(self) -> SilverWriteMode | str:
    return self.table.silver_write_mode

@property
def gold_write_mode(self) -> GoldWriteMode | str:
    return self.table.gold_write_mode
```

**Why `SilverWriteMode | str` and not just `SilverWriteMode`:**
The `TableConfig` field is declared as `SilverWriteMode | str`. Even though
`__post_init__` converts it, mypy sees the declared type. The convenience
property must match the declared type of the field it forwards. Using
`cast()` (as in `3i5df9`) is a workaround that silences mypy but doesn't
fix the underlying issue.

**Alternative (preferred, but larger scope):** Change `TableConfig` field
declarations to use `SilverWriteMode` (without `| str`) and handle string
conversion exclusively in the infrastructure → domain boundary
(`yaml_config_to_domain`). This is cleaner but requires verifying no caller
passes strings directly. This can be done in Step 5 below.

**Requires import:** Add `SilverWriteMode`, `GoldWriteMode` imports to
`pipeline.py` (or use `TYPE_CHECKING` if only for annotations).

### 3.3 Step 3: Separate SilverFilterConfig from GoldFilterConfig Without Duplication
**Risk:** MEDIUM | **Files:** 3-4

The goal from branch `codex/...main` is correct: Silver and Gold filter
configs should be structurally independent for nominal typing. But the
implementation (full copy-paste) is wrong.

**Correct approach — shared base with nominal types:**

```python
# domain/filtering/_base_filter_config.py (NEW — private module)
@dataclass(frozen=True, slots=True)
class BaseFilterConfig:
    """Shared filter configuration logic for Silver and Gold layers."""
    column_filters: tuple[GoldColumnFilter, ...] = ()
    range_filters: tuple[GoldRangeFilter, ...] = ()
    list_length_filters: tuple[GoldListLengthFilter, ...] = ()
    list_contains_filters: tuple[GoldListContainsFilter, ...] = ()
    required_fields: tuple[str, ...] = ()
    exclude_if_present: tuple[str, ...] = ()

    def should_include(self, record: dict[str, Any]) -> bool: ...
    # ... all shared methods ...
    def is_empty(self) -> bool: ...


# domain/filtering/gold_config.py
@dataclass(frozen=True, slots=True)
class GoldFilterConfig(BaseFilterConfig):
    """Gold layer filter configuration (nominal type)."""


# domain/filtering/silver_config.py
@dataclass(frozen=True, slots=True)
class SilverFilterConfig(BaseFilterConfig):
    """Silver layer filter configuration (nominal type)."""
```

This achieves:
- Nominal type separation (mypy catches Silver↔Gold mix-ups)
- `isinstance(silver_cfg, GoldFilterConfig)` is `False` (no inheritance)
- Zero code duplication
- Single `_OPERATOR_CHECKERS` dispatch table (in base module)

**Note on `from_gold_filter_config`:** The factory method can be removed.
Construction should use explicit field mapping (as in the codex main branch's
`_base.py` changes). Or better, a shared factory on `BaseFilterConfig`:

```python
@classmethod
def from_base(cls, other: BaseFilterConfig) -> Self:
    return cls(
        column_filters=other.column_filters,
        range_filters=other.range_filters,
        list_length_filters=other.list_length_filters,
        list_contains_filters=other.list_contains_filters,
        required_fields=other.required_fields,
        exclude_if_present=other.exclude_if_present,
    )
```

**Infrastructure updates** (from codex main, corrected):
- `infrastructure/schemas/filter_config.py`:
  - Add `to_silver_domain() -> SilverFilterConfig` to `SilverFiltersFileConfig`
  - Fix docstring: "Returns: SilverFilterConfig" (not GoldFilterConfig)
  - Update `FilterConfigFile.to_domain()` return type to include `SilverFilterConfig`
- `infrastructure/config/filter_config_loader.py`:
  - Update return type signature
- `infrastructure/config/_base.py`:
  - Replace `SilverFilterConfig.from_gold_filter_config(gold)` with
    `SilverFilterConfig.from_base(gold)` or inline field mapping

### 3.4 Step 4: Migrate Callers to `config.table.*` (from `jl7hsb`, corrected)
**Risk:** HIGH | **Files:** ~8

**CRITICAL:** Must update ALL callers BEFORE removing convenience properties.
Branch `jl7hsb` missed several.

**Complete caller inventory** (from grep analysis):

| Caller File | Usage | Migration |
|-------------|-------|-----------|
| `application/services/medallion_lifecycle.py` | `config.silver_table`, `config.gold_table` | `config.table.silver_table`, `config.table.gold_table` |
| `application/core/preflight_service.py` | `config.write_mode`, `config.gold_write_mode` | `config.table.silver_write_mode`, `config.table.gold_write_mode` |
| `composition/factories/services_factory.py` | `config.primary_keys`, `config.silver_table`, `config.gold_table`, `config.write_mode`, `config.gold_write_mode`, `config.on_schema_mismatch` | All → `config.table.*` |
| `composition/_resource_management.py` | `config.silver_table`, `config.gold_table` | `config.table.silver_table`, `config.table.gold_table` |
| `composition/bootstrap/cli/storage.py` | `config.silver_table`, `config.gold_table` | `config.table.silver_table`, `config.table.gold_table` |
| `application/composite/dependency_coordinator.py` | `source_config.silver_table` (8 occurrences) | `source_config.table.silver_table` |

**Table name fallback centralization:**
Instead of scattering `config.table.silver_table or f"{config.provider}.{config.entity_type}"`
in every caller, add a helper method to `PipelineConfig`:

```python
@property
def effective_silver_table(self) -> str:
    """Silver table name with provider.entity fallback."""
    return self.table.silver_table or f"{self.provider}.{self.entity_type}"

@property
def effective_gold_table(self) -> str:
    """Gold table name with provider.entity fallback."""
    return self.table.gold_table or f"{self.provider}.{self.entity_type}"
```

This replaces the scattered fallback logic and provides a single point
of truth for the default table naming convention.

### 3.5 Step 5: Remove Convenience Properties
**Risk:** MEDIUM | **Files:** 1

After ALL callers are migrated (Step 4), remove from `PipelineConfig`:
- `primary_keys` property
- `silver_table` property
- `gold_table` property
- `write_mode` property
- `gold_write_mode` property
- `partition_cols` property
- `on_schema_mismatch` property

Update the class docstring to reflect that `config.table.*` is the canonical
access path.

**Keep:** `effective_silver_table` and `effective_gold_table` from Step 4.

### 3.6 Step 6: Clean Up `validation.py` (from `3i5df9`/`codex main`, corrected)
**Risk:** LOW | **Files:** 1

**Remove:**
- Section divider comments (`# ============`, `# Range validation`, etc.)
- Module-level docstring verbosity (keep one-liner)
- Redundant `_validate_ranges()` extraction — inline into `__post_init__`

**Preserve:**
- Attribute docstrings in `ValidationConfig` (publication year ranges,
  molecular weight ranges — these are domain-specific knowledge)
- `FieldValidation` validation_type explanations (what "required", "not_null",
  "range" etc. mean)
- `CrossFieldValidation.condition` inline comments explaining each variant
- `ConditionalValidation` attribute descriptions

### 3.7 Step 7: Narrow `TableConfig` Write Mode Types (optional, from Step 2 follow-up)
**Risk:** MEDIUM | **Files:** 3-5

If infrastructure boundary guarantees string→enum conversion:

```python
# domain/config/table.py — AFTER
class TableConfig:
    silver_write_mode: SilverWriteMode = SilverWriteMode.MERGE
    gold_write_mode: GoldWriteMode = GoldWriteMode.APPEND
```

Remove `| str` from declarations. Move string conversion entirely to
`infrastructure/config/_base.py` in `yaml_config_to_domain()`.

This eliminates the need for `cast()` and makes the domain model purely typed.

### 3.8 Step 8: Tests
**Risk:** LOW | **Files:** 3-5 new test files

- **Architecture tests:** Verify `SilverFilterConfig` is NOT a subclass of
  `GoldFilterConfig` (and vice versa)
- **Unit tests:** `SilverFilterConfig.should_include()` works identically to
  `GoldFilterConfig.should_include()` (parameterized test on `BaseFilterConfig`)
- **Integration tests:** Verify `PipelineConfig.effective_silver_table` fallback
- **Regression tests:** Ensure `config.table.silver_write_mode` is always an
  enum after construction (not a string)

---

## 4. Execution Order

```
Step 1 (silver_filters type)
    │
    v
Step 2 (write_mode return types)
    │
    v
Step 3 (SilverFilterConfig separation via base class)
    │
    v
Step 4 (migrate ALL callers to config.table.*)
    │
    v
Step 5 (remove convenience properties)
    │
    v
Step 6 (validation.py cleanup)
    │
    v
Step 7 (narrow TableConfig types — optional)
    │
    v
Step 8 (tests)
```

Steps 1, 2, 6 are independent and can be parallelized.
Steps 3-5 are sequential and must be done in order.
Step 7 is optional and independent of 6.
Step 8 should be done incrementally after each step.

---

## 5. Risk Matrix

| Step | Risk | Impact if Wrong | Mitigation |
|------|------|-----------------|------------|
| 1 | LOW | mypy errors | Run `mypy --strict` |
| 2 | LOW | Type annotation mismatch | Run `mypy --strict` |
| 3 | MEDIUM | Filter behavior regression | Run filter unit tests |
| 4 | **HIGH** | Runtime AttributeError | `grep` ALL uses before removing |
| 5 | MEDIUM | Runtime AttributeError | Only after Step 4 is verified |
| 6 | LOW | None (cosmetic) | Code review |
| 7 | MEDIUM | Construction failures | Test all config loading paths |
| 8 | LOW | None | Standard testing |

---

## 6. Files Changed Summary

| Step | New Files | Modified Files |
|------|-----------|----------------|
| 1 | 0 | 13 |
| 2 | 0 | 1 |
| 3 | 1 (`_base_filter_config.py`) | 5 (`silver_config.py`, `gold_config.py`, `_base.py`, `filter_config.py`, `filter_config_loader.py`) |
| 4 | 0 | 7 (`medallion_lifecycle.py`, `preflight_service.py`, `services_factory.py`, `_resource_management.py`, `storage.py`, `dependency_coordinator.py`, `pipeline.py`) |
| 5 | 0 | 1 (`pipeline.py`) |
| 6 | 0 | 1 (`validation.py`) |
| 7 | 0 | 2-3 (`table.py`, `_base.py`, possibly others) |
| 8 | 3-5 | 0 |
| **Total** | **4-6** | **~25 unique files** |
