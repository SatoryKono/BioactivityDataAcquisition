# TOP-50 Архитектурных Диаграмм BioETL

*Версия: 1.0 | Дата: 2026-01-20*

Таблица 50 наиболее важных диаграмм для понимания архитектуры, логики и кодовой базы проекта BioETL, отсортированных по приоритету.

**Методология приоритизации:**

- **Arch** (1-10): Архитектурная важность
- **Doc** (1-10): Документационная ценность
- **Freq** (1-10): Частота использования
- **Complex** (1-10): Сложность без диаграммы
- **Coverage** (1-10): Охват кодовой базы
- **Приоритет** = (Arch × 2 + Doc × 1.5 + Freq × 1.5 + Complex × 2 + Coverage × 1) / 8

______________________________________________________________________

## Структура файлов диаграмм

- Mermaid-исходники: `docs/02-architecture/diagrams/mermaid/`
- PNG-рендеры: `docs/02-architecture/diagrams/png/`
- Индекс диаграмм: [diagrams-index.md](diagrams-index.md)

## TOP-50 Диаграммы

| #      | Название                              | Тип        | Приоритет | Обоснование                                                                                                                                                                             | Классы/Компоненты                                                                                                                                             |
| ------ | ------------------------------------- | ---------- | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1**  | **Five Layer Architecture**           | Component  | **9.69**  | Фундаментальная диаграмма для понимания всей архитектуры. Критична для новых разработчиков. Показывает разделение на Domain, Application, Composition, Infrastructure, Interfaces слои. | `domain/*`, `application/*`, `composition/*`, `infrastructure/*`, `interfaces/*`                                                                              |
| **2**  | **Complete Pipeline Flow**            | Flowchart  | **9.56**  | End-to-end поток данных от API до Gold layer. Самая частая ссылка при обсуждении pipeline. Показывает полный цикл обработки.                                                            | `PipelineRunner`, `BatchExecutor`, `RecordProcessor`, `BatchTransformer`, `BatchWriter`, `BronzeWriter`, `SilverWriter`, `GoldWriter`                         |
| **3**  | **Hexagonal Architecture Overview**   | C4 Context | **9.50**  | Ports & Adapters — ключевой паттерн проекта. Критично для понимания принципов DI и слоёв.                                                                                               | 24 Ports (все Protocol интерфейсы), Infrastructure Adapters                                                                                                   |
| **4**  | **Layer Dependency Matrix**           | Matrix     | **9.44**  | Матрица импортов — enforcement правило. Предотвращает архитектурные нарушения. Часто проверяется при code review.                                                                       | Все слои проекта, `tests/architecture/test_layer_contracts.py`                                                                                                |
| **5**  | **Medallion Architecture Overview**   | Flowchart  | **9.38**  | Bronze → Silver → Gold — core концепция хранения данных. Критично для понимания data pipeline.                                                                                          | `BronzeWriter`, `SilverWriter`, `GoldWriter`, `MedallionLifecycleService`, `MedallionPolicy`                                                                  |
| **6**  | **Domain Model Overview**             | Class      | **9.31**  | Полная доменная модель: entities, value objects, aggregates. Показывает business logic структуру.                                                                                       | `PipelineRun`, `Batch`, `QuarantineEntry`, `Activity`, `DQMetrics`, `RunContext`, все entities                                                                |
| **7**  | **Ports Architecture**                | Interface  | **9.25**  | 24 порта — контракты между слоями. Критично для понимания DI и тестирования.                                                                                                            | `StoragePort`, `DataSourcePort`, `LockPort`, `CheckpointPort`, `QuarantinePort`, `TracingPort`, `MetricsPort`, `LoggerPort` и др. (всего 24)                  |
| **8**  | **Batch Processing Flow**             | Activity   | **9.19**  | Полный цикл обработки батча — core процесс pipeline. Сложный процесс с множеством шагов.                                                                                                | `Batch`, `RecordProcessor`, `BatchTransformer`, `BatchWriter`, `BatchMetricsRecorder`, `QuarantineManager`                                                    |
| **9**  | **DDD Aggregates**                    | Class      | **9.13**  | PipelineRun, Batch, QuarantineEntry — bounded contexts с инвариантами. Критично для понимания domain logic.                                                                             | `PipelineRun` (574 LOC), `Batch` (536 LOC), `QuarantineEntry` (517 LOC), `StageResult`, `BatchRecord`                                                         |
| **10** | **Pipeline Core Components**          | Component  | **9.06**  | PipelineRunner, BatchExecutor, RecordProcessor — сердце application layer. Самые частые изменения.                                                                                      | `PipelineRunner` (189 LOC), `BatchExecutor` (786 LOC), `RecordProcessor` (222 LOC), `RunnerServices`                                                          |
| **11** | **Composition Root**                  | Component  | **9.00**  | bootstrap_pipeline() — единственное место сборки DI. Критично для понимания wiring.                                                                                                     | `bootstrap_pipeline()`, `bootstrap_observability()`, `bootstrap_storage()`, `bootstrap_checkpoint()`, `bootstrap_quarantine()`                                |
| **12** | **Error Classification**              | Flowchart  | **8.94**  | Critical/Recoverable/DQ — основа error handling стратегии. Сложная логика с множеством условий.                                                                                         | `BioETLError`, `CriticalError`, `RecoverableError`, `DataQualityError`, `ErrorService`, `ErrorClassifier`                                                     |
| **13** | **Storage Architecture**              | Component  | **8.88**  | Bronze/Silver/Gold writers — core infrastructure. Сложная Delta Lake интеграция.                                                                                                        | `BronzeWriter` (814 LOC), `SilverWriter` (1154 LOC), `GoldWriter` (953 LOC), `BaseDeltaWriter`, `RetentionManager`                                            |
| **14** | **HTTP Infrastructure**               | Component  | **8.81**  | UnifiedHTTPClient — унифицированная HTTP инфраструктура для всех провайдеров.                                                                                                           | `UnifiedHTTPClient`, `RateLimiter`, `CircuitBreaker`, `HealthMonitor`, `Pagination`, `BaseHttpAdapter`                                                        |
| **15** | **Circuit Breaker States**            | State      | **8.75**  | Closed → Open → Half-Open — fault tolerance паттерн. Критично для resilience.                                                                                                           | `CircuitBreaker`, `CircuitBreakerPort`, state transitions                                                                                                     |
| **16** | **PipelineRun Aggregate**             | Class      | **8.69**  | Самый сложный aggregate с event sourcing. 574 LOC, множество state transitions.                                                                                                         | `PipelineRun` (574 LOC), `StageResult`, `PipelineState` enum, domain events                                                                                   |
| **17** | **Retry Mechanism**                   | Activity   | **8.63**  | Exponential backoff — критичная resilience логика. Сложный алгоритм с jitter.                                                                                                           | Retry logic в `UnifiedHTTPClient`, backoff calculation, jitter addition                                                                                       |
| **18** | **DQ Check Flow**                     | Sequence   | **8.56**  | Complete DQ process — критично для data quality. Сложный multi-stage процесс.                                                                                                           | `DQMonitorPort`, `BronzeDQAnalyzerPort`, `SilverDQAnalyzerPort`, `GoldDQAnalyzerPort`, `DQReportService`, `PostrunService`                                    |
| **19** | **BaseTransformer Template Method**   | Activity   | **8.50**  | Template Method pattern — base для всех transformers. Критично для понимания extension points.                                                                                          | `BaseTransformer` (821 LOC), hook methods: `transform_entity()`, `validate_input()`, `validate_output()`                                                      |
| **20** | **Factory Pattern Usage**             | Class      | **8.44**  | 8 фабрик — object creation strategy. Сложная система зависимостей.                                                                                                                      | `PipelineFactory`, `RunnerFactory`, `ServicesFactory`, `StorageFactory`, `HTTPClientFactory`, `DataSourceFactory`, `TransformerFactory`, `DQFactory`          |
| **21** | **Lock Acquisition Flow**             | Sequence   | **8.38**  | acquire() → heartbeat → release() — distributed locking. Критично для concurrency.                                                                                                      | `LockManager`, `MemoryLock`, `LockPort`, `Heartbeat`, TTL checker                                                                                             |
| **22** | **Silver Merge Operation**            | Sequence   | **8.31**  | Delta merge by content_hash — ACID операция. Сложная Delta Lake логика.                                                                                                                 | `SilverWriter` (1154 LOC), Delta merge, content_hash deduplication, ACID transaction                                                                          |
| **23** | **Provider Adapters Overview**        | Component  | **8.25**  | 7 провайдеров — все data sources. Критично для понимания integration layer.                                                                                                             | `ChemblAdapter`, `PubChemAdapter`, `UniProtAdapter`, `CrossRefAdapter`, `OpenAlexAdapter`, `PubMedAdapter`, `SemanticScholarAdapter`                          |
| **24** | **Graceful Shutdown**                 | Sequence   | **8.19**  | SIGTERM → Cleanup → Exit — критично для production. Сложная координация ресурсов.                                                                                                       | `Shutdown`, `ShutdownPort`, `PipelineRunner.shutdown()`, checkpoint save, lock release, `aclose()` cascade                                                    |
| **25** | **PipelineConfig Structure**          | Class      | **8.13**  | Complete pipeline configuration — core для всех pipelines. 100+ поля.                                                                                                                   | `PipelineConfig` (969 LOC), `ValidationConfig`, `DQConfig`, `TableConfig`, nested structures                                                                  |
| **26** | **Dependency Injection Flow**         | Sequence   | **8.06**  | Как собираются зависимости через конструкторы. Критично для DI понимания.                                                                                                               | Composition Root → Factories → Constructor injection chain                                                                                                    |
| **27** | **Bronze Write Operation**            | Sequence   | **8.00**  | JSONL append with metadata — Bronze layer механика. Часто используется.                                                                                                                 | `BronzeWriter` (814 LOC), JSONL format, zstd compression, metadata YAML                                                                                       |
| **28** | **Batch Aggregate**                   | Class      | **7.94**  | Batch aggregate — второй по сложности aggregate. 536 LOC, state machine.                                                                                                                | `Batch` (536 LOC), `BatchRecord`, `BatchState` enum, quarantine logic                                                                                         |
| **29** | **Rate Limiting**                     | Activity   | **7.88**  | Token bucket algorithm — критично для API compliance. Сложная математика.                                                                                                               | `RateLimiter`, `RateLimiterPort`, token bucket, provider-specific limits                                                                                      |
| **30** | **ChEMBL Adapter Architecture**       | Component  | **7.81**  | Самый большой адаптер — 13 pipelines. Критично для ChEMBL integration.                                                                                                                  | `ChemblAdapter` (1170 LOC), `ChemblEntityMapper`, `CHEMBL_DTO_MODELS`, 13 entity types                                                                        |
| **31** | **Pipeline Lifecycle**                | State      | **7.75**  | PENDING → RUNNING → COMPLETED/FAILED — pipeline states. Часто используется.                                                                                                             | `PipelineRun` states, `PipelineRunner` lifecycle, state transitions                                                                                           |
| **32** | **DQ Report Generation**              | Sequence   | **7.69**  | Report creation — критично для DQ visibility. Сложный aggregation процесс.                                                                                                              | `DQReportService`, `DQReportWriterPort`, `DQReport` VO, Bronze/Silver/Gold analyzers                                                                          |
| **33** | **Gold SCD2 Write**                   | Sequence   | **7.63**  | Slowly Changing Dimension Type 2 — сложная аналитическая логика.                                                                                                                        | `GoldWriter` (953 LOC), SCD2 mode, `valid_from`/`valid_to` timestamps                                                                                         |
| **34** | **Observability Integration**         | Component  | **7.56**  | PipelineObserver — cross-cutting concerns. Tracing + Metrics + Logging.                                                                                                                 | `PipelineObserver`, `TracingPort`, `MetricsPort`, `LoggerPort`, span hierarchy                                                                                |
| **35** | **System Context Diagram**            | C4 Context | **7.50**  | BioETL в контексте внешних систем — big picture.                                                                                                                                        | BioETL System, 7 external providers (ChEMBL, PubChem, UniProt, CrossRef, OpenAlex, PubMed, SemanticScholar), Local Storage                                    |
| **36** | **Domain Services**                   | Component  | **7.44**  | Stateless domain logic — часто путают с application services.                                                                                                                           | `DataNormalizationService`, `IdentityService`, `UnitConverter`, `ActivityAggregator`, `ValueValidator`, `DQSerializer`                                        |
| **37** | **Checkpoint Lifecycle**              | State      | **7.38**  | Create → Update → Load — state persistence. Критично для incremental runs.                                                                                                              | `CheckpointManager`, `CheckpointPort`, `CheckpointAdapter`, checkpoint JSON schema                                                                            |
| **38** | **Entity Mapping**                    | Activity   | **7.31**  | DTO → Domain Entity — часто выполняется. Критично для transformation.                                                                                                                   | Entity mappers для всех провайдеров, DTO models, domain entities                                                                                              |
| **39** | **Gold Write Flow**                   | Sequence   | **7.25**  | Filter → Validate → Delta Write — Gold layer механика.                                                                                                                                  | `GoldWriter` (953 LOC), JSON filtering, strict validation, Delta write modes                                                                                  |
| **40** | **Preflight Checklist**               | Activity   | **7.19**  | Pre-run infrastructure validation — предотвращает ошибки.                                                                                                                               | `PreflightService` (816 LOC), health checks, storage validation, lock availability                                                                            |
| **41** | **Pipeline Services Bundle**          | Component  | **7.13**  | PipelineServices — injected dependencies. Критично для понимания dependencies.                                                                                                          | `PipelineServices` (152 LOC): `data_source`, `storage`, `lock`, `checkpoint`, `quarantine`, `metrics`, `logger`, `tracer`                                     |
| **42** | **Value Objects Hierarchy**           | Class      | **7.06**  | Все value objects — immutable domain concepts. Часто используются.                                                                                                                      | `Activity`, `ActivityValues`, `DQMetrics`, `DQResult`, `DQReport`, `SilverResult`, `BronzeResult`, `RunContext`, `CompoundIds`, `TaxonomyId`, `Identifiers`   |
| **43** | **Incremental Run Flow**              | Flowchart  | **7.00**  | Resume from checkpoint — самый частый run type.                                                                                                                                         | `RuntimeConfig.run_type=incremental`, `CheckpointManager.load()`, resume logic                                                                                |
| **44** | **Configuration Loading Flow**        | Sequence   | **6.94**  | YAML → PipelineConfig — критично для pipeline setup.                                                                                                                                    | `ConfigLoader`, YAML parsing, `PipelineConfig` construction, validation                                                                                       |
| **45** | **Memory Monitor Lifecycle**          | Sequence   | **6.88**  | Adaptive batch sizing — critical для production stability.                                                                                                                              | `MemoryMonitor` (310 LOC), `MemoryMonitorPort`, batch size adaptation, memory stats                                                                           |
| **46** | **Quarantine Handling**               | Activity   | **6.81**  | Failed record isolation — критично для data quality.                                                                                                                                    | `QuarantineManager`, `QuarantinePort`, `QuarantineAdapter`, `QuarantineEntry` aggregate                                                                       |
| **47** | **CLI Flow**                          | Flowchart  | **6.75**  | User input → execution — entry point. Критично для user experience.                                                                                                                     | `cli/main.py`, `cli/commands/*`, 11+ commands, Click CLI routing                                                                                              |
| **48** | **Data Normalization**                | Activity   | **6.69**  | Text/Value/ID normalization — часто выполняется.                                                                                                                                        | `DataNormalizationService`, `IdentityService`, `UnitConverter`, normalization algorithms                                                                      |
| **49** | **Schema Validation Flow**            | Sequence   | **6.63**  | Pandera validation — критично для data integrity.                                                                                                                                       | Pandera schemas для всех entities, validation logic, schema enforcement                                                                                       |
| **50** | **Architecture Decision Records Map** | Mind Map   | **6.56**  | 27 ADR и их связи — architecture rationale. Критично для понимания "why".                                                                                                               | ADR-001 (Delta Lake), ADR-007 (Circuit Breaker), ADR-008 (Graceful Shutdown), ADR-020 (BasePipeline Decomposition), ADR-021 (DDD Aggregates) и др. (27 total) |

