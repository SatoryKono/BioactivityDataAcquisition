# 00 QC Artifacts Overview

Every dataset produced by BioETL is accompanied by quality control artifacts that capture metadata, validation results, and summary statistics.

These artifacts are essential for enforcing determinism and blocking regressions in CI.

## meta.yaml

Each output dataset has a `meta.yaml` file stored alongside it. It includes at least the following fields:

- `pipeline_version` — версия пайплайна
- `git_commit` — Git commit hash
- `config_hash` — хеш конфигурации
- `schema_version` — версия схемы
- `row_count` — количество строк
- `blake2_checksum` — контрольная сумма Blake2
- `business_key_hash` — хеш бизнес-ключа
- `generated_at_utc` — время генерации в UTC

These fields allow runs to be traced back to exact code, configuration, input data, and business keys.

## Quality Report CSV

For each dataset, a `*_quality_report.csv` file summarizes data quality metrics.

The format and column order are fixed:

- `section` — секция отчёта
- `metric` — метрика
- `column` — колонка
- `value` — значение
- `count` — количество
- `ratio` — соотношение
- `lower_bound` — нижняя граница
- `upper_bound` — верхняя граница

Sections include at least `summary`, `missing`, `distribution`, `outliers`, and any custom sections using the `custom:*` prefix.

## JSON QC File

A `*_qc.json` file captures a machine-readable summary of QC metrics. Keys are serialized in a canonical, deterministic order to support byte-for-byte comparisons.

Typical fields include:

- `row_count` — количество строк
- `deduplicated_count` — количество после дедупликации
- `duplicate_ratio` — соотношение дубликатов
- `business_key_fields` — поля бизнес-ключа
- `custom_metrics` — пользовательские метрики

## Correlation Reports

Some datasets may also have `*_correlation_report.csv` files that capture feature correlations.

The first column is always `feature`, and the remaining columns list other features in alphabetical order.

## Golden Checks and CI

QC artifacts are used together with golden datasets in CI:

- Golden jobs compare current outputs and QC files byte-for-byte against stored golden artifacts when the `--golden` flag is used
- Any deviation in data, metadata, or QC summaries causes a non-zero exit code and blocks merging

This mechanism ensures that schema, data quality, and determinism invariants remain enforced over time.

## Related Components

- **UnifiedOutputWriter**: унифицированный writer для записи (см. `docs/02-pipelines/04-unified-output-writer.md`)
- **DefaultValidationService**: сервис валидации (см. `docs/02-pipelines/06-validation-service.md`)

