# 00 Target Chembl Overview

## Pipeline
- Универсальный `ChemblEntityPipeline` (`src/bioetl/application/pipelines/chembl/pipeline.py`) поверх `ChemblPipelineBase`.
- Схема: `domain/schemas/chembl/target.py`.

## Компоненты
- `ChemblExtractorImpl` — API/CSV/ID-list, управляется `input_mode`.
- `ChemblTransformerImpl` — выравнивание под Pandera-схему, очистка обязательных полей.
- Post-transform: хеши, индекс, версия ChEMBL, дата извлечения.
- Валидация через `ValidationService`.

## Особенности
- `primary_key`: из конфига или `target_id` по умолчанию.
- `input_mode`: `api|csv|id_only`; `id_only` формирует фильтр `<primary_key>__in`.
- Стабильная сортировка и хеши по бизнес-ключам перед записью.

## Связи
- Target-данные потребляются Activity/Assay. Итог: `target.csv` + `meta.yaml`, атомарная запись.

## Диаграммы
- Flowchart: `docs/application/pipelines/chembl/target/diagrams/flow/target-workflow.mmd`
- Sequence: `docs/application/pipelines/chembl/target/diagrams/sequence/target-main-sequence.mmd`
- Class: `docs/application/pipelines/chembl/target/diagrams/class/target-pipeline-class.mmd`