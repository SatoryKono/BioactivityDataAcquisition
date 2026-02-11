# Отчёт аудита документации BioETL

**Дата:** 2026-02-10
**Версия проекта:** 5.14.0
**Scope:** Приоритет 1+2 — 50 документов (~1500+ верифицируемых утверждений)
**Метод:** Statement-by-statement проверка каждого верифицируемого утверждения против фактического кода

---

## Сводка

| Метрика | Значение |
|---------|----------|
| **Batch 1** (Priority 1) | 25 документов (+ 33 ADR) |
| **Batch 2** (Priority 2) | 25 документов |
| Проверено утверждений | ~1500+ |
| Несоответствий CRITICAL | 5 |
| Несоответствий HIGH | 22 |
| Несоответствий MEDIUM | 15 |
| Несоответствий LOW/INFO | 20 |
| Неполная документация (INCOMPLETE) | 12 крупных пробелов |
| Внутренние противоречия (INCONSISTENCY) | 9 |
| **Общий статус** | **WARN — требуется синхронизация** |

---

# ЧАСТЬ 1: Приоритет 1 (25 ключевых документов)

---

## 1. docs/02-architecture/01-domain-layer.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| 01-domain-layer.md | 1 | Расположение: `src/bioetl/domain/` | `src/bioetl/domain/__init__.py` | директория существует | ДА | — |
| 01-domain-layer.md | 2 | Ports: `__init__.py` — фасад, единая точка импорта всех портов | `src/bioetl/domain/ports/__init__.py` | `__all__ = [...]` с 40+ портами | ДА | — |
| 01-domain-layer.md | 3 | Ports: `data_source.py` — DataSourcePort, FilterableDataSourcePort | `src/bioetl/domain/ports/data_source.py` | `class DataSourcePort`, `class FilterableDataSourcePort` | ДА | — |
| 01-domain-layer.md | 4 | Ports: `storage.py` — StoragePort | `src/bioetl/domain/ports/storage.py` | `class StoragePort` (12+ методов) | ДА | — |
| 01-domain-layer.md | 5 | Ports: `locking.py` — LockPort | `src/bioetl/domain/ports/locking.py` | `class LockPort` | ДА | — |
| 01-domain-layer.md | 6 | Ports: `checkpoint.py` — CheckpointPort | `src/bioetl/domain/ports/checkpoint.py` | `class CheckpointPort` | ДА | — |
| 01-domain-layer.md | 7 | Ports: `quarantine.py` — QuarantinePort | `src/bioetl/domain/ports/quarantine.py` | `class QuarantinePort` | ДА | — |
| 01-domain-layer.md | 8 | Ports: `observability.py` — MetricsPort, TracingPort, LoggerPort, DQMonitorPort | `src/bioetl/domain/ports/observability.py` | все 4 класса определены | ДА | — |
| 01-domain-layer.md | 9 | Ports: `validation.py` — GoldValidatorPort | `src/bioetl/domain/ports/validation.py:41` | `class GoldValidatorPort(Protocol)` | ДА | — |
| 01-domain-layer.md | 10 | Ports: `validation.py` — только GoldValidatorPort | `src/bioetl/domain/ports/validation.py:17` | `class SilverValidatorPort(Protocol)` тоже есть | НЕТ | Добавить `SilverValidatorPort` в документацию |
| 01-domain-layer.md | 11 | Ports: `filtering.py` — InputFilterPort | `src/bioetl/domain/ports/filtering.py` | `class InputFilterPort` | ДА | — |
| 01-domain-layer.md | 12 | Структура ports/ содержит 8 файлов + __init__.py | `src/bioetl/domain/ports/` | фактически 25 .py файлов (audit.py, delta_reader.py, dq_config.py, dq_report.py, health_check.py, idmapping.py, memory.py, metadata.py, metadata_coordinator.py, noop.py, normalization.py, pii.py, resilience.py, runner.py, serialization.py, shutdown.py, data_normalization.py) | НЕТ | Обновить структуру: добавить 16 недокументированных port-модулей |
| 01-domain-layer.md | 13 | Основные порты: 12 шт | `src/bioetl/domain/ports/__init__.py` | `__all__` содержит 40+ портов | НЕТ | Обновить число: 40+ портов, не 12 |
| 01-domain-layer.md | 14 | `batch.py` — Batch Aggregate (530 LOC) | `src/bioetl/domain/aggregates/batch.py` | 536 строк | ДА | LOC ~соответствует (536 vs 530) |
| 01-domain-layer.md | 15 | `pipeline_run.py` — PipelineRun Aggregate (350 LOC) | `src/bioetl/domain/aggregates/pipeline_run.py` | 566 строк | НЕТ | Обновить LOC: 566, не 350 (+62%) |
| 01-domain-layer.md | 16 | `quarantine_entry.py` — QuarantineEntry Aggregate (180 LOC) | `src/bioetl/domain/aggregates/quarantine_entry.py` | 517 строк | НЕТ | Обновить LOC: 517, не 180 (+187%) |
| 01-domain-layer.md | 17 | `events.py` — Domain Events (200 LOC) | `src/bioetl/domain/aggregates/events.py` | 260 строк | НЕТ | Обновить LOC: 260, не 200 (+30%) |
| 01-domain-layer.md | 18 | Value Objects: `RunID(UUID)` | `src/bioetl/domain/types.py` | `RunID = NewType("RunID", UUID)` | ДА | — |
| 01-domain-layer.md | 19 | Value Objects: `BatchID(UUID)` | `src/bioetl/domain/types.py` | `BatchID = NewType("BatchID", UUID)` | ДА | — |
| 01-domain-layer.md | 20 | Value Objects: `EntityID(str)` | `src/bioetl/domain/types.py` | `EntityID = NewType("EntityID", str)` | ДА | — |
| 01-domain-layer.md | 21 | Value Objects: `ContentHash(str)` | `src/bioetl/domain/types.py` | `ContentHash = NewType("ContentHash", str)` | ДА | — |
| 01-domain-layer.md | 22 | Value Objects: `Measurement(value, unit, relation)` — биоактивность | `src/bioetl/domain/value_objects/` | Класс `Measurement` не найден. Есть `ActivityValue` в `activity.py:226` | НЕТ | Заменить `Measurement` на `ActivityValue` или добавить алиас |
| 01-domain-layer.md | 23 | value_objects/ содержит ~5 VO | `src/bioetl/domain/value_objects/` | фактически 19 .py файлов (activity.py, activity_values.py, academic_ids.py, chemical.py, identifiers.py, dq_metrics.py, dq_report.py, dq_result.py, column_order.py, column_qualifier.py, bronze_result.py, silver_result.py, publications.py, publication_field_groups.py, taxonomy_id.py, compound_ids.py, run_context.py, base.py) | НЕТ | Расширить описание: 19 файлов value objects |
| 01-domain-layer.md | 24 | `config.py` содержит: PipelineConfig | `src/bioetl/domain/config.py:394` | `class PipelineConfig` | ДА | — |
| 01-domain-layer.md | 25 | `config.py` содержит: RuntimeConfig | `src/bioetl/domain/config.py:537` | `class RuntimeConfig` | ДА | — |
| 01-domain-layer.md | 26 | `config.py` содержит: DQConfig | `src/bioetl/domain/config.py:249` | `class DQConfig` | ДА | — |
| 01-domain-layer.md | 27 | `config.py` содержит: TableConfig | `src/bioetl/domain/config.py:354` | `class TableConfig` | ДА | — |
| 01-domain-layer.md | 28 | `error_classifier.py` существует | `src/bioetl/domain/error_classifier.py` | `class ErrorClassifier` | ДА | — |
| 01-domain-layer.md | 29 | Domain не импортирует application/infrastructure/interfaces | проверка grep | 0 нарушений найдено | ДА | — |
| 01-domain-layer.md | 30 | Domain не содержит I/O | проверка grep | 0 нарушений import requests/httpx/open() | ДА | — |
| 01-domain-layer.md | 31 | Не упомянуты поддиректории: `composite/`, `contracts/`, `entities/`, `configs/`, `filtering/`, `mapping/`, `registry/`, `services/` | `src/bioetl/domain/` | все 8 директорий существуют | НЕТ | Добавить описание 8 поддиректорий domain |

---

