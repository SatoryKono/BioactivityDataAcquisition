# 00 Document Chembl Overview

## Pipeline

- Универсальный `ChemblEntityPipeline` (`src/bioetl/application/pipelines/chembl/pipeline.py`) с базой `ChemblPipelineBase`.
- Схема: `domain/schemas/chembl/document.py`.

## Компоненты

- `ChemblExtractorImpl` — API/CSV/ID-list режимы (`input_mode`).
- `ChemblTransformerImpl` — выравнивает столбцы под Pandera-схему, удаляет строки с null в обязательных полях.
- Пост-цепочка базового пайплайна: хеши, индекс, версия ChEMBL, дата.

## Особенности

- `primary_key`: из конфига или `document_id` по умолчанию.
- `input_mode=csv|id_only|api`; при `id_only` фильтр `<primary_key>__in` формируется автоматически.
- Хеши и сортировка завязаны на `hashing.business_key_fields`.

## Связи

- Документы нужны Activity/Assay для ссылок на публикации. Запись: `document.csv` + `meta.yaml` через `UnifiedOutputWriter` (атомарно, checksum).
