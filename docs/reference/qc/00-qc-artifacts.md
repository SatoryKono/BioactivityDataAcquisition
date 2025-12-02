# QC Artifacts

Помимо основных данных (`.csv` / `.parquet`), пайплайны генерируют артефакты контроля качества (Quality Control).

## 1. meta.yaml

Файл метаданных запуска. Обеспечивает отслеживаемость (provenance).

```yaml
pipeline_version: "1.0.0"
chembl_release: "chembl_34"
run_id: "manual_run_20241202"
timestamp_utc: "2024-12-02T12:00:00Z"
row_count: 1500
checksums:
  activity.csv: "sha256:..."
```

## 2. quality_report_table.csv

Таблица с метриками по каждой колонке. Позволяет быстро оценить качество данных.

| Колонка | Описание |
|---------|----------|
| `column_name` | Имя колонки |
| `dtype` | Тип данных |
| `null_count` | Количество пропущенных значений |
| `null_percent` | Процент пропусков |
| `unique_count` | Количество уникальных значений |
| `min_value` | Минимальное значение (для чисел) |
| `max_value` | Максимальное значение (для чисел) |
| `mean_value` | Среднее значение (для чисел) |

## 3. correlation_report_table.csv

Матрица корреляций Пирсона для всех числовых колонок. Позволяет выявить линейные зависимости.

| column_a | column_b | correlation |
|----------|----------|-------------|
| pchembl_value | standard_value | -0.75 |