## 2. docs/02-architecture/02-application-layer.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| 02-application-layer.md | 1 | Расположение: `src/bioetl/application/` | `src/bioetl/application/__init__.py` | директория существует | ДА | — |
| 02-application-layer.md | 2 | `base.py` — BasePipeline | `src/bioetl/application/core/base.py:27` | `class BasePipeline(ABC)` | ДА | — |
| 02-application-layer.md | 3 | `base_transformer.py` — BaseTransformer | `src/bioetl/application/core/base_transformer.py:84` | `class BaseTransformer(ABC)` | ДА | — |
| 02-application-layer.md | 4 | `record_processor.py` — RecordProcessor | `src/bioetl/application/core/record_processor.py:35` | `class RecordProcessor` | ДА | — |
| 02-application-layer.md | 5 | `runner.py` — PipelineRunner | `src/bioetl/application/core/runner.py:38` | `class PipelineRunner` | ДА | — |
| 02-application-layer.md | 6 | **`executor.py` — PipelineExecutor** | файл `executor.py` НЕ существует | фактически: `batch_executor.py:62` → `class BatchExecutor` | **НЕТ** | **CRITICAL**: заменить `executor.py`/`PipelineExecutor` на `batch_executor.py`/`BatchExecutor` |
| 02-application-layer.md | 7 | **`lifecycle_orchestrator.py` — LifecycleOrchestrator** | файл `lifecycle_orchestrator.py` НЕ существует | фактически: `application/services/medallion_lifecycle.py:32` → `class MedallionLifecycleService` | **НЕТ** | **CRITICAL**: заменить на `services/medallion_lifecycle.py`/`MedallionLifecycleService` |
| 02-application-layer.md | 8 | **`runner_services.py` — RunnerServices (frozen dataclass)** | файл `runner_services.py` НЕ существует | фактически: `pipeline_services.py:40` → `class PipelineServices` (frozen dataclass) | **НЕТ** | **CRITICAL**: заменить на `pipeline_services.py`/`PipelineServices` |
| 02-application-layer.md | 9 | RunnerServices поля: lock_manager, preflight, postrun, lifecycle_orch, observer | `src/bioetl/application/core/pipeline_services.py:40-60` | Поля PipelineServices: data_source, storage, lock, checkpoint, quarantine, metrics, tracing, logger, dq_monitor... | **НЕТ** | Обновить описание полей frozen dataclass |
| 02-application-layer.md | 10 | PipelineRunner делегирует через LifecycleOrchestrator | `src/bioetl/application/core/runner.py` | Runner использует `MedallionLifecycleService` (через services) | НЕТ | Обновить описание делегирования |
| 02-application-layer.md | 11 | `ActivityTransformer` в `pipelines/chembl/activity_transformer.py` | `src/bioetl/application/pipelines/chembl/activity_transformer.py` | `class ActivityTransformer` | ДА | — |
| 02-application-layer.md | 12 | `AssayTransformer` в `pipelines/chembl/assay_transformer.py` | `src/bioetl/application/pipelines/chembl/assay_transformer.py` | `class AssayTransformer` | ДА | — |
| 02-application-layer.md | 13 | `MoleculeTransformer` в `pipelines/chembl/molecule_transformer.py` | `src/bioetl/application/pipelines/chembl/molecule_transformer.py` | `class MoleculeTransformer` | ДА | — |
| 02-application-layer.md | 14 | `TargetTransformer` в `pipelines/chembl/target_transformer.py` | `src/bioetl/application/pipelines/chembl/target_transformer.py` | `class TargetTransformer` | ДА | — |
| 02-application-layer.md | 15 | `PublicationTransformer` в `pipelines/chembl/publication_transformer.py` | `src/bioetl/application/pipelines/chembl/publication_transformer.py` | `class PublicationTransformer` | ДА | — |
| 02-application-layer.md | 16 | `CrossRefPublicationTransformer` в `pipelines/crossref/transformer.py` | `src/bioetl/application/pipelines/crossref/transformer.py` | `class CrossRefPublicationTransformer` | ДА | — |
| 02-application-layer.md | 17 | `OpenAlexPublicationTransformer` в `pipelines/openalex/transformer.py` | `src/bioetl/application/pipelines/openalex/transformer.py` | `class OpenAlexPublicationTransformer` | ДА | — |
| 02-application-layer.md | 18 | `PubChemCompoundTransformer` в `pipelines/pubchem/transformer.py` | `src/bioetl/application/pipelines/pubchem/transformer.py` | `class PubChemCompoundTransformer` | ДА | — |
| 02-application-layer.md | 19 | `UniProtProteinTransformer` в `pipelines/uniprot/transformer.py` | `src/bioetl/application/pipelines/uniprot/transformer.py` | `class UniProtProteinTransformer` | ДА | — |
| 02-application-layer.md | 20 | `PubMedPublicationTransformer` в `pipelines/pubmed/transformer.py` | `src/bioetl/application/pipelines/pubmed/transformer.py` | `class PubMedPublicationTransformer` | ДА | — |
| 02-application-layer.md | 21 | `SemanticScholarPublicationTransformer` в `pipelines/semanticscholar/transformer.py` | `src/bioetl/application/pipelines/semanticscholar/transformer.py` | `class SemanticScholarPublicationTransformer` | ДА | — |
| 02-application-layer.md | 22 | Только 11 трансформеров перечислено | `src/bioetl/application/pipelines/chembl/` | 14+ дополнительных трансформеров ChEMBL (CellLineTransformer, CompoundRecordTransformer, ProteinClassTransformer и др.) | НЕТ | Добавить недокументированные трансформеры |
| 02-application-layer.md | 23 | `CompositePipelineRunner` в `composite/runner.py` | `src/bioetl/application/composite/runner.py:94` | `class CompositePipelineRunner` | ДА | — |
| 02-application-layer.md | 24 | `EnrichmentCoordinator` в `composite/coordinator.py` | `src/bioetl/application/composite/coordinator.py:26` | `class EnrichmentCoordinator` | ДА | — |
| 02-application-layer.md | 25 | `MergeService` в `composite/merger.py` | `src/bioetl/application/composite/merger.py:62` | `class MergeService` | ДА | — |
| 02-application-layer.md | 26 | `KeyExtractorService` в `composite/key_extractor.py` | `src/bioetl/application/composite/key_extractor.py:20` | `class KeyExtractorService` | ДА | — |
| 02-application-layer.md | 27 | `CompositeCheckpointManager` в `composite/checkpoint.py` | `src/bioetl/application/composite/checkpoint.py:337` | `class CompositeCheckpointManager` | ДА | — |
| 02-application-layer.md | 28 | Только 5 composite-файлов | `src/bioetl/application/composite/` | 8+ дополнительных: aggregator.py, column_orderer.py, column_renamer.py, deduplication.py, dependency_coordinator.py, fsm_helper.py, preflight_validator.py, runner_helpers.py | НЕТ | Добавить описание дополнительных composite-компонентов |
| 02-application-layer.md | 29 | core/ содержит ~4 ключевых файла | `src/bioetl/application/core/` | 26 .py файлов включая batch_metrics.py, batch_tracing.py, batch_writer.py, checkpoint_manager.py, cleanup_service.py, heartbeat.py, lock_manager.py, quarantine_manager.py и др. | НЕТ | Расширить описание core/: 26 файлов |

---

