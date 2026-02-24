# BioETL Component–Object Inventory

**Date**: 2026-02-23
**Companion to**: COMPREHENSIVE_AUDIT_2026-02-23.md

This document provides the exhaustive component → object mapping requested in the audit.
Every object is listed with its source file path and the port/protocol it implements (where applicable).

---

## Component 1: REST API Client Layer (HTTP I/O)

All outbound HTTP communication with external bioactivity data providers.

| Object | Source File | Implements Port | Description |
|--------|------------|-----------------|-------------|
| `BaseHttpAdapter` | `infrastructure/adapters/base.py` | — | Shared HTTP client base (httpx AsyncClient) |
| `BaseAdapterMetrics` | `infrastructure/adapters/base_metrics.py` | — | Shared metrics collection for adapters |
| `SyncBaseAdapter` | `infrastructure/adapters/sync_base.py` | — | Synchronous adapter base |
| `ChEMBLClient` | `infrastructure/adapters/chembl/client.py` | `DataSourcePort`, `FilterableDataSourcePort` | ChEMBL REST API v2 adapter |
| `ChEMBLEntityMapper` | `infrastructure/adapters/chembl/entity_mapper.py` | — | Maps entity names to API resources |
| `ChEMBLHealth` | `infrastructure/adapters/chembl/health.py` | `HealthCheckPort` | ChEMBL health check |
| `ChEMBLDeduplication` | `infrastructure/adapters/chembl/deduplication.py` | — | API-level dedup for ChEMBL |
| `ChEMBLMetadata` | `infrastructure/adapters/chembl/metadata.py` | — | ChEMBL metadata extraction |
| `ChEMBLModels` | `infrastructure/adapters/chembl/models.py` | — | Pydantic models for ChEMBL config |
| `ChEMBLConstants` | `infrastructure/adapters/chembl/constants.py` | — | ChEMBL-specific constants |
| `PubChemClient` | `infrastructure/adapters/pubchem/client.py` | `DataSourcePort`, `FilterableDataSourcePort` | PubChem PUG REST adapter |
| `PubChemEntityMapper` | `infrastructure/adapters/pubchem/entity_mapper.py` | — | Maps entity names to PUG REST paths |
| `PubChemFetchStrategies` | `infrastructure/adapters/pubchem/fetch_strategies.py` | — | SMILES/CID fetch strategies |
| `PubChemModels` | `infrastructure/adapters/pubchem/models.py` | — | Pydantic models for PubChem config |
| `PubChemConstants` | `infrastructure/adapters/pubchem/constants.py` | — | PubChem constants |
| `UniProtClient` | `infrastructure/adapters/uniprot/client.py` | `DataSourcePort`, `FilterableDataSourcePort` | UniProt REST API adapter |
| `UniProtIDMappingClient` | `infrastructure/adapters/uniprot/idmapping_client.py` | `IDMappingPort` | UniProt ID mapping service |
| `FastaParser` | `infrastructure/adapters/uniprot/fasta_parser.py` | — | FASTA format parser |
| `UniProtModels` | `infrastructure/adapters/uniprot/models.py` | — | Pydantic models for UniProt config |
| `PubMedClient` | `infrastructure/adapters/pubmed/pubmed_client.py` | `DataSourcePort`, `FilterableDataSourcePort` | PubMed Entrez E-utilities adapter |
| `PubMedSearch` | `infrastructure/adapters/pubmed/_search.py` | — | PubMed search module |
| `PubMedFetch` | `infrastructure/adapters/pubmed/_fetch.py` | — | PubMed fetch module |
| `PubMedHealth` | `infrastructure/adapters/pubmed/_health.py` | — | PubMed health check |
| `PubMedXmlProcessor` | `infrastructure/adapters/pubmed/xml_processor.py` | — | XML response processing |
| `PubMedFallback` | `infrastructure/adapters/pubmed/fallback.py` | — | Title-based fallback search |
| `PubMedModels` | `infrastructure/adapters/pubmed/models.py` | — | Pydantic models |
| `PubMedConstants` | `infrastructure/adapters/pubmed/constants.py` | — | PubMed constants |
| `CrossRefClient` | `infrastructure/adapters/crossref/client.py` | `DataSourcePort`, `FilterableDataSourcePort` | CrossRef API adapter |
| `CrossRefBatch` | `infrastructure/adapters/crossref/batch.py` | — | Batch DOI resolution |
| `CrossRefFallback` | `infrastructure/adapters/crossref/fallback.py` | — | Title-based fallback |
| `CrossRefExceptions` | `infrastructure/adapters/crossref/exceptions.py` | — | CrossRef-specific exceptions |
| `CrossRefModels` | `infrastructure/adapters/crossref/models.py` | — | Pydantic models |
| `OpenAlexClient` | `infrastructure/adapters/openalex/client.py` | `DataSourcePort`, `FilterableDataSourcePort` | OpenAlex API adapter |
| `OpenAlexFallback` | `infrastructure/adapters/openalex/fallback.py` | — | Title-based fallback |
| `SemanticScholarAdapter` | `infrastructure/adapters/semanticscholar/adapter.py` | `DataSourcePort`, `FilterableDataSourcePort` | Semantic Scholar API adapter |
| `SemanticScholarFallback` | `infrastructure/adapters/semanticscholar/fallback.py` | — | Title-based fallback |
| `SemanticScholarConstants` | `infrastructure/adapters/semanticscholar/constants.py` | — | S2 constants |
| `CachedBronzeDataSource` | `infrastructure/adapters/cached_bronze_data_source.py` | `DataSourcePort` | Reads from cached Bronze layer instead of API |
| `FilterableMixin` | `infrastructure/adapters/filterable_mixin.py` | — | Shared filterable behavior mixin |
| `HealthCheckMixin` | `infrastructure/adapters/health_check_mixin.py` | — | Shared health check mixin |
| `ErrorHandling` | `infrastructure/adapters/error_handling.py` | — | Shared error handling utilities |
| `ValidationAdapter` | `infrastructure/adapters/validation.py` | — | Input validation for adapters |
| `ApiRequestCollector` | `infrastructure/adapters/common/api_request_collector.py` | — | API request metrics collection |
| `BaseTitleFallback` | `infrastructure/adapters/common/base_title_fallback.py` | — | Base class for title fallback |
| `TitleMatching` | `infrastructure/adapters/common/title_matching.py` | — | Fuzzy title matching service |
| `CsvFilterReader` | `infrastructure/adapters/input/csv_filter_reader.py` | `InputFilterPort` | CSV-based input filter loading |

