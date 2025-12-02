# 00 Activity ChEMBL Overview

## Описание

`ChemblActivityPipeline` — основной ETL-пайплайн для обработки данных биоактивности из ChEMBL. Пайплайн имеет код `activity_chembl` и реализует полный цикл извлечения данных из API ChEMBL, их трансформации, валидации и сохранения результатов.

Пайплайн наследуется от `PipelineBase` и использует дескриптор для извлечения данных, реализуя полный цикл ETL для сущности "activity".

## Модуль

`src/bioetl/pipelines/chembl/activity/run.py`

## Наследование

Пайплайн наследуется от `PipelineBase` и использует общую инфраструктуру ChEMBL-пайплайнов.

## Архитектура

Пайплайн состоит из следующих стадий:

1. **Extract** (`ActivityExtractor`) — извлечение сырых данных из ChEMBL API
2. **Transform** (`ActivityTransformer`) — трансформация и обогащение данных
3. **Validate** — валидация данных по Pandera-схеме
4. **Write** (`ActivityWriter`) — сохранение результатов в файлы

## Основные методы

### `__init__(self, config, run_id, *, client_factory=None)`

Инициализирует пайплайн с конфигурацией, run_id и опциональной фабрикой клиентов.

### `build_descriptor(self) -> ChemblExtractionDescriptor`

Создаёт дескриптор извлечения данных на основе конфигурации пайплайна.

### `resolve_chembl_release(self, config) -> str | None`

Определяет версию релиза ChEMBL для метаданных.

### `prepare_run(self, options: StageExecutionOptions) -> None`

Подготавливает выполнение пайплайна: инициализирует компоненты, настраивает контекст выполнения.

### `extract(self, descriptor, options) -> pd.DataFrame`

Извлекает сырые данные из ChEMBL API и преобразует их в pandas DataFrame. Поддерживает опциональные ограничения через параметр `limit` для тестирования.

### `transform(self, df: pd.DataFrame, options) -> pd.DataFrame`

Трансформирует извлечённые данные: обогащает доменными полями, нормализует значения и типы данных.

### `validate(self, df: pd.DataFrame, options) -> pd.DataFrame`

Валидирует данные по Pandera-схеме. В случае пустого DataFrame создаёт пустой DataFrame с правильной структурой для валидации.

### `run(self, output_dir: Path, *, run_tag=None, mode=None, extended=False, dry_run=None, sample=None, limit=None, include_qc_metrics=False, fail_on_schema_drift=True) -> RunResult`

Основной метод выполнения пайплайна. Выполняет полный цикл: подготовку конфигурации, стадии extract/transform/validate, сохранение результатов и генерацию QC-метрик.

**Параметры:**
- `output_dir` — директория для сохранения результатов
- `run_tag` — тег запуска для именования артефактов
- `mode` — режим выполнения
- `extended` — расширенный режим с дополнительными метриками
- `dry_run` — режим без записи результатов
- `sample` — ограничение количества записей для тестирования
- `limit` — ограничение количества записей при извлечении
- `include_qc_metrics` — включение QC-метрик в результаты
- `fail_on_schema_drift` — прерывание при отклонении схемы

### `save_results(self, df: pd.DataFrame, artifacts: WriteArtifacts, options: StageExecutionOptions) -> WriteResult`

Сохраняет DataFrame через унифицированный вывод. При ошибке использует запасной сервис записи для обеспечения надёжности сохранения результатов.

### `build_pipeline_metadata(self, context=None) -> Mapping[str, Any]`

Создаёт метаданные пайплайна, включая информацию о конфигурации, релизе ChEMBL и параметрах выполнения.

## Внутренние методы

### `_get_config_metadata(self, config=None) -> ChemblPipelineMetadata`

Извлекает метаданные конфигурации из конфигурации пайплайна.

### `_extract_with_dataclass_descriptor(self, descriptor, options) -> pd.DataFrame`

Выполняет извлечение данных, используя дескриптор типа dataclass, и возвращает нормализованный DataFrame.

### `run_descriptor_extraction(self, descriptor, *, batch_size=None) -> tuple[pd.DataFrame, dict]`

Запускает извлечение через `extractor.extract`, возвращает DataFrame и метаданные извлечения.

### `_build_schema_registry(self) -> SchemaRegistry`

Создаёт реестр схем, регистрируя `ChEMBLActivitySchema` и связанные схемы для валидации данных.

## Конфигурация

Конфигурация пайплайна находится в `configs/pipelines/chembl/activity.yaml` и определяет:
- Поля данных и их типы
- Параметры пагинации
- Фильтры и ограничения
- Настройки нормализации

## Related Components

- **ActivityExtractor**: стадия извлечения данных (см. `01-activity-chembl-extraction.md`)
- **ActivityTransformer**: стадия трансформации данных (см. `02-activity-chembl-transformation.md`)
- **ActivityWriter**: стадия записи результатов (см. `03-activity-chembl-io.md`)
- **ActivityParser**: парсер ответов ChEMBL API (см. `04-activity-chembl-parser.md`)
- **ActivityNormalizer**: нормализатор данных активности (см. `05-activity-chembl-normalizer.md`)
- **ChemblClient**: REST-клиент для ChEMBL API (см. `docs/02-pipelines/01-base-external-data-client.md`)
- **UnifiedOutputWriter**: унифицированный writer для сохранения результатов (см. `docs/02-pipelines/04-unified-output-writer.md`)
- **SchemaRegistry**: реестр схем для валидации (см. `docs/02-pipelines/05-schema-registry.md`)