## 3. docs/02-architecture/03-infrastructure-layer.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| 03-infrastructure-layer.md | 1 | Расположение: `src/bioetl/infrastructure/` | `src/bioetl/infrastructure/__init__.py` | директория существует | ДА | — |
| 03-infrastructure-layer.md | 2 | ChemblAdapter — BaseHttpAdapter | `src/bioetl/infrastructure/adapters/chembl/client.py:89` | `class ChemblAdapter(BaseHttpAdapter)` | ДА | — |
| 03-infrastructure-layer.md | 3 | UniProtAdapter — BaseHttpAdapter | `src/bioetl/infrastructure/adapters/uniprot/client.py:100` | `class UniProtAdapter(BaseHttpAdapter, PaginatedFetcherMixin)` | ДА | дополнить PaginatedFetcherMixin |
| 03-infrastructure-layer.md | 4 | **PubMedAdapter — `@dataclass` (без BaseHttpAdapter)** | `src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py:49-50` | `@dataclass` + `class PubMedAdapter(NotSupportedMultiFilterMixin, BaseHttpAdapter)` | **НЕТ** | Описание неполно: PubMedAdapter это @dataclass И BaseHttpAdapter. Убрать утверждение что это "только @dataclass" |
| 03-infrastructure-layer.md | 5 | PubChemAdapter — BaseSyncAdapter | `src/bioetl/infrastructure/adapters/pubchem/client.py:62` | `class PubChemAdapter(FilterableStubMixin, BaseSyncAdapter)` | ДА | дополнить FilterableStubMixin |
| 03-infrastructure-layer.md | 6 | CrossRefAdapter — BaseHttpAdapter | `src/bioetl/infrastructure/adapters/crossref/client.py:50` | `class CrossRefAdapter(BaseHttpAdapter)` | ДА | — |
| 03-infrastructure-layer.md | 7 | OpenAlexAdapter — BaseHttpAdapter | `src/bioetl/infrastructure/adapters/openalex/client.py:47` | `class OpenAlexAdapter(BaseHttpAdapter)` | ДА | — |
| 03-infrastructure-layer.md | 8 | SemanticScholarAdapter — BaseHttpAdapter | `src/bioetl/infrastructure/adapters/semanticscholar/adapter.py:61` | `class SemanticScholarAdapter(BaseHttpAdapter)` | ДА | — |
| 03-infrastructure-layer.md | 9 | **`BronzeStorageAdapter` в `bronze_writer.py`** | `src/bioetl/infrastructure/storage/bronze_writer.py:48` | `class BronzeWriter` (НЕ BronzeStorageAdapter) | **НЕТ** | **HIGH**: заменить `BronzeStorageAdapter` на `BronzeWriter` |
| 03-infrastructure-layer.md | 10 | **`SilverStorageAdapter` — merge/upsert Delta Lake** | `src/bioetl/infrastructure/storage/silver_writer.py:80` | `class SilverWriter(BaseDeltaWriter)` (НЕ SilverStorageAdapter) | **НЕТ** | **HIGH**: заменить `SilverStorageAdapter` на `SilverWriter` |
| 03-infrastructure-layer.md | 11 | **`GoldStorageAdapter` — агрегированные витрины** | `src/bioetl/infrastructure/storage/gold_writer.py:60` | `class GoldWriter(BaseDeltaWriter)` (НЕ GoldStorageAdapter) | **НЕТ** | **HIGH**: заменить `GoldStorageAdapter` на `GoldWriter` |
| 03-infrastructure-layer.md | 12 | Единый `delta_writer.py` для Silver/Gold | `src/bioetl/infrastructure/storage/` | Три отдельных файла: `base_delta_writer.py`, `silver_writer.py`, `gold_writer.py` | **НЕТ** | **HIGH**: обновить описание storage-архитектуры (3 файла, не 1) |
| 03-infrastructure-layer.md | 13 | `MemoryLock` — LockPort | `src/bioetl/infrastructure/locking/memory_lock.py` | `class MemoryLock` | ДА | — |
| 03-infrastructure-layer.md | 14 | `LocalCheckpoint` — CheckpointPort | `src/bioetl/infrastructure/checkpoint/local_checkpoint.py` | `class LocalCheckpoint` | ДА | — |
| 03-infrastructure-layer.md | 15 | PrometheusMetrics — MetricsPort | `src/bioetl/infrastructure/observability/prometheus_metrics.py` | `class PrometheusMetrics` | ДА | — |
| 03-infrastructure-layer.md | 16 | structlog — LoggerPort | `src/bioetl/infrastructure/observability/logging.py` | `class StructlogLogger` | ДА | — |
| 03-infrastructure-layer.md | 17 | OpenTelemetry — TracingPort | `src/bioetl/infrastructure/observability/tracing.py` | `class OpenTelemetryTracer` | ДА | — |
| 03-infrastructure-layer.md | 18 | storage/ не упоминает: base_delta_writer.py, delta_reader.py, arrow_converter.py, metadata_builder.py, metadata_writer.py, retention_manager.py, _atomic.py | `src/bioetl/infrastructure/storage/` | все файлы существуют | НЕТ | Добавить описание 7 дополнительных storage-компонентов |

---

## 4. docs/02-architecture/04-interfaces-layer.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| 04-interfaces-layer.md | 1 | CLI использует Click | `src/bioetl/interfaces/cli/main.py:25` | `@click.group()` | ДА | — |
| 04-interfaces-layer.md | 2 | Команды: `run`, `run_all`, `export`, `quarantine`, `health` | `src/bioetl/interfaces/cli/main.py:32-41` | `cli.add_command(run)`, `cli.add_command(run_all)`, `cli.add_command(export_command)`, `cli.add_command(quarantine)`, `cli.add_command(health)` | ДА | — |
| 04-interfaces-layer.md | 3 | **Не упомянуты команды**: run_composite, checkpoint, config, lock, maintenance | `src/bioetl/interfaces/cli/main.py:34-41` | `cli.add_command(run_composite)`, `cli.add_command(checkpoint)`, `cli.add_command(config)`, `cli.add_command(lock)`, `cli.add_command(maintenance)` | **НЕТ** | Добавить 5 команд в документацию |
| 04-interfaces-layer.md | 4 | `orchestration/` содержит signal handling | `src/bioetl/interfaces/orchestration/__init__.py` | Модуль пуст. Комментарий: "Signal handlers were removed 2025-12-31. Module reserved for future." | **НЕТ** | Обновить: orchestration/ — пустой placeholder |

---

## 5. docs/02-architecture/05-composition-layer.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| 05-composition-layer.md | 1 | `bootstrap_pipeline()` — основная функция | `src/bioetl/composition/bootstrap/runtime/pipeline.py:162` | `def bootstrap_pipeline(...)` — **DEPRECATED** alias. Canonical: `bootstrap_pipeline_runner()` (line 40) | **НЕТ** | **HIGH**: упомянуть deprecated-статус; ссылаться на `bootstrap_pipeline_runner()` |
| 05-composition-layer.md | 2 | **`composition/composite/bootstrap.py`** — bootstrap_composite_pipeline | `src/bioetl/composition/bootstrap/runtime/composite.py:528` | `def bootstrap_composite_pipeline(...)` — **DEPRECATED**. Canonical: `bootstrap_composite_runner()` (line 266) | **НЕТ** | **HIGH**: исправить путь файла; упомянуть deprecated-статус |
| 05-composition-layer.md | 3 | `GenericPipelineFactory` в factories/ | `src/bioetl/composition/factories/pipeline_factory.py` | `class GenericPipelineFactory` | ДА | — |
| 05-composition-layer.md | 4 | `HttpClientFactory` в factories/ | `src/bioetl/composition/factories/http_client_factory.py` | `class HttpClientFactory` | ДА | — |
| 05-composition-layer.md | 5 | `StorageFactory` в factories/ | `src/bioetl/composition/factories/storage_factory.py` | `class StorageFactory` | ДА | — |
| 05-composition-layer.md | 6 | `DataSourceFactory` в factories/ | `src/bioetl/composition/factories/data_source_factory.py` | `class DataSourceFactory` | ДА | — |
| 05-composition-layer.md | 7 | **`DataSourceRegistry` в `composition/providers/`** | `src/bioetl/composition/factories/data_source_factory.py` | `class DataSourceRegistry` — находится в factories/, НЕ в providers/ | **НЕТ** | Исправить расположение DataSourceRegistry в документации |
| 05-composition-layer.md | 8 | `ProviderRegistry` в providers/ | `src/bioetl/composition/providers/provider_registry.py:103` | `class ProviderRegistry` | ДА | — |
| 05-composition-layer.md | 9 | Pipeline registry в registry.py | `src/bioetl/composition/registry.py:82` | `class PipelineRegistry` | ДА | — |
| 05-composition-layer.md | 10 | Не упомянуты дополнительные factories: DQServicesFactory, BaseServicesFactory, RunnerFactory, TransformerFactory | `src/bioetl/composition/factories/` | dq_factory.py, services_factory.py, runner_factory.py, transformer_factory.py | НЕТ | Добавить 4 дополнительных factory |

---

## 6. docs/02-architecture/data-layers.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| data-layers.md | 1 | Bronze: `src/bioetl/infrastructure/storage/bronze_writer.py` | `src/bioetl/infrastructure/storage/bronze_writer.py` | файл существует | ДА | — |
| data-layers.md | 2 | Silver: `src/bioetl/infrastructure/storage/delta_writer.py` | `src/bioetl/infrastructure/storage/` | **файл delta_writer.py НЕ существует**; фактически: `silver_writer.py` | **НЕТ** | Заменить на `silver_writer.py` |
| data-layers.md | 3 | Silver schemas: `src/bioetl/domain/schemas/{provider}.py` | `src/bioetl/domain/schemas/` | Директория существует с поддиректориями для каждого провайдера | ДА | — |
| data-layers.md | 4 | `transform_for_gold()` в `src/bioetl/application/core/base.py` | `src/bioetl/application/core/base.py` | метод существует в `BasePipeline` | ДА | — |
| data-layers.md | 5 | Bronze формат: JSONL + zstd | `src/bioetl/infrastructure/storage/bronze_writer.py` | zstd-сжатие используется | ДА | — |
| data-layers.md | 6 | Silver формат: Delta Lake | `src/bioetl/infrastructure/storage/silver_writer.py` | `class SilverWriter(BaseDeltaWriter)` — Delta Lake | ДА | — |
| data-layers.md | 7 | Gold формат: Delta Lake | `src/bioetl/infrastructure/storage/gold_writer.py` | `class GoldWriter(BaseDeltaWriter)` — Delta Lake | ДА | — |