---

## Component 2: Data Storage (Medallion Architecture)

All persistence operations across Bronze → Silver → Gold medallion layers.

| Object | Source File | Implements Port | Description |
|--------|------------|-----------------|-------------|
| `BronzeWriter` | `infrastructure/storage/bronze_writer.py` | `StoragePort` (partial) | Raw data to Parquet files |
| `SilverWriter` | `infrastructure/storage/silver_writer.py` | `StoragePort` (partial) | Deduplicated data to Delta Lake tables |
| `GoldWriter` | `infrastructure/storage/gold_writer.py` | `StoragePort` (partial) | Validated data to Delta Lake tables |
| `DeltaWriter` | `infrastructure/storage/delta_writer.py` | — | Core Delta Lake write abstraction |
| `BaseDeltaWriter` | `infrastructure/storage/base_delta_writer.py` | — | Base class for Delta writers |
| `DeltaReader` | `infrastructure/storage/delta_reader.py` | `DeltaReaderPort` | Delta Lake read operations |
| `ArrowConverter` | `infrastructure/storage/arrow_converter.py` | — | Pandas DataFrame to Arrow conversion |
| `MetadataWriter` | `infrastructure/storage/metadata_writer.py` | `MetadataWriterPort` | Table metadata JSON persistence |
| `MetadataBuilder` | `infrastructure/storage/metadata_builder.py` | — | Metadata record construction |
| `RetentionManager` | `infrastructure/storage/retention_manager.py` | — | Data retention and cleanup |
| `AtomicWriter` | `infrastructure/storage/_atomic.py` | — | Atomic file write operations |

---

## Component 3: Data Transformation (ETL)

Converting raw API data (dict) into structured, normalized records (dict).

