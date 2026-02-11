# Исчерпывающий Аудит Документации BioETL

**Дата:** 2026-02-11
**Версия проекта:** 5.14.0 (pyproject.toml)
**Версия RULES.md:** v5.17

---

## Методология

Для каждого предложения из ключевых документов архитектуры выполнена проверка:
1. Соответствие утверждения фактическому коду (файл:строка)
2. Наличие автоматического теста, верифицирующего данное утверждение
3. При несоответствии — предложен план исправления и тест

### Обозначения

| Символ | Значение |
|--------|----------|
| ✅ | Соответствует коду |
| ❌ | НЕ соответствует коду |
| ⚠️ | Частично соответствует |

---

## 1. Domain Layer (`docs/02-architecture/01-domain-layer.md`)

| № | Утверждение в документе | Ссылка на код | Фрагмент кода | Соответствует | План устранения | Тест | Предлагаемый тест |
|---|-------------------------|---------------|----------------|---------------|-----------------|------|-------------------|
| D-01 | «Пакет содержит 26 protocol-файлов» (§2.1) | `src/bioetl/domain/ports/` | 25 файлов (.py), 24 без `__init__.py`, из них `noop.py` — не protocol | ❌ Фактически 24 файла (23 protocol + 1 noop) | Исправить текст: «24 файла (23 protocol-файла + noop.py)» | ❌ | `test_ports_file_count`: `assert len(glob('domain/ports/*.py')) - 1 == 24` |
| D-02 | Перечислены 21 порт: DataSourcePort, FilterableDataSourcePort, StoragePort, LockPort, CheckpointPort, QuarantinePort, MetricsPort, TracingPort, LoggerPort, DQMonitorPort, **PipelineObserverPort**, BronzeDQAnalyzerPort, SilverDQAnalyzerPort, GoldDQAnalyzerPort, DQReportWriterPort, GoldValidatorPort, **InputFilterPort**, **ExportPort**, HealthCheckPort, AuditPort, **RetentionPort** (§2.1) | `src/bioetl/domain/ports/__init__.py` | 3 порта НЕ существуют: `PipelineObserverPort`, `ExportPort`, `RetentionPort`. Фактически 43+ protocol-класса, 22+ не документированы | ❌ | Удалить 3 несуществующих порта, добавить недокументированные (SilverValidatorPort, DeltaReaderPort, IDMappingPort, PiiHasherPort, MemoryMonitorPort, ShutdownPort и др.) | ⚠️ `test_port_contracts.py::TestPortExportsComplete` проверяет `__all__`, но не сверяет с документацией | `test_docs_ports_list_matches_code`: сравнить список портов в docs с `__all__` в `domain/ports/__init__.py` |
| D-03 | QuarantineEntry: состояния `PENDING → RETRYING → RECOVERED/DEAD_LETTER` (§2.2) | `src/bioetl/domain/aggregates/quarantine_entry.py:31-55` | `class QuarantineStatus(StrEnum): NEW, UNDER_REVIEW, IGNORED, REPROCESSED, EXPIRED` | ❌ Фактические состояния: NEW → UNDER_REVIEW → IGNORED/REPROCESSED/EXPIRED | Заменить на: «NEW → UNDER_REVIEW → IGNORED / REPROCESSED / EXPIRED» | ✅ `test_aggregate_boundaries.py` тестирует агрегаты, но не сверяет с документацией | `test_quarantine_states_match_docs`: сравнить enum-значения с текстом документа |
| D-04 | «exceptions/ (5 файлов)» (§2.7) | `src/bioetl/domain/exceptions/` | 7 файлов: `__init__.py`, `base.py`, `data_quality.py`, `infrastructure.py`, `internal.py`, `network.py`, `validation.py` | ❌ Фактически 7 файлов (6 без __init__) | Исправить: «6 файлов исключений» | ❌ | `test_exceptions_file_count`: `assert len(glob('domain/exceptions/*.py')) - 1 == 6` |
| D-05 | «schemas/ (~60 файлов)» (§2.7) | `src/bioetl/domain/schemas/` | 37 .py файлов (включая __init__.py) | ❌ Фактически 37 файлов, не ~60 | Исправить: «~37 файлов» | ❌ | `test_schemas_file_count`: `assert 30 <= len(glob('domain/schemas/**/*.py')) <= 45` |
| D-06 | «value_objects/ (19 файлов)» (§2.3) | `src/bioetl/domain/value_objects/` | 19 .py файлов | ✅ | — | ❌ | `test_value_objects_file_count` |
| D-07 | Batch: OPEN → SEALED → WRITING → COMMITTED/FAILED (§2.2) | `src/bioetl/domain/aggregates/batch.py:31-51` | `class BatchStatus(StrEnum): OPEN, SEALED, WRITING, COMMITTED, FAILED` | ✅ | — | ✅ `test_aggregate_boundaries.py` | — |
| D-08 | PipelineRun: PENDING → RUNNING → COMPLETED/FAILED/SHUTDOWN (§2.2) | `src/bioetl/domain/aggregates/pipeline_run.py:27-38` | `class RunStatus(StrEnum): PENDING, RUNNING, COMPLETED, FAILED, SHUTDOWN` | ✅ | — | ✅ `test_aggregate_boundaries.py` | — |
| D-09 | config.py: PipelineConfig, RuntimeConfig, DQConfig, TableConfig (§2.5) | `src/bioetl/domain/config.py:249,354,394,537` | Все 4 класса найдены + 6 дополнительных | ✅ | — | ❌ | `test_config_classes_exist` |
| D-10 | types.py: RunID, BatchID, EntityID, ContentHash (§2.4) | `src/bioetl/domain/types.py:22-31` | `RunID = NewType("RunID", UUID)` и др. | ✅ | — | ✅ `test_domain_public_api.py` | — |
| D-11 | Domain не импортирует application/infrastructure/interfaces (§1) | `src/bioetl/domain/**/*.py` | 0 нарушений | ✅ | — | ✅ `test_layer_dependencies.py` (7 тестов) + import-linter | — |
| D-12 | Тест `test_ports_imported_only_from_facade` (§2.1) | `tests/architecture/test_forbidden_imports.py:171` | `class TestPortImportFacade` | ✅ | — | ✅ | — |

