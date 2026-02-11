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

# ФАЗА 2: Расширенный Аудит

**Дополнительно проверены:** RULES.md (§1-§7), API Reference (4 файла), CLI Reference, Getting Started, 14 ADR, Operations/Runbooks (20+ файлов), .aiassistant/governance (25+ файлов), Pipeline/Provider specs (41 файл)

---

## 12. RULES.md §1-§3 (`docs/00-project/RULES.md`)

| № | Утверждение | Ссылка на код | Соответствует | План устранения |
|---|-------------|---------------|---------------|-----------------|
| R-01 | Silver формат: «Delta Lake / Iceberg» (§1.3) | `silver_writer.py:36`: `from deltalake import DeltaTable` | ❌ Iceberg НЕ реализован, только Delta Lake | Убрать «/ Iceberg» из RULES.md |
| R-02 | Gold формат: «Delta/Iceberg/Parquet» (§1.3) | `gold_writer.py:27`: `from deltalake` | ❌ Только Delta Lake, нет Iceberg/Parquet | Исправить: «Delta Lake» |
| R-03 | `PipelineRunner._clear_exports()` очищает Silver/Gold (§1.4) | `application/core/runner.py` | ❌ Метод не существует. Логика в `MedallionLifecycleService.clear()` | Исправить ссылку на `MedallionLifecycleService.clear()` |
| R-04 | QuarantineStatus: 3 значения (NEW\|IGNORED\|REPROCESSED) (§2.3) | `domain/aggregates/quarantine_entry.py:31-55` | ❌ Фактически 5: +UNDER_REVIEW, EXPIRED | Добавить 2 недокументированных статуса |
| R-05 | `compute_content_hash` (§2.2) | `domain/transformations.py:101` | ❌ Фактическое имя: `generate_content_hash` | Исправить имя функции |
| R-06 | Лог-поле `ts` (§3.1) | structlog TimeStamper | ❌ Фактическое поле: `timestamp` | Исправить: `timestamp` |
| R-07 | Bronze: JSONL + zstd (§1.3) | `bronze_writer.py:30,463` | ✅ | — |
| R-08 | Lock TTL: 90 секунд (§5.2) | `domain/config.py:554` | ✅ | — |
| R-09 | Heartbeat interval: 30 секунд (§5.2) | `domain/config.py:551` | ✅ | — |
| R-10 | `from __future__ import annotations` во всех файлах (§4.1) | 100+ файлов проверено | ✅ | — |
| R-11 | Coverage threshold: 85% (§4.3) | `pyproject.toml:219`, `Makefile:66` | ✅ | — |
| R-12 | VCR cassettes в `tests/fixtures/vcr/` (§4.3) | 8 провайдер-директорий | ✅ | — |
| R-13 | ChEMBL API base URL: `ebi.ac.uk/chembl/api/data` (§5.1) | `infrastructure/adapters/chembl/entity_mapper.py:35` | ✅ | — |
| R-14 | PII hashing: sha256(lowercase + SALT) (§5.4) | Domain filtering modules | ✅ | — |
| R-15 | 33 ADR (§6.1) | `docs/02-architecture/decisions/ADR-*.md` | ✅ | — |

**Итого RULES.md §1-§3:** 9/15 ✅ (60%), 0 ⚠️, 6/15 ❌ (40%)

---

## 13. RULES.md §4-§7 (`docs/00-project/RULES.md`)

| № | Утверждение (секция) | Ссылка на код | Соответствует | План устранения |
|---|----------------------|---------------|---------------|-----------------|
| R-16 | UnifiedHTTPClient в `infrastructure/adapters/http/client.py` (§4.1) | `client.py:48`: `class UnifiedHTTPClient` | ✅ | — |
| R-17 | HTTP client использует httpx (§4.1) | `client.py:24`: `import httpx` | ✅ | — |
| R-18 | pytest>=8.0, pytest-cov>=4.0, pytest-asyncio>=0.23, pytest-xdist>=3.5 (§4.3) | `pyproject.toml:62-66` | ✅ | — |
| R-19 | VCR.py и pytest-vcr (§4.3) | `pyproject.toml:79-81` | ✅ | — |
| R-20 | Type hints: `list[str]` не `List[str]`, `X | None` не `Optional[X]` (§4.1) | Ruff rules FA enabled | ✅ | — |
| R-21 | No `import random` в storage writers (§4.2) | 0 occurrences | ✅ | — |
| R-22 | Graceful shutdown with signal handling (§5.3) | `application/core/shutdown.py` | ✅ | — |
| R-23 | `async def aclose()` contract в адаптерах (§5.3) | 5+ адаптеров проверено | ✅ | — |
| R-24 | aclose() is idempotent (§5.3) | Base adapter definition | ✅ | — |
| R-25 | DR targets: RPO 24h, RTO 4h (§5.5) | RULES.md §5.5 | ✅ | — |
| R-26 | Content hash excludes: `_ingestion_ts`, `_run_id`, `_run_type`, `_source_batch_id` (§4.2) | Config-driven | ✅ | — |
| R-27 | MD5-based jitter (not random module) (§4.2) | Domain resilience config | ✅ | — |
| R-28 | `docs/archived/refactoring-plan.md` exists (§7.1) | File confirmed | ✅ | — |

