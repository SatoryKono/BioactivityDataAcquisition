# Adding New Pipeline

This document describes how to introduce a new ETL pipeline into BioETL, from code placement and configuration to testing and documentation. It consolidates project rules from `docs/project`, schema guidelines, CLI contracts, and existing pipeline examples.

## 1. Architecture and Project Structure

BioETL follows Hexagonal Architecture + DDD and is split into four layers:

- **domain** – domain models, Pandera schemas, Pydantic configs, abstract ports.
- **application** – orchestration, pipelines, services.
- **infrastructure** – concrete clients, adapters, low-level services.
- **interfaces** – CLI, HTTP APIs, other external interfaces.

All source code lives under:

- `src/bioetl/`

Application-layer pipelines are located at:

- `src/bioetl/application/pipelines/<provider>/<entity>/`

where:

- **`<provider>`** – data source, e.g. `chembl`, `pubchem`.
- **`<entity>`** – domain entity, e.g. `activity`, `assay`, `new_entity`.

Example for a new ChEMBL pipeline:

- `src/bioetl/application/pipelines/chembl/new_entity/`

**Naming rules:**

- **Modules / files** – `snake_case`.
- **Classes** – `PascalCase` with meaningful suffixes: `*Client`, `*Config`, `*Impl`, etc.
- **Entities / providers** – short, lowercase, no spaces.

Pipelines **must not** mix responsibilities of different layers. Domain models and schemas stay in `domain`, infrastructure clients stay in `infrastructure`, orchestration and stages stay in `application`.

## 2. Pipeline Folder and Stage Files

Each pipeline is a subfolder:

- `src/bioetl/application/pipelines/<provider>/<entity>/`

with **mandatory** stage modules:

- `extract.py` – Extract stage.
- `transform.py` – Transform stage.
- `validate.py` – Validate stage.
- `export.py` – Export (Load) stage.
- `__init__.py`

Example:

```text
src/bioetl/application/pipelines/chembl/new_entity/
    extract.py
    transform.py
    validate.py
    export.py
    __init__.py
```

**Stage responsibilities:**

- **`extract.py`**
  - Fetches raw data from external source (API, files, DB).
  - Handles pagination / batching.
  - Performs minimal normalization (flattening JSON, basic cleanup).
  - Returns an iterable of `pd.DataFrame` chunks.

- **`transform.py`**
  - Applies business rules: cleaning, enrichment, filtering, aggregation.
  - Renames and derives fields to approach the target schema.
  - Returns a `DataFrame` matching the domain schema **without** hash/service columns.

- **`validate.py`**
  - Uses `ValidationService` + Pandera schema for the entity.
  - Ensures all expected columns are present, typed correctly, and satisfy constraints.
  - Fails fast on schema violations with detailed error information.
  - Returns the same `DataFrame`, now validated.

- **`export.py`**
  - Sorts data deterministically, adds system columns (hashes, indices, version).
  - Writes the final `DataFrame` to storage (CSV/Parquet/DB).
  - Produces run metadata (`meta.yaml` with version, counts, checksums).
  - Returns a `WriteResult` with output parameters.

Each module may implement functions (`extract`, `transform`, `validate`, `export`) or classes (`*ExtractorImpl`, `*TransformerImpl`, etc.), but the **file names are fixed** and required by project tests.

## 3. Pipeline Identifier and Registry

Each pipeline has a **unique string ID**:

- Format: `"<entity>_<provider>"`, lowercase.
- Example: `activity_chembl`, `new_entity_chembl`.

This ID is used:

- In CLI: `--pipeline-name <entity>_<provider>`.
- In internal registry: to resolve pipeline class from its name.

**Registration** happens in:

- `src/bioetl/application/pipelines/registry.py`

There, `PIPELINE_REGISTRY` maps IDs to pipeline classes (subclasses of `PipelineBase` / provider-specific base):

```python
PIPELINE_REGISTRY: dict[str, type[PipelineBase]] = {
    # ... existing pipelines ...
    "new_entity_chembl": ChemblPipelineBase,  # or other provider-specific base
}
```

Guidelines:

- **Order in ID**: first `entity`, then `provider`.
- Ensure the ID is **unique**.
- Provider must be present in the **`ProviderId` enum** (domain-level).
  - Adding a new provider requires:
    - Updating `ProviderId`.
    - Extending provider configs and validation so Pydantic recognizes it.

If you add a new provider-specific base pipeline, place it in the application layer and register all new pipelines via this base.

## 4. Pandera Schemas and Pydantic Models

### 4.1. Pandera DataFrame Schemas

Each pipeline has a strict Pandera schema describing its **final output**.

Location:

- `src/bioetl/domain/schemas/<provider>/<entity>.py`

The schema is a subclass of `pandera.DataFrameModel` (or `pa.SchemaModel`), named:

- `<Entity>Schema`, e.g. `NewEntitySchema`.

The class must declare:

- **Business columns**:
  - Each column is a class attribute:
    - Type: `pd.Series[<python_type>]`.
    - Constraints: `pa.Field(...)` (e.g., `nullable`, `ge`, `le`, `str_matches`, `isin`).
  - Include descriptions for non-obvious fields.

- **System columns** (determinism and lineage):
  - `hash_row` – row-level hash.
  - `hash_business_key` – hash of the business key fields.
  - `index` – stable row index.
  - `database_version` – upstream source version / release.
  - `extracted_at` – extraction timestamp (UTC ISO).

Use a **column order constant**, e.g.:

```python
NEW_ENTITY_OUTPUT_COLUMNS = [
    # business columns...
    "hash_business_key",
    "hash_row",
    "index",
    "database_version",
    "extracted_at",
]
```

and ensure the final DataFrame respects this order.

**Config:**

```python
class Config:
    strict = True      # no extra columns
    coerce = True      # enforce types
    ordered = True     # enforce column order
```

After defining the schema, **register** it in the schema registry:

- `src/bioetl/domain/schemas/registry.py`

Example:

```python
registry.register(
    "new_entity",
    NewEntitySchema,
    column_order=NEW_ENTITY_OUTPUT_COLUMNS,
)
```

This allows the validation service to retrieve the schema by entity name. Omitting registration breaks the pipeline contract.

### 4.2. Pydantic Models

Pydantic is used for:

- **Pipeline configuration** – `PipelineConfig` for YAML configs.
- **Provider-specific configs** – e.g. `ChemblSourceConfig`.
- **API response models** – if your extract step parses complex JSON.

Guidelines:

- Config models:
  - Use `*Config` suffix, e.g. `NewEntityPipelineConfig`.
  - Set `model_config = ConfigDict(extra="forbid")` (no unknown keys).
- Data models:
  - Use `*Model` suffix.
  - Use precise typing and validators (`field_validator`) where needed.

For complex JSON in `extract`:

- Model the response with Pydantic.
- Convert nested structures (lists/dicts) into flat columns or serialized strings before creating the final DataFrame.

## 5. Pipeline YAML Configuration

Each pipeline has a YAML configuration in:

- `configs/pipelines/<provider>/<entity>.yaml`

Example path:

- `configs/pipelines/chembl/new_entity.yaml`

Template:

```yaml
# configs/pipelines/<provider>/<entity>.yaml

id: <entity>_<provider>             # pipeline ID, e.g. new_entity_chembl
provider: <provider>                # data provider code, e.g. "chembl"
entity: <entity>                    # entity name, e.g. "new_entity"
primary_key: <primary_column>       # main identifier, e.g. "new_entity_id"

input_mode: <mode>                  # "csv", "id_only", or "api"/"auto_detect"
input_path: <path_to_input_file>    # required for "csv" / "id_only" modes

output_path: ./data/output/<provider>/<entity>  # output directory

batch_size: 100                     # processing batch size

provider_config:
  provider: <provider>              # must match ProviderId
  base_url: <api_base_url>          # API base URL (if applicable)
  timeout_sec: 30.0
  max_retries: 3
  rate_limit_per_sec: 10.0
  # provider-specific fields...

fields:                             # optional, for documentation
  - name: <column_name>
    data_type: <type>
    is_nullable: false
    description: <column_description>

pipeline:                           # optional, pipeline-specific options
  custom_param: <value>
```

**Key rules:**

- `id`, `provider`, `entity` must be consistent:
  - `id = "<entity>_<provider>"`.
- `primary_key`:
  - Use explicit column name; defaulting should be avoided for clarity.
- `input_mode`:
  - `"csv"` – read data from a CSV file (`input_path` required).
  - `"id_only"` – read IDs from file and fetch details via API.
  - `"api"` / `"auto_detect"` – fetch full data from provider API.

Validate config via CLI:

```bash
bioetl validate-config --config configs/pipelines/<provider>/<entity>.yaml
```

This loads YAML into `PipelineConfig` and checks types, required fields, and provider IDs.

**Profiles:**

- Profiles live in `configs/profiles/*.yaml`.
- Applied via `--profile` to override a base pipeline config (e.g. different limits for `dev` vs `prod`).
- Pipeline YAML must be self-contained; profiles are additive and optional.

## 6. Logging

Logging is centralized via **UnifiedLogger**.