---

## 2. Application Layer (`docs/02-architecture/02-application-layer.md`)

| № | Утверждение | Ссылка на код | Фрагмент | Соответствует | План устранения | Тест | Предлагаемый тест |
|---|-------------|---------------|----------|---------------|-----------------|------|-------------------|
| A-01 | «core/ (27 файлов)» (§2.2) | `src/bioetl/application/core/` | 27 .py файлов | ✅ | — | ❌ | `test_core_file_count` |
| A-02 | BasePipeline в base.py (§2.2) | `src/bioetl/application/core/base.py:27` | `class BasePipeline(ABC):` | ✅ | — | ✅ `test_base_pipeline_purity.py` | — |
| A-03 | BaseTransformer в base_transformer.py (§2.2) | `src/bioetl/application/core/base_transformer.py:84` | `class BaseTransformer(ABC):` | ✅ | — | ✅ `test_transformer_signatures.py` | — |
| A-04 | BatchExecutor 783 LOC (§2.2) | `src/bioetl/application/core/batch_executor.py` | 783 строк, `class BatchExecutor:` на строке 62 | ✅ | — | ❌ | — |
| A-05 | PipelineServices frozen dataclass с 14 полями (§2.4) | `src/bioetl/application/core/pipeline_services.py:39-93` | `@dataclass(frozen=True) class PipelineServices:` — все 14 полей совпадают | ✅ | — | ❌ | `test_pipeline_services_fields` |
| A-06 | 11 трансформеров по документированным путям (§2.3) | См. таблицу | Все 11 найдены по точным путям | ✅ | — | ✅ `test_transformer_signatures.py` | — |
| A-07 | Composite: CompositePipelineRunner, EnrichmentCoordinator, MergeService, KeyExtractorService, CompositeCheckpointManager (§2.5) | `src/bioetl/application/composite/` | Все 5 классов найдены | ✅ | — | ✅ `test_composite_layer_boundaries.py` | — |
| A-08 | Application не импортирует infrastructure (§1) | `src/bioetl/application/**/*.py` | 0 нарушений | ✅ | — | ✅ `test_layer_dependencies.py` + import-linter | — |

---

## 3. Infrastructure Layer (`docs/02-architecture/03-infrastructure-layer.md`)