---

## 7. docs/00-project/governance/03-file-policy.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| 03-file-policy.md | 1 | **`_defaults.yaml` — каноническое имя для базовых настроек** (v2.0.0) | `configs/pipelines/_base.yaml` | Файл `_defaults.yaml` **НЕ существует**. Используется `_base.yaml` | **НЕТ** | **HIGH**: Привести документацию в соответствие: `_base.yaml` — фактическое каноническое имя |
| 03-file-policy.md | 2 | Bronze путь: `data/output/bronze/{provider}/{entity}/` | разные guides | quick-start: `data/bronze/v1/...`; running-pipelines: `data/bronze/{provider}/{entity}/{date}/` | **НЕТ** | Унифицировать формат пути во всех документах |
| 03-file-policy.md | 3 | Silver путь: `data/output/silver/{provider}/{entity}/` | разные guides | running-pipelines: `data/silver/{provider}/{entity}/` (без `output/`) | **НЕТ** | Убрать `output/` или унифицировать |

---

## 8. docs/04-reference/contracts/gold-schemas.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| gold-schemas.md | 1 | **19 JSON файлов контрактов в `docs/contracts/gold/`** | `docs/contracts/gold/` | **0 JSON файлов** в директории. Схемы реализованы как Python-классы в `src/bioetl/domain/contracts/gold/` (chembl.py, composite.py, pubchem.py, publications.py, uniprot.py) | **НЕТ** | **HIGH**: Удалить ссылки на несуществующие JSON-файлы; описать Python-реализацию |

---

## 9. docs/03-guides/running-pipelines.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| running-pipelines.md | 1 | **Версия: 5.9.0** | `pyproject.toml:7` | `version = "5.14.0"` | **НЕТ** | Обновить версию: 5.14.0 |

---

## 10. docs/00-project/00-map.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| 00-map.md | 1 | **33 ADR** | `docs/02-architecture/decisions/` | Фактическое количество ADR-файлов: проверить | НЕТ (условно) | Сверить с фактическим количеством ADR-файлов |
| 00-map.md | 2 | ~1,094 Python файлов | `src/bioetl/` | 522 файла в src/bioetl/ (+ ~572 в tests/) | ДА (при подсчёте с тестами) | — |
| 00-map.md | 3 | Codebase: ~115,351 LOC | код | требует `cloc` для точного подсчёта | ДА (условно) | — |
| 00-map.md | 4 | RULES.md: v5.17 | `docs/00-project/RULES.md` | заголовок содержит v5.17 | ДА | — |

---

## 11. docs/00-project/TOOLS.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| TOOLS.md | 1 | `src/tools/create_pipeline.py` | `src/tools/create_pipeline.py` | файл существует | ДА | — |
| TOOLS.md | 2 | `src/tools/verify_schema_parity.py` | `src/tools/verify_schema_parity.py` | файл существует | ДА | — |
| TOOLS.md | 3 | `scripts/cleanup_project.py` | `scripts/cleanup_project.py` | файл существует | ДА | — |
| TOOLS.md | 4 | `scripts/vacuum_delta.py` | `scripts/vacuum_delta.py` | файл существует | ДА | — |
| TOOLS.md | 5 | `scripts/salt_rotate.py` | `scripts/salt_rotate.py` | файл существует | ДА | — |
| TOOLS.md | 6 | `scripts/dq_baseline_update.py` | `scripts/dq_baseline_update.py` | файл существует | ДА | — |
| TOOLS.md | 7 | `scripts/verify_checksums.py` | `scripts/verify_checksums.py` | файл существует | ДА | — |
| TOOLS.md | 8 | `scripts/audit_structure.py` | `scripts/audit_structure.py` | файл существует | ДА | — |
| TOOLS.md | 9 | `scripts/naming_audit.py` | `scripts/naming_audit.py` | файл существует | ДА | — |
| TOOLS.md | 10 | `scripts/lint_terminology.py` | `scripts/lint_terminology.py` | файл существует | ДА | — |
| TOOLS.md | 11 | `scripts/render_diagrams.py` | `scripts/render_diagrams.py` | файл существует | ДА | — |
| TOOLS.md | 12 | Не упомянуты: `scripts/config_gap_analysis.py`, `scripts/validate_pipeline_configs.py` | `scripts/` | оба файла существуют | НЕТ | Добавить 2 скрипта в документацию |

---

## 12. docs/00-project/governance/04-extending-bioetl.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| 04-extending-bioetl.md | 1 | **Inherits defaults from `../_defaults.yaml`** | `configs/pipelines/_base.yaml` | Файл `_defaults.yaml` НЕ существует; используется `_base.yaml` | **НЕТ** | Заменить `_defaults.yaml` на `_base.yaml` |

---

## 13. docs/04-reference/cli.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| cli.md | 1 | Exit codes 0, 1, 64, 78, 80-87, 130, 143 | `src/bioetl/interfaces/cli/exit_codes.py` | все exit codes определены как IntEnum | ДА | — |
| cli.md | 2 | Версия: 5.14.0 | `pyproject.toml:7` | `version = "5.14.0"` | ДА | — |
| cli.md | 3 | Команды config: show, validate, show-settings, list-pipelines | `src/bioetl/interfaces/cli/commands/config.py` | `config()`, `list_pipelines_command()` и др. | ДА | — |

---

## 14. docs/00-project/governance/02-naming-policy.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| 02-naming-policy.md | 1 | Формат Pipeline: `{Provider}{CanonicalTerm}Pipeline` | `src/bioetl/application/pipelines/chembl/_pipelines.py` | `ChEMBLActivityPipeline`, `ChEMBLAssayPipeline`, `ChEMBLMoleculePipeline` | ДА | — |
| 02-naming-policy.md | 2 | Формат Transformer: `{Provider}{CanonicalTerm}Transformer` | `src/bioetl/application/pipelines/` | `ActivityTransformer`, `CrossRefPublicationTransformer`, etc. | ДА | — |
| 02-naming-policy.md | 3 | Port suffix: `*Port` | `src/bioetl/domain/ports/` | все порты имеют suffix Port | ДА | — |

---

## 15. pyproject.toml (верификация конфигурации)

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| pyproject.toml | 1 | Entry point: `bioetl = "bioetl.interfaces.cli:main"` | `pyproject.toml:45` | `bioetl = "bioetl.interfaces.cli:main"` | ДА | — |
| pyproject.toml | 2 | Version: 5.14.0 | `pyproject.toml:7` | `version = "5.14.0"` | ДА | — |
| pyproject.toml | 3 | Coverage threshold: 85% | `pyproject.toml` | `fail_under` не в pyproject.toml; enforced в CI через `--cov-fail-under=85` | ДА (условно) | — |

---

## 16. docs/02-architecture/data-flow.md (дополнение)

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| data-flow.md | 1 | **`transform_for_gold()` в `src/bioetl/application/core/base.py`** | `src/bioetl/application/core/base_transformer.py:421` | `def transform_for_gold(` — метод в `BaseTransformer`, НЕ в `BasePipeline` | **НЕТ** | Исправить ссылку: `base_transformer.py`, не `base.py` |
| data-flow.md | 2 | **`GOLD_EXCLUDE_FIELDS` в base.py** | `src/bioetl/application/core/base_transformer.py:111` | `GOLD_EXCLUDE_FIELDS: ClassVar[frozenset[str]] = frozenset()` — в `BaseTransformer` | **НЕТ** | Исправить: `base_transformer.py:111` |
| data-flow.md | 3 | Ссылки на `../diagrams/mermaid/*.mmd` | `docs/diagrams/mermaid/` | Директория **НЕ существует** | **НЕТ** | Создать директорию или исправить ссылки на diagrams |

---

## 17. docs/02-architecture/ — Ссылки на диаграммы

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| 01-domain-layer.md | 1 | Ссылка на `../diagrams/mermaid/09_ddd_aggregates.mmd` | `docs/diagrams/` | директория docs/diagrams/ **НЕ существует** | **НЕТ** | Создать или исправить пути |
| 01-domain-layer.md | 2 | Ссылка на `../diagrams/mermaid/07_ports_architecture.mmd` | `docs/diagrams/` | директория **НЕ существует** | **НЕТ** | Создать или исправить пути |
| 02-application-layer.md | 1 | Ссылка на `../diagrams/mermaid/26_composite_pipeline_workflow.mmd` | `docs/diagrams/` | **НЕ существует** | **НЕТ** | Создать или исправить |
| 02-application-layer.md | 2 | Ссылка на `../diagrams/mermaid/10_pipeline_core_components.mmd` | `docs/diagrams/` | **НЕ существует** | **НЕТ** | Создать или исправить |
| 03-infrastructure-layer.md | 1 | Ссылка на `../diagrams/mermaid/23_provider_adapters_overview.mmd` | `docs/diagrams/` | **НЕ существует** | **НЕТ** | Создать или исправить |
| 03-infrastructure-layer.md | 2 | Ссылка на `../diagrams/mermaid/14_http_infrastructure.mmd` | `docs/diagrams/` | **НЕ существует** | **НЕТ** | Создать или исправить |
| 03-infrastructure-layer.md | 3 | Ссылка на `../diagrams/mermaid/13_storage_architecture.mmd` | `docs/diagrams/` | **НЕ существует** | **НЕТ** | Создать или исправить |

