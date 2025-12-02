# 19 ChEMBL Pipeline Base

## Описание

`ChemblPipelineBase` — базовый пайплайн для ChEMBL с делегированием доменной логики сервису. Интегрирует сервис извлечения ChEMBL (автоматически определяет `chembl_release`) и задаёт стандартные хуки `pre_transform` и `domain_enrich` для переопределения в подклассах.

## Модуль

`src/bioetl/core/pipeline/unified.py`

## Наследование

Класс наследуется от `PipelineBase` и предоставляет базовую реализацию для ChEMBL-пайплайнов.

## Основные свойства и методы

### `__init__(self, config: Mapping[str, Any], *, run_id: str | None = None, extraction_service: ChemblExtractionService | None = None, extraction_service_factory: Callable[[], ChemblExtractionService] | None = None, **kwargs)`

Конструктор, вызывает базовый PipelineBase и инициализирует `self.extraction_service` (либо использует переданный, либо создаёт стандартный).

**Параметры:**
- `config` — конфигурация пайплайна
- `run_id` — идентификатор запуска (опционально)
- `extraction_service` — сервис извлечения (опционально)
- `extraction_service_factory` — фабрика сервиса извлечения (опционально)
- `**kwargs` — дополнительные параметры для базового класса

**Процесс:**
1. Вызов базового конструктора PipelineBase
2. Разрешение сервиса извлечения через `_resolve_extraction_service`

### `chembl_release(self) -> str | None`

Свойство, возвращающее текущий релиз ChEMBL (берётся у внутреннего *extraction_service*).

### `resolve_chembl_release(self, chembl_client) -> str`

Получить версию релиза ChEMBL, вызвав метод у клиента Chembl (через *extraction_service*).

**Параметры:**
- `chembl_client` — клиент ChEMBL API

**Возвращает:** версию релиза ChEMBL.

### `get_release(self) -> str | None`

Алиас к `chembl_release` для получения версии релиза.

### `build_descriptor(self) -> Any`

Абстрактный метод построения дескриптора извлечения (реализуется в наследниках, например, в ChemblCommonPipeline).

### `pre_transform(self, df: pd.DataFrame) -> pd.DataFrame`

Хук предобработки данных перед трансформацией (по умолчанию возвращает *df* без изменений).

**Параметры:**
- `df` — DataFrame для предварительной трансформации

**Возвращает:** предварительно трансформированный DataFrame.

### `domain_enrich(self, df: pd.DataFrame) -> pd.DataFrame`

Хук доменного обогащения данных (по умолчанию ничего не делает).

**Параметры:**
- `df` — DataFrame для обогащения

**Возвращает:** обогащённый DataFrame.

### `run_descriptor_extraction(self, descriptor: ChemblExtractionServiceDescriptor, ids: Sequence[str] | None, *, summary_event: str, metadata_filters: Mapping[str, Any] | None = None, fetch_mode: str = "default", **batch_kwargs) -> tuple[pd.DataFrame, BatchExtractionStats]`

Выполняет извлечение по дескриптору через встроенный *ChemblExtractionService* с логированием статистики.

**Параметры:**
- `descriptor` — дескриптор извлечения
- `ids` — последовательность идентификаторов (опционально)
- `summary_event` — событие для логирования
- `metadata_filters` — фильтры метаданных (опционально)
- `fetch_mode` — режим выборки (по умолчанию "default")
- `**batch_kwargs` — дополнительные параметры батчирования

**Процесс:**
1. Вызов `extraction_service.run_descriptor_extraction(...)`
2. Логирование статистики извлечения
3. Обработка ошибок

**Возвращает:** кортеж из DataFrame с данными и статистики извлечения.

## Внутренние методы

### `_resolve_extraction_service(extraction_service: ChemblExtractionService | None, extraction_service_factory: Callable[[], ChemblExtractionService] | None) -> ChemblExtractionService`

Статический метод, выбирающий способ инициализации *ChemblExtractionService* (либо напрямую, либо через фабрику, с защитой от одновременной передачи двух).

**Параметры:**
- `extraction_service` — сервис извлечения (опционально)
- `extraction_service_factory` — фабрика сервиса извлечения (опционально)

**Процесс:**
1. Проверка на одновременную передачу обоих параметров (ошибка)
2. Возврат переданного сервиса, если задан
3. Создание сервиса через фабрику, если задана
4. Создание стандартного сервиса, если ничего не задано

**Возвращает:** инициализированный сервис извлечения.

## Related Components

- **PipelineBase**: абстрактный базовый класс пайплайнов (см. `docs/02-pipelines/00-pipeline-base.md`)
- **ChemblExtractionService**: сервис извлечения данных (см. `docs/02-pipelines/chembl/common/20-chembl-extraction-service.md`)