| Object | Source File | Implements Port | Description |
|--------|------------|-----------------|-------------|
| `BaseTransformer` | `application/core/base_transformer.py` | — | Abstract transformer base class |
| `BatchTransformer` | `application/core/batch_transformer.py` | — | Batch-level transformation orchestrator |
| `DictTransformers` | `application/core/dict_transformers.py` | — | Dictionary-level transformation utilities |
| `EntityIdExtractor` | `application/core/entity_id.py` | — | Entity ID extraction logic |
| `FieldSpecs` | `application/core/field_specs.py` | — | Field specification definitions |
| `PublicationAliases` | `application/core/publication_aliases.py` | — | Publication field alias management |
| `BaseChemblTransformer` | `application/pipelines/chembl/base_chembl_transformer.py` | — | ChEMBL-specific base transformer |
| `ActivityTransformer` | `application/pipelines/chembl/activity_transformer.py` | — | ChEMBL activity transformation |
| `AssayTransformer` | `application/pipelines/chembl/assay_transformer.py` | — | ChEMBL assay transformation |
| `AssayParametersTransformer` | `application/pipelines/chembl/assay_parameters_transformer.py` | — | ChEMBL assay parameters |
| `CellLineTransformer` | `application/pipelines/chembl/cell_line_transformer.py` | — | ChEMBL cell line |
| `CompoundRecordTransformer` | `application/pipelines/chembl/compound_record_transformer.py` | — | ChEMBL compound record |
| `MoleculeTransformer` | `application/pipelines/chembl/molecule_transformer.py` | — | ChEMBL molecule |
| `ProteinClassTransformer` | `application/pipelines/chembl/protein_class_transformer.py` | — | ChEMBL protein class |
| `PublicationTransformer` | `application/pipelines/chembl/publication_transformer.py` | — | ChEMBL publication |
| `PublicationSimilarityTransformer` | `application/pipelines/chembl/publication_similarity_transformer.py` | — | ChEMBL publication similarity |
| `PublicationTermTransformer` | `application/pipelines/chembl/publication_term_transformer.py` | — | ChEMBL publication term |
| `SubcellularFractionTransformer` | `application/pipelines/chembl/subcellular_fraction_transformer.py` | — | ChEMBL subcellular fraction |
| `TargetTransformer` | `application/pipelines/chembl/target_transformer.py` | — | ChEMBL target |
| `TargetComponentTransformer` | `application/pipelines/chembl/target_component_transformer.py` | — | ChEMBL target component |
| `TissueTransformer` | `application/pipelines/chembl/tissue_transformer.py` | — | ChEMBL tissue |
| `PubChemCompoundTransformer` | `application/pipelines/pubchem/transformer.py` | — | PubChem compound |
| `BasePublicationTransformer` | `application/pipelines/common/base_publication_transformer.py` | — | Shared publication transformer base |
| `CommonExtractors` | `application/pipelines/common/extractors.py` | — | Shared publication field extractors |
| `CrossRefTransformer` | `application/pipelines/crossref/transformer.py` | — | CrossRef publication |
| `CrossRefAuthorExtractors` | `application/pipelines/crossref/author_extractors.py` | — | CrossRef author extraction |
| `CrossRefExtractors` | `application/pipelines/crossref/extractors.py` | — | CrossRef field extraction |
| `CrossRefReferenceExtractors` | `application/pipelines/crossref/reference_extractors.py` | — | CrossRef reference extraction |
| `OpenAlexTransformer` | `application/pipelines/openalex/transformer.py` | — | OpenAlex publication |
| `OpenAlexExtractors` | `application/pipelines/openalex/extractors.py` | — | OpenAlex field extraction |
| `PubMedPublicationTransformer` | `application/pipelines/pubmed/transformer.py` | — | PubMed publication |
| `PubMedXmlParser` | `application/pipelines/pubmed/xml_parser.py` | — | PubMed XML parsing |
| `PubMedAbstractExtractor` | `application/pipelines/pubmed/extractors/abstract.py` | — | PubMed abstract extraction |
| `PubMedAuthorExtractor` | `application/pipelines/pubmed/extractors/author.py` | — | PubMed author extraction |
| `PubMedBaseExtractor` | `application/pipelines/pubmed/extractors/base.py` | — | PubMed base extractor |
| `PubMedClassificationExtractor` | `application/pipelines/pubmed/extractors/classification.py` | — | PubMed classification |
| `PubMedDateExtractor` | `application/pipelines/pubmed/extractors/date.py` | — | PubMed date extraction |
| `PubMedIdentifierExtractor` | `application/pipelines/pubmed/extractors/identifier.py` | — | PubMed identifier extraction |
| `PubMedIdentifierTypes` | `application/pipelines/pubmed/extractors/identifier_types.py` | — | PubMed identifier type definitions |
| `SemanticScholarTransformer` | `application/pipelines/semanticscholar/transformer.py` | — | Semantic Scholar publication |
| `SemanticScholarAuthorExtractors` | `application/pipelines/semanticscholar/_author_extractors.py` | — | S2 author extraction |
| `SemanticScholarPageParsing` | `application/pipelines/semanticscholar/_page_parsing.py` | — | S2 page number parsing |
| `SemanticScholarExtractors` | `application/pipelines/semanticscholar/extractors.py` | — | S2 field extraction |
| `UniProtProteinTransformer` | `application/pipelines/uniprot/transformer.py` | — | UniProt protein |
| `IDMappingTransformer` | `application/pipelines/uniprot/idmapping_transformer.py` | — | UniProt ID mapping |
| `UniProtCommentsExtractor` | `application/pipelines/uniprot/extractors/comments.py` | — | UniProt comments extraction |
| `UniProtCrossRefsExtractor` | `application/pipelines/uniprot/extractors/crossrefs.py` | — | UniProt cross-references |
| `UniProtFeaturesExtractor` | `application/pipelines/uniprot/extractors/features.py` | — | UniProt features |
| `UniProtGenesExtractor` | `application/pipelines/uniprot/extractors/genes.py` | — | UniProt gene names |
| `UniProtTaxonomyExtractor` | `application/pipelines/uniprot/extractors/taxonomy.py` | — | UniProt taxonomy |
| `UniProtExtractorHelpers` | `application/pipelines/uniprot/extractors/extractor_helpers.py` | — | Shared extractor utilities |
| `GenericPipeline` | `application/pipelines/generic.py` | — | Generic entity pipeline |