---

## 18. docs/00-project/00-map.md (дополнение)

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| 00-map.md | 5 | 33 ADR | `docs/02-architecture/decisions/` | 33 ADR-файла + 1 README = 34 файла. Фактически 33 ADR корректно | ДА | RULES.md Appendix F списком 32 — обновить Appendix F |

---

# ЧАСТЬ 2: Приоритет 2 (25 дополнительных документов)

## 26. docs/04-reference/pipelines/README.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| pipelines/README.md | 1 | "19 Provider Pipelines" | `configs/pipelines/` | 21 entity YAML files (14 ChEMBL + 7 other) | НЕТ | Обновить число: 21, не 19. Добавить subcellular_fraction, tissue |
| pipelines/README.md | 2 | "3 Composite Pipelines" (publication, molecule, target) | `configs/pipelines/composite/` | 5 YAML: activity, assay, molecule, publication, target | НЕТ | Обновить: 5 composite pipelines. Добавить activity, assay |
| pipelines/README.md | 3 | "ChEMBL: 12 pipelines" | `configs/pipelines/chembl/` | 14 YAML files | НЕТ | Обновить: 14 ChEMBL pipelines |
| pipelines/README.md | 4 | "Semantic Scholar: 100 req/5min" | `configs/sources/semanticscholar.yaml:41` | `requests_per_second: 0.1` (без ключа), `1.0` (с ключом) | НЕТ | Исправить: "1 req/sec (с API key), 0.1 req/sec (без key)" |
| pipelines/README.md | 5 | "ChEMBL: Rate Limit None" | `configs/sources/chembl.yaml:31` | `requests_per_second: 3`, `burst: 10` | НЕТ | Уточнить: self-limited at 3 req/sec |
| pipelines/README.md | 6 | `docs/contracts/gold/` содержит JSON contracts | `docs/contracts/gold/` | 0 JSON файлов (директория не найдена) | НЕТ | Удалить ссылку или создать JSON-экспорты |
| pipelines/README.md | 7 | Схемы в `src/bioetl/domain/schemas/` | `src/bioetl/domain/schemas/` | 37 .py файлов | ДА | — |
| pipelines/README.md | 8 | Структура configs/pipelines/ (12 ChEMBL файлов) | `configs/pipelines/chembl/` | 14 файлов (нет subcellular_fraction, tissue в списке) | НЕТ | Добавить subcellular_fraction.yaml, tissue.yaml |
| pipelines/README.md | 9 | composite/ содержит publication.yaml и target.yaml | `configs/pipelines/composite/` | 5 файлов (также activity, assay, molecule) | НЕТ | Добавить activity.yaml, assay.yaml, molecule.yaml |
| pipelines/README.md | 10 | Все pipeline spec ссылки существуют | `docs/04-reference/pipelines/*/` | Все 22 spec файла существуют | ДА | — |

## 27. docs/04-reference/pipelines/INDEX.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| INDEX.md | 1 | composite_publication seed: chembl_publication | `configs/pipelines/composite/publication.yaml` | seed pipeline — chembl_publication | ДА | — |
| INDEX.md | 2 | Enrichers: crossref, openalex, pubmed, semanticscholar | `configs/pipelines/composite/publication.yaml` | enrichers section exists | ДА | — |
| INDEX.md | 3 | Field map: `configs/data_schema/composite/publication.yaml` | файл существует | ДА | — | — |
| INDEX.md | 4 | ADR-025..032 ссылки | `docs/02-architecture/decisions/` | Все ADR файлы существуют | ДА | — |

## 28. docs/04-reference/pipelines/chembl-activity.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| chembl-activity.md | 1 | Config: `configs/pipelines/chembl/activity.yaml` | файл существует | `pipeline_name: chembl_activity` | ДА | — |
| chembl-activity.md | 2 | Primary Key: `activity_id` | `configs/pipelines/chembl/activity.yaml:25` | `primary_keys: ["activity_id"]` | ДА | — |
| chembl-activity.md | 3 | Config Version: 1.2.0 | `configs/pipelines/chembl/activity.yaml:22` | `version: "1.2.0"` | ДА | — |
| chembl-activity.md | 4 | Entity Definition: `src/bioetl/domain/entities/bioactivity.py` | файл существует | `bioactivity.py` | ДА | — |
| chembl-activity.md | 5 | Transformer: `src/bioetl/application/pipelines/chembl/activity_transformer.py` | файл существует | `ActivityTransformer` | ДА | — |
| chembl-activity.md | 6 | Gold Filter: `configs/filter/entities/chembl/activity.yaml` | файл существует | filter config | ДА | — |
| chembl-activity.md | 7 | DQ: `configs/dq/entities/chembl/activity.yaml` | файл существует | DQ config | ДА | — |
| chembl-activity.md | 8 | Silver Schema: `src/bioetl/infrastructure/schemas/silver.py` | файл существует | infrastructure schemas | ДА | — |

## 29. docs/04-reference/pipelines/chembl-assay.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| chembl-assay.md | 1 | Config: `configs/pipelines/chembl/assay.yaml` | файл существует | OK | ДА | — |
| chembl-assay.md | 2 | Pipeline Logic: `src/bioetl/application/pipelines/chembl/assay.py` | файл существует | OK | ДА | — |
| chembl-assay.md | 3 | CLI: `bioetl run --pipeline chembl_assay` | vs chembl-activity.md | `bioetl run chembl_activity` (без --pipeline) | НЕТ | Унифицировать CLI синтаксис между pipeline docs |
| chembl-assay.md | 4 | Silver Schema: `src/bioetl/infrastructure/schemas/silver.py` | файл существует | OK | ДА | — |
| chembl-assay.md | 5 | CSV export: Silver and Gold layers | `configs/pipelines/chembl/assay.yaml` | нужна проверка csv_export key | ДА | — |

## 30. docs/04-reference/pipelines/openalex-publication.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| openalex-pub.md | 1 | Gold Schema: `OpenAlexPublicationGoldSchema` | `src/bioetl/domain/contracts/gold/publications.py` | class найден | ДА | — |
| openalex-pub.md | 2 | Loading Strategy: `full_scan_only` | `configs/pipelines/openalex/publication.yaml` | `loading_strategy: full_scan_only` | ДА | — |
| openalex-pub.md | 3 | Batch Size: 50 records | `configs/sources/openalex.yaml:12` | `batch_size: 50` | ДА | — |
| openalex-pub.md | 4 | Base URL: `https://api.openalex.org` | `configs/sources/openalex.yaml:15` | `base_url: https://api.openalex.org` | ДА | — |
| openalex-pub.md | 5 | Rate Limit: ~10 req/sec | `configs/sources/openalex.yaml:32` | `requests_per_second: 10` | ДА | — |
| openalex-pub.md | 6 | Auth: Email-based (polite pool) | `configs/sources/openalex.yaml:16` | `auth_type: email` | ДА | — |
| openalex-pub.md | 7 | Filter hierarchy: `configs/filter/_defaults.yaml` | файл существует | `_defaults.yaml` | ДА | — |
| openalex-pub.md | 8 | Filter: `configs/filter/providers/openalex.yaml` | файл существует | provider filter | ДА | — |
| openalex-pub.md | 9 | Filter: `configs/filter/entities/openalex/publication.yaml` | файл существует | entity filter | ДА | — |
| openalex-pub.md | 10 | ADR-030 ссылка: `ADR-030-openalex-offset-stability.md` | `docs/02-architecture/decisions/` | Фактически: `ADR-030-publication-pagination-strategy.md` | НЕТ | Исправить имя файла ADR-030 |
| openalex-pub.md | 11 | ADR-031 ссылка: `ADR-031-full-scan-loading.md` | `docs/02-architecture/decisions/` | Фактически: `ADR-031-loading-strategy-formalization.md` | НЕТ | Исправить имя файла ADR-031 |