| № | Утверждение | Ссылка на код | Фрагмент | Соответствует | План устранения | Тест | Предлагаемый тест |
|---|-------------|---------------|----------|---------------|-----------------|------|-------------------|
| I-01 | ChemblAdapter наследует BaseHttpAdapter (§2.1.1) | `src/bioetl/infrastructure/adapters/chembl/client.py:88-89` | `@dataclass class ChemblAdapter(BaseHttpAdapter)` | ✅ | — | ✅ `test_adapter_contracts.py` | — |
| I-02 | PubMedAdapter: базовый класс `@dataclass` (§2.1.1) | `src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py:49-50` | `@dataclass class PubMedAdapter(NotSupportedMultiFilterMixin, BaseHttpAdapter)` | ⚠️ Doc говорит базовый класс `@dataclass`, но фактически BaseHttpAdapter | Исправить таблицу: «BaseHttpAdapter» в колонке «Базовый класс» | ❌ | `test_adapter_base_classes`: проверить базовые классы всех адаптеров |
| I-03 | PubChemAdapter наследует BaseSyncAdapter (§2.1.1) | `src/bioetl/infrastructure/adapters/pubchem/client.py:62` | `class PubChemAdapter(FilterableStubMixin, BaseSyncAdapter)` | ✅ | — | ✅ `test_adapter_contracts.py` | — |
| I-04 | UnifiedHTTPClient: Rate Limiter, Circuit Breaker, Retry, Metrics (§2.1.1) | `src/bioetl/infrastructure/adapters/http/client.py:83-93` | `rate_limiter: RateLimiterPort`, `circuit_breaker: CircuitBreakerPort`, `retry_config: RetryConfig`, `metrics: MetricsPort` | ✅ | — | ✅ `test_port_contracts.py` | — |
| I-05 | BronzeWriter: JSONL+zstd, atomic temp+rename (§2.2) | `src/bioetl/infrastructure/storage/bronze_writer.py:30,341-407,463` | `import zstandard as zstd`, `.jsonl.zst`, `mkstemp()` + `replace()` | ✅ | — | ✅ `test_medallion_invariants.py`, `test_adapter_contracts.py` | — |
| I-06 | SilverWriter: Delta Lake, merge/upsert (§2.2) | `src/bioetl/infrastructure/storage/silver_writer.py:36,80,859-894` | `from deltalake import DeltaTable`, `dt.merge()` | ✅ | — | ✅ `test_medallion_invariants.py` | — |
| I-07 | GoldWriter наследует BaseDeltaWriter + Pandera (§2.2) | `src/bioetl/infrastructure/storage/gold_writer.py:25,60` | `class GoldWriter(BaseDeltaWriter)`, `import pandera` | ✅ | — | ✅ `test_gold_schema_contracts.py` | — |
| I-08 | MemoryLock: in-memory, LockPort (§2.3) | `src/bioetl/infrastructure/locking/memory_lock.py:19` | `class MemoryLock(LockPort)` с asyncio.Lock | ✅ | — | ✅ `test_lock_safety_guard.py` | — |
| I-09 | LocalCheckpoint (§2.4) | `src/bioetl/infrastructure/checkpoint/local_checkpoint.py:31` | `class LocalCheckpoint` — filesystem-based | ✅ | — | ❌ | `test_local_checkpoint_implements_port` |
| I-10 | Infrastructure не импортирует application/interfaces (§3) | `src/bioetl/infrastructure/**/*.py` | 0 нарушений | ✅ | — | ✅ `test_layer_dependencies.py` | — |

---

## 4. Interfaces Layer (`docs/02-architecture/04-interfaces-layer.md`)