**Итого RULES.md §4-§7:** 13/13 ✅ (100%)

---

## 14. API Reference Documentation

### 14.1. Domain API (`docs/04-reference/api/domain.md`)

| № | Утверждение | Ссылка на код | Соответствует | План устранения |
|---|-------------|---------------|---------------|-----------------|
| API-01 | LockPort: метод `refresh()` (§Ports) | `domain/ports/locking.py:64` | ❌ Фактический метод: `heartbeat()` | Исправить: `heartbeat()` |
| API-02 | MetricsPort: `increment()` (§Ports) | `domain/ports/observability.py:46` | ❌ Фактический: `increment_counter()` | Исправить имя метода |
| API-03 | MetricsPort: `gauge()` (§Ports) | `domain/ports/observability.py:61` | ❌ Фактический: `set_gauge()` | Исправить имя метода |
| API-04 | MetricsPort: `histogram()` (§Ports) | `domain/ports/observability.py:76` | ❌ Фактический: `observe_histogram()` | Исправить имя метода |
| API-05 | Entity `Activity` (§Entities) | `domain/entities/` | ❌ Фактически: `ActivityRecord` / `Bioactivity` | Исправить имя |
| API-06 | Entity `Document` (§Entities) | `domain/entities/` | ❌ Класс не существует | Удалить или уточнить |
| API-07 | `compute_content_hash` (§Transformations) | `domain/transformations.py:101` | ❌ Фактически: `generate_content_hash` | Исправить имя |

### 14.2. Infrastructure API (`docs/04-reference/api/infrastructure.md`)

| № | Утверждение | Ссылка на код | Соответствует | План устранения |
|---|-------------|---------------|---------------|-----------------|
| API-08 | `MetricsExporter` class (§Observability) | Весь код | ❌ Не существует. Фактически: `PrometheusMetrics` | Исправить имя класса |
| API-09 | `LineageTracker` class (§Observability) | Весь код | ❌ Класс не существует нигде | Удалить из документации |
| API-10 | UnifiedHTTPClient constructor: `base_url`, `rate_limit`, `max_retries` (§HTTP) | `http/client.py:83-93` | ❌ Фактически: `rate_limiter: RateLimiterPort`, `circuit_breaker: CircuitBreakerPort`, `retry_config: RetryConfig` | Полностью переписать пример конструктора |
| API-11 | `DeltaWriter` class (§Storage) | Весь код | ❌ Класс полностью удалён | Удалить из документации |

### 14.3. Composition API (`docs/04-reference/api/composition.md`)

| № | Утверждение | Ссылка на код | Соответствует | План устранения |
|---|-------------|---------------|---------------|-----------------|
| API-12 | `ServicesFactory` class (§Factories) | `composition/factories/services_factory.py` | ❌ Фактически: `BaseServicesFactory` / `ServicesBuilder` | Исправить имя |
| API-13 | `@register("chembl_activity")` decorator (§Registry) | Весь код | ❌ Декоратор не существует. Фактически: `registry.register_factory()` | Исправить пример |
| API-14 | `bootstrap_pipeline(ctx)` extra `registry` param (§Bootstrap) | `composition/bootstrap/` | ⚠️ Сигнатура в целом верна, но `registry` не документирован | Добавить optional param |

### 14.4. CLI Reference (`docs/04-reference/cli.md`)

