# Code Review Report — S5: Cross_cutting
**Date**: 2026-03-15
**Scope**: src/bioetl
**Files reviewed**: 1079
**Total LOC**: 160217
**Status**: FAIL
**Score**: 5.5/10.0

---

## Summary
| Category | Issues | CRIT | HIGH | MED | LOW | Score |
|----------|--------|------|------|-----|-----|-------|
| Architecture | 195 | 0 | 32 | 163 | 0 | 0.0 |
| Anti-Patterns | 0 | 0 | 0 | 0 | 0 | 10.0 |
| DI Violations | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Naming | 20 | 0 | 0 | 20 | 0 | 0.0 |
| Types | 19 | 0 | 0 | 0 | 19 | 5.2 |
| Testing | 0 | 0 | 0 | 0 | 0 | 10.0 |
| **TOTAL** | **234** | **0** | **32** | **183** | **19** | **5.5** |

## High Issues

### ARCH-009: Determinism
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/adapters/common/api_request_collector.py:67`
- **Description**: datetime.now() used in infrastructure layer
### ARCH-009: Determinism
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/storage/metadata_builder.py:76`
- **Description**: datetime.now() used in infrastructure layer
### ARCH-009: Determinism
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/storage/metadata_builder.py:235`
- **Description**: datetime.now() used in infrastructure layer
### ARCH-009: Determinism
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/storage/metadata_builder.py:303`
- **Description**: datetime.now() used in infrastructure layer
### ARCH-009: Determinism
- **Severity**: HIGH
- **File**: `src/bioetl/infrastructure/storage/silver_writer.py:197`
- **Description**: datetime.now() used in infrastructure layer
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/health_check.py:31`
- **Description**: Class 'HealthCheckResult' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/audit.py:28`
- **Description**: Class 'AuditOperation' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/audit.py:47`
- **Description**: Class 'AuditLayer' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/audit.py:61`
- **Description**: Class 'AuditEntry' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/adr.py:18`
- **Description**: Class 'AdrInfo' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/adr.py:27`
- **Description**: Class 'AdrDocument' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/adr.py:39`
- **Description**: Class 'AdrValidationIssue' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/adr.py:49`
- **Description**: Class 'AdrValidationReport' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/metadata/coordinator.py:38`
- **Description**: Class 'BronzeMetadataInput' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/metadata/coordinator.py:67`
- **Description**: Class 'SilverMetadataInput' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/metadata/coordinator.py:118`
- **Description**: Class 'SilverRef' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/metadata/coordinator.py:136`
- **Description**: Class 'GoldMetadataInput' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/runtime/pipeline_debug.py:22`
- **Description**: Class 'StageBreakpoint' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/runtime/pipeline_debug.py:34`
- **Description**: Class 'DebugAction' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/runtime/pipeline_debug.py:45`
- **Description**: Class 'PipelineSnapshot' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/runtime/pipeline_debug.py:76`
- **Description**: Class 'BreakpointHit' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/runtime/memory.py:14`
- **Description**: Class 'MemoryStats' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/noop/_tracing.py:11`
- **Description**: Class '_NoOpSpan' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/noop/_tracing.py:63`
- **Description**: Class '_NoOpOtelTracer' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/noop/_tracing.py:83`
- **Description**: Class 'NoOpTracing' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/noop/_memory_metadata.py:18`
- **Description**: Class 'NoOpMemoryMonitor' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/noop/_memory_metadata.py:77`
- **Description**: Class 'NoOpMetadataWriter' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/noop/_audit_pii.py:13`
- **Description**: Class 'NoOpAudit' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/noop/_audit_pii.py:53`
- **Description**: Class 'NoOpPiiHasher' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/noop/_metrics.py:11`
- **Description**: Class 'NoOpMetrics' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/noop/_debug.py:15`
- **Description**: Class 'NoOpDebug' in domain/ports must end with Port
### ARCH-003: Port Naming
- **Severity**: HIGH
- **File**: `src/bioetl/domain/ports/quality/quarantine.py:27`
- **Description**: Class 'QuarantineWriteRequest' in domain/ports must end with Port
## Medium Issues

