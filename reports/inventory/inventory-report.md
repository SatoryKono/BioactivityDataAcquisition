# Code Inventory Report — BioETL

**Date:** 2026-02-11 (updated)
**Scope:** `src/bioetl/` (all layers)
**Previous revision:** 2026-02-11 (branch `claude/inventory-code-duplication-z4DSx`)
**Current revision:** 2026-02-11 (branch `claude/update-code-audit-report-aOveE`)

---

## Change Log (vs previous revision)

| Area | Change |
|------|--------|
| Metrics | Files 508→499, LOC 116,351→115,851, Classes 937→928, Functions 564→541, Constants 187→119, TypeAliases 10→5 |
| Dead classes | 10→8 (`MoleculeFormSchema`, `TargetRelationSchema` **REMOVED** from codebase) |
| Dead constants | +15 DEAD constants, +4 TEST_ONLY constants identified (section 1.7) |
| Orphan modules | 10→5 (6 files removed: `molecule_form.py`, `target_relation.py`, `crossref/author.py`, `crossref/funder.py`, `crossref/reference.py`, `uniprot/isoform.py`; `adapter_error_logging.py` removed; `chembl/exceptions.py` reclassified as STILL_ORPHAN) |
| Duplicate pipeline classes | **RESOLVED** — `PubChemCompoundPipeline`, `PubMedPublicationPipeline`, `UniProtProteinPipeline` double definitions eliminated (separate `.py` files removed) |
| Config schema duplicates | **STILL PRESENT** — `BaseGoldFiltersConfig.to_domain` / `GoldFiltersConfig.to_domain` and `BaseInputFilterConfig.to_domain` / `InputFilterConfig.to_domain` |
| Fallback handler duplicate | **STILL PRESENT** — `SemanticScholarTitleFallbackHandler._process_found_result` is a no-op override |
| Import cycles | Cycles mitigated via deferred imports / TYPE_CHECKING guards; no runtime failures observed |
| Fan-in/fan-out | `bioetl.domain.ports` fan-in 141→144; `pipeline_factories.py` fan-out 47→50 |

---

## Executive Summary

| Metric | Previous | Current | Delta |
|--------|----------|---------|-------|
| Total .py files | 508 | 499 | -9 |
| Total classes | 937 | 928 | -9 |
| Total module-level functions | 564 | 541 | -23 |
| Total LOC | 116,351 | 115,851 | -500 |
| UPPER_SNAKE_CASE constants | 187 | 119 | -68 |
| Type aliases | 10 | 5 | -5 |
| Modules with `__all__` | 220 | 221 | +1 |
| Dead classes (DEAD) | 10 | 8 | -2 (removed) |
| Dead ports (DEAD) | 6 | 6 | 0 |
| Dead exceptions (DEAD) | 3 | 3 | 0 |
| Dead constants (DEAD) | — | 15 | new |
| TEST_ONLY objects | 10 | 15 | +5 (4 constants + 1 reclassified) |
| Orphan modules | 10 | 5 | -5 (removed) |
| Confirmed name duplicates | 16 | 16 | 0 |
| Confirmed logic duplicates | 5 | 5 | 0 |
| PROD_ONLY (no test coverage) | 1 | 1 | 0 |

### Per-Layer Metrics

| Layer | Files | Classes | Functions | LOC | Constants | TypeAliases | `__all__` modules |
|-------|------:|--------:|----------:|----:|----------:|------------:|------------------:|
| domain | 164 | 452 | 148 | 37,541 | 30 | 5 | 71 |
| application | 129 | 174 | 126 | 32,661 | 11 | 0 | 45 |
| infrastructure | 126 | 264 | 70 | 31,555 | 74 | 0 | 56 |
| composition | 50 | 34 | 134 | 10,868 | 3 | 0 | 36 |
| interfaces | 28 | 4 | 63 | 3,213 | 1 | 0 | 13 |
| **root** | 2 | 0 | 0 | 13 | 0 | 0 | 0 |
| **TOTAL** | **499** | **928** | **541** | **115,851** | **119** | **5** | **221** |

---

## 1. Dead Code

### 1.1 DEAD Classes (0 references in production AND tests)

| # | Object | Type | Layer | Location | Est. LOC | Status vs Previous |
|---|--------|------|-------|----------|----------|-------------------|
| 1 | `PipelineStarted` | Event | domain | `domain/aggregates/events.py:48` | ~50 | unchanged |
| 2 | `StageCompleted` | Event | domain | `domain/aggregates/events.py:103` | ~40 | unchanged |
| 3 | `DQThresholdExceeded` | Event | domain | `domain/aggregates/events.py:233` | ~15 | unchanged |
| 4 | `SchemaEvolutionDetected` | Event | domain | `domain/aggregates/events.py:249` | ~15 | unchanged |
| ~~5~~ | ~~`MoleculeFormSchema`~~ | ~~Schema~~ | ~~domain~~ | ~~`domain/schemas/chembl/molecule_form.py`~~ | ~~35~~ | **REMOVED** |
| ~~6~~ | ~~`TargetRelationSchema`~~ | ~~Schema~~ | ~~domain~~ | ~~`domain/schemas/chembl/target_relation.py`~~ | ~~38~~ | **REMOVED** |
| 5 | `ChemblStatusResponse` | Model | infrastructure | `infrastructure/adapters/chembl/models.py:611` | ~25 | unchanged |
| 6 | `HasProviderName` | Protocol | infrastructure | `infrastructure/adapters/filterable_mixin.py:23` | ~10 | unchanged |
| 7 | `HealthCheckObservability` | Protocol | infrastructure | `infrastructure/adapters/health_check_mixin.py:40` | ~15 | unchanged |
| 8 | `PageFetcher` | Protocol | infrastructure | `infrastructure/adapters/http/pagination.py:14` | ~10 | unchanged |

**Estimated dead class LOC: ~180** (was ~253; -73 from removed schemas)

### 1.2 DEAD Exceptions (0 references anywhere)

| # | Exception | Layer | Location | Status vs Previous |
|---|-----------|-------|----------|-------------------|
| 1 | `ConfigurationError` | domain | `domain/exceptions/infrastructure.py` | unchanged |
| 2 | `FileSystemError` | domain | `domain/exceptions/infrastructure.py` | unchanged |
| 3 | `InternalError` | domain | `domain/exceptions/internal.py` | unchanged |

### 1.3 DEAD Ports (0 implementation refs AND 0 import refs)

| # | Port | Location | Status vs Previous |
|---|------|----------|-------------------|
| 1 | `ActivityAggregatorPort` | `domain/ports/normalization.py` | unchanged |
| 2 | `HealthStatePort` | `domain/ports/health_check.py` | unchanged |
| 3 | `NormalizationServicePort` | `domain/ports/normalization.py` | unchanged |
| 4 | `OutlierFilterPort` | `domain/ports/normalization.py` | unchanged |
| 5 | `UnitConverterPort` | `domain/ports/normalization.py` | unchanged |
| 6 | `ValueValidatorPort` | `domain/ports/normalization.py` | unchanged |