______________________________________________________________________

## Статистика по Категориям

| Категория                   | Количество в TOP-50 |
| --------------------------- | ------------------- |
| Архитектурные Обзоры        | 12                  |
| Потоки Данных               | 10                  |
| Паттерны и Механизмы        | 14                  |
| Компонентные Диаграммы      | 8                   |
| Взаимодействия              | 4                   |
| Состояния и Жизненные Циклы | 2                   |

______________________________________________________________________

## TOP-25 для Создания (Приоритет ≥ 7.75)

Первые 25 диаграмм из списка выше будут созданы в формате Mermaid и отрендерены в PNG:

1. Five Layer Architecture (9.69)
1. Complete Pipeline Flow (9.56)
1. Hexagonal Architecture Overview (9.50)
1. Layer Dependency Matrix (9.44)
1. Medallion Architecture Overview (9.38)
1. Domain Model Overview (9.31)
1. Ports Architecture (9.25)
1. Batch Processing Flow (9.19)
1. DDD Aggregates (9.13)
1. Pipeline Core Components (9.06)
1. Composition Root (9.00)
1. Error Classification (8.94)
1. Storage Architecture (8.88)
1. HTTP Infrastructure (8.81)
1. Circuit Breaker States (8.75)
1. PipelineRun Aggregate (8.69)
1. Retry Mechanism (8.63)
1. DQ Check Flow (8.56)
1. BaseTransformer Template Method (8.50)
1. Factory Pattern Usage (8.44)
1. Lock Acquisition Flow (8.38)
1. Silver Merge Operation (8.31)
1. Provider Adapters Overview (8.25)
1. Graceful Shutdown (8.19)
1. PipelineConfig Structure (8.13)

______________________________________________________________________

*Следующий шаг: Создание Mermaid диаграмм для TOP-25*

## Definition of Done (для каждой диаграммы)

- [ ] Есть `.mermaid` файл в `diagrams/mermaid/`.
- [ ] Есть `.png` файл в `diagrams/png/`.
- [ ] Есть ссылка в `diagrams-index.md`.
- [ ] Есть контекстный абзац и ссылка в одной из страниц `docs/02-architecture/*.md`.