| № | Утверждение | Ссылка на код | Фрагмент | Соответствует | План устранения | Тест | Предлагаемый тест |
|---|-------------|---------------|----------|---------------|-----------------|------|-------------------|
| IF-01 | «17 модулей в commands/» (§2.1) | `src/bioetl/interfaces/cli/commands/` | 16 файлов (15 без __init__) | ❌ Фактически 15 command-модулей | Исправить: «15 модулей» (или 16 с __init__) | ❌ | `test_cli_commands_count` |
| IF-02 | 13 перечисленных команд (run, run_all, ... archive) (§2.1) | `src/bioetl/interfaces/cli/commands/` | Все 13 найдены + 3 не упомянуты: `health_server_integration.py`, `metrics_server_integration.py`, `run_helpers.py` | ⚠️ Перечисленные существуют, но 3 модуля не документированы | Добавить в таблицу: health_server_integration, metrics_server_integration, run_helpers | ❌ | `test_all_commands_documented` |
| IF-03 | CLI использует Click (§2.1) | `src/bioetl/interfaces/cli/main.py:9` | `import click` — Click везде, Typer не используется | ✅ | — | ❌ | — |
| IF-04 | HTTP: /health, /health/live, /health/ready (§2.2) | `src/bioetl/interfaces/http/health_server.py:143-151` | Все 3 endpoints + 2 дополнительных: `/healthz`, `/health/providers` | ✅ | Документировать `/healthz` и `/health/providers` | ❌ | `test_health_endpoints_documented` |
| IF-05 | orchestration/ содержит graceful shutdown (§2.3) | `src/bioetl/interfaces/orchestration/__init__.py:10-12` | «Signal handlers were removed in 2025-12-31» — модуль пуст | ❌ Graceful shutdown удалён, обрабатывается в CLI напрямую | Обновить: «Graceful shutdown обрабатывается в CLI (run.py, run_all.py, run_composite.py)» | ❌ | `test_orchestration_not_empty_or_docs_updated` |

---

## 5. Composition Layer (`docs/02-architecture/05-composition-layer.md`)

| № | Утверждение | Ссылка на код | Фрагмент | Соответствует | План устранения | Тест | Предлагаемый тест |
|---|-------------|---------------|----------|---------------|-----------------|------|-------------------|
| C-01 | bootstrap/cli/ содержит: health, lock, config, metrics, noop (§2.1) | `src/bioetl/composition/bootstrap/cli/` | 7 модулей (без __init__): checkpoint, config, health, lock, metrics, noop, storage | ⚠️ 2 модуля не документированы: `checkpoint.py`, `storage.py` | Добавить checkpoint и storage в список | ❌ | `test_bootstrap_cli_modules_documented` |
| C-02 | «factories/ (12 файлов)» (§2.2) | `src/bioetl/composition/factories/` | 12 .py файлов | ✅ | — | ❌ | `test_factories_file_count` |
| C-03 | StorageAdapterFactory (§2.2) | `src/bioetl/composition/factories/storage_adapter.py:38` | Класс называется `StorageAdapter`, не `StorageAdapterFactory` | ❌ | Исправить: «StorageAdapter» (без Factory) | ❌ | — |
| C-04 | ServicesFactory (§2.2) | `src/bioetl/composition/factories/services_factory.py:129,372` | Классы: `BaseServicesFactory` и `ServicesBuilder`, не `ServicesFactory` | ❌ | Исправить: «BaseServicesFactory / ServicesBuilder» | ❌ | — |
| C-05 | TransformerFactory — класс (§2.2) | `src/bioetl/composition/factories/transformer_factory.py:31,47` | Нет класса TransformerFactory — только функции `register_transformer()`, `create_transformer()` | ❌ | Исправить: «transformer_factory.py — модуль с функциями create_transformer(), register_transformer()» | ❌ | — |
| C-06 | DQFactory (§2.2) | `src/bioetl/composition/factories/dq_factory.py:35` | Класс называется `DQServicesFactory`, не `DQFactory` | ❌ | Исправить: «DQServicesFactory» | ❌ | — |
| C-07 | DataSourceRegistry в providers/ (§2.3) | `src/bioetl/composition/factories/data_source_factory.py:100` | DataSourceRegistry находится в factories/, не в providers/ | ❌ | Исправить расположение в документации | ❌ | — |
| C-08 | «7 зарегистрированных провайдеров» (§2.3) | `src/bioetl/composition/providers/registration.py:506-637` | 8 провайдеров: +`uniprot_idmapping` | ❌ | Добавить uniprot_idmapping в таблицу (8 провайдеров) | ❌ | `test_registered_providers_count_matches_docs` |
| C-09 | bootstrap_composite_pipeline — async, принимает (name, limit) (§3.1) | `src/bioetl/composition/bootstrap/runtime/composite.py:528` | Функция sync (не async), принимает `(config: CompositeConfig, runtime: CompositeRuntimeConfig)` | ❌ | Исправить пример в документации на актуальную сигнатуру | ❌ | `test_bootstrap_composite_signature` |

