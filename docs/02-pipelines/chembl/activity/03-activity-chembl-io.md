# 03 Activity ChEMBL IO

## Description

Input/Output operations and artifact management for Activity ChEMBL pipeline. Includes `ActivityWriter` stage and artifact planning components.

## ActivityWriter

`ActivityWriter` — класс этапа сохранения результатов пайплайна активности. Записывает финальный набор данных на диск и генерирует артефакты контроля качества (QC). Наследуется от `StageABC` и реализует интерфейс стадии записи.

**Module:** `src/bioetl/pipelines/chembl/activity/stages.py`

**Inheritance:**

Класс наследуется от `StageABC` и реализует интерфейс стадии записи результатов.

### Main Method

#### `write(self, df: pd.DataFrame, artifacts: WriteArtifacts, *, run_stem: str, output_dir: Path) -> WriteResult`

Сохраняет результаты обработки данных активности.

**Parameters:**
- `df` — DataFrame с обработанными данными
- `artifacts` — объект `WriteArtifacts` с путями для артефактов
- `run_stem` — основа имени файла (например, `"activity_run_001"`)
- `output_dir` — директория для сохранения результатов

**Write Process:**

1. Подготовка артефактов: создание `RunArtifacts` с путями для данных, метаданных и манифеста
2. Запись данных: использование `UnifiedOutputWriter.write_dataset_atomic` для атомарной записи DataFrame
3. Генерация QC-отчётов: создание отчётов о качестве данных (если требуется)
4. Возврат результата: возврат `WriteResult` с информацией о записанных файлах

**Returns:** `WriteResult` с метриками записи и путями к артефактам.

## Artifact Planning

### ActivityArtifactPlanner

`ActivityArtifactPlanner` — специализированный планировщик артефактов для пайплайна активности. Определяет, как будут именоваться и размещаться файлы вывода. В реализации для активности формирует поддиректорию с именем, основанным на `run_tag` и `mode`, и внутри неё задаёт имя файла данных формата `activity_<run_stem>.csv` для основного датасета.

**Module:** `bioetl/pipelines/chembl/activity/run.py`

**Main Method:**

#### `plan(self, output_dir: Path, pipeline_code: str, run_tag: str | None, mode: str | None) -> tuple[Path, WriteArtifacts]`

Переопределяет абстрактный метод базового класса `ArtifactPlanner`.

**Parameters:**
- `output_dir` — базовая директория вывода
- `pipeline_code` — код пайплайна
- `run_tag` — тег запуска
- `mode` — режим выполнения

**Planning Process:**

1. Создание целевой директории: формирование поддиректории `<output_dir>/<run_stem>` на основе `run_tag` и `mode`
2. Формирование путей: создание объекта `WriteArtifacts` с путём для будущего CSV-файла
3. Возврат результатов: возврат пути к директории и объекта `WriteArtifacts`

**Returns:** кортеж из пути к директории и объекта `WriteArtifacts`.

### ActivityWriteService

`ActivityWriteService` — сервис вывода данных для пайплайна активности. Оборачивает `ActivityWriter` в интерфейс `WriteService` для совместимости с оркестрацией.

**Module:** `src/bioetl/pipelines/chembl/activity/run.py`

**Inheritance:**

Сервис наследуется от `WriteService` и предоставляет специализированную реализацию для пайплайна активности.

**Main Method:**

#### `save(self, df: pd.DataFrame, artifacts: WriteArtifacts, options: StageExecutionOptions, *, context: StageContextProtocol, runtime: StageRuntimeContext) -> WriteResult`

Переопределяет метод базового класса `WriteService`.

**Parameters:**
- `df` — DataFrame с данными для сохранения
- `artifacts` — объект `WriteArtifacts` с путями к артефактам
- `options` — опции выполнения стадии
- `context` — контекст выполнения стадии
- `runtime` — контекст времени выполнения

**Save Process:**

1. Определение директории вывода: извлечение пути из контекста
2. Формирование имени файла: создание имени по шаблону `activity_<run_stem>.csv` при необходимости
3. Вызов writer: использование `self.writer.write(...)` для непосредственной записи
4. Возврат результата: возврат `WriteResult` с информацией о записанных файлах

**Returns:** `WriteResult` с метриками записи.

## Output Artifacts

Pipeline produces the following artifacts:

1. **Data File**: `activity_<run_stem>.parquet` (or `.csv`) — main data file
2. **Metadata**: `meta.yaml` — pipeline metadata (version, row count, checksums)
3. **QC Reports**: `quality_report_activity_chembl.csv`, `correlation_report_activity_chembl.csv`
4. **Schema**: Schema validation results

## Artifact Structure

```
<output_dir>/
└── <run_stem>/
    ├── activity_<run_stem>.parquet
    ├── meta.yaml
    ├── quality_report_activity_chembl.csv
    └── correlation_report_activity_chembl.csv
```

## Write Process

1. **Validation**: Data validated against Pandera schema
2. **Sorting**: Stable sort by business keys
3. **Writing**: Atomic write via `UnifiedOutputWriter`
4. **Metadata Generation**: Creation of `meta.yaml` with pipeline metadata

## Related Components

- **UnifiedOutputWriter**: unified writer (see `docs/02-pipelines/core/04-unified-output-writer.md`)
- **WriteArtifacts**: artifact management (see `docs/02-pipelines/core/01-write-artifacts.md`)
- **MetadataWriterABC**: metadata writing contract (see `docs/reference/abc/11-metadata-writer-abc.md`)
