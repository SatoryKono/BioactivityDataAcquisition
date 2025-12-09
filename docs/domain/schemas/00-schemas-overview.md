# Schemas Overview

## Coverage
- **ActivityTableSchema / AssayTableSchema** — нормализованные таблицы активности и ассая (BAO IDs, единицы измерения, нормализованные значения).
- **MoleculeTableSchema** — идентификаторы соединений, иерархия, свойства, структурные представления и статусы допуска.
- **PublicationTableSchema** — DOI/PubMed, тип документа, метаданные журнала и релиз ChEMBL.
- **TargetTableSchema** — идентификаторы таргетов, тип, таксономия, UniProt и кросс-референсы.
- **CellTableSchema / TissueTableSchema** — справочники клеточных линий и тканей.

Все схемы наследуют `BaseGeneratedColumnsSchema`, добавляющую служебные колонки `hash_row`, `hash_business_key`, `index`, `database_version`, `extracted_at` в фиксированном порядке.

## Deterministic ordering
- Каждая схема экспортирует `OUTPUT_COLUMN_ORDER`, где сначала идут бизнес-колонки, затем служебные.
- Реестр схем (`register_schemas` в `src/bioetl/domain/schemas/__init__.py`) использует эти константы, поэтому порядок идентичен для валидации и записи.
- Подробный порядок колонок для ChEMBL-схем приведён в `docs/schemas/01-chembl-schema-columns.md`.

## Usage
Schemas are applied in the validate stage via `ValidationService`. Column order is fixed and drives hashing and deterministic writes. Business constraints (identifiers, ranges, nullability) ensure stable, reproducible datasets.

Полный регламент требований и процесса описан в `01-pandera-validation-rules.md`.