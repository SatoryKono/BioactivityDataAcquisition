# 01 Write Artifacts

## Описание

`WriteArtifacts` — структура данных для хранения путей выходных файлов пайплайна. Содержит поля: `dataset` (имя основного набора данных), `data_path` (путь к файлу данных), `meta_path` (путь к YAML-файлу метаданных), `manifest_path` (путь к JSON-манифесту), `quality_report_path` (путь к CSV файлу с отчётом качества), `qc_summary_path` (путь для сводки QC) и словарь `extra` для дополнительных артефактов. Эти пути заполняются в процессе сохранения результатов (например, *ChemblWriteService* формирует их имена).

## Модуль

`src/bioetl/core/io/artifacts.py`

## Наследование

Класс является dataclass.

## Структура

Артефакты содержат следующие поля:

- `dataset: str` — имя основного набора данных
- `data_path: Path` — путь к файлу данных (CSV/Parquet)
- `meta_path: Path` — путь к YAML-файлу метаданных
- `manifest_path: Path` — путь к JSON-манифесту запуска
- `quality_report_path: Path` — путь к CSV файлу с отчётом качества
- `qc_summary_path: Path` — путь для сводки QC
- `extra: dict[str, Any]` — словарь для дополнительных артефактов

## Использование

Артефакты используются сервисами записи для передачи информации о путях выходных файлов:

```python
artifacts = WriteArtifacts(
    dataset="target",
    data_path=Path("output/target_data.csv"),
    meta_path=Path("output/target_meta.yaml"),
    ...
)
```

## Related Components

- **ChemblWriteService**: формирует артефакты при сохранении (см. `docs/02-pipelines/chembl/common/04-chembl-write-service.md`)
- **PipelineOutputService**: использует артефакты для сохранения (см. `docs/02-pipelines/core/00-pipeline-output-service.md`)

