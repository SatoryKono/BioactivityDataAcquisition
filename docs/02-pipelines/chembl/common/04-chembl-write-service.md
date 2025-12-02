# 04 ChEMBL Write Service

## Описание

`ChemblWriteService` — сервис детерминированной записи для всех ChEMBL-пайплайнов. Выполняет сохранение основного датасета, метаданных и отчёта качества с единообразным именованием.

## Модуль

`src/bioetl/pipelines/chembl/common/base.py`

## Наследование

Сервис реализует протокол `WriteService` (Protocol) и предоставляет специализированную реализацию для всех ChEMBL-пайплайнов.

## Основные методы

### `save(self, df: pd.DataFrame, artifacts: WriteArtifacts, options: StageExecutionOptions, *, context: StageContextProtocol, runtime: StageRuntimeContext) -> WriteResult`

Сохраняет DataFrame в CSV по сформированному пути (если не *dry_run*), вызывает `_write_quality_report` для отчета качества, записывает файл метаданных (YAML) и манифест запуска (JSON), при расширенном режиме вызывает дополнительную запись метаданных, если определена.

**Параметры:**

- `df` — DataFrame с данными для сохранения
- `artifacts` — объект `WriteArtifacts` с путями к артефактам
- `options` — опции выполнения стадии
- `context` — контекст выполнения стадии
- `runtime` — контекст времени выполнения

**Процесс сохранения:**

1. Формирование путей для выходного CSV-файла (включая дату и название сущности)
2. Сохранение основного датасета: запись DataFrame в CSV (если не dry_run)
3. Запись отчёта по качеству через `_write_quality_report`
4. Запись метаданных: сохранение YAML-файла метаданных
5. Запись манифеста: сохранение JSON-манифеста запуска
6. Дополнительная запись метаданных (в расширенном режиме, если определена)

**Возвращает:** `WriteResult` с информацией о записанных файлах.

### `write_metadata(self, output_dir: Path, artifacts: WriteArtifacts, df: pd.DataFrame | None, *, dry_run: bool) -> None`

Метод совместимости (не выполняет действий, метаданные уже сохраняются в `save()`).

**Параметры:**

- `output_dir` — директория вывода
- `artifacts` — объект `WriteArtifacts` с путями
- `df` — DataFrame с данными (опционально)
- `dry_run` — режим без записи (опционально)

**Примечание:** Метод оставлен для совместимости, фактическое сохранение метаданных выполняется в методе `save()`.

## Единообразное именование

Сервис обеспечивает единообразное именование файлов для всех ChEMBL-пайплайнов:

- Основной датасет: `<entity>_<run_stem>.csv`
- Метаданные: `<entity>_<run_stem>_meta.yaml`
- QC-отчёт: `<entity>_<run_stem>_qc.csv`

## Related Components

- **WriteService**: базовый класс сервиса записи
- **UnifiedOutputWriter**: унифицированный writer для записи (см. `docs/02-pipelines/04-unified-output-writer.md`)
- **ActivityWriteService**: специализированный сервис для activity (см. `docs/02-pipelines/chembl/activity/13-activity-chembl-artifacts.md`)