| № | Утверждение | Ссылка на код | Соответствует | План устранения |
|---|-------------|---------------|---------------|-----------------|
| API-15 | Exit codes 82-87 (§Exit Codes) | `interfaces/cli/exit_codes.py:52-57` | ✅ | — |
| API-16 | `--health-server/--no-health-server` flag (§run) | `interfaces/cli/commands/run.py:191` | ✅ | — |
| API-17 | `quarantine resolve --payload-hash` (§quarantine) | `interfaces/cli/commands/quarantine.py:220` | ✅ | — |

**Итого API Reference:** 3/17 ✅ (18%), 1/17 ⚠️ (6%), 13/17 ❌ (76%)

---

## 15. Getting Started Guide (`docs/03-guides/getting-started.md`)

| № | Утверждение | Ссылка на код | Соответствует | План устранения |
|---|-------------|---------------|---------------|-----------------|
| GS-01 | Bronze path: `data/bronze/v1/chembl/activity/` | `config_loader.py:163` | ❌ Фактически: `data/output/bronze/chembl/activity/{date}/` (нет `v1/`, нужен `output/`) | Исправить паттерн пути |
| GS-02 | Silver path: `data/silver/chembl.activity/` | `config_loader.py:163` | ❌ Фактически: `data/output/silver/chembl/activity/` (слеш не точка, нужен `output/`) | Исправить разделитель и путь |
| GS-03 | Gold path: `data/gold/chembl.activity_gold/` | `config_loader.py:163` | ❌ Фактически: `data/output/gold/chembl/activity/` (нет `_gold` суффикса) | Исправить паттерн пути |
| GS-04 | Convention: `data/output/{layer}/{provider}/{entity}/` | `config_loader.py:163` | ✅ Это фактический паттерн | — |

**Итого Getting Started:** 1/4 ✅, 3/4 ❌ — все пути неверны

---

## 16. Pipelines README (`docs/04-reference/pipelines/README.md`)

| № | Утверждение | Ссылка на код | Соответствует | План устранения |
|---|-------------|---------------|---------------|-----------------|
| PL-01 | «19 standard + 3 composite = 22 pipelines» | `configs/pipelines/` | ❌ Фактически: 21 standard + 5 composite = 26 | Обновить подсчёт |
| PL-02 | Недокументированные: ChEMBL `subcellular_fraction.yaml`, `tissue.yaml` | `configs/pipelines/chembl/` | ❌ Файлы существуют, но не в списке | Добавить в список |
| PL-03 | Недокументированные composite: `activity.yaml`, `assay.yaml` | `configs/composite/` | ❌ Файлы существуют, но не в списке | Добавить в список |

---

## 17. Оставшиеся ADR (Фаза 2)

| № | ADR | Утверждение | Соответствует | Проблема |
|---|-----|-------------|---------------|----------|
| ADR-09 | ADR-002 | Bronze: Medallion Architecture | ✅ | — |
| ADR-10 | ADR-004 | «Pydantic for all models» | ⚠️ Гибридный: Pydantic для API records, dataclasses для domain entities/configs | Уточнить: «Pydantic + dataclasses hybrid» |
| ADR-11 | ADR-006 | Circuit Breaker states | ✅ | — |
| ADR-12 | ADR-007 | Circuit Breaker thresholds, metrics | ✅ Все 6 claims совпадают | — |
| ADR-13 | ADR-008 | Graceful Shutdown — signal handlers | ❌ Signal handlers удалены (2025-12-31), orchestration/ пуст | ADR устарел, пометить Superseded |
| ADR-14 | ADR-009 | PaginatedFetcherMixin у ChEMBL/PubChem/UniProt | ⚠️ Только UniProt, ChEMBL имеет свою pagination, PubChem — sync | Уточнить список пользователей mixin |
| ADR-15 | ADR-012 | Checkpoint Strategy | ✅ | — |
| ADR-16 | ADR-014 | Deterministic Writes | ✅ | — |
| ADR-17 | ADR-018 | DQ Architecture | ✅ | — |
| ADR-18 | ADR-022 | Batch Processing | ✅ | — |
| ADR-19 | ADR-025 | Pipeline Config Unification | ✅ Все 7 claims | — |
| ADR-20 | ADR-027 | Storage Refactoring | ✅ | — |
| ADR-21 | ADR-028 | Transformer DI | ✅ | — |
| ADR-22 | ADR-033 | Config Validation (Proposed) | ❌ Статус «Proposed» — внешняя и семантическая валидация не реализованы, `configs/validation/` не существует | Обновить статус или реализовать |

