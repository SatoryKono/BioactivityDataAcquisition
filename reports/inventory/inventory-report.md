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
