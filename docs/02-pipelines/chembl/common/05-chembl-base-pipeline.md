# 05 ChEMBL Base Pipeline

## Описание

`ChemblBasePipeline` — базовый пайплайн для обработки данных ChEMBL, объединяющий общую логику инициализации сервисов, валидации конфигурации и оркестрации этапов. Наследуется от `PipelineBase`.

Интегрирует:
- **ChemblExtractionService**: сервис извлечения данных (с поддержкой версионирования релизов).
- **ChemblWriteService**: сервис записи результатов.
- **ChemblDescriptorFactory**: фабрику дескрипторов для стратегий извлечения.

## Модуль

`src/bioetl/pipelines/chembl/common/base.py`

## Наследование

Класс наследуется от `PipelineBase`.

## Основные свойства и методы

### `__init__(self, config: Mapping[str, Any], *, run_id: str | None = None, extraction_service: ChemblExtractionService | None = None, extraction_service_factory: Callable[[], ChemblExtractionService] | None = None, descriptor_factory: ChemblDescriptorFactory | None = None, client_registry: ClientFactoryRegistry | None = None, ..., descriptor_type: str = "service", extraction_strategy_factory: ExtractionStrategyFactory | None = None)`

Конструктор, выполняет полную инициализацию пайплайна:
1. Вызывает базовый `PipelineBase`.
2. Валидирует общую конфигурацию ChEMBL (batch_size, таймауты и пр.).
3. Инициализирует сервисы: извлечения (`extraction_service`), записи (через `ChemblWriteService`), фабрику дескрипторов и стратегий.

**Параметры:**
- `config`: конфигурация пайплайна.
- `run_id`: идентификатор запуска.
- `extraction_service`: готовый сервис извлечения (опционально).
- `descriptor_factory`: фабрика дескрипторов (опционально).
- `descriptor_type`: тип дескриптора ("service" по умолчанию).

### `extract(self, descriptor: ChemblExtractionServiceDescriptor | ChemblExtractionDescriptor | None, options: StageExecutionOptions) -> pd.DataFrame`

Реализует стадию извлечения: выбирает стратегию по типу дескриптора и выполняет её.

**Процесс:**
1. Определение типа дескриптора.
2. Выбор стратегии извлечения через фабрику.
3. Выполнение `strategy.run(...)`.

### `transform(self, df: pd.DataFrame, options: StageExecutionOptions) -> pd.DataFrame`

Стандартная реализация трансформации с хуками:
1. `pre_transform(df)`: предобработка.
2. `domain_enrich(df)`: доменное обогащение.

### `chembl_release(self) -> str | None`

Свойство, возвращающее текущую версию релиза ChEMBL (делегирует сервису извлечения).

### `build_descriptor(self) -> Any`

Строит дескриптор для извлечения, используя `descriptor_factory`.
Для типа "service" вызывает `build()`, для "dataclass" может выбрасывать исключение, если не переопределено.

## Хуки (Hooks)

### `pre_transform(self, df: pd.DataFrame) -> pd.DataFrame`
Хук предобработки данных перед трансформацией (по умолчанию `noop`).

### `domain_enrich(self, df: pd.DataFrame) -> pd.DataFrame`
Хук доменного обогащения данных (по умолчанию `noop`).

## Внутренние методы

### `_validate_common_config(self) -> None`
Проверяет корректность общих параметров конфигурации (batch size, namespace кэша, сортировку).

### `_resolve_extraction_service(...) -> ChemblExtractionService`
Утилита для разрешения сервиса извлечения (инъекция или создание через фабрику).

## Related Components

- **PipelineBase**: абстрактный базовый пайплайн (см. `docs/02-pipelines/core/00-pipeline-base.md`)
- **ChemblExtractionService**: сервис извлечения данных (см. `docs/02-pipelines/chembl/common/06-chembl-extraction-service.md`)
- **ChemblDescriptorFactory**: фабрика дескрипторов (см. `docs/02-pipelines/chembl/common/07-chembl-descriptor-factory.md`)

