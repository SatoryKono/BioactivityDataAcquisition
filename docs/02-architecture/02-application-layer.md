______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# Слой Application (Приложение)

**Расположение:** `src/bioetl/application/`

## 1. Назначение

Слой `Application` является координатором. Он не содержит бизнес-логики (это задача `Domain`) и не взаимодействует напрямую с внешними системами (это задача `Infrastructure`). Вместо этого он оркестрирует поток данных, используя порты из `Domain` для выполнения операций.

Здесь реализуются **Use Cases** или, в нашей терминологии, **пайплайны**. Для композитных пайплайнов используются `CompositePipelineRunner` и `EnrichmentCoordinatorService`.

**Ключевые характеристики:**

- **Оркестрация:** Определяет *что* и *в каком порядке* делать. Например: "взять данные из `DataSourcePort`, преобразовать их и положить через storage ports (`BronzeStoragePort`/`SilverStoragePort`/`GoldStoragePort`)".
- **Зависимости:** Зависит от `Domain`, но не от `Infrastructure`. Зависимости из `Infrastructure` (конкретные адаптеры) внедряются в него через Dependency Injection.
- **Состояние:** Может управлять состоянием выполнения пайплайна (например, через `CheckpointPort`).

## 2. Ключевые Компоненты

### 2.1. `pipelines/` — Пайплайны

**Расположение:** `src/bioetl/application/pipelines/`

Здесь находится логика ETL-пайплайнов. Каждый пайплайн — это класс, который в конструкторе получает необходимые ему порты (адаптеры) и реализует основной метод `run()`.

Сборка пайплайнов и внедрение зависимостей происходит в слое [Composition](05-composition-layer.md).

**Примерный жизненный цикл пайплайна:**

1. **Инициализация:** Получает через конструктор `DataSourcePort`, storage ports (`BronzeStoragePort`/`SilverStoragePort`/`GoldStoragePort`), `LockPort` и т.д.
1. **Захват блокировки:** Использует `LockPort`, чтобы убедиться, что другой экземпляр этого пайплайна не запущен.
1. **Загрузка чекпоинта:** Использует `CheckpointPort` для определения, с какого момента начинать загрузку данных.
1. **Извлечение (Extract):** Вызывает `DataSourcePort.fetch()` для получения сырых данных.
1. **Преобразование (Transform):** Применяет бизнес-логику из `Domain` для очистки и валидации данных.
1. **Загрузка (Load):** Использует application-owned aggregate protocol
   `PipelineStorageProtocol`, который объединяет narrow domain storage ports
   (`BronzeStoragePort`/`SilverStoragePort`/`GoldStoragePort`/
   `MergedStoragePort`) для записи данных в medallion слои.
1. **Обновление чекпоинта:** Сохраняет новое состояние через `CheckpointPort`.
1. **Освобождение блокировки:** Снимает блокировку через `LockPort`.

### 2.2. `core/` — Базовые Абстракции

**Расположение:** `src/bioetl/application/core/`

Содержит базовые классы и общие компоненты, используемые пайплайнами. В
`application/core/` сосуществуют корневые orchestration-модули и вынесенные
подпакеты: корневые модули остаются реальными implementation/entrypoint
модулями, а подпакеты группируют lifecycle, execution и helper-логику.
Документ описывает эту family-level topology вместо жёстких file counts:

- `lifecycle/` — Runtime lifecycle management (locks, checkpoints, cleanup, heartbeat)
- `postrun/` — Post-run operations (DQ, VACUUM, cleanup, reporting)
- `preflight/` — Pre-run health checks and validation
- `base_transformer/` — Base transformer implementation and templates
- `batch_execution/` — Batch execution coordination and flow
- `data_sources/` — Data source management and adapters
- `field_transforms/` — Field-level transformation utilities
- `transformer_runtime/` — Transformer runtime coordination
- `wiring/` — Composition-facing assembly и typed runtime exports

**Базовые классы:**

- **`BasePipeline`** (`base.py`) — Базовый класс для всех пайплайнов
- **`BaseTransformer`** (`base_transformer/base.py`) — Базовый класс для трансформеров (Template Method паттерн)
- **`RecordProcessor`** (`record_processor.py`) — Отдельный действующий
  orchestrator Bronze→Silver→Gold, экспортируемый через `wiring/runtime.py` и
  используемый composition builder-ом
- **`BatchProcessingService`** (`batch_processing_service.py`) — Основной
  processing service для extract/transform/write одного batch-а; реализует
  processing port, который получает `BatchExecutor`

