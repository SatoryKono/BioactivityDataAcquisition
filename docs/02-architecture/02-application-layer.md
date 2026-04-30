______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Слой Application (Приложение)

**Расположение:** `src/bioetl/application/`

## 1. Назначение

Слой `Application` является координатором. Он не содержит бизнес-логики (это задача `Domain`) и не взаимодействует напрямую с внешними системами (это задача `Infrastructure`). Вместо этого он оркестрирует поток данных, используя порты из `Domain` для выполнения операций.

Здесь реализуются **Use Cases** или, в нашей терминологии, **пайплайны**. Для композитных пайплайнов используются `CompositePipelineRunner` и `EnrichmentCoordinatorService`.

**Ключевые характеристики:**

- **Оркестрация:** Определяет *что* и *в каком порядке* делать. Например: "взять данные из `DataSourcePort`, преобразовать их и положить в `StoragePort`".
- **Зависимости:** Зависит от `Domain`, но не от `Infrastructure`. Зависимости из `Infrastructure` (конкретные адаптеры) внедряются в него через Dependency Injection.
- **Состояние:** Может управлять состоянием выполнения пайплайна (например, через `CheckpointPort`).

## 2. Ключевые Компоненты

### 2.1. `pipelines/` — Пайплайны

**Расположение:** `src/bioetl/application/pipelines/`

Здесь находится логика ETL-пайплайнов. Каждый пайплайн — это класс, который в конструкторе получает необходимые ему порты (адаптеры) и реализует основной метод `run()`.

Сборка пайплайнов и внедрение зависимостей происходит в слое [Composition](05-composition-layer.md).

**Примерный жизненный цикл пайплайна:**

1. **Инициализация:** Получает через конструктор `DataSourcePort`, `StoragePort`, `LockPort` и т.д.
1. **Захват блокировки:** Использует `LockPort`, чтобы убедиться, что другой экземпляр этого пайплайна не запущен.
1. **Загрузка чекпоинта:** Использует `CheckpointPort` для определения, с какого момента начинать загрузку данных.
1. **Извлечение (Extract):** Вызывает `DataSourcePort.fetch()` для получения сырых данных.
1. **Преобразование (Transform):** Применяет бизнес-логику из `Domain` для очистки и валидации данных.
1. **Загрузка (Load):** Использует `StoragePort` для записи данных в Bronze, Silver и Gold слои.
1. **Обновление чекпоинта:** Сохраняет новое состояние через `CheckpointPort`.
1. **Освобождение блокировки:** Снимает блокировку через `LockPort`.

### 2.2. `core/` — Базовые Абстракции

**Расположение:** `src/bioetl/application/core/`

Содержит базовые классы и общие компоненты, используемые пайплайнами. Документ intentionally описывает family-level topology вместо жёстких file counts, потому что `application/core/` активно развивается и сейчас включает несколько устойчивых подпакетов:

- `lifecycle/`
- `postrun/`
- `preflight/`
- `base_transformer/`
- `batch_execution/`
- `field_transforms/`
- `transformer_runtime/`

**Базовые классы:**

- **`BasePipeline`** (`base.py`) — Базовый класс для всех пайплайнов
- **`BaseTransformer`** (`base_transformer/base.py`) — Базовый класс для трансформеров (Template Method паттерн)
- **`RecordProcessor`** (`record_processor.py`) — Обработка batch-ов записей через Bronze→Silver→Gold

**Исполнение:**

- **`BatchExecutor`** (`batch_executor.py`) — Unified batch executor (extract→transform→write)
- **`BatchTransformer`** (`batch_transformer.py`) — Координация трансформаций
- **`BatchWriter`** (`batch_writer.py`) — Запись batch-ов в medallion слои
- **`PipelineRunner`** (`runner.py`) — Оркестрация жизненного цикла пайплайна

**Сервисы ядра:**