---

## Component 4: Data Quality (Validation & DQ)

Data validation, quality assessment, threshold enforcement, anomaly detection.

| Object | Source File | Implements Port | Description |
|--------|------------|-----------------|-------------|
| `DataQualityService` | `application/services/data_quality_service.py` | — | DQ threshold evaluation |
| `BronzeAnalyzer` | `application/services/dq/bronze_analyzer.py` | `BronzeDQAnalyzerPort` | Bronze layer DQ analysis |
| `SilverAnalyzer` | `application/services/dq/silver_analyzer.py` | `SilverDQAnalyzerPort` | Silver layer DQ analysis |
| `GoldAnalyzer` | `application/services/dq/gold_analyzer.py` | `GoldDQAnalyzerPort` | Gold layer DQ analysis |
| `BasicChecks` | `application/services/dq/_checks_basic.py` | — | Basic DQ checks (nulls, duplicates) |
| `BusinessChecks` | `application/services/dq/_checks_business.py` | — | Business rule DQ checks |
| `IntegrityChecks` | `application/services/dq/_checks_integrity.py` | — | Referential integrity checks |
| `StatisticalChecks` | `application/services/dq/_checks_statistical.py` | — | Statistical anomaly DQ checks |
| `DQReportBuilders` | `application/services/dq/dq_report_builders.py` | — | DQ report construction |
| `DQReportService` | `application/services/dq_report_service.py` | — | DQ report generation |
| `PanderaValidator` | `infrastructure/validation/pandera_validator.py` | `GoldValidatorPort`, `SilverValidatorPort` | Pandera schema validation |
| `AnomalyDetector` | `infrastructure/observability/anomaly/detector.py` | — | Statistical anomaly detection |
| `ZScoreDetector` | `infrastructure/observability/anomaly/detectors/zscore.py` | — | Z-score based detection |
| `BaseDetector` | `infrastructure/observability/anomaly/detectors/base.py` | — | Anomaly detector base class |
| `AnomalyMonitor` | `infrastructure/observability/anomaly/monitor.py` | `DQMonitorPort` | DQ anomaly monitoring |
| `AnomalyTypes` | `infrastructure/observability/anomaly/types.py` | — | Anomaly type definitions |
| `DQReportWriter` | `infrastructure/export/dq_report_writer.py` | `DQReportWriterPort` | DQ report file persistence |
| `DQMetricsCalculator` | `domain/services/dq_metrics_calculator.py` | — | Pure DQ metrics calculation |
| `DQSerializer` | `domain/services/dq_serializer.py` | — | DQ data serialization |
| `DQConfigLoader` | `infrastructure/config/dq_config_loader.py` | `GoldDQConfigPort`, `SilverDQConfigPort`, `BronzeDQConfigPort` | DQ rules YAML loading |
| 50+ Gold Schemas | `domain/schemas/*/` | — | Pandera DataFrameModel validation schemas |

