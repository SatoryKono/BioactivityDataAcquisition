# 17 ChEMBL Write Service

## Описание

`ChemblWriteService` — сервис детерминированной записи для всех ChEMBL-пайплайнов. Выполняет сохранение основного датасета, метаданных и отчёта качества с единообразным именованием.

## Модуль

`src/bioetl/pipelines/chembl/common/base.py`

## Наследование

Сервис наследуется от `WriteService` и предоставляет общую реализацию для всех ChEMBL-пайплайнов.

## Основные методы

### `save(self, df: pd.DataFrame, artifacts: WriteArtifacts, options: StageExecutionOptions, *, context: StageContextProtocol, runtime: StageRuntimeContext) -> WriteResult`

Выполняет сохранение результатов пайплайна с единообразным именованием файлов.

**Параметры:**
- `df` — DataFrame с данными для сохранения
- `artifacts` — объект `WriteArtifacts` с путями к артефактам
- `options` — опции выполнения стадии
- `context` — контекст выполнения стадии
- `runtime` — контекст времени выполнения

**Процесс сохранения:**

1. Сохранение основного датасета: запись DataFrame в CSV или Parquet
2. Запись метаданных: сохранение метаданных пайплайна
3. Генерация QC-отчёта: создание отчёта о качестве данных

**Возвращает:** `WriteResult` с информацией о записанных файлах.

### `write_metadata(self, output_dir: Path, artifacts: WriteArtifacts, df: pd.DataFrame | None, *, dry_run: bool) -> None`

Записывает метаданные пайплайна в файл.

**Параметры:**
- `output_dir` — директория вывода
- `artifacts` — объект `WriteArtifacts` с путями
- `df` — DataFrame с данными (опционально)
- `dry_run` — режим без записи (опционально)

## Единообразное именование

Сервис обеспечивает единообразное именование файлов для всех ChEMBL-пайплайнов:
- Основной датасет: `<entity>_<run_stem>.csv`
- Метаданные: `<entity>_<run_stem>_meta.yaml`
- QC-отчёт: `<entity>_<run_stem>_qc.csv`

## Related Components

- **WriteService**: базовый класс сервиса записи
- **UnifiedOutputWriter**: унифицированный writer для записи (см. `docs/02-pipelines/04-unified-output-writer.md`)
- **ActivityWriteService**: специализированный сервис для activity (см. `docs/02-pipelines/chembl/activity/13-activity-chembl-artifacts.md`)