Note: 5 of 6 dead ports are in `domain/ports/normalization.py` — the entire file's port contracts appear unused despite having concrete implementations in `domain/services/`.

### 1.4 TEST_ONLY Classes (0 production refs, test refs only)

| # | Object | Layer | Location | Test Refs | Status vs Previous |
|---|--------|-------|----------|-----------|-------------------|
| 1 | `TransformerPort` | application | `application/core/protocols.py:49` | 14 | unchanged |
| 2 | `MetricsCollector` | infrastructure | `infrastructure/observability/metrics.py:189` | 6 | unchanged |

### 1.5 TEST_ONLY Exceptions

| # | Exception | Location | Test Refs | Status vs Previous |
|---|-----------|----------|-----------|-------------------|
| 1 | `BucketNotFoundError` | `domain/exceptions/infrastructure.py` | 10 | unchanged |
| 2 | `UploadError` | `domain/exceptions/infrastructure.py` | 9 | unchanged |
| 3 | `StorageQuotaExceededError` | `domain/exceptions/infrastructure.py` | 9 | unchanged |
| 4 | `DeltaWriteConflictError` | `domain/exceptions/infrastructure.py` | 12 | unchanged |
| 5 | `DeltaTransactionError` | `domain/exceptions/infrastructure.py` | 10 | unchanged |
| 6 | `DeltaSchemaValidationError` | `domain/exceptions/infrastructure.py` | 12 | unchanged |
| 7 | `DeltaOptimizeError` | `domain/exceptions/infrastructure.py` | 10 | unchanged |
| 8 | `CheckpointConflictError` | `domain/exceptions/internal.py` | 3 | unchanged |
| 9 | `DataValidationError` | `domain/exceptions/network.py` | 3 | unchanged |

Note: Many of these TEST_ONLY exceptions are likely intentional (error hierarchy for future use / defensive coverage). Verify before removing.

### 1.6 Orphan Modules (files with 0 imports from codebase)

| # | File | LOC | Content | Status vs Previous |
|---|------|-----|---------|-------------------|
| 1 | `domain/config_types.py` | 446 | Type definitions (RateLimitDict etc.) | **STILL ORPHAN** — referenced only in a comment, types likely migrated to proper dataclasses |
| 2 | `domain/schemas/_field_orders.py` | 223 | Field ordering constants | **STILL ORPHAN** — zero imports in src or tests |
| ~~3~~ | ~~`domain/schemas/chembl/molecule_form.py`~~ | ~~35~~ | ~~MoleculeFormSchema~~ | **REMOVED** |
| ~~4~~ | ~~`domain/schemas/chembl/target_relation.py`~~ | ~~38~~ | ~~TargetRelationSchema~~ | **REMOVED** |
| ~~5~~ | ~~`domain/schemas/crossref/funder.py`~~ | ~~68~~ | ~~Funder schemas~~ | **REMOVED** |
| ~~6~~ | ~~`domain/schemas/crossref/author.py`~~ | ~~86~~ | ~~Author schemas~~ | **REMOVED** |
| ~~7~~ | ~~`domain/schemas/uniprot/isoform.py`~~ | ~~81~~ | ~~Isoform schemas~~ | **REMOVED** |
| 3 | `infrastructure/adapters/chembl/exceptions.py` | 116 | ChemblApiError hierarchy | **RECLASSIFIED** — not imported by any module in src/bioetl/ (not even via `__init__.py`); actual orphan |
| ~~9~~ | ~~`infrastructure/adapters/adapter_error_logging.py`~~ | ~~56~~ | ~~Error logging decorator~~ | **REMOVED** |
| 4 | `application/services/dq_metrics_calculator.py` | 25 | Deprecated re-export shim (warns on import) | **STILL ORPHAN** — nobody imports it |
| 5 | `application/core/subcellular_fraction_data_source.py` | ~50 | Data source class | **NEW** — not imported by any module, not wired in composition |

**Current orphan count: 5 modules (~860 LOC)**

### 1.7 DEAD Constants (0 references in production code)

| # | Object | Layer | File | Status | Notes |
|---|--------|-------|------|--------|-------|
| 1 | `STR` | application | `core/field_specs.py:35` | **DEAD** | Listed in `__all__` but never imported |
| 2 | `CLASSIFICATION_TABLE_SIZE` | domain | `mapping/publication_type_classification.py:1521` | **DEAD** | Zero refs anywhere |
| 3 | `ALL_PUBLICATION_ENTITY_TYPES` | domain | `registry/publication.py:171` | **DEAD** | Zero refs anywhere |
| 4 | `PUBLICATION_CANONICAL_CATEGORIES` | domain | `schemas/_field_orders.py:216` | **DEAD** | In orphan module |
| 5 | `PUBLICATION_FIELD_ORDER` | domain | `schemas/_field_orders.py:27` | **DEAD** | In orphan module (187 LOC) |
| 6 | `ALL_PUBLICATION_FIELDS` | domain | `schemas/column_order.py:84` | **DEAD** | Zero refs anywhere |
| 7 | `DOCUMENT_TYPES` | domain | `schemas/crossref/publication.py:23` | **DEAD** | Zero refs anywhere |
| 8 | `ALL_SUPPORTED_ENTITY_TYPES` | infrastructure | `adapters/chembl/entity_mapper.py:88` | **DEAD** | Zero refs anywhere |
| 9 | `ENTITY_MAPPING` | infrastructure | `adapters/chembl/entity_mapper.py:315` | **DEAD** | Re-aggregation dict, never consumed |
| 10 | `ENTITY_PLURAL` | infrastructure | `adapters/chembl/entity_mapper.py:326` | **DEAD** | Re-aggregation dict, never consumed |
| 11 | `PK_FIELD_OVERRIDES` | infrastructure | `adapters/chembl/entity_mapper.py:333` | **DEAD** | Re-aggregation dict, never consumed |
| 12 | `DEFAULT_HEALTH_CHECK_TIMEOUT_SECONDS` | infrastructure | `adapters/health_check_mixin.py:36` | **DEAD** | Defined but never used |
| 13 | `HEALTH_CHECK_FAILURES_TOTAL` | infrastructure | `observability/metrics.py:175` | **DEAD** | Prometheus metric, never used |
| 14 | `HEALTH_CHECK_LATENCY_SECONDS` | infrastructure | `observability/metrics.py:181` | **DEAD** | Prometheus metric, never used |
| 15 | `HEALTH_CHECK_SUCCESS_TOTAL` | infrastructure | `observability/metrics.py:169` | **DEAD** | Prometheus metric, never used |

### 1.8 TEST_ONLY Constants

| # | Object | Layer | File | Test Refs |
|---|--------|-------|------|-----------|
| 1 | `KNOWN_PARAM_TYPES` | application | `pipelines/chembl/assay_parameters_transformer.py:28` | 1 (test_chembl_assay_parameters.py) |
| 2 | `HEALTH_CHECK_DURATION_SECONDS` | infrastructure | `observability/metrics.py:160` | 2 (test_observability_contract.py) |
| 3 | `INFRASTRUCTURE_VALIDATED` | infrastructure | `observability/metrics.py:154` | 5 (test_observability_contract.py) |
| 4 | `PIPELINE_HEALTH_CHECK_PASSED` | infrastructure | `observability/metrics.py:148` | 5 (test_observability_contract.py) |

