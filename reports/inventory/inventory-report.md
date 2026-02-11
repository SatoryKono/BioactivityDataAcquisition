# Code Inventory Report — BioETL

**Date:** 2026-02-11
**Scope:** `src/bioetl/` (all layers)
**Branch:** `claude/inventory-duplicate-detection-k8gol`
**Base:** `main` @ `3ba7aea` (rebased)
**Version:** 2.2 (synced with main; +doc-code drift finding)

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total .py files | 492 |
| Total classes | 876 |
| Total module-level functions | 561 |
| Total LOC | 113,887 |
| Dead objects (DEAD) | 16 classes + 3 value objects + 3 exceptions + 6 ports = **28** |
| Dead orphan modules | 10 (~1,058 LOC) |
| TEST_ONLY objects | 12 value objects + 7 domain services + 2 classes + 9 exceptions = **30** |
| Confirmed duplicates (same name) | 15 groups (was 16; DriftLevel **resolved on main**) |
| Confirmed duplicates (same logic) | 5 groups |
| Duplicate constants | 6 groups |
| Suspected duplicates | 4 groups |
| Exception hierarchy fragmentation | 8 exceptions outside BioETLError |
| Doc-code drift (NEW) | 1 finding — DriftLevel WARN level removed from RULES.md but still in code |

### Per-Layer Metrics

| Layer | Files | Classes | Functions | LOC |
|-------|-------|---------|-----------|-----|
| domain | 161 | 412 | 155 | 36,229 |
| application | 128 | 174 | 123 | 32,524 |
| infrastructure | 123 | 253 | 70 | 31,044 |
| composition | 50 | 33 | 141 | 10,860 |
| interfaces | 28 | 4 | 72 | 3,217 |
| **root** | 2 | 0 | 0 | 13 |

---

## 0. Main Branch Delta (sync with `3ba7aea`)

This report is rebased on `main` @ `3ba7aea`. Changes on main since the initial analysis:

### Sync 1: `7e265aa` (path updates)

| Commit | Files Changed | Impact on Inventory |
|--------|--------------|---------------------|
| `0ef246a` | 4 src files + 1 test file | **Cosmetic only**: example paths updated `/data/bronze/` → `/data/output/bronze/` in docstrings. |
| `7e265aa` | Same as above | Same batch of path updates. |

### Sync 2: `3ba7aea` (docs overhaul, RULES.md drift level change)

| Commit | Files Changed | Impact on Inventory |
|--------|--------------|---------------------|
| `29fccea` | `docs/00-project/RULES.md` | **RULES.md §2.2 Schema Drift Policy changed**: removed `Warn` level. Now only `Info` and `Critical`. **NEW DOC-CODE DRIFT** — code still has 3 levels. |
| `78ddff1` | 30+ docs files | Docs-only: fixed paths, CLI flags, exit codes, versions, API references. |
| `db46861` | 6 docs + 1 config | Docs-only: documentation discrepancies. `configs/pipelines/composite/target.yaml` — added comments (no logic change). |
| `87f9fd8` .. `2c2f407` | `docs/audits/` | New documentation audit reports. No code impact. |

### Already Resolved on Main

