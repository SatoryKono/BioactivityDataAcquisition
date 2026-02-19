# Audit Report: `codex/review-refactoring-results-and-prepare-changes`

**Date:** 2026-02-13
**Commit:** `f7877eb` — `refactor(chembl): unify dto taxonomy and molecule field naming`
**Files changed:** 19 (90 insertions, 86 deletions)
**Auditor:** claude/audit-refactoring-changes-RNoTN

---

## Summary

The branch performs three categories of field renames across domain entities, schemas, and infrastructure:

1. **Taxonomy ID disambiguation:** `taxonomy-id` → `target-taxonomy-id` (activity context) / `assay-taxonomy-id` (assay context)
2. **Molecule property cleanup:** Remove `property-` prefix from 5 molecule fields (e.g. `property-qed-weighted` → `qed-score`)
3. **JSON suffix removal:** Remove `-json` suffix from 13 DTO fields (e.g. `activity-properties-json` → `activity-properties`)
4. **Target enrichment:** New `description` field added to Target entity/schema/gold
5. **TargetRecord cleanup:** Removed unused fields `dap-id`, `target-constraints`, `component-tax-ids`

---

## Architecture Compliance (ARCH)

| Rule | Severity | Status | Notes |
|------|----------|--------|-------|
| ARCH-001 Import Matrix | CRITICAL | **PASS** | No cross-layer violations |
| ARCH-002 Domain Purity | CRITICAL | **PASS** | No I/O in domain layer |
| ARCH-008 Port Facade | MEDIUM | **PASS** | No internal port imports |

**Score: 10/10**

---

## Anti-Patterns (AP)

| Rule | Severity | Status | Notes |
|------|----------|--------|-------|
| AP-001 DI Violation | CRITICAL | **PASS** | No hard-coded constructors |
| AP-002 structlog | HIGH | **PASS** | No direct structlog in app/interfaces |
| AP-003 Import Boundary | CRITICAL | **PASS** | See ARCH-001 |
| AP-004 Sentinel Values | MEDIUM | **PASS** | Uses `None` properly |
| AP-005 Secrets | CRITICAL | **PASS** | No hardcoded credentials |
| AP-006 Print | MEDIUM | **PASS** | No print statements |

**Score: 10/10**

---

## DI Violations (DI)

No DI violations found. All changed files use constructor injection properly.

**Score: 10/10**

---

## Naming Conventions (NAME)

| Rule | Severity | Status | Notes |
|------|----------|--------|-------|
| NAME-001 Class Suffixes | MUST | **PASS** | Transformer, Schema, Record suffixes correct |
| NAME-002 Function Prefixes | SHOULD | **PASS** | `validate-*` prefix used correctly |
| NAME-003 Module Naming | MUST | **PASS** | |
| NAME-004 Private Attributes | SHOULD | **PASS** | |

**Score: 10/10**

---

## Type Annotations (TYPE)

| Rule | Severity | Status | Notes |
|------|----------|--------|-------|
| TYPE-001 Public Annotations | MUST | **PASS** | All public methods annotated |
| TYPE-002 Any Usage | SHOULD | **PASS** | No unjustified `Any` |

**Score: 10/10**

---

## Issues Found

### BUG-1: Test field ordering mismatch (WILL CAUSE TEST FAILURE)

**Severity:** CRITICAL
**File:** `tests/unit/infrastructure/schemas/test-silver-pipeline-contracts.py:345`

The silver schema (`silver.py`) places `description` in **alphabetical order** (after `cross-references`, before `downgraded`):

```python
# silver.py (CORRECT — alphabetical)
pa.field("cross-references", pa.string()),
pa.field("description", pa.string()),      # ← alphabetical
pa.field("downgraded", pa.bool-()),
```

But the test expectations place `description` **after** `species-group-flag`:

```python
# test-silver-pipeline-contracts.py (WRONG — not alphabetical)
("species-group-flag", pa.bool-()),
("description", pa.string()),              # ← out of order
("target-id", pa.string()),
```

The test asserts `schema.names == expected-names` (line 886), which checks exact field order. This **will fail** at runtime.

**Fix:** Move `("description", pa.string())` to between `("cross-references", pa.string())` and `("downgraded", pa.bool-())` in the test expectations.

---

### BUG-2: Architecture test has stale `-json` aliases (WILL CAUSE TEST FAILURE)

**Severity:** HIGH
**File:** `tests/test-architecture.py:308-314`

The architecture test maps schema fields to entity fields using an `aliases` dict. Six entries still reference old `-json`-suffixed entity field names that no longer exist:

```python
aliases = {
    "atc-classifications": "atc-classifications-json",       # line 308 — STALE
    "cross-references": "cross-references-json",             # line 309 — STALE
    "molecule-hierarchy": "molecule-hierarchy-json",          # line 311 — STALE
    "molecule-properties": "molecule-properties-json",        # line 312 — STALE
    "molecule-structures": "molecule-structures-json",        # line 313 — STALE
    "molecule-synonyms": "molecule-synonyms-json",            # line 314 — STALE
}
```

The entity `Molecule` (`chembl-structures.py`) no longer has these `-json` fields — they were renamed to match the schema names exactly.

**Fix:** Remove these 6 entries from the `aliases` dict (schema name now equals entity name, no alias needed).