### ARCH-008: Future Annotations
- **Severity**: MEDIUM
- **File**: `src/bioetl/interfaces/__init__.py:1`
- **Description**: Missing from __future__ import annotations
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/adapter_error_mapper.py:30`
- **Description**: Adapter 'AdapterErrorMapper' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/validation.py:37`
- **Description**: Adapter 'RecordValidationResult' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/base.py:51`
- **Description**: Adapter 'BaseHttpAdapter' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/health_check_mixin.py:52`
- **Description**: Adapter '_HealthCheckProbeOutcome' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/base_metrics.py:42`
- **Description**: Adapter 'AdapterMetricsRecorder' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/error_handling.py:40`
- **Description**: Adapter 'AdapterErrorContext' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/error_handling.py:54`
- **Description**: Adapter 'ErrorService' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/filterable_mixin.py:33`
- **Description**: Adapter 'FetchFilteredPort' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/adapter_error_classifier.py:17`
- **Description**: Adapter 'ErrorCategory' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/adapter_error_classifier.py:39`
- **Description**: Adapter 'AdapterErrorClassifier' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/health_check_contract.py:29`
- **Description**: Adapter 'HealthCheckContext' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/sync_base.py:50`
- **Description**: Adapter 'BaseSyncAdapter' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/semanticscholar/health_metadata_mixin.py:39`
- **Description**: Adapter 'SemanticScholarHTTPResponseProtocol' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/semanticscholar/health_metadata_mixin.py:46`
- **Description**: Adapter 'SemanticScholarHTTPClientProtocol' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/semanticscholar/health_metadata_mixin.py:67`
- **Description**: Adapter 'SemanticScholarAdapterMetricsProtocol' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/semanticscholar/health_metadata_mixin.py:76`
- **Description**: Adapter 'SemanticScholarRequestCollectorProtocol' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/semanticscholar/health_metadata_mixin.py:83`
- **Description**: Adapter 'SemanticScholarHealthMetadataDependencies' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/semanticscholar/fallback.py:58`
- **Description**: Adapter 'SemanticScholarTitleFallbackHandler' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/semanticscholar/adapter.py:118`
- **Description**: Adapter 'SemanticScholarAdapter' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/common/source_metadata_capability.py:18`
- **Description**: Adapter 'SourceMetadataCollectorProtocol' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/common/fallback_fetch_service.py:24`
- **Description**: Adapter 'PrimaryRecordFetchPort' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/common/fallback_fetch_service.py:32`
- **Description**: Adapter 'NormalizeIdPort' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/common/fallback_fetch_service.py:38`
- **Description**: Adapter 'ExtractRecordIdPort' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/common/fallback_fetch_service.py:44`
- **Description**: Adapter 'Phase1SummaryLoggerPort' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/common/fallback_fetch_service.py:50`
- **Description**: Adapter 'FallbackExecutionPort' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/common/fallback_fetch_service.py:68`
- **Description**: Adapter 'DefaultFallbackExecution' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/common/fallback_fetch_service.py:90`
- **Description**: Adapter 'FallbackFetchRequest' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/common/fallback_fetch_service.py:148`
- **Description**: Adapter 'FallbackFetchOrchestratorService' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/common/api_request_collector.py:21`
- **Description**: Adapter 'APIRequestCollector' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/common/base_title_fallback.py:25`
- **Description**: Adapter 'BaseTitleFallbackHandler' missing health_check()
### NAME-002: Private attributes
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/common/base_title_fallback.py:307`
- **Description**: Double underscore used for private attribute
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/common/composable_fallback.py:38`
- **Description**: Adapter 'FallbackDecoratorConfig' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/common/composable_fallback.py:52`
- **Description**: Adapter 'ComposableFallbackDecorator' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/common/fetch_retry_policy.py:32`
- **Description**: Adapter '_FetchState' missing health_check()
### NAME-002: Private attributes
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/common/fetch_retry_policy.py:27`
- **Description**: Double underscore used for private attribute
### NAME-002: Private attributes
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/common/fetch_retry_policy.py:50`
- **Description**: Double underscore used for private attribute
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/models.py:47`
- **Description**: Adapter 'CrossRefPublicationRecord' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/models.py:238`
- **Description**: Adapter 'CrossRefMessage' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/models.py:270`
- **Description**: Adapter 'CrossRefPublicationsResponse' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/models.py:283`
- **Description**: Adapter 'CrossRefPublicationResponse' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/models_shared.py:10`
- **Description**: Adapter 'CrossRefAuthor' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/models_shared.py:35`
- **Description**: Adapter 'CrossRefFunder' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/models_shared.py:48`
- **Description**: Adapter 'CrossRefLicense' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/models_shared.py:63`
- **Description**: Adapter 'CrossRefLink' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/models_shared.py:80`
- **Description**: Adapter 'CrossRefReference' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/models_shared.py:108`
- **Description**: Adapter 'CrossRefAssertion' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/models_shared.py:119`
- **Description**: Adapter 'CrossRefClinicalTrial' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/models_shared.py:131`
- **Description**: Adapter 'CrossRefDateParts' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/fetch_flow.py:31`
- **Description**: Adapter 'CrossRefFetchFlow' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/response_mapper.py:23`
- **Description**: Adapter 'CrossRefHealthProbeMapping' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/response_mapper.py:30`
- **Description**: Adapter 'CrossRefResponseMapper' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/fallback.py:40`
- **Description**: Adapter 'CrossRefTitleFallbackHandler' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/client.py:95`
- **Description**: Adapter 'CrossRefAdapter' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/batch.py:40`
- **Description**: Adapter 'HttpTransport' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/batch.py:52`
- **Description**: Adapter 'BaseMetrics' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/batch.py:73`
- **Description**: Adapter 'DoiBatchProcessor' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/batch.py:283`
- **Description**: Adapter 'SearchPaginator' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/client_runtime_helpers.py:48`
- **Description**: Adapter 'CrossRefRuntimeServices' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/crossref/query_builder.py:46`
- **Description**: Adapter 'CrossRefQueryBuilder' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/input/csv_filter_reader.py:25`
- **Description**: Adapter 'CsvFilterReader' missing health_check()
### NAME-002: Private attributes
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/input/csv_filter_reader.py:179`
- **Description**: Double underscore used for private attribute
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/openalex/cursor_flow.py:29`
- **Description**: Adapter 'OpenAlexCursorFlowService' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/openalex/query_execution.py:23`
- **Description**: Adapter 'OpenAlexQueryExecutor' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/openalex/filter_fetch_adapter_mixin.py:27`
- **Description**: Adapter '_FilteredFetchRequest' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/openalex/filter_fetch_adapter_mixin.py:37`
- **Description**: Adapter '_FallbackFetchRequest' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/openalex/filter_fetch_adapter_mixin.py:48`
- **Description**: Adapter '_FetchRequest' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/openalex/fallback.py:25`
- **Description**: Adapter 'OpenAlexTitleFallbackHandler' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/openalex/client.py:90`
- **Description**: Adapter 'OpenAlexAdapter' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/openalex/fallback_orchestrator.py:77`
- **Description**: Adapter 'OpenAlexFallbackOrchestrator' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/openalex/client_runtime_helpers.py:49`
- **Description**: Adapter 'OpenAlexRuntimeServices' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/openalex/health_adapter_mixin.py:17`
- **Description**: Adapter '_OpenAlexHealthHost' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/openalex/response_mapping.py:14`
- **Description**: Adapter 'OpenAlexResponseMapper' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubmed/models.py:39`
- **Description**: Adapter 'PubMedArticleRecord' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubmed/models.py:62`
- **Description**: Adapter 'PubMedAuthor' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubmed/models.py:76`
- **Description**: Adapter 'PubMedJournal' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubmed/models.py:95`
- **Description**: Adapter 'PubMedPubDate' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubmed/models.py:105`
- **Description**: Adapter 'PubMedMeshHeading' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubmed/models.py:120`
- **Description**: Adapter 'PubMedChemical' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubmed/models.py:130`
- **Description**: Adapter 'PubMedGrant' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubmed/models.py:141`
- **Description**: Adapter 'PubMedReference' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubmed/models.py:150`
- **Description**: Adapter 'PubMedArticleId' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubmed/models.py:159`
- **Description**: Adapter 'PubMedExtendedRecord' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubmed/models.py:261`
- **Description**: Adapter 'PubMedSearchResult' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubmed/models.py:286`
- **Description**: Adapter 'PubMedSearchResponse' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubmed/xml_processor.py:17`
- **Description**: Adapter 'PubMedXmlProcessor' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubmed/fallback.py:38`
- **Description**: Adapter 'PubMedTitleFallbackHandler' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py:88`
- **Description**: Adapter 'PubMedAdapter' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubmed/adapter_filter_fetch_mixin.py:25`
- **Description**: Adapter '_PubMedAdapterFilterFetchHost' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/idmapping_client.py:43`
- **Description**: Adapter 'UniProtIDMappingClient' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_idmapping_transport.py:18`
- **Description**: Adapter 'IDMappingTransportDependencies' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_idmapping_retry.py:20`
- **Description**: Adapter 'IDMappingRetryDependencies' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/fasta_parser.py:15`
- **Description**: Adapter 'FastaParser' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_records.py:31`
- **Description**: Adapter 'UniProtProteinRecord' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_records.py:87`
- **Description**: Adapter 'UniProtSearchResponse' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_records.py:97`
- **Description**: Adapter 'UniProtFeatureRecord' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_records.py:110`
- **Description**: Adapter 'UniProtSequenceRecord' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_annotations.py:26`
- **Description**: Adapter 'UniProtEcNumber' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_annotations.py:34`
- **Description**: Adapter 'UniProtKeyword' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_annotations.py:44`
- **Description**: Adapter 'UniProtOrganism' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_annotations.py:59`
- **Description**: Adapter 'UniProtName' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_annotations.py:67`
- **Description**: Adapter 'UniProtFullName' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_annotations.py:80`
- **Description**: Adapter 'UniProtRecommendedName' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_annotations.py:96`
- **Description**: Adapter 'UniProtProteinDescription' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_annotations.py:116`
- **Description**: Adapter 'UniProtGene' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_annotations.py:135`
- **Description**: Adapter 'UniProtEvidence' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_annotations.py:145`
- **Description**: Adapter 'UniProtText' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_annotations.py:156`
- **Description**: Adapter 'UniProtLocation' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_annotations.py:167`
- **Description**: Adapter 'UniProtSubcellularLocation' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_annotations.py:177`
- **Description**: Adapter 'UniProtReaction' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_annotations.py:191`
- **Description**: Adapter 'UniProtIsoform' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_annotations.py:205`
- **Description**: Adapter 'UniProtComment' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/client.py:82`
- **Description**: Adapter 'UniProtAdapter' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_structures.py:21`
- **Description**: Adapter 'UniProtFeatureLocation' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_structures.py:34`
- **Description**: Adapter 'UniProtFeature' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_structures.py:52`
- **Description**: Adapter 'UniProtCrossReference' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_structures.py:64`
- **Description**: Adapter 'UniProtSequence' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_structures.py:76`
- **Description**: Adapter 'UniProtExtraAttributes' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/fallback_policy.py:12`
- **Description**: Adapter 'UniProtFallbackPolicy' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/uniprot/_idmapping_health.py:16`
- **Description**: Adapter 'IDMappingHealthDependencies' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_activity.py:18`
- **Description**: Adapter 'LigandEfficiency' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_activity.py:29`
- **Description**: Adapter 'ActionType' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_activity.py:39`
- **Description**: Adapter 'ChemblActivityRecord' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_activity.py:148`
- **Description**: Adapter 'ChemblActivityResponse' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_common.py:25`
- **Description**: Adapter 'ChemblPageMeta' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_common.py:37`
- **Description**: Adapter 'ChemblAssayRecord' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_common.py:85`
- **Description**: Adapter 'ChemblAssayResponse' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_common.py:98`
- **Description**: Adapter 'ChemblTargetRecord' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_common.py:121`
- **Description**: Adapter 'ChemblTargetResponse' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_common.py:134`
- **Description**: Adapter 'ChemblReleaseInfo' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_common.py:147`
- **Description**: Adapter 'ChemblPublicationApiRecord' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_common.py:174`
- **Description**: Adapter 'ChemblPublicationResponse' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_common.py:187`
- **Description**: Adapter 'ChemblTargetComponentRecord' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_common.py:228`
- **Description**: Adapter 'ChemblTargetComponentResponse' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_common.py:241`
- **Description**: Adapter 'ChemblCellLineRecord' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_common.py:258`
- **Description**: Adapter 'ChemblCellLineResponse' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/entity_mapper.py:91`
- **Description**: Adapter 'ChemblEntityMapper' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/client.py:57`
- **Description**: Adapter 'ChemblAdapter' missing health_check()
### NAME-002: Private attributes
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/client.py:159`
- **Description**: Double underscore used for private attribute
### NAME-002: Private attributes
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/client.py:161`
- **Description**: Double underscore used for private attribute
### NAME-002: Private attributes
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/client.py:186`
- **Description**: Double underscore used for private attribute
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_compound.py:19`
- **Description**: Adapter 'MoleculeHierarchy' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_compound.py:29`
- **Description**: Adapter 'MoleculeProperties' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_compound.py:59`
- **Description**: Adapter 'MoleculeStructures' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_compound.py:70`
- **Description**: Adapter 'ChemblMoleculeRecord' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/chembl/models_compound.py:121`
- **Description**: Adapter 'ChemblMoleculeResponse' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubchem/models.py:28`
- **Description**: Adapter 'PubchemMoleculeApiRecord' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubchem/models.py:88`
- **Description**: Adapter 'PubChemSubstanceRecord' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubchem/models.py:119`
- **Description**: Adapter 'PubChemAssayRecord' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubchem/models.py:144`
- **Description**: Adapter 'PubchemMoleculeDetailRecord' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubchem/models.py:213`
- **Description**: Adapter 'PubChemBioactivityRecord' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubchem/fetch_flow.py:18`
- **Description**: Adapter '_RequestRecorder' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubchem/fetch_flow.py:29`
- **Description**: Adapter 'PubChemFetchFlowService' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubchem/response_mapper.py:23`
- **Description**: Adapter 'PubChemResponseMapper' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubchem/entity_mapper.py:103`
- **Description**: Adapter 'PubChemEntityMapper' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubchem/fetch_strategies.py:121`
- **Description**: Adapter 'PubChemFetchStrategies' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/pubchem/client.py:71`
- **Description**: Adapter 'PubChemAdapter' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/http/rate_limiter.py:22`
- **Description**: Adapter 'TokenBucketRateLimiter' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/http/health_tracker.py:19`
- **Description**: Adapter 'ProviderHealthTracker' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/http/circuit_breaker.py:60`
- **Description**: Adapter 'CircuitBreakerGuard' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/http/client.py:35`
- **Description**: Adapter 'UnifiedHTTPClient' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/http/client_retry_mixin.py:26`
- **Description**: Adapter '_RequestAttemptOutcome' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/http/client_retry_mixin.py:36`
- **Description**: Adapter '_RetryRequestState' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/http/health_monitor.py:39`
- **Description**: Adapter 'HealthAdjustedConfig' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/http/health_monitor.py:90`
- **Description**: Adapter 'ProviderHealthState' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/adapters/http/health_monitor.py:111`
- **Description**: Adapter 'ProviderHealthMonitor' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/observability/debug_adapters.py:26`
- **Description**: Adapter 'InteractiveDebugAdapter' missing health_check()
### ARCH-004: Adapter Health Check
- **Severity**: MEDIUM
- **File**: `src/bioetl/infrastructure/observability/debug_adapters.py:101`
- **Description**: Adapter 'LoggingDebugAdapter' missing health_check()
### ARCH-008: Future Annotations
- **Severity**: MEDIUM
- **File**: `src/bioetl/composition/__init__.py:1`
- **Description**: Missing from __future__ import annotations
### NAME-002: Private attributes
- **Severity**: MEDIUM
- **File**: `src/bioetl/application/composite/join_execution.py:100`
- **Description**: Double underscore used for private attribute
### NAME-002: Private attributes
- **Severity**: MEDIUM
- **File**: `src/bioetl/application/composite/join_execution.py:152`
- **Description**: Double underscore used for private attribute
### NAME-002: Private attributes
- **Severity**: MEDIUM
- **File**: `src/bioetl/application/composite/deduplication.py:121`
- **Description**: Double underscore used for private attribute
### NAME-002: Private attributes
- **Severity**: MEDIUM
- **File**: `src/bioetl/application/composite/deduplication.py:123`
- **Description**: Double underscore used for private attribute
### NAME-002: Private attributes
- **Severity**: MEDIUM
- **File**: `src/bioetl/application/composite/deduplication.py:124`
- **Description**: Double underscore used for private attribute
### NAME-002: Private attributes
- **Severity**: MEDIUM
- **File**: `src/bioetl/application/composite/deduplication.py:132`
- **Description**: Double underscore used for private attribute
### NAME-002: Private attributes
- **Severity**: MEDIUM
- **File**: `src/bioetl/application/composite/deduplication.py:133`
- **Description**: Double underscore used for private attribute
### NAME-002: Private attributes
- **Severity**: MEDIUM
- **File**: `src/bioetl/application/composite/deduplication.py:134`
- **Description**: Double underscore used for private attribute
### NAME-002: Private attributes
- **Severity**: MEDIUM
- **File**: `src/bioetl/application/services/dq/_checks_integrity.py:90`
- **Description**: Double underscore used for private attribute
### NAME-002: Private attributes
- **Severity**: MEDIUM
- **File**: `src/bioetl/application/services/dq/_checks_integrity.py:91`
- **Description**: Double underscore used for private attribute
### NAME-002: Private attributes
- **Severity**: MEDIUM
- **File**: `src/bioetl/domain/ports/filtering.py:108`
- **Description**: Double underscore used for private attribute
### NAME-002: Private attributes
- **Severity**: MEDIUM
- **File**: `src/bioetl/domain/ports/filtering.py:135`
- **Description**: Double underscore used for private attribute
### NAME-002: Private attributes
- **Severity**: MEDIUM
- **File**: `src/bioetl/domain/models/filter.py:24`
- **Description**: Double underscore used for private attribute
### ARCH-008: Future Annotations
- **Severity**: MEDIUM
- **File**: `src/bioetl/domain/entities/bioactivity/__init__.py:1`
- **Description**: Missing from __future__ import annotations
## Low Issues

