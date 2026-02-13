# Consolidated Code Inventory & Duplication Audit Plan

Date: 2026-02-13
ID: INV-20260213-CONSOLIDATED
Status: CORRECTED (based on cross-verification of 4 independent audits)

---

## Executive Summary (Verified)

| Метрика | Значение | Confidence |
|---------|----------|------------|
| Всего классов | 878 | HIGH (4/4 branches agree) |
| Всего функций (module-level) | 564 | HIGH (4/4 branches agree) |
| Всего констант | ~184 | MEDIUM (needs definition clarity) |
| Мёртвых объектов (DEAD) | 9 | HIGH (verified cross-file grep) |
| SELF_ONLY объектов | ~30 | MEDIUM (needs full verification) |
| TEST_ONLY объектов | ~20 | MEDIUM (needs full verification) |
| Name collisions (cross-module) | 2 | HIGH (verified code review) |
| True copy-paste duplicates | 0 | HIGH (verified code review) |
| Schema↔Domain pairs (intentional) | ~8 | HIGH (architectural pattern) |

---

## 1. Object Registry by Layer (Verified Counts)

### 1.1 Summary

| Layer | Classes | Functions | Constants | Total |
|-------|--------:|----------:|----------:|------:|
| domain | 410 | 154 | 47 | 611 |
| application | 181 | 127 | 41 | 349 |
| infrastructure | 250 | 70 | 80 | 400 |
| composition | 33 | 141 | 6 | 180 |
| interfaces | 4 | 72 | 10 | 86 |
| **Total** | **878** | **564** | **184** | **1626** |

### 1.2 Constant Count Methodology Note

The constant count of 184 uses the criterion: module-level `UPPER_SNAKE_CASE`
assignments (excluding `__all__`, `__version__`, and type alias assignments).
Branches reporting 132 excluded some valid constants; branches reporting 192
included some non-constant module-level assignments.

---

## 2. Dead Code (Verified)

### 2.1 True DEAD Objects (0 references outside of definition)

These objects are not referenced anywhere in production code or tests:

| # | Object | Type | Layer | File:Line | Recommendation |
|---|--------|------|-------|-----------|----------------|
| 1 | `CIRCUIT_BREAKER_HELPERS` | constant | infrastructure | adapters/http/circuit_breaker.py:235 | Remove |
| 2 | `METRICS_COLLECTOR` | constant | infrastructure | observability/metrics.py:221 | Remove |
| 3 | `LOGGING_API` | constant | infrastructure | observability/logging.py:52 | Remove |
| 4 | `BOOTSTRAP_LOGGER_EXPORTS` | constant | composition | bootstrap_logger.py:140 | Remove |
| 5 | `EXIT_CODE_HELPERS` | constant | interfaces | cli/exit_codes.py:120 | Remove |
| 6 | `RUN_HEALTH_SERVER` | constant | interfaces | http/health_server.py:305 | Remove |
| 7 | `PARSER_HELPERS` | constant | application | pipelines/pubmed/xml_parser.py:79 | Remove |
| 8 | `compute_subcellular_fraction_entity_id` | function | application | core/entity_id.py:36 | Remove |
| 9 | `VALIDATION_API` | constant | domain | validation.py:412 | Remove |

**Note:** All 9 are either unused module-level aggregation constants (`*_HELPERS`,
`*_API`, etc.) or a single orphan function. These can be safely deleted.

### 2.2 Commonly Misclassified Objects

The following objects were incorrectly flagged as DEAD by 1-2 branches.
They are NOT dead:

| Object | Misclassification | Actual Status | Reason |
|--------|-------------------|---------------|--------|
| `_now_utc` | DEAD (B1) | PRODUCTION_ONLY | Used as `default_factory` in dataclass |
| `CachedBronzeEmptyError` | DEAD (B1) | PRODUCTION_ONLY | Imported in `cached_bronze_data_source.py` |
| `parse_date_field` | TEST_ONLY (B1) | ACTIVE | Delegated from `dict_transformers.py` |
| `validate_smiles` | TEST_ONLY (B1) | ACTIVE | Delegated from `dict_transformers.py` |
| `_get_orjson_options` | DEAD (B1) | SELF_ONLY | Called within `serialization.py` |
| `_serialize_with_orjson` | DEAD (B1) | SELF_ONLY | Called within `serialization.py` |
| `_is_electronic_page` | DEAD (B1) | SELF_ONLY | Called within `normalization.py` |
| `_validate_threshold_order` | DEAD (B1,B3) | SELF_ONLY | Called within `config.py` |
| `_match_error_type` | DEAD (B1) | SELF_ONLY | Called within `error_classifier.py` |

