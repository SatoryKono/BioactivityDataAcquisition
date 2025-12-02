# Assay ChEMBL Documentation

Документация по пайплайну обработки данных assay из ChEMBL.

## Обзор

- [00 Assay ChEMBL Overview](00-assay-chembl-overview.md) — основной пайплайн для выгрузки данных об ассаях

## Компоненты пайплайна

- [01 Assay ChEMBL Methods](01-assay-chembl-methods.md) — приватные методы пайплайна
- [02 Assay Normalizer](02-assay-normalizer.md) — нормализатор данных assay
- [03 Assay Payload Parser](03-assay-payload-parser.md) — парсер payload'ов ассая

## Схемы данных

- **AssaySchema**: схема валидации данных assay (см. `docs/02-pipelines/schemas/04-assay-schema.md`)

## Related Components

- **ChemblBasePipeline**: базовый класс для ChEMBL-пайплайнов (см. `docs/02-pipelines/chembl/common/05-chembl-base-pipeline.md`)
- **ChemblWriteService**: сервис записи для ChEMBL-пайплайнов (см. `docs/02-pipelines/chembl/common/04-chembl-write-service.md`)

