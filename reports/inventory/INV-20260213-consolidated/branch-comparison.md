# Cross-Branch Comparison — Code Inventory Audit

Date: 2026-02-13
Source branches:
- B1: `codex/conduct-code-inventory-and-duplication-audit`
- B2: `codex/conduct-code-inventory-and-duplication-audit-7h7iyr`
- B3: `codex/conduct-code-inventory-and-duplication-audit-3c56mh`
- B4: `codex/conduct-code-inventory-and-duplication-audit-b4wzwo`

## 1. Executive Summary Discrepancies

| Метрика | B1 | B2 | B3 | B4 | Verified |
|---------|----|----|----|----|----------|
| Classes | 878 | 878 | 878 | 878 | **878** OK |
| Functions | 564 | 564 | 564 | 564 | **564** OK |
| Constants | 132 | 192 | 132 | 192 | **184** (none correct) |
| Dead objects | 359 | 7 | 9 | 264 | **~9 true DEAD** (see below) |
| Confirmed duplicates | 3 | 1 | 0 | 0 | **0 true duplicates** |
| Suspected duplicates | 26 | 0 | 264 groups | 21 | **~21 name collisions** |

### Key Observation

All four branches disagree fundamentally on dead object and duplication counts.
This stems from different methodologies and classification errors.

## 2. Constant Count Discrepancy (132 vs 192 vs 184)

**Actual count: ~184 module-level UPPER_SNAKE_CASE assignments.**

| Layer | B1/B3 | B2/B4 | Verified |
|-------|-------|-------|----------|
| domain | 30 | 73 | **47** |
| application | 15 | 20 | **41** |
| infrastructure | 73 | 83 | **80** |
| composition | 4 | 5 | **6** |
| interfaces | 10 | 11 | **10** |
| **Total** | **132** | **192** | **184** |

- B1/B3 (132) — undercounted, likely excluded `__all__` exports and type aliases
- B2/B4 (192) — overcounted, likely included some non-constant module-level assignments
- Neither is exact; the true count depends on the definition of "constant"

## 3. Dead Object Count Discrepancy (359 vs 7 vs 9 vs 264)

This is the most severe divergence. Root cause analysis:

### B1 (359 dead objects)
**ERROR: Massive overcount.** Classified SELF_ONLY helpers as DEAD.
- Private helpers like `_get_orjson_options`, `_serialize_with_orjson`, `_is_electronic_page`
  are called within their own files but were classified as "0 references"
- The reference search likely excluded intra-file calls
- Also incorrectly classified `_now_utc` (used as default_factory) and
  `CachedBronzeEmptyError` (imported in infrastructure) as DEAD
- Also classified `parse_date_field` and `validate_smiles` as TEST_ONLY when they
  are ACTIVE (used in production via delegation in dict_transformers.py)

### B2 (7 dead objects)
**CONSERVATIVE: Likely only flagged module-level helper constants.**
- Did not list specific DEAD objects in the report
- The `confirmed=1` duplicate is also unverified

### B3 (9 dead objects)
**CLOSEST TO CORRECT.** Listed specific objects with verifiable evidence:
- 7 module-level constants (`CIRCUIT_BREAKER_HELPERS`, `METRICS_COLLECTOR`, etc.)
- 1 function (`compute_subcellular_fraction_entity_id`)
- 1 constant (`VALIDATION_API`)
- These are primarily `__all__`-style export constants that aggregate module objects
- Also provided CSV files for machine-readable verification

### B4 (264 dead objects)
**ERROR: Significant overcount.** Mixed SELF_ONLY, TEST_ONLY, and truly DEAD objects.
- Listed many private helper functions as DEAD
- Also classified delegation pattern wrappers as duplicates
- However, the list is more granular and detailed than B1

### Verified DEAD objects (true 0-reference, not SELF_ONLY)

| # | Object | Type | Layer | File:Line |
|---|--------|------|-------|-----------|
| 1 | `CIRCUIT_BREAKER_HELPERS` | constant | infrastructure | adapters/http/circuit_breaker.py:235 |
| 2 | `METRICS_COLLECTOR` | constant | infrastructure | observability/metrics.py:221 |
| 3 | `LOGGING_API` | constant | infrastructure | observability/logging.py:52 |
| 4 | `BOOTSTRAP_LOGGER_EXPORTS` | constant | composition | bootstrap_logger.py:140 |
| 5 | `EXIT_CODE_HELPERS` | constant | interfaces | cli/exit_codes.py:120 |
| 6 | `RUN_HEALTH_SERVER` | constant | interfaces | http/health_server.py:305 |
| 7 | `PARSER_HELPERS` | constant | application | pipelines/pubmed/xml_parser.py:79 |
| 8 | `compute_subcellular_fraction_entity_id` | function | application | core/entity_id.py:36 |
| 9 | `VALIDATION_API` | constant | domain | validation.py:412 |

These 9 objects (from B3) are the only ones confirmed as truly unreferenced.
The rest flagged across branches are either SELF_ONLY helpers or misclassified.

## 4. Duplication Count Discrepancy

### B1: 3 confirmed + 26 suspected
- The "3 confirmed" are not documented with evidence
- The 26 suspected are not listed in detail

### B2: 1 confirmed + 0 suspected
- The "1 confirmed" is not documented

