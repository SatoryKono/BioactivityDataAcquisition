# 18 ChEMBL Common Pipeline

## Описание

`ChemblCommonPipeline` — базовый класс для ChEMBL-пайплайнов без legacy-зависимостей. Отвечает за общую логику: проверку корректности конфигурации, инициализацию сервиса записи результатов и создание дескриптора извлечения для сущности.

## Модуль

`src/bioetl/pipelines/chembl/common/base.py`

## Наследование

Класс наследуется от `ChemblPipelineBase` и предоставляет общую реализацию для всех ChEMBL-пайплайнов.

## Основные методы

### `__init__(self, config: Mapping[str, Any], *, run_id: str | None = None, extraction_service: ChemblExtractionService | None = None, extraction_service_factory: Callable[[], ChemblExtractionService] | None = None, descriptor_factory: ChemblDescriptorFactory | None = None, client_registry: ClientFactoryRegistry | None = None, ..., descriptor_type: str = "service", extraction_strategy_factory: ExtractionStrategyFactory | None = None)`

Конструктор, вызывает базовый ChemblPipelineBase, валидирует конфиг и настраивает службы (запись через ChemblWriteService, стратегии извлечения и др.).

**Параметры:**
- `config` — конфигурация пайплайна
- `run_id` — идентификатор запуска (опционально)
- `extraction_service` — сервис извлечения (опционально)
- `extraction_service_factory` — фабрика сервиса извлечения (опционально)
- `descriptor_factory` — фабрика дескрипторов (опционально)
- `client_registry` — реестр фабрик клиентов (опционально)
- `descriptor_type` — тип дескриптора (по умолчанию "service")
- `extraction_strategy_factory` — фабрика стратегий извлечения (опционально)

**Процесс:**
1. Вызов базового конструктора ChemblPipelineBase
2. Валидация конфигурации через `_validate_common_config`
3. Инициализация сервисов (запись, валидация, стратегии)

### `extract(self, descriptor: ChemblExtractionServiceDescriptor | ChemblExtractionDescriptor | None, options: StageExecutionOptions) -> pd.DataFrame`

Реализует стадию извлечения: выбирает стратегию по типу дескриптора и выполняет её (`strategy.run(...)`).

**Параметры:**
- `descriptor` — дескриптор извлечения (service или dataclass)
- `options` — опции выполнения стадии

**Процесс:**
1. Определение типа дескриптора
2. Выбор стратегии извлечения через фабрику
3. Выполнение извлечения через стратегию (`strategy.run(...)`)

**Возвращает:** DataFrame с извлечёнными данными.

### `transform(self, df: pd.DataFrame, options: StageExecutionOptions) -> pd.DataFrame`

Стадия трансформации: вызывает хуки `pre_transform` и `domain_enrich` (можно переопределить в наследниках).

**Параметры:**
- `df` — DataFrame для трансформации
- `options` — опции выполнения стадии

**Процесс:**
1. Вызов `pre_transform` для предварительной обработки
2. Вызов `domain_enrich` для обогащения доменными данными

**Возвращает:** трансформированный DataFrame.

### `validate(self, df: pd.DataFrame, options: StageExecutionOptions) -> pd.DataFrame`

Валидирует DataFrame через службу валидации, если она настроена.

**Параметры:**
- `df` — DataFrame для валидации
- `options` — опции выполнения стадии

**Возвращает:** валидированный DataFrame.

### `build_descriptor(self) -> ChemblExtractionServiceDescriptor | ChemblExtractionDescriptor`

Строит дескриптор для извлечения: для типа *service* вызывает фабрику дескрипторов (`_descriptor_factory.build(...)`) (для *dataclass* бросает исключение).

**Процесс:**
1. Проверка типа дескриптора
2. Для типа "service": вызов `_descriptor_factory.build(...)`
3. Для типа "dataclass": выбрасывание исключения (не поддерживается в базовом классе)

**Возвращает:** дескриптор извлечения данных.

## Внутренние методы

### `_create_descriptor_factory(self) -> ChemblDescriptorFactory`

Создаёт фабрику дескрипторов ChEMBL для текущей сущности (инициализируя при необходимости реестр клиентов).

### `_validate_common_config(self) -> None`

Проверяет конфигурацию на корректность (параметры batch_size, max_url_length, namespace кэша, сортировку и т.д.).

### `_get_config_value(self, dotted_path: str) -> Any`

Утилита для получения вложенного значения из конфига или выброса `ConfigValidationError`, если ключ отсутствует.

### `_write_quality_report(self, df: pd.DataFrame, output_path: Path) -> None`

Генерирует CSV-отчёт по качеству данных (число строк, столбцов, пропусков).

### `_fallback_rows(self, ids: Iterable[str], exc: Exception) -> list[dict[str, Any]]`

Формирует "записи-замены" с информацией об ошибках для каждого идентификатора при неудаче извлечения (для fallback).

### `_build_generic_descriptor(self) -> ChemblExtractionServiceDescriptor`

Строит универсальный дескриптор извлечения по конфигурации (используется, если явно не задан специфичный дескриптор).

### `_extract_with_dataclass_descriptor(self, descriptor: ChemblExtractionDescriptor, options: StageExecutionOptions) -> pd.DataFrame`

Выполняет извлечение данных, если используется dataclass-дескриптор (вызывается стратегией для `descriptor_type="dataclass"`).

## Related Components

- **ChemblPipelineBase**: базовый пайплайн для ChEMBL (см. `docs/02-pipelines/chembl/common/19-chembl-pipeline-base.md`)
- **ChemblExtractionService**: сервис извлечения данных (см. `docs/02-pipelines/chembl/common/20-chembl-extraction-service.md`)
- **ChemblDescriptorFactory**: фабрика дескрипторов (см. `docs/02-pipelines/chembl/common/21-chembl-descriptor-factory.md`)