---

## Component 5: Pipeline Orchestration

Pipeline lifecycle management and execution coordination.

| Object | Source File | Implements Port | Description |
|--------|------------|-----------------|-------------|
| `PipelineRunner` | `application/core/runner.py` | `RunnablePort` | Core pipeline execution orchestrator |
| `BatchExecutor` | `application/core/batch_executor.py` | — | Batch-level processing loop |
| `BatchWriter` | `application/core/batch_writer.py` | — | Batch write operations |
| `BatchMemoryManager` | `application/core/batch_memory_manager.py` | — | Memory management for batches |
| `BatchMetrics` | `application/core/batch_metrics.py` | — | Batch-level metrics recording |
| `BatchTracing` | `application/core/batch_tracing.py` | — | Batch-level tracing |
| `RecordProcessor` | `application/core/record_processor.py` | — | Record-level processing pipeline |
| `PipelineRunnerService` | `application/services/pipeline_runner_service.py` | — | Service-level pipeline execution |
| `MedallionLifecycleService` | `application/services/medallion_lifecycle.py` | — | Medallion clear/rebuild policy |
| `MedallionTypes` | `application/services/medallion_types.py` | — | Medallion service type definitions |
| `PreflightService` | `application/core/preflight_service.py` | — | Pre-run validation checks |
| `PostrunService` | `application/core/postrun_service.py` | — | Post-run cleanup and metrics |
| `CleanupService` | `application/core/cleanup_service.py` | — | Resource cleanup |
| `HeartbeatService` | `application/core/heartbeat.py` | — | Pipeline liveness monitoring |
| `ShutdownService` | `application/services/shutdown_service.py` | — | Graceful termination |
| `PipelineServicesModule` | `application/core/pipeline_services.py` | — | Pipeline service composition |
| `BasePipeline` | `application/core/base.py` | — | Base pipeline class |
| `CoreConfig` | `application/core/config.py` | — | Core configuration |
| `CoreProtocols` | `application/core/protocols.py` | — | Core protocol definitions |

---

## Component 6: Composite Pipeline

Multi-source data aggregation and merging.

| Object | Source File | Implements Port | Description |
|--------|------------|-----------------|-------------|
| `CompositeRunner` | `application/composite/runner.py` | `RunnablePort` | Composite pipeline orchestrator |
| `CompositeRunnerHelpers` | `application/composite/runner_helpers.py` | — | Runner utility functions |
| `CompositeCoordinator` | `application/composite/coordinator.py` | — | Coordination logic |
| `DependencyCoordinator` | `application/composite/dependency_coordinator.py` | — | Source dependency management |
| `CompositeAggregator` | `application/composite/aggregator.py` | — | Data aggregation across sources |
| `CompositeMerger` | `application/composite/merger.py` | — | DataFrame merging logic |
| `CompositeCrossValidator` | `application/composite/cross_validator.py` | — | Cross-source validation |
| `CompositeDeduplication` | `application/composite/deduplication.py` | — | Cross-source deduplication |
| `CompositeColumnOrderer` | `application/composite/column_orderer.py` | — | Column ordering for Gold output |
| `CompositeColumnRenamer` | `application/composite/column_renamer.py` | — | Column renaming |
| `CompositeKeyExtractor` | `application/composite/key_extractor.py` | — | Join key extraction |
| `CompositePreflightValidator` | `application/composite/preflight_validator.py` | — | Pre-merge validation |
| `CompositeCheckpoint` | `application/composite/checkpoint.py` | — | Composite-specific checkpointing |
| `CompositeFSMHelper` | `application/composite/fsm_helper.py` | — | Composite state machine |

---

## Component 7: Configuration Management

