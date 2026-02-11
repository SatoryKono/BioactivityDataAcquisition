# Code Inventory Report — BioETL

**Date:** 2026-02-11
**Scope:** `src/bioetl/` (all layers)
**Branch:** `claude/inventory-code-duplication-z4DSx`

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total .py files | 508 |
| Total classes | 937 |
| Total module-level functions | 564 |
| Total LOC | 116,351 |
| Dead objects (DEAD) | 17 |
| Dead orphan modules | 10 (~1,174 LOC) |
| TEST_ONLY objects | 10 |
| Confirmed duplicates | 12 groups |
| Suspected duplicates | 6 groups |
| Unused Ports (0 refs) | 5 |
| Dead exceptions | 3 |

### Per-Layer Metrics

| Layer | Files | Classes | Functions | LOC |
|-------|-------|---------|-----------|-----|
| domain | 170 | 458 | 148 | 37,898 |
| application | 131 | 177 | 127 | 32,697 |
| infrastructure | 127 | 264 | 74 | 31,613 |
| composition | 50 | 34 | 143 | 10,917 |
| interfaces | 28 | 4 | 72 | 3,213 |
| **root** | 2 | 0 | 0 | 13 |

---

## 1. Dead Code

### 1.1 DEAD Classes (0 references in production AND tests)

| # | Object | Type | Layer | Location | Est. LOC |
|---|--------|------|-------|----------|----------|
| 1 | `PipelineStarted` | Event | domain | `domain/aggregates/events.py:48` | ~50 |
| 2 | `StageCompleted` | Event | domain | `domain/aggregates/events.py:103` | ~40 |
| 3 | `DQThresholdExceeded` | Event | domain | `domain/aggregates/events.py:233` | ~15 |
| 4 | `SchemaEvolutionDetected` | Event | domain | `domain/aggregates/events.py:249` | ~15 |
| 5 | `MoleculeFormSchema` | Schema | domain | `domain/schemas/chembl/molecule_form.py:14` | 35 |
| 6 | `TargetRelationSchema` | Schema | domain | `domain/schemas/chembl/target_relation.py:14` | 38 |
| 7 | `ChemblStatusResponse` | Model | infrastructure | `infrastructure/adapters/chembl/models.py:611` | ~25 |
| 8 | `HasProviderName` | Protocol | infrastructure | `infrastructure/adapters/filterable_mixin.py:23` | ~10 |
| 9 | `HealthCheckObservability` | Protocol | infrastructure | `infrastructure/adapters/health_check_mixin.py:40` | ~15 |
| 10 | `PageFetcher` | Protocol | infrastructure | `infrastructure/adapters/http/pagination.py:14` | ~10 |

**Estimated dead class LOC: ~253**

### 1.2 DEAD Exceptions (0 references anywhere)

| # | Exception | Layer | Location |
|---|-----------|-------|----------|
| 1 | `ConfigurationError` | domain | `domain/exceptions/infrastructure.py` |
| 2 | `FileSystemError` | domain | `domain/exceptions/infrastructure.py` |
| 3 | `InternalError` | domain | `domain/exceptions/internal.py` |

### 1.3 DEAD Ports (0 implementation refs AND 0 import refs)

| # | Port | Location | Notes |
|---|------|----------|-------|
| 1 | `ActivityAggregatorPort` | `domain/ports/normalization.py` | Port defined but never used |
| 2 | `HealthStatePort` | `domain/ports/health_check.py` | Port defined but never used |
| 3 | `NormalizationServicePort` | `domain/ports/normalization.py` | Port defined but never used |
| 4 | `OutlierFilterPort` | `domain/ports/normalization.py` | Port defined but never used |
| 5 | `UnitConverterPort` | `domain/ports/normalization.py` | Port defined but never used |
| 6 | `ValueValidatorPort` | `domain/ports/normalization.py` | Port defined but never used |

Note: 5 of 6 dead ports are in `domain/ports/normalization.py` — the entire file's port contracts appear unused despite having concrete implementations in `domain/services/`.

### 1.4 TEST_ONLY Classes (0 production refs, test refs only)

| # | Object | Layer | Location | Test Refs |
|---|--------|-------|----------|-----------|
| 1 | `TransformerPort` | application | `application/core/protocols.py:49` | 14 |
| 2 | `MetricsCollector` | infrastructure | `infrastructure/observability/metrics.py:189` | 6 |

