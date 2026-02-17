# Слой Application (Приложение)

**Расположение:** `src/bioetl/application/`

## 1. Назначение

Слой `Application` является координатором. Он не содержит бизнес-логики (это задача `Domain`) и не взаимодействует напрямую с внешними системами (это задача `Infrastructure`). Вместо этого он оркестрирует поток данных, используя порты из `Domain` для выполнения операций.

Здесь реализуются **Use Cases** или, в нашей терминологии, **пайплайны**.

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

Содержит базовые классы и общие компоненты, используемые пайплайнами (27 файлов):

**Базовые классы:**

- **`BasePipeline`** (`base.py`) — Базовый класс для всех пайплайнов
- **`BaseTransformer`** (`base_transformer.py`) — Базовый класс для трансформеров (Template Method паттерн)
- **`RecordProcessor`** (`record_processor.py`) — Обработка batch-ов записей через Bronze→Silver→Gold

**Исполнение:**

- **`BatchExecutor`** (`batch_executor.py`, 786 LOC) — Unified batch executor (extract→transform→write)
- **`BatchTransformer`** (`batch_transformer.py`) — Координация трансформаций
- **`BatchWriter`** (`batch_writer.py`) — Запись batch-ов в medallion слои
- **`PipelineRunner`** (`runner.py`) — Оркестрация жизненного цикла пайплайна

**Сервисы ядра:**

- **`PipelineServices`** (`pipeline_services.py`) — DI bundle портов для пайплайна
- **`LockManager`** (`lock_manager.py`) — Координация блокировок
- **`PreflightService`** (`preflight_service.py`) — Pre-run health checks
- **`PostrunService`** (`postrun_service.py`) — Post-run операции (DQ, VACUUM, cleanup)
- **`CheckpointManager`** (`checkpoint_manager.py`) — Checkpoint I/O
- **`QuarantineManager`** (`quarantine_manager.py`) — Quarantine record handling
- **`CleanupService`** (`cleanup_service.py`) — Bronze cleanup

**Observability:**

- **`BatchMetricsRecorder`** (`batch_metrics.py`) — Метрики per batch
- **`BatchTracingManager`** (`batch_tracing.py`) — Tracing span management
- **`HeartbeatTask`** (`heartbeat.py:21`) — Heartbeat мониторинг

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
- **Template Method**: `BaseTransformer` определяет скелет алгоритма, подклассы реализуют `_transform_impl()`. Примечание: `_extract_business_data()` — метод промежуточных базовых классов `BaseChemblTransformer` (`base_chembl_transformer.py:160`) и `BasePublicationTransformer` (`base_publication_transformer.py:54`), не `BaseTransformer`.
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

| Файл                              | Компонент                   | Назначение                                                               |
| --------------------------------- | --------------------------- | ------------------------------------------------------------------------ |
| `runner.py`                       | `PipelineRunner`            | Оркестрирует жизненный цикл пайплайна: блокировки, чекпоинты, исполнение |
| `batch_executor.py`               | `BatchExecutor`             | Координирует data flow: извлечение → трансформация → запись (786 LOC)    |
| `services/medallion_lifecycle.py` | `MedallionLifecycleService` | Управляет очисткой Silver/Gold слоёв по политике, VACUUM                 |
| `pipeline_services.py`            | `PipelineServices`          | DI bundle сервисов для PipelineRunner                                    |

**`PipelineRunner`** — координатор исполнения:

- Делегирует блокировку через `LockManager`
- Запускает preflight-валидацию через `PreflightService`
- Исполняет пайплайн через `BatchExecutor`
- Управляет postrun-операциями через `PostrunService`
- Оркестрирует очистку слоёв через `MedallionLifecycleService`

**`PipelineServices`** — frozen dataclass, bundling зависимостей:

```python
@dataclass(frozen=True)
class PipelineServices:
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

Содержит компоненты для **композитных пайплайнов** — оркестрации нескольких пайплайнов для обогащения данных из разных источников.

**Ключевые компоненты:**

| Файл               | Компонент                    | Назначение                                                |
| ------------------ | ---------------------------- | --------------------------------------------------------- |
| `runner.py`        | `CompositePipelineRunner`    | Оркестрирует: seed → enrich (fan-out) → merge             |
| `coordinator.py`   | `EnrichmentCoordinator`      | Параллельный запуск enrichers через asyncio.gather        |
| `merger.py`        | `MergeService`               | Объединение данных из разных источников (LEFT OUTER JOIN) |
| `key_extractor.py` | `KeyExtractorService`        | Извлечение join keys из seed pipeline                     |
| `checkpoint.py`    | `CompositeCheckpointManager` | Resume после сбоя                                         |

**Workflow Composite Pipeline:**

```
Seed Pipeline → Extract Keys → [CrossRef, OpenAlex, PubMed, SemanticScholar] → Merge → Gold
                                     ↑ Fan-Out (parallel)
```

См. [ADR-026: Composite Pipeline Pattern](decisions/ADR-026-composite-pipeline-pattern.md) для деталей.

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

| Диаграмма                 | Файл                                                                                                                 | Описание                                 |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| Application Layer Classes | [06-application-layer-class-diagram.mermaid](diagrams/mermaid/06-application-layer-class-diagram.mermaid)            | Классы слоя Application                  |
| Pipeline Execution        | [06-pipeline-execution.mermaid](diagrams/mermaid/06-pipeline-execution.mermaid)                                      | Поток выполнения пайплайна               |
| Pipeline Hierarchy        | [17-pipeline-hierarchy.mermaid](diagrams/mermaid/17-pipeline-hierarchy.mermaid)                                      | Иерархия Pipeline/Transformer            |
| Layers Interaction        | [05-layers-interaction.mermaid](diagrams/mermaid/05-layers-interaction.mermaid)                                      | Взаимодействие слоёв (включая Composite) |
| Composite Pipeline        | [diagrams/mermaid/26_composite_pipeline_workflow.mmd](diagrams/mermaid/26_composite_pipeline_workflow.mmd)           | Workflow Composite Pipeline              |
| Pipeline Core             | [diagrams/mermaid/10_pipeline_core_components.mmd](diagrams/mermaid/10_pipeline_core_components.mmd)                 | Ядро пайплайнов                          |
| BaseTransformer           | [diagrams/mermaid/19_base_transformer_template_method.mmd](diagrams/mermaid/19_base_transformer_template_method.mmd) | Template Method паттерн                  |

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
- [RULES.md §1 "Архитектура и Слои"](../RULES.md) — матрица импортов
