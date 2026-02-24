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
- **`BaseTransformer`** (`base-transformer.py`) — Базовый класс для трансформеров (Template Method паттерн)
- **`RecordProcessor`** (`record-processor.py`) — Обработка batch-ов записей через Bronze→Silver→Gold

**Исполнение:**

- **`BatchExecutor`** (`batch-executor.py`, 786 LOC) — Unified batch executor (extract→transform→write)
- **`BatchTransformer`** (`batch-transformer.py`) — Координация трансформаций
- **`BatchWriter`** (`batch-writer.py`) — Запись batch-ов в medallion слои
- **`PipelineRunner`** (`runner.py`) — Оркестрация жизненного цикла пайплайна

**Сервисы ядра:**

- **`PipelineServices`** (`pipeline-services.py`) — DI bundle портов для пайплайна
- **`LockManager`** (`lock-manager.py`) — Координация блокировок
- **`PreflightService`** (`preflight-service.py`) — Pre-run health checks
- **`PostrunService`** (`postrun-service.py`) — Post-run операции (DQ, VACUUM, cleanup)
- **`CheckpointManager`** (`checkpoint-manager.py`) — Checkpoint I/O
- **`QuarantineManager`** (`quarantine-manager.py`) — Quarantine record handling
- **`CleanupService`** (`cleanup-service.py`) — Bronze cleanup

**Observability:**

- **`BatchMetricsRecorder`** (`batch-metrics.py`) — Метрики per batch
- **`BatchTracingManager`** (`batch-tracing.py`) — Tracing span management
- **`HeartbeatTask`** (`heartbeat.py:21`) — Heartbeat мониторинг

**Data Sources:**

- **`FilteredDataSource`** (`filtered-data-source.py`) — Filter wrapper для data sources
- **`IDMappingDataSource`** (`idmapping-data-source.py`) — ID mapping wrapper

