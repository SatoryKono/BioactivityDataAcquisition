______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Guide: Add a Pipeline for an Existing Provider

This guide describes the current process for adding a **new entity pipeline** when provider integration already exists.

Example: add `{provider}=chembl`, `{entity}=mechanism`.

______________________________________________________________________

## 1. Target Artifacts

For each new pipeline, update these artifacts:

1. Config:

- `configs/entities/{provider}/{entity}.yaml`

2. Application transformer:

- `src/bioetl/application/pipelines/{provider}/{entity}_transformer.py`
  or existing provider transformer module when provider keeps a single `transformer.py`

3. Silver schema (Pandera):

- `src/bioetl/domain/schemas/{provider}/{entity}.py`

4. Gold contract (Pandera DataFrameModel):

- `src/bioetl/domain/contracts/gold/{provider}.py`
- export in `src/bioetl/domain/contracts/gold/__init__.py`
- export in `src/bioetl/domain/contracts/__init__.py`

5. Composition registration:

- `src/bioetl/composition/factories/transformer_factory.py` (`register_all_transformers`)
- `src/bioetl/composition/factories/pipeline/registry.py` (imports + `PIPELINE_CONFIGS`)

6. Tests:

- `tests/unit/application/pipelines/{provider}/test_{entity}_transformer.py`
- optional integration/e2e tests for provider adapter and runner path

______________________________________________________________________

## 2. Create Unified Entity Config

Create `configs/entities/{provider}/{entity}.yaml`.

Start from template:

- `docs/04-reference/templates/config.yaml.tpl`

Minimum required sections:

- top-level: `version`, `provider`, `entity`
- required sections: `pipeline`, `schema`, `quality`, `filters`, `contracts`

Important consistency rules:

- `provider == pipeline.provider`
- `entity == pipeline.entity_type`
- `pipeline.pipeline_name == {provider}_{entity}`
- `pipeline.business_primary_keys` must be non-empty

______________________________________________________________________

## 3. Implement Transformer

Create transformer with `BaseTransformer`. For publication entities, use `BasePublicationTransformer` and compose it via Strategy interfaces (`DataExtractorStrategy`, `IdentifierResolverStrategy`, `PublicationMetadataStrategy`) rather than overriding protected methods.

Start from template:

- `docs/04-reference/templates/pipeline.py.tpl`

Implementation requirements:

- constructor should receive DI dependencies (tracer/metrics/filters/identity/normalizer)
- implement `_transform_impl(context, record, index)` (for standard pipelines)
- for publication pipelines, inject your extraction and resolution strategies via the constructor
- compute:
  - `entity_id` via `compute_entity_id(...)`
  - `content_hash` via `compute_content_hash(...)`
- return `SilverRecord` (or `None` for skipped invalid input)

______________________________________________________________________

## 4. Register Transformer and Pipeline Factory

### 4.1 Transformer registry

Update `src/bioetl/composition/factories/transformer_factory.py`:

- import transformer class
- add `register_transformer("{provider}", "{entity}", {TransformerClass})`

### 4.2 Pipeline factory registry

Update `src/bioetl/composition/factories/pipeline/registry.py`:

- add imports for transformer/schemas/contracts
- add new `PipelineFactoryConfig(...)` entry into `PIPELINE_CONFIGS`

Start from template:

- `docs/04-reference/templates/factory.py.tpl`

______________________________________________________________________

## 5. Provider Config Sync

Update `configs/providers/{provider}.yaml`:

- append entity to `entities:` list
- add `entity_notes.{entity}` block (description/input mode)

______________________________________________________________________

## 6. Validation and Tests

Config validation:

```bash
uv run python -m scripts.schema validate-configs --verbose
```

Config load smoke:

```bash
python -c "from bioetl.infrastructure.config import load_pipeline_config; load_pipeline_config('chembl_mechanism'); print('ok')"
```

Targeted tests:

```bash
uv run python -m pytest tests/unit/application/pipelines/{provider}/ -q
uv run python -m pytest tests/architecture/test_registry_contracts.py -q
uv run python -m pytest tests/architecture/test_config_ci_invariants.py -q
```

Optional runtime smoke:

```bash
uv run python -m bioetl run --pipeline {provider}_{entity} --limit 10
```

______________________________________________________________________

## 7. Definition of Done

Pipeline is complete when:

- unified entity config passes schema validation
- transformer registered in both registries (transformer + pipeline factory)
- Silver and Gold contracts are available and exported
- unit tests pass
- documentation/spec for pipeline is updated
