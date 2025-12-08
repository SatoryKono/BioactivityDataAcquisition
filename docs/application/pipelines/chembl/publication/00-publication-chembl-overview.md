# Publication Chembl Overview

## Pipeline

- Универсальный `ChemblPipelineBase` (`src/bioetl/application/pipelines/chembl/base.py`).
- Схема: `domain/schemas/chembl/publication.py`.

## Компоненты

- `ChemblExtractorImpl` — API/CSV/ID-list режимы (`input_mode`).
- `ChemblTransformerImpl` — выравнивает столбцы под Pandera-схему, удаляет строки с null в обязательных полях.
- Пост-цепочка базового пайплайна: хеши, индекс, версия ChEMBL, дата.

## Особенности

- `primary_key`: из конфига или `document_id` по умолчанию.
- `input_mode=csv|id_only|api`; при `id_only` фильтр `<primary_key>__in` формируется автоматически.
- Хеши и сортировка завязаны на `hashing.business_key_fields`.

## Связи

- Публикации нужны Activity/Assay для ссылок на источники. Запись: `document.csv` + `meta.yaml` через `UnifiedOutputWriter` (атомарно, checksum).

## Диаграммы
- Flowchart: `docs/application/pipelines/chembl/publication/diagrams/flow/publication-workflow.mmd`
- Sequence: `docs/application/pipelines/chembl/publication/diagrams/sequence/publication-main-sequence.mmd`
- Class: `docs/application/pipelines/chembl/publication/diagrams/class/publication-pipeline-class.mmd`