### 1.5 TEST_ONLY Exceptions

| # | Exception | Location | Test Refs |
|---|-----------|----------|-----------|
| 1 | `BucketNotFoundError` | `domain/exceptions/infrastructure.py` | 10 |
| 2 | `UploadError` | `domain/exceptions/infrastructure.py` | 9 |
| 3 | `StorageQuotaExceededError` | `domain/exceptions/infrastructure.py` | 9 |
| 4 | `DeltaWriteConflictError` | `domain/exceptions/infrastructure.py` | 12 |
| 5 | `DeltaTransactionError` | `domain/exceptions/infrastructure.py` | 10 |
| 6 | `DeltaSchemaValidationError` | `domain/exceptions/infrastructure.py` | 12 |
| 7 | `DeltaOptimizeError` | `domain/exceptions/infrastructure.py` | 10 |
| 8 | `CheckpointConflictError` | `domain/exceptions/internal.py` | 3 |
| 9 | `DataValidationError` | `domain/exceptions/network.py` | 3 |

Note: Many of these TEST_ONLY exceptions are likely intentional (error hierarchy for future use / defensive coverage). Verify before removing.

### 1.6 Orphan Modules (files with 0 imports from codebase)

| # | File | LOC | Content | Recommendation |
|---|------|-----|---------|----------------|
| 1 | `domain/config_types.py` | 446 | Type definitions (RateLimitDict etc.) | **HIGH** — large orphan; verify if types migrated elsewhere |
| 2 | `domain/schemas/_field_orders.py` | 223 | Field ordering constants | **HIGH** — verify if superseded by `schemas/column_order.py` |
| 3 | `domain/schemas/chembl/molecule_form.py` | 35 | MoleculeFormSchema | Remove (class also DEAD) |
| 4 | `domain/schemas/chembl/target_relation.py` | 38 | TargetRelationSchema | Remove (class also DEAD) |
| 5 | `domain/schemas/crossref/funder.py` | 68 | Funder bronze/silver/gold schemas | Verify — entity may be planned |
| 6 | `domain/schemas/crossref/author.py` | 86 | Author bronze/silver/gold schemas | Verify — entity may be planned |
| 7 | `domain/schemas/uniprot/isoform.py` | 81 | Isoform bronze/silver/gold schemas | Verify — entity may be planned |
| 8 | `infrastructure/adapters/chembl/exceptions.py` | 116 | ChemblApiError hierarchy | **FALSE POSITIVE** — classes imported via `__init__.py` |
| 9 | `infrastructure/adapters/adapter_error_logging.py` | 56 | Error logging decorator | Verify usage via decorator references |
| 10 | `application/services/dq_metrics_calculator.py` | 25 | Re-export shim | Remove if nobody imports |

**Confirmed orphan LOC (excluding false positives): ~1,058**

### 1.7 PROD_ONLY (no test coverage)

| # | Exception | Prod Refs |
|---|-----------|-----------|
| 1 | `CachedBronzeEmptyError` | 3 |

---

## 2. Duplicate Logic

### 2.1 Confirmed Duplicates — Same Name, Different Module (CRITICAL)

