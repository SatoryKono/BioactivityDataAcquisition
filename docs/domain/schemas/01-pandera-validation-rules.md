# 01 Pandera Validation Rules

## Purpose and Scope

This document defines the mandatory rules and extended guidance for validating tabular data in BioETL using Pandera 0.27+ on Python 3.14. It standardises how schemas are authored, registered, and executed through the unified `ValidationService` and the global `SchemaRegistry`. The rules apply to every pipeline and entity (Activity, Assay, Target, Document, TestItem, etc.) across all environments (development, CI, production). Objectives:

- Provide an executable specification of table structure via Pandera schemas.
- Increase resilience to upstream data defects.
- Preserve deterministic outputs (fixed schema, order, hashing).
- Enable traceable and auditable data quality.
- Guarantee uniform validation behaviour across modules.

## Architectural Placement

- Schemas live in the domain layer: `src/bioetl/domain/schemas/<provider>/<entity>.py`.
- Each schema is a `pa.DataFrameModel` describing business columns and mandatory system columns.
- `Config` must set `strict=True` and `coerce=True`; use `ordered=True` where available to reinforce column order.
- Schemas are treated as the source of truth for ETL outputs and are registered in `SchemaRegistry`.
- Pipeline code invokes validation only through the `ValidationService`; direct calls to `schema.validate` in pipelines are not allowed.

## Authoring Standards

### Naming and placement

- Class name: `<Entity>Schema` (e.g., `ActivitySchema`, `TargetSchema`).
- One file per entity under `src/bioetl/domain/schemas/<provider>/<entity>.py`.
- Each module must export the schema class and `OUTPUT_COLUMN_ORDER`.
- Follow project naming policies (snake_case modules, PascalCase classes, kebab-case docs).

### Types and fields

- Declare each column with `Series[type]` and `pa.Field(...)`.
- Prefer the narrowest concrete types (`str`, `int`, `float`, `bool`, `TimestampType`). `Any` is allowed only for opaque blobs with documented justification.
- Example:

  ```python
  class TargetSchema(pa.DataFrameModel):
      target_chembl_id: Series[str] = pa.Field(
          str_matches=CHEMBL_ID_REGEX.pattern,
          description="ChEMBL ID"
      )
  ```

- Use `coerce=True` to force conversion; non-coercible values must fail validation.

### Constraints

- Use `str_matches` for identifier formats (ChEMBL, DOI, UniProt, PubChem).
- Use `isin` for enumerations (e.g., `assay_type`, `doc_type`).
- Use `ge` / `le` for numeric ranges.
- Set `nullable=True` only when the business contract explicitly allows nulls.
- Provide `description` to clarify business meaning when not obvious.

### Mandatory system columns

Every ChEMBL and most internal schemas must include the following service columns:

| Column              | Purpose                                                |
|---------------------|--------------------------------------------------------|
| `hash_row`          | 64-hex row hash (required).                            |
| `hash_business_key` | Business-key hash (often nullable but present).        |
| `index`             | Row ordinal for deterministic ordering.                |
| `database_version`  | Source release identifier.                             |
| `extracted_at`      | UTC extraction timestamp.                              |

These columns are part of the lineage and determinism chain defined in project rules (deterministic I/O, hashing, lineage metadata).

### Column order

- Preserve a dedicated constant `OUTPUT_COLUMN_ORDER` that lists all business columns first, followed by the system columns above.
- Writers must respect `OUTPUT_COLUMN_ORDER` to guarantee deterministic files and stable hashes.
- Schema definitions should match this order; avoid ad-hoc column sorting inside pipelines.

### Configuration

- `class Config:` must set `strict=True`, `coerce=True`, and, where applicable, `ordered=True`.
- Avoid custom `dtype` adapters unless documented and covered by tests.

## Inter-column Validation

- Use `@pa.dataframe_check` for cross-column rules that cannot be expressed at the field level.
- Checks must be deterministic, idempotent, and reproducible.
- Examples:
  - `value >= 0` unless `relation == "<"` where `value` may be null.
  - `unit == "pM"` implies `value_nM <= 1000`.
  - `parent_molecule_chembl_id` allowed only when `molecule_chembl_id` exists.
  - `standard_value` required when `standard_flag is True`.
- Prefer pure boolean logic; avoid external I/O or randomness in checks.

## Validation in Pipelines

- Entry point: `validated_df = self._validation_service.validate(df, entity_name)`.
- `entity_name` must match the registry key of the schema/pipeline contract.
- Validation always runs with `lazy=True` to collect all errors before raising.
- Errors are wrapped by `ValidationService` into `ValueError` enriched with entity name; pipeline error handlers follow project error policy.
- In `dry-run`, validation executes fully; write stage is skipped, and results are logged for inspection.