---

## 6. Architecture Overview (`docs/02-architecture/00-overview.md`)

| № | Утверждение | Ссылка на код | Фрагмент | Соответствует | План устранения | Тест | Предлагаемый тест |
|---|-------------|---------------|----------|---------------|-----------------|------|-------------------|
| O-01 | «33 ADR» (строка 40) | `docs/02-architecture/decisions/ADR-*.md` | 33 файла ADR-001..ADR-033 | ✅ | — | ❌ | `test_adr_count` |
| O-02 | «35 Mermaid diagram files» (строка 31) | `docs/02-architecture/diagrams/` | 35 `.mermaid` + 22 `.mmd` = 57 файлов | ⚠️ 35 .mermaid верно, но 22 .mmd не упомянуты | Уточнить: «35 .mermaid + 22 .mmd файлов» | ❌ | `test_diagram_files_count` |
| O-03 | «Additional 26 diagrams» в mermaid/ (строка 34) | `docs/02-architecture/diagrams/mermaid/` | 22 .mmd файла, не 26 | ❌ | Исправить: 22 | ❌ | `test_mermaid_subdir_count` |
| O-04 | Import Matrix (строки 84-90) | `.importlinter`, `tests/architecture/test_layer_dependencies.py` | Семантически идентична ARCH-001 (порядок колонок отличается) | ✅ | — | ✅ `test_layer_dependencies.py` + import-linter | — |
| O-05 | «Enforced by import-linter and tests/architecture/» (строка 92) | `.importlinter` (71 строка, 5 контрактов) + `tests/architecture/` (45 тестовых файлов) | Оба механизма существуют | ✅ | — | ✅ (самореференция) | — |

---

## 7. Ключевые ADR

| № | ADR | Утверждение | Ссылка на код | Соответствует | План устранения | Тест | Предлагаемый тест |
|---|-----|-------------|---------------|---------------|-----------------|------|-------------------|
| ADR-01 | ADR-001 | Delta Lake для Silver/Gold | `silver_writer.py:36`, `gold_writer.py:27` | ✅ | — | ✅ `test_medallion_invariants.py` | — |
| ADR-02 | ADR-003 | MemoryLock, нет Redis | `memory_lock.py:19`, pyproject.toml | ✅ Нет Redis-зависимостей | — | ✅ `test_lock_safety_guard.py` | — |
| ADR-03 | ADR-005 | Composition как отдельный слой | `src/bioetl/composition/` | ✅ | — | ✅ `test_bootstrap_layer_boundaries.py` | — |
| ADR-04 | ADR-010 | Local-only, нет cloud deps | pyproject.toml | ✅ Нет boto3/redis/prefect | — | ✅ `test_forbidden_imports.py::test_no_cloud_or_distributed_libs` | — |
| ADR-05 | ADR-021 | 3 DDD агрегата + события | `domain/aggregates/` | ✅ Batch, PipelineRun, QuarantineEntry + 12 event-классов | — | ✅ `test_aggregate_boundaries.py` | — |
| ADR-06 | ADR-026 | Composite Pipeline | `application/composite/`, `domain/composite/` | ✅ Runner, Coordinator, Merger, FSM | — | ✅ `test_composite_layer_boundaries.py` | — |
| ADR-07 | ADR-032 | Unified HTTP Client | `infrastructure/adapters/http/client.py:48` | ✅ Rate limiter + CB + retry + metrics | — | ✅ `test_port_contracts.py` | — |
| ADR-08 | — | User-Agent версия «BioETL/5.0.0» | `infrastructure/adapters/http/client.py:88` | ❌ pyproject.toml = 5.14.0, UA = 5.0.0 | Обновить `user_agent` до `"BioETL/5.14.0"` или динамически из `importlib.metadata` | ❌ | `test_user_agent_version_matches_package` |

---

## 8. Правила Self-Review (`ai-selfreview-rules.md`) — Покрытие тестами

