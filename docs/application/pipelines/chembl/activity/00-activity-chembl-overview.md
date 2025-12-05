# 00 Activity Chembl Overview

## Pipeline
- Используется универсальный `ChemblEntityPipeline` (`src/bioetl/application/pipelines/chembl/pipeline.py`) с базой `ChemblPipelineBase`.
- Схема и контракт: `domain/schemas/chembl/activity.py`.

## Компоненты
- `ChemblExtractorImpl` — API/CSV/ID-list режимы через `input_mode`.
- `ChemblTransformerImpl` — приводит к `activity`-схеме, убирает строки с null в обязательных столбцах.
- Post-transform: `HashColumnsTransformer`, `IndexColumnTransformer`, `DatabaseVersionTransformer`, `FulldateTransformer`.
- `ValidationService` + Pandera-схема `chembl.activity`.
- `UnifiedOutputWriter` — стабильная сортировка, атомарная запись `<output>/activity.csv`, `meta.yaml`.

## Особенности
- `primary_key`: берётся из `PipelineConfig.primary_key` или `pipeline.primary_key`, по умолчанию `activity_id`.
- `input_mode`: `api` (ChEMBL), `csv` (полный датасет), `id_only` (список ID → дозагрузка через API) с `csv_options`.
- Хеши рассчитываются на нормализованных данных; ключи — `hashing.business_key_fields`.

## Конфигурация
- `configs/pipelines/chembl/activity.yaml` (совместно с `configs/profiles/chembl_default.yaml`).
- Рекомендация: для smoke → `--profile dev --limit 100 --dry-run`; для прод — полный запуск без `--dry-run`.