- **`PipelineService`** (`pipeline_services.py`) — Frozen DI bundle портов и optional DQ/metadata collaborators для pipeline execution и `PipelineRunner`
- **`LockCoordinator`** (`lifecycle/lock_manager.py`) — Координация блокировок
- **`PreflightService`** (`preflight/service.py`) — Pre-run health checks
- **`PostrunService`** (`postrun/service.py`) — Post-run операции (DQ, VACUUM, cleanup)
- **`CheckpointRuntimeService`** (`lifecycle/checkpoint_manager.py`) — runtime checkpoint I/O и resume policy
- **`QuarantineRuntimeService`** (`quarantine_manager.py`) — runtime quarantine write-path handling
- **`CleanupService`** (`lifecycle/cleanup_service.py`) — Bronze cleanup

**Observability:**

- **`BatchMetricsRecorderService`** (`batch_metrics.py`) — Метрики per batch
- **`BatchTracingManagerService`** (`batch_tracing.py`) — Tracing span management
- **`HeartbeatTask`** (`lifecycle/heartbeat.py`) — Heartbeat мониторинг

**Дополнительные application families:**

- **`application/observability/`** — application-level observability facade (`PipelineObserver`, lifecycle events, tracing helpers). Этот пакет описывает, какие execution events испускает application-слой, а concrete metrics/logging adapters остаются в infrastructure.
- **`application/services/dq/`** — DQ-oriented application services и orchestration seams, используемые postrun/preflight и quality workflows.

Checkpoint/quarantine naming is role-driven: runtime collaborators use
`*RuntimeService`, while operator/admin inspection surfaces use
`CheckpointService` and `QuarantineService` under `application/services/`.
Manager-style names such as `CheckpointManager`, `CheckpointManagerService`, `QuarantineManager`, and `QuarantineManagerService` are retired from first-party code.

**Data Sources:**

- **`FilteredDataSource`** (`filtered_data_source.py`) — Filter wrapper для data sources
- **`IDMappingDataSource`** (`idmapping_data_source.py`) — ID mapping wrapper