| Finding | Original Severity | Resolution |
|---------|------------------|------------|
| **DriftLevel enum conflict** (§2.1 #4, QW-8, RF-DRIFT) | CRITICAL | `dq_report.py` now imports `DriftLevel` from `domain/types.py` instead of defining a duplicate with different values |

### New Finding from Main Changes

| Finding | Severity | Detail |
|---------|----------|--------|
| **DriftLevel WARN doc-code drift** (NEW) | HIGH | RULES.md §2.2 removed `Warn` level (only Info + Critical remain), but code still defines and uses `DriftLevel.WARN` in `domain/types.py:85` and `domain/transformations.py:144` with ">3 new fields" threshold. Either restore `Warn` in RULES.md or remove `WARN` from code and adjust `detect_schema_drift()`. See §3.2a below. |

### Confirmed Unchanged

All other findings verified against rebased state:
- Dead classes/VOs/exceptions/ports: **unchanged** (still dead)
- TEST_ONLY services/VOs: **unchanged** (still test-only)
- Duplicate constants: **unchanged** (still duplicated)
- Orphan modules: **unchanged** (still orphaned)
- Exception hierarchy fragmentation: **unchanged** (still 8 orphan exceptions)
- LOOKUP_METHODS inconsistency: **unchanged** (still 4 vs 6 values)
- Production code (`src/bioetl/`): **zero changes** between `7e265aa` and `3ba7aea`

**Actionable remaining items: 14 quick wins (13 original + QW-15) + 11 refactorings** (was 14 + 12 before DriftLevel resolution; +1 new doc-code drift finding QW-15).

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

### 1.2 DEAD Value Objects (0 references outside own file + `__init__.py`)

| # | Object | Layer | Location | Notes |
|---|--------|-------|----------|-------|
| 1 | `BaseDQReport` | domain | `domain/value_objects/dq_report.py:489` | Only in `__all__`, never imported/used |
| 2 | `DQCheckResult` | domain | `domain/value_objects/dq_report.py:107` | Only in `__all__`, never imported/used |
| 3 | `FieldPresenceResult` | domain | `domain/value_objects/dq_report.py:179` | Only in `__all__`, never imported/used |

### 1.3 DEAD Entity

| # | Object | Layer | Location | Notes |
|---|--------|-------|----------|-------|
| 1 | `OpenAlexPublicationRecord` | domain | `domain/entities/openalex.py:24` | DTO model, 0 refs outside own file |

### 1.4 DEAD Exceptions (0 references anywhere)

| # | Exception | Layer | Location |
|---|-----------|-------|----------|
| 1 | `ConfigurationError` | domain | `domain/exceptions/infrastructure.py` |
| 2 | `FileSystemError` | domain | `domain/exceptions/infrastructure.py` |
| 3 | `InternalError` | domain | `domain/exceptions/internal.py` |

### 1.5 DEAD Ports (0 implementation refs AND 0 import refs)

| # | Port | Location | Notes |
|---|------|----------|-------|
| 1 | `ActivityAggregatorPort` | `domain/ports/normalization.py` | Port defined but never used |
| 2 | `HealthStatePort` | `domain/ports/health_check.py` | Used only as return type in `HealthMonitorPort.get_all_states()` |
| 3 | `NormalizationServicePort` | `domain/ports/normalization.py` | Port defined but never used |
| 4 | `OutlierFilterPort` | `domain/ports/normalization.py` | Port defined but never used |
| 5 | `UnitConverterPort` | `domain/ports/normalization.py` | Port defined but never used |
| 6 | `ValueValidatorPort` | `domain/ports/normalization.py` | Port defined but never used |

Note: 5 of 6 dead ports are in `domain/ports/normalization.py` — the entire file's port contracts appear unused despite having concrete implementations in `domain/services/`.

### 1.6 TEST_ONLY Value Objects (0 production refs, test refs only)

| # | Object | Layer | Location | Test Refs |
|---|--------|-------|----------|-----------|
| 1 | `ActivityValue` | domain | `domain/value_objects/activity.py` | 31 |
| 2 | `AssayId` | domain | `domain/value_objects/assay_id.py` | 30 |
| 3 | `ColumnStats` | domain | `domain/value_objects/dq_report.py` | 15 |
| 4 | `CompoundId` | domain | `domain/value_objects/compound_ids.py` | 41 |
| 5 | `CompoundSource` | domain | `domain/value_objects/compound_ids.py` | 13 |
| 6 | `ConfidenceScore` | domain | `domain/value_objects/confidence.py` | 40 |
| 7 | `FieldGroupConfig` | domain | `domain/value_objects/publication_field_groups.py` | 23 |
| 8 | `OpenAlexId` | domain | `domain/value_objects/provider_ids.py` | 36 |
| 9 | `RelationOperator` | domain | `domain/value_objects/activity.py` | 51 |
| 10 | `SemanticScholarId` | domain | `domain/value_objects/provider_ids.py` | 30 |

Note: These value objects have implementations and tests but are not integrated into production pipelines. They may be planned for future use or represent an incomplete integration.

### 1.7 TEST_ONLY Domain Services (0 production refs outside domain/services/)

| # | Object | Layer | Location | Test Refs |
|---|--------|-------|----------|-----------|
| 1 | `ActivityAggregator` | domain | `domain/services/activity_aggregator.py` | 50 |
| 2 | `AggregationMethod` | domain | `domain/services/activity_aggregator.py` | 12 |
| 3 | `ConcentrationRangeConfig` | domain | `domain/services/value_validator.py` | 8 |
| 4 | `NormalizationResult` | domain | `domain/services/normalization_service.py` | 8 |
| 5 | `PChemblRangeConfig` | domain | `domain/services/value_validator.py` | 10 |
| 6 | `UnitConverter` | domain | `domain/services/unit_converter.py` | 35 |
| 7 | `ValueValidator` | domain | `domain/services/value_validator.py` | 48 |

Note: These services are tested but their dead ports (§1.5) are never used — the services themselves are never injected into application-layer pipelines. Likely an incomplete "activity normalization" feature.

### 1.8 TEST_ONLY Classes

| # | Object | Layer | Location | Test Refs |
|---|--------|-------|----------|-----------|
| 1 | `TransformerPort` | application | `application/core/protocols.py:49` | 14 |
| 2 | `MetricsCollector` | infrastructure | `infrastructure/observability/metrics.py:189` | 6 |

### 1.9 TEST_ONLY Exceptions

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

### 1.10 Orphan Modules (files with 0 imports from codebase)

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

### 1.11 PROD_ONLY (no test coverage)

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
| 4 | ~~`DriftLevel`~~ | ~~`domain/types.py`~~ | ~~`domain/value_objects/dq_report.py`~~ | — | ~~CRITICAL~~ **RESOLVED** | Fixed on `main` (`7e265aa`): `dq_report.py` now imports from `domain/types.py`. |
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
| 15 | `BaseClientConfig` | `domain/configs/base.py:56` | `infrastructure/schemas/base_schemas.py:151` | — | **MEDIUM** | Domain dataclass vs infra Pydantic. Same name, different field sets. |
| 16 | `RateLimitConfig` | `domain/configs/base.py:20` | `composition/bootstrap_contexts.py:105` | — | **MEDIUM** | Domain dataclass vs composition NamedTuple. Same defaults (5.0 rps, burst=10). |

### 2.2 Confirmed Duplicates — Same Logic, Different Location

| # | Function/Logic | Location A | Location B | Location C | Severity | LOC Savings |
|---|----------------|-----------|-----------|-----------|----------|-------------|
| 1 | `normalize_string()` | `domain/normalization.py:16` | `application/core/dict_transformers.py:198` | `domain/services/data_normalization_service.py:132` | **MEDIUM** | ~20. App delegates to domain; service is independent copy. |
| 2 | `parse_date_field()` | `domain/normalization.py:88` | `application/core/dict_transformers.py:223` | — | **MEDIUM** | ~25. App delegates to domain (thin wrapper). |
| 3 | `parse_page_range()` | `domain/normalization.py:160` | `semanticscholar/_page_parsing.py:124` | — | **HIGH** | ~40. Two INDEPENDENT implementations with different logic. |
| 4 | `normalize_doi()` | `domain/normalization.py:32` | `openalex/client.py:591` | `semanticscholar/adapter.py:463` | **MEDIUM** | ~15. Three implementations. Domain: `strip().lower()`. Adapters: additional URL stripping. |
| 5 | `_normalize_for_hash()` | `domain/transformations.py:81` | `domain/services/identity_service.py:119` | `composition/services/versioning.py:65` | **HIGH** | ~50. Three normalize-for-hash implementations. |

### 2.3 Duplicate Constants

| # | Constant | Location A | Location B | Severity | Notes |
|---|----------|-----------|-----------|----------|-------|
| 1 | `SEMANTICSCHOLAR_BASE_URL` | `infrastructure/adapters/semanticscholar/adapter.py:47` | `infrastructure/adapters/semanticscholar/fallback.py:30` | **HIGH** | Identical value. Should be defined once. |
| 2 | `PUBCHEM_API_BASE` | `infrastructure/adapters/pubchem/client.py:45` | `infrastructure/adapters/pubchem/fetch_strategies.py:27` | **HIGH** | Identical value. Should be defined once. |
| 3 | `DATE_REGEX` / `ISO_DATE_PATTERN` | `domain/contracts/gold/_base.py:17` | `domain/schemas/constants.py:30` | **MEDIUM** | Same regex `r"^\d{4}-\d{2}-\d{2}$"`, different names. |
| 4 | `LOOKUP_METHODS` | `domain/entities/openalex.py:18` | `domain/schemas/common/publication_base.py:26` | **HIGH** | DIFFERENT VALUES: openalex has 4 items, common has 6 items (includes "direct", "pmid"). Inconsistency risk. |
| 5 | `OA_STATUS_VALUES` / `VALID_OA_STATUS_VALUES` | `domain/schemas/common/publication_base.py:29` | `application/pipelines/semanticscholar/extractors.py:162` | **MEDIUM** | Same values, different types (list vs set). Application layer should import from domain. |
| 6 | `PUBLICATION_TYPES` | `domain/schemas/constants.py:188` | `domain/schemas/crossref/work.py:22` | **LOW** | Different values (ChEMBL types vs Crossref types). Same name, different semantics — naming collision only. |

### 2.4 Normalization Hierarchy Confusion (CRITICAL structural duplication)

The domain layer contains **two parallel normalization subsystems** with confusing naming:

**System A: Activity/Chemistry Normalization**
| Component | File | Purpose | Status |
|-----------|------|---------|--------|
| `NormalizationServicePort` | `domain/ports/normalization.py` | Port | DEAD — 0 refs |
| `NormalizationService` | `domain/services/normalization_service.py` | Activity value normalization | TEST_ONLY |
| `NormalizationConfig` | `domain/services/normalization_config.py` | Config for activity norms | Active (6 prod + 32 test) |
| `UnitConverterPort` | `domain/ports/normalization.py` | Port | DEAD — 0 refs |
| `ValueValidatorPort` | `domain/ports/normalization.py` | Port | DEAD — 0 refs |
| `ActivityAggregatorPort` | `domain/ports/normalization.py` | Port | DEAD — 0 refs |
| `OutlierFilterPort` | `domain/ports/normalization.py` | Port | DEAD — 0 refs |

**System B: Publication Data Normalization**
| Component | File | Purpose | Status |
|-----------|------|---------|--------|
| `DataNormalizationPort` | `domain/ports/data_normalization.py` | Port | ACTIVE — 26 refs |
| `DefaultDataNormalizationService` | `domain/services/data_normalization_service.py` | DOI, PMID, author normalization | Active (3 prod + 28 test) |
| `DataNormalizationConfig` | `domain/services/data_normalization_config.py` | Config for pub norms | Active |

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

### 2.5 Cross-Provider Duplicates (Transformer/Client/Schema)

| # | Provider A | Provider B | Shared Logic | Severity |
|---|-----------|-----------|-------------|----------|
| 1 | `openalex/client.py:_normalize_doi` | `semanticscholar/adapter.py:_normalize_doi` | DOI normalization with URL stripping | MEDIUM |
| 2 | `crossref/client.py:_probe_health` | `openalex/client.py:_probe_health` | Near-identical health probe (~30 LOC each): query /works with 1 result, check >5s for DEGRADED, non-200 for UNHEALTHY | **HIGH** |
| 3 | `crossref/fallback.py` | `openalex/fallback.py` | Near-identical TitleFallbackHandler (both extend BaseTitleFallbackHandler) | LOW |
| 4 | `pubmed/fallback.py` | `crossref/fallback.py` | Near-identical TitleFallbackHandler | LOW |
| 5 | `domain/normalization.py:parse_page_range` | `semanticscholar/_page_parsing.py:parse_page_range` | Page range parsing (but different capabilities) | HIGH |

### 2.6 NoOp Implementation Duplication (470 + 199 = 669 LOC)

Two parallel NoOp hierarchies exist:

**domain/ports/noop.py** (470 LOC):
- `NoOpTracing`, `NoOpMetrics`, `NoOpAudit`, `NoOpPiiHasher`, `NoOpMemoryMonitor`, `NoOpMetadataWriter`
- Used via `from bioetl.domain.ports import NoOp*` (application/infrastructure layers)

**infrastructure/observability/noop_*.py** (199 LOC total):
- `NoOpLogger` (51 LOC), `NoOpMetrics` (88 LOC), `NoOpTracing` (60 LOC)
- Used via `from bioetl.infrastructure.observability.noop_* import *` (composition/tests)

**Overlap:** `NoOpTracing` and `NoOpMetrics` exist in BOTH locations with separate implementations.

### 2.7 Exception Hierarchy Fragmentation

8 exceptions in application/infrastructure layers bypass the `BioETLError` hierarchy:

| # | Exception | File | Extends | Severity |
|---|-----------|------|---------|----------|
| 1 | `PreflightValidationError` | `application/composite/preflight_validator.py:81` | `Exception` | MEDIUM |
| 2 | `TransformationError` | `application/core/base_transformer.py:65` | `Exception` | MEDIUM |
| 3 | `PipelineNotFoundError` | `application/services/pipeline_runner_service.py:166` | `ValueError` | LOW |
| 4 | `PipelineShutdownError` | `application/services/shutdown_service.py:247` | `Exception` | MEDIUM |
| 5 | `IDMappingJobError` | `infrastructure/adapters/uniprot/idmapping_client.py:35` | `Exception` | MEDIUM |
| 6 | `IDMappingTimeoutError` | `infrastructure/adapters/uniprot/idmapping_client.py:49` | `Exception` | MEDIUM |
| 7 | `FieldGroupLoadError` | `infrastructure/config/field_group_loader.py:31` | `ValueError` | LOW |
| 8 | `AtomicWriteError` | `infrastructure/storage/_atomic.py:26` | `Exception` | MEDIUM |

Note: All are actively used (10-91 refs each). The issue is NOT dead code but inconsistent error handling — these exceptions won't be caught by `except BioETLError` handlers.

---

## 3. Dependency Map — Notable Patterns

### 3.1 Highest Fan-In Objects (most depended upon)

| # | Object | Layer | Dependents |
|---|--------|-------|-----------|
| 1 | `LoggerPort` | domain | 223 implementation refs |
| 2 | `DataSourcePort` | domain | 141 implementation refs |
| 3 | `MetricsPort` | domain | 135 implementation refs |
| 4 | `TracingPort` | domain | 87 implementation refs |
| 5 | `NoOpMetrics` (domain) | domain | 77 production refs |
| 6 | `NoOpTracing` (domain) | domain | 60 production refs |
| 7 | `FilterableDataSourcePort` | domain | 48 implementation refs |

### 3.2 Domain DriftLevel Enum Conflict — RESOLVED

~~**CRITICAL BUG RISK**~~: **Resolved on `main` (`7e265aa`)**. The duplicate `DriftLevel` enum in `domain/value_objects/dq_report.py` was replaced with an import from `domain/types.py`:

```python
# domain/value_objects/dq_report.py (AFTER fix)
from bioetl.domain.types import DriftLevel  # ← single source of truth
```

The canonical definition remains in `domain/types.py` with UPPERCASE values (`"INFO"`, `"WARN"`, `"CRITICAL"`).

### 3.2a DriftLevel WARN Doc-Code Drift — NEW (introduced on `main` @ `29fccea`)

**Severity:** HIGH

RULES.md §2.2 was updated on main (`29fccea`) to remove the `Warn` drift level:

```markdown
# RULES.md §2.2 (AFTER change)
| Уровень  | Условие                                  |
|----------|------------------------------------------|
| Info     | Новые поля (любое количество)            |
| Critical | Пропавшее обязательное поле / смена типа |
```

But the code still defines and uses 3 levels:

```python
# domain/types.py:83-87 — still has WARN
class DriftLevel(StrEnum):
    INFO = "INFO"
    WARN = "WARN"        # ← not in RULES.md anymore
    CRITICAL = "CRITICAL"

# domain/transformations.py:140-144 — still uses WARN with ">3 fields" threshold
level = DriftLevel.INFO
if missing_required:
    level = DriftLevel.CRITICAL
elif len(added) > 3:
    level = DriftLevel.WARN   # ← dead policy per RULES.md
```

**Options:**
1. **Align code to RULES.md** — remove `WARN` from enum, collapse `>3 new fields` case to `INFO`.
2. **Restore WARN in RULES.md** — if the WARN level is still desired, update RULES.md §2.2 back.

**Impact:** The `detect_schema_drift()` function returns `DriftLevel.WARN` for schemas with >3 new fields, but RULES.md says any number of new fields is just `Info`. Consumers relying on RULES.md won't expect WARN events.

### 3.3 LOOKUP_METHODS Inconsistency

```python
# domain/entities/openalex.py — 4 values
LOOKUP_METHODS = ["doi", "title_fallback", "title_only", "unknown"]

# domain/schemas/common/publication_base.py — 6 values
LOOKUP_METHODS = ["direct", "doi", "pmid", "title_fallback", "title_only", "unknown"]
```

The OpenAlex entity definition is a **subset** of the canonical schema definition. This could cause validation failures if an OpenAlex record uses "direct" or "pmid" lookup methods.

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
| ~~QW-8~~ | ~~**Fix DriftLevel enum conflict**~~ | **RESOLVED on main** (`7e265aa`) | — | — |
| QW-9 | **Deduplicate `SEMANTICSCHOLAR_BASE_URL`** | `adapter.py` + `fallback.py` → single definition | DRY | Trivial |
| QW-10 | **Deduplicate `PUBCHEM_API_BASE`** | `client.py` + `fetch_strategies.py` → single definition | DRY | Trivial |
| QW-11 | **Remove dead value objects** | `BaseDQReport`, `DQCheckResult`, `FieldPresenceResult` | -~100 LOC | Low |
| QW-12 | **Remove dead entity** | `OpenAlexPublicationRecord` | -~30 LOC | Trivial |
| QW-13 | **Fix `LOOKUP_METHODS` inconsistency** | Align `domain/entities/openalex.py` with `schemas/common/publication_base.py` | Correctness | Low |
| QW-14 | **Deduplicate `OA_STATUS_VALUES`** | `application/pipelines/semanticscholar/extractors.py` → import from domain | DRY | Trivial |
| QW-15 | **Resolve DriftLevel WARN doc-code drift** (NEW) | RULES.md §2.2 removed WARN, code still has it | Consistency | Medium |

**Total quick-win LOC removal: ~1,107 LOC** (14 active items: 13 original + QW-15 new; QW-8 resolved on main)

### 5.2 Refactorings (Require Planning)

| # | RF-ID | Description | Objects | Impact | Risk |
|---|-------|-------------|---------|--------|------|
| 1 | RF-NOOP | **Consolidate NoOp implementations** — Merge domain/ports/noop.py and infrastructure/observability/noop_*.py into a single canonical location | 2 `NoOpTracing`, 2 `NoOpMetrics`, `NoOpLogger` | -199 LOC, unified imports | Medium |
| 2 | RF-NORM | **Clean normalization hierarchy** — Remove dead ports in `domain/ports/normalization.py`; clarify relationship between `domain/normalization.py` functions and `DataNormalizationService`; decide fate of TEST_ONLY services | 5 dead ports, 7 TEST_ONLY services, ~10 overlapping functions | Architecture clarity | High |
| 3 | RF-CBCFG | **Unify CircuitBreakerConfig** — Consolidate triple definition into domain dataclass + Pydantic `to_domain()` converter | 3 definitions | Type safety | Medium |
| 4 | RF-RUNST | **Resolve RunStatus duplication** — Either remove unused `domain/aggregates/pipeline_run.py:RunStatus` or reconcile with `application/services/pipeline_runner_service.py:RunStatus` | 2 definitions | Naming clarity | Low |
| 5 | RF-ENTITY | **Resolve entity/model duplication** — `ChemblPublicationRecord` and `PubchemMoleculeRecord` exist in both domain/entities and infrastructure/models | 4 classes | Architecture clarity | High |
| 6 | ~~RF-DRIFT~~ | ~~**Fix DriftLevel enum values**~~ — **RESOLVED on main** (`7e265aa`) | — | — | — |
| 7 | RF-PAGES | **Consolidate `parse_page_range`** — Merge domain/normalization.py and semanticscholar/_page_parsing.py implementations | 2 functions | DRY | Low |
| 8 | RF-HASH | **Consolidate `normalize_for_hash`** — Three independent implementations | 3 functions | DRY | Medium |
| 9 | RF-ORPHAN-SCHEMAS | **Decide on orphan schemas** — crossref/author.py, crossref/funder.py, uniprot/isoform.py: remove if entities not planned | 3 modules | -235 LOC | Low |
| 10 | RF-HEALTH | **Extract shared health probe pattern** — CrossRef and OpenAlex `_probe_health` are near-identical; could be a parameterized method in BaseHttpAdapter | 2 implementations (~60 LOC) | DRY | Low |
| 11 | RF-EXCN | **Integrate orphan exceptions into BioETLError hierarchy** — 8 exceptions bypass the domain exception hierarchy | 8 exceptions | Error handling consistency | Medium |
| 12 | RF-DATEREGEX | **Consolidate DATE_REGEX / ISO_DATE_PATTERN** — Same regex with different names in contracts vs schemas | 2 constants | Naming clarity | Trivial |

### 5.3 Layer Health Summary

| Layer | Dead Objects | Duplicates | Orphans | Health |
|-------|-------------|------------|---------|--------|
| domain | 10 classes + 3 VOs + 1 entity + 3 exceptions + 6 ports + 7 TEST_ONLY services + 10 TEST_ONLY VOs | ~~DriftLevel~~ (resolved), RunStatus, normalization overlap, LOOKUP_METHODS, DATE_REGEX | 7 files (932 LOC) | ⚠️ |
| application | 0 dead (1 TEST_ONLY) | normalize_string/parse_date_field wrappers, OA_STATUS_VALUES dup, 4 orphan exceptions | 1 file (25 LOC) | ✅ |
| infrastructure | 4 dead (1 TEST_ONLY) | NoOp overlap, entity/model duplication, PUBCHEM_API_BASE, SEMANTICSCHOLAR_BASE_URL, health probe pattern, 4 orphan exceptions | 1 file (56 LOC) | ⚠️ |
| composition | 0 | CircuitBreakerConfig, RateLimitConfig | 0 | ✅ |
| interfaces | 0 | 0 | 0 | ✅ |

---

## 6. Checklist

- [x] Object registry collected for all 5 layers (876 classes, 561 functions, ~120 constants)
- [x] Reference count analyzed for all classes (dead/test-only/active)
- [x] Dead code identified and verified against exception list
- [x] Dead value objects and domain services identified
- [x] Cross-provider duplication analyzed (transformers, clients, fallbacks, health probes)
- [x] Cross-layer duplication analyzed (NoOps, configs, entities, normalization)
- [x] Duplicate constants cataloged (6 groups)
- [x] Orphan modules identified (10 candidates, 1 false positive)
- [x] Duplicate class names cataloged (16 groups)
- [x] DriftLevel enum conflict flagged as CRITICAL → **RESOLVED on main**
- [x] LOOKUP_METHODS inconsistency flagged
- [x] Exception hierarchy fragmentation analyzed (8 orphan exceptions)
- [x] Recommendations prioritized (14 active quick wins + 11 active refactorings; QW-8 + RF-DRIFT resolved on main; QW-15 added for new doc-code drift)

---

## Appendix A: Methodology

Analysis performed using:
- `grep -rn` for class/function extraction and reference counting
- Systematic dead-class detection across all layers (876 classes checked)
- Manual file comparison for semantic duplication (normalization, NoOp, configs)
- Orphan detection via module-level import pattern matching
- Cross-referencing with tests/ directory for TEST_ONLY classification
- Constant duplication detection via name-based grep
- Exception hierarchy analysis (BioETLError lineage check)

### Exclusions (per methodology)
- Protocol/Port classes without direct calls (contracts) — verified individually
- `__all__` re-exports — checked for bitrot
- Pydantic/Pandera validators — called by framework
- Click decorators — called by CLI framework
- `TYPE_CHECKING` imports — type hints only
- Template method overrides (e.g., `entity_to_silver_record`) — not duplicates
- Per-provider `_probe_health` implementations — provider-specific logic (except CrossRef/OpenAlex near-identical pair)

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
- `NormalizationService` in `domain/services/normalization_service.py` (TEST_ONLY)
- `UnitConverter` in `domain/services/unit_converter.py` (TEST_ONLY)
- `ValueValidator` in `domain/services/value_validator.py` (TEST_ONLY)
- `ActivityAggregator` in `domain/services/activity_aggregator.py` (TEST_ONLY)

**Conclusion:** Both ports AND their service implementations are unused in production. This appears to be a designed but unintegrated "activity data normalization" subsystem. Either complete the integration or remove the entire subsystem.

---

## Appendix C: TEST_ONLY Domain Services — Activity Normalization Subsystem

The following domain services form a coherent but unintegrated subsystem for activity data normalization:

| Service | File | Responsibility | Test Refs |
|---------|------|---------------|-----------|
| `ActivityAggregator` | `domain/services/activity_aggregator.py` | Aggregate activity measurements | 50 |
| `UnitConverter` | `domain/services/unit_converter.py` | Convert between concentration units | 35 |
| `ValueValidator` | `domain/services/value_validator.py` | Validate activity values/ranges | 48 |
| `NormalizationService` | `domain/services/normalization_service.py` | Normalize activity data | Active via NormalizationConfig |

Supporting types (also TEST_ONLY):
- `AggregationMethod`, `ConcentrationRangeConfig`, `PChemblRangeConfig`, `NormalizationResult`
- `ActivityValue`, `AssayId`, `CompoundId`, `CompoundSource`, `ConfidenceScore`

**Total estimated LOC of unintegrated subsystem:** ~1,500 LOC (services + value objects + ports + tests)

**Recommendation:** This is a significant design decision. Either:
1. **Integrate into pipelines** — wire through composition layer, add to ChEMBL transformer
2. **Archive/remove** — if activity normalization is out of scope

---

## Appendix D: Duplicate Constants Quick Reference

| Constant | Canonical Location | Duplicate Location | Action |
|----------|-------------------|-------------------|--------|
| `SEMANTICSCHOLAR_BASE_URL` | `adapters/semanticscholar/adapter.py:47` | `adapters/semanticscholar/fallback.py:30` | Import from adapter |
| `PUBCHEM_API_BASE` | `adapters/pubchem/client.py:45` | `adapters/pubchem/fetch_strategies.py:27` | Import from client |
| `DATE_REGEX` / `ISO_DATE_PATTERN` | `domain/schemas/constants.py:30` | `domain/contracts/gold/_base.py:17` | Consolidate to single name |
| `LOOKUP_METHODS` | `domain/schemas/common/publication_base.py:26` | `domain/entities/openalex.py:18` | Align openalex to canonical (add "direct", "pmid") |
| `OA_STATUS_VALUES` | `domain/schemas/common/publication_base.py:29` | `application/pipelines/semanticscholar/extractors.py:162` | Import from domain |
| `PUBLICATION_TYPES` | `domain/schemas/constants.py:188` | `domain/schemas/crossref/work.py:22` | Rename one (different semantics) |

---

## Appendix E: Actionable Prompts for Code Modification

Ready-to-use prompts for sub-agents to execute recommended changes.
Each prompt is self-contained and includes scope, verification criteria, and rollback guidance.

---

### E.1 Quick Wins — Dead Code Removal

#### QW-1: Remove Dead Schemas (molecule_form, target_relation)

**Target agent:** `py-code-bot`
**Estimated impact:** -73 LOC, 2 files deleted

```
ЗАДАЧА: Удалить мёртвые схемы MoleculeFormSchema и TargetRelationSchema.

ФАЙЛЫ ДЛЯ УДАЛЕНИЯ:
1. src/bioetl/domain/schemas/chembl/molecule_form.py (35 LOC) — содержит MoleculeFormSchema, 0 ссылок в production и tests
2. src/bioetl/domain/schemas/chembl/target_relation.py (38 LOC) — содержит TargetRelationSchema, 0 ссылок в production и tests

ДЕЙСТВИЯ:
1. Удалить оба файла
2. Убрать импорты из src/bioetl/domain/schemas/chembl/__init__.py (если есть)
3. Убрать из src/bioetl/domain/schemas/__init__.py (если есть)
4. Убрать из src/bioetl/domain/__init__.py __all__ (если экспортируются)
5. Поиск по всему проекту: grep -rn "MoleculeFormSchema\|TargetRelationSchema" src/ tests/
   — должно вернуть 0 результатов после очистки

ВЕРИФИКАЦИЯ:
- pytest tests/architecture/ -v  (архитектурные тесты проходят)
- mypy --strict src/bioetl/domain/schemas/chembl/  (нет ошибок)
- grep -rn "molecule_form\|target_relation" src/bioetl/domain/schemas/ — только __pycache__ или 0 результатов

ОТКАТ: git checkout -- src/bioetl/domain/schemas/chembl/
```

#### QW-2: Remove Dead Events

**Target agent:** `py-code-bot`
**Estimated impact:** -120 LOC

```
ЗАДАЧА: Удалить мёртвые event-классы из domain/aggregates/events.py.

ЦЕЛЕВОЙ ФАЙЛ: src/bioetl/domain/aggregates/events.py

КЛАССЫ ДЛЯ УДАЛЕНИЯ (0 ссылок в production и tests):
1. PipelineStarted (строка ~48, ~50 LOC)
2. StageCompleted (строка ~103, ~40 LOC)
3. DQThresholdExceeded (строка ~233, ~15 LOC)
4. SchemaEvolutionDetected (строка ~249, ~15 LOC)

ДЕЙСТВИЯ:
1. Прочитать src/bioetl/domain/aggregates/events.py
2. Удалить определения 4 классов
3. Убрать из __all__ в этом файле (если есть)
4. Убрать из src/bioetl/domain/aggregates/__init__.py
5. Убрать из src/bioetl/domain/__init__.py __all__
6. Проверить: grep -rn "PipelineStarted\|StageCompleted\|DQThresholdExceeded\|SchemaEvolutionDetected" src/ tests/

ВАЖНО: НЕ удалять другие event-классы в том же файле — только эти 4.

ВЕРИФИКАЦИЯ:
- python -c "from bioetl.domain.aggregates import events"  (модуль импортируется)
- pytest tests/architecture/ -v
- mypy --strict src/bioetl/domain/aggregates/
```

#### QW-3: Remove Dead Exceptions

**Target agent:** `py-code-bot`
**Estimated impact:** -30 LOC

```
ЗАДАЧА: Удалить мёртвые exceptions (0 ссылок нигде).

ЦЕЛЕВЫЕ ФАЙЛЫ:
1. src/bioetl/domain/exceptions/infrastructure.py — удалить ConfigurationError, FileSystemError
2. src/bioetl/domain/exceptions/internal.py — удалить InternalError

ДЕЙСТВИЯ:
1. Прочитать оба файла
2. Удалить определения классов ConfigurationError, FileSystemError, InternalError
3. Убрать из __all__ в каждом файле
4. Убрать из src/bioetl/domain/exceptions/__init__.py
5. Убрать из src/bioetl/domain/__init__.py __all__
6. Проверить: grep -rn "ConfigurationError\|FileSystemError\|InternalError" src/ tests/ | grep -v "class "

ВАЖНО: НЕ путать InternalError с другими классами в internal.py (InvalidStateError, PolicyViolationError и т.д.).

ВЕРИФИКАЦИЯ:
- python -c "from bioetl.domain.exceptions import infrastructure, internal"
- pytest tests/unit/domain/ -v -k "exception"
```

#### QW-4: Remove Dead Infrastructure Classes

**Target agent:** `py-code-bot`
**Estimated impact:** -60 LOC

```
ЗАДАЧА: Удалить мёртвые классы в infrastructure layer.

КЛАССЫ:
1. ChemblStatusResponse в src/bioetl/infrastructure/adapters/chembl/models.py:611 (~25 LOC)
2. HasProviderName в src/bioetl/infrastructure/adapters/filterable_mixin.py:23 (~10 LOC)
3. HealthCheckObservability в src/bioetl/infrastructure/adapters/health_check_mixin.py:40 (~15 LOC)
4. PageFetcher в src/bioetl/infrastructure/adapters/http/pagination.py:14 (~10 LOC)

ДЕЙСТВИЯ (для каждого класса):
1. Прочитать файл
2. Удалить определение класса
3. Убрать из __all__ / re-exports
4. Убрать неиспользуемые импорты, появившиеся после удаления
5. Проверить grep -rn "ClassName" src/ tests/

ОСТОРОЖНО с HasProviderName и HealthCheckObservability — файлы могут содержать другие
активные классы. Удалять ТОЛЬКО указанные классы. Если файл становится пустым (только
импорты), можно удалить весь файл.

ВЕРИФИКАЦИЯ:
- pytest tests/unit/infrastructure/ -v
- mypy --strict src/bioetl/infrastructure/adapters/
```

#### QW-5 + QW-6: Remove Orphan Domain Modules

**Target agent:** `py-code-bot`
**Estimated impact:** -669 LOC

```
ЗАДАЧА: Удалить orphan-модули domain layer после верификации.

КАНДИДАТЫ НА УДАЛЕНИЕ:
1. src/bioetl/domain/config_types.py (446 LOC)
2. src/bioetl/domain/schemas/_field_orders.py (223 LOC)

ДО УДАЛЕНИЯ — ОБЯЗАТЕЛЬНАЯ ВЕРИФИКАЦИЯ:
1. grep -rn "config_types" src/bioetl/ tests/ --include="*.py"
   — Если есть ссылки (кроме комментариев) → НЕ УДАЛЯТЬ, доложить
2. grep -rn "_field_orders\|field_orders" src/bioetl/ tests/ --include="*.py"
   — Если есть ссылки → НЕ УДАЛЯТЬ, доложить
3. Проверить git log -5 -- для каждого файла (убедиться, что не активная разработка)

ЕСЛИ ВЕРИФИКАЦИЯ ПРОЙДЕНА:
1. Удалить файлы
2. Убрать из __init__.py любые re-exports
3. Убрать из __all__

ВЕРИФИКАЦИЯ:
- python -c "import bioetl.domain"  (пакет импортируется)
- pytest tests/architecture/ -v
```

#### QW-7: Remove Orphan dq_metrics_calculator.py

**Target agent:** `py-code-bot`
**Estimated impact:** -25 LOC

```
ЗАДАЧА: Удалить re-export shim src/bioetl/application/services/dq_metrics_calculator.py.

ВЕРИФИКАЦИЯ ДО УДАЛЕНИЯ:
1. grep -rn "dq_metrics_calculator" src/ tests/ --include="*.py"
   — Если есть ссылки → НЕ УДАЛЯТЬ
2. cat src/bioetl/application/services/dq_metrics_calculator.py
   — Убедиться что это действительно re-export shim

ДЕЙСТВИЯ:
1. Удалить файл
2. Убрать из application/services/__init__.py (если есть)

ВЕРИФИКАЦИЯ:
- python -c "from bioetl.application import services"
```

#### ~~QW-8: Fix DriftLevel Enum Conflict~~ — RESOLVED ON MAIN

**Status:** Already fixed on `main` (`7e265aa`).
`domain/value_objects/dq_report.py` now imports `DriftLevel` from `domain/types.py`.
No action required.

#### QW-9 + QW-10: Deduplicate API Base URL Constants

**Target agent:** `py-code-bot`
**Estimated impact:** DRY improvement

```
ЗАДАЧА: Устранить дублирование констант API base URL.

ДУБЛИКАТ 1: SEMANTICSCHOLAR_BASE_URL
- Canonical: src/bioetl/infrastructure/adapters/semanticscholar/adapter.py:47
- Дубликат: src/bioetl/infrastructure/adapters/semanticscholar/fallback.py:30

ДЕЙСТВИЯ:
1. В fallback.py удалить определение SEMANTICSCHOLAR_BASE_URL
2. Добавить: from bioetl.infrastructure.adapters.semanticscholar.adapter import SEMANTICSCHOLAR_BASE_URL
   ИЛИ вынести в __init__.py пакета semanticscholar/ и импортировать оттуда

ДУБЛИКАТ 2: PUBCHEM_API_BASE
- Canonical: src/bioetl/infrastructure/adapters/pubchem/client.py:45
- Дубликат: src/bioetl/infrastructure/adapters/pubchem/fetch_strategies.py:27

ДЕЙСТВИЯ:
1. В fetch_strategies.py удалить определение PUBCHEM_API_BASE
2. Добавить: from bioetl.infrastructure.adapters.pubchem.client import PUBCHEM_API_BASE
   ИЛИ вынести в __init__.py пакета pubchem/ и импортировать оттуда

ВЕРИФИКАЦИЯ:
- grep -rn "SEMANTICSCHOLAR_BASE_URL\s*=" src/ — РОВНО 1 результат
- grep -rn "PUBCHEM_API_BASE\s*=" src/ — РОВНО 1 результат
- pytest tests/unit/infrastructure/adapters/semanticscholar/ -v
- pytest tests/unit/infrastructure/adapters/pubchem/ -v
```

#### QW-11: Remove Dead Value Objects

**Target agent:** `py-code-bot`
**Estimated impact:** -~100 LOC

```
ЗАДАЧА: Удалить мёртвые value objects из domain/value_objects/dq_report.py.

КЛАССЫ ДЛЯ УДАЛЕНИЯ (0 ссылок кроме __all__):
1. BaseDQReport (~50 LOC)
2. DQCheckResult (~70 LOC)
3. FieldPresenceResult (~40 LOC)

ВЕРИФИКАЦИЯ ДО УДАЛЕНИЯ:
grep -rn "BaseDQReport\|DQCheckResult\|FieldPresenceResult" src/ tests/ --include="*.py"
— Ожидается: только class definition + __all__ entry

ДЕЙСТВИЯ:
1. Прочитать src/bioetl/domain/value_objects/dq_report.py
2. Удалить определения 3 классов
3. Убрать из __all__ в файле
4. Убрать из domain/value_objects/__init__.py
5. Убрать из domain/__init__.py __all__
6. Удалить импорты, ставшие неиспользуемыми

ОСТОРОЖНО: В том же файле находятся АКТИВНЫЕ классы (DriftLevel, ColumnStats и др.).
Удалять ТОЛЬКО указанные 3 класса.

ВЕРИФИКАЦИЯ:
- python -c "from bioetl.domain.value_objects import dq_report"
- pytest tests/unit/domain/value_objects/ -v
```

#### QW-12: Remove Dead Entity OpenAlexPublicationRecord

**Target agent:** `py-code-bot`
**Estimated impact:** -~30 LOC

```
ЗАДАЧА: Удалить мёртвую DTO-модель OpenAlexPublicationRecord.

ФАЙЛ: src/bioetl/domain/entities/openalex.py
КЛАСС: OpenAlexPublicationRecord (строка ~24, Pydantic BaseModel)

ВЕРИФИКАЦИЯ ДО УДАЛЕНИЯ:
grep -rn "OpenAlexPublicationRecord" src/ tests/ --include="*.py"
— Ожидается: только class definition + __all__ + docstring

ДЕЙСТВИЯ:
1. Прочитать файл
2. Удалить class OpenAlexPublicationRecord
3. Убрать из __all__ в файле
4. Убрать из domain/entities/__init__.py
5. Убрать из domain/__init__.py
6. Удалить неиспользуемые импорты

ВАЖНО: НЕ удалять OpenAlexPublicationEntity (он активно используется, 8 prod refs).

ВЕРИФИКАЦИЯ:
- python -c "from bioetl.domain.entities.openalex import OpenAlexPublicationEntity"
- pytest tests/unit/domain/ -v -k "openalex"
```

#### QW-13: Fix LOOKUP_METHODS Inconsistency

**Target agent:** `py-code-bot`
**Estimated impact:** Correctness

```
ЗАДАЧА: Устранить несоответствие LOOKUP_METHODS между entity и schema.

ПРОБЛЕМА:
- domain/entities/openalex.py:18 — LOOKUP_METHODS = ["doi", "title_fallback", "title_only", "unknown"]
- domain/schemas/common/publication_base.py:26 — LOOKUP_METHODS = ["direct", "doi", "pmid", "title_fallback", "title_only", "unknown"]

АНАЛИЗ:
1. Определить каноническое определение (publication_base.py — 6 значений, более полное)
2. Проверить: используются ли "direct" и "pmid" для OpenAlex записей?
   grep -rn "lookup_method.*direct\|lookup_method.*pmid" src/bioetl/application/pipelines/openalex/

РЕКОМЕНДУЕМОЕ РЕШЕНИЕ:
Вариант A (предпочтительный): Импортировать из schemas
1. В domain/entities/openalex.py убрать локальный LOOKUP_METHODS
2. Добавить: from bioetl.domain.schemas.common.publication_base import LOOKUP_METHODS
3. Обновить __all__

Вариант B: Если OpenAlex действительно поддерживает только 4 метода, переименовать:
1. LOOKUP_METHODS → OPENALEX_LOOKUP_METHODS в entities/openalex.py
2. Оставить как provider-specific subset

ВЕРИФИКАЦИЯ:
- pytest tests/unit/domain/entities/ -v -k "openalex"
- pytest tests/unit/domain/schemas/ -v -k "publication"
```

#### QW-14: Deduplicate OA_STATUS_VALUES

**Target agent:** `py-code-bot`
**Estimated impact:** DRY

```
ЗАДАЧА: Устранить дублирование OA_STATUS_VALUES.

ПРОБЛЕМА:
- domain/schemas/common/publication_base.py:29 — OA_STATUS_VALUES = ["gold", "green", "hybrid", "bronze", "closed"]
- application/pipelines/semanticscholar/extractors.py:162 — VALID_OA_STATUS_VALUES = {"gold", "green", "hybrid", "bronze", "closed"}

ДЕЙСТВИЯ:
1. В application/pipelines/semanticscholar/extractors.py:
   - Удалить VALID_OA_STATUS_VALUES = {...}
   - Добавить: from bioetl.domain.schemas.common.publication_base import OA_STATUS_VALUES
   - Заменить все использования VALID_OA_STATUS_VALUES на set(OA_STATUS_VALUES) или frozenset(OA_STATUS_VALUES)
   ИЛИ: OA_STATUS_SET = frozenset(OA_STATUS_VALUES) для O(1) lookup

ВЕРИФИКАЦИЯ:
- grep -rn "VALID_OA_STATUS_VALUES" src/ — 0 результатов
- pytest tests/unit/application/pipelines/semanticscholar/ -v
```

#### QW-15: Resolve DriftLevel WARN Doc-Code Drift (NEW)

**Target agent:** `py-code-bot` or `py-doc-bot`
**Estimated impact:** Doc-code consistency

```
ЗАДАЧА: Устранить рассинхрон между RULES.md §2.2 и кодом DriftLevel.

ПРОБЛЕМА (появилась после коммита 29fccea на main):
- RULES.md §2.2 определяет ТОЛЬКО 2 уровня: Info, Critical
- domain/types.py:83-87 определяет 3 уровня: INFO, WARN, CRITICAL
- domain/transformations.py:144 использует DriftLevel.WARN (условие ">3 new fields")
- Docstring в domain/types.py ссылается на старую политику ">3 new fields → WARN"

ВАРИАНТ A — Align code to RULES.md (предпочтительный, т.к. RULES.md — source of truth):
1. Удалить WARN из DriftLevel enum в domain/types.py
2. Обновить detect_schema_drift() в domain/transformations.py:
   - Убрать elif len(added) > 3: level = DriftLevel.WARN
   - Все "new fields" случаи → DriftLevel.INFO
3. Обновить docstring DriftLevel
4. grep -rn "DriftLevel.WARN\|DriftLevel\.WARN" src/ tests/ — обновить все ссылки

ВАРИАНТ B — Restore WARN in RULES.md:
1. Обновить docs/00-project/RULES.md §2.2 добавив обратно:
   | Warn | >3 новых полей |
2. Код не менять

ВЕРИФИКАЦИЯ:
- grep -rn "DriftLevel" src/bioetl/ --include="*.py" | wc -l — посчитать все ссылки
- pytest tests/unit/domain/ -v -k "drift"
- mypy --strict src/bioetl/domain/types.py src/bioetl/domain/transformations.py
```

---

### E.2 Refactorings — Structural Changes

#### RF-NOOP: Consolidate NoOp Implementations

**Target agent:** `py-code-bot` (координация с `py-plan-bot`)
**Estimated impact:** -199 LOC, unified import paths

```
ЗАДАЧА: Объединить две параллельные иерархии NoOp-реализаций.

ТЕКУЩЕЕ СОСТОЯНИЕ:
A) domain/ports/noop.py (470 LOC): NoOpTracing, NoOpMetrics, NoOpAudit, NoOpPiiHasher, NoOpMemoryMonitor, NoOpMetadataWriter
B) infrastructure/observability/noop_*.py (199 LOC): NoOpLogger, NoOpMetrics, NoOpTracing

ДУБЛИРУЮТСЯ: NoOpTracing (A + B), NoOpMetrics (A + B)
УНИКАЛЬНЫЕ: NoOpLogger (только в B), остальные (только в A)

ПЛАН:
1. ФАЗА АНАЛИЗА (read-only):
   - Сравнить сигнатуры и реализации NoOpTracing из A и B
   - Сравнить сигнатуры и реализации NoOpMetrics из A и B
   - Определить каноническую версию (domain/ports/noop.py — приоритет по ARCH-001)
   - Собрать ВСЕ точки импорта обеих версий: grep -rn "NoOpTracing\|NoOpMetrics" src/ tests/

2. ФАЗА МИГРАЦИИ:
   - Перенести NoOpLogger из infrastructure/ в domain/ports/noop.py
   - Обновить ВСЕ импорты infrastructure NoOp → domain NoOp
   - Удалить infrastructure/observability/noop_metrics.py
   - Удалить infrastructure/observability/noop_tracing.py
   - Обновить infrastructure/observability/__init__.py

3. ФАЗА ВЕРИФИКАЦИИ:
   - grep -rn "from bioetl.infrastructure.observability.noop" src/ tests/ — 0 результатов
   - pytest tests/ -v --tb=short
   - mypy --strict src/bioetl/

РИСКИ:
- Circular import при переносе NoOpLogger в domain (LoggerPort уже в domain)
- Тесты могут использовать infra-версию напрямую
```

#### RF-NORM: Clean Normalization Hierarchy

**Target agent:** `py-plan-bot` → `py-code-bot`
**Estimated impact:** Architecture clarity, -~500 LOC dead code

```
ЗАДАЧА: Очистить запутанную иерархию нормализации в domain layer.

ТЕКУЩЕЕ СОСТОЯНИЕ (3 параллельные системы):
A) Activity Normalization — 5 мёртвых портов + 7 TEST_ONLY сервисов
B) Publication Normalization — АКТИВНАЯ система (DataNormalizationPort → DefaultDataNormalizationService)
C) Standalone functions в domain/normalization.py — частично дублируют B

ФАЗА 1: Удаление мёртвых портов
1. Удалить из domain/ports/normalization.py:
   - ActivityAggregatorPort, NormalizationServicePort, OutlierFilterPort, UnitConverterPort, ValueValidatorPort
2. Если файл становится пустым — удалить файл
3. Обновить domain/ports/__init__.py и domain/__init__.py

ФАЗА 2: Решение по TEST_ONLY сервисам (ТРЕБУЕТ РЕШЕНИЯ ВЛАДЕЛЬЦА)
Варианты:
A) Интегрировать в production pipeline (добавить в composition/, вызывать из transformers)
B) Оставить как есть (documented intent для будущего использования)
C) Удалить вместе с тестами (-~1,500 LOC total)

→ Спросить владельца проекта перед выполнением фазы 2.

ФАЗА 3: Устранить дублирование C ↔ B
1. Сравнить domain/normalization.py:normalize_string() с DataNormalizationService.normalize_string()
2. Если идентичны — service должен делегировать standalone функции (или наоборот)
3. Аналогично для normalize_doi(), parse_authors_to_list()

ВЕРИФИКАЦИЯ:
- grep -rn "NormalizationServicePort\|UnitConverterPort\|ValueValidatorPort\|ActivityAggregatorPort\|OutlierFilterPort" src/ — 0 результатов (после фазы 1)
- pytest tests/architecture/ -v
- pytest tests/unit/domain/ -v
```

#### RF-CBCFG: Unify CircuitBreakerConfig

**Target agent:** `py-code-bot`
**Estimated impact:** Type safety, single source of truth

```
ЗАДАЧА: Объединить тройное определение CircuitBreakerConfig.

ТЕКУЩИЕ ОПРЕДЕЛЕНИЯ:
1. domain/resilience.py — dataclass (каноническое)
2. infrastructure/schemas/pipeline_config.py — Pydantic BaseModel (для YAML validation)
3. composition/bootstrap_contexts.py — NamedTuple

ПЛАН:
1. Оставить domain/resilience.py как каноническое определение (dataclass)
2. infrastructure/schemas/pipeline_config.py — переименовать в CircuitBreakerConfigSchema,
   добавить метод to_domain() -> CircuitBreakerConfig
3. composition/bootstrap_contexts.py — удалить NamedTuple, импортировать domain dataclass

ВЕРИФИКАЦИЯ:
- grep -rn "class CircuitBreakerConfig" src/ — РОВНО 1 результат в domain/ + 1 Schema в infrastructure/
- pytest tests/ -v -k "circuit_breaker"
- mypy --strict src/bioetl/domain/resilience.py src/bioetl/infrastructure/schemas/pipeline_config.py
```

#### RF-ENTITY: Resolve Entity/Model Name Collisions

**Target agent:** `py-plan-bot` → `py-code-bot`
**Estimated impact:** Architecture clarity

```
ЗАДАЧА: Разрешить коллизию имён между domain entities и infrastructure models.

КОЛЛИЗИИ:
1. ChemblPublicationRecord — domain/entities/chembl.py:511 vs infrastructure/adapters/chembl/models.py:467
2. PubchemMoleculeRecord — domain/entities/pubchem.py:24 vs infrastructure/adapters/pubchem/models.py:19

АНАЛИЗ (read-only):
1. Прочитать ОБА определения каждого класса
2. Сравнить поля: идентичные, подмножество, или разные?
3. Определить роль: domain — DTO для pipeline, infrastructure — API response parsing

РЕКОМЕНДУЕМОЕ РЕШЕНИЕ:
- Infrastructure модели переименовать: ChemblPublicationResponse, PubchemCompoundResponse
  (суффикс *Response для API DTO в infrastructure)
- ИЛИ: domain модели переименовать с суффиксом *Entity / *DTO если они вторичны

ДЕЙСТВИЯ:
1. Определить каноническое определение
2. Переименовать дубликат (rename class + update ALL imports)
3. grep -rn "OldName" src/ tests/ → update все ссылки

ВЕРИФИКАЦИЯ:
- grep -rn "class ChemblPublicationRecord" src/ — РОВНО 1 результат
- grep -rn "class PubchemMoleculeRecord" src/ — РОВНО 1 результат
- pytest tests/ -v --tb=short
```

#### RF-EXCN: Integrate Orphan Exceptions into BioETLError

**Target agent:** `py-code-bot`
**Estimated impact:** Consistent error handling

```
ЗАДАЧА: Интегрировать 8 исключений, не наследующих от BioETLError, в иерархию ошибок.

ЦЕЛЕВЫЕ ИСКЛЮЧЕНИЯ:
1. PreflightValidationError(Exception) → PreflightValidationError(ValidationError)
2. TransformationError(Exception) → TransformationError(RecoverableError)
3. PipelineNotFoundError(ValueError) → PipelineNotFoundError(BioETLError)
4. PipelineShutdownError(Exception) → PipelineShutdownError(CriticalError)
5. IDMappingJobError(Exception) → IDMappingJobError(ExternalServiceError)
6. IDMappingTimeoutError(Exception) → IDMappingTimeoutError(TimeoutError)
7. FieldGroupLoadError(ValueError) → FieldGroupLoadError(BioETLError)
8. AtomicWriteError(Exception) → AtomicWriteError(StorageError)

АНАЛИЗ ПЕРЕД ИЗМЕНЕНИЕМ (для каждого):
1. grep -rn "except ExceptionName" src/ tests/ — кто ловит?
2. grep -rn "except (ValueError\|Exception)" в том же файле — кто ловит через parent?
3. Убедиться, что смена базового класса НЕ сломает существующие except-блоки

ДЕЙСТВИЯ (для каждого):
1. Добавить import нового базового класса из bioetl.domain.exceptions
2. Изменить наследование
3. Убедиться что сигнатура __init__ совместима

ВЕРИФИКАЦИЯ:
- pytest tests/ -v --tb=short (ВСЕ тесты)
- mypy --strict src/bioetl/ (на каждый изменённый файл)
```

#### RF-HEALTH: Extract Shared Health Probe Pattern

**Target agent:** `py-code-bot`
**Estimated impact:** -30 LOC, DRY

```
ЗАДАЧА: Вынести общий паттерн _probe_health из CrossRef и OpenAlex в BaseHttpAdapter.

ДУБЛИРОВАНИЕ:
- crossref/client.py:_probe_health — query /works?rows=1, check time >5s, check status code
- openalex/client.py:_probe_health — query /works?per-page=1, check time >5s, check status code

ОБЩИЙ ПАТТЕРН (параметризовать):
1. URL: self._health_endpoint (или метод _get_health_endpoint())
2. Params: dict (provider-specific)
3. Threshold: 5.0 seconds (configurable)
4. Logic: request → check status → check latency → return HealthStatus

РЕКОМЕНДУЕМОЕ РЕШЕНИЕ:
Добавить в BaseHttpAdapter (infrastructure/adapters/base.py) или health_check_mixin.py:

async def _standard_probe_health(self, url: str, params: dict, threshold: float = 5.0) -> HealthStatus:
    ...общая логика...

CrossRef и OpenAlex вызывают:
async def _probe_health(self) -> HealthStatus:
    return await self._standard_probe_health(f"{API_BASE}/works", {"rows": "1", "mailto": self.mailto})

ВЕРИФИКАЦИЯ:
- pytest tests/unit/infrastructure/adapters/crossref/ -v
- pytest tests/unit/infrastructure/adapters/openalex/ -v
```

#### RF-DATEREGEX: Consolidate DATE_REGEX / ISO_DATE_PATTERN

**Target agent:** `py-code-bot`
**Estimated impact:** Naming clarity

```
ЗАДАЧА: Объединить два определения одного и того же regex.

ДУБЛИКАТЫ:
1. domain/contracts/gold/_base.py:17 — DATE_REGEX = r"^\d{4}-\d{2}-\d{2}$"
2. domain/schemas/constants.py:30 — ISO_DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"

ДЕЙСТВИЯ:
1. Оставить каноническое определение в domain/schemas/constants.py как ISO_DATE_PATTERN
2. В domain/contracts/gold/_base.py:
   - Удалить DATE_REGEX = ...
   - Добавить: from bioetl.domain.schemas.constants import ISO_DATE_PATTERN
   - Заменить все DATE_REGEX → ISO_DATE_PATTERN в файле
3. grep -rn "DATE_REGEX" src/ → обновить все ссылки

ВЕРИФИКАЦИЯ:
- grep -rn "DATE_REGEX\s*=" src/ — 0 результатов
- pytest tests/unit/domain/contracts/ -v
- pytest tests/unit/domain/schemas/ -v
```

---

### E.3 Documentation Updates

#### DOC-INVENTORY: Update CHANGELOG after Dead Code Removal

**Target agent:** `py-doc-bot`

```
ЗАДАЧА: Обновить CHANGELOG после выполнения quick wins QW-1..QW-15.

ШАБЛОН ЗАПИСИ:

### Removed
- Dead schemas: MoleculeFormSchema, TargetRelationSchema (QW-1)
- Dead events: PipelineStarted, StageCompleted, DQThresholdExceeded, SchemaEvolutionDetected (QW-2)
- Dead exceptions: ConfigurationError, FileSystemError, InternalError (QW-3)
- Dead infrastructure classes: ChemblStatusResponse, HasProviderName, HealthCheckObservability, PageFetcher (QW-4)
- Orphan modules: config_types.py, _field_orders.py, dq_metrics_calculator.py (QW-5/6/7)
- Dead value objects: BaseDQReport, DQCheckResult, FieldPresenceResult (QW-11)
- Dead entity: OpenAlexPublicationRecord (QW-12)

### Fixed
- DriftLevel enum value conflict (uppercase vs lowercase) resolved (QW-8)
- LOOKUP_METHODS inconsistency between openalex entity and common schema (QW-13)

### Changed
- Deduplicated SEMANTICSCHOLAR_BASE_URL, PUBCHEM_API_BASE constants (QW-9/10)
- OA_STATUS_VALUES imported from domain instead of duplicated in application (QW-14)
- DriftLevel WARN doc-code drift resolved (QW-15)
```

#### DOC-ARCH: Update Architecture Documentation

**Target agent:** `py-doc-bot`

```
ЗАДАЧА: Обновить архитектурную документацию после рефакторингов RF-*.

ФАЙЛЫ ДЛЯ ОБНОВЛЕНИЯ:
1. docs/02-architecture/ — если содержит references к удалённым/переименованным классам
2. docs/00-project/RULES.md — обновить статистику если есть
3. ADR documents — если RF-NORM или RF-ENTITY приняты, создать ADR

КОНТРОЛЬНЫЕ ВОПРОСЫ:
- grep -rn "удалённый_класс" docs/ — заменить/удалить reference
- Проверить диаграммы (если есть) на соответствие текущей структуре
```

---

### E.4 Testing Updates

#### TEST-COVERAGE: Add Tests for PROD_ONLY Objects

**Target agent:** `py-test-bot`

```
ЗАДАЧА: Написать тесты для объектов с 0 test coverage.

PRODUCTION_ONLY объекты (используются в production, нет тестов):
1. CachedBronzeEmptyError — 3 production refs, 0 test refs

ДЕЙСТВИЯ:
1. Найти файл определения: grep -rn "class CachedBronzeEmptyError" src/
2. Найти использования: grep -rn "CachedBronzeEmptyError" src/ --include="*.py"
3. Написать тесты:
   - Создание exception с сообщением
   - Проверка наследования от правильного базового класса
   - Проверка что она ловится через except StorageError
4. Расположить в tests/unit/domain/exceptions/

ВЕРИФИКАЦИЯ:
- pytest tests/unit/domain/exceptions/ -v -k "cached_bronze"
```

---

### E.5 Batch Execution Order

Рекомендуемый порядок выполнения для минимизации конфликтов:

```
ЭТАП 1: Безопасные удаления (нет зависимостей)
  QW-1 → QW-2 → QW-3 → QW-4 → QW-11 → QW-12 → QW-7
  Затем: pytest tests/ -v --tb=short (полный прогон)

ЭТАП 2: Orphan modules (требуют верификации)
  QW-5 → QW-6
  Затем: pytest tests/ -v

ЭТАП 3: Constant deduplication (минимальный риск)
  QW-9 → QW-10 → QW-14 → QW-15
  Затем: pytest tests/ -v

ЭТАП 4: Bug fixes и doc-code drift (требуют внимания)
  QW-8 — SKIP (resolved on main)
  QW-13 (LOOKUP_METHODS)
  QW-15 (DriftLevel WARN doc-code drift — NEW)
  Затем: pytest tests/ -v

ЭТАП 5: Refactorings (требуют планирования)
  RF-DATEREGEX → RF-HEALTH → RF-EXCN → RF-NOOP → RF-CBCFG → RF-RUNST → RF-ENTITY → RF-NORM
  (RF-DRIFT — SKIP, resolved on main)
  Каждый с отдельным коммитом и полным прогоном тестов.
```