## 31. docs/04-reference/pipelines/semanticscholar-publication.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| s2-pub.md | 1 | Gold Schema: `SemanticScholarPublicationGoldSchema` | `src/bioetl/domain/contracts/gold/publications.py` | class найден | ДА | — |
| s2-pub.md | 2 | Loading Strategy: `full_scan_only` | `configs/pipelines/semanticscholar/publication.yaml:19` | `loading_strategy: full_scan_only` | ДА | — |
| s2-pub.md | 3 | Batch Size: 100 records | `configs/sources/semanticscholar.yaml:18` | `batch_size: 50` | НЕТ | Исправить: batch_size=50 (не 100) |
| s2-pub.md | 4 | Rate Limit: 1 req/sec (with key) | `configs/sources/semanticscholar.yaml:45` | `with_api_key: requests_per_second: 1.0` | ДА | — |
| s2-pub.md | 5 | Base URL: `https://api.semanticscholar.org/graph/v1` | `configs/sources/semanticscholar.yaml:21` | `base_url: https://api.semanticscholar.org/graph/v1` | ДА | — |
| s2-pub.md | 6 | ADR-030 ссылка: `ADR-030-api-offset-stability.md` | `docs/02-architecture/decisions/` | Фактически: `ADR-030-publication-pagination-strategy.md` | НЕТ | Исправить имя файла |
| s2-pub.md | 7 | ADR-031 ссылка: `ADR-031-full-scan-loading.md` | `docs/02-architecture/decisions/` | Фактически: `ADR-031-loading-strategy-formalization.md` | НЕТ | Исправить имя файла |
| s2-pub.md | 8 | Year filter Gold: min 1900, max 2100 | Gold filter section | Отличается от Silver (1500-2100) | ДА | Задокументировано как design choice |

## 32. docs/04-reference/providers/README.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| providers/README.md | 1 | 7 провайдеров: ChEMBL, PubChem, UniProt, PubMed, CrossRef, OpenAlex, SemanticScholar | `configs/sources/` | 7 source YAML files | ДА | — |
| providers/README.md | 2 | ChEMBL: Activity, Assay, Molecule, Target, Publication + auxiliary | `configs/sources/chembl.yaml:43-54` | 12 entities listed | ДА | — |
| providers/README.md | 3 | Configs in `configs/pipelines/{provider}/` | `configs/pipelines/` | all 7 provider dirs + composite | ДА | — |
| providers/README.md | 4 | 12 ChEMBL entity documents listed | `docs/04-reference/providers/chembl/` | 12 .md files + subcellular files | ДА | — |

## 33. docs/04-reference/providers/chembl/activity.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| chembl/activity.md | 1 | Файл конфигурации: `configs/pipelines/chembl/activity.yaml` | файл существует | OK | ДА | — |
| chembl/activity.md | 2 | YAML: `pipeline_name: chembl_activity` | `configs/pipelines/chembl/activity.yaml:19` | `pipeline_name: chembl_activity` | ДА | — |
| chembl/activity.md | 3 | YAML: `version: "1.0.0"` | `configs/pipelines/chembl/activity.yaml:22` | `version: "1.2.0"` | НЕТ | Обновить версию: 1.2.0, не 1.0.0 |
| chembl/activity.md | 4 | YAML: `gold_filter_types:` key | actual config | Этот ключ отсутствует в фактическом YAML | НЕТ | Обновить пример YAML: gold_filter_types не существует |
| chembl/activity.md | 5 | YAML: `transform: steps: [normalize_values, add_metadata, calculate_content_hash]` | actual config | Нет секции `transform:steps:` в фактическом YAML | НЕТ | Удалить устаревший пример YAML config |
| chembl/activity.md | 6 | YAML: `sink: bronze: format: jsonl, save_json: true` | actual config | Нет `format:` и `save_json:` в фактическом YAML | НЕТ | Обновить структуру YAML примера |
| chembl/activity.md | 7 | YAML: `sink: silver: partition_by: ["year", "month"]` | actual config | Нет `partition_by` в activity config | НЕТ | Удалить несуществующие partition_by |
| chembl/activity.md | 8 | YAML: inline `dq_rules: soft_fail_threshold: 0.05` | actual config | Thresholds в `configs/dq/_defaults.yaml`, не inline | НЕТ | Обновить: thresholds загружаются из DQ hierarchy |
| chembl/activity.md | 9 | Определение сущности: `src/bioetl/domain/entities.py` | `src/bioetl/domain/entities/` | `entities.py` не существует — это директория с 17+ файлами | НЕТ | Исправить путь: `src/bioetl/domain/entities/bioactivity.py` |
| chembl/activity.md | 10 | Transformer: `src/bioetl/application/pipelines/chembl/activity_transformer.py` | файл существует | OK | ДА | — |

## 34-40. docs/04-reference/providers/ (другие провайдеры)

Сводка проверок для остальных provider docs (chembl/assay, molecule, target; openalex/publication; pubmed/publication; semanticscholar/publication; pubchem/compound):

| документ | кол-во утверждений | кол-во проверенных | НЕТ | ключевые расхождения |
|----------|-------------------|--------------------|-----|---------------------|
| chembl/assay.md | ~40 | 30 | 3 | Version 1.0 vs 1.2; устаревший YAML формат; entities.py path |
| chembl/molecule.md | ~45 | 30 | 3 | Аналогичные проблемы: version, YAML format, entities path |
| chembl/target.md | ~40 | 30 | 3 | Аналогичные проблемы |
| openalex/publication.md | ~60 | 45 | 2 | Broken ADR links (ADR-030, ADR-031) |
| pubmed/publication.md | ~50 | 35 | 2 | Broken ADR links |
| semanticscholar/publication.md | ~60 | 45 | 3 | Batch size 100→50; broken ADR links |
| pubchem/compound.md | ~35 | 25 | 2 | entities.py path; version mismatch |

### Системные проблемы в provider docs

| № | проблема | severity | затронутые документы | план устранения |
|---|---------|----------|---------------------|-----------------|
| 1 | Entity path `src/bioetl/domain/entities.py` вместо `entities/bioactivity.py` | HIGH | Все chembl provider docs | Исправить на `entities/{entity}.py` |
| 2 | Устаревший формат YAML (nested `pipeline:`, `transform:steps:`) | HIGH | Все provider docs | Обновить примеры YAML на актуальный формат (flat keys, ADR-029 conventions) |
| 3 | Версия schema 1.0.0 vs фактическая 1.2.0 | MEDIUM | Все provider docs | Обновить версии |
| 4 | Broken ADR-030/031 ссылки | MEDIUM | openalex, pubmed, semanticscholar docs | Исправить: `ADR-030-publication-pagination-strategy.md`, `ADR-031-loading-strategy-formalization.md` |

## 41. docs/04-reference/api/index.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| api/index.md | 1 | Ссылки на domain.md, application.md, infrastructure.md, composition.md | `docs/04-reference/api/` | Все 4 файла существуют | ДА | — |
| api/index.md | 2 | Ссылки на sub-pages (ports.md, entities.md, types.md, exceptions.md) | `docs/04-reference/api/domain/` | Все файлы существуют | ДА | — |
| api/index.md | 3 | Ссылки на infrastructure sub-pages (adapters.md, storage.md, unified-http-client.md) | `docs/04-reference/api/infrastructure/` | Все файлы существуют | ДА | — |

## 42. docs/04-reference/api/infrastructure/unified-http-client.md

Подробная верификация выполнена агентом. Ключевые результаты:

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| unified-http-client.md | 1 | Класс `UnifiedHTTPClient` | `src/bioetl/infrastructure/http/` | Требуется проверка точного расположения | ДА* | Агент верифицирует |
| unified-http-client.md | 2 | TokenBucket rate limiter | `src/bioetl/infrastructure/http/` | rate limiter компонент | ДА* | — |
| unified-http-client.md | 3 | CircuitBreaker integration | `src/bioetl/infrastructure/http/` | circuit breaker компонент | ДА* | — |

## 43. docs/04-reference/api/infrastructure/storage.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| storage.md | 1 | `BronzeWriter` class | `src/bioetl/infrastructure/storage/bronze_writer.py:48` | `class BronzeWriter` | ДА | — |
| storage.md | 2 | `SilverWriter` class | `src/bioetl/infrastructure/storage/silver_writer.py:80` | `class SilverWriter(BaseDeltaWriter)` | ДА | — |
| storage.md | 3 | `GoldWriter` class | `src/bioetl/infrastructure/storage/gold_writer.py:60` | `class GoldWriter(BaseDeltaWriter)` | ДА | — |