**Root cause:** Branches B1 and B4 used grep-based reference counting that
excluded intra-file references. Private helper functions (`_name`) are SELF_ONLY
by design — they support public functions within the same module.

### 2.3 SELF_ONLY Objects (Require Review, Not Removal)

Objects used only within their own module. These are typically private helpers
and are NOT candidates for removal. Review for potential consolidation only:

Source: B3 report (30 objects identified). Key categories:

| Category | Count | Example | Action |
|----------|-------|---------|--------|
| Config loader helpers | 9 | `_load_base_config`, `_apply_file_reference_defaults` | No action — internal pipeline |
| Adapter models | 5 | `UniProtEcNumber`, `UniProtKeyword` | No action — used by `to_domain()` |
| Storage helpers | 4 | `_get_string_fields`, `_get_git_commit_cached` | No action — internal utils |
| Validation helpers | 2 | `BasePanderaValidator`, `NoOpValidator` | No action — subclass hierarchy |
| Mixin classes | 4 | `HealthCheckMixin`, `DelegatingFallbackMixin` | No action — mixin pattern |
| Error handling | 2 | `ErrorCategory`, `AdapterErrorContext` | No action — error infrastructure |
| Other | 4 | Various | Case-by-case review |

### 2.4 TEST_ONLY Objects (Require Review)

Objects referenced only in test files. May indicate:
- Test-specific utilities that belong in test fixtures
- Public API that is tested but no longer used in production
- New code with tests written first (TDD)

Key items from B3/B4 that need manual review:

| # | Object | Layer | Possible Status |
|---|--------|-------|-----------------|
| 1 | `TransformerPort` | application | May be upcoming feature |
| 2 | `PIPELINE_HEALTH_CHECK_PASSED` | infrastructure | Prometheus metric — may be used at runtime |
| 3 | `DataClassification` | domain | Enum — may be used via value matching |
| 4 | Various domain validation functions | domain | May be used through delegation pattern |

### 2.5 Orphan Modules (Files Without External Imports)

Source: B4 report.

| # | File | LOC | Verdict |
|---|------|-----|---------|
| 1 | `src/bioetl/__main__.py` | 8 | **OK** — Python entry point (`python -m bioetl`) |
| 2 | `src/bioetl/interfaces/cli/__main__.py` | 9 | **OK** — CLI entry point |
| 3 | `src/bioetl/interfaces/observability.py` | 19 | **OK** — Re-export facade, tested in test_observability.py |
| 4 | `src/bioetl/infrastructure/storage/delta_writer.py` | 8 | **OK** — Compat wrapper, used in benchmark tests |
| 5 | `src/bioetl/composition/types.py` | 52 | **OK** — Type re-export facade, tested in test_types.py |
| 6 | `src/bioetl/composition/factories/storage_factory.py` | 341 | **OK** — Active factory, re-exported via storage.py facade |
| 7 | `src/bioetl/composition/factories/storage_adapter.py` | 652 | **OK** — StoragePort impl, re-exported via storage.py facade |
| 8 | `src/bioetl/application/core/subcellular_fraction_data_source.py` | 297 | **VERIFY** — Has tests but no direct import in src/ |

**CORRECTION:** Verification shows 7/8 modules are NOT orphaned (re-export facades,
compat wrappers, factored-out implementations). Only #8 needs further investigation
for possible dynamic registration.

### 2.6 `__all__` Export Gaps

Source: B3 report (unique contribution).

**CORRECTION:** Cross-verification showed that most B3 `__all__` gap claims are
**FALSE POSITIVES**. The constants ARE already correctly exported. Verified:

| # | Module | Claimed Missing | Actual Status |
|---|--------|----------------|---------------|
| 1 | `infrastructure.serialization.encoders` | `ORJSON_AVAILABLE` | **IN `__all__`** — false positive |
| 2 | `composition.factories.pipeline_factories` | `PIPELINE_CONFIGS` | **IN `__all__`** (line 580) — false positive |
| 3 | `interfaces.cli.exit_codes` | `EXCEPTION_EXIT_CODES` | **IN `__all__`** (line 123) — false positive |
| 4 | `application.core.field_specs` | `FLOAT`, `INT`, `STR` | **IN `__all__`** (lines 306-310) — false positive |
| 5 | `domain.composite.field_groups` | `DEFAULT_PROVIDER_ORDER` | **IN `__all__`** (line 29) — false positive |
| 6 | `domain.schemas.column_order` | `ALL_SYSTEM_FIELDS`, etc. | **IN `__all__`** (lines 17-19) — false positive |
| 7 | `domain.value_objects.column_order` | `DEFAULT_COLUMN_ORDER`, etc. | **IN `__all__`** (lines 14-15) — false positive |
| 8 | `domain.value_objects.publication_field_groups` | `DEFAULT_FIELD_GROUP_CONFIG`, etc. | **IN `__all__`** (lines 24-25) — false positive |
| 9 | `domain.value_objects.column_qualifier` | `JOIN_KEY_COLUMNS` | **IN `__all__`** (line 12) — false positive |