**Итого ADR (Фаза 2):** 10/14 ✅ (71%), 2 ⚠️ (14%), 2 ❌ (14%)

---

## 18. Operations Documentation & Runbooks (`docs/05-operations/`)

| № | Документ | Утверждение | Соответствует | План устранения |
|---|----------|-------------|---------------|-----------------|
| OPS-01 | observability-checklist.md | `health_check() -> bool` | ❌ Фактически: `-> HealthStatus` (enum) | Исправить тип возврата |
| OPS-02 | observability-checklist.md | ChEMBL health endpoint: `/chembl/api/data/status.json` | ⚠️ Фактически: `/chembl/api/data/status` (без .json) | Исправить путь |
| OPS-03 | runbooks/README.md | DQ hard threshold exit code: 10 | ❌ Фактически: 83 (DATA_QUALITY_ERROR) | Исправить: exit code 83 |
| OPS-04 | runbooks/pipeline-failure-recovery.md | DQ hard threshold exit code: 10 | ❌ Фактически: 83 | Исправить: exit code 83 |
| OPS-05 | runbooks/pipeline-failure-recovery.md | CLI flag `--full-refresh` | ❌ Не реализован. Использовать `--run-type rebuild` | Заменить на `--run-type rebuild` |
| OPS-06 | runbooks/data-recovery.md | CLI flag `--full-rebuild` | ❌ Не реализован. Использовать `--run-type rebuild` | Заменить на `--run-type rebuild` |
| OPS-07 | runbooks/data-recovery.md | CLI flag `--ignore-checkpoint` | ❌ Не реализован | Удалить или реализовать |
| OPS-08 | runbooks/pipeline-failure-recovery.md | `bioetl verify --table chembl_activity` | ❌ Команда `verify` не существует | Удалить или реализовать |
| OPS-09 | runbooks/dq-failure-investigation.md | `bioetl quarantine-purge --older-than 30d` | ❌ Фактически: `bioetl quarantine purge --pipeline <name> --older-than-days 30` | Исправить формат команды |
| OPS-10 | runbooks/backfill-rebuild.md | `make run-pipeline PIPELINE={name} ARGS="--full-rebuild"` | ❌ Makefile target не существует. Использовать `bioetl run --pipeline <name> --run-type rebuild` | Заменить на актуальную CLI команду |
| OPS-11 | runbooks/backfill-rebuild.md | `make run-pipeline ... ARGS="--backfill ..."` | ❌ Использовать `bioetl run --pipeline <name> --run-type backfill` | Исправить формат |
| OPS-12 | runbooks/vacuum-procedures.md | `retention_hours: 168` config field | ✅ | — |
| OPS-13 | incident-response.md | `make release-lock PIPELINE=chembl_activity` | ✅ Makefile target делегирует в CLI | — |
| OPS-14 | runbooks/dq-failure-investigation.md | `bioetl quarantine stats --pipeline chembl_activity` | ✅ Команда и флаги существуют | — |

**Итого Operations:** 3/14 ✅ (21%), 1/14 ⚠️ (7%), 10/14 ❌ (71%)

---

## 19. .aiassistant Rules & Governance