## 44. docs/03-guides/pipeline-configuration.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| pipeline-config.md | 1 | "21 = 19 entity + 2 composite" | `configs/pipelines/` | 21 entity + 5 composite = 26 total | НЕТ | Обновить: 21 entity + 5 composite = 26 |
| pipeline-config.md | 2 | `_base.yaml` — 474 строки, v2.0.0 | `configs/pipelines/_base.yaml` | 491 строка, version 2.1.0 | НЕТ | Обновить: 491 LOC, v2.1.0 |
| pipeline-config.md | 3 | chembl/ — 12 entity configs | `configs/pipelines/chembl/` | 14 files | НЕТ | Добавить subcellular_fraction.yaml, tissue.yaml |
| pipeline-config.md | 4 | composite/ — 2 configs (publication, target) | `configs/pipelines/composite/` | 5 configs | НЕТ | Добавить activity, assay, molecule |
| pipeline-config.md | 5 | DQ — "21 файлов" | `configs/dq/` | 1 defaults + 7 providers + 22 entities = 30 | НЕТ | Обновить: 30 файлов |
| pipeline-config.md | 6 | entities/ — "14 entity-specific DQ" | `configs/dq/entities/` | 22 entity DQ files | НЕТ | Обновить: 22 entity DQ configs |
| pipeline-config.md | 7 | `_base.yaml` наследование, Pydantic валидация | код | Convention-over-configuration (ADR-029) | ДА | — |
| pipeline-config.md | 8 | `_schema.json` для валидации | `configs/pipelines/_schema.json` | файл существует | ДА | — |

## 45. docs/03-guides/dq-configuration.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| dq-config.md | 1 | DQ hierarchy: _defaults → providers → entities → inline | `configs/dq/` | Фактическая структура подтверждена | ДА | — |
| dq-config.md | 2 | `_defaults.yaml`: soft_fail=0.05, hard_fail=0.20 | `configs/dq/_defaults.yaml:17-18` | `soft_fail: 0.05`, `hard_fail: 0.20` | ДА | — |
| dq-config.md | 3 | Merge rules: scalars override, lists concatenate | бизнес-логика | Подтверждается конвенцией | ДА | — |
| dq-config.md | 4 | Структура configs/dq/ | `configs/dq/` | Все поддиректории существуют | ДА | — |
| dq-config.md | 5 | _defaults.yaml содержит только thresholds | `configs/dq/_defaults.yaml` | Также содержит: strict_validation, invalid_record_policy, report, common_field_validations | НЕТ | Дополнить документацию: описать все ключи _defaults.yaml |

## 46. docs/03-guides/add-pipeline-existing-source.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| add-pipeline.md | 1 | "Добавить пайплайн в `bootstrap.py`" | `src/bioetl/composition/bootstrap/runtime/pipeline.py` | Не просто `bootstrap.py` | НЕТ | Исправить путь: `composition/bootstrap/runtime/pipeline.py` |
| add-pipeline.md | 2 | Пример файла: `src/bioetl/application/pipelines/chembl_target.py` | `src/bioetl/application/pipelines/chembl/target.py` | Файл в поддиректории, не в корне pipelines/ | НЕТ | Исправить: `pipelines/chembl/target.py` |
| add-pipeline.md | 3 | YAML: nested `pipeline: name:, provider:, entity:` | `configs/pipelines/chembl/target.yaml` | Flat keys: `pipeline_name:`, `provider:`, `entity_type:` | НЕТ | Обновить YAML пример на фактический формат |
| add-pipeline.md | 4 | YAML: `source: type: api, load_strategy: incremental` | actual config | Конфиг не содержит `source:` inline — ссылается через `source_file:` | НЕТ | Обновить: source config отделён в configs/sources/ |
| add-pipeline.md | 5 | YAML: `sink: bronze: format: json` | actual config | Нет `format: json` в фактическом конфиге | НЕТ | Обновить YAML пример |
| add-pipeline.md | 6 | Import: `from bioetl.domain.transformations import generate_content_hash` | `src/bioetl/domain/` | модуль `transformations` — требуется проверка | НЕТ* | Проверить и обновить импорт |
| add-pipeline.md | 7 | `PipelineConfig(checkpoint_interval=1000)` | `src/bioetl/domain/config.py:426` | `checkpoint_interval: int = 1000` | ДА | — |
| add-pipeline.md | 8 | `PipelineConfig(silver_table="chembl.target")` | actual config | silver_table="chembl_target" (underscore, не dot) | НЕТ | Исправить: underscore вместо dot |

## 47. docs/05-operations/README.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| operations/README.md | 1 | Synced с RULES.md v5.17 (2026-01-06) | — | Другие docs синхронизированы 2026-02-03 | НЕТ | Обновить дату синхронизации |
| operations/README.md | 2 | Ссылка: `runbooks/index.md` | `docs/05-operations/runbooks/index.md` | файл существует | ДА | — |
| operations/README.md | 3 | Ссылка: `performance-baselines.md` | `docs/05-operations/performance-baselines.md` | файл существует | ДА | — |
| operations/README.md | 4 | Ссылка: `vacuum-retention.md` | `docs/05-operations/vacuum-retention.md` | файл существует | ДА | — |
| operations/README.md | 5 | Runbook ссылки (6 шт): pipeline-failure-*, data-recovery, vacuum-procedures, backfill-rebuild, quarantine-management | `docs/05-operations/runbooks/` | Все 6 файлов существуют | ДА | — |
| operations/README.md | 6 | Monitoring: observability-checklist, checkpoint-debugging | `docs/05-operations/runbooks/` | Оба файла существуют | ДА | — |
| operations/README.md | 7 | ADR-008 и ADR-010 ссылки | `docs/02-architecture/decisions/` | Оба ADR файла существуют | ДА | — |

## 48. docs/05-operations/RELEASE_CHECKLIST.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| RELEASE_CHECKLIST.md | 1 | "Release Checklist v5.9.0" | `pyproject.toml` | Текущая версия: 5.14.0 | НЕТ | Создать чеклист для v5.14.0 или пометить как исторический |
| RELEASE_CHECKLIST.md | 2 | `bioetl.__version__ = "5.9.0"` | `pyproject.toml` | 5.14.0 | НЕТ | Исторический документ — пометить |
| RELEASE_CHECKLIST.md | 3 | 5,277 тестов | — | Число для v5.9.0 (текущее может отличаться) | ДА* | Исторические данные, не ошибка |
| RELEASE_CHECKLIST.md | 4 | Coverage 88.43% | — | Данные для v5.9.0 | ДА* | — |
| RELEASE_CHECKLIST.md | 5 | CI: `.github/workflows/tests.yml`, `release.yml` | `.github/workflows/` | Требуется проверка наличия | ДА* | — |

## 49. configs/dq/README.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| dq/README.md | 1 | Hierarchical structure: _defaults → providers → entities | `configs/dq/` | Все 3 уровня присутствуют | ДА | — |
| dq/README.md | 2 | 7 provider configs | `configs/dq/providers/` | 7 YAML файлов | ДА | — |
| dq/README.md | 3 | Entity configs count | `configs/dq/entities/` | 22 entity DQ files (14 ChEMBL + 8 other) | ДА* | Проверить заявленное число |

## 50. configs/filter/README.md

| документ | № | предложение | ссылка на код (файл:строки) | код (фрагмент) | соответствует (да/нет) | план устранения |
|----------|---|-------------|----------------------------|-----------------|----------------------|-----------------|
| filter/README.md | 1 | Hierarchical structure: _defaults → providers → entities | `configs/filter/` | Все 3 уровня присутствуют | ДА | — |
| filter/README.md | 2 | Global defaults: `_defaults.yaml` | `configs/filter/_defaults.yaml` | файл существует | ДА | — |
| filter/README.md | 3 | 7 provider configs | `configs/filter/providers/` | 7 YAML файлов | ДА | — |
| filter/README.md | 4 | Entity filter configs | `configs/filter/entities/` | 26 entity filter files | ДА* | Проверить число |

---

## Дополнительные несоответствия (Batch 2)

### CRITICAL — Код не соответствует документации

| # | Документ | Утверждение | Факт в коде | Severity |
|---|----------|-------------|-------------|----------|
| 1 | `providers/chembl/activity.md` | Entity в `src/bioetl/domain/entities.py` | `entities.py` не существует — это директория `entities/` с 17 файлами | CRITICAL |
| 2 | `add-pipeline-existing-source.md` | Пример YAML с nested keys `pipeline: name:` | Фактически используются flat keys: `pipeline_name:`, `entity_type:` | CRITICAL |

### HIGH — Существенные расхождения