**Conclusion:** No verified `__all__` export gaps found. B3 likely used AST parsing
that failed to match multi-line `__all__` definitions or compared against a stale snapshot.

---

## 3. Duplication Analysis (Verified)

### 3.1 True Duplicates

**None found.** All 4 branches failed to identify any verified copy-paste duplicates.

### 3.2 Name Collisions (Verified — 2 issues)

| # | Name | Location A | Location B | Nature | Recommendation |
|---|------|-----------|-----------|--------|----------------|
| 1 | `RateLimitConfig` | `domain/configs/base.py` (fields: `requests_per_second`, `burst`) | `composition/bootstrap_contexts.py` (fields: `rate`, `capacity`) | Different classes, different fields, same name | Rename composition version → `RateLimitContext` |
| 2 | `CleanupResult` | `application/core/cleanup_service.py` (Silver/Gold) | `application/services/bronze_cleanup_service.py` (Bronze) | Same layer, different semantics | Rename bronze version → `BronzeCleanupResult` |

### 3.3 Intentional Schema↔Domain Pairs (NOT Duplicates)

These are correctly separated by architecture (ARCH-001):

| # | Domain Object | Infrastructure Object | Pattern |
|---|--------------|----------------------|---------|
| 1 | `BaseClientConfig` (frozen dataclass) | `BaseClientConfig` (Pydantic) | Schema parses YAML → `to_domain()` → domain object |
| 2 | `CircuitBreakerConfig` (frozen dataclass) | `CircuitBreakerConfig` (Pydantic) | Same pattern |
| 3 | `DQConfig` (frozen dataclass) | `DQConfig` (Pydantic) | Same pattern |
| 4 | `DQReportConfig` (frozen dataclass) | `DQReportConfig` (Pydantic) | Same pattern |
| 5 | `InputFilterConfig` (frozen dataclass) | `BaseInputFilterConfig` (Pydantic) | Same pattern |

**Why this is NOT duplication:**
- Domain layer defines immutable value objects
- Infrastructure layer defines Pydantic models for YAML deserialization
- Infrastructure models have `to_domain()` methods for conversion
- ARCH-001 forbids infrastructure → domain reverse dependency

### 3.4 Intentional Delegation Patterns (NOT Duplicates)

| # | Application Function | Domain Function | Pattern |
|---|---------------------|----------------|---------|
| 1 | `dict_transformers.normalize_string()` | `normalization.normalize_string()` | Thin wrapper → delegates to domain |
| 2 | `dict_transformers.parse_date_field()` | `normalization.parse_date_field()` | Thin wrapper → delegates to domain |
| 3 | `dict_transformers.validate_smiles()` | `validation.validate_smiles()` | Thin wrapper → delegates to domain |

**Why this is NOT duplication:**
- Application functions are thin wrappers for use-case convenience
- Actual business logic lives in domain layer
- This follows REFACTOR-004 (business logic separation)

### 3.5 Architecture-Mandated Independent Implementations (NOT Duplicates)

| # | Object | Layer A | Layer B | Reason |
|---|--------|---------|---------|--------|
| 1 | `_get_bioetl_version` | composition | infrastructure | ARCH-001 forbids cross-import; different error handling |
| 2 | `_serialize_value` | domain (DQ serializer) | infrastructure (Delta writer) | Different logic, different purpose |

### 3.6 Protocol-Mandated Method Signatures (NOT Duplicates)

B3 flagged 264 "structural signature groups" like `aclose(self)` (35 occurrences),
`to_domain(self)` (27), `fetch(...)` (16), etc. These are **Protocol implementations**
— every adapter must implement the same interface methods. This is correct OOP
design, not duplication.

---

## 4. Dependency Map (Consolidated)

### 4.1 Highest Fan-Out (most outgoing dependencies)

Source: B3/B4 (consistent data).

| # | Module | Layer | Deps | Risk |
|---|--------|-------|------|------|
| 1 | `composition.factories.pipeline_factories` | composition | 49 | High coupling — expected for factory |
| 2 | `domain.__init__` | domain | 25 | Re-export facade — expected |
| 3 | `domain.ports.__init__` | domain | 24 | Re-export facade — expected |
| 4 | `composition.bootstrap.runtime.composite` | composition | 22 | Assembly — expected |
| 5 | `composition.factories.services_factory` | composition | 22 | Factory — expected |
| 6 | `composition.factories.pipeline_factory` | composition | 21 | Factory — expected |
| 7 | `application.core.__init__` | application | 21 | Re-export facade — expected |
| 8 | `infrastructure.adapters.chembl.client` | infrastructure | 20 | Largest adapter |
| 9 | `composition.providers.registration` | composition | 18 | Provider registration |
| 10 | `domain.value_objects.__init__` | domain | 18 | Re-export facade |