### 1.9 PROD_ONLY (no test coverage)

| # | Exception | Prod Refs | Status vs Previous |
|---|-----------|-----------|-------------------|
| 1 | `CachedBronzeEmptyError` | 2 (imported + raised in `cached_bronze_data_source.py`) | unchanged |

---

## 2. Duplicate Logic

### 2.1 Confirmed Duplicates — Same Name, Different Module (CRITICAL)

| # | Class | Definition A | Definition B | Definition C | Severity | Status vs Previous |
|---|-------|-------------|-------------|-------------|----------|-------------------|
| 1 | `NoOpTracing` | `domain/ports/noop.py` | `infrastructure/observability/noop_tracing.py` | — | **HIGH** | unchanged |
| 2 | `NoOpMetrics` | `domain/ports/noop.py` | `infrastructure/observability/noop_metrics.py` | — | **HIGH** | unchanged |
| 3 | `CircuitBreakerConfig` | `domain/resilience.py` | `infrastructure/schemas/pipeline_config.py` | `composition/bootstrap_contexts.py` | **HIGH** | unchanged (composition version is likely redundant) |
| 4 | `DriftLevel` | `domain/types.py` | `domain/value_objects/dq_report.py` | — | **CRITICAL** | unchanged — UPPERCASE vs lowercase values |
| 5 | `DQConfig` | `domain/config.py` | `infrastructure/schemas/pipeline_config.py` | — | **MEDIUM** | unchanged |
| 6 | `DQReportConfig` | `domain/config.py` | `infrastructure/schemas/pipeline_config.py` | — | **MEDIUM** | unchanged |
| 7 | `InputFilterConfig` | `domain/filtering/input_config.py` | `infrastructure/schemas/pipeline_config.py` | — | **MEDIUM** | unchanged |
| 8 | `RunStatus` | `domain/aggregates/pipeline_run.py` | `application/services/pipeline_runner_service.py` | — | **HIGH** | unchanged — different members (5 vs 4) |
| 9 | `ValidationResult` | `domain/types.py` | `infrastructure/adapters/validation.py` | — | **MEDIUM** | unchanged |
| 10 | `CleanupResult` | `application/core/cleanup_service.py` | `application/services/bronze_cleanup_service.py` | — | **LOW** | unchanged |
| 11 | `LineageMetadata` | `domain/composite/lineage.py` | `domain/models/metadata.py` | — | **MEDIUM** | unchanged |
| 12 | `ChemblPublicationRecord` | `domain/entities/chembl.py:511` | `infrastructure/adapters/chembl/models.py:467` | — | **HIGH** | unchanged |
| 13 | `PubchemMoleculeRecord` | `domain/entities/pubchem.py:24` | `infrastructure/adapters/pubchem/models.py:19` | — | **HIGH** | unchanged |
| 14 | `TitleFallbackHandler` | `crossref/fallback.py:25` | `openalex/fallback.py:21` | `pubmed/fallback.py:21` | **LOW** | unchanged |
| 15 | `BaseClientConfig` | `domain/configs/base.py:56` | `infrastructure/schemas/base_schemas.py:151` | — | **MEDIUM** | unchanged |
| 16 | `RateLimitConfig` | `domain/configs/base.py:20` | `composition/bootstrap_contexts.py:105` | — | **MEDIUM** | unchanged |

### 2.2 Confirmed Duplicates — Same Logic, Different Location

| # | Function/Logic | Location A | Location B | Severity | Status vs Previous |
|---|----------------|-----------|-----------|----------|-------------------|
| 1 | `normalize_string()` | `domain/normalization.py:16` | `application/core/dict_transformers.py:198` | **MEDIUM** | unchanged |
| 2 | `parse_date_field()` | `domain/normalization.py:88` | `application/core/dict_transformers.py:223` | **MEDIUM** | unchanged |
| 3 | `parse_page_range()` | `domain/normalization.py:160` | `semanticscholar/_page_parsing.py:124` | **HIGH** | unchanged |
| 4 | `normalize_doi()` | `domain/normalization.py:32` | `openalex/client.py:591` + `semanticscholar/adapter.py:463` | **MEDIUM** | unchanged |
| 5 | `_normalize_for_hash()` | `domain/transformations.py:81` | `domain/services/identity_service.py:119` + `composition/services/versioning.py:65` | **HIGH** | unchanged |

### 2.3 Infrastructure Schema Duplicates (to_domain conversion)

| # | Object A | Object B | Similarity | LOC | Severity | Status vs Previous |
|---|----------|----------|-----------|-----|----------|-------------------|
| 1 | `BaseGoldFiltersConfig.to_domain` (base_schemas.py:551) | `GoldFiltersConfig.to_domain` (pipeline_config.py:795) | AST-identical | 61 | **CRITICAL** | **STILL PRESENT** — both extend BaseModel independently, no inheritance |
| 2 | `BaseInputFilterConfig.to_domain` (base_schemas.py:333) | `InputFilterConfig.to_domain` (pipeline_config.py:363) | AST-identical | 35 | **HIGH** | **STILL PRESENT** — both extend BaseModel independently, no inheritance |
| 3 | `BaseTitleFallbackHandler._process_found_result` | `SemanticScholarTitleFallbackHandler._process_found_result` | Identical override | 15 | **MEDIUM** | **STILL PRESENT** — SemanticScholar overrides base with identical code (no-op) |

### 2.4 Resolved Duplicates (since previous report)

| # | Object A | Object B | Resolution |
|---|----------|----------|-----------|
| 1 | `PubChemCompoundPipeline` (`__init__.py`) | `PubChemCompoundPipeline` (`compound.py`) | **RESOLVED** — `compound.py` removed |
| 2 | `PubMedPublicationPipeline` (`__init__.py`) | `PubMedPublicationPipeline` (`publication.py`) | **RESOLVED** — `publication.py` removed |
| 3 | `UniProtProteinPipeline` (`__init__.py`) | `UniProtProteinPipeline` (`protein.py`) | **RESOLVED** — `protein.py` removed |

### 2.5 Normalization Hierarchy Confusion (CRITICAL structural duplication)

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

**Finding:** `domain/normalization.py` standalone functions overlap significantly with `DataNormalizationService` methods. System A's ports are all dead — the concrete services exist but ports are unused.

### 2.6 NoOp Implementation Duplication (470 + 199 = 669 LOC)

Two parallel NoOp hierarchies exist:

**domain/ports/noop.py** (470 LOC):
- `NoOpTracing`, `NoOpMetrics`, `NoOpAudit`, `NoOpPiiHasher`, `NoOpMemoryMonitor`, `NoOpMetadataWriter`
- Used via `from bioetl.domain.ports import NoOp*` (application/infrastructure layers)

**infrastructure/observability/noop_*.py** (199 LOC total):
- `NoOpLogger` (51 LOC), `NoOpMetrics` (88 LOC), `NoOpTracing` (60 LOC)
- Used via `from bioetl.infrastructure.observability.noop_* import *` (composition/tests)