Loading, validating, and providing configurations.

| Object | Source File | Implements Port | Description |
|--------|------------|-----------------|-------------|
| `PipelineConfigLoader` | `infrastructure/config/pipeline_config_loader.py` | — | Pipeline YAML loading |
| `DQConfigLoader` | `infrastructure/config/dq_config_loader.py` | DQ config ports | DQ rules loading |
| `FilterConfigLoader` | `infrastructure/config/filter_config_loader.py` | — | Filter rules loading |
| `FieldGroupLoader` | `infrastructure/config/field_group_loader.py` | — | Field group definitions |
| `ContractPolicyLoader` | `infrastructure/config/contract_policy_loader.py` | — | Contract policies |
| `BaseConfigLoader` | `infrastructure/config/base_config_loader.py` | — | Shared loading base |
| `ConfigBase` | `infrastructure/config/_base.py` | — | Config base utilities |
| `ConfigConverters` | `infrastructure/config/converters.py` | — | Type converters |
| `ConfigLoader` | `infrastructure/config_loader.py` | — | Top-level config loading |
| `ConfigService` | `application/services/config_service.py` | — | Config validation service |
| Pydantic schemas | `infrastructure/schemas/*.py` | — | Pipeline, DQ, filter, composite, source schemas |

---

## Component 8: Observability

Structured logging, Prometheus metrics, distributed tracing.

| Object | Source File | Implements Port | Description |
|--------|------------|-----------------|-------------|
| `UnifiedLogger` | `infrastructure/observability/unified_logger.py` | `LoggerPort` | Structured logging (structlog) |
| `NoOpLogger` | `infrastructure/observability/noop_logger.py` | `LoggerPort` | Null object for logging |
| `LoggingConfig` | `infrastructure/observability/logging_config.py` | — | Logging configuration |
| `LoggingModule` | `infrastructure/observability/logging.py` | — | Logging setup |
| `PrometheusMetrics` | `infrastructure/observability/prometheus_metrics.py` | `MetricsPort` | Prometheus metric emission |
| `MetricsModule` | `infrastructure/observability/metrics.py` | — | Metrics setup |
| `MetricsServerAdapter` | `infrastructure/observability/metrics_server_adapter.py` | — | Metrics HTTP server adapter |
| `MetricsServer` | `infrastructure/observability/server.py` | — | Metrics HTTP server |
| `OpenTelemetryTracing` | `infrastructure/observability/tracing.py` | `TracingPort` | OpenTelemetry tracing |
| `NoOpTracing` | `domain/ports/tracing_port.py` | `TracingPort` | Null object for tracing |
| `NoOpMetrics` | `domain/ports/metrics_port.py` | `MetricsPort` | Null object for metrics |
| `MetricsService` | `application/services/metrics_service.py` | — | Application-level metrics |
| `Observer` | `application/observability/observer.py` | — | Event observation |
| `SpanHelpers` | `application/observability/span_helpers.py` | — | Tracing span utilities |

---

## Component 9: Resilience

Fault tolerance for external API communication.

| Object | Source File | Implements Port | Description |
|--------|------------|-----------------|-------------|
| `CircuitBreaker` | `infrastructure/adapters/http/circuit_breaker.py` | `CircuitBreakerPort` | Circuit breaker state machine |
| `TokenBucketRateLimiter` | `infrastructure/adapters/http/rate_limiter.py` | `RateLimiterPort` | Token bucket rate limiting |
| `Pagination` | `infrastructure/adapters/http/pagination.py` | — | Pagination strategies (offset, cursor) |
| `HttpClient` | `infrastructure/adapters/http/client.py` | — | Core HTTP client with resilience |
| `HttpHealth` | `infrastructure/adapters/http/health.py` | — | HTTP health checking |
| `HealthMonitor` | `infrastructure/adapters/http/health_monitor.py` | `HealthMonitorPort` | Continuous health tracking |
| `RetryDecorator` | `infrastructure/adapters/decorators/retry.py` | — | Exponential backoff retry |
| `CircuitBreakerDecorator` | `infrastructure/adapters/decorators/circuit_breaker.py` | — | Circuit breaker decorator |
| `RetryConfig` | `domain/resilience.py` | — | Retry strategy configuration |

---

## Component 10: Security & Privacy