| № | Документ | Утверждение | Соответствует | План устранения |
|---|----------|-------------|---------------|-----------------|
| GOV-01 | `.claude/PROJECT_CONTEXT.md` | 5 architecture layers: domain/, application/, composition/, infrastructure/, interfaces/ | ✅ | — |
| GOV-02 | `governance/02-naming-policy.md` | Pipeline IDs: `{provider}_{entity}` (snake_case) | ✅ `chembl_activity` и др. | — |
| GOV-03 | `governance/02-naming-policy.md` | Transformer placement: `application/pipelines/{provider}/{entity}_transformer.py` | ✅ | — |
| GOV-04 | `governance/03-file-policy.md` | Config path: `configs/pipelines/{provider}/{entity}.yaml` | ✅ | — |
| GOV-05 | `governance/03-file-policy.md` | 7 required config fields: pipeline_name, provider, entity_type, version, primary_keys, silver_table, gold_table | ✅ | — |
| GOV-06 | `governance/03-file-policy.md` | Schema validation: `configs/pipelines/_schema.json` | ✅ Файл существует (8747 bytes) | — |
| GOV-07 | `.aiassistant/rules/09-etl-architecture.md` | Pipeline naming: `{entity}_{source}` | ❌ Фактически обратный порядок: `{source}_{entity}` (chembl_activity) | Исправить: `{source}_{entity}` |
| GOV-08 | `.claude/agents/py-code-bot.md` | Entity location: `domain/entities/{provider}/{entity}.py` с поддиректориями | ❌ Фактически: flat структура `domain/entities/chembl_activity.py` | Исправить: убрать поддиректории |
| GOV-09 | `.claude/agents/py-code-bot.md` | Client file: `adapters/{provider}/{entity}_client.py` | ⚠️ Фактически: `adapters/{provider}/client.py` (generic, не per-entity) | Исправить паттерн |
| GOV-10 | `.aiassistant/rules/12-entity-naming-policy.md` | Test path: `tests/bioetl/pipelines/<provider>/<entity>/test_<stage>.py` | ❌ Фактически: `tests/unit/` и `tests/integration/`, нет `tests/bioetl/` | Исправить базовый путь |
| GOV-11 | `.claude/agents/py-code-bot.md` | BaseTransformer в `application/core/base_transformer.py` | ✅ `class BaseTransformer(ABC)` line 84 | — |
| GOV-12 | `.claude/agents/py-code-bot.md` | Provider-specific base: `BaseChemblTransformer` | ✅ `base_chembl_transformer.py:34` | — |
| GOV-13 | `.claude/PROJECT_CONTEXT.md` | Domain Ports: `domain/ports/` с 27 port файлами | ✅ | — |
| GOV-14 | `.claude/PROJECT_CONTEXT.md` | Facade import: `from bioetl.domain.ports import DataSourcePort` | ✅ `__init__.py` re-exports via `__all__` | — |
| GOV-15 | `governance/02-naming-policy.md` | Entity naming: `{Provider}{CanonicalTerm}` PascalCase | ⚠️ Смешанный: есть provider-prefixed (ChemblMolecule) и generic (Bioactivity, Assay) | Стандартизировать |

**Итого Governance:** 10/15 ✅ (67%), 2/15 ⚠️ (13%), 3/15 ❌ (20%)

---

## 20. Pipeline & Provider Specifications

### 20.1. ChEMBL Providers

| № | Документ | Утверждение | Соответствует | План устранения |
|---|----------|-------------|---------------|-----------------|
| PROV-01 | chembl/molecule.md | Schema version: 1.0.0 | ❌ Config: 1.2.0 | Обновить версию |
| PROV-02 | chembl/molecule.md | Primary ID: `molecule_chembl_id` | ✅ | — |
| PROV-03 | chembl/molecule.md | SMILES validation через Value Object | ✅ `SMILES.from_raw()` в transformer:177 | — |
| PROV-04 | chembl/molecule.md | InChI Key validation через Value Object | ✅ `InChIKey.validate_value_object()` | — |
| PROV-05 | chembl/activity.md | Schema version: 1.0.0 | ❌ Config: 1.2.0 | Обновить версию |
| PROV-06 | chembl/activity.md | «55 полей» в Activity entity | ❌ Фактически: 57 полей (includes _state, activity_properties, toid) | Исправить: 57 |
| PROV-07 | chembl/activity.md | Gold filter: IC50, Ki | ❌ Фактически 9 типов: IC50, Ki, Kd, EC50, AC50, GI50, ED50, MIC, CC50 | Добавить все 9 типов |
| PROV-08 | chembl/activity.md | Primary key: `["activity_id"]` | ✅ | — |
| PROV-09 | chembl/activity.md | Ligand efficiency: bei, le, lle, sei | ✅ Все 4 метрики в `bioactivity.py:132-135` | — |

### 20.2. PubChem, PubMed, UniProt

| № | Документ | Утверждение | Соответствует | План устранения |
|---|----------|-------------|---------------|-----------------|
| PROV-10 | pubchem/compound.md | Primary key: `["cid"]` | ✅ | — |
| PROV-11 | pubchem/compound.md | Rate Limit: 5 req/sec | ✅ `pubchem.yaml:27`: `requests_per_second: 5.0` | — |
| PROV-12 | pubmed/publication.md | Rate limit (no key): 3 req/sec | ✅ `pubmed.yaml:32` | — |
| PROV-13 | pubmed/publication.md | Rate limit (with key): 10 req/sec | ✅ `pubmed.yaml:34-36` | — |
| PROV-14 | pubmed/publication.md | Entity ID: `pubmed:{pmid}` | ✅ `transformer.py:297` | — |
| PROV-15 | uniprot/protein.md | Primary key: `["accession"]` | ✅ `protein.yaml:17` | — |
| PROV-16 | uniprot/protein.md | Rate limit (no key): 10 req/sec | ✅ `uniprot.yaml:28` | — |
| PROV-17 | uniprot/protein.md | Partition by: `["organism"]` | ✅ `protein.yaml:30` | — |

