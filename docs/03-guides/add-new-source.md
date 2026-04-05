______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Guide: Add a New Provider

This guide describes the current (v6.x) process for adding a **new external provider** to BioETL.

Scope:

- add a provider source config (`configs/providers/{provider}.yaml`)
- add an infrastructure adapter (`src/bioetl/infrastructure/adapters/{provider}/`)
- register provider in Composition (`src/bioetl/composition/providers/registration.py`)
- bootstrap at least one pipeline for this provider

Use this guide together with:

- [add-pipeline-existing-source.md](add-pipeline-existing-source.md)
- [pipeline-configuration.md](pipeline-configuration.md)
- [RULES.md](../00-project/RULES.md)

______________________________________________________________________

## 1. Naming and Scope

Provider naming rules:

- provider id: `snake_case` (example: `myprovider`)
- entity ids: `snake_case` singular (`publication`, `compound`)
- pipeline name: `{provider}_{entity}`

Before implementation:

- verify provider is not already present in `configs/providers/`
- define first supported entity (recommended: a small, stable endpoint)

______________________________________________________________________

## 2. Create Provider Source Config

Create `configs/providers/{provider}.yaml`.

Example template:

```yaml
version: 1.0.0
provider: myprovider

source:
  batch_size: 100
  provider_config:
    provider: myprovider
    base_url: https://api.example.org/v1
    auth_type: api_key
    api_key_env: BIOETL_MYPROVIDER_API_KEY
    client:
      timeout_sec: 60.0
      max_retries: 3
    pagination:
      page_size: 100
      id_batch_size: 50
      strategy: offset
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 300
  rate_limit:
    requests_per_second: 2.0
    burst: 5
  health_check:
    endpoint: /health
    timeout: 10
  retry:
    use_retry_after: true

entities:
  - publication

entity_notes:
  publication:
    description: Publication metadata
    input_mode: DOI/title search

quality:
  version: 1.0.0
  provider: myprovider
  thresholds:
    soft_fail: 0.05
    hard_fail: 0.15
  field_validations: []

filters:
  version: 1.0.0
  provider: myprovider
  input_filter:
    batch_size: 100
  gold_filters:
    required_fields: []
    columns: {}
```

Notes:

- `source.provider_config.pagination` is the canonical place for paging defaults.
- Keep credentials in env vars (`*_ENV`), never in YAML.

______________________________________________________________________

## 3. Implement Infrastructure Adapter

Create adapter module under:

- `src/bioetl/infrastructure/adapters/{provider}/client.py`

Adapter must satisfy `DataSourcePort`/`FilterableDataSourcePort` contract and use `UnifiedHTTPClient`.

Start from template:

- `docs/04-reference/templates/source_adapter.py.tpl`

Minimum expectations:

- implement `fetch(...)` async generator
- implement or inherit `health_check()`
- keep API/network logic in infrastructure only

______________________________________________________________________

## 4. Register Provider in Composition Layer

Update `src/bioetl/composition/providers/registration.py`:

1. Add provider-specific creator function:

- `_create_{provider}_data_source(...) -> DataSourcePort`

2. Register provider inside the composition registration flow (`src/bioetl/composition/providers/registration.py`), after resolving `target_registry`:

```python
if not target_registry.is_registered("myprovider"):
    target_registry.register(
        "myprovider",
        ProviderConfig(
            adapter_class=MyProviderAdapter,
            http_config=HttpConfig(rate=2.0, capacity=5),
            requires_http_client=True,
            requires_logger=True,
            data_source_creator=_create_myprovider_data_source,
        ),
    )
```

If provider needs custom lifecycle/constructor wiring, use `custom_creator=` as in existing providers.

Runtime/bootstrap code should continue to use `ensure_providers_loaded()` as the
shared lifecycle seam rather than calling registration directly.

______________________________________________________________________

## 5. Add First Pipeline for the Provider

For the first provider entity, complete all items from
[add-pipeline-existing-source.md](add-pipeline-existing-source.md):

- unified entity config: `configs/entities/{provider}/{entity}.yaml`
- transformer: `src/bioetl/application/pipelines/{provider}/...`
- Pandera Silver schema + Gold contract
- `register_all_transformers()` entry
- `PIPELINE_CONFIGS` entry in `src/bioetl/composition/factories/pipeline/registry.py`

______________________________________________________________________

## 6. Validation Checklist

Configuration:

```bash
uv run python -m scripts.schema validate-configs --verbose
```

Loadability smoke (provider + one pipeline):

```bash
python -c "from bioetl.infrastructure.config import load_pipeline_config, load_source_config; load_source_config('myprovider'); load_pipeline_config('myprovider_publication'); print('ok')"
```

Architecture/registry smoke:

```bash
uv run python -m pytest tests/architecture/test_registry_contracts.py -q
uv run python -m pytest tests/architecture/test_source_config_usage.py -q
```

Recommended targeted tests:

```bash
uv run python -m pytest tests/unit/application/pipelines/myprovider/ -q
uv run python -m pytest tests/integration/ -k myprovider -q
```

______________________________________________________________________

## 7. Done Criteria

Provider onboarding is complete when:

- provider config exists and loads
- adapter and provider registration are in place
- at least one pipeline runs end-to-end (`run --pipeline {provider}_{entity}`)
- config/schema/contract validations pass
- provider docs and pipeline docs are updated