**Overlap:** `NoOpTracing` and `NoOpMetrics` exist in BOTH locations with separate implementations.

---

## 3. Dependency Map

### 3.1 Highest Fan-In Modules (most depended upon)

| # | Module | Fan-In (files importing it) | Breakdown |
|---|--------|:---------------------------:|-----------|
| 1 | `bioetl.domain.ports` | 144 | application: 64, infrastructure: 49, composition: 23, domain: 6, interfaces: 2 |
| 2 | `bioetl.domain.types` | 123 | application: 48, domain: 33, infrastructure: 28, composition: 11, interfaces: 3 |
| 3 | `bioetl.domain.exceptions` | 37 | — |
| 4 | `bioetl.domain.filtering` | 31 | — |
| 5 | `bioetl.domain.context` | 29 | — |
| 6 | `bioetl.domain.config` | 24 | — |
| 7 | `bioetl.infrastructure.config` | 23 | — |
| 8 | `bioetl.domain.models.metadata` | 22 | — |
| 9 | `bioetl.domain.schemas.base` | 22 | — |
| 10 | `bioetl.domain.entities` | 18 | — |

### 3.2 Highest Fan-Out Modules

| # | Module | Fan-Out (import lines) | Notes |
|---|--------|:----------------------:|-------|
| 1 | `composition/factories/pipeline_factories.py` | 50 | Central pipeline registration |
| 2 | `composition/factories/pipeline_factory.py` | 33 | ~18 under TYPE_CHECKING |
| 3 | `composition/factories/services_factory.py` | 33 | ~15 under TYPE_CHECKING |
| 4 | `composition/factories/transformer_factory.py` | ~24 | — |
| 5 | `composition/bootstrap/runtime/composite.py` | ~21 | — |

### 3.3 Import Cycles

| # | Cycle | Length | Mitigation | Status |
|---|-------|--------|-----------|--------|
| 1 | `infrastructure.config` → `config._base` → `schemas.pipeline_config` → `infrastructure.config` | 3 | Deferred import in `pipeline_config.py:1106` (inside `to_domain()`) | Mitigated, no runtime failure |
| 2 | `infrastructure.config` → `pipeline_config_loader` → `schemas.pipeline_config` → `infrastructure.config` | 3 | Same deferred import as cycle 1 | Mitigated |
| 3 | `composition.bootstrap` → `runtime` → `runner` → `runner_factory` → `bootstrap` | 4 | Deferred import in `runner_factory.py:75` (explicit comment: "Import inside method to avoid circular import") | Mitigated, developer-documented |
| 4 | `providers._config_helpers` → `data_source_factory` → `providers` → `registration` → `_config_helpers` | 4 | `_config_helpers` imports `data_source_factory` under `TYPE_CHECKING` only | Mitigated at runtime |
| ~~5~~ | ~~`bootstrap` → `runtime` → `composite` → `entrypoints`~~ | ~~4~~ | — | **DOES NOT EXIST** (previously reported incorrectly) |

### 3.4 Domain DriftLevel Enum Conflict

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

Import split:
- `from bioetl.domain import DriftLevel` → UPPERCASE values (from `domain/types.py`)
- `from bioetl.domain.value_objects import DriftLevel` → lowercase values (from `dq_report.py`)
- `domain/transformations.py` uses the UPPERCASE version
- `application/services/dq/silver_analyzer.py` uses the lowercase version

---

## 4. Recommendations

### 4.1 Immediate Actions (Quick Wins)

| # | Action | Objects | Impact | Effort | Status |
|---|--------|---------|--------|--------|--------|
| ~~QW-1~~ | ~~Remove dead schemas~~ | ~~`molecule_form.py`, `target_relation.py`~~ | ~~-73 LOC~~ | ~~Trivial~~ | **DONE** |
| QW-2 | **Remove dead events** | `PipelineStarted`, `StageCompleted`, `DQThresholdExceeded`, `SchemaEvolutionDetected` | -120 LOC | Trivial | open |
| QW-3 | **Remove dead exceptions** | `ConfigurationError`, `FileSystemError`, `InternalError` | -30 LOC | Trivial | open |
| QW-4 | **Remove dead infra classes** | `ChemblStatusResponse`, `HasProviderName`, `HealthCheckObservability`, `PageFetcher` | -60 LOC | Low | open |
| QW-5 | **Remove orphan `config_types.py`** | `domain/config_types.py` | -446 LOC | Verify first | open |
| QW-6 | **Remove orphan `_field_orders.py`** | `domain/schemas/_field_orders.py` | -223 LOC | Verify first | open |
| QW-7 | **Remove orphan `dq_metrics_calculator.py`** (application) | `application/services/dq_metrics_calculator.py` | -25 LOC | Trivial | open |
| QW-8 | **Fix DriftLevel enum conflict** | `domain/types.py` vs `domain/value_objects/dq_report.py` | Bug risk | Medium | open |
| QW-9 | **Remove dead constants** | 15 constants (see 1.7) | -30 LOC | Low | **NEW** |
| QW-10 | **Remove orphan `chembl/exceptions.py`** | `infrastructure/adapters/chembl/exceptions.py` | -116 LOC | Verify first | **NEW** (reclassified) |

**Total quick-win LOC removal: ~1,050 LOC** (was ~977)

### 4.2 Refactorings (Require Planning)

| # | RF-ID | Description | Objects | Impact | Risk | Status |
|---|-------|-------------|---------|--------|------|--------|
| 1 | RF-NOOP | **Consolidate NoOp implementations** | 2 `NoOpTracing`, 2 `NoOpMetrics`, `NoOpLogger` | -199 LOC | Medium | open |
| 2 | RF-NORM | **Clean normalization hierarchy** — Remove dead ports; clarify overlap | 5 dead ports, ~10 functions | Architecture | High | open |
| 3 | RF-CBCFG | **Unify CircuitBreakerConfig** — Consolidate triple definition | 3 definitions | Type safety | Medium | open |
| 4 | RF-RUNST | **Resolve RunStatus duplication** | 2 definitions | Naming | Low | open |
| 5 | RF-ENTITY | **Resolve entity/model duplication** | `ChemblPublicationRecord`, `PubchemMoleculeRecord` | Architecture | High | open |
| 6 | RF-DRIFT | **Fix DriftLevel enum values** | 2 definitions | Bug prevention | Low | open |
| 7 | RF-PAGES | **Consolidate `parse_page_range`** | 2 functions | DRY | Low | open |
| 8 | RF-HASH | **Consolidate `normalize_for_hash`** | 3 functions | DRY | Medium | open |
| ~~9~~ | ~~RF-ORPHAN-SCHEMAS~~ | ~~Decide on orphan schemas~~ | ~~3 modules~~ | ~~-235 LOC~~ | ~~Low~~ | **DONE** (removed) |
| ~~10~~ | ~~RF-PIPELINES~~ | ~~Remove pipeline double definitions~~ | ~~3 pairs~~ | ~~clarity~~ | ~~Low~~ | **DONE** (removed) |
| 9 | RF-TODOMAIN | **Deduplicate to_domain() converters** — `BaseGoldFiltersConfig`/`GoldFiltersConfig` and `BaseInputFilterConfig`/`InputFilterConfig` | 2 pairs | -96 LOC, DRY | Medium | **NEW** |
| 10 | RF-FALLBACK | **Remove redundant SemanticScholar fallback override** | 1 method | -15 LOC, clarity | Low | **NEW** |