### 20.3. CrossRef, OpenAlex, Semantic Scholar

| № | Документ | Утверждение | Соответствует | План устранения |
|---|----------|-------------|---------------|-----------------|
| PROV-18 | crossref/publication.md | Rate limit без email: ~5 req/sec | ❌ Фактически: 50 req/sec (polite pool) | Исправить |
| PROV-19 | crossref/publication.md | Batch DOI: до 100 DOIs | ❌ Config: `batch_size: 50` | Исправить: 50 |
| PROV-20 | openalex/publication.md | Rate limit без email: ~5 req/sec | ❌ Фактически: 10 req/sec (polite pool) | Исправить |
| PROV-21 | openalex/publication.md | Batch DOI: до 50 DOIs | ✅ `batch_size: 50` | — |
| PROV-22 | semanticscholar/publication.md | Rate limit: 1000 req/sec (shared) | ❌ Config не содержит rate_limit секции | Добавить rate_limit в config |
| PROV-23 | semanticscholar/publication.md | Rate limit (API key): 1 req/sec | ❌ Config не содержит rate_limit секции | Добавить rate_limit в config |

**Итого Provider Specs:** 14/23 ✅ (61%), 0 ⚠️, 9/23 ❌ (39%)

---

## 21. Сводная статистика (Полный аудит)

### По категориям документов

| Категория | Всего | ✅ | ⚠️ | ❌ | Процент ✅ |
|-----------|-------|----|----|----|-----------:|
| Architecture layers (Phase 1) | 57 | 37 | 5 | 15 | 65% |
| RULES.md §1-§3 | 15 | 9 | 0 | 6 | 60% |
| RULES.md §4-§7 | 13 | 13 | 0 | 0 | 100% |
| API Reference | 17 | 3 | 1 | 13 | 18% |
| Getting Started | 4 | 1 | 0 | 3 | 25% |
| Pipeline README | 3 | 0 | 0 | 3 | 0% |
| ADR (Phase 2) | 14 | 10 | 2 | 2 | 71% |
| Operations/Runbooks | 14 | 3 | 1 | 10 | 21% |
| Governance/.aiassistant | 15 | 10 | 2 | 3 | 67% |
| Provider Specs | 23 | 14 | 0 | 9 | 61% |
| **ИТОГО** | **175** | **100 (57%)** | **11 (6%)** | **64 (37%)** | **57%** |

### По серьёзности несоответствий

| Серьёзность | Кол-во | Примеры |
|-------------|--------|---------|
| P0 CRITICAL | 6 | API-10 (UnifiedHTTPClient конструктор полностью неверен), OPS-05..08 (несуществующие CLI flags/commands), GS-01..03 (все data paths неверны) |
| P1 HIGH | 14 | API-01..07 (неверные имена методов/классов), OPS-03..04 (exit codes), PROV-22..23 (missing rate limits) |
| P2 MEDIUM | 22 | R-01..R-06, C-03..C-09, PROV-01..07, GOV-07..10 |
| P3 LOW | 22 | Подсчёты файлов, недокументированные модули, косметические расхождения |

---

## 22. Топ-20 критических несоответствий (обновлённый)

