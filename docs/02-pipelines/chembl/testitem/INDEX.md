# TestItem ChEMBL Documentation

Документация по пайплайну обработки тестовых элементов из ChEMBL.

## Обзор

- [00 TestItem ChEMBL Overview](00-testitem-chembl-overview.md) — основной пайплайн для тестовых элементов с обогащением через PubChem

## Компоненты пайплайна

- [01 TestItem ChEMBL Methods](01-testitem-chembl-methods.md) — приватные методы пайплайна
- [02 TestItem ChEMBL Thin Pipeline](02-testitem-chembl-thin-pipeline.md) — "тонкий" вариант пайплайна без PubChem
- [03 TestItem ChEMBL Pipeline Options](03-testitem-chembl-pipeline-options.md) — параметры командной строки

## Обогащение данными

- [04 TestItem ChEMBL Parent Enrichment Preparation](04-testitem-chembl-parent-enrichment-preparation.md) — подготовка данных для обогащения родительских ID
- [05 TestItem ChEMBL Parent Enrichment Result](05-testitem-chembl-parent-enrichment-result.md) — результат обогащения родительских ID
- [06 TestItem ChEMBL Parent Lookup Prepared Data](06-testitem-chembl-parent-lookup-prepared-data.md) — подготовленные данные для поиска
- [07 TestItem ChEMBL Parent Lookup Stats](07-testitem-chembl-parent-lookup-stats.md) — статистика обогащения родительских ID

## Утилиты

- [08 TestItem ChEMBL Requested IDs Snapshot](08-testitem-chembl-requested-ids-snapshot.md) — накопление идентификаторов без перегрузки памяти

## Схемы данных

- **TestItemSchema**: схема для отдельного элемента (см. `docs/02-pipelines/schemas/01-testitem-schema.md`)
- **TestitemsSchema**: схема для полного набора (см. `docs/02-pipelines/schemas/02-testitems-schema.md`)

## Related Components

- **ChemblBasePipeline**: базовый класс для ChEMBL-пайплайнов (см. `docs/02-pipelines/chembl/common/05-chembl-base-pipeline.md`)
- **PubChemClient**: клиент для PubChem (см. `docs/02-pipelines/clients/02-pubchem-client.md`)