### 4.3 Layer Health Summary

| Layer | Dead Objects | Duplicates | Orphans | Health | Trend |
|-------|-------------|------------|---------|--------|-------|
| domain | 4 classes + 3 exceptions + 6 ports + 7 constants | DriftLevel, RunStatus, normalization overlap | 2 files (669 LOC) | ⚠️ | improved (orphans reduced) |
| application | 0 classes (1 TEST_ONLY) + 1 constant | normalize_string/parse_date_field wrappers | 2 files (75 LOC) | ⚠️ | slight decline (new orphan found) |
| infrastructure | 4 classes (1 TEST_ONLY) + 7 constants | NoOp overlap, entity/model duplication, to_domain() duplication | 1 file (116 LOC) | ⚠️ | unchanged |
| composition | 0 | CircuitBreakerConfig, RateLimitConfig | 0 | ✅ | stable |
| interfaces | 0 | 0 | 0 | ✅ | stable |

---

## 5. Checklist

- [x] Object registry collected for all 5 layers
- [x] Reference count analyzed for all classes (dead/test-only/active)
- [x] Dead code identified and verified against exception list
- [x] Cross-provider duplication analyzed (transformers, clients, fallbacks)
- [x] Cross-layer duplication analyzed (NoOps, configs, entities, normalization)
- [x] Orphan modules identified and re-verified
- [x] Duplicate class names cataloged
- [x] DriftLevel enum conflict flagged as CRITICAL
- [x] Infrastructure schema to_domain() duplication verified
- [x] Dead constants inventory added
- [x] Import cycles verified (1 false positive removed)
- [x] Fan-in/fan-out metrics updated
- [x] Pipeline double definitions confirmed resolved
- [x] Orphan schema files confirmed removed
- [x] Recommendations prioritized and status tracked

---

## Appendix A: Methodology

Analysis performed using:
- `grep -rn` for class/function extraction and reference counting
- AST-level analysis for constant/function/class enumeration
- Module-level import graph construction (excluding `TYPE_CHECKING` blocks)
- Token-based identifier search for cross-reference validation
- Manual file comparison for semantic duplication (normalization, NoOp, configs, to_domain converters)
- Orphan detection via module-level import pattern matching
- Cross-referencing with `tests/` directory for TEST_ONLY classification

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

---

## Appendix C: Resolved Items Since Previous Report

| Item | Category | Resolution |
|------|----------|-----------|
| `MoleculeFormSchema` | Dead class + orphan | File `domain/schemas/chembl/molecule_form.py` removed |
| `TargetRelationSchema` | Dead class + orphan | File `domain/schemas/chembl/target_relation.py` removed |
| `crossref/author.py` | Orphan schema | File removed |
| `crossref/funder.py` | Orphan schema | File removed |
| `crossref/reference.py` | Orphan schema | File removed |
| `uniprot/isoform.py` | Orphan schema | File removed |
| `adapter_error_logging.py` | Orphan module | File removed |
| `PubChemCompoundPipeline` double def | Duplicate class | `compound.py` removed; single definition in `__init__.py` |
| `PubMedPublicationPipeline` double def | Duplicate class | `publication.py` removed; single definition in `__init__.py` |
| `UniProtProteinPipeline` double def | Duplicate class | `protein.py` removed; single definition in `__init__.py` |

---

## Appendix D: Промпты для модификации кода

Готовые к использованию промпты. Каждый промпт самодостаточен — содержит контекст,
файлы и ожидаемый результат. Рекомендуется выполнять в указанном порядке:
Quick Wins (QW) → Refactorings (RF).

---

### QW-2: Удаление мёртвых Event-классов

```
Удали 4 мёртвых Event-класса из src/bioetl/domain/aggregates/events.py:

- PipelineStarted (строка ~48)
- StageCompleted (строка ~103)
- DQThresholdExceeded (строка ~233)
- SchemaEvolutionDetected (строка ~249)

Все 4 класса наследуют DomainEvent, но не используются ни в production, ни в тестах
(0 ссылок в src/bioetl/, 0 ссылок в tests/). Они НЕ экспортируются из
domain/aggregates/__init__.py.

Шаги:
1. Удали определения 4 классов из events.py.
2. Удали импорты, ставшие ненужными (если какой-то import используется только этими классами).
3. Убедись что файл events.py остаётся синтаксически корректным.
4. Запусти: grep -rn "PipelineStarted\|StageCompleted\|DQThresholdExceeded\|SchemaEvolutionDetected" src/ tests/ — должно быть 0 результатов.
5. Запусти pytest tests/unit/domain/aggregates/ -x — тесты должны проходить.

Ожидаемый результат: −120 LOC, без поломок.
```

---

### QW-3: Удаление мёртвых Exceptions

```
Удали 3 мёртвых исключения, которые определены и ре-экспортируются, но нигде не используются:

1. ConfigurationError в src/bioetl/domain/exceptions/infrastructure.py (строка ~57)
2. FileSystemError в src/bioetl/domain/exceptions/infrastructure.py (строка ~82)
3. InternalError в src/bioetl/domain/exceptions/internal.py (строка ~24)

Шаги:
1. Удали определения классов из соответствующих файлов.
2. Удали их из __all__ и из import-строк в src/bioetl/domain/exceptions/__init__.py.
3. Проверь что domain/__init__.py не ре-экспортирует их — если да, удали оттуда тоже.
4. Запусти: grep -rn "ConfigurationError\|FileSystemError\|InternalError" src/bioetl/ tests/ --include="*.py" — убедись что осталось 0 ссылок (кроме возможных строк в самих удалённых определениях).
5. Запусти pytest tests/unit/domain/ -x и pytest tests/architecture/ -x.

Ожидаемый результат: −30 LOC. Эти исключения не импортируются и не выбрасываются нигде.
```

---

### QW-4: Удаление мёртвых инфраструктурных классов

```
Удали 4 мёртвых класса из infrastructure-слоя (0 ссылок в production и тестах):

1. ChemblStatusResponse в src/bioetl/infrastructure/adapters/chembl/models.py (строка ~611)
   — Pydantic-модель для ответа ChEMBL status, не используется нигде.

2. HasProviderName в src/bioetl/infrastructure/adapters/filterable_mixin.py (строка ~22)
   — Protocol с единственным полем provider_name, не используется.

3. HealthCheckObservability в src/bioetl/infrastructure/adapters/health_check_mixin.py (строка ~39)
   — Protocol для health check адаптеров, не используется.

4. PageFetcher в src/bioetl/infrastructure/adapters/http/pagination.py (строка ~14)
   — Generic Protocol для пагинированного fetch, не используется.

Шаги:
1. Удали каждый класс из файла.
2. Если класс упомянут в __all__ своего модуля — удали из __all__.
3. Удали ставшие ненужными импорты (typing.Protocol, runtime_checkable и т.д.) если они не используются другими классами в том же файле.
4. Запусти: grep -rn "ChemblStatusResponse\|HasProviderName\|HealthCheckObservability\|PageFetcher" src/ tests/ — 0 результатов.
5. Запусти pytest tests/unit/infrastructure/ -x.

Ожидаемый результат: −60 LOC.
```