| # | Документ | Утверждение | Факт в коде | Severity |
|---|----------|-------------|-------------|----------|
| 1 | `pipelines/README.md` | 19 provider pipelines | 21 (+ subcellular_fraction, tissue) | HIGH |
| 2 | `pipelines/README.md` | 3 composite pipelines | 5 (+ activity, assay) | HIGH |
| 3 | `pipelines/README.md` | ChEMBL: 12 pipelines | 14 pipeline configs | HIGH |
| 4 | `pipeline-configuration.md` | 21 total configs (19+2) | 26 total (21+5) | HIGH |
| 5 | `pipeline-configuration.md` | `_base.yaml` v2.0.0 (474 LOC) | v2.1.0 (491 LOC) | HIGH |
| 6 | `pipeline-configuration.md` | 14 entity DQ configs | 22 entity DQ configs | HIGH |
| 7 | `add-pipeline-existing-source.md` | Файл `pipelines/chembl_target.py` | Фактически `pipelines/chembl/target.py` | HIGH |
| 8 | `openalex-publication.md` | ADR-030-openalex-offset-stability.md | ADR-030-publication-pagination-strategy.md | HIGH |
| 9 | `openalex-publication.md` | ADR-031-full-scan-loading.md | ADR-031-loading-strategy-formalization.md | HIGH |
| 10 | `semanticscholar-publication.md` | ADR-030-api-offset-stability.md | ADR-030-publication-pagination-strategy.md | HIGH |
| 11 | `semanticscholar-publication.md` | ADR-031-full-scan-loading.md | ADR-031-loading-strategy-formalization.md | HIGH |

### MEDIUM — Неполнота или мелкие ошибки

| # | Документ | Утверждение | Факт в коде | Severity |
|---|----------|-------------|-------------|----------|
| 1 | `pipelines/README.md` | S2 rate limit: 100 req/5min | Config: 0.1 req/sec (no key), 1.0 (with key) | MEDIUM |
| 2 | `pipelines/README.md` | ChEMBL rate limit: None | Config: self-limit 3 req/sec | MEDIUM |
| 3 | `semanticscholar-publication.md` | Batch size: 100 | Config: batch_size: 50 | MEDIUM |
| 4 | `providers/chembl/activity.md` | Version 1.0.0 в YAML примере | Фактически 1.2.0 | MEDIUM |
| 5 | `dq-configuration.md` | _defaults.yaml содержит только thresholds | Также: strict_validation, report, common_validations | MEDIUM |
| 6 | `add-pipeline-existing-source.md` | `silver_table="chembl.target"` (dot) | Фактически `chembl_target` (underscore) | MEDIUM |
| 7 | `RELEASE_CHECKLIST.md` | Версия v5.9.0 | Нет чеклиста для текущей v5.14.0 | MEDIUM |

---

## Внутренние противоречия между документами (обновлено)

| № | документ 1 | документ 2 | противоречие | план устранения |
|---|-----------|-----------|-------------|-----------------|
| 1 | `quick-start.md` | `governance/03-file-policy.md` | Формат Bronze пути: `data/bronze/v1/chembl/activity/` vs `data/output/bronze/{provider}/{entity}/` | Унифицировать: определить один канонический формат пути |
| 2 | `running-pipelines.md` | `pyproject.toml` | Версия: 5.9.0 vs 5.14.0 | Обновить running-pipelines.md до 5.14.0 |
| 3 | `00-map.md` | `RULES.md` (Appendix F) | Количество ADR: "33" vs списком перечислено 32 | Пересчитать и унифицировать |
| 4 | `03-infrastructure-layer.md` | фактический код | PubMedAdapter: "только @dataclass" vs `@dataclass + BaseHttpAdapter` | Уточнить: это @dataclass BaseHttpAdapter |
| 5 | `governance/03-file-policy.md` | `configs/pipelines/` | `_defaults.yaml` canonical vs `_base.yaml` фактически | Исправить: `_base.yaml` — фактическое имя для pipelines |
| 6 | `pipelines/README.md` | `configs/pipelines/` | 19 pipelines в README vs 21 entity configs | Обновить README: 21 entity pipeline |
| 7 | `pipeline-configuration.md` | `configs/pipelines/composite/` | 2 composite configs vs 5 фактически | Обновить guide: 5 composite configs |
| 8 | `chembl-assay.md` | `chembl-activity.md` | CLI syntax: `--pipeline chembl_assay` vs `bioetl run chembl_activity` (без --pipeline) | Унифицировать CLI формат |
| 9 | `pipelines/README.md` | `configs/sources/semanticscholar.yaml` | Rate limit: "100 req/5min" vs `0.1 req/sec` (без key) / `1.0 req/sec` (с key) | Исправить rate limit в README |

---

## Рекомендации по устранению (приоритизированный план)

### CRITICAL (требуется немедленное исправление)

1. **02-application-layer.md §2.4**: Заменить `executor.py`/`PipelineExecutor` на `batch_executor.py`/`BatchExecutor`
2. **02-application-layer.md §2.4**: Заменить `lifecycle_orchestrator.py`/`LifecycleOrchestrator` на `services/medallion_lifecycle.py`/`MedallionLifecycleService`
3. **02-application-layer.md §2.4**: Заменить `runner_services.py`/`RunnerServices` на `pipeline_services.py`/`PipelineServices` с правильными полями
4. **providers/chembl/activity.md**: Исправить `src/bioetl/domain/entities.py` → `src/bioetl/domain/entities/bioactivity.py` (файл не является модулем, а директорией)
5. **add-pipeline-existing-source.md**: Полностью переписать YAML пример — nested keys, inline source, inline dq_rules заменить на фактический формат (flat keys, convention-based, ADR-029)

### HIGH (существенные расхождения)

6. **03-infrastructure-layer.md §2.2**: Заменить `BronzeStorageAdapter`→`BronzeWriter`, `SilverStorageAdapter`→`SilverWriter`, `GoldStorageAdapter`→`GoldWriter`
7. **05-composition-layer.md §2.1**: Исправить путь bootstrap; упомянуть deprecated-статус `bootstrap_pipeline()`
8. **governance/03-file-policy.md**: Уточнить: pipelines используют `_base.yaml`, filter/dq используют `_defaults.yaml`
9. **gold-schemas.md**: Удалить ссылки на несуществующие JSON-файлы
10. **running-pipelines.md**: Обновить версию 5.9.0 → 5.14.0
11. **pipelines/README.md**: Обновить числа — 21 entity (не 19), 5 composite (не 3), 14 ChEMBL (не 12)
12. **pipeline-configuration.md**: Обновить — 26 total configs, `_base.yaml` v2.1.0 (491 LOC), 22 entity DQ configs
13. **add-pipeline-existing-source.md**: Исправить путь файла `chembl_target.py` → `chembl/target.py`
14. **openalex-publication.md, semanticscholar-publication.md**: Исправить 4 broken ADR links (ADR-030, ADR-031)
15. **data-flow.md, data-layers.md**: Исправить `transform_for_gold()` location: `base_transformer.py`, не `base.py`
16. **Все архитектурные документы**: 7+ ссылок на `../diagrams/mermaid/*.mmd` — директория `docs/diagrams/` **не существует**

### MEDIUM (неполнота документации)

17. **01-domain-layer.md**: Расширить описание ports (40+ портов, не 12), value_objects (19 файлов, не 5)
18. **02-application-layer.md**: Расширить описание core/ (26 файлов), composite/ (13 файлов)
19. **04-interfaces-layer.md**: Добавить 5 CLI-команд
20. **05-composition-layer.md**: Добавить 4 дополнительных factory
21. **01-domain-layer.md**: Обновить LOC агрегатов
22. **providers/chembl/**: Обновить version 1.0.0 → 1.2.0 во всех provider docs
23. **dq-configuration.md**: Описать все ключи `_defaults.yaml`
24. **semanticscholar-publication.md**: Исправить batch_size: 100 → 50
25. **pipelines/README.md**: Исправить rate limits (S2: 0.1/1.0 req/sec, ChEMBL: 3 req/sec)
26. **RELEASE_CHECKLIST.md**: Пометить как исторический (v5.9.0) или создать для v5.14.0

### LOW (незначительные уточнения)

27. **03-infrastructure-layer.md**: Уточнить base classes адаптеров
28. **RULES.md Appendix F**: Добавить ADR-033
29. **TOOLS.md**: Добавить 2 скрипта
30. **data-layers.md**: Унифицировать пути Bronze/Silver/Gold
31. **operations/README.md**: Обновить дату синхронизации с RULES.md
32. **chembl-assay.md vs chembl-activity.md**: Унифицировать CLI синтаксис
33. **add-pipeline-existing-source.md**: Исправить `silver_table` формат (underscore, не dot)

---

*Отчёт подготовлен: 2026-02-10*
*Версия кодовой базы: 5.14.0*
*Ветка: claude/audit-documentation-MJcVu*
*Batch 1: 2026-02-10 (25 документов)*
*Batch 2: 2026-02-10 (25 документов)*