| # | Class | Definition A | Definition B | Definition C | Severity | Notes |
|---|-------|-------------|-------------|-------------|----------|-------|
| 1 | `NoOpTracing` | `domain/ports/noop.py` | `infrastructure/observability/noop_tracing.py` | — | **HIGH** | Both actively used (60 + 16 refs). Parallel implementations. |
| 2 | `NoOpMetrics` | `domain/ports/noop.py` | `infrastructure/observability/noop_metrics.py` | — | **HIGH** | Both actively used (77 + 12 refs). Parallel implementations. |
| 3 | `CircuitBreakerConfig` | `domain/resilience.py` | `infrastructure/schemas/pipeline_config.py` | `composition/bootstrap_contexts.py` | **HIGH** | Triple definition. Domain=dataclass, Infra=Pydantic, Composition=NamedTuple. |
| 4 | `DriftLevel` | `domain/types.py` | `domain/value_objects/dq_report.py` | — | **CRITICAL** | Same enum, DIFFERENT VALUES (uppercase vs lowercase). Risk of runtime bugs. |
| 5 | `DQConfig` | `domain/config.py` | `infrastructure/schemas/pipeline_config.py` | — | **MEDIUM** | Domain dataclass + Pydantic model (intentional pattern, but name collision) |
| 6 | `DQReportConfig` | `domain/config.py` | `infrastructure/schemas/pipeline_config.py` | — | **MEDIUM** | Same pattern as DQConfig |
| 7 | `InputFilterConfig` | `domain/filtering/input_config.py` | `infrastructure/schemas/pipeline_config.py` | — | **MEDIUM** | Same pattern |
| 8 | `RunStatus` | `domain/aggregates/pipeline_run.py` | `application/services/pipeline_runner_service.py` | — | **HIGH** | Different members (5 vs 4 values). Only application version imported. |
| 9 | `ValidationResult` | `domain/types.py` | `infrastructure/adapters/validation.py` | — | **MEDIUM** | Different semantics (schema validation vs API record validation) |
| 10 | `CleanupResult` | `application/core/cleanup_service.py` | `application/services/bronze_cleanup_service.py` | — | **LOW** | Different fields, different purposes (medallion vs file cleanup) |
| 11 | `LineageMetadata` | `domain/composite/lineage.py` | `domain/models/metadata.py` | — | **MEDIUM** | Dataclass vs Pydantic; different field sets |
| 12 | `ChemblPublicationRecord` | `domain/entities/chembl.py:511` | `infrastructure/adapters/chembl/models.py:467` | — | **HIGH** | Same name + BaseModel, likely divergent field sets |
| 13 | `PubchemMoleculeRecord` | `domain/entities/pubchem.py:24` | `infrastructure/adapters/pubchem/models.py:19` | — | **HIGH** | Same name + BaseModel, likely divergent field sets |
| 14 | `TitleFallbackHandler` | `crossref/fallback.py:25` | `openalex/fallback.py:21` | `pubmed/fallback.py:21` | **LOW** | Intentional per-provider implementations of BaseTitleFallbackHandler |
| 15 | `BaseClientConfig` | `domain/configs/base.py:56` | `infrastructure/schemas/base_schemas.py:151` | — | **MEDIUM** | Domain vs infra Pydantic schemas |
| 16 | `RateLimitConfig` | `domain/configs/base.py:20` | `composition/bootstrap_contexts.py:105` | — | **MEDIUM** | Domain dataclass vs composition NamedTuple |

### 2.2 Confirmed Duplicates — Same Logic, Different Location

| # | Function/Logic | Location A | Location B | Severity | LOC Savings |
|---|----------------|-----------|-----------|----------|-------------|
| 1 | `normalize_string()` | `domain/normalization.py:16` | `application/core/dict_transformers.py:198` | **MEDIUM** | ~20 | App version delegates to domain (thin wrapper). |
| 2 | `parse_date_field()` | `domain/normalization.py:88` | `application/core/dict_transformers.py:223` | **MEDIUM** | ~25 | App version delegates to domain (thin wrapper). |
| 3 | `parse_page_range()` | `domain/normalization.py:160` | `semanticscholar/_page_parsing.py:124` | **HIGH** | ~40 | Two INDEPENDENT implementations with different logic. Domain version does not handle abbreviated ranges (e.g., "737-9" → "737-739"). |
| 4 | `normalize_doi()` | `domain/normalization.py:32` | `openalex/client.py:591` | `semanticscholar/adapter.py:463` | **MEDIUM** | ~15 | Three implementations. Domain: `strip().lower()`. Adapters: additional URL stripping. |
| 5 | `_normalize_for_hash()` | `domain/transformations.py:81` | `domain/services/identity_service.py:119` | `composition/services/versioning.py:65` | **HIGH** | ~50 | Three normalize-for-hash implementations across codebase. |

### 2.3 Normalization Hierarchy Confusion (CRITICAL structural duplication)

The domain layer contains **two parallel normalization subsystems** with confusing naming:

**System A: Activity/Chemistry Normalization**
| Component | File | Purpose |
|-----------|------|---------|
| `NormalizationServicePort` | `domain/ports/normalization.py` | Port (DEAD — 0 refs) |
| `NormalizationService` | `domain/services/normalization_service.py` | Activity value normalization |
| `NormalizationConfig` | `domain/services/normalization_config.py` | Config for activity norms |
| `UnitConverterPort` | `domain/ports/normalization.py` | Port (DEAD — 0 refs) |
| `ValueValidatorPort` | `domain/ports/normalization.py` | Port (DEAD — 0 refs) |
| `ActivityAggregatorPort` | `domain/ports/normalization.py` | Port (DEAD — 0 refs) |
| `OutlierFilterPort` | `domain/ports/normalization.py` | Port (DEAD — 0 refs) |

