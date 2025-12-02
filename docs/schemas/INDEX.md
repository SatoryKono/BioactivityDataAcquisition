# Data Schemas

This section describes the Pandera schemas used by BioETL to validate all tabular datasets before writing them.

Start with the overview document for the schema registry and then follow links to entity-specific schema descriptions.

## Documents

- **00-schemas-registry-overview.md** — High-level description of the central schema registry and common conventions

## Entity Schemas

- **26-document-schema.md** — схема данных документов ChEMBL (см. `docs/02-pipelines/schemas/26-document-schema.md`)
- **27-testitem-schema.md** — схема для отдельного тестового элемента
- **28-testitems-schema.md** — схема для полного набора тестовых элементов
- **29-target-schema.md** — схема для сущности target (см. `docs/02-pipelines/schemas/29-target-schema.md`)
- **30-assay-schema.md** — схема для сущности assay (см. `docs/02-pipelines/schemas/30-assay-schema.md`)

Additional documents for concrete entities such as activity, assay, and target can be added under this directory as the project evolves.

