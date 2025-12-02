# TestItem ChEMBL Documentation

Документация по пайплайну обработки тестовых элементов из ChEMBL.

## Обзор

- [00 TestItem ChEMBL Overview](00-testitem-chembl-overview.md) — основной пайплайн для тестовых элементов с обогащением через PubChem

## Компоненты пайплайна

- [01 TestItem ChEMBL Methods](01-testitem-chembl-methods.md) — приватные методы пайплайна
- [02 ChEMBL TestItem Thin Pipeline](02-chembl-testitem-thin-pipeline.md) — "тонкий" вариант пайплайна без PubChem
- [03 TestItem Pipeline Options](03-testitem-pipeline-options.md) — параметры командной строки

## Обогащение данными

- [04 Parent Enrichment Preparation](04-parent-enrichment-preparation.md) — подготовка данных для обогащения родительских ID
- [05 Parent Enrichment Result](05-parent-enrichment-result.md) — результат обогащения родительских ID
- [06 Parent Lookup Prepared Data](06-parent-lookup-prepared-data.md) — подготовленные данные для поиска
- [07 Parent Lookup Stats](07-parent-lookup-stats.md) — статистика обогащения родительских ID

## Утилиты

- [08 Requested IDs Snapshot](08-requested-ids-snapshot.md) — накопление идентификаторов без перегрузки памяти

## Схемы данных

- **TestItemSchema**: схема для отдельного элемента (см. `docs/02-pipelines/schemas/01-testitem-schema.md`)
- **TestitemsSchema**: схема для полного набора (см. `docs/02-pipelines/schemas/02-testitems-schema.md`)

## Related Components

- **ChemblBasePipeline**: базовый класс для ChEMBL-пайплайнов (см. `docs/02-pipelines/chembl/common/05-chembl-base-pipeline.md`)
- **PubChemClient**: клиент для PubChem (см. `docs/02-pipelines/clients/02-pubchem-client.md`)

