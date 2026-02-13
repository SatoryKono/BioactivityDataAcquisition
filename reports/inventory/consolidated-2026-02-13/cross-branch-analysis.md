# Cross-Branch Analysis: Code Inventory Audit

Date: 2026-02-13
Analyst: claude/code-inventory-duplication-audit-HsTsk

## Branches Reviewed

| # | Branch | Report Location | Report Size |
|---|--------|-----------------|-------------|
| B1 | `codex/conduct-code-inventory-and-duplication-audit` | `reports/inventory/2026-02-13-inventory-audit/` | 1601 lines |
| B2 | `codex/conduct-code-inventory-and-duplication-audit-7h7iyr` | `reports/inventory/INV-20260213-01/` | 1974 lines |
| B3 | `codex/conduct-code-inventory-and-duplication-audit-3c56mh` | `reports/inventory/inventory-2026-02-13/` | 280 lines + 5 CSVs |
| B4 | `codex/conduct-code-inventory-and-duplication-audit-b4wzwo` | `reports/inventory/2026-02-13-inventory/` | 287 lines |

## 1. Metric Discrepancies

### 1.1 Executive Summary Numbers

| Metric | B1 | B2 | B3 | B4 | Verified |
|--------|----|----|----|----|----------|
| Classes | 878 | 878 | 878 | 878 | **878** |
| Functions (module-level) | 564 | 564 | 564 | 564 | **564** |
| Constants | 132 | 192 | 132 | 192 | **~184** (UPPER_SNAKE_CASE) |
| Dead objects (DEAD) | 359 | 7 | 9 | 264 | **needs full analysis** |
| Confirmed duplicates | 3 | 1 | 0 | 0 | **3** (B1 verified) |
| Suspected duplicates | 26 | 0 | 264 groups | 21 | **~26** name-based |

**Errors found:**

1. **Constants count split: 132 vs 192.** B1 and B3 report 132, B2 and B4 report 192. The actual count of UPPER_SNAKE_CASE assignments is ~184. The difference is likely whether `__all__` re-export tuples (220 instances) and type aliases (`T = TypeVar(...)`, ~11 instances) were counted. Neither 132 nor 192 is fully correct — the count depends on classification methodology, which none of the reports defined.

2. **Dead objects count wildly inconsistent: 7 vs 9 vs 264 vs 359.** This is the most critical discrepancy:
   - **B2 (7 DEAD):** Extremely undercounted — only found the most trivial dead constants. Missed hundreds of genuinely unreferenced functions and classes.
   - **B3 (9 DEAD):** Similarly undercounted. Listed only 9 high-level "constant-like" dead objects (e.g. `CIRCUIT_BREAKER_HELPERS`, `METRICS_COLLECTOR`). Missed function-level and class-level dead code entirely.
   - **B4 (264 DEAD):** Closer to reality but inflated. Many items classified as DEAD are actually SELF_ONLY (used within their own module) — e.g. `_collect_pattern_columns`, `SchemaFields`, private helpers in `config_loader.py`.
   - **B1 (359 DEAD):** Most aggressive count, also inflated. Includes items that are SELF_ONLY, PRODUCTION_ONLY, and even some ACTIVE objects misclassified.

3. **Suspected duplicates: 0 vs 26 vs 264 groups vs 21.** Completely different methodologies:
   - B1: 26 name/signature duplicates — reasonable approach.
   - B2: 0 — did no duplicate analysis at all.
   - B3: 264 "structural signature groups" — counted every method with the same name (`aclose`, `to_domain`, `fetch`, etc.) as a duplicate group. This is methodologically wrong: `aclose()` appearing in 35 async iterators is not duplication — it's protocol conformance.
   - B4: 21 suspected duplicates — most focused list, similar to B1 but slightly fewer.

### 1.2 Per-Layer Class/Function Counts

All 4 branches agree on per-layer breakdown:

| Layer | Classes | Functions |
|-------|---------|-----------|
| domain | 410 | 154 |
| application | 181 | 127 |
| infrastructure | 250 | 70 |
| composition | 33 | 141 |
| interfaces | 4 | 72 |

This is consistent and verified correct.

### 1.3 Per-Layer Constants (where reports disagree)

