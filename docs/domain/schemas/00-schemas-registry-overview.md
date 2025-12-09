# Schemas Registry Overview

BioETL uses Pandera schemas as a central mechanism to validate all datasets before they are written.

All public schemas live in the `bioetl.domain.schemas` package and are exposed through the central registration helper `register_schemas` (see `src/bioetl/domain/schemas/__init__.py`). The helper populates the default `SchemaRegistry` with deterministic column order for every entity.

## Core Principles

- **Validate-before-write**: Every dataset must be validated against a Pandera schema before it is written to disk
- **Strict and ordered schemas**: Schemas are configured with `strict=True`, `ordered=True`, and `coerce=True` to enforce column presence, order, and types
- **Deterministic column order**: Column order in output files follows the order defined in the schema

## Using the Registry

Typical usage pattern:

1. Call `register_schemas(schema_provider)` once at startup to register all ChEMBL schemas and aliases (`<entity>`, `<entity>_input`, `<entity>_output`).
2. Look up the schema by name using the central registry (`schema_provider.get_schema(name)`).
3. Apply any lightweight normalization required to match the schema (for example, ensuring all required columns exist).
4. Call `schema.validate(df)` before writing the dataframe to storage.

This pattern ensures that all written datasets respect the same contracts and can be validated consistently in CI.

## Relationship to Datatype Docs

Human-readable column order for ChEMBL entities is documented in `docs/schemas/01-chembl-schema-columns.md` and in the per-entity pipeline docs under `docs/application/pipelines/chembl/`.

Pandera schemas provide the executable specification of these tables, including:

- Column names and order
- Data types and nullability rules
- Constraints and allowed values where applicable

Both views are complementary: datatype documentation explains the business meaning, while schemas enforce the technical contract.

## Related Components

- **SchemaRegistry**: реестр схем (`src/bioetl/domain/schemas/registry.py`)
- **DefaultValidationService**: сервис валидации (`src/bioetl/domain/validation/service.py`)
- **OUTPUT_COLUMN_ORDER**: порядок колонок для детерминированной записи (`src/bioetl/domain/schemas/chembl/*`)