---

### QW-5: Удаление orphan-модуля config_types.py

```
Удали orphan-файл src/bioetl/domain/config_types.py (446 LOC).

Контекст: файл содержит TypedDict-определения (RateLimitDict, RetryPolicyDict и др.),
которые были вытеснены dataclass-аналогами в domain/configs/ и domain/resilience.py.
Единственная "ссылка" — комментарий в domain/configs/base.py, а не import.

Шаги:
1. Проверь: grep -rn "config_types" src/bioetl/ — должно быть 0 import-ов (только комментарий).
2. Проверь: grep -rn "RateLimitDict\|RetryPolicyDict\|CircuitBreakerDict\|HealthCheckDict" src/bioetl/ — убедись что TypedDict-имена из этого файла не используются нигде.
3. Удали файл: src/bioetl/domain/config_types.py.
4. Если есть ссылка в domain/__init__.py — удали.
5. Запусти pytest tests/ -x --timeout=60.

Ожидаемый результат: −446 LOC. Файл не импортируется, типы мигрированы.
```

---

### QW-6: Удаление orphan-модуля _field_orders.py

```
Удали orphan-файл src/bioetl/domain/schemas/_field_orders.py (223 LOC).

Контекст: файл содержит PUBLICATION_FIELD_ORDER и PUBLICATION_CANONICAL_CATEGORIES —
константы порядка полей, не импортируемые ни в production, ни в тестах. Функциональность
перенесена в domain/schemas/column_order.py и domain/value_objects/column_order.py.

Шаги:
1. Проверь: grep -rn "_field_orders\|PUBLICATION_FIELD_ORDER\|PUBLICATION_CANONICAL_CATEGORIES" src/bioetl/ tests/ — должно быть 0 import-ов.
2. Удали файл: src/bioetl/domain/schemas/_field_orders.py.
3. Запусти pytest tests/ -x --timeout=60.

Ожидаемый результат: −223 LOC.
```

---

### QW-7: Удаление deprecated shim dq_metrics_calculator.py

```
Удали deprecated re-export shim src/bioetl/application/services/dq_metrics_calculator.py (25 LOC).

Контекст: файл содержит DeprecationWarning и ре-экспорт из bioetl.domain.services.dq_metrics_calculator.
Никто не импортирует из bioetl.application.services.dq_metrics_calculator —
все потребители уже используют domain-версию напрямую.

Шаги:
1. Проверь: grep -rn "from bioetl.application.services.dq_metrics_calculator" src/ tests/ — 0 результатов.
2. Удали файл.
3. Если application/services/__init__.py содержит import из этого модуля — проверь что import идёт из domain.services, а не из application.services.
4. Запусти pytest tests/ -x --timeout=60.

Ожидаемый результат: −25 LOC.
```

---

### QW-8 / RF-DRIFT: Устранение конфликта DriftLevel enum

```
Устрани конфликт двух DriftLevel enum с разными значениями:

- src/bioetl/domain/types.py:83 — DriftLevel(StrEnum) со значениями "INFO", "WARN", "CRITICAL" (UPPERCASE)
- src/bioetl/domain/value_objects/dq_report.py:41 — DriftLevel(StrEnum) со значениями "info", "warn", "critical" (lowercase)

Это BUG RISK: `from bioetl.domain import DriftLevel` и `from bioetl.domain.value_objects import DriftLevel`
дают разные классы с разными строковыми значениями.

Потребители:
- domain/transformations.py → импортирует из domain.types (UPPERCASE)
- application/services/dq/silver_analyzer.py → импортирует из domain.value_objects.dq_report (lowercase)

Шаги:
1. Определи каноническую версию: domain/types.py (UPPERCASE) — она используется в domain/transformations.py, ре-экспортируется из domain/__init__.py.
2. В src/bioetl/domain/value_objects/dq_report.py: удали определение DriftLevel, замени на import из domain.types:
   `from bioetl.domain.types import DriftLevel`
3. В domain/value_objects/__init__.py: замени ре-экспорт так, чтобы он указывал на единственный DriftLevel.
4. В application/services/dq/silver_analyzer.py: обнови import на `from bioetl.domain.types import DriftLevel`.
5. Найди все места сравнения с lowercase строками ("info", "warn", "critical") и обнови на UPPERCASE ("INFO", "WARN", "CRITICAL") или на enum-члены.
6. Запусти: grep -rn "DriftLevel" src/bioetl/ — убедись что все import ведут к единому определению.
7. Запусти pytest tests/ -x.

Ожидаемый результат: единый DriftLevel enum, устранённый риск silent bugs при сравнении.
```

---

### QW-9: Удаление мёртвых констант

```
Удали 15 мёртвых констант (0 ссылок в production-коде):

Файл src/bioetl/application/core/field_specs.py:
- STR (строка ~35) — удали из файла и из __all__

Файл src/bioetl/domain/mapping/publication_type_classification.py:
- CLASSIFICATION_TABLE_SIZE (строка ~1521)

Файл src/bioetl/domain/registry/publication.py:
- ALL_PUBLICATION_ENTITY_TYPES (строка ~171)

Файл src/bioetl/domain/schemas/column_order.py:
- ALL_PUBLICATION_FIELDS (строка ~84)

Файл src/bioetl/domain/schemas/crossref/publication.py:
- DOCUMENT_TYPES (строка ~23)

Файл src/bioetl/infrastructure/adapters/chembl/entity_mapper.py:
- ALL_SUPPORTED_ENTITY_TYPES (строка ~88)
- ENTITY_MAPPING (строка ~315)
- ENTITY_PLURAL (строка ~326)
- PK_FIELD_OVERRIDES (строка ~333)

Файл src/bioetl/infrastructure/adapters/health_check_mixin.py:
- DEFAULT_HEALTH_CHECK_TIMEOUT_SECONDS (строка ~36)

Файл src/bioetl/infrastructure/observability/metrics.py:
- HEALTH_CHECK_FAILURES_TOTAL (строка ~175)
- HEALTH_CHECK_LATENCY_SECONDS (строка ~181)
- HEALTH_CHECK_SUCCESS_TOTAL (строка ~169)

Шаги:
1. Для каждой константы проверь: grep -rn "CONSTANT_NAME" src/bioetl/ tests/ — 0 ссылок кроме определения.
2. Удали определение из файла.
3. Если константа в __all__ — удали из __all__.
4. Удали ставшие ненужными imports.
5. Запусти pytest tests/ -x.

Ожидаемый результат: −30 LOC, чище кодовая база.
```

---

