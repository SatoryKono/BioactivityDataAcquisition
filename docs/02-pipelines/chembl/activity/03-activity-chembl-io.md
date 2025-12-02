# 03 Activity ChEMBL IO

## Описание

`ActivityWriter` — класс этапа сохранения результатов пайплайна активности. Записывает финальный набор данных на диск и генерирует артефакты контроля качества (QC). Наследуется от `StageABC` и реализует интерфейс стадии записи.

## Модуль

`src/bioetl/pipelines/chembl/activity/stages.py`

## Наследование

Класс наследуется от `StageABC` и реализует интерфейс стадии записи результатов.

## Основной метод

### `write(self, df: pd.DataFrame, artifacts: WriteArtifacts, *, run_stem: str, output_dir: Path) -> WriteResult`

Сохраняет результаты обработки данных активности.

**Параметры:**
- `df` — DataFrame с обработанными данными
- `artifacts` — объект `WriteArtifacts` с путями для артефактов
- `run_stem` — основа имени файла (например, `"activity_run_001"`)
- `output_dir` — директория для сохранения результатов

**Процесс записи:**

1. Подготовка артефактов: создание `RunArtifacts` с путями для данных, метаданных и манифеста
2. Запись данных: использование `UnifiedOutputWriter.write_dataset_atomic` для атомарной записи DataFrame
3. Генерация QC-отчётов: создание отчётов о качестве данных (если требуется)
4. Возврат результата: возврат `WriteResult` с информацией о записанных файлах

**Возвращает:** `WriteResult` с метриками записи и путями к артефактам.

## Артефакты

Стадия создаёт следующие артефакты:
- `<run_stem>.csv` или `<run_stem>.parquet` — основные данные
- `<run_stem>_meta.yaml` — метаданные пайплайна
- `<run_stem>_manifest.json` — манифест с путями к артефактам
- QC-отчёты (если включены)

## Related Components

- **UnifiedOutputWriter**: унифицированный writer для записи результатов (см. `docs/02-pipelines/04-unified-output-writer.md`)
- **ActivityArtifactPlanner**: планировщик артефактов для определения путей (см. `docs/02-pipelines/chembl/activity/09-activity-chembl-artifacts.md`)