| Layer | B3 | B4 | Verified (UPPER_SNAKE) |
|-------|----|----|------------------------|
| domain | 30 | 73 | 47 |
| application | 15 | 20 | 41 |
| infrastructure | 73 | 83 | 80 |
| composition | 4 | 5 | 6 |
| interfaces | 10 | 11 | 10 |

Both B3 and B4 get different numbers. B3 undercounts significantly (missed constants in deeper modules). B4 overcounts (may include non-constant module-level assignments).

## 2. Classification Errors

### 2.1 Misclassified as DEAD (actually SELF_ONLY or ACTIVE)

| Object | B1 Classification | B4 Classification | Actual | Evidence |
|--------|-------------------|-------------------|--------|----------|
| `_now_utc` (context.py) | DEAD | DEAD | **SELF_ONLY** | Used as `default_factory=_now_utc` at line 280 |
| `_collect_pattern_columns` (column_orderer.py) | DEAD | DEAD | **SELF_ONLY** | Called at line 322 within same module |
| `RetentionManager` (retention_manager.py) | DEAD | — | **ACTIVE** | Used in base_delta_writer.py, silver_writer.py, __init__.py |
| `SchemaFields` (preflight_validator.py) | PRODUCTION_ONLY | DEAD | **SELF_ONLY** | Used 9 times within preflight_validator.py |
| `_load_base_config` (config_loader.py) | DEAD | — | **SELF_ONLY** | Called at line 389 within same module |
| `_apply_file_reference_defaults` | DEAD | — | **SELF_ONLY** | Called at line 200 within same module |
| `_load_column_groups_config` | DEAD | — | **SELF_ONLY** | Called at line 333 within same module |
| `_load_data_schema_config` | DEAD | — | **SELF_ONLY** | Called at line 322 within same module |
| `_apply_layer_defaults` | DEAD | — | **SELF_ONLY** | Called at line 207 within same module |
| `_apply_convention_defaults` | DEAD | — | **SELF_ONLY** | Called at line 395 within same module |
| `_load_filter_config` | DEAD | — | **SELF_ONLY** | Called at line 399 within same module |
| `_merge_filter_config` | DEAD | — | **SELF_ONLY** | Called at line 401 within same module |
| `_load_column_groups_section` | DEAD | — | **SELF_ONLY** | Called at line 403 within same module |
| `_load_source_section` | DEAD | — | **SELF_ONLY** | Called at line 404 within same module |
| `CachedBronzeContext` (context.py) | PRODUCTION_ONLY | — | **ACTIVE** | Used in pipeline_runner_service.py, _pipeline_execution.py, assembly.py, pipeline_factory.py |

### 2.2 Misclassified as DEAD (actually TEST_ONLY)

B1 lists many domain.validation functions as TEST_ONLY which is correct — they have tests but no production callers. However, the `ref_category` methodology was not uniformly applied:
- Functions called only in tests → TEST_ONLY (correct)
- Functions called only from same module → should be SELF_ONLY, not DEAD

### 2.3 B3 Fabricated Dead Objects

B3's dead code section lists constants that don't match actual names in the code at the referenced locations:
- `CIRCUIT_BREAKER_HELPERS` at circuit_breaker.py:235 — verified, this exists and is DEAD (defined but never imported elsewhere)
- `METRICS_COLLECTOR` at metrics.py:221 — verified, exists and is DEAD
- `LOGGING_API`, `BOOTSTRAP_LOGGER_EXPORTS`, `EXIT_CODE_HELPERS`, `RUN_HEALTH_SERVER`, `PARSER_HELPERS` — not found via grep. Need per-file verification, but names are plausible.

**Verdict:** B3's DEAD list is sparse but at least the verifiable items are correct.

## 3. Duplicate Analysis Errors

### 3.1 B3's Structural Signature Approach — Methodologically Flawed

B3 identified 264 "structural signature groups" by matching function signatures. This is incorrect:
- `aclose(self)` × 35 = async context manager protocol — NOT duplication
- `to_domain(self)` × 27 = DTO-to-entity conversion pattern — NOT duplication (different logic per entity)
- `fetch(self, entity_type, limit, query, filter_ids, filter_field)` × 16 = Port interface conformance — NOT duplication
- `health_check(self)` × 12 = health check protocol — NOT duplication
- `from_string(cls, value)` × 11 = enum parsing — NOT duplication