- Pipelines receive a `logger` (implementation of `LoggingPortABC`) in `PipelineBase.__init__`.
- This logger is **pre-bound** with:
  - `pipeline_name`, `provider`, `entity`, `run_id`, etc.

**Guidelines:**

- Use `self.logger.info(...)`, `self.logger.warning(...)`, etc.
- Do **not** use `print` or create ad-hoc `logging.getLogger`.
- Log as **structured data**:

```python
self.logger.info("filtered_records", removed_count=42, total=1000)
```

**Automatic logs:**

- `PipelineBase` + `StageRuntimeManager` log:
  - Pipeline start / finish.
  - Stage start / finish / failure.
  - Error policies (retry/skip), including stack traces.

Do not suppress or bypass these logs.

**Additional logs:**

- Log significant events:
  - Number of records extracted/filtered.
  - Paths of exported files.
  - Applied special filters / switches.

Avoid logging:

- Secrets and credentials (config can enable redaction).
- Large payloads (full DataFrames, full JSON responses).

## 7. CLI Integration (Typer)

BioETL provides a Typer-based CLI.

To run a single pipeline:

```bash
bioetl run \
  --pipeline-name <entity>_<provider> \
  --config configs/pipelines/<provider>/<entity>.yaml \
  [--profile <name>] \
  [--output-dir <path>] \
  [--dry-run]
```

Example:

```bash
bioetl run \
  --pipeline-name new_entity_chembl \
  --config configs/pipelines/chembl/new_entity.yaml \
  --profile development \
  --dry-run
```

Notes:

- CLI resolves the pipeline class via `PIPELINE_REGISTRY`.
- **No extra CLI registration** is needed for a single pipeline; registry entry is enough.
- For orchestration commands (e.g. “run all ChemBL pipelines”) you can:
  - Create a wrapper pipeline that sequentially runs others.
  - Or implement a dedicated Typer command in `bioetl/interfaces/cli`.

Other useful commands:

- `bioetl validate-config --config <path>`
- `bioetl smoke-run --pipeline <name> --config <path> --limit N`

Use `smoke-run` to test a new pipeline on a small subset.

## 8. Docstrings for Pipeline Stages

Each stage file must be documented with clear docstrings. Examples:

```python
# extract.py
def extract(...) -> Iterable[pd.DataFrame]:
    """
    Extracts raw data from the external source and yields DataFrame chunks.

    Connects to the provider API or reads an input file according to the
    pipeline configuration, loads data page by page, performs minimal
    normalization (e.g. flattening JSON), and yields chunks for downstream
    processing.
    """
```

```python
# transform.py
def transform(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforms raw data into the target structure for <entity>.

    Applies business rules: cleans invalid records, computes derived fields,
    renames columns, and prepares the DataFrame for validation. The output
    matches the Pandera schema business columns (without hash and service
    fields).
    """
```

```python
# validate.py
def validate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validates the DataFrame against the <Entity>Schema.

    Uses the ValidationService and entity-specific Pandera schema to enforce
    column presence, types, and constraints. Raises a detailed error if
    validation fails. Returns the validated DataFrame unchanged.
    """
```

```python
# export.py
def export(df: pd.DataFrame, output_path: Path) -> WriteResult:
    """
    Exports validated data to storage and produces run metadata.

    Sorts the DataFrame in a deterministic order, adds service columns
    (hashes, index, version), and writes the result to CSV/Parquet under
    output_path using atomic writes. Also generates meta.yaml with source
    version, row count, and checksum information, and returns a WriteResult
    describing the output.
    """
```

If stages are implemented as classes, document both the class and core methods.

## 9. Testing a New Pipeline

Tests must mirror the source layout:

- Code: `src/bioetl/application/pipelines/<provider>/<entity>/`
- Tests: `tests/bioetl/application/pipelines/<provider>/<entity>/`

Use filenames like:

- `test_extract.py`, `test_transform.py`, `test_validate.py`, `test_export.py`
- Or a consolidated `test_pipeline_stages.py` for small pipelines.

### 9.1. Unit Tests

- Test each stage in isolation.
- Mock:
  - Network calls (API clients).
  - File I/O where appropriate.
- Cover:
  - Normal flow (small DataFrame).
  - Edge cases (empty responses, invalid records).
  - Validation failures (expect Pandera / ValidationService errors).

### 9.2. Golden Tests

Golden tests verify determinism and backward compatibility:

- Prepare fixed input data (e.g. CSV in `tests/golden/...`).
- Prepare golden outputs:
  - Final CSV/Parquet.
  - `meta.yaml`.
  - Optional quality reports.
- Run the pipeline on the golden input (via CLI or directly).
- Compare produced artifacts byte-for-byte with golden files.

When the schema or logic intentionally changes:

- Update golden artifacts.
- Record the change in `CHANGELOG` or ADR.

Golden test files usually carry a `_golden` suffix, e.g.:

- `test_new_entity_golden.py`

### 9.3. Integration Tests

Integration tests run the pipeline end-to-end:

- Via CLI (subprocess calling `bioetl run`), or
- Via orchestration code, constructing `PipelineConfig` and `PipelineBase`.

Guidelines:

- Use `--dry-run` or `--limit` to keep tests fast.
- Mock external APIs in CI, or use dummy providers.
- Check:
  - Config is parsed.
  - Registry resolves the pipeline.
  - Stages execute in order.
  - Export is skipped in dry-run mode but metadata is consistent.
  - Idempotence: repeated runs on the same data produce identical outputs.

### 9.4. Coverage and Invariants

- Do not reduce global coverage; target **≥ 85%** for critical modules.
- Test:
  - Deterministic sort order.
  - Stable hashes (`hash_row`, `hash_business_key`).
  - Exact column order as in `OUTPUT_COLUMN_ORDER`.
  - Error policies (retry/skip) where used.
  - Dry-run behaviour (no writes, but full extract→transform→validate).

Refer to `docs/guides/04-testing.md` for general testing standards.

## 10. User-Facing Pipeline Documentation

For each new pipeline, create an overview document under:

- `docs/application/pipelines/<provider>/<entity>/`

At minimum:

- `00-<entity>-<provider>-overview.md`

Example:

- `docs/application/pipelines/chembl/new_entity/00-new-entity-chembl-overview.md`

**File requirements:**

- Name: `00-...-overview.md`, kebab-case, English.
- First line: H1 heading describing the pipeline, e.g.:
  - `# NewEntity Chembl Overview`

Recommended sections:

- **Pipeline**
  - Base class used (e.g. `ChemblPipelineBase`).
  - Schema module (`domain/schemas/<provider>/<entity>.py`).
  - Where the config lives (`configs/pipelines/<provider>/<entity>.yaml`).

- **Components**
  - **Extractor** – describes input modes (`api`, `csv`, `id_only`).
  - **Transformer** – main transformations and filters.
  - **Validation** – Pandera schema and service used.
  - **Output writer** – where artifacts are stored, metadata format.

- **Features**
  - Supported input modes and special flags.
  - Primary key logic.
  - Hashing strategy (which fields form business key).
  - Data versioning source (e.g. provider release number).

- **Configuration**
  - Link to YAML.
  - Short explanation of key parameters (especially non-obvious ones).

- **Usage**
  - Example CLI commands (with and without `--profile`, `--dry-run`).
  - Smoke / golden test usage if relevant.

- **Diagrams**
  - Place diagrams in subfolders:
    - `diagrams/flow/`
    - `diagrams/sequence/`
    - `diagrams/class/`
  - Use text-first formats (Mermaid/PlantUML) as primary artifacts:
    - `activity-chembl-flow.mmd`
    - `activity-chembl-sequence-main.mmd`

Ensure this documentation matches the actual code and config. The project has tests (e.g. `tests/project_rules/test_pipeline_structure.py`) that check for the existence of documentation for each pipeline config.

## 11. Checklist for a New Pipeline

Before opening a PR, verify:

- **Code**
  - [ ] `src/bioetl/application/pipelines/<provider>/<entity>/` with all four stage files.
  - [ ] Domain schema in `src/bioetl/domain/schemas/<provider>/<entity>.py`.
  - [ ] Schema registered in schema registry with proper column order.
  - [ ] Pipeline class registered in `PIPELINE_REGISTRY` with unique ID `<entity>_<provider>`.

- **Config**
  - [ ] YAML at `configs/pipelines/<provider>/<entity>.yaml`.
  - [ ] `bioetl validate-config` passes.
  - [ ] Provider exists in `ProviderId` and provider configs.

- **Logging**
  - [ ] Only `UnifiedLogger` is used; no `print` calls.
  - [ ] Key events (filters, exports, special conditions) are logged with context.

- **Tests**
  - [ ] Unit tests for `extract`, `transform`, `validate`, `export`.
  - [ ] Golden test(s) for deterministic outputs.
  - [ ] Integration / smoke test via CLI or orchestrator.
  - [ ] Coverage for normal and error paths; deterministic I/O verified.

- **Docs**
  - [ ] `docs/application/pipelines/<provider>/<entity>/00-<entity>-<provider>-overview.md` created.
  - [ ] Diagrams added if required and stored as text (`.mmd` / `.puml`).
  - [ ] Any relevant indices / maps updated (if present).

Following this guide ensures that new pipelines conform to BioETL’s architectural, validation, logging, and documentation standards.
