# Pipeline Review Checklist

Use this template when reviewing an existing or new pipeline.
Copy it into the PR description or an issue and fill in the fields.

- **Pipeline name (entity/provider)**: `...`
- **Pipeline ID**: `<entity>_<provider>`
- **Config file**: `configs/pipelines/<provider>/<entity>.yaml`
- **Schema module**: `src/bioetl/domain/schemas/<provider>/<entity>.py`

---

## 1. Architecture and Placement

- [ ] Pipeline code is located at `src/bioetl/application/pipelines/<provider>/<entity>/`.
- [ ] Modules/files follow `snake_case`; classes follow `PascalCase` with meaningful suffixes.
- [ ] No domain or infrastructure logic is implemented directly in the application layer pipeline.

## 2. Pipeline Folder Structure

- [ ] The folder contains all required stage modules:
  - [ ] `extract.py`
  - [ ] `transform.py`
  - [ ] `validate.py`
  - [ ] `export.py`
  - [ ] `__init__.py`
- [ ] Stage responsibilities are separated (no export logic in `transform.py`, etc.).
- [ ] Stage APIs are clear:
  - [ ] Extract returns iterable/generator of `pd.DataFrame` chunks.
  - [ ] Transform and validate return `pd.DataFrame`.
  - [ ] Export returns a `WriteResult` (or equivalent).

## 3. Pipeline ID and Registry

- [ ] Pipeline ID in YAML is `<entity>_<provider>` and matches folder names.
- [ ] `PIPELINE_REGISTRY` in `application/pipelines/registry.py` contains an entry for this ID.
- [ ] The registry entry uses the correct base pipeline class for the provider.
- [ ] Provider is present in the `ProviderId` enum and related config models.

## 4. Pandera Schema and Domain Layer

- [ ] Schema module exists: `src/bioetl/domain/schemas/<provider>/<entity>.py`.
- [ ] Schema class is named `<Entity>Schema` and inherits from `DataFrameModel` / `SchemaModel`.
- [ ] All business columns of the final DataFrame are defined with correct types and constraints.
- [ ] System columns are defined:
  - [ ] `hash_row`
  - [ ] `hash_business_key`
  - [ ] `index`
  - [ ] `database_version`
  - [ ] `extracted_at`
- [ ] Pandera Config enforces:
  - [ ] `strict = True`
  - [ ] `coerce = True`
  - [ ] `ordered = True`
- [ ] Column order constant (`*_OUTPUT_COLUMNS` / `*_COLUMN_ORDER`) exists and includes all columns.
- [ ] Schema is registered in `domain/schemas/registry.py` with correct name and `column_order`.

## 5. Pydantic Configs and Models

- [ ] Pipeline uses `PipelineConfig` (or a compatible Pydantic model) instead of raw dicts.
- [ ] Config model forbids extra fields (`extra = "forbid"`/equivalent).
- [ ] If complex provider JSON is used, it is modeled with Pydantic `*Model` classes (not ad‑hoc dicts).

## 6. YAML Configuration

- [ ] YAML exists at `configs/pipelines/<provider>/<entity>.yaml`.
- [ ] `id`, `provider`, and `entity` are consistent with each other and with the code structure.
- [ ] `primary_key` is explicitly set and matches the business key column.
- [ ] `input_mode` (`csv` / `id_only` / `api` / `auto_detect`) matches the actual extract implementation.
- [ ] `input_path` (if required) and `output_path` are valid and match export logic.
- [ ] `provider_config` includes all required provider fields (base URL, timeout, retries, rate limiting, etc.).
- [ ] Pipeline‑specific options in `pipeline` section are documented and used in code.
- [ ] `bioetl validate-config --config configs/pipelines/<provider>/<entity>.yaml` passes.

## 7. Logging

- [ ] Pipeline uses the injected logger (`UnifiedLogger` adapter), not `print` or bare `logging.getLogger`.
- [ ] Important events (filters, exports, special branches) are logged as structured data.
- [ ] Logs include context fields (`pipeline`, `provider`, `entity`, `run_id`).
- [ ] No secrets or large payloads (full DataFrames / full JSON) are logged.

## 8. CLI Integration

- [ ] Pipeline can be started via:
  - [ ] `bioetl run --pipeline-name <entity>_<provider> --config configs/pipelines/<provider>/<entity>.yaml`.
- [ ] `--dry-run` correctly executes extract→transform→validate without performing a real export (as per project rules).
- [ ] (If applicable) `bioetl smoke-run` works for this pipeline with a small limit.

## 9. Tests

- [ ] Tests exist at `tests/bioetl/application/pipelines/<provider>/<entity>/`.
- [ ] Unit tests cover:
  - [ ] `extract`
  - [ ] `transform`
  - [ ] `validate`
  - [ ] `export`
- [ ] All external dependencies (network, heavy I/O) are mocked in unit tests.
- [ ] There are tests that intentionally feed invalid data and assert Pandera / validation errors.
- [ ] Golden tests exist and compare outputs to golden artifacts (CSV, `meta.yaml`, reports) when appropriate.
- [ ] At least one integration/smoke test runs the full pipeline end‑to‑end.
- [ ] Tests verify deterministic behaviour: stable sort, repeated hashes, exact column order.
- [ ] Overall coverage is not reduced and remains at or above the project target for critical modules.

## 10. User Documentation and Diagrams

- [ ] Overview document exists:
  - [ ] `docs/application/pipelines/<provider>/<entity>/00-<entity>-<provider>-overview.md`.
- [ ] Document contents are in sync with the code (file names, classes, IDs, config keys).
- [ ] Document includes CLI usage examples and describes key configuration parameters.
- [ ] Diagrams (if required) are present as text sources (`.mmd` / `.puml`) under `diagrams/flow`, `diagrams/sequence`, and/or `diagrams/class`.
- [ ] `tests/project_rules/test_pipeline_structure.py` passes for this pipeline.

## 11. Determinism and Data Quality Invariants

- [ ] Final DataFrame is sorted deterministically (`sort_values` with fixed keys) before export.
- [ ] Column order strictly follows the declared `*_OUTPUT_COLUMNS` / `*_COLUMN_ORDER`.
- [ ] Hash columns (`hash_row`, `hash_business_key`) are populated via standard hashing services.
- [ ] Timestamps (e.g. `extracted_at`) are in UTC and ISO format.
- [ ] Exports use atomic write strategy via the unified output writer.
- [ ] All data passes Pandera validation before being written; validation errors are not silently ignored.

---

**Reviewer notes / findings:**

- ...