**Observation:** Top fan-out modules are all composition factories and
`__init__` re-export facades. This is expected for Hexagonal Architecture.

### 4.2 Highest Fan-In (most depended upon)

| # | Module | Layer | Dependents | Criticality |
|---|--------|-------|------------|-------------|
| 1 | `bioetl.domain.types` | domain | 74-131* | Critical — shared enums/types |
| 2 | `bioetl.domain.ports` | domain | 46-181* | Critical — all port contracts |
| 3 | `bioetl.domain.exceptions` | domain | 26-30 | High — shared exceptions |
| 4 | `bioetl.domain.config` | domain | 37 | High — configuration |
| 5 | `bioetl.domain.context` | domain | 36 | High — pipeline context |
| 6 | `bioetl.domain.medallion` | domain | 16-21 | High — layer policies |

*Range reflects different counting methodologies between B3 and B4.

### 4.3 Cyclic Dependencies

Not computed by any branch. All branches note this requires dedicated tooling
(`import-linter`, `grimp`, `pydeps`).

**Recommendation:** Run `import-linter` as part of CI.

---

## 5. Corrected Action Plan

### Phase 1: Quick Wins (Low Risk, Immediate)

| # | Action | Objects | Effort | Impact |
|---|--------|---------|--------|--------|
| 1.1 | Delete 9 verified DEAD objects | §2.1 table | S | Clean dead code |
| 1.2 | Rename `CleanupResult` → `BronzeCleanupResult` | 1 class + refs | S | Resolve name collision |
| 1.3 | Rename `RateLimitConfig` → `RateLimitContext` in composition | 1 class + refs | S | Resolve name collision |
| 1.4 | Run `pyflakes` / `ruff` unused import check | All modules | S | Clean imports |

### Phase 2: Verification Tasks (Medium Risk)

| # | Action | Objects | Effort | Impact |
|---|--------|---------|--------|--------|
| 2.1 | Verify 8 orphan modules (§2.5) | 8 files | M | May remove/refactor |
| 2.2 | Verify TEST_ONLY objects (§2.4) | ~20 objects | M | May remove or add prod usage |
| 2.3 | Full SELF_ONLY audit with corrected methodology | ~30 objects | M | Baseline for future |
| 2.4 | Set up `import-linter` in CI | Infrastructure | M | Ongoing protection |

### Phase 3: Structural Improvements (Higher Risk, Needs Planning)

| # | RF-ID | Action | Impact | Risk |
|---|-------|--------|--------|------|
| 3.1 | RF-INV-001 | Review cross-provider extractor patterns | HIGH | MEDIUM |
| 3.2 | RF-INV-002 | Document schema↔domain pair convention in ADR | MEDIUM | LOW |
| 3.3 | RF-INV-003 | Review facade `__init__` re-export strategy | MEDIUM | LOW |

---

## 6. Methodology Recommendations for Future Audits

### 6.1 Object Classification Definitions

| Category | Definition | Detection |
|----------|-----------|-----------|
| **ACTIVE** | Referenced in production code AND tests | `grep` in src/ AND tests/ |
| **PRODUCTION_ONLY** | Referenced in production code, NOT in tests | `grep` in src/ only |
| **TEST_ONLY** | Referenced in tests only, NOT in production | `grep` in tests/ only, excluding src/ |
| **SELF_ONLY** | Referenced only within the same file | `grep` finds refs only in defining file |
| **DEAD** | Zero references anywhere (including own file) | `grep` finds 0 matches outside definition line |

**Critical rule:** SELF_ONLY ≠ DEAD. Private helper functions called within their
own module are NOT dead code. They are implementation details.

### 6.2 Duplication Classification Definitions

| Category | Definition | Action |
|----------|-----------|--------|
| **True duplicate** | Same logic, same purpose, copy-pasted | Consolidate |
| **Name collision** | Same name, different logic/fields | Rename one |
| **Schema↔Domain pair** | Infrastructure Pydantic ↔ Domain dataclass with `to_domain()` | Document pattern |
| **Delegation wrapper** | Application function wrapping domain function | Document pattern |
| **Protocol implementation** | Same method signature across implementors | No action (by design) |
| **Architecture-mandated** | Same utility in layers that cannot cross-import | No action (ARCH-001) |

### 6.3 Tooling Recommendations

