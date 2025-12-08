# Assay Chembl Overview

## Pipeline

Ассей‑пайплайн использует универсальный `ChemblPipelineBase` (`src/bioetl/application/pipelines/chembl/base.py`) и отличается только конфигурацией (`entity="assay"`, схема, primary key, hashing‑настройки).

## Компоненты

- `ChemblExtractorImpl` (`src/bioetl/application/pipelines/chembl/extractor.py`) — поддерживает режимы `input_mode=api|csv|id_only` и строит `RecordSource` для ChEMBL в зависимости от конфига.
- `ChemblTransformerImpl` (`src/bioetl/application/pipelines/chembl/transformer.py`) —
  - применяет общую цепочку трансформаций: `pre_transform -> do_transform -> normalize -> serialize_nested -> enforce_schema -> drop_nulls_in_required_columns`;
  - для `assay`‑сущности использует контракт `PipelineSchemaModel` (`domain/schemas/pipeline_contracts.py`) и Pandera‑схему `chembl.assay`, поэтому поля `assay_classifications`, `assay_parameters` и др. нормализуются и сериализуются детерминированно (через `_serialize_dict`/`_serialize_list`).
- Post‑transform цепочка базового пайплайна: `HashColumnsTransformerImpl`, `IndexColumnTransformerImpl`, `DatabaseVersionTransformerImpl`, `FulldateTransformerImpl` (собирается через `default_post_transformer`).
- `ValidationService` + Pandera‑схема `chembl.assay` гарантируют порядок и типы колонок.
- `UnifiedOutputWriter` — стабильная сортировка, атомарная запись `<output>/assay.csv` и `meta.yaml`.

## Особенности

- `primary_key`: из `PipelineConfig.primary_key` или `pipeline.primary_key`, по умолчанию `assay_chembl_id` (см. `configs/pipelines/chembl/assay.yaml`).
- Входные режимы: `api` (полный выгруз ChEMBL), `csv` (локальный датасет), `id_only` (список `assay_chembl_id` с дозагрузкой через API; фильтр `<primary_key>__in` формируется автоматически).
- Бизнес‑ключи для хеширования задаются в секции `quality.hashing.business_key_fields` и используются пост‑цепочкой.

## Связи

Данные ассеев используются Activity‑пайплайном для контекста экспериментов; общие компоненты (`ValidationService`, `UnifiedOutputWriter`, `HashService`) обеспечивают консистентную запись и QC для всех ChEMBL‑пайплайнов.

## Конфигурация

- `configs/pipelines/chembl/assay.yaml` (профиль `chembl_default`).
- Smoke: `--profile dev --limit 100 --dry-run`; прод — полный запуск без `--dry-run`.

## Диаграммы

- Flowchart: `docs/application/pipelines/chembl/assay/diagrams/flow/assay-workflow.mmd`
- Sequence: `docs/application/pipelines/chembl/assay/diagrams/sequence/assay-main-sequence.mmd`
- Class: `docs/application/pipelines/chembl/assay/diagrams/class/assay-pipeline-class.mmd`