| № | Правило | Описание | Тест есть? | Файл теста | Предлагаемый тест |
|---|---------|----------|------------|------------|-------------------|
| SR-01 | ARCH-001 | Import Matrix | ✅ | `test_layer_dependencies.py` (7+ тестов), `.importlinter` | — |
| SR-02 | ARCH-002 | Domain Purity (no I/O) | ✅ | `test_domain_purity.py` | — |
| SR-03 | ARCH-003 | Port Protocol Naming (*Port suffix) | ⚠️ | `test_domain_purity.py` (Protocol usage), но нет проверки суффикса *Port | `test_all_ports_have_port_suffix` |
| SR-04 | ARCH-004 | Adapter Health Check | ✅ | `test_adapter_contracts.py` | — |
| SR-05 | ARCH-005 | Composition Root Isolation | ✅ | `test_di_compliance.py::test_factories_only_in_composition` | — |
| SR-06 | ARCH-006 | Silver Layer ACID (Delta Lake) | ✅ | `test_medallion_invariants.py` | — |
| SR-07 | ARCH-007 | Medallion Clear Policy (REBUILD/BACKFILL/INCREMENTAL) | ❌ | — | `test_clear_policy_by_run_type`: проверить что REBUILD очищает Silver+Gold, INCREMENTAL — нет |
| SR-08 | ARCH-008 | Ports from facade only | ✅ | `test_forbidden_imports.py::test_ports_imported_only_from_facade` | — |
| SR-09 | AP-001 | DI Hard-coded Constructor | ✅ | `test_di_compliance.py`, `test_di_constructors.py` | — |
| SR-10 | AP-002 | No structlog in app/interfaces | ✅ | `test_no_structlog_in_application_interfaces.py` | — |
| SR-11 | AP-004 | Sentinel Values | ❌ | — | `test_no_sentinel_values`: grep для `-1`, `"N/A"`, `9999` в `src/bioetl/` |
| SR-12 | AP-005 | Hardcoded Secrets | ❌ | — | `test_no_hardcoded_secrets`: grep для `password=`, `api_key=`, `secret=` |
| SR-13 | AP-006 | Print Statements | ⚠️ | `test_no_print_in_docstrings.py` (только docstrings) | `test_no_print_in_production`: grep `print(` в `src/bioetl/` кроме `interfaces/cli/` |
| SR-14 | AP-008 | Blocking I/O in Async | ❌ | — | `test_no_blocking_io_in_async`: проверить `open(`, `requests.` внутри `async def` |
| SR-15 | DI-003 | Service Locator | ❌ | — | `test_no_service_locator`: grep `ServiceLocator`, `Container.resolve` |
| SR-16 | DI-004 | Import-time Side Effects | ⚠️ | `test_no_side_effects_in_composition.py` (только composition) | `test_no_module_level_instantiation`: AST-анализ `domain/`, `application/` |
| SR-17 | NAME-001 | Class Suffixes | ❌ | — | `test_class_naming_conventions`: проверить суффиксы Factory, Client, Port, Service, Transformer |
| SR-18 | NAME-002 | Function Prefixes | ❌ | — | `test_function_naming_prefixes` |
| SR-19 | NAME-003..006 | Module/Constant/Enum Naming | ❌ | — | `test_naming_conventions_suite` |
| SR-20 | TYPE-001 | Public Function Annotations | ❌ | — | `test_public_functions_have_annotations` |
| SR-21 | TYPE-002 | Any Usage | ❌ | — | `test_any_usage_justified` |
| SR-22 | TYPE-003 | mypy --strict | ❌ (в CI, не в arch-тестах) | — | `test_mypy_strict` (или оставить в CI) |
| SR-23 | TYPE-004 | Protocol @runtime_checkable | ✅ | `test_port_contracts.py::TestPortRuntimeCheckable` | — |
| SR-24 | TEST-003 | VCR Cassettes for HTTP | ❌ | — | `test_http_tests_use_vcr` |
| SR-25 | TEST-005 | No Test Logic in Production | ❌ | — | `test_no_test_logic_in_production`: grep `pytest`, `unittest` в `src/bioetl/` |

---

## 9. Сводная статистика

### По документам