| Tool | Purpose | Phase |
|------|---------|-------|
| `ruff` with unused import rules | Detect unused imports | CI |
| `vulture` | Detect dead code (understands SELF_ONLY) | CI |
| `import-linter` | Detect cyclic and cross-layer violations | CI |
| AST-based duplicate detector | Detect true copy-paste (not just name matches) | Audit |

---

## Appendix A: Branch Quality Assessment

| Criterion | B1 | B2 | B3 | B4 |
|-----------|:--:|:--:|:--:|:--:|
| Correct DEAD classification | - | ? | ++ | - |
| Correct duplication analysis | - | - | + | + |
| Object registry detail | ++ | +++ | + | + |
| Dependency analysis | - | - | ++ | ++ |
| `__all__` gap analysis | - | - | +++ | - |
| Orphan module detection | - | - | - | ++ |
| CSV/machine-readable output | - | - | +++ | - |
| Actionable recommendations | + | - | ++ | ++ |
| **Overall reliability** | **LOW** | **LOW** | **HIGH** | **MEDIUM** |

Best source for each section:
- Dead code → **B3**
- Object registry → **B2** (format), **B3** (accuracy)
- Duplications → **B4** (with corrections from this document)
- Dependencies → **B3** = **B4** (consistent)
- `__all__` gaps → **None** (B3 claims are false positives)
- Orphan modules → **B4** (but 7/8 verified as non-orphaned)

---

## Appendix B: Modification Prompts

Ready-to-use prompts for each action item. Each prompt is self-contained and
can be executed independently. Order matches the Phase 1/2/3 plan in §5.

---

### PROMPT 1.1: Delete 9 Verified DEAD Objects

```
Remove the following 9 verified dead objects from the BioETL codebase.
Each is a module-level constant or function with zero references anywhere
in production code or tests. Delete ONLY the object definition line(s);
do NOT remove surrounding code, imports, or other objects.

1. src/bioetl/infrastructure/adapters/http/circuit_breaker.py
   - Delete: `CIRCUIT_BREAKER_HELPERS = (is_circuit_breaker_error,)`
   - Location: last line of file (line ~235)
   - This is a 1-line tuple constant at EOF

2. src/bioetl/infrastructure/observability/metrics.py
   - Delete: the comment + constant (2 lines):
     ```
     # Expose for tooling to avoid false dead-code flags.
     METRICS_COLLECTOR = MetricsCollector
     ```
   - Location: last 2 lines of file (lines ~220-221)

3. src/bioetl/infrastructure/observability/logging.py
   - Delete: `LOGGING_API = (create_logger,)`
   - Location: line ~52 (between create_logger function and StructlogLogger class)
   - Leave a blank line between the function and the class after removal

4. src/bioetl/composition/bootstrap_logger.py
   - Delete: `BOOTSTRAP_LOGGER_EXPORTS = (BootstrapLogger, reset_bootstrap_logger)`
   - Location: line ~140 (between BootstrapLogger class and __all__ list)
   - Leave blank line between class and __all__ after removal

5. src/bioetl/interfaces/cli/exit_codes.py
   - Delete: `EXIT_CODE_HELPERS = (get_exit_code_for_exception,)`
   - Location: line ~120 (between get_exit_code_for_exception function and __all__ list)
   - Leave blank line between function and __all__ after removal

6. src/bioetl/interfaces/http/health_server.py
   - Delete: `RUN_HEALTH_SERVER = run_health_server`
   - Location: line ~305 (between run_health_server function and __all__ list)
   - Leave blank line between function and __all__ after removal

7. src/bioetl/application/pipelines/pubmed/xml_parser.py
   - Delete: `PARSER_HELPERS = (get_text, get_int)`
   - Location: last line of file (line ~79)

8. src/bioetl/application/core/entity_id.py
   - Delete: the entire function `compute_subcellular_fraction_entity_id`
     (lines ~36-51, including docstring)
   - This is the last function in the file; leave trailing newline

9. src/bioetl/domain/validation.py
   - Delete: `VALIDATION_API = (validate_publication_year, validate_inchi_key)`
   - Location: last line of file (line ~412)

Verification after changes:
  - Run `ruff check src/bioetl/` to ensure no broken imports
  - Run `pytest tests/architecture/ -v` to ensure no architecture violations
  - Run `pytest tests/ -x --timeout=60` to ensure no test regressions
  - Grep for each deleted name to confirm zero remaining references

Commit message:
  refactor: remove 9 verified dead objects (INV-20260213 §2.1)
```

---

### PROMPT 1.2: Rename CleanupResult → BronzeCleanupResult