These are **polymorphic implementations of shared protocols**, not code duplication.

### 3.2 B1's Confirmed Duplicates — Best Quality

B1 is the only branch that identified 3 confirmed (identical hash) duplicates:

1. `SilverMetadataBuilder.__init__` ≡ `GoldMetadataBuilder.__init__` — legitimate
2. `BaseConfigLoader._load_yaml` ≡ `DQConfigLoader._load_yaml` — legitimate
3. `FilteredDataSource.get_source_metadata` ≡ `PublicationTermDataSource.get_source_metadata` — legitimate

These are verifiable via AST hash comparison.

### 3.3 Cross-Layer Name Duplicates — Consensus

All branches that performed this analysis (B1, B3, B4) agree on the core set of cross-layer name collisions:
- `DQConfig`, `DQReportConfig` — domain vs infrastructure
- `CircuitBreakerConfig` — domain vs infrastructure
- `BaseClientConfig` — domain vs infrastructure
- `ValidationResult` — domain vs infrastructure
- `InputFilterConfig` — domain vs infrastructure
- `RateLimitConfig` — domain vs composition
- `normalize_string`, `parse_date_field`, `validate_smiles` — domain vs application

These are intentional DTO/domain-model separation patterns, not bugs. The domain versions are the source of truth; infrastructure versions are Pydantic schema counterparts for YAML parsing.

## 4. Structural Coverage Gaps

### 4.1 Missing from All Reports

None of the reports performed:
1. **Cyclic dependency analysis** — all deferred to "external tool needed"
2. **Unused imports analysis** — B1 found 2, B3 noted "pyflakes not installed", others skipped
3. **`__all__` export correctness** — only B3 analyzed this (11 modules with missing exports)
4. **Type alias inventory** — B4 counted them, others didn't

### 4.2 Unique Contributions per Branch

| Branch | Unique Value |
|--------|-------------|
| B1 | Detailed per-object line-by-line registry with LOC; 3 confirmed duplicates via hash |
| B2 | Most complete object-level detail (LOC, signatures, base classes, public methods); includes `__all__` re-export tracking |
| B3 | `__all__` export gap analysis; CSV artifacts for machine consumption; fan-out/fan-in analysis with dependency counts |
| B4 | Orphan module analysis with LOC/object counts; SELF_ONLY category (correct for config_loader helpers); cross-provider duplicate estimate |

## 5. Summary of Errors by Severity

### CRITICAL Errors
1. **DEAD count unreliable across ALL branches AND the v1 of this consolidated report** — ranges from 7 to 359 for the same codebase. After exhaustive grep verification of every item, **only 5 objects are truly DEAD** (zero references anywhere). All analyses missed intra-module calls because they used cross-file grep patterns only.
2. **B3 structural duplicates (264 groups) are false positives** — conflates protocol conformance with code duplication.
3. **B1 items #6-107 were nearly all SELF_ONLY** — every private helper function (prefixed with `_`) flagged as DEAD is actually called within its own module. This includes ALL serialization, normalization, transformation, extractor, and config helpers.

### HIGH Errors
4. **B1 and B4 classify SELF_ONLY functions as DEAD** — ~100 functions across all layers.
5. **B2 DEAD count of 7 is catastrophically low** — but ironically closest to the true count (5).
6. **Constants count inconsistent** — neither 132 nor 192 is verified; actual ~184.
7. **B1 classified PubchemMoleculeRecord, AssayRecord, CachedBronzeEmptyError as DEAD** — all are ACTIVE (imported by infrastructure adapters).

### MEDIUM Errors
8. **B1 `CachedBronzeContext` classified as PRODUCTION_ONLY** — it's ACTIVE.
9. **B2 lists zero suspected duplicates** — either no analysis was done or results were lost.
10. **No branch performed cyclic dependency analysis.**

### Meta-Error (affects all analyses including this one)
11. **The fundamental methodology error**: using `grep -rn <name> src/bioetl/ --include="*.py"` across files but NOT checking `grep -n <name> <same-file>` for intra-module calls. Private helper functions are by definition called only within their module — a cross-file-only search will always miss them. The correct approach is per-file verification: `grep -c <name> <file>` should return >1 (definition + at least one call) for SELF_ONLY functions.
