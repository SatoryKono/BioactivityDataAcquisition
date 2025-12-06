# 00 Testitem Chembl Overview

## Pipeline
- Универсальный `ChemblEntityPipeline` (`src/bioetl/application/pipelines/chembl/pipeline.py`) поверх `ChemblPipelineBase`.
- Схема: `domain/schemas/chembl/testitem.py`.

## Компоненты
- `ChemblExtractorImpl` — `input_mode` `api|csv|id_only`.
- `ChemblTransformerImpl` — нормализация под Pandera-схему, удаление строк с пустыми обязательными полями.
- Пост-цепочка: хеши, индекс, версия базы, дата.
- `UnifiedOutputWriter` — стабильная сортировка по бизнес-ключам, атомарная запись.

## Особенности
- `primary_key`: из конфига или `testitem_id` по умолчанию.
- `input_mode=csv` позволяет прогонять офлайн выгрузки; `id_only` подтягивает записи по списку ID.
- Хеши рассчитываются на нормализованных данных; сортировка стабилизирует вывод перед записью.

## Связи
- TestItem используется Activity-пайплайном. Вывод: `testitem.csv` + `meta.yaml` через атомарную запись.
