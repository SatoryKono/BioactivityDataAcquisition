# 00 Activity ChEMBL Overview

## Description

`ChemblActivityPipeline` — основной ETL-пайплайн для обработки данных биоактивности из ChEMBL. Пайплайн имеет код `activity_chembl` и реализует полный цикл извлечения данных из API ChEMBL, их трансформации, валидации и сохранения результатов.

Пайплайн наследуется от `ChemblBasePipeline`, который в свою очередь наследуется от `PipelineBase`. Использует дескриптор для извлечения данных, реализуя полный цикл ETL для сущности "activity".

## Module

`src/bioetl/pipelines/chembl/activity/run.py`

## Inheritance

Пайплайн наследуется от `ChemblBasePipeline`, который в свою очередь наследуется от `PipelineBase`. Использует общую инфраструктуру ChEMBL-пайплайнов через базовый класс `ChemblBasePipeline`.

## Architecture

Пайплайн состоит из следующих стадий:

1. **Extract** (`ActivityExtractor`) — извлечение сырых данных из ChEMBL API
2. **Transform** (`ActivityTransformer`) — трансформация и обогащение данных
3. **Validate** — валидация данных по Pandera-схеме
4. **Write** (`ActivityWriter`) — сохранение результатов в файлы

## Key Methods

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

## Extraction Descriptor

### ChemblExtractionDescriptor

`ChemblExtractionDescriptor` — описание задачи извлечения данных из ChEMBL. Хранит параметры, определяющие, *что* извлекать: список идентификаторов `ids` (ChEMBL IDs интересующих объектов) либо параметры фильтрации, настройки пагинации (`limit/offset`), режим выгрузки и т.д.

**Module:** `bioetl/pipelines/chembl/common/descriptor.py`

**Structure:**

Дескриптор является dataclass и содержит следующие поля:

- `ids: Sequence[str] | None` — список ChEMBL IDs для извлечения (опционально)
- `filters: Mapping[str, object] | None` — параметры фильтрации (опционально)
- `pagination: PaginationParams | None` — настройки пагинации (limit/offset)
- `mode: str` — режим выгрузки (`"chembl"` или `"all"`)
- `batch_plan: BatchPlan | None` — план батчирования запросов

**Validation:**

`__post_init__(self)` проверяет корректность поля `mode` при инициализации. Разрешены только значения `"chembl"` или `"all"`, иначе выбрасывается `ConfigValidationError`.

**Usage:**

Дескриптор используется пайплайном для:
- Разбиения работы на части (батчи)
- Логирования целей выгрузки
- Передачи параметров извлечения в `ActivityExtractor`

## Batch Plan

### BatchPlan

`BatchPlan` — простая структура для параметров пакетирования запросов. Содержит размер батча (`batch_size`) – число идентификаторов в одном запросе к API – и размер чанка (`chunk_size`) – количество батчей, объединяемых в одну запись результатов. Эти параметры влияют на стратегию извлечения данных из API (ограничение в 25 ID на запрос у ChEMBL).

**Module:** `bioetl/clients/chembl/descriptor_factory.py`

**Structure:**

BatchPlan является dataclass и содержит следующие поля:

- `batch_size: int` — размер батча (количество ID в одном запросе к API)
- `chunk_size: int` — размер чанка (количество батчей, объединяемых в одну запись)

**Usage:**

План батчирования используется для:
- Оптимизации запросов к ChEMBL API (ограничение в 25 ID на запрос)
- Управления размером обрабатываемых данных
- Контроля использования памяти при извлечении больших объёмов данных

**Example:**

```python
batch_plan = BatchPlan(
    batch_size=25,  # 25 ID на запрос (ограничение ChEMBL)
    chunk_size=10   # 10 батчей в одном чанке
)
```

## Configuration

Конфигурация пайплайна находится в `configs/pipelines/chembl/activity.yaml` и определяет:
- Поля данных и их типы
- Параметры пагинации
- Фильтры и ограничения
- Настройки нормализации

## Related Components

- **ActivityExtractor**: стадия извлечения данных (см. `01-activity-chembl-extraction.md`)
- **ActivityTransformer**: стадия трансформации данных (см. `02-activity-chembl-transformation.md`)
- **ActivityWriter**: стадия записи результатов (см. `03-activity-chembl-io.md`)
- **ChemblClient**: REST-клиент для ChEMBL API (см. `docs/02-pipelines/core/01-base-external-data-client.md`)
- **UnifiedOutputWriter**: унифицированный writer для сохранения результатов (см. `docs/02-pipelines/core/04-unified-output-writer.md`)
- **SchemaRegistry**: реестр схем для валидации (см. `docs/02-pipelines/core/05-schema-registry.md`)