### QW-10: Удаление orphan-модуля chembl/exceptions.py

```
Удали orphan-файл src/bioetl/infrastructure/adapters/chembl/exceptions.py (116 LOC).

Контекст: файл содержит иерархию ChemblApiError, но НЕ импортируется ни одним модулем
в src/bioetl/ — ни напрямую, ни через chembl/__init__.py. Ошибки ChEMBL-адаптера
обрабатываются через domain/exceptions/.

Шаги:
1. Проверь: grep -rn "from bioetl.infrastructure.adapters.chembl.exceptions\|from bioetl.infrastructure.adapters.chembl import.*Error\|ChemblApiError" src/bioetl/ — должно быть 0 import-ов из этого модуля.
2. Проверь chembl/__init__.py — убедись что нет ре-экспорта из exceptions.
3. Удали файл.
4. Запусти pytest tests/unit/infrastructure/adapters/chembl/ -x.

Ожидаемый результат: −116 LOC.
```

---

### RF-NOOP: Консолидация NoOp-реализаций

```
Консолидируй две параллельные NoOp-иерархии в единую каноническую локацию.

Сейчас:
- domain/ports/noop.py (470 LOC): NoOpTracing, NoOpMetrics, NoOpAudit, NoOpPiiHasher, NoOpMemoryMonitor, NoOpMetadataWriter
- infrastructure/observability/noop_tracing.py (60 LOC): NoOpTracing (дубликат)
- infrastructure/observability/noop_metrics.py (88 LOC): NoOpMetrics (дубликат, расширенный с warn_on_use)

Дубли: NoOpTracing и NoOpMetrics определены в обоих местах с разными реализациями.

Потребители domain/ports/noop.py:
- application/core/base_transformer.py, batch_tracing.py
- infrastructure/adapters/http/client.py, bronze_writer.py, gold_writer.py
- infrastructure/adapters/base.py, sync_base.py, health_check_mixin.py
- Все provider clients (chembl, crossref, openalex, pubmed, semanticscholar, uniprot)

Потребители infrastructure/observability/noop_*.py:
- composition/bootstrap/assembly/storage.py, cli/noop.py, runtime/observability.py
- composition/factories/services_factory.py, storage_factory.py
- infrastructure/storage/silver_writer.py

Шаги:
1. Каноническая локация: domain/ports/noop.py (больше потребителей, ближе к портам).
2. Если infrastructure NoOpMetrics имеет полезную логику warn_on_use — перенеси её в domain-версию.
3. В каждом потребителе infrastructure/observability/noop_*.py замени import на domain/ports:
   `from bioetl.domain.ports import NoOpTracing, NoOpMetrics`
4. Удали файлы infrastructure/observability/noop_tracing.py и noop_metrics.py.
5. Обнови infrastructure/observability/__init__.py (убери ре-экспорты удалённых модулей).
6. Запусти: grep -rn "from bioetl.infrastructure.observability.noop_tracing\|from bioetl.infrastructure.observability.noop_metrics" src/ — 0 результатов.
7. Запусти pytest tests/ -x и pytest tests/architecture/ -x.

Ожидаемый результат: −148 LOC (noop_tracing.py + noop_metrics.py), единая точка определения NoOp.
```

---

### RF-NORM: Очистка нормализационной иерархии

```
Очисти нормализационную иерархию domain-слоя, которая содержит 3 пересекающиеся системы.

Проблема:
- System A: domain/ports/normalization.py — 5 DEAD портов (0 ссылок): ActivityAggregatorPort,
  NormalizationServicePort, OutlierFilterPort, UnitConverterPort, ValueValidatorPort.
  Конкретные сервисы (NormalizationService, UnitConverter и др.) используются напрямую, минуя порты.
- System B: domain/ports/data_normalization.py — DataNormalizationPort (ACTIVE, 12 refs). OK.
- System C: domain/normalization.py — standalone-функции (normalize_string, normalize_doi,
  parse_date_field и др.), частично дублирующие DataNormalizationService.

Шаги:
1. Удали 5 мёртвых портов из src/bioetl/domain/ports/normalization.py.
2. Удали ре-экспорт этих портов из domain/ports/__init__.py:
   - ActivityAggregatorPort
   - NormalizationServicePort
   - OutlierFilterPort
   - UnitConverterPort
   - ValueValidatorPort
3. Если domain/ports/normalization.py стал пустым — удали файл.
4. Проверь domain/__init__.py — удали ре-экспорт мёртвых портов если есть.
5. Запусти pytest tests/architecture/ -x — архитектурные тесты должны проходить.
6. Запусти pytest tests/ -x.

Примечание: Консолидация standalone-функций в normalization.py с DataNormalizationService
требует отдельного рефакторинга — здесь удаляем только мёртвые порты.

Ожидаемый результат: −5 мёртвых Protocol-классов, чище port-контракты.
```

---

### RF-TODOMAIN: Дедупликация to_domain() конвертеров

```
Устрани дублирование to_domain() методов между base_schemas.py и pipeline_config.py.

Дубли:
1. BaseGoldFiltersConfig.to_domain() в src/bioetl/infrastructure/schemas/base_schemas.py (строка ~551, 61 LOC)
   vs GoldFiltersConfig.to_domain() в src/bioetl/infrastructure/schemas/pipeline_config.py (строка ~795)
   — AST-идентичны. Оба класса наследуют BaseModel напрямую, без наследования друг от друга.

2. BaseInputFilterConfig.to_domain() в base_schemas.py (строка ~333, 35 LOC)
   vs InputFilterConfig.to_domain() в pipeline_config.py (строка ~363)
   — AST-идентичны. Та же ситуация.

Варианты решения (выбери один):

A) Наследование: GoldFiltersConfig(BaseGoldFiltersConfig) и InputFilterConfig(BaseInputFilterConfig)
   — to_domain() наследуется автоматически. Нужно проверить совместимость полей Pydantic.

B) Общий mixin/helper: вынести логику конвертации в standalone-функцию:
   def _gold_filters_to_domain(config: BaseModel) -> GoldFilterConfig: ...
   и вызывать из обоих классов.

C) Делегирование: pipeline_config.py-версии делегируют к base_schemas.py:
   def to_domain(self): return BaseGoldFiltersConfig(**self.model_dump()).to_domain()

Шаги:
1. Сравни поля BaseGoldFiltersConfig и GoldFiltersConfig — если идентичны, используй вариант A.
2. Аналогично для BaseInputFilterConfig и InputFilterConfig.
3. Удали дублирующий to_domain() из pipeline_config.py-версий.
4. Запусти pytest tests/unit/infrastructure/schemas/ -x.
5. Запусти pytest tests/ -x.

Ожидаемый результат: −96 LOC, единая точка конвертации schema→domain.
```

---

### RF-FALLBACK: Удаление избыточного override в SemanticScholar fallback

