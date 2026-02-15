# Исчерпывающий аудит документации BioETL

*Дата: 2026-02-11 | Версия проекта: 5.14.0 | RULES.md: v5.18*
*Обновлено с учётом состояния ветки `main` (commit 7e265aa)*

## Методология

Каждое верифицируемое утверждение из документов проверено путём поиска в исходном коде, подсчёта файлов и чтения реализации. После первичного аудита ветка `main` получила 11 коммитов с масштабными правками документации. Отчёт перепроверен и обновлён.

- **Да** — код полностью соответствует документации
- **Нет** — обнаружено расхождение
- **Частично** — утверждение верно, но неполно или упрощено
- **~~Исправлено~~** — было расхождение, устранено в main

---

## Содержание

1. [01-domain-layer.md](#1-01-domain-layermd)
2. [02-application-layer.md](#2-02-application-layermd)
3. [03-infrastructure-layer.md](#3-03-infrastructure-layermd)
4. [04-interfaces-layer.md](#4-04-interfaces-layermd)
5. [05-composition-layer.md](#5-05-composition-layermd)
6. [00-overview.md](#6-00-overviewmd)
7. [README.md](#7-readmemd)
8. [RULES.md](#8-rulesmd)
9. [ADR документы](#9-adr-документы)
10. [Гайды и справочники](#10-гайды-и-справочники)
11. [Сводка несоответствий (актуальная)](#11-сводка-несоответствий-актуальная)
12. [Промты для исправления документации](#12-промты-для-исправления-документации)

---

## 1. 01-domain-layer.md

**Файл:** `docs/02-architecture/01-domain-layer.md`

| № | Предложение | Ссылка на код | Код (фрагмент) | Соответствует | План устранения |
|---|-------------|---------------|-----------------|---------------|-----------------|
| 1 | «Расположение: `src/bioetl/domain/`» | `src/bioetl/domain/` | Директория существует | Да | — |
| 2 | «Не импортирует модули из application, infrastructure или interfaces» | `src/bioetl/domain/**/*.py` | grep подтверждает отсутствие запрещённых импортов | Да | — |
| 3 | «Пакет содержит 24 protocol-файла» | `src/bioetl/domain/ports/*.py` | 24 файла (без `__init__.py`) | Да | — |
| 4 | «DataSourcePort, FilterableDataSourcePort» | `src/bioetl/domain/ports/data_source.py` | Оба класса определены как `@runtime_checkable Protocol` | Да | — |
| 5 | «StoragePort» | `src/bioetl/domain/ports/storage.py` | `class StoragePort(Protocol)` | Да | — |
| 6 | «LockPort» | `src/bioetl/domain/ports/locking.py` | `class LockPort(Protocol)` | Да | — |
| 7 | «CheckpointPort» | `src/bioetl/domain/ports/checkpoint.py` | `class CheckpointPort(Protocol)` | Да | — |
| 8 | «QuarantinePort» | `src/bioetl/domain/ports/quarantine.py` | `class QuarantinePort(Protocol)` | Да | — |
| 9 | «MetricsPort, TracingPort, LoggerPort, DQMonitorPort» | `src/bioetl/domain/ports/observability.py` | Все 4 класса определены | Да | — |
| 10 | «MetadataCoordinatorPort» | `src/bioetl/domain/ports/metadata_coordinator.py` | `class MetadataCoordinatorPort(Protocol)` | Да | — |
| 11 | «BronzeDQAnalyzerPort, SilverDQAnalyzerPort, GoldDQAnalyzerPort, DQReportWriterPort» | `src/bioetl/domain/ports/dq_report.py` | Все 4 класса | Да | — |
| 12 | «GoldValidatorPort» | `src/bioetl/domain/ports/validation.py` | `class GoldValidatorPort(Protocol)` | Да | — |
| 13 | «InputFilterPort» | `src/bioetl/domain/ports/filtering.py` | `class InputFilterPort(Protocol)` | Да | — |
| 14 | «JsonEncoderPort» | `src/bioetl/domain/ports/serialization.py` | `class JsonEncoderPort(Protocol)` | Да | — |
| 15 | «HealthCheckPort, AuditPort, ShutdownPort, MemoryMonitorPort, DeltaReaderPort, IDMappingPort, PiiHasherPort» | Файлы в `domain/ports/` | Все 7 классов | Да | — |
| 16 | «Тест test_ports_imported_only_from_facade» | `tests/architecture/test_forbidden_imports.py:171` | `def test_ports_imported_only_from_facade` | Да | — |
| 17 | «batch.py (536 LOC)» | `src/bioetl/domain/aggregates/batch.py` | 536 строк | Да | — |
| 18 | «pipeline_run.py (574 LOC)» | `src/bioetl/domain/aggregates/pipeline_run.py` | 574 строки | Да | — |
| 19 | «quarantine_entry.py (517 LOC)» | `src/bioetl/domain/aggregates/quarantine_entry.py` | 517 строк | Да | — |
| 20 | «events.py (197 LOC)» | `src/bioetl/domain/aggregates/events.py` | 197 строк | Да | — |
| 21 | «QuarantineStatus: NEW, UNDER_REVIEW, IGNORED, REPROCESSED, EXPIRED» | `src/bioetl/domain/aggregates/quarantine_entry.py:31` | Все 5 значений `StrEnum` | Да | — |
| 22 | «18 файлов в value_objects/» | `src/bioetl/domain/value_objects/` | 18 файлов (без `__init__.py`) | Да | — |
| 23 | «RunID(UUID), BatchID(UUID), EntityID(str), ContentHash(str)» | `src/bioetl/domain/types.py:22-31` | `RunID = NewType("RunID", UUID)` и т.д. | Да | — |
| 24 | «ActivityValue в activity.py (329 LOC) с RelationOperator и ConfidenceScore» | `src/bioetl/domain/value_objects/activity.py` | 329 LOC | Да | — |
| 25 | «PipelineConfig, RuntimeConfig, DQConfig, TableConfig в config.py» | `src/bioetl/domain/config.py` | PipelineConfig :394, RuntimeConfig :538, DQConfig :249, TableConfig :354 | Да | — |
| 26 | «6 файлов в exceptions/» | `src/bioetl/domain/exceptions/` | 6 файлов (без `__init__.py`) | Да | — |
| 27 | «25 файлов в schemas/» | `src/bioetl/domain/schemas/` | 25 файлов (без `__init__.py`) | Да | — |
| 28 | «11 поддиректорий» | `src/bioetl/domain/` | Все 11 поддиректорий существуют | Да | — |
| 29 | «Никакого I/O в domain — нет requests, httpx, aiohttp» | `src/bioetl/domain/**/*.py` | grep подтверждает отсутствие | Да | — |

---

## 2. 02-application-layer.md

**Файл:** `docs/02-architecture/02-application-layer.md`

| № | Предложение | Ссылка на код | Код (фрагмент) | Соответствует | План устранения |
|---|-------------|---------------|-----------------|---------------|-----------------|
| 1 | «Расположение: `src/bioetl/application/`» | `src/bioetl/application/` | Директория существует | Да | — |
| 2 | «Содержит базовые классы (27 файлов) в core/» | `src/bioetl/application/core/` | 27 файлов (без `__init__.py`), 28 с ним | Да | — |
| 3 | «BasePipeline в base.py» | `src/bioetl/application/core/base.py` | `class BasePipeline` | Да | — |
| 4 | «BaseTransformer в base_transformer.py» | `src/bioetl/application/core/base_transformer.py` | `class BaseTransformer` | Да | — |
| 5 | «RecordProcessor в record_processor.py» | `src/bioetl/application/core/record_processor.py` | `class RecordProcessor` | Да | — |
| 6 | «BatchExecutor (786 LOC)» | `src/bioetl/application/core/batch_executor.py` | 786 строк | Да | — |
| 7 | «BatchTransformer, BatchWriter, PipelineRunner» | Файлы в `core/` | Все классы существуют | Да | — |
| 8 | «PipelineServices, LockManager, PreflightService, PostrunService» | Файлы в `core/` | Все классы существуют | Да | — |
| 9 | «CheckpointManager, QuarantineManager, CleanupService» | Файлы в `core/` | Все классы существуют | Да | — |
| 10 | «BatchMetricsRecorder, BatchTracingManager, HeartbeatTask» | Файлы в `core/` | Все классы существуют | Да | — |
| 11 | «FilteredDataSource, IDMappingDataSource» | Файлы в `core/` | Оба класса существуют | Да | — |
| 12 | «PipelineServices — frozen dataclass» | `src/bioetl/application/core/pipeline_services.py:78-93` | `@dataclass(frozen=True)` | Да | — |
| 13 | «23 трансформера (таблица)» | Файлы в `application/pipelines/*/` | Все 23 файла/класса существуют | Да | — |
| 14 | «CompositePipelineRunner в composite/runner.py» | `src/bioetl/application/composite/runner.py:94` | `class CompositePipelineRunner` | Да | — |
| 15 | «EnrichmentCoordinator в composite/coordinator.py» | `src/bioetl/application/composite/coordinator.py:26` | `class EnrichmentCoordinator` | Да | — |
| 16 | «MergeService в composite/merger.py» | `src/bioetl/application/composite/merger.py:62` | `class MergeService` | Да | — |
| 17 | «KeyExtractorService в composite/key_extractor.py» | `src/bioetl/application/composite/key_extractor.py:20` | `class KeyExtractorService` | Да | — |
| 18 | «CompositeCheckpointManager в composite/checkpoint.py» | `src/bioetl/application/composite/checkpoint.py:337` | `class CompositeCheckpointManager` | Да | — |
| 19 | «MedallionLifecycleService в services/medallion_lifecycle.py» | `src/bioetl/application/services/medallion_lifecycle.py:32` | `class MedallionLifecycleService` | Да | — |

---

## 3. 03-infrastructure-layer.md

**Файл:** `docs/02-architecture/03-infrastructure-layer.md`

| № | Предложение | Ссылка на код | Код (фрагмент) | Соответствует | План устранения |
|---|-------------|---------------|-----------------|---------------|-----------------|
| 1 | «ChemblAdapter extends BaseHttpAdapter» | `infrastructure/adapters/chembl/client.py:89` | `class ChemblAdapter(BaseHttpAdapter)` | Да | — |
| 2 | «UniProtAdapter extends BaseHttpAdapter» | `infrastructure/adapters/uniprot/client.py:100` | `class UniProtAdapter(BaseHttpAdapter, PaginatedFetcherMixin)` | Да | — |
| 3 | «PubMedAdapter — @dataclass + BaseHttpAdapter» | `infrastructure/adapters/pubmed/pubmed_client.py:50` | `@dataclass class PubMedAdapter(NotSupportedMultiFilterMixin, BaseHttpAdapter)` | Да | — |
| 4 | «PubChemAdapter extends BaseSyncAdapter» | `infrastructure/adapters/pubchem/client.py:62` | `class PubChemAdapter(FilterableStubMixin, BaseSyncAdapter)` | Да | — |
| 5 | «CrossRefAdapter extends BaseHttpAdapter» | `infrastructure/adapters/crossref/client.py:50` | `@dataclass class CrossRefAdapter(BaseHttpAdapter)` | Да | — |
| 6 | «OpenAlexAdapter extends BaseHttpAdapter» | `infrastructure/adapters/openalex/client.py:47` | `@dataclass class OpenAlexAdapter(BaseHttpAdapter)` | Да | — |
| 7 | «SemanticScholarAdapter extends BaseHttpAdapter» | `infrastructure/adapters/semanticscholar/adapter.py:61` | `class SemanticScholarAdapter(BaseHttpAdapter)` | Да | — |
| 8 | «BronzeWriter записывает JSONL + zstd» | `infrastructure/storage/bronze_writer.py:463` | `.jsonl.zst`, `ZstdCompressor` | Да | — |
| 9 | «SilverWriter — Delta Lake» | `infrastructure/storage/silver_writer.py:36` | `from deltalake import DeltaTable, write_deltalake` | Да | — |
| 10 | «GoldWriter наследует BaseDeltaWriter» | `infrastructure/storage/gold_writer.py:60` | Наследует `BaseDeltaWriter` | Да | — |
| 11 | «ArrowDataConverter в arrow_converter.py» | `infrastructure/storage/arrow_converter.py:19` | `class ArrowDataConverter` | Да | — |
| 12 | «RetentionManager» | `infrastructure/storage/retention_manager.py:31` | `class RetentionManager` | Да | — |
| 13 | «DeltaReader» | `infrastructure/storage/delta_reader.py:23` | `class DeltaReader` | Да | — |
| 14 | «MemoryLock» | `infrastructure/locking/memory_lock.py:19` | `class MemoryLock(LockPort)` | Да | — |
| 15 | «UnifiedHTTPClient с TokenBucket и CircuitBreaker» | `infrastructure/adapters/http/` | Все компоненты существуют | Да | — |
| 16 | «BaseSyncAdapter с ThreadPoolExecutor» | `infrastructure/adapters/sync_base.py:38` | `class BaseSyncAdapter` | Да | — |

---

## 4. 04-interfaces-layer.md

**Файл:** `docs/02-architecture/04-interfaces-layer.md`

| № | Предложение | Ссылка на код | Код (фрагмент) | Соответствует | План устранения |
|---|-------------|---------------|-----------------|---------------|-----------------|
| 1 | «Расположение: `src/bioetl/interfaces/`» | `src/bioetl/interfaces/` | Директория существует | Да | — |
| 2 | «CLI использует Click» | `interfaces/cli/commands/run.py:11` | `import click` | Да | — |
| 3 | «17 модулей в commands/» | `interfaces/cli/commands/` | 17 файлов | Да | — |
| 4 | «run, run_all, run_composite, export, quarantine, health, config, checkpoint, lock, vacuum, cleanup, maintenance, archive» | `interfaces/cli/commands/` | Все файлы существуют | Да | — |
| 5 | «HTTP health endpoint: /health, /health/live, /health/ready» | `interfaces/http/health_server.py` | `class HealthServer` | Да | — |
| 6 | «orchestration/ — модуль пуст, handlers удалены 2025-12-31» | `interfaces/orchestration/__init__.py` | Модуль пуст | Да | — |
| 7 | «Shutdown логика в application/core/shutdown.py» | `application/core/shutdown.py` | `class ShutdownSignal` | Да | — |

---

## 5. 05-composition-layer.md

**Файл:** `docs/02-architecture/05-composition-layer.md`

| № | Предложение | Ссылка на код | Код (фрагмент) | Соответствует | План устранения |
|---|-------------|---------------|-----------------|---------------|-----------------|
| 1 | «bootstrap/ содержит assembly/, cli/, runtime/» | `composition/bootstrap/` | Все 3 поддиректории | Да | — |
| 2 | «runtime/ содержит assembly.py, composite.py, observability.py, pipeline.py, runner.py» | `composition/bootstrap/runtime/` | Все 5 файлов | Да | — |
| 3 | «factories/ — 11 файлов» | `composition/factories/` | 11 файлов (без `__init__.py`), 12 с ним | Да | — |
| 4 | «GenericPipelineFactory, DataSourceFactory, DataSourceRegistry, HttpClientFactory» | Соответствующие файлы | Все классы существуют | Да | — |
| 5 | «StorageFactory, StorageAdapter, RunnerFactory, ServicesBuilder, DQServicesFactory» | Соответствующие файлы | Все классы существуют | Да | — |
| 6 | «ProviderRegistry в composition/providers/» | `composition/providers/provider_registry.py` | `class ProviderRegistry` | Да | — |
| 7 | «8 зарегистрированных провайдеров (включая uniprot_idmapping)» | `composition/providers/registration.py` | 8 вызовов register() | Да | — |
| 8 | «14 ChEMBL pipelines» | `composition/factories/pipeline_factories.py` | 14 ChEMBL pipeline entries | Да | — |
| 9 | «bootstrap_composite_pipeline()» | `composition/bootstrap/runtime/composite.py:529` | Функция существует | Да | — |
| 10 | «Root-level файлы: bootstrap_contexts, builders, entrypoints, registry, types и др.» | `composition/` | Все файлы существуют | Да | — |

---

## 6. 00-overview.md

**Файл:** `docs/02-architecture/00-overview.md`

| № | Предложение | Ссылка на код | Код (фрагмент) | Соответствует | План устранения |
|---|-------------|---------------|-----------------|---------------|-----------------|
| 1 | «33 ADRs» | `docs/02-architecture/decisions/ADR-*.md` | 33 файла | Да | — |
| 2 | «Hexagonal Architecture + Medallion Architecture» | Вся структура src/bioetl/ | Паттерн реализован | Да | — |
| 3 | «Import Matrix — 5 слоёв» | `.importlinter` | Контракты соответствуют | Да | — |
| 4 | «Violation = PR Blocker, enforced by import-linter» | `.importlinter`, `tests/architecture/` | На месте | Да | — |

---

## 7. README.md

**Файл:** `README.md`

| № | Предложение | Ссылка на код | Код (фрагмент) | Соответствует | План устранения |
|---|-------------|---------------|-----------------|---------------|-----------------|
| 1 | «version-5.14.0» (badge) | `pyproject.toml:7` | `version = "5.14.0"` | Да | — |
| 2 | «Python 3.11+» | `pyproject.toml` | `requires-python = ">=3.11"` | Да | — |
| 3 | «coverage ≥85%» (badge) | `pyproject.toml` | `--cov-fail-under=85` | Да | — |
| 4 | «33 ADRs» | `docs/02-architecture/decisions/` | 33 файла | Да | — |
| 5 | «docs/00-project/RULES.md» | `docs/00-project/RULES.md` | Путь корректный | Да | — |
| 6 | «docs/00-project/glossary.md» | `docs/00-project/glossary.md` | Путь корректный | Да | — |
| 7 | «docs/00-project/00-map.md» | `docs/00-project/00-map.md` | Путь корректный | Да | — |
| 8 | «orchestration/ — Reserved (empty)» | `interfaces/orchestration/__init__.py` | Модуль пуст | Да | — |
| 9 | «pipelines/ — 7 провайдеров» | `application/pipelines/` | 7 директорий провайдеров + common | Да | — |
| 10 | «dev_setup.sh, Makefile» | Корень проекта | Оба файла на месте | Да | — |

---

## 8. RULES.md

**Файл:** `docs/00-project/RULES.md`

| № | Предложение | Ссылка на код | Код (фрагмент) | Соответствует | План устранения |
|---|-------------|---------------|-----------------|---------------|-----------------|
| 1 | «SilverWriteMode: MERGE, APPEND, DELETE» | `domain/medallion.py:47-61` | `class SilverWriteMode(StrEnum)` | Да | — |
| 2 | «GoldWriteMode: OVERWRITE, APPEND, SCD2» | `domain/medallion.py:85-99` | `class GoldWriteMode(StrEnum)` | Да | — |
| 3 | «Bronze: JSONL + zstd» | `infrastructure/storage/bronze_writer.py` | `ZstdCompressor`, `.jsonl.zst` | Да | — |
| 4 | «Silver: Delta Lake ACID» | `infrastructure/storage/silver_writer.py:36` | `from deltalake import DeltaTable` | Да | — |
| 5 | «VACUUM retention 7 дней» | `domain/config.py:562`, `domain/medallion.py:283` | `vacuum_retention_days: int = 7` | Да | — |
| 6 | «HealthStatus: HEALTHY, DEGRADED, UNHEALTHY» | `domain/types.py:100-115` | `class HealthStatus(StrEnum)` | Да | — |
| 7 | «Lock key: lock:{provider}_{entity}[:exclusive]» | `domain/locking.py:64-93` | Формат подтверждён | Да | — |
| 8 | «DataSourcePort.fetch — полная сигнатура с 5 параметрами» | `domain/ports/data_source.py:43-67` | `fetch(entity_type, limit, query, filter_ids, filter_field) -> AsyncIterator[dict]` | Да | — |
| 9 | «Классификация ошибок: Critical, Recoverable, Data Quality» | `domain/error_classifier.py:17-57` | Три категории в ErrorType | Да | — |
| 10 | «Schema drift: Info / Warn (>3 полей) / Critical» | `application/services/dq/silver_analyzer.py:227-257` | Реализованы только INFO и CRITICAL; порог >3 для WARN **не реализован** | **Нет** | Либо реализовать WARN порог, либо обновить RULES.md (см. промт 12.1) |
| 11 | «Coverage ≥85%» | `pyproject.toml` | `--cov-fail-under=85` | Да | — |
| 12 | «CircuitBreaker: CLOSED, OPEN, HALF_OPEN» | `domain/types.py:130-145` | `class CircuitBreakerState(StrEnum)` | Да | — |
| 13 | «Medallion Clear Policy» | `application/services/medallion_lifecycle.py` | Логика run_type подтверждена | Да | — |

---

## 9. ADR документы

**Директория:** `docs/02-architecture/decisions/`

| № | ADR | Предложение | Ссылка на код | Соответствует |
|---|-----|-------------|---------------|---------------|
| 1 | ADR-001 | «Delta Lake для Silver/Gold» | `silver_writer.py`, `gold_writer.py` | Да |
| 2 | ADR-004 | «Pydantic для entities, dataclasses для internal» | `domain/entities/`, `domain/aggregates/` | Да |
| 3 | ADR-010 | «Local-Only, нет Redis» | Нет `import redis`; `MemoryLock` единственная реализация | Да |
| 4 | ADR-021 | «3 агрегата: Batch, PipelineRun, QuarantineEntry» | `domain/aggregates/` | Да |
| 5 | ADR-026 | «Composite Pipeline: CompositePipelineRunner» | `application/composite/runner.py:94` | Да |
| 6 | ADR-032 | «UnifiedHTTPClient» | `infrastructure/adapters/http/client.py:48` | Да |

---

## 10. Гайды и справочники

| № | Документ | Предложение | Ссылка на код | Соответствует | План устранения |
|---|----------|-------------|---------------|---------------|-----------------|
| 1 | `pipeline-configuration.md` | «_base.yaml — 491 строка» | `configs/pipelines/_base.yaml` | Да | — |
| 2 | `pipeline-configuration.md` | «31 DQ файл» | `configs/dq/` | Да (31 файл) | — |
| 3 | `local-storage-layout.md` | «Bronze: data/output/bronze/{provider}/{entity}» | `infrastructure/config/config_loader.py:163` | Да | — |
| 4 | `cli.md` | «Все CLI команды и exit codes» | `interfaces/cli/commands/`, `exit_codes.py` | Да | — |
| 5 | `data-layers.md` | «Bronze: JSONL+zstd, Silver: Delta Lake, Gold: Delta Lake» | `bronze_writer.py`, `silver_writer.py`, `gold_writer.py` | Да | — |
| 6 | `testing.md` | «pytest markers: unit, integration, e2e, architecture и др.» | `pyproject.toml` | Да (13 markers) | — |
| 7 | `glossary.md` | «v2.0 Migration: Compound→PubchemMolecule, Document→ChemblPublication, Protein→UniprotTarget (migration complete, old name removed)» | `domain/entities/` | Да | — |

---

## 11. Сводка несоответствий (актуальная)

### Статус исправлений после слияния с main

Из **23 оригинальных несоответствий**, выявленных в первичном аудите, **22 исправлены** коммитами в `main`.

| # | Документ | Проблема | Статус |
|---|----------|----------|--------|
| 1 | `README.md` | Неверные пути: docs/RULES.md, docs/glossary.md, docs/00-map.md | ~~Исправлено~~ |
| 2 | `README.md` | orchestration/ описана как «Signal handlers» | ~~Исправлено~~ |
| 3 | `RULES.md` | DataSourcePort.fetch — упрощённая сигнатура | ~~Исправлено~~ |
| 4 | `RULES.md` | **Schema drift WARN (>3 полей) не реализован** | **Не исправлено** |
| 5 | `01-domain-layer.md` | 26 портов → 24 | ~~Исправлено~~ |
| 6 | `01-domain-layer.md` | 37 файлов schemas → 25 | ~~Исправлено~~ |
| 7 | `01-domain-layer.md` | events.py 260 LOC → 197 | ~~Исправлено~~ |
| 8 | `01-domain-layer.md` | 7 файлов exceptions → 6 | ~~Исправлено~~ |
| 9 | `01-domain-layer.md` | 19 value objects → 18 | ~~Исправлено~~ |
| 10 | `02-application-layer.md` | 27 файлов в core/ | ~~Исправлено~~ (27 без `__init__` верно) |
| 11 | `02-application-layer.md` | 11 трансформеров → 23 | ~~Исправлено~~ |
| 12 | `05-composition-layer.md` | 7 провайдеров → 8 | ~~Исправлено~~ |
| 13 | `05-composition-layer.md` | 13 ChEMBL pipelines → 14 | ~~Исправлено~~ |
| 14 | `README.md` | 32 ADR → 33 | ~~Исправлено~~ |
| 15 | `README.md` | 4 провайдера → 7+ | ~~Исправлено~~ |
| 16 | `README.md` | coverage >80% → ≥85% | ~~Исправлено~~ |
| 17 | `03-infrastructure-layer.md` | ArrowConverter → ArrowDataConverter | ~~Исправлено~~ |
| 18 | `01-domain-layer.md` | batch.py 530 LOC → 536 | ~~Исправлено~~ |
| 19 | `01-domain-layer.md` | pipeline_run.py 566 LOC → 574 | ~~Исправлено~~ |
| 20 | `02-application-layer.md` | BatchExecutor 783 LOC → 786 | ~~Исправлено~~ |
| 21 | `pipeline-configuration.md` | 30 DQ файлов → 31 | ~~Исправлено~~ |
| 22 | `glossary.md` | Deprecated aliases retained → removed | ~~Исправлено~~ |
| 23 | `03-infrastructure-layer.md` | PubMedAdapter @dataclass → + BaseHttpAdapter | ~~Исправлено~~ |

### Оставшееся несоответствие (1 из 23)

| # | Документ | Проблема | Severity | Описание |
|---|----------|----------|----------|----------|
| 4 | `docs/00-project/RULES.md` | Schema drift WARN (>3 полей) документирован, но не реализован | CRITICAL | RULES.md §3.1.2 утверждает три уровня drift: Info / Warn (>3 полей) / Critical. Фактически в `silver_analyzer.py:227-257` реализованы только Info и Critical. Порог >3 для Warn отсутствует в коде. |

---

## Статистика аудита (обновлённая)

| Метрика | Первичный аудит | После слияния main |
|---------|----------------|-------------------|
| Всего проверенных утверждений | 115 | 115 |
| Полное соответствие (Да) | 88 (76.5%) | 114 (99.1%) |
| Несоответствие (Нет) | 23 (20.0%) | **1 (0.9%)** |
| Частичное соответствие | 4 (3.5%) | 0 (0%) |
| Критические проблемы | 4 | **1** |
| Высокие проблемы | 12 | 0 |
| Средние проблемы | 7 | 0 |

---

## 12. Промты для исправления документации

После слияния с `main` остался **единственный промт** для единственного оставшегося несоответствия. Остальные промты помечены как выполненные для справки.

---

### 12.1. CRITICAL — Schema Drift уровни в RULES.md (ЕДИНСТВЕННОЕ ОСТАВШЕЕСЯ)

**Файл:** `docs/00-project/RULES.md`
**Проблема:** WARN >3 полей документирован, но не реализован в коде

```
В файле docs/00-project/RULES.md найди секцию о Schema Drift Detection (§3.1.2).
Текущий текст утверждает три уровня:
- Info: новые опциональные поля
- Warn: >3 новых полей
- Critical: пропавшее обязательное поле

Фактическая реализация (src/bioetl/application/services/dq/silver_analyzer.py:227-257)
использует только два уровня: INFO (любые новые поля) и CRITICAL (пропавшие поля / смена типов).
Порог >3 для WARN не реализован.

Обнови документ одним из двух способов (выбери подходящий):

ВАРИАНТ A — Привести документ в соответствие с кодом:
  Замени таблицу на:
  | Уровень  | Условие                                  |
  |----------|------------------------------------------|
  | Info     | Новые поля (любое количество)            |
  | Critical | Пропавшее обязательное поле / смена типа |

ВАРИАНТ B — Пометить как TODO для реализации:
  Добавь после таблицы:
  > **TODO**: Уровень Warn (>3 новых полей) описан в спецификации,
  > но не реализован в коде. См. silver_analyzer.py:227.
```

---

### 12.2–12.11 — ~~ВЫПОЛНЕНО~~ (исправлено в main)

Промты 12.2–12.11 из оригинального аудита **больше не требуются** — все 22 соответствующих
несоответствия исправлены коммитами в ветке `main`:
- ~~12.2. README.md: пути, orchestration, провайдеры, ADR count, badge~~
- ~~12.3. RULES.md: DataSourcePort.fetch сигнатура~~
- ~~12.4. 01-domain-layer.md: числа (порты, LOC, schemas, exceptions, VO)~~
- ~~12.5. 02-application-layer.md: таблица трансформеров, core count, BatchExecutor LOC~~
- ~~12.6. 05-composition-layer.md: провайдеры, ChEMBL pipelines, root-level файлы~~
- ~~12.7. 03-infrastructure-layer.md: ArrowDataConverter, PubMedAdapter~~
- ~~12.8. glossary.md: deprecated aliases~~
- ~~12.9. pipeline-configuration.md: DQ file count~~
- ~~12.10. Мета-промт: LOC-подсчёты~~
- ~~12.11. Мета-промт: file counts~~

---

### 12.12. Верификационный промт (запуск после исправления #4)

```
Выполни верификацию исправления Schema Drift в RULES.md.

1. Прочитай docs/00-project/RULES.md, секция §3.1.2 Schema Drift Detection
2. Проверь, что таблица уровней соответствует одному из вариантов:
   - Вариант A: только Info и Critical (без Warn)
   - Вариант B: три уровня с пометкой TODO для Warn
3. Прочитай src/bioetl/application/services/dq/silver_analyzer.py:227-257
4. Подтверди, что документ и код согласованы

Результат: «Schema Drift: FIXED» или «Schema Drift: STILL DIVERGENT»
```

---

*Аудит проведён 2026-02-11. Обновлён после слияния с main (7e265aa). Верификация: 114/115 утверждений соответствуют коду (99.1%).*