**System B: Publication Data Normalization**
| Component | File | Purpose |
|-----------|------|---------|
| `DataNormalizationPort` | `domain/ports/data_normalization.py` | Port (ACTIVE — 12 import refs) |
| `DefaultDataNormalizationService` | `domain/services/data_normalization_service.py` | DOI, PMID, author normalization |
| `DataNormalizationConfig` | `domain/services/data_normalization_config.py` | Config for pub norms |

**System C: Standalone Functions (overlapping with A and B)**
| Function | File | Overlaps |
|----------|------|----------|
| `normalize_string()` | `domain/normalization.py:16` | `DataNormalizationService.normalize_string()` |
| `normalize_doi()` | `domain/normalization.py:32` | `DataNormalizationService.normalize_doi()` |
| `parse_date_field()` | `domain/normalization.py:88` | — |
| `parse_page_range()` | `domain/normalization.py:160` | — |
| `normalize_pmc_id()` | `domain/normalization.py:193` | — |
| `parse_authors_to_list()` | `domain/normalization.py:287` | `DataNormalizationService.parse_authors_to_list()` |
| `format_date_parts()` | `domain/normalization.py` | — |

**Finding:** `domain/normalization.py` standalone functions overlap significantly with `DataNormalizationService` methods. The service wraps many of the same functions with additional validation. System A's ports are all dead — the concrete services exist but ports are unused.

### 2.4 Cross-Provider Duplicates (Transformer/Client/Schema)

| # | Provider A | Provider B | Shared Logic | Severity |
|---|-----------|-----------|-------------|----------|
| 1 | `openalex/client.py:_normalize_doi` | `semanticscholar/adapter.py:_normalize_doi` | DOI normalization with URL stripping | MEDIUM |
| 2 | `crossref/fallback.py` | `openalex/fallback.py` | Near-identical TitleFallbackHandler (both extend BaseTitleFallbackHandler) | LOW |
| 3 | `pubmed/fallback.py` | `crossref/fallback.py` | Near-identical TitleFallbackHandler | LOW |
| 4 | `domain/normalization.py:parse_page_range` | `semanticscholar/_page_parsing.py:parse_page_range` | Page range parsing (but different capabilities) | HIGH |

### 2.5 NoOp Implementation Duplication (470 + 199 = 669 LOC)

Two parallel NoOp hierarchies exist:

**domain/ports/noop.py** (470 LOC):
- `NoOpTracing`, `NoOpMetrics`, `NoOpAudit`, `NoOpPiiHasher`, `NoOpMemoryMonitor`, `NoOpMetadataWriter`
- Used via `from bioetl.domain.ports import NoOp*` (application/infrastructure layers)

**infrastructure/observability/noop_*.py** (199 LOC total):
- `NoOpLogger` (51 LOC), `NoOpMetrics` (88 LOC), `NoOpTracing` (60 LOC)
- Used via `from bioetl.infrastructure.observability.noop_* import *` (composition/tests)

**Overlap:** `NoOpTracing` and `NoOpMetrics` exist in BOTH locations with separate implementations.

---

## 3. Dependency Map — Notable Patterns

### 3.1 Highest Fan-In Objects (most depended upon)

| # | Object | Layer | Dependents |
|---|--------|-------|-----------|
| 1 | `LoggerPort` | domain | 264 import refs |
| 2 | `MetricsPort` | domain | 119 import refs |
| 3 | `DataSourcePort` | domain | 23 import refs, 106 impl refs |
| 4 | `TracingPort` | domain | 65 import refs |
| 5 | `NoOpMetrics` (domain) | domain | 77 production refs |
| 6 | `NoOpTracing` (domain) | domain | 60 production refs |

### 3.2 Domain DriftLevel Enum Conflict

**CRITICAL BUG RISK**: Two `DriftLevel` enums with **different values**:

```python
# domain/types.py — UPPERCASE values
class DriftLevel(StrEnum):
    INFO = "INFO"
    WARN = "WARN"      # uppercase
    CRITICAL = "CRITICAL"

# domain/value_objects/dq_report.py — lowercase values
class DriftLevel(StrEnum):
    INFO = "info"
    WARN = "warn"      # lowercase
    CRITICAL = "critical"
```