```
Удали избыточный override метода _process_found_result в SemanticScholarTitleFallbackHandler.

Файл: src/bioetl/infrastructure/adapters/semanticscholar/fallback.py
Класс: SemanticScholarTitleFallbackHandler (наследует BaseTitleFallbackHandler)
Метод: _process_found_result — переопределяет базовый метод идентичным кодом (no-op override).

Базовый метод в src/bioetl/infrastructure/adapters/common/base_title_fallback.py:
  result["_lookup_method"] = "title_fallback"
  result["_original_id"] = original_doi

Override в SemanticScholar делает ровно то же самое — нет кастомной логики.

Шаги:
1. Удали метод _process_found_result из SemanticScholarTitleFallbackHandler.
2. Базовая реализация будет использоваться автоматически через наследование.
3. Запусти pytest tests/unit/infrastructure/adapters/semanticscholar/ -x.
4. Запусти pytest tests/ -x.

Ожидаемый результат: −15 LOC, наследование работает как задумано.
```

---

### RF-CBCFG: Консолидация CircuitBreakerConfig

```
Устрани тройное определение CircuitBreakerConfig (3 класса в разных слоях).

Текущее состояние:
1. src/bioetl/domain/resilience.py:124 — @dataclass (frozen) — каноническое domain value object
2. src/bioetl/infrastructure/schemas/pipeline_config.py:267 — Pydantic BaseModel с to_domain() — OK (schema→domain converter pattern)
3. src/bioetl/composition/bootstrap_contexts.py:120 — @dataclass — ДУБЛИКАТ domain-версии

Потребители composition-версии:
- composition/providers/_config_helpers.py

Шаги:
1. В composition/bootstrap_contexts.py: удали определение CircuitBreakerConfig.
2. Замени на import из domain: `from bioetl.domain.resilience import CircuitBreakerConfig`
3. В composition/providers/_config_helpers.py: обнови import если он шёл из bootstrap_contexts.
4. Убедись что domain/resilience.py:CircuitBreakerConfig имеет все поля, которые были в composition-версии.
5. Запусти pytest tests/ -x.

Примечание: Pydantic-версия в pipeline_config.py — штатный паттерн (YAML schema → domain).
Оставляем её. Удаляем только composition-дубль.

Ожидаемый результат: −20 LOC, два определения вместо трёх.
```

---

### RF-RUNST: Разрешение дублирования RunStatus

```
Разреши конфликт двух RunStatus enum с разными членами.

Текущее состояние:
1. src/bioetl/domain/aggregates/pipeline_run.py:27 — RunStatus(StrEnum):
   PENDING, RUNNING, COMPLETED, FAILED, SHUTDOWN — состояния жизненного цикла PipelineRun aggregate.

2. src/bioetl/application/services/pipeline_runner_service.py:34 — RunStatus(StrEnum):
   SUCCESS, SHUTDOWN, FAILED, DRY_RUN — результат выполнения runner service.

Семантически это РАЗНЫЕ enum с одинаковым именем:
- Domain: lifecycle state (PENDING→RUNNING→COMPLETED/FAILED/SHUTDOWN)
- Application: outcome status (SUCCESS/FAILED/SHUTDOWN/DRY_RUN)

Шаги:
1. Переименуй application-версию в PipelineRunResult или RunOutcome:
   - В src/bioetl/application/services/pipeline_runner_service.py
   - Обнови все import в composition/ и interfaces/cli/
2. Оставь domain-версию RunStatus без изменений.
3. grep -rn "RunStatus" src/bioetl/ — убедись что нет путаницы.
4. Запусти pytest tests/ -x.

Ожидаемый результат: устранена двусмысленность имён, 0 LOC изменение.
```

---

### RF-ENTITY: Разрешение entity/model дублирования

```
Разреши дублирование entity-классов между domain/entities и infrastructure/adapters:

1. ChemblPublicationRecord:
   - src/bioetl/domain/entities/chembl.py:511 — domain entity
   - src/bioetl/infrastructure/adapters/chembl/models.py:467 — infrastructure model

2. PubchemMoleculeRecord:
   - src/bioetl/domain/entities/pubchem.py:24 — domain entity
   - src/bioetl/infrastructure/adapters/pubchem/models.py:19 — infrastructure model

Шаги:
1. Сравни поля domain-версий и infrastructure-версий для каждой пары.
2. Если поля идентичны: удали infrastructure-версию, замени import на domain-версию.
3. Если поля различаются: переименуй infrastructure-версию (напр. RawChemblPublicationRecord),
   чтобы было ясно что это raw API response, а domain-версия — нормализованный entity.
4. Обнови все import потребителей.
5. Запусти pytest tests/ -x.

Ожидаемый результат: устранена двусмысленность, ясная граница domain vs infrastructure.
```

---

### RF-PAGES: Консолидация parse_page_range

```
Консолидируй две реализации parse_page_range():

1. src/bioetl/domain/normalization.py:160 — базовая версия (не обрабатывает сокращённые диапазоны вроде "737-9")
2. src/bioetl/infrastructure/adapters/semanticscholar/_page_parsing.py:124 — расширенная версия (обрабатывает "737-9" → "737-739")

Шаги:
1. Перенеси расширенную логику из _page_parsing.py в domain/normalization.py:parse_page_range().
2. В _page_parsing.py замени реализацию на import:
   `from bioetl.domain.normalization import parse_page_range`
   или удали файл если в нём нет другой логики.
3. Напиши unit-тесты для новых edge cases ("737-9" → "737-739") в tests/unit/domain/.
4. Запусти pytest tests/ -x.

Ожидаемый результат: −40 LOC, единая реализация в domain с полным набором возможностей.
```

---

### RF-HASH: Консолидация _normalize_for_hash

```
Консолидируй 3 реализации _normalize_for_hash():

1. src/bioetl/domain/transformations.py:81
2. src/bioetl/domain/services/identity_service.py:119
3. src/bioetl/composition/services/versioning.py:65

Шаги:
1. Определи каноническую версию (domain/transformations.py — наиболее общая).
2. В identity_service.py и versioning.py замени локальную реализацию на import:
   `from bioetl.domain.transformations import _normalize_for_hash`
   Или, если функция приватная и не экспортируется: сделай её публичной (normalize_for_hash)
   и добавь в domain/transformations/__all__.
3. Убедись что все 3 реализации семантически идентичны. Если нет — определи superset-логику.
4. Запусти pytest tests/ -x.

Ожидаемый результат: −50 LOC, единая hash-нормализация.
```

---

### RF-ORPHAN: Удаление оставшихся orphan-модулей

```
Удали 2 оставшихся orphan-модуля, не охваченных Quick Wins:

1. src/bioetl/infrastructure/adapters/chembl/exceptions.py (116 LOC)
   — ChemblApiError иерархия, не импортируется ни одним модулем.
   → Если QW-10 уже выполнен — пропусти.

2. src/bioetl/application/core/subcellular_fraction_data_source.py (~50 LOC)
   — Data source класс, не подключённый в composition/ и не импортируемый нигде.

Шаги:
1. Для каждого файла: grep -rn "module_name\|ClassName" src/bioetl/ — 0 import-ов.
2. Удали файл.
3. Удали ре-экспорты из __init__.py если есть.
4. Запусти pytest tests/ -x.

Ожидаемый результат: −166 LOC.
```
