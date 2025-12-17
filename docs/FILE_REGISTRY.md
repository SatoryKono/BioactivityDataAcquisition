# File Registry / Реестр файлов

*Generated: 2025-12-17*

## Summary / Сводка

```
Всего файлов кода (без тестов): 47
Диаграмм существует: 5 (высокоуровневые)
Модульных диаграмм: 0 → требуется создать
```

## Module Registry / Реестр модулей

| # | Path | Layer | Module Type | LOC | Main Classes/Functions | Diagram Status |
|---|------|-------|-------------|-----|------------------------|----------------|
| **DOMAIN LAYER** |||||
| 1 | `src/bioetl/domain/ports.py` | domain | port | 403 | DataSourcePort, StoragePort, LockPort, CheckpointPort, QuarantinePort, MetricsPort | missing |
| 2 | `src/bioetl/domain/types.py` | domain | value_object | 218 | RunID, EntityID, ContentHash, BatchID, Watermark, RunType, DriftLevel, HealthStatus, CircuitBreakerState, ErrorType, DQStatus | missing |
| 3 | `src/bioetl/domain/transformations.py` | domain | util | 185 | normalize_for_hash, canonical_json_dumps, generate_content_hash, generate_entity_id, detect_schema_drift | missing |
| 4 | `src/bioetl/domain/exceptions.py` | domain | exception | 256 | BioETLError, CriticalError, RecoverableError, DataQualityError, LockLostError, RateLimitError, ApiError | missing |
| 5 | `src/bioetl/domain/error_classifier.py` | domain | util | 119 | ErrorClassifier | missing |
| 6 | `src/bioetl/domain/context.py` | domain | value_object | 61 | PipelineContext, BoundLogger | missing |
| **APPLICATION LAYER - Core** |||||
| 7 | `src/bioetl/application/core/base.py` | application | service | 299 | BasePipeline (ABC), run_pipeline_flow | missing |
| 8 | `src/bioetl/application/core/protocols.py` | application | port | 19 | TransformCallback, GoldFilterCallback | skip (<20 LOC) |
| 9 | `src/bioetl/application/core/pipeline_config.py` | application | config | 70 | PipelineConfig, PipelineRuntimeConfig | missing |
| 10 | `src/bioetl/application/core/pipeline_services.py` | application | dto | 96 | PipelineServices | missing |
| 11 | `src/bioetl/application/core/checkpoint_manager.py` | application | service | 68 | CheckpointManager | missing |
| 12 | `src/bioetl/application/core/lock_manager.py` | application | service | 123 | LockManager | missing |
| 13 | `src/bioetl/application/core/quarantine_manager.py` | application | service | 54 | QuarantineManager | missing |
| 14 | `src/bioetl/application/core/executor.py` | application | service | 118 | PipelineExecutor | missing |
| 15 | `src/bioetl/application/core/record_processor.py` | application | service | 136 | RecordProcessor | missing |
| 16 | `src/bioetl/application/core/orchestrator.py` | application | service | 233 | PipelineOrchestrator | missing |
| 17 | `src/bioetl/application/core/shutdown.py` | application | util | 77 | ShutdownSignal, PipelineShutdownError | missing |
| **APPLICATION LAYER - Pipelines** |||||
| 18 | `src/bioetl/application/pipelines/chembl_activity.py` | application | pipeline | 123 | ChEMBLActivityPipeline | missing |
| **INFRASTRUCTURE LAYER - HTTP Adapters** |||||
| 19 | `src/bioetl/infrastructure/adapters/http/rate_limiter.py` | infrastructure | adapter | 145 | TokenBucket | missing |
| 20 | `src/bioetl/infrastructure/adapters/http/circuit_breaker.py` | infrastructure | adapter | 182 | CircuitBreaker | missing |
| 21 | `src/bioetl/infrastructure/adapters/http/pagination.py` | infrastructure | adapter | 82 | PageFetcher, PaginatedFetcherMixin | missing |
| 22 | `src/bioetl/infrastructure/adapters/http/client.py` | infrastructure | adapter | 246 | UnifiedHTTPClient, RetryConfig | missing |
| **INFRASTRUCTURE LAYER - Data Source Adapters** |||||
| 23 | `src/bioetl/infrastructure/adapters/chembl/client.py` | infrastructure | adapter | 301 | ChemblAdapter | missing |
| 24 | `src/bioetl/infrastructure/adapters/pubchem/client.py` | infrastructure | adapter | 381 | PubChemClient | missing |
| 25 | `src/bioetl/infrastructure/adapters/uniprot/client.py` | infrastructure | adapter | 421 | UniProtClient | missing |
| **INFRASTRUCTURE LAYER - Storage** |||||
| 26 | `src/bioetl/infrastructure/storage/bronze_writer.py` | infrastructure | adapter | 285 | BronzeWriter | missing |
| 27 | `src/bioetl/infrastructure/storage/delta_writer.py` | infrastructure | adapter | 286 | DeltaWriter | missing |
| 28 | `src/bioetl/infrastructure/storage/gold_writer.py` | infrastructure | adapter | 248 | GoldWriter | missing |
| 29 | `src/bioetl/infrastructure/storage/s3_pool.py` | infrastructure | util | 124 | S3ClientPool | missing |
| **INFRASTRUCTURE LAYER - Locking** |||||
| 30 | `src/bioetl/infrastructure/locking/memory_lock.py` | infrastructure | adapter | 50 | MemoryLock | missing |
| 31 | `src/bioetl/infrastructure/locking/redis_lock.py` | infrastructure | adapter | 242 | RedisDistributedLock | missing |
| **INFRASTRUCTURE LAYER - Checkpoint** |||||
| 32 | `src/bioetl/infrastructure/checkpoint/s3_checkpoint.py` | infrastructure | adapter | 233 | S3Checkpoint | missing |
| **INFRASTRUCTURE LAYER - Quarantine** |||||
| 33 | `src/bioetl/infrastructure/quarantine/unified_quarantine.py` | infrastructure | adapter | 484 | UnifiedQuarantine | missing |
| **INFRASTRUCTURE LAYER - Observability** |||||
| 34 | `src/bioetl/infrastructure/observability/logging.py` | infrastructure | adapter | 65 | create_logger | missing |
| 35 | `src/bioetl/infrastructure/observability/metrics.py` | infrastructure | adapter | 54 | MetricsCollector | missing |
| 36 | `src/bioetl/infrastructure/observability/noop_metrics.py` | infrastructure | adapter | 79 | NoOpMetrics | missing |
| 37 | `src/bioetl/infrastructure/observability/prometheus_metrics.py` | infrastructure | adapter | 74 | PrometheusMetrics | missing |
| 38 | `src/bioetl/infrastructure/observability/lineage.py` | infrastructure | adapter | 450 | LineageTracker, LineageRecord | missing |
| 39 | `src/bioetl/infrastructure/observability/anomaly.py` | infrastructure | adapter | 445 | AnomalyDetector, Anomaly, AnomalyType | missing |
| **INFRASTRUCTURE LAYER - Factories & Config** |||||
| 40 | `src/bioetl/infrastructure/config.py` | infrastructure | config | 270 | Settings, load_pipeline_config | missing |
| 41 | `src/bioetl/infrastructure/factories/storage.py` | infrastructure | factory | 77 | StorageAdapter | missing |
| 42 | `src/bioetl/infrastructure/factories/clients.py` | infrastructure | factory | 56 | create_redis_client, get_aws_credentials | missing |
| **INTERFACES LAYER** |||||
| 43 | `src/bioetl/interfaces/bootstrap.py` | interfaces | factory | 95 | bootstrap_logger, bootstrap_pipeline | missing |
| 44 | `src/bioetl/interfaces/cli.py` | interfaces | handler | 128 | cli, run, quarantine, checkpoint | missing |
| 45 | `src/bioetl/interfaces/orchestration/runner.py` | interfaces | handler | 114 | PipelineRunner | missing |
| 46 | `src/bioetl/interfaces/orchestration/signals.py` | interfaces | handler | 35 | setup_shutdown_handlers | missing |
| 47 | `src/bioetl/interfaces/orchestration/prefect/tasks.py` | interfaces | handler | 74 | execute_pipeline_task, run_pipeline_flow | missing |
| 48 | `src/bioetl/interfaces/factories/chembl_activity.py` | interfaces | factory | 229 | ChEMBLActivityPipelineFactory | missing |

## Layer Statistics / Статистика по слоям

| Layer | Modules | Total LOC | Main Purpose |
|-------|---------|-----------|--------------|
| domain | 6 | 1,242 | Pure business logic, ports, types |
| application | 12 | 1,413 | Business workflows, lifecycle management |
| infrastructure | 21 | 4,597 | External system integrations |
| interfaces | 6 | 675 | Entry points (CLI, orchestration) |
| **TOTAL** | **45** | **7,927** | |

## Excluded Files / Исключённые файлы

Files excluded from diagram generation:
- `__init__.py` files (re-exports only)
- Files < 10 LOC
- `src/tools/repro_watermark.py` (utility script)