---

### BUG-3: Integration test references old field name

**Severity:** MEDIUM
**File:** `tests/integration/composite/test-molecule-pipeline.py:350`

```python
chembl-only-fields = [
    ...
    "property-qed-weighted",    # ← should be "qed-score"
    ...
]
```

The field was renamed to `qed-score` in the domain entity, silver schema, and gold schema. The test uses the old name.

**Fix:** Change `"property-qed-weighted"` to `"qed-score"`.

---

### BUG-4: Type inconsistency between Bioactivity entity and converter/silver schema

**Severity:** MEDIUM
**File:** `src/bioetl/domain/entities/bioactivity.py:96`

The `Bioactivity` entity declares:
```python
target-taxonomy-id: str | None = None   # str type
```

But:
- The activity transformer now uses `validate-taxonomy-id` which returns `int | None`
- The silver schema changed from `pa.string()` to `pa.float64()` for `target-taxonomy-id`
- The activity domain schema uses `Series[float]`
- The gold schema uses `Series[float]`

The entity type annotation is `str | None` but the entire pipeline now works with numeric types. The `Bioactivity.from-raw()` method wraps the value in `-safe-str()`, which converts `int` back to `str`, masking the inconsistency. The test confirms the transformer outputs `int`:

```python
assert result["target-taxonomy-id"] == 9606  # int, not "9606"
```

**Fix:** Change `target-taxonomy-id: str | None = None` to `target-taxonomy-id: int | None = None` in the `Bioactivity` entity to match the converter, silver schema, and gold schema types.

---

### WARN-1: Dead code — `validate-taxonomy-id-str`

**Severity:** LOW
**File:** `src/bioetl/domain/value-objects/taxonomy-id.py:163-186`

The function `validate-taxonomy-id-str` is still defined and exported from `domain/value-objects/--init--.py` but has **zero callers** in `src/bioetl/`. The activity transformer was the only caller and now uses `validate-taxonomy-id` (returning `int`) instead.

**Fix:** Remove `validate-taxonomy-id-str` and its export, or deprecate it.

---

### WARN-2: Inconsistent `-json` suffix removal

**Severity:** LOW
**Files:**
- `src/bioetl/domain/entities/chembl.py:283` — `variant-sequence-json` NOT renamed
- `src/bioetl/domain/entities/chembl-activity.py:88` — `variant-sequence-json` NOT renamed

The refactoring removed `-json` suffixes from 13 fields across `ActivityRecord`, `AssayRecord`, `MoleculeRecord`, `TargetRecord`, and `TargetComponentRecord`, but `variant-sequence-json` was left unchanged in both `AssayRecord` and `Assay` entity. If the naming convention is to remove `-json`, this is inconsistent.

**Note:** This may be intentional — `variant-sequence-json` is a forensic/raw dump field distinct from the processed fields. If intentional, a comment would help.

---

### WARN-3: Stale comment in activity-transformer.py

**Severity:** INFO
**File:** `src/bioetl/application/pipelines/chembl/activity-transformer.py:72`

```python
# Standardized to 'taxonomy-id' for NCBI consistency (was 'tax-id')
```

The comment says "Standardized to 'taxonomy-id'" but the actual target is now `target-taxonomy-id`. The comment is stale.

---

## Scoring Summary

| Category | Weight | Raw Score | Deductions | Final |
|----------|--------|-----------|------------|-------|
| Architecture (ARCH) | 30% | 10 | 0 | 10.0 |
| Anti-Patterns (AP) | 25% | 10 | 0 | 10.0 |
| DI Violations (DI) | 20% | 10 | 0 | 10.0 |
| Naming (NAME) | 10% | 10 | −0.25 (WARN-2) | 9.75 |
| Types (TYPE) | 10% | 10 | −0.5 (BUG-4) | 9.5 |
| Testing (TEST) | 5% | 10 | −2.0 (BUG-1) −1.0 (BUG-2) −0.5 (BUG-3) | 6.5 |

**Weighted Score:** (10×0.30) + (10×0.25) + (10×0.20) + (9.75×0.10) + (9.5×0.10) + (6.5×0.05) = **9.75**

**Status: PASS** (≥ 8.0)

---

## Action Items

| # | Priority | Issue | File(s) | Action |
|---|----------|-------|---------|--------|
| 1 | **MUST** | BUG-1: Field ordering | `test-silver-pipeline-contracts.py` | Move `description` to alphabetical position |
| 2 | **MUST** | BUG-2: Stale aliases | `test-architecture.py` | Remove 6 stale `-json` aliases |
| 3 | **SHOULD** | BUG-3: Old field name | `test-molecule-pipeline.py` | Rename `property-qed-weighted` → `qed-score` |
| 4 | **SHOULD** | BUG-4: Type mismatch | `bioactivity.py` | Change `target-taxonomy-id: str` → `int` |
| 5 | **MAY** | WARN-1: Dead code | `taxonomy-id.py` | Remove `validate-taxonomy-id-str` |
| 6 | **MAY** | WARN-2: Incomplete rename | `chembl.py`, `chembl-activity.py` | Rename `variant-sequence-json` or add comment |
| 7 | **MAY** | WARN-3: Stale comment | `activity-transformer.py` | Update comment text |