PII hashing, authentication.

| Object | Source File | Implements Port | Description |
|--------|------------|-----------------|-------------|
| `PiiHasher` | `infrastructure/security/pii_hasher.py` | `PiiHasherPort` | SHA256-based PII hashing |
| `NoOpPiiHasher` | `domain/ports/pii_hasher_port.py` | `PiiHasherPort` | Null object |
| `AuthFailureError` | `domain/exceptions/internal.py` | — | Auth failure exception |

---

## Component 11: Locking & Concurrency

Pipeline-level locking to prevent concurrent execution.

| Object | Source File | Implements Port | Description |
|--------|------------|-----------------|-------------|
| `MemoryLock` | `infrastructure/locking/memory_lock.py` | `LockPort` | In-process locking |
| `LockManager` | `application/core/lock_manager.py` | — | Application-level lock management |
| `LockService` | `application/services/lock_service.py` | — | Lock lifecycle service |
| `FencingToken` | `domain/locking.py` | — | Monotonic fencing token |
| `LockContext` | `domain/locking.py` | — | Immutable lock state |
| `LockContextHolder` | `domain/locking.py` | — | Mutable lock state holder |
| `LockNotHeldError` | `domain/locking.py` | — | Lock not held exception |
| `LockLostError` | `domain/exceptions/internal.py` | — | Lock lost exception |
| `LockAcquisitionError` | `domain/exceptions/internal.py` | — | Acquisition failure |

---

## Component 12: Checkpoint & State Management

Pipeline progress persistence for resume capability.

| Object | Source File | Implements Port | Description |
|--------|------------|-----------------|-------------|
| `LocalCheckpoint` | `infrastructure/checkpoint/local_checkpoint.py` | `CheckpointPort` | File-based checkpoint |
| `CheckpointManager` | `application/core/checkpoint_manager.py` | — | Checkpoint management |
| `CheckpointService` | `application/services/checkpoint_service.py` | — | Checkpoint lifecycle |
| `CheckpointConflictError` | `domain/exceptions/internal.py` | — | Conflict exception |

---

## Component 13: Quarantine System

Failed record isolation and management.

| Object | Source File | Implements Port | Description |
|--------|------------|-----------------|-------------|
| `UnifiedQuarantine` | `infrastructure/quarantine/unified.py` | `QuarantinePort` | Unified quarantine storage |
| `QuarantineOperations` | `infrastructure/quarantine/operations.py` | — | CRUD operations |
| `QuarantineRecordEncoding` | `infrastructure/quarantine/record_encoding.py` | — | Record serialization |
| `QuarantineManager` | `application/core/quarantine_manager.py` | — | Quarantine management |
| `QuarantineService` | `application/services/quarantine_service.py` | — | Quarantine lifecycle |
| `QuarantineEntry` | `domain/aggregates/quarantine_entry.py` | — | Domain aggregate |

---

## Component 14: Audit Trail

Write operation audit logging.

| Object | Source File | Implements Port | Description |
|--------|------------|-----------------|-------------|
| `FileAudit` | `infrastructure/audit/file_audit.py` | `AuditPort` | File-based audit writer |
| `NoOpAudit` | `domain/ports/audit_port.py` | `AuditPort` | Null object |

---

## Component 15: Export & Reporting

Data export to external formats.

| Object | Source File | Implements Port | Description |
|--------|------------|-----------------|-------------|
| `CsvExporter` | `infrastructure/export/csv_exporter.py` | — | Delta Lake → CSV export |
| `DQReportWriter` | `infrastructure/export/dq_report_writer.py` | `DQReportWriterPort` | DQ report file writing |
| `ExportService` | `application/services/export_service.py` | — | Export lifecycle |
| `DQReportService` | `application/services/dq_report_service.py` | — | DQ report generation |

---

## Component 16: Health Monitoring

Provider and system health assessment.

