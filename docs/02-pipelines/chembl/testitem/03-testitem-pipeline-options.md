# 03 TestItem Pipeline Options

## Описание

`TestitemPipelineOptions` — класс параметров командной строки для запуска пайплайна тестовых элементов. Содержит настройки путей ввода/вывода, лимиты выборки, флаги (например, использование PubChem) и другие опции.

## Модуль

`src/bioetl/library/pipelines/testitem/cli.py`

## Наследование

Класс наследуется от `object` и представляет собой dataclass или Pydantic модель для хранения параметров CLI.

## Основные поля

Класс содержит следующие поля:

- `input_path` — путь к входному файлу (CSV/Parquet) с ID для batch-извлечения
- `output_dir` — директория для сохранения результатов
- `limit` — лимит выборки записей
- `use_pubchem` — флаг использования PubChem для обогащения
- `batch_size` — размер батча для обработки
- И другие параметры согласно спецификации

## Использование

Параметры используются при запуске пайплайна через CLI:

```python
from bioetl.library.pipelines.testitem.cli import TestitemPipelineOptions

options = TestitemPipelineOptions(
    input_path="data/input/testitem_ids.csv",
    output_dir="data/output/testitem/",
    limit=1000,
    use_pubchem=True
)
```

## Related Components

- **TestItemChemblPipeline**: использует опции для настройки выполнения (см. `docs/02-pipelines/chembl/testitem/00-testitem-chembl-overview.md`)
- **CLI**: интерфейс командной строки (см. `docs/reference/cli/cli-overview.md`)