```
Rename the `CleanupResult` class in the Bronze cleanup service to
`BronzeCleanupResult` to resolve a name collision with the core
`CleanupResult` class (which handles Silver/Gold cleanup).

Files to modify (3 files, ~5 changes):

1. src/bioetl/application/services/bronze_cleanup_service.py
   - Rename: `class CleanupResult:` → `class BronzeCleanupResult:`
   - Update all references within the file:
     - Method return type annotations: `-> CleanupResult` → `-> BronzeCleanupResult`
     - Constructor calls: `CleanupResult(` → `BronzeCleanupResult(`
     - Type hints in method parameters

2. src/bioetl/application/services/__init__.py
   - Update import: `from .bronze_cleanup_service import CleanupResult`
     → `from .bronze_cleanup_service import BronzeCleanupResult`
   - Update __all__: replace `"CleanupResult"` with `"BronzeCleanupResult"`
     in the __all__ list IF it appears there. If CleanupResult is NOT in
     __all__ of this module, then only update the import line.
   - IMPORTANT: Do NOT touch any import of CleanupResult from
     `application.core.cleanup_service` — that is the CORRECT class to keep.

3. src/bioetl/composition/_services.py (if references exist)
   - Update any TYPE_CHECKING import that imports CleanupResult from
     `application.services.bronze_cleanup_service`
   - Update return type annotations that reference the Bronze version

4. tests/unit/application/services/test_bronze_cleanup_service.py
   - Update import and all usages of CleanupResult → BronzeCleanupResult

DO NOT modify:
- src/bioetl/application/core/cleanup_service.py — the CORE CleanupResult stays
- src/bioetl/application/core/__init__.py — the core export stays
- Any file that imports CleanupResult from `application.core`

Verification:
  - `grep -rn "class CleanupResult" src/bioetl/` should show exactly 1 result
    (in core/cleanup_service.py)
  - `grep -rn "class BronzeCleanupResult" src/bioetl/` should show exactly 1 result
    (in services/bronze_cleanup_service.py)
  - `pytest tests/unit/application/services/test_bronze_cleanup_service.py -v`
  - `pytest tests/unit/application/core/test_cleanup_service.py -v`

Commit message:
  refactor: rename bronze CleanupResult → BronzeCleanupResult (INV-20260213 §3.2)
```

---

### PROMPT 1.3: Rename RateLimitConfig → RateLimitContext in Composition

```
Rename the `RateLimitConfig` class in composition/bootstrap_contexts.py
to `RateLimitContext` to resolve a name collision with the domain
`RateLimitConfig` class (which has validation logic and different fields).

Files to modify (3 production files + tests):

1. src/bioetl/composition/bootstrap_contexts.py
   - Rename: `class RateLimitConfig:` → `class RateLimitContext:`
   - Update the docstring if it references the old name
   - Update __all__ entry: `"RateLimitConfig"` → `"RateLimitContext"`

2. src/bioetl/composition/types.py
   - Update import: `from .bootstrap_contexts import RateLimitConfig`
     → `from .bootstrap_contexts import RateLimitContext`
   - Update __all__ entry: `"RateLimitConfig"` → `"RateLimitContext"`

3. src/bioetl/composition/providers/_config_helpers.py
   - Update import: `from ..bootstrap_contexts import RateLimitConfig`
     → `from ..bootstrap_contexts import RateLimitContext`
   - Update return type annotation of `_get_rate_limit_from_config()`:
     `-> RateLimitConfig` → `-> RateLimitContext`
   - Update constructor call: `RateLimitConfig(rate=..., capacity=...)`
     → `RateLimitContext(rate=..., capacity=...)`

4. tests/unit/composition/test_types.py
   - Update import and all usages of RateLimitConfig → RateLimitContext

DO NOT modify:
- src/bioetl/domain/configs/base.py — domain RateLimitConfig stays as is
- src/bioetl/domain/configs/__init__.py — domain export stays
- src/bioetl/domain/__init__.py — domain re-export stays
- Any file that imports RateLimitConfig from `bioetl.domain`

Verification:
  - `grep -rn "class RateLimitConfig" src/bioetl/` should show exactly 1 result
    (in domain/configs/base.py)
  - `grep -rn "class RateLimitContext" src/bioetl/` should show exactly 1 result
    (in composition/bootstrap_contexts.py)
  - `pytest tests/unit/composition/ -v`

Commit message:
  refactor: rename composition RateLimitConfig → RateLimitContext (INV-20260213 §3.2)
```

---

### PROMPT 1.4: Run Ruff Unused Import Check

```
Run ruff with unused import rules on the entire BioETL source tree
and fix any violations found.

Steps:

1. Run the linter:
   ruff check src/bioetl/ --select F401 --output-format=full

2. For each unused import found:
   - If the import is in an __init__.py and is a re-export:
     KEEP IT (add to __all__ if not already there, or add `# noqa: F401`)
   - If the import is genuinely unused: REMOVE the import line
   - If the import is used only under TYPE_CHECKING: move it there

3. Run again to confirm zero violations:
   ruff check src/bioetl/ --select F401

Verification:
  - `ruff check src/bioetl/ --select F401` returns 0 violations
  - `pytest tests/ -x --timeout=60` passes

Commit message:
  chore: remove unused imports (INV-20260213 §5, Phase 1.4)
```

---

### PROMPT 2.1: Verify Orphan Module — SubcellularFractionDataSource

```
Investigate whether `src/bioetl/application/core/subcellular_fraction_data_source.py`
is used in production code. It defines `SubcellularFractionDataSource` which
has a test file but no direct import found in src/.

Steps:

1. Search for any dynamic registration or factory creation:
   grep -rn "subcellular_fraction_data_source\|SubcellularFractionDataSource" src/bioetl/

2. Search for any string-based references (dynamic import / registry):
   grep -rn "subcellular.*data.*source\|SubcellularFraction" src/bioetl/composition/

3. Check if the chembl_subcellular_fraction pipeline creates this adapter:
   - Read src/bioetl/composition/factories/pipeline_factories.py
   - Search for "subcellular" in factory definitions

4. If NO production references are found:
   - This is TEST_ONLY code — consider if it should be:
     a) Moved to tests/fixtures/ (if only used in tests)
     b) Integrated into a pipeline factory (if it was intended to be used)
     c) Removed (if it's truly abandoned)
   - DO NOT remove without confirming with the team

5. If production references ARE found:
   - Document the reference chain
   - Mark as ACTIVE in the inventory

Report findings but do NOT delete the file without confirmation.
```

---

### PROMPT 2.2: Verify TEST_ONLY Objects

```
Verify whether the following objects are truly TEST_ONLY or are actually
used in production through indirect patterns (delegation, dynamic dispatch,
reflection). For each object, determine its correct classification.

Objects to verify:

1. `TransformerPort` in src/bioetl/application/core/protocols.py:49
   - Is this Protocol used as a type hint in any production code?
   - grep -rn "TransformerPort" src/bioetl/ (exclude tests/)

2. `PIPELINE_HEALTH_CHECK_PASSED` in infrastructure
   - Is this a Prometheus metric name used at runtime?
   - grep -rn "PIPELINE_HEALTH_CHECK_PASSED" src/bioetl/

3. `DataClassification` in src/bioetl/domain/types.py
   - Is this enum's .value used in string comparisons?
   - grep -rn "DataClassification\|data_classification" src/bioetl/

4. Domain validation functions (validate_smiles, validate_positive_int,
   validate_publication_year, etc.) in src/bioetl/domain/validation.py
   - Are these called via delegation in dict_transformers.py or other wrappers?
   - grep -rn "validate_smiles\|validate_positive_int\|validate_publication_year" src/bioetl/

For each object, report:
  - ACTIVE (used in production AND tests)
  - PRODUCTION_ONLY (used in production, not tested)
  - TEST_ONLY (confirmed: only referenced in tests/)
  - DEAD (zero references anywhere)

Do NOT modify any files. Report findings only.
```

---

### PROMPT 2.4: Set Up import-linter in CI

```
Set up import-linter to enforce ARCH-001 layer boundaries in CI.

Steps:

1. Add import-linter to dev dependencies:
   - Add `import-linter>=2.0` to pyproject.toml [project.optional-dependencies.dev]

2. Create .importlinter configuration in pyproject.toml:

   [tool.importlinter]
   root_packages = ["bioetl"]

   [[tool.importlinter.contracts]]
   name = "Domain layer must not import infrastructure"
   type = "forbidden"
   source_modules = ["bioetl.domain"]
   forbidden_modules = ["bioetl.infrastructure", "bioetl.composition", "bioetl.interfaces"]

   [[tool.importlinter.contracts]]
   name = "Application layer must not import infrastructure"
   type = "forbidden"
   source_modules = ["bioetl.application"]
   forbidden_modules = ["bioetl.infrastructure", "bioetl.composition", "bioetl.interfaces"]
   ignore_imports = ["bioetl.application.* -> bioetl.infrastructure.* (TYPE_CHECKING)"]

   [[tool.importlinter.contracts]]
   name = "Infrastructure must not import application or composition"
   type = "forbidden"
   source_modules = ["bioetl.infrastructure"]
   forbidden_modules = ["bioetl.application", "bioetl.composition", "bioetl.interfaces"]
   ignore_imports = ["bioetl.infrastructure.* -> bioetl.application.* (TYPE_CHECKING)"]

3. Run initial check:
   lint-imports

4. If violations are found, review each one:
   - If it's a TYPE_CHECKING import: add to ignore_imports
   - If it's a real violation: file a separate issue

5. Add to CI pipeline (Makefile or CI config):
   lint-imports

Commit message:
  ci: add import-linter for ARCH-001 enforcement (INV-20260213 §5, Phase 2.4)
```

---

### PROMPT 3.1: Review Cross-Provider Extractor Patterns (RF-INV-001)

```
Analyze the cross-provider extractor modules for potential consolidation
opportunities. Several publication providers (SemanticScholar, OpenAlex,
CrossRef, PubMed, ChEMBL) have extractors with similar function names.

The following function name pairs exist across providers:
  - extract_authors (semanticscholar ↔ openalex)
  - extract_author_orcids (semanticscholar ↔ openalex)
  - extract_affiliations (semanticscholar ↔ openalex)
  - extract_journal_info (semanticscholar ↔ openalex)
  - extract_external_ids (semanticscholar ↔ openalex)
  - extract_open_access_info (semanticscholar ↔ openalex)

For each pair:

1. Read both implementations side by side
2. Determine if the logic is:
   a) IDENTICAL — true copy-paste → candidate for shared base function
   b) SIMILAR STRUCTURE — same pattern, different API fields → candidate for
      parameterized base function with provider-specific field mappings
   c) DIFFERENT — same name but different logic → no action (correct as-is)