Подробнее о компонентах исполнения пайплайнов см. [раздел 2.4](#24-core--%D1%8F%D0%B4%D1%80%D0%BE-%D0%B8%D1%81%D0%BF%D0%BE%D0%BB%D0%BD%D0%B5%D0%BD%D0%B8%D1%8F-%D0%BF%D0%B0%D0%B9%D0%BF%D0%BB%D0%B0%D0%B9%D0%BD%D0%BE%D0%B2).

### 2.3. Трансформеры (Transformer DI)

**Расположение:** `src/bioetl/application/pipelines/{provider}/`

Трансформеры отвечают за преобразование Bronze → Silver. Они инжектируются в пайплайны через DI:

```python
# Пример инъекции трансформера в GenericPipelineFactory
factory = GenericPipelineFactory(
    pipeline_name="chembl_activity",
    pipeline_class=ChEMBLActivityPipeline,
    provider="chembl",
    transformer_class=ActivityTransformer,  # <-- DI
    gold_schema=ChEMBLActivityGoldSchema,
)
```

**Ключевые характеристики:**

- **MUST**: Трансформер передаётся в конструктор `BasePipeline` через параметр `transformer`
- **MUST NOT**: Пайплайн не создаёт трансформер внутри себя
- **Template Method**: `BaseTransformer` определяет скелет алгоритма, подклассы реализуют `transform_impl()`. Примечание: `extract_business_data()` — метод промежуточных базовых классов `BaseChemblTransformer` (`base_chembl_transformer.py:160`) и `BasePublicationTransformer` (`base_publication_transformer.py:54`), не `BaseTransformer`.
- **Explicit DI**: runtime collaborators трансформера (`TracingPort`, `MetricsPort`,
  `IdentityService`, `PiiHasherPort`, `DataNormalizationPort`, `ContractPolicyPort`)
  канонически собираются в composition и передаются как явный dependency bundle;
  прямое no-arg создание трансформеров допускается только как compatibility path.
- **Если трансформер не передан**: `transform_bronze_to_silver()` выбрасывает `NotImplementedError`

**Доступные трансформеры (23 класса):**

| Provider         | Трансформер                             | Расположение                                             |
| ---------------- | --------------------------------------- | -------------------------------------------------------- |
| ChEMBL           | `ActivityTransformer`                   | `pipelines/chembl/activity_transformer.py`               |
| ChEMBL           | `AssayTransformer`                      | `pipelines/chembl/assay_transformer.py`                  |
| ChEMBL           | `MoleculeTransformer`                   | `pipelines/chembl/molecule_transformer.py`               |
| ChEMBL           | `TargetTransformer`                     | `pipelines/chembl/target_transformer.py`                 |
| ChEMBL           | `PublicationTransformer`                | `pipelines/chembl/publication_transformer.py`            |
| ChEMBL           | `AssayParametersTransformer`            | `pipelines/chembl/assay_parameters_transformer.py`       |
| ChEMBL           | `CellLineTransformer`                   | `pipelines/chembl/cell_line_transformer.py`              |
| ChEMBL           | `CompoundRecordTransformer`             | `pipelines/chembl/compound_record_transformer.py`        |
| ChEMBL           | `ProteinClassTransformer`               | `pipelines/chembl/protein_class_transformer.py`          |
| ChEMBL           | `PublicationSimilarityTransformer`      | `pipelines/chembl/publication_similarity_transformer.py` |
| ChEMBL           | `PublicationTermTransformer`            | `pipelines/chembl/publication_term_transformer.py`       |
| ChEMBL           | `SubcellularFractionTransformer`        | `pipelines/chembl/subcellular_fraction_transformer.py`   |
| ChEMBL           | `TargetComponentTransformer`            | `pipelines/chembl/target_component_transformer.py`       |
| ChEMBL           | `TissueTransformer`                     | `pipelines/chembl/tissue_transformer.py`                 |
| ChEMBL           | `BaseChemblTransformer`                 | `pipelines/chembl/base_chembl_transformer.py`            |
| CrossRef         | `CrossRefPublicationTransformer`        | `pipelines/crossref/transformer.py`                      |
| OpenAlex         | `OpenAlexPublicationTransformer`        | `pipelines/openalex/transformer.py`                      |
| PubChem          | `PubChemCompoundTransformer`            | `pipelines/pubchem/transformer.py`                       |
| UniProt          | `UniProtProteinTransformer`             | `pipelines/uniprot/transformer.py`                       |
| UniProt          | `IDMappingTransformer`                  | `pipelines/uniprot/idmapping_transformer.py`             |
| PubMed           | `PubMedPublicationTransformer`          | `pipelines/pubmed/transformer.py`                        |
| Semantic Scholar | `SemanticScholarPublicationTransformer` | `pipelines/semanticscholar/transformer.py`               |
| Common           | `BasePublicationTransformer`            | `pipelines/common/base_publication_transformer.py`       |

### 2.4. `core/` — Ядро Исполнения Пайплайнов

**Расположение:** `src/bioetl/application/core/`

Содержит компоненты, отвечающие за *запуск*, *координацию* и *исполнение* пайплайнов.

**Ключевые компоненты:**

| Файл                                 | Компонент                   | Назначение                                                                         |
| ------------------------------------ | --------------------------- | ---------------------------------------------------------------------------------- |
| `runner.py`                          | `PipelineRunner`            | Оркестрирует жизненный цикл пайплайна: блокировки, чекпоинты, исполнение           |
| `batch_executor.py`                  | `BatchExecutor`             | Координирует data flow: извлечение → трансформация → запись                        |
| `../services/medallion_lifecycle.py` | `MedallionLifecycleService` | Управляет очисткой Silver/Gold слоёв по политике, VACUUM (`application/services/`) |
| `pipeline_services.py`               | `PipelineService`           | DI bundle сервисов для PipelineRunner                                              |

**`PipelineRunner`** — координатор исполнения:

- Делегирует блокировку через `LockCoordinator`
- Запускает preflight-валидацию через `PreflightService`
- Исполняет пайплайн через `BatchExecutor`
- Управляет postrun-операциями через `PostrunService`
- Оркестрирует очистку слоёв через `MedallionLifecycleService`

**`PipelineService`** — frozen dataclass, bundling зависимостей:

```python
@dataclass(frozen=True)
class PipelineService:
    data_source: DataSourcePort
    storage: StoragePort
    lock: LockPort
    checkpoint: CheckpointPort
    quarantine: QuarantinePort
    metrics: MetricsPort
    tracing: TracingPort
    logger: LoggerPort
    dq_monitor: DQMonitorPort | None = None
    bronze_dq_analyzer: BronzeDQAnalyzerPort | None = None
    silver_dq_analyzer: SilverDQAnalyzerPort | None = None
    gold_dq_analyzer: GoldDQAnalyzerPort | None = None
    dq_report_writer: DQReportWriterPort | None = None
    dq_report_service: DQReportService | None = None
```

### 2.5. `composite/` — Composite Pipeline (ADR-026)

**Расположение:** `src/bioetl/application/composite/`

Содержит компоненты для **композитных пайплайнов** — оркестрации нескольких пайплайнов для обогащения данных из разных источников. Основные классы — `CompositePipelineRunner` (оркестратор seed→enrich→merge) и `EnrichmentCoordinatorService` (параллельный fan-out enrichers).

Текущая composite-specific DQ/cross-validation semantics:

- `EnrichmentCrossValidator` валидирует enricher-поля относительно seed-данных до merge closeout;
- при `ENRICHER_ERROR` он nullify-ит enricher-prefixed columns и добавляет `_cv_*` metadata columns;
- эта семантика сейчас формализована как composite runtime behavior, а не как полностью унифицированный rule-provenance contract для всех DQ путей.

**Ключевые компоненты:**

| Файл/Пакет              | Компонент                      | Назначение                                                |
| ----------------------- | ------------------------------ | --------------------------------------------------------- |
| `runner_pkg/runner.py`  | `CompositePipelineRunner`      | Оркестрирует: seed → enrich (fan-out) → merge             |
| `coordinator.py`        | `EnrichmentCoordinatorService` | Параллельный запуск enrichers через asyncio.gather        |
| `merger.py`             | `MergeService`                 | Объединение данных из разных источников (LEFT OUTER JOIN) |
| `key_extractor.py`      | `KeyExtractorService`          | Извлечение join keys из seed pipeline                     |
| `checkpoint/service.py` | `CompositeCheckpointService`   | Resume после сбоя                                         |

**Workflow Composite Pipeline:**

```
Seed Pipeline → Extract Keys → [CrossRef, OpenAlex, PubMed, SemanticScholar] → Merge → Gold
                                     ↑ Fan-Out (parallel)
```

См. [ADR-026: Composite Pipeline Pattern](decisions/ADR-026-composite-pipeline-pattern.md) для деталей.

#### 2.5.1. Runner Mixin Decomposition (`runner_pkg/`)

`CompositePipelineRunner` декомпозирован на mixins для управления сложностью:

| Файл                               | Назначение                                    |
| ---------------------------------- | --------------------------------------------- |
| `runner.py`                        | Главный класс `CompositePipelineRunner`       |
| `runner_stage_mixin.py`            | Оркестрация seed/enrich/merge стадий          |
| `runner_stage_enrichment_mixin.py` | Fan-out enrichment stage                      |
| `runner_merge_stage_mixin.py`      | Merge stage orchestration                     |
| `runner_observability_mixin.py`    | Metrics и tracing для composite run           |
| `runner_support_mixin.py`          | Вспомогательные операции (config, validation) |
| `runner_stage_support_mixin.py`    | Поддержка отдельных стадий                    |
| `runner_helpers.py`                | Pure functions для runner                     |
| `runner_constants.py`              | Константы composite runner                    |

#### 2.5.2. Merger Mixin Decomposition

`MergeService` декомпозирован на mixins для разделения ответственностей:

| Файл                      | Назначение                                          |
| ------------------------- | --------------------------------------------------- |
| `merger.py`               | Главный `MergeService` (координация)                |
| `merger_collaborators.py` | Bundle collaborator-ов и legacy wiring bridge       |
| `merger_collaborators.py` | Bundle collaborator-ов и compatibility bridge       |
| `merger_input_mixin.py`   | Чтение и подготовка входных данных                  |
| `merger_io_mixin.py`      | I/O операции merge                                  |
| `merger_output_mixin.py`  | Формирование результата merge                       |
| `merger_metrics_mixin.py` | Метрики merge операций                              |
| `merger_orchestration.py` | Оркестрация merge workflow                          |
| `merger_post_join.py`     | Post-join обработка (conflict resolution, coalesce) |

Compatibility bridge и collaborator bundle для `MergeService` находятся в
`merger_collaborators.py`. `merger.py` остаётся facade/orchestration entrypoint,
а каноническое поведение реализуется в специализированных collaborator/service
модулях, перечисленных ниже.

#### 2.5.3. Column и Join Infrastructure

Каноническая бизнес-логика merge, извлечённая из MergeService:

**Column management:**

| Файл                         | Компонент               | Назначение                              |
| ---------------------------- | ----------------------- | --------------------------------------- |
| `column_service.py`          | `ColumnOrderService`    | Канонический порядок колонок и source-priority merge logic |
| `column_orderer.py`          | `ColumnOrderer`         | Deprecated compatibility alias for `ColumnOrderService` |
| `column_orderer_helpers.py`  | Helper functions        | Вспомогательные функции для ordering    |
| `column_priority_orderer.py` | `ColumnPriorityOrderer` | Deprecated compatibility surface for explicit priority ordering |
| `column_renamer.py`          | `ColumnRenamerService`  | Переименование колонок (suffix removal) |

**Join infrastructure:**

| Файл                             | Компонент                      | Назначение                              |
| -------------------------------- | ------------------------------ | --------------------------------------- |
| `join_planner.py`                | `JoinPlannerService`           | Планирование join операций              |
| `join_execution.py`              | `JoinExecutorService`          | Исполнение Polars join                  |
| `join_key_resolution.py`         | `JoinKeyResolverService`       | Разрешение join key columns             |
| `dependency_joiner.py`           | `DependencyJoinerService`      | Join по dependency edges                |
| `dependency_coordinator.py`      | `DependencyCoordinatorService` | Координация dependency joins            |
| `dependency_key_resolvers.py`    | Key resolver functions         | Разрешение ключей зависимостей          |
| `dependency_join_support.py`     | Support utilities              | Вспомогательные функции dependency join |
| `dependency_progress_tracker.py` | Progress tracking              | Отслеживание прогресса dependency joins |
| `dependency_result_mapper.py`    | Result mapping                 | Маппинг результатов dependency join     |

**Other composite services:**

| Файл                          | Компонент                 | Назначение                             |
| ----------------------------- | ------------------------- | -------------------------------------- |
| `conflict_resolver.py`        | `ConflictResolverService` | Разрешение конфликтов при merge        |
| `coalesce_policy.py`          | `CoalescePolicyService`   | Coalesce стратегии (prefer_seed и др.) |
| `aggregator.py`               | `EnricherAggregator`      | Агрегация результатов enrichers        |
| `cross_validator.py`          | `CrossValidatorService`   | Cross-validation merge результатов     |
| `deduplication.py`            | `DeduplicationService`    | Дедупликация записей                   |
| `coordinator_result_mixin.py` | Result mixin              | Формирование результата координатора   |
| `fsm_helper.py`               | `FSMStateHelper`          | Управление FSM состояниями             |

**Preflight validation:**

| Файл                          | Назначение                                |
| ----------------------------- | ----------------------------------------- |
| `_preflight_orchestration.py` | Оркестрация preflight проверок            |
| `_preflight_reporting.py`     | Формирование отчёта preflight             |
| `_preflight_rules.py`         | Правила валидации composite config        |
| `_preflight_types.py`         | Типы для preflight (результаты, severity) |

### 2.6. `services/` — Сервисы Уровня Приложения

**Расположение:** `src/bioetl/application/services/`

Содержит переиспользуемые сервисы уровня приложения (30+ файлов, включая подпакет `dq/`). В отличие от `core/`, компоненты `services/` предоставляют законченные бизнес-операции, не зависящие от конкретного пайплайна.

**CLI Orchestration и Pipeline Run:**

| Файл                                | Компонент                     | Назначение                                              |
| ----------------------------------- | ----------------------------- | ------------------------------------------------------- |
| `cli_run_orchestration_service.py`  | `CliRunOrchestrationService`  | Верхнеуровневая CLI-оркестрация запуска пайплайна       |
| `pipeline_runner_service.py`        | `PipelineRunnerService`       | Координация запуска пайплайна (preflight→exec→postrun)  |
| `pipeline_run_context_service.py`   | `PipelineRunContextService`   | Управление run context (run_id, config, logger binding) |
| `pipeline_run_execution_service.py` | `PipelineRunExecutionService` | Исполнение pipeline run (batch loop)                    |
| `pipeline_run_lifecycle_service.py` | `PipelineRunLifecycleService` | Lifecycle hooks (pre-run, post-run, cleanup)            |
| `pipeline_runner_models.py`         | Models                        | Модели результатов pipeline run                         |
| `pipeline_debug_service.py`         | `PipelineDebugService`        | Debug logging для pipeline execution                    |

**Metadata и Medallion Lifecycle:**

| Файл                             | Компонент                   | Назначение                                              |
| -------------------------------- | --------------------------- | ------------------------------------------------------- |
| `medallion_lifecycle.py`         | `MedallionLifecycleService` | Очистка Silver/Gold по политике (REBUILD/BACKFILL/INCR) |
| `medallion_maintenance_mixin.py` | Maintenance mixin           | VACUUM и maintenance операции                           |
| `medallion_types.py`             | Types                       | Типы для medallion lifecycle                            |
| `metadata_coordinator.py`        | `MetadataCoordinator`       | Координация сборки метаданных                           |
| `metadata_assemblers.py`         | Assembler functions         | Сборка Bronze/Silver/Gold метаданных                    |
| `metadata_assemblers_helpers.py` | Helper functions            | Вспомогательные функции для assemblers                  |

**Data Quality:**

| Файл                            | Компонент               | Назначение                                |
| ------------------------------- | ----------------------- | ----------------------------------------- |
| `data_quality_service.py`       | `DataQualityService`    | Оркестрация DQ-анализа Bronze/Silver/Gold |
| `dq_report_service.py`          | `DQReportService`       | Формирование и запись DQ-отчётов          |
| `dq_report_generation_mixin.py` | Report generation mixin | Генерация DQ-отчётов                      |
| `dq_report_models.py`           | Models                  | Модели DQ-отчётов                         |
| `dq/`                           | DQ subpackage           | Специализированные DQ-компоненты          |

**Other Services:**

| Файл                        | Компонент              | Назначение                                     |
| --------------------------- | ---------------------- | ---------------------------------------------- |
| `health_service.py`         | `HealthService`        | Агрегация health-статусов адаптеров и сервисов |
| `export_service.py`         | `ExportService`        | Экспорт Gold-данных в CSV/Parquet по запросу   |
| `export_models.py`          | Models                 | Модели для export операций                     |
| `config_service.py`         | `ConfigService`        | Загрузка и валидация конфигураций              |
| `metrics_service.py`        | `MetricsService`       | Управление метриками pipeline run              |
| `lock_service.py`           | `LockService`          | Оркестрация блокировок pipeline                |
| `checkpoint_service.py`     | `CheckpointService`    | Управление чекпоинтами                         |
| `quarantine_service.py`     | `QuarantineService`    | Обработка quarantine записей                   |
| `shutdown_service.py`       | `ShutdownService`      | Graceful shutdown                              |
| `bronze_cleanup_service.py` | `BronzeCleanupService` | Очистка Bronze данных                          |

Сервисы инжектируются через DI в `PipelineRunner` и `CompositeRunner` из слоя `composition/`.

## 3. Принципы Работы

- **Dependency Injection:** Пайплайны никогда не создают зависимости сами (`LocalStorage()`). Они получают уже созданные экземпляры адаптеров в конструкторе. Это делает их легко тестируемыми и гибкими.
- **Минимум логики:** Слой `Application` должен быть "тонким". Вся сложная бизнес-логика выносится в `Domain`, а детали реализации — в `Infrastructure`.
- **Управление транзакциями:** Этот слой отвечает за управление жизненным циклом операций, включая обработку ошибок, повторные попытки и откат в случае сбоя.

______________________________________________________________________

## 4. Связанные Материалы

### Навигация по Слоям

| ← Предыдущий                       | Текущий         | Следующий →                                        |
| ---------------------------------- | --------------- | -------------------------------------------------- |
| [Domain Layer](01-domain-layer.md) | **Application** | [Infrastructure Layer](03-infrastructure-layer.md) |

### Связанные Диаграммы

| Диаграмма                 | Файл                                                                                                     | Описание                                 |
| ------------------------- | -------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| Application Layer Classes | [06-application-layer-class-diagram.mermaid](diagrams/foundation/06-application-layer-class-diagram.mmd) | Классы слоя Application                  |
| Pipeline Execution        | [06-pipeline-execution.mermaid](diagrams/foundation/06-pipeline-execution.mmd)                           | Поток выполнения пайплайна               |
| Pipeline Hierarchy        | [17-pipeline-hierarchy.mermaid](diagrams/foundation/17-pipeline-hierarchy.mmd)                           | Иерархия Pipeline/Transformer            |
| Layers Interaction        | [05-layers-interaction.mermaid](diagrams/foundation/05-layers-interaction.mmd)                           | Взаимодействие слоёв (включая Composite) |
| Composite Pipeline        | [29-composite-pipeline-workflow.mermaid](diagrams/foundation/29-composite-pipeline-workflow.mmd)         | Workflow Composite Pipeline              |
| Pipeline Core             | [40-application-core-collaboration.mermaid](diagrams/foundation/40-application-core-collaboration.mmd)   | Ядро пайплайнов                          |
| BaseTransformer           | [09-transformers.mermaid](diagrams/class-diagrams/09-transformers.mmd)                                   | Template Method паттерн                  |

### Связанные ADR

| ADR                                                         | Тема                        |
| ----------------------------------------------------------- | --------------------------- |
| [ADR-015](decisions/ADR-015-pipeline-services-lifecycle.md) | Pipeline Services Lifecycle |
| [ADR-020](decisions/ADR-020-basepipeline-decomposition.md)  | BasePipeline Decomposition  |
| [ADR-026](decisions/ADR-026-composite-pipeline-pattern.md)  | Composite Pipeline Pattern  |

### Смежные Разделы Документации

- [Domain Layer](01-domain-layer.md) — порты, используемые Application
- [Composition Layer](05-composition-layer.md) — сборка и DI пайплайнов
- [API Reference: Application](../04-reference/api/application.md) — API документация слоя
- [RULES.md §1 "Архитектура и Слои"](../00-project/RULES.md) — матрица импортов