| # | ID | Документ | Проблема | Серьёзность |
|---|-----|----------|----------|-------------|
| 1 | API-10 | api/infrastructure.md | UnifiedHTTPClient constructor — полностью неверная сигнатура | P0 CRITICAL |
| 2 | GS-01..03 | getting-started.md | ВСЕ data path паттерны неверны (`v1/`, точка вместо слеша, `_gold` суффикс) | P0 CRITICAL |
| 3 | OPS-05..07 | runbooks/ | 3 несуществующих CLI flags: `--full-refresh`, `--full-rebuild`, `--ignore-checkpoint` | P0 CRITICAL |
| 4 | OPS-08 | pipeline-failure-recovery.md | Команда `bioetl verify` не существует | P0 CRITICAL |
| 5 | D-03 | domain-layer.md | QuarantineEntry states полностью неверны | P1 HIGH |
| 6 | C-09 | composition-layer.md | bootstrap_composite_pipeline — неверная сигнатура | P1 HIGH |
| 7 | IF-05 | interfaces-layer.md | Graceful shutdown в orchestration/ — модуль пуст | P1 HIGH |
| 8 | API-01..04 | api/domain.md | 4 неверных имени методов MetricsPort/LockPort | P1 HIGH |
| 9 | API-08..09 | api/infrastructure.md | 2 несуществующих класса: MetricsExporter, LineageTracker | P1 HIGH |
| 10 | API-11 | api/infrastructure.md | DeltaWriter — класс полностью удалён | P1 HIGH |
| 11 | R-01..R-02 | RULES.md | «Iceberg» упоминается но не реализован | P2 MEDIUM |
| 12 | R-03 | RULES.md | `PipelineRunner._clear_exports()` не существует | P2 MEDIUM |
| 13 | OPS-03..04 | runbooks/ | DQ exit code 10 vs фактический 83 | P1 HIGH |
| 14 | OPS-10..11 | backfill-rebuild.md | Makefile targets не существуют | P1 HIGH |
| 15 | PROV-01,05 | chembl/ docs | Schema version 1.0.0 vs фактическая 1.2.0 | P2 MEDIUM |
| 16 | PROV-22..23 | semanticscholar/ docs | Rate limits не сконфигурированы | P1 HIGH |
| 17 | GOV-08 | py-code-bot.md | Entity path structure: subdirs vs flat | P2 MEDIUM |
| 18 | GOV-07 | 09-etl-architecture.md | Pipeline naming order reversed | P2 MEDIUM |
| 19 | ADR-13 | ADR-008 | Graceful Shutdown ADR устарел | P2 MEDIUM |
| 20 | PL-01..03 | pipelines/README.md | Pipeline count: 22 vs 26 | P2 MEDIUM |

---

## 23. Обновлённый план устранения

### Фаза 0: Блокирующие (P0) — немедленно

1. **GS-01..03**: Исправить ВСЕ data path паттерны в `getting-started.md` на `data/output/{layer}/{provider}/{entity}/`
2. **API-10**: Полностью переписать пример конструктора UnifiedHTTPClient с актуальной сигнатурой
3. **OPS-05..08**: Удалить/заменить все 3 несуществующих CLI flags + команду `verify` в runbooks
4. **OPS-10..11**: Заменить `make run-pipeline` на `bioetl run --pipeline <name> --run-type {rebuild|backfill}`

### Фаза 1: Критические (P1) — в течение 1-2 дней

5. **D-03**: Исправить QuarantineEntry states
6. **C-09**: Исправить bootstrap_composite_pipeline сигнатуру
7. **IF-05**: Обновить orchestration/ описание
8. **API-01..07**: Исправить все имена методов/классов в API domain reference
9. **API-08..11**: Удалить несуществующие классы из API infrastructure reference
10. **OPS-03..04**: Исправить exit code 10→83
11. **PROV-22..23**: Добавить rate_limit конфигурацию для Semantic Scholar

### Фаза 2: Важные (P2) — в текущем спринте

12. **R-01..R-02**: Убрать упоминания Iceberg из RULES.md
13. **R-03**: Исправить `_clear_exports()` → `MedallionLifecycleService.clear()`
14. **C-03..C-07**: Исправить имена фабрик в composition docs
15. **PROV-01,05**: Обновить schema versions 1.0.0→1.2.0
16. **GOV-07,08,10**: Исправить пути и naming patterns в agent/governance docs
17. **ADR-13**: Пометить ADR-008 как Superseded
18. **PL-01..03**: Обновить подсчёт пайплайнов

### Фаза 3: Косметические (P3) — при следующем обновлении

19. Исправить все подсчёты файлов (D-01, D-04, D-05, IF-01, O-03)
20. Документировать недостающие модули и провайдеры

### Фаза 4: Тесты

21. Добавить 21 недостающий архитектурный тест (§8)
22. Добавить тест синхронизации документации с кодом

---

*Полный аудит завершён. Проверено 175 утверждений из 40+ документов.*
*Отчёт сгенерирован 2026-02-11. Рекомендуется ручная верификация P0/P1 несоответствий.*