### B3: 0 confirmed + 264 structural signature groups
- Used method signature grouping (e.g., `aclose(self)` appears 35 times)
- These are NOT duplicates — they're protocol implementations
- Methods like `aclose()`, `to_domain()`, `fetch()` are Protocol-mandated

### B4: 0 confirmed + 21 suspected
- Provided detailed list of 21 name collisions
- Also incorrectly flagged delegation patterns as duplicates

### Verified Duplication Status

| # | Object Pair | Claim | Verdict |
|---|-------------|-------|---------|
| 1 | `normalize_string` (application ↔ domain) | Duplicate | **NOT duplicate** — delegation pattern |
| 2 | `parse_date_field` (application ↔ domain) | Duplicate | **NOT duplicate** — delegation pattern |
| 3 | `validate_smiles` (application ↔ domain) | Duplicate | **NOT duplicate** — delegation pattern |
| 4 | `_get_bioetl_version` (composition ↔ infrastructure) | Duplicate | **NOT duplicate** — independent impl, ARCH-001 forbids import |
| 5 | `_serialize_value` (domain ↔ infrastructure) | Duplicate | **NOT duplicate** — different logic/purpose |
| 6 | `ValidationResult` (domain ↔ infrastructure) | Duplicate | **NOT duplicate** — only exists in infrastructure |
| 7 | `BaseClientConfig` (domain ↔ infrastructure) | Duplicate | **NOT duplicate** — schema↔domain conversion pattern |
| 8 | `CircuitBreakerConfig` (domain ↔ infrastructure) | Duplicate | **NOT duplicate** — schema↔domain conversion pattern |
| 9 | `DQConfig` (domain ↔ infrastructure) | Duplicate | **NOT duplicate** — schema↔domain conversion pattern |
| 10 | `InputFilterConfig` (domain ↔ infrastructure) | Duplicate | **NOT duplicate** — schema↔domain conversion pattern |
| 11 | `RateLimitConfig` (domain ↔ composition) | Duplicate | **NAME COLLISION** — different fields, different purpose |
| 12 | `CleanupResult` (application × 2) | Duplicate | **NAME COLLISION** — same layer, different semantics |

**True duplicates: 0.**
**Name collisions requiring attention: 2** (`RateLimitConfig`, `CleanupResult`).

## 5. Structural / Methodological Errors by Branch

### B1 Errors
| # | Error | Severity |
|---|-------|----------|
| 1 | SELF_ONLY private helpers classified as DEAD (inflated count 40x) | CRITICAL |
| 2 | `_now_utc` classified as DEAD (used as dataclass default_factory) | HIGH |
| 3 | `CachedBronzeEmptyError` classified as DEAD (imported in infrastructure) | HIGH |
| 4 | `parse_date_field`, `validate_smiles` classified as TEST_ONLY (used in production) | HIGH |
| 5 | "3 confirmed duplicates" claimed without evidence | MEDIUM |
| 6 | Constants count 132 (undercount) | LOW |
| 7 | Inline exhaustive registry (5000+ line report) — low signal-to-noise | INFO |

### B2 Errors
| # | Error | Severity |
|---|-------|----------|
| 1 | Date field shows "INV-20260213-01" instead of date | LOW |
| 2 | Inline exhaustive registry with `__all__` entries — noise | INFO |
| 3 | "1 confirmed duplicate" claimed without evidence | MEDIUM |
| 4 | No dead code details — cannot verify 7 DEAD objects | HIGH |
| 5 | Constants count 192 (overcount) | LOW |

### B3 Errors
| # | Error | Severity |
|---|-------|----------|
| 1 | 264 "structural signature groups" presented as suspected duplicates | HIGH |
| 2 | Protocol implementations (`aclose`, `fetch`, `health_check`) flagged as duplication | HIGH |
| 3 | Constants count 132 (undercount) | LOW |
| 4 | No confirmed duplicates section is correct | — |
| 5 | Dead object list (9 items) is the most accurate of all branches | — |

### B4 Errors
| # | Error | Severity |
|---|-------|----------|
| 1 | 264 DEAD objects (massive overcount due to SELF_ONLY inclusion) | CRITICAL |
| 2 | Delegation patterns flagged as duplicates | HIGH |
| 3 | Schema↔domain conversion pairs flagged as duplicates | HIGH |
| 4 | `ValidationResult` claimed in domain/types.py — not found there | MEDIUM |
| 5 | Constants count 192 (overcount) | LOW |

## 6. What Each Branch Got Right

| Branch | Strengths |
|--------|-----------|
| B1 | Most detailed per-object registry with LOC and ref_category |
| B2 | Most detailed object signatures, base classes, public methods |
| B3 | Most accurate DEAD list; CSV exports; `__all__` gap analysis; dependency fan-in/fan-out; SELF_ONLY list |
| B4 | Good dependency map; cross-layer duplicate analysis; orphan module detection |

## 7. Conclusion

No single branch produced a correct report. The best approach is to consolidate:
- **Object registry**: B2's format (with signatures and base classes)
- **Dead code**: B3's methodology and list (verified 9 objects)
- **Duplication**: B4's approach (name collisions) with corrected analysis
- **Dependencies**: B3/B4's fan-in/fan-out tables
- **`__all__` gaps**: B3's unique contribution
- **Orphan modules**: B4's unique contribution