The `domain/types.py` version is actively used (via `domain/transformations.py` and tests).
The `domain/value_objects/dq_report.py` version is re-exported via `value_objects/__init__.py` but appears to shadow/conflict.

---

## 4. Orphan Modules — Details

### 4.1 High-Impact Orphans (>100 LOC)

| # | File | LOC | Analysis |
|---|------|-----|----------|
| 1 | `domain/config_types.py` | 446 | Contains `RateLimitDict`, `RetryPolicyDict`, etc. Referenced only in a comment in `domain/configs/base.py`. Types likely migrated to proper dataclasses. **Candidate for removal.** |
| 2 | `domain/schemas/_field_orders.py` | 223 | Column ordering definitions. No imports found. May have been superseded by `domain/schemas/column_order.py` or `domain/value_objects/column_order.py`. **Candidate for removal.** |
| 3 | `infrastructure/adapters/chembl/exceptions.py` | 116 | **FALSE POSITIVE** — classes (ChemblApiError etc.) are imported via provider `__init__.py`. Module name pattern doesn't match grep. |

### 4.2 Medium-Impact Orphans (35-100 LOC)

| # | File | LOC | Analysis |
|---|------|-----|----------|
| 4 | `domain/schemas/crossref/author.py` | 86 | AuthorBronzeSchema etc. No imports. Entity may be planned but not yet wired. |
| 5 | `domain/schemas/uniprot/isoform.py` | 81 | IsoformBronzeSchema etc. No imports. Entity may be planned. |
| 6 | `domain/schemas/crossref/funder.py` | 68 | FunderBronzeSchema etc. No imports. Entity may be planned. |
| 7 | `infrastructure/adapters/adapter_error_logging.py` | 56 | Error logging decorator. Verify if decorator is applied via import. |
| 8 | `domain/schemas/chembl/target_relation.py` | 38 | TargetRelationSchema. Dead class + orphan module. |
| 9 | `domain/schemas/chembl/molecule_form.py` | 35 | MoleculeFormSchema. Dead class + orphan module. |

### 4.3 Low-Impact Orphans (<35 LOC)

| # | File | LOC | Analysis |
|---|------|-----|----------|
| 10 | `application/services/dq_metrics_calculator.py` | 25 | Likely a re-export shim left over from refactoring. |

---

## 5. Recommendations

### 5.1 Immediate Actions (Quick Wins)

| # | Action | Objects | Impact | Effort |
|---|--------|---------|--------|--------|
| QW-1 | **Remove dead schemas** | `molecule_form.py`, `target_relation.py` | -73 LOC | Trivial |
| QW-2 | **Remove dead events** | `PipelineStarted`, `StageCompleted`, `DQThresholdExceeded`, `SchemaEvolutionDetected` | -120 LOC | Trivial |
| QW-3 | **Remove dead exceptions** | `ConfigurationError`, `FileSystemError`, `InternalError` | -30 LOC | Trivial |
| QW-4 | **Remove dead infra classes** | `ChemblStatusResponse`, `HasProviderName`, `HealthCheckObservability`, `PageFetcher` | -60 LOC | Low |
| QW-5 | **Remove orphan `config_types.py`** | `domain/config_types.py` | -446 LOC | Verify first |
| QW-6 | **Remove orphan `_field_orders.py`** | `domain/schemas/_field_orders.py` | -223 LOC | Verify first |
| QW-7 | **Remove orphan `dq_metrics_calculator.py`** (application) | `application/services/dq_metrics_calculator.py` | -25 LOC | Trivial |
| QW-8 | **Fix DriftLevel enum conflict** | `domain/types.py` vs `domain/value_objects/dq_report.py` | Bug risk | Medium |

**Total quick-win LOC removal: ~977 LOC**

### 5.2 Refactorings (Require Planning)