| Object | Source File | Implements Port | Description |
|--------|------------|-----------------|-------------|
| `HealthService` | `application/services/health_service.py` | — | Health check orchestration |
| `HealthMonitor` | `infrastructure/adapters/http/health_monitor.py` | `HealthMonitorPort` | Continuous state tracking |
| `MemoryMonitor` | `infrastructure/system/memory_monitor.py` | `MemoryMonitorPort` | Memory stats monitoring |
| `NoOpMemoryMonitor` | `domain/ports/memory_monitor_port.py` | `MemoryMonitorPort` | Null object |
| `HealthReport` | `domain/types.py` | — | Health report value object |
| `PreflightReport` | `domain/types.py` | — | Pre-run health assessment |
| `ComponentHealthResult` | `domain/types.py` | — | Per-component health result |
| `HealthServer` | `interfaces/http/health_server.py` | — | HTTP health endpoint |

---

## Component 17: Data Extraction (Parsers & Extractors)

Documented above in Component 3 (inline with transformers).

---

## Component 18: Dependency Injection (Composition Root)

Wiring ports to concrete adapters, creating assembled pipelines.

| Object | Source File | Implements Port | Description |
|--------|------------|-----------------|-------------|
| `DataSourceFactory` | `composition/factories/data_source_factory.py` | — | Creates provider data sources |
| `HttpClientFactory` | `composition/factories/http_client_factory.py` | — | Creates HTTP clients |
| `PipelineFactory` | `composition/factories/pipeline_factory.py` | — | Creates pipeline instances |
| `PipelineFactories` | `composition/factories/pipeline_factories.py` | — | Provider-specific factories |
| `RunnerFactory` | `composition/factories/runner_factory.py` | `RunnerFactoryPort` | Creates pipeline runners |
| `StorageFactory` | `composition/factories/storage_factory.py` | — | Creates storage adapters |
| `StorageAdapterFactory` | `composition/factories/storage_adapter.py` | — | Storage adapter creation |
| `StorageModule` | `composition/factories/storage.py` | — | Storage wiring |
| `TransformerFactory` | `composition/factories/transformer_factory.py` | — | Creates transformers |
| `ServicesFactory` | `composition/factories/services_factory.py` | — | Creates services |
| `DQFactory` | `composition/factories/dq_factory.py` | — | Creates DQ components |
| `ProviderRegistry` | `composition/providers/provider_registry.py` | — | Available providers |
| `ProviderRegistration` | `composition/providers/registration.py` | — | Provider registration |
| `ProviderDecorators` | `composition/providers/decorators.py` | — | Registration decorators |
| `FactoryLoader` | `composition/providers/factory_loader.py` | — | Dynamic factory loading |
| `ProviderLoader` | `composition/providers/loader.py` | — | Provider loading |
| `ConfigHelpers` | `composition/providers/_config_helpers.py` | — | Config helper functions |
| `RuntimeAssembly` | `composition/bootstrap/runtime/assembly.py` | — | Runtime component assembly |
| `PipelineAssembly` | `composition/bootstrap/runtime/pipeline.py` | — | Pipeline assembly |
| `RunnerAssembly` | `composition/bootstrap/runtime/runner.py` | — | Runner assembly |
| `CompositeAssembly` | `composition/bootstrap/runtime/composite.py` | — | Composite assembly |
| `ObservabilityAssembly` | `composition/bootstrap/runtime/observability.py` | — | Observability wiring |
| `Entrypoints` | `composition/entrypoints.py` | — | Main entry points |
| `Builders` | `composition/builders.py` | — | High-level builders |
| `BootstrapContexts` | `composition/bootstrap_contexts.py` | — | Bootstrap context management |
| `BootstrapLogger` | `composition/bootstrap_logger.py` | — | Bootstrap-time logging |
| `Registry` | `composition/registry.py` | — | Central pipeline registry |
| `MetadataCoordinator` | `composition/services/metadata_coordinator.py` | `MetadataCoordinatorPort` | Metadata coordination |
| `Versioning` | `composition/services/versioning.py` | — | Version management |
| CLI bootstraps | `composition/bootstrap/cli/*.py` | — | CLI-specific assembly (checkpoint, config, health, lock, metrics, noop, storage) |
| Storage assembly | `composition/bootstrap/assembly/*.py` | — | Storage assembly (checkpoint, storage) |

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total components identified | 18 |
| Total unique objects cataloged | ~260 |
| Objects implementing domain Ports | ~30 |
| Factory classes | 11 |
| NoOp/Null object implementations | 6 |
| Exception classes | 35+ |
| Pandera Gold schemas | 50+ |

---

*Generated: 2026-02-23 | BioETL Component–Object Inventory*