### TYPE-002: Any Usage
- **Severity**: LOW
- **File**: `src/bioetl/infrastructure/config/_yaml_settings_source.py:35`
- **Description**: Any used without justification
### TYPE-002: Any Usage
- **Severity**: LOW
- **File**: `src/bioetl/infrastructure/observability/unified_logger.py:178`
- **Description**: Any used without justification
### TYPE-002: Any Usage
- **Severity**: LOW
- **File**: `src/bioetl/infrastructure/observability/unified_logger.py:235`
- **Description**: Any used without justification
### TYPE-002: Any Usage
- **Severity**: LOW
- **File**: `src/bioetl/infrastructure/observability/logging.py:124`
- **Description**: Any used without justification
### TYPE-002: Any Usage
- **Severity**: LOW
- **File**: `src/bioetl/infrastructure/observability/logging.py:164`
- **Description**: Any used without justification
### TYPE-002: Any Usage
- **Severity**: LOW
- **File**: `src/bioetl/infrastructure/storage/arrow_converter.py:33`
- **Description**: Any used without justification
### TYPE-002: Any Usage
- **Severity**: LOW
- **File**: `src/bioetl/infrastructure/storage/base_delta_writer.py:50`
- **Description**: Any used without justification
### TYPE-002: Any Usage
- **Severity**: LOW
- **File**: `src/bioetl/application/composite/merger_compat_join_planner_mixin.py:22`
- **Description**: Any used without justification
### TYPE-002: Any Usage
- **Severity**: LOW
- **File**: `src/bioetl/application/composite/merger_compat_join_planner_mixin.py:34`
- **Description**: Any used without justification
### TYPE-002: Any Usage
- **Severity**: LOW
- **File**: `src/bioetl/application/core/_data_source_mixins.py:26`
- **Description**: Any used without justification
### TYPE-002: Any Usage
- **Severity**: LOW
- **File**: `src/bioetl/application/core/batch_processing_service_mixins.py:214`
- **Description**: Any used without justification
### TYPE-002: Any Usage
- **Severity**: LOW
- **File**: `src/bioetl/application/core/base_transformer/base.py:201`
- **Description**: Any used without justification
### TYPE-002: Any Usage
- **Severity**: LOW
- **File**: `src/bioetl/domain/ports/data_source.py:219`
- **Description**: Any used without justification
### TYPE-002: Any Usage
- **Severity**: LOW
- **File**: `src/bioetl/domain/ports/observability/tracing.py:12`
- **Description**: Any used without justification
### TYPE-002: Any Usage
- **Severity**: LOW
- **File**: `src/bioetl/domain/ports/observability/logging.py:35`
- **Description**: Any used without justification
### TYPE-002: Any Usage
- **Severity**: LOW
- **File**: `src/bioetl/domain/ports/observability/logging.py:75`
- **Description**: Any used without justification
### TYPE-002: Any Usage
- **Severity**: LOW
- **File**: `src/bioetl/domain/transformations/hashing.py:27`
- **Description**: Any used without justification
### TYPE-002: Any Usage
- **Severity**: LOW
- **File**: `src/bioetl/domain/entities/bioactivity/_converters.py:36`
- **Description**: Any used without justification
### TYPE-002: Any Usage
- **Severity**: LOW
- **File**: `src/bioetl/domain/services/dq_serializer.py:71`
- **Description**: Any used without justification