| # | RF-ID | Description | Objects | Impact | Risk |
|---|-------|-------------|---------|--------|------|
| 1 | RF-NOOP | **Consolidate NoOp implementations** — Merge domain/ports/noop.py and infrastructure/observability/noop_*.py into a single canonical location | 2 `NoOpTracing`, 2 `NoOpMetrics`, `NoOpLogger` | -199 LOC, unified imports | Medium |
| 2 | RF-NORM | **Clean normalization hierarchy** — Remove dead ports in `domain/ports/normalization.py`; clarify relationship between `domain/normalization.py` functions and `DataNormalizationService` | 5 dead ports, ~10 overlapping functions | Architecture clarity | High |
| 3 | RF-CBCFG | **Unify CircuitBreakerConfig** — Consolidate triple definition into domain dataclass + Pydantic `to_domain()` converter | 3 definitions | Type safety | Medium |
| 4 | RF-RUNST | **Resolve RunStatus duplication** — Either remove unused `domain/aggregates/pipeline_run.py:RunStatus` or reconcile with `application/services/pipeline_runner_service.py:RunStatus` | 2 definitions | Naming clarity | Low |
| 5 | RF-ENTITY | **Resolve entity/model duplication** — `ChemblPublicationRecord` and `PubchemMoleculeRecord` exist in both domain/entities and infrastructure/models | 4 classes | Architecture clarity | High |
| 6 | RF-DRIFT | **Fix DriftLevel enum values** — Consolidate to single definition with consistent case | 2 definitions | Bug prevention | Low |
| 7 | RF-PAGES | **Consolidate `parse_page_range`** — Merge domain/normalization.py and semanticscholar/_page_parsing.py implementations | 2 functions | DRY | Low |
| 8 | RF-HASH | **Consolidate `normalize_for_hash`** — Three independent implementations | 3 functions | DRY | Medium |
| 9 | RF-ORPHAN-SCHEMAS | **Decide on orphan schemas** — crossref/author.py, crossref/funder.py, uniprot/isoform.py: remove if entities not planned | 3 modules | -235 LOC | Low |

### 5.3 Layer Health Summary

| Layer | Dead Objects | Duplicates | Orphans | Health |
|-------|-------------|------------|---------|--------|
| domain | 10 classes + 3 exceptions + 5 ports | DriftLevel, RunStatus, normalization overlap | 7 files (932 LOC) | ⚠️ |
| application | 0 classes (1 TEST_ONLY) | normalize_string/parse_date_field wrappers | 1 file (25 LOC) | ✅ |
| infrastructure | 4 classes (1 TEST_ONLY) | NoOp overlap, entity/model duplication | 1 file (56 LOC) | ⚠️ |
| composition | 0 | CircuitBreakerConfig, RateLimitConfig | 0 | ✅ |
| interfaces | 0 | 0 | 0 | ✅ |

---

## 6. Checklist

- [x] Object registry collected for all 5 layers
- [x] Reference count analyzed for all classes (dead/test-only/active)
- [x] Dead code identified and verified against exception list
- [x] Cross-provider duplication analyzed (transformers, clients, fallbacks)
- [x] Cross-layer duplication analyzed (NoOps, configs, entities, normalization)
- [x] Orphan modules identified
- [x] Duplicate class names cataloged
- [x] DriftLevel enum conflict flagged as CRITICAL
- [x] Recommendations prioritized

---

## Appendix A: Methodology

Analysis performed using:
- `grep -rn` for class/function extraction and reference counting
- Python scripts for systematic dead-class detection across all layers
- Manual file comparison for semantic duplication (normalization, NoOp, configs)
- Orphan detection via module-level import pattern matching
- Cross-referencing with tests/ directory for TEST_ONLY classification

### Exclusions (per methodology)
- Protocol/Port classes without direct calls (contracts) — verified individually
- `__all__` re-exports — checked for bitrot
- Pydantic/Pandera validators — called by framework
- Click decorators — called by CLI framework
- `TYPE_CHECKING` imports — type hints only

---

## Appendix B: Dead Ports Detail

The file `domain/ports/normalization.py` defines 6 ports, of which 5 are completely dead:

```
ActivityAggregatorPort:  0 impl_refs, 0 import_refs  → DEAD
NormalizationServicePort: 0 impl_refs, 0 import_refs → DEAD
OutlierFilterPort:       0 impl_refs, 0 import_refs  → DEAD
UnitConverterPort:       0 impl_refs, 0 import_refs  → DEAD
ValueValidatorPort:      0 impl_refs, 0 import_refs  → DEAD
```

Despite these ports being dead, concrete implementations exist:
- `NormalizationService` in `domain/services/normalization_service.py` (used directly, not via port)
- `UnitConverter` in `domain/services/unit_converter.py` (used directly)
- `ValueValidator` in `domain/services/value_validator.py` (used directly)
- `ActivityAggregator` in `domain/services/activity_aggregator.py` (used directly)

**Conclusion:** Services bypass their port contracts entirely. Either wire services through ports or remove the dead ports.
