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
| 1 | `src/bioetl/__main__.py` | 8 | **OK** — Python entry point, called via `python -m bioetl` |
| 2 | `src/bioetl/interfaces/cli/__main__.py` | 9 | **OK** — CLI entry point |
| 3 | `src/bioetl/interfaces/observability.py` | 19 | **REVIEW** — may be unused |
| 4 | `src/bioetl/infrastructure/storage/delta_writer.py` | 8 | **REVIEW** — may be a facade/re-export |
| 5 | `src/bioetl/composition/types.py` | 52 | **REVIEW** — check if types are imported elsewhere |
| 6 | `src/bioetl/composition/factories/storage_factory.py` | 341 | **REVIEW** — check if used in assembly |
| 7 | `src/bioetl/composition/factories/storage_adapter.py` | 652 | **REVIEW** — check if used in assembly |
| 8 | `src/bioetl/application/core/subcellular_fraction_data_source.py` | 297 | **REVIEW** — check if registered dynamically |

### 2.6 `__all__` Export Gaps

Source: B3 report (unique contribution).

| # | Module | Missing from `__all__` |
|---|--------|----------------------|
| 1 | `infrastructure.serialization.encoders` | `ORJSON_AVAILABLE` |
| 2 | `composition.factories.pipeline_factories` | `PIPELINE_CONFIGS` |
| 3 | `interfaces.cli.exit_codes` | `EXCEPTION_EXIT_CODES` |
| 4 | `application.pipelines.chembl.assay_parameters_transformer` | `KNOWN_PARAM_TYPES` |
| 5 | `application.core.field_specs` | `FLOAT`, `INT`, `PMID`, `STR` |
| 6 | `domain.composite.field_groups` | `DEFAULT_PROVIDER_ORDER` |
| 7 | `domain.schemas.column_order` | `ALL_SYSTEM_FIELDS`, `DQ_FIELDS_SUFFIX`, `SYSTEM_FIELDS_PREFIX` |
| 8 | `domain.schemas.constants` | 14 enum constants |
| 9 | `domain.value_objects.column_order` | `DEFAULT_COLUMN_ORDER`, `PUBLICATION_FIELD_GROUPS` |
| 10 | `domain.value_objects.publication_field_groups` | `DEFAULT_FIELD_GROUP_CONFIG`, `FIELD_TO_GROUP_MAPPING` |
| 11 | `domain.value_objects.column_qualifier` | `JOIN_KEY_COLUMNS` |

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
| 1.5 | Add missing `__all__` entries | §2.6 table | S | Complete exports |

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
- `__all__` gaps → **B3** (unique)
- Orphan modules → **B4** (unique)