## Schema Registration

- Register every schema in the global registry:

  ```python
  from bioetl.domain.schemas.registry import registry

  registry.register(
      "activity",
      ActivitySchema,
      column_order=ACTIVITY_OUTPUT_COLUMNS,
  )
  ```

- Registration is mandatory and forms part of the pipeline contract (SchemaProvider/SchemaRegistry).
- Duplicate keys or missing registrations are treated as build-time errors.

## Changing Schemas and Versioning

- Any schema change is potentially breaking because it alters column set, order, constraints, or hashing behaviour.
- Requirements for schema changes:
  - Document in `CHANGELOG.md`.
  - Update golden tests and integration tests.
  - Update pipeline docs and schema docs.
  - Review downstream consumers for compatibility (QC reports, lineage, exports).
  - Keep column order stable; when adding columns, append before system columns and update `OUTPUT_COLUMN_ORDER`.
- Coordinate schema versioning with pipeline version metadata and `meta.yaml` contents.

## Testing Requirements

- Follow `task_testing.md` / testing standards: coverage ≥85% for critical schema logic.
- Minimum set:
  - Positive cases with valid data.
  - Negative cases for range/nullable/regex/category violations.
  - `dry-run` validation test to ensure behaviour without writes.
  - Golden tests for final tables (post-validate/write).
  - Property-based tests for complex cross-column checks where applicable.
- Unit tests must not hit network; fixtures should be deterministic and small.

## Data Lineage and QC Integration

- Schemas drive lineage by enforcing stable keys and by providing the columns used for `hash_row` and `hash_business_key`.
- Validation must run before QC reporting; failed validation blocks QC and write.
- QC artefacts (`quality_report_table.csv`, `correlation_report_table.csv`) rely on schema-guaranteed column availability and ordering.
- `meta.yaml` must include `pipeline_version`, `chembl_release`, `row_count`, checksums; these depend on validated, ordered data.

## Performance and Batching

- For large datasets, chunked validation is allowed if:
  - Chunk boundaries preserve deterministic ordering;
  - Each chunk is validated independently and reassembled without reshuffling rows;
  - Hash computations remain stable across runs.
- Pandera 0.27 lazy checks are efficient; avoid premature optimisation before profiling.

## Determinism and Atomicity

- Enforce type coercion before writing; rejection is preferable to silent casts.
- Maintain stable column order (`OUTPUT_COLUMN_ORDER`) and deterministic row ordering per pipeline policy.
- All file writes must be atomic (`tmp` → `os.replace`); no in-place overwrites.
- Avoid non-UTC timestamps and non-canonical serialisation.

## Validation Touchpoints

Validation is mandatory at these stages:

| Stage                       | Purpose                                         |
|-----------------------------|-------------------------------------------------|
| `extract → transform`       | Early rejection of structurally invalid rows.   |
| `validate` (main stage)     | Full schema conformance check.                  |
| Pre-write                   | Final contract enforcement before persistence.  |
| External ingest             | Shield against dirty sources prior to merge.    |

Pipelines must not skip validation in fast paths or retries.

## Documentation Requirements

- Schemas must be reflected in ETL docs under `docs/domain/schemas` and pipeline docs under `docs/application/pipelines/<provider>/<entity>/`.
- API/contract docs must reference the same column names and order.
- Any schema change requires doc updates in the same PR; stale docs are a blocker.

## Extensibility for New Entities

When introducing a new entity:

1. Create the Pandera schema in `domain/schemas/<provider>/<entity>.py`.
2. Define business fields and mandatory system columns.
3. Export `OUTPUT_COLUMN_ORDER`.
4. Register the schema in `SchemaRegistry`.
5. Update pipeline contract and configs.
6. Add tests (positive/negative, cross-column, golden).
7. Update documentation (schema doc, pipeline doc, changelog).

This workflow aligns with the project’s ABC/Default/Impl and pipeline standards.

## Operational Checklist

- [ ] Schema class uses `pa.DataFrameModel` with `Config(strict=True, coerce=True)`.
- [ ] All mandatory system columns present and ordered after business columns.
- [ ] Constraints cover identifiers, ranges, categories, and nullability.
- [ ] Cross-column checks expressed via `@pa.dataframe_check` where needed.
- [ ] Schema registered with `SchemaRegistry` and exposes `OUTPUT_COLUMN_ORDER`.
- [ ] Validation invoked through `ValidationService` with `lazy=True`.
- [ ] Tests cover positive/negative, dry-run, golden outputs; no network in unit tests.
- [ ] Docs updated (schema, pipeline, changelog); determinism and atomic writes preserved.