**Исполнение:**

- **`BatchExecutor`** (`batch_executor.py`) — Unified batch executor;
  делегирует lifecycle/state helper-ам из `batch_execution/` и processing port-у
- **`BatchTransformer`** (`batch_transformer.py`) — Корневой orchestrator
  трансформаций с helper-логикой в `transformer_runtime/`
- **`BatchWriter`** (`batch_writer.py`) — Корневой orchestrator записи с
  специализированными `batch_writer_*_mixin.py` и support-модулями
- **`PipelineRunner`** (`runner.py`) — Оркестрация жизненного цикла пайплайна

**Сервисы ядра:**

- **`PipelineService`** (`pipeline_services.py`) — Frozen DI bundle портов и optional DQ/metadata collaborators для pipeline execution и `PipelineRunner`
- **`LockRuntimeService`** (`lifecycle/lock_runtime_service.py`) — runtime-координация блокировок
- **`PreflightService`** (`preflight/service.py`) — Pre-run health checks
- **`PostrunService`** (`postrun/service.py`) — Post-run операции (DQ, VACUUM, cleanup)
- **`CheckpointRuntimeService`** (`lifecycle/checkpoint_runtime.py`) — runtime checkpoint I/O и resume policy
- **`QuarantineRuntimeService`** — runtime quarantine write-path handling (implemented via support modules in lifecycle/)
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
  `EntityIdentityGenerator`, `PiiHasherPort`, `DataNormalizationPort`, `ContractPolicyPort`)
  канонически собираются в composition и передаются как явный dependency bundle;
  прямое no-arg создание трансформеров допускается только как compatibility path.
- **Если трансформер не передан**: `transform_bronze_to_silver()` выбрасывает `NotImplementedError`

**Доступные трансформеры и базовые transformer foundations (24 класса):**

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
| ChEMBL           | `TargetProteinClassificationTransformer` | `pipelines/chembl/target_protein_classification_transformer.py` |
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

| Файл/пакет                           | Компонент                   | Назначение                                                                         |
| ------------------------------------ | --------------------------- | ---------------------------------------------------------------------------------- |
| `runner.py`                          | `PipelineRunner`            | Оркестрирует жизненный цикл пайплайна: блокировки, чекпоинты, исполнение           |
| `batch_executor.py`                  | `BatchExecutor`             | Координирует batch data flow через injected processing port                       |
| `batch_execution/`                   | Execution services/contracts | Lifecycle, run и state helpers для `BatchExecutor`                                 |
| `batch_processing_service.py`        | `BatchProcessingService`    | Выполняет extract→transform→Bronze/Silver/Gold write для batch-а                   |
| `batch_transformer.py`               | `BatchTransformer`          | Координирует Bronze→Silver/Gold transformation                                     |
| `batch_writer.py`                    | `BatchWriter`               | Координирует запись batch-а в medallion layers                                     |
| `record_processor.py`                | `RecordProcessor`           | Действующий explicit batch orchestrator для отдельного composition route          |
| `../services/medallion/medallion_lifecycle.py` | `MedallionLifecycleService` | Управляет очисткой Silver/Gold слоёв по политике, VACUUM (`application/services/`) |
| `pipeline_services.py`               | `PipelineService`           | DI bundle сервисов для `PipelineRunner`                                            |

**`PipelineRunner`** — координатор исполнения:

- Делегирует блокировку через `LockRuntimeService`
- Запускает preflight-валидацию через `PreflightService`
- Исполняет пайплайн через `BatchExecutor`
- Управляет postrun-операциями через `PostrunService`
- Оркестрирует очистку слоёв через `MedallionLifecycleService`

**`PipelineService`** — frozen dataclass, bundling зависимостей:

```python
@dataclass(frozen=True)
class PipelineService:
    data_source: DataSourcePort
    # Application-owned aggregate protocol from
    # application/core/pipeline_runtime_service_protocols.py.
    storage: PipelineStorageProtocol
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
| `merge_service.py`      | `MergeService`                 | Объединение данных из разных источников (LEFT OUTER JOIN) |
| `merger.py`             | Compatibility facade           | Стабильный import entrypoint для `MergeService`            |
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

| Файл                               | Класс                                      | Назначение                                    |
| ---------------------------------- | ------------------------------------------ | --------------------------------------------- |
| `runner.py`                        | `CompositePipelineRunner`                  | Главный composite runner                      |
| `runner_control_plane_mixin.py`    | `CompositeRunnerControlPlaneMixin`         | Run ledger/manifest и phase completion        |
| `runner_stage_mixin.py`            | `CompositeRunnerStageMixin`                | Композиция seed/dependency/enrich/merge стадий |
| `runner_stage_enrichment_mixin.py` | `_CompositeRunnerStageEnrichmentMixin`     | Fan-out enrichment stage                      |
| `runner_merge_stage_mixin.py`      | `CompositeRunnerMergeStageMixin`           | Merge stage orchestration                     |
| `runner_observability_mixin.py`    | `CompositeRunnerObservabilityMixin`        | Metrics и tracing для composite run           |
| `runner_support_mixin.py`          | `CompositeRunnerSupportMixin`              | Вспомогательные операции (config, validation) |
| `runner_stage_support_mixin.py`    | `_CompositeRunnerStageSupportMixin`        | Поддержка отдельных стадий                    |
| `runner_helpers.py`                | Helper functions                           | Pure functions для runner                     |
| `runner_constants.py`              | Constants                                  | Константы composite runner                    |

#### 2.5.2. Merger Mixin Decomposition

`MergeService` декомпозирован на mixins для разделения ответственностей:

| Файл                      | Класс/роль                   | Назначение                                          |
| ------------------------- | ---------------------------- | --------------------------------------------------- |
| `merge_service.py`        | `MergeService`               | Главная реализация и координация                    |
| `merger.py`               | Compatibility facade         | Стабильный import entrypoint                        |
| `merger_collaborators.py` | `MergeCollaboratorGroup`     | Bundle collaborator-ов и compatibility bridge       |
| `merger_input_mixin.py`   | `_MergeInputLoaderMixin`     | Чтение и подготовка входных данных                  |
| `merger_io_mixin.py`      | `MergeIOMixin`               | I/O и cross-validation workflow                     |
| `merger_output_mixin.py`  | `MergeOutputWriterMixin`     | Формирование и запись результата merge              |
| `merger_metrics_mixin.py` | `MergeMetricsRecorderMixin`  | Метрики merge операций                              |
| `merger_orchestration.py` | Orchestration functions      | Оркестрация merge workflow                          |
| `merger_post_join.py`     | Post-join functions          | Post-join обработка (conflict resolution, coalesce) |

Compatibility bridge и collaborator bundle для `MergeService` находятся в
`merger_collaborators.py`. `merger.py` остаётся compatibility import facade, а
реализация `MergeService` и каноническое поведение находятся в
`merge_service.py` и специализированных collaborator/service модулях,
перечисленных ниже.

#### 2.5.3. Column и Join Infrastructure

Каноническая бизнес-логика merge, извлечённая из MergeService:

**Column management:**

| Файл                         | Компонент               | Назначение                              |
| ---------------------------- | ----------------------- | --------------------------------------- |
| `column_service.py`          | `ColumnOrderService`    | Канонический порядок колонок и source-priority merge logic |
| `column_orderer_group_flow.py` | Group-flow functions   | Группировка и ordering flow             |
| `column_orderer_semantic.py` | Semantic functions      | Semantic ordering helpers               |
| `column_priority_orderer.py` | Priority helper functions | Explicit priority ordering            |
| `column_service_priority.py` | Priority service helpers | Source-priority merge helpers          |
| `column_service_support.py`  | Support functions       | Общие helpers для `ColumnOrderService`  |
| `column_renamer.py`          | `ColumnRenamer`         | Переименование колонок (suffix removal) |

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
| `cross_validator.py`          | `EnrichmentCrossValidator` | Cross-validation merge результатов    |
| `deduplication.py`            | `EnricherDeduplicatorService` | Дедупликация записей               |
| `coordinator_result_mixin.py` | Result mixin              | Формирование результата координатора   |
| `fsm_helper.py`               | `FSMStateHelperService`   | Управление FSM состояниями             |

**Preflight validation:**

| Файл                          | Назначение                                |
| ----------------------------- | ----------------------------------------- |
| `_preflight_orchestration.py` | Оркестрация preflight проверок            |
| `_preflight_reporting.py`     | Формирование отчёта preflight             |
| `_preflight_field_priority.py` | Правила field-priority валидации         |
| `_preflight_types.py`         | Типы для preflight (результаты, severity) |
| `preflight_validator.py`      | `CompositePreflightValidationService`     |

### 2.6. `services/` — Сервисы Уровня Приложения

**Расположение:** `src/bioetl/application/services/`

Содержит переиспользуемые сервисы уровня приложения, сгруппированные по
назначению в подпакетах `execution/`, `medallion/`, `lineage/`, `quality/`,
`dq/`, `ops/`, `checkpoint/`, `export_lineage/`, `control_plane/`, `workflow/`
и других узких families. В отличие от `core/`, компоненты `services/`
предоставляют законченные application operations, не зависящие от конкретного
пайплайна.

**CLI Orchestration и Pipeline Run:**

| Файл                                | Компонент                     | Назначение                                              |
| ----------------------------------- | ----------------------------- | ------------------------------------------------------- |
| `execution/cli_run_orchestration_service.py` | `CliRunOrchestrationService` | Верхнеуровневая CLI-оркестрация запуска пайплайна       |
| `execution/pipeline_runner_service.py` | `PipelineRunnerService`    | Координация запуска пайплайна (preflight→exec→postrun)  |
| `execution/pipeline_run_context_service.py`   | `PipelineRunContextService`   | Управление run context (run_id, config, logger binding) |
| `execution/pipeline_run_execution_service.py` | `PipelineRunExecutionService` | Исполнение pipeline run (batch loop)                    |
| `execution/pipeline_run_lifecycle_service.py` | `PipelineRunLifecycleService` | Lifecycle hooks (pre-run, post-run, cleanup)            |
| `execution/pipeline_runner_models.py`         | Models                        | Модели результатов pipeline run                         |
| `export_lineage/pipeline_debug_service.py`    | `PipelineDebugService`        | Debug logging для pipeline execution                    |

**Metadata и Medallion Lifecycle:**

| Файл                             | Компонент                   | Назначение                                              |
| -------------------------------- | --------------------------- | ------------------------------------------------------- |
| `medallion/medallion_lifecycle.py`         | `MedallionLifecycleService` | Очистка Silver/Gold по политике (REBUILD/BACKFILL/INCR) |
| `medallion/medallion_maintenance_mixin.py` | Maintenance mixin           | VACUUM и maintenance операции                           |
| `medallion/medallion_types.py`             | Types                       | Типы для medallion lifecycle                            |
| `lineage/metadata_coordinator.py`           | `MetadataCoordinator`       | Координация сборки метаданных                           |
| `lineage/metadata_assemblers.py`            | Assembler functions         | Сборка Bronze/Silver/Gold метаданных                    |
| `lineage/metadata_assemblers_helpers.py`    | Helper functions            | Вспомогательные функции для assemblers                  |

**Data Quality:**

| Файл                            | Компонент               | Назначение                                |
| ------------------------------- | ----------------------- | ----------------------------------------- |
| `quality/data_quality_service.py`       | `DataQualityService`    | Оркестрация DQ-анализа Bronze/Silver/Gold |
| `quality/dq_report_service.py`          | `DQReportService`       | Формирование и запись DQ-отчётов          |
| `quality/dq_report_generation_mixin.py` | Report generation mixin | Генерация DQ-отчётов                      |
| `quality/dq_report_models.py`           | Models                  | Модели DQ-отчётов                         |
| `dq/`                                   | DQ analyzers            | Специализированные layer analyzers        |

**Other Services:**

| Файл                        | Компонент              | Назначение                                     |
| --------------------------- | ---------------------- | ---------------------------------------------- |
| `ops/health_service.py`                    | `HealthService`        | Агрегация health-статусов адаптеров и сервисов |
| `export_lineage/export_service.py`         | `ExportService`        | Экспорт Gold-данных в CSV/Parquet по запросу   |
| `export_lineage/export_models.py`          | Models                 | Модели для export операций                     |
| `ops/config_service.py`                    | `ConfigService`        | Загрузка и валидация конфигураций              |
| `ops/metrics_service.py`                   | `MetricsService`       | Управление метриками pipeline run              |
| `ops/lock_service.py`                      | `LockService`          | Оркестрация блокировок pipeline                |
| `checkpoint/checkpoint_service.py`         | `CheckpointService`    | Управление чекпоинтами                         |
| `quality/quarantine_service.py`            | `QuarantineService`    | Обработка quarantine записей                   |
| `ops/shutdown_service.py`                  | `ShutdownService`      | Graceful shutdown                              |
| `ops/bronze_cleanup_service.py`            | `BronzeCleanupService` | Очистка Bronze данных                          |

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