3. For cases (a) or (b), estimate:
   - LOC savings from consolidation
   - Risk of breaking provider-specific edge cases
   - Whether a shared `_extract_*` in `application/core/` is appropriate

Report findings with recommendations. Do NOT modify code without a plan
review. Each consolidated function must be tested against all providers.

Expected outcome: A decision document (not code changes) with one of:
  - "Consolidate X functions into application/core/publication_extractors.py"
  - "Keep separate — differences are provider-specific by design"
  - "Partial consolidation: merge A+B, keep C+D separate"
```

---

### PROMPT 3.2: Document Schema↔Domain Pair Convention (RF-INV-002)

```
Create an ADR (Architecture Decision Record) documenting the intentional
schema↔domain pair pattern used in BioETL.

File: docs/02-architecture/decisions/ADR-NNN-schema-domain-pairs.md

Content should cover:

1. Context:
   - BioETL uses frozen dataclasses in domain/ for configuration value objects
   - Infrastructure uses Pydantic models for YAML deserialization
   - Both layers define classes with the same name (e.g., DQConfig, BaseClientConfig)

2. Decision:
   - Domain classes are immutable value objects with business validation
   - Infrastructure Pydantic models are DTOs for deserialization only
   - Infrastructure models have `to_domain()` methods for conversion
   - This is NOT duplication — it's the Hexagonal Architecture boundary