| Документ | Всего утверждений | ✅ Совпадает | ⚠️ Частично | ❌ Не совпадает |
|----------|-------------------|-------------|-------------|----------------|
| 01-domain-layer.md | 12 | 6 | 1 | 5 |
| 02-application-layer.md | 8 | 8 | 0 | 0 |
| 03-infrastructure-layer.md | 10 | 9 | 1 | 0 |
| 04-interfaces-layer.md | 5 | 2 | 1 | 2 |
| 05-composition-layer.md | 9 | 2 | 1 | 6 |
| 00-overview.md | 5 | 3 | 1 | 1 |
| ADR (ключевые) | 8 | 7 | 0 | 1 |
| **Итого** | **57** | **37 (65%)** | **5 (9%)** | **15 (26%)** |

### По покрытию тестами правил

| Категория | Всего правил | С тестом | Без теста |
|-----------|-------------|----------|-----------|
| ARCH (архитектура) | 8 | 7 | 1 |
| AP (антипаттерны) | 8 | 3 | 5 |
| DI (dependency injection) | 5 | 3 | 2 |
| NAME (именование) | 6 | 0 | 6 |
| TYPE (типизация) | 4 | 1 | 3 |
| TEST (тестирование) | 5 | 1 | 4 |
| **Итого** | **36** | **15 (42%)** | **21 (58%)** |

---

## 10. Топ-10 критических несоответствий

| Приоритет | ID | Документ | Проблема | Влияние |
|-----------|----|----------|----------|---------|
| 🔴 P1 | D-03 | domain-layer | QuarantineEntry states полностью неверны (PENDING/RETRYING vs NEW/UNDER_REVIEW) | Разработчики будут реализовывать несуществующие состояния |
| 🔴 P1 | C-09 | composition-layer | bootstrap_composite_pipeline — неверная сигнатура (async vs sync, string vs config) | Пример кода не компилируется |
| 🔴 P1 | IF-05 | interfaces-layer | Документирован graceful shutdown в orchestration/, но модуль пуст | Архитектурная документация описывает несуществующий функционал |
| 🟡 P2 | D-02 | domain-layer | 3 несуществующих порта, 22+ недокументированных | Неполная карта портов |
| 🟡 P2 | C-03..C-06 | composition-layer | 4 фабрики с неверными именами классов | Разработчики не найдут классы по документации |
| 🟡 P2 | C-07 | composition-layer | DataSourceRegistry — неверное расположение (providers/ vs factories/) | Неверная навигация по коду |
| 🟡 P2 | ADR-08 | http/client.py | User-Agent "BioETL/5.0.0" при версии 5.14.0 | Некорректная идентификация в запросах к API |
| 🟢 P3 | D-01, D-04, D-05 | domain-layer | Неверные подсчёты файлов (26→24, 5→6, ~60→37) | Косметика, но снижает доверие к документации |
| 🟢 P3 | IF-01 | interfaces-layer | «17 модулей» → фактически 15 | Косметика |
| 🟢 P3 | O-03 | overview | «26 diagrams» → фактически 22 | Косметика |

---

## 11. Рекомендуемый план устранения

### Фаза 1: Критические (P1) — срочно

1. **D-03**: Обновить `01-domain-layer.md §2.2` — заменить `PENDING → RETRYING → RECOVERED/DEAD_LETTER` на `NEW → UNDER_REVIEW → IGNORED/REPROCESSED/EXPIRED`
2. **C-09**: Обновить `05-composition-layer.md §3.1` — исправить пример `bootstrap_composite_pipeline` на актуальную сигнатуру
3. **IF-05**: Обновить `04-interfaces-layer.md §2.3` — указать что signal handlers удалены, graceful shutdown в CLI

### Фаза 2: Важные (P2) — в текущем спринте

4. **D-02**: Обновить список портов в `01-domain-layer.md §2.1` — удалить 3 несуществующих, добавить актуальные
5. **C-03..C-06**: Исправить имена фабрик в `05-composition-layer.md §2.2`
6. **C-07**: Исправить расположение DataSourceRegistry
7. **ADR-08**: Исправить user_agent в `http/client.py` или сделать динамическим

### Фаза 3: Косметические (P3) — при следующем обновлении

8. Исправить подсчёты файлов (D-01, D-04, D-05, IF-01, O-03)
9. Документировать недостающие модули (IF-02, C-01, C-08)

### Фаза 4: Недостающие тесты

10. Добавить 21 недостающий архитектурный тест (см. таблицу §8)

---

*Отчёт сгенерирован автоматически. Рекомендуется ручная верификация критических несоответствий.*