Подробнее о компонентах исполнения пайплайнов см. [раздел 2.4](#24-core--%D1%8F%D0%B4%D1%80%D0%BE-%D0%B8%D1%81%D0%BF%D0%BE%D0%BB%D0%BD%D0%B5%D0%BD%D0%B8%D1%8F-%D0%BF%D0%B0%D0%B9%D0%BF%D0%BB%D0%B0%D0%B9%D0%BD%D0%BE%D0%B2).

### 2.3. Трансформеры (Transformer DI)

**Расположение:** `src/bioetl/application/pipelines/{provider}/`

Трансформеры отвечают за преобразование Bronze → Silver. Они инжектируются в пайплайны через DI:

```python
# Пример инъекции трансформера в GenericPipelineFactory
factory = GenericPipelineFactory(
    pipeline-name="chembl_activity",
    pipeline-class=ChEMBLActivityPipeline,
    provider="chembl",
    transformer-class=ActivityTransformer,  # <-- DI
    gold-schema=ChEMBLActivityGoldSchema,
)
```

**Ключевые характеристики:**

- **MUST**: Трансформер передаётся в конструктор `BasePipeline` через параметр `transformer`
- **MUST NOT**: Пайплайн не создаёт трансформер внутри себя
- **Template Method**: `BaseTransformer` определяет скелет алгоритма, подклассы реализуют `-transform-impl()`. Примечание: `-extract-business-data()` — метод промежуточных базовых классов `BaseChemblTransformer` (`base-chembl-transformer.py:160`) и `BasePublicationTransformer` (`base-publication-transformer.py:54`), не `BaseTransformer`.
- **Если трансформер не передан**: `transform-bronze-to-silver()` выбрасывает `NotImplementedError`

**Доступные трансформеры (23 класса):**

| Provider         | Трансформер                             | Расположение                                             |
| ---------------- | --------------------------------------- | -------------------------------------------------------- |
| ChEMBL           | `ActivityTransformer`                   | `pipelines/chembl/activity-transformer.py`               |
| ChEMBL           | `AssayTransformer`                      | `pipelines/chembl/assay-transformer.py`                  |
| ChEMBL           | `MoleculeTransformer`                   | `pipelines/chembl/molecule-transformer.py`               |
| ChEMBL           | `TargetTransformer`                     | `pipelines/chembl/target-transformer.py`                 |
| ChEMBL           | `PublicationTransformer`                | `pipelines/chembl/publication-transformer.py`            |
| ChEMBL           | `AssayParametersTransformer`            | `pipelines/chembl/assay-parameters-transformer.py`       |
| ChEMBL           | `CellLineTransformer`                   | `pipelines/chembl/cell-line-transformer.py`              |
| ChEMBL           | `CompoundRecordTransformer`             | `pipelines/chembl/compound-record-transformer.py`        |
| ChEMBL           | `ProteinClassTransformer`               | `pipelines/chembl/protein-class-transformer.py`          |
| ChEMBL           | `PublicationSimilarityTransformer`      | `pipelines/chembl/publication-similarity-transformer.py` |
| ChEMBL           | `PublicationTermTransformer`            | `pipelines/chembl/publication-term-transformer.py`       |
| ChEMBL           | `SubcellularFractionTransformer`        | `pipelines/chembl/subcellular-fraction-transformer.py`   |
| ChEMBL           | `TargetComponentTransformer`            | `pipelines/chembl/target-component-transformer.py`       |
| ChEMBL           | `TissueTransformer`                     | `pipelines/chembl/tissue-transformer.py`                 |
| ChEMBL           | `BaseChemblTransformer`                 | `pipelines/chembl/base-chembl-transformer.py`            |
| CrossRef         | `CrossRefPublicationTransformer`        | `pipelines/crossref/transformer.py`                      |
| OpenAlex         | `OpenAlexPublicationTransformer`        | `pipelines/openalex/transformer.py`                      |
| PubChem          | `PubChemCompoundTransformer`            | `pipelines/pubchem/transformer.py`                       |
| UniProt          | `UniProtProteinTransformer`             | `pipelines/uniprot/transformer.py`                       |
| UniProt          | `IDMappingTransformer`                  | `pipelines/uniprot/idmapping-transformer.py`             |
| PubMed           | `PubMedPublicationTransformer`          | `pipelines/pubmed/transformer.py`                        |
| Semantic Scholar | `SemanticScholarPublicationTransformer` | `pipelines/semanticscholar/transformer.py`               |
| Common           | `BasePublicationTransformer`            | `pipelines/common/base-publication-transformer.py`       |

### 2.4. `core/` — Ядро Исполнения Пайплайнов

**Расположение:** `src/bioetl/application/core/`

Содержит компоненты, отвечающие за *запуск*, *координацию* и *исполнение* пайплайнов.

**Ключевые компоненты:**

| Файл                              | Компонент                   | Назначение                                                               |
| --------------------------------- | --------------------------- | ------------------------------------------------------------------------ |
| `runner.py`                       | `PipelineRunner`            | Оркестрирует жизненный цикл пайплайна: блокировки, чекпоинты, исполнение |
| `batch-executor.py`               | `BatchExecutor`             | Координирует data flow: извлечение → трансформация → запись (774 LOC)    |
| `../services/medallion-lifecycle.py` | `MedallionLifecycleService` | Управляет очисткой Silver/Gold слоёв по политике, VACUUM (`application/services/`) |
| `pipeline-services.py`            | `PipelineServices`          | DI bundle сервисов для PipelineRunner                                    |

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
    data-source: DataSourcePort
    storage: StoragePort
    lock: LockPort
    checkpoint: CheckpointPort
    quarantine: QuarantinePort
    metrics: MetricsPort
    tracing: TracingPort
    logger: LoggerPort
    dq-monitor: DQMonitorPort | None = None
    bronze-dq-analyzer: BronzeDQAnalyzerPort | None = None
    silver-dq-analyzer: SilverDQAnalyzerPort | None = None
    gold-dq-analyzer: GoldDQAnalyzerPort | None = None
    dq-report-writer: DQReportWriterPort | None = None
    dq-report-service: DQReportService | None = None
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
| `key-extractor.py` | `KeyExtractorService`        | Извлечение join keys из seed pipeline                     |
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

----------------------------------------------------------------------

## 4. Связанные Материалы

### Навигация по Слоям

| ← Предыдущий                       | Текущий         | Следующий →                                        |
| ---------------------------------- | --------------- | -------------------------------------------------- |
| [Domain Layer](01-domain-layer.md) | **Application** | [Infrastructure Layer](03-infrastructure-layer.md) |

### Связанные Диаграммы

| Диаграмма                 | Файл                                                                                                                 | Описание                                 |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| Application Layer Classes | [06-application-layer-class-diagram.mmd](mmd-diagrams/foundation/06-application-layer-class-diagram.mmd)            | Классы слоя Application                  |
| Pipeline Execution        | [06-pipeline-execution.mmd](mmd-diagrams/foundation/06-pipeline-execution.mmd)                                      | Поток выполнения пайплайна               |
| Pipeline Hierarchy        | [17-pipeline-hierarchy.mmd](mmd-diagrams/foundation/17-pipeline-hierarchy.mmd)                                      | Иерархия Pipeline/Transformer            |
| Layers Interaction        | [05-layers-interaction.mmd](mmd-diagrams/foundation/05-layers-interaction.mmd)                                      | Взаимодействие слоёв (включая Composite) |
| Composite Pipeline        | [29-composite-pipeline-workflow.mmd](mmd-diagrams/foundation/29-composite-pipeline-workflow.mmd)                     | Workflow Composite Pipeline              |
| Pipeline Core             | [40-application-core-collaboration.mmd](mmd-diagrams/foundation/40-application-core-collaboration.mmd)              | Ядро пайплайнов                          |
| BaseTransformer           | [45-template-method-transformer.mmd](mmd-diagrams/foundation/45-template-method-transformer.mmd)                    | Template Method паттерн                  |

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