3. Consequences:
   - Same-name classes exist across layers (intentional)
   - Changes to domain config require corresponding infrastructure schema update
   - New config objects must follow the pattern: Pydantic schema → to_domain() → frozen dataclass

4. Known pairs:
   - BaseClientConfig (domain/configs/base.py ↔ infrastructure/schemas/base_schemas.py)
   - CircuitBreakerConfig (domain/resilience.py ↔ infrastructure/schemas/pipeline_config.py)
   - DQConfig (domain/config/dq.py ↔ infrastructure/schemas/pipeline_config.py)
   - DQReportConfig (domain/config/dq.py ↔ infrastructure/schemas/pipeline_config.py)
   - InputFilterConfig (domain/filtering/ ↔ infrastructure/schemas/pipeline_config.py)

Determine the next ADR number by checking existing ADRs in docs/02-architecture/decisions/.

Commit message:
  docs: ADR for schema-domain pair convention (INV-20260213 §3.3, RF-INV-002)
```

---

### PROMPT 3.3: Review Facade Re-export Strategy (RF-INV-003)

```
Audit all __init__.py facade re-exports in BioETL and assess whether
the re-export strategy is consistent and minimal.

Steps:

1. List all __init__.py files with __all__ exports:
   grep -rn "__all__" src/bioetl/**/__init__.py

2. For each __init__.py with __all__:
   - Count total exports
   - Check if all exported names are actually importable
   - Check if any exported name is DEAD (not imported by anyone)
   - Check if important public objects are MISSING from __all__

3. Identify the largest facades (>20 exports) and evaluate:
   - Should they be split into sub-facades?
   - Are all exports truly part of the public API?
   - Is there a pattern (e.g., all Ports re-exported from domain.ports)?

4. Report inconsistencies:
   - Modules that export things NOT in __all__
   - Modules that have __all__ but it's incomplete
   - Modules that DON'T have __all__ but should

Expected outcome: A summary table of all facades with export counts
and recommendations. No code changes without review.
```
