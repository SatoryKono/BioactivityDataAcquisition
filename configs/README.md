# Configuration Files

This directory contains project configuration assets, JSON schemas, provider
configs, and compatibility policy documents for BioETL.

## File Types

- `YAML` / `JSON` / `TOML`: configuration and schema files
- `XML`: portable IDE project templates under `configs/ide/`
- `.env*`: environment files
- `Dockerfile` / compose files: container and local runtime setup
- tool-specific config files

## Canonical Config Policy

Active configuration docs must stay aligned with the JSON schemas under
`configs/_schema/`.
Config compatibility shapes are not implicit: accepted aliases, rejected
retired forms, removal dates, and permanent rationales are governed by
`configs/quality/config_compatibility_registry.yaml`.

- pipeline `page_size_override`: canonical pipeline-level pagination override
- source `provider_config.batch_size/page_size/max_url_length/cursor_pagination`:
  retired source provider pagination aliases
- source `batch_size`: retired source root alias
- provider source `pagination.*`: canonical source pagination contract
- source `api`, `client`, and `batch`: retired migration aliases and rejected
  by normalization before schema validation
- composite `merge.column_groups_file`: retired legacy merge alias
- composite `composite.version`: required composite schema field

## Provider Runtime Values

Tracked provider configs are deterministic documentation and policy surfaces.
They must not contain `${ENV_VAR}` interpolation strings:

- non-secret operator contact fields such as CrossRef/OpenAlex `mailto` use the
  safe `your-email@example.com` placeholder; set the real runtime contact with
  `BIOETL_DEFAULT_EMAIL` in the machine-local environment;
- secret-bearing fields use named indirection keys such as
  `api_key_env: BIOETL_SEMANTICSCHOLAR_API_KEY`; secret values remain in the
  machine-local environment and never enter tracked YAML.

## Versioning Strategy

- top-level `version` identifies the current file's contract: provider config
  bundle and each entity config bundle evolve independently;
- nested `quality.version`, `filters.version`, source-profile versions, and
  contract versions identify their own independently evolving section
  contracts and therefore do not have to equal the top-level version;
- every declared config version uses `MAJOR.MINOR.PATCH`; a version changes only
  when its own scoped contract changes, so `chembl/activity` root `1.0.0` with
  `quality.version: 1.1.0` is intentional rather than drift;
- **Version synchronization policy**: Provider config top-level versions should
  generally align with their corresponding entity config top-level versions for
  consistency, but nested section versions (quality, filters, etc.) are independent
  and reflect the evolution of their specific contracts;
- `configs/entities/composite/{entity}.yaml` is the entity-level composite
  contract and must contain `pipeline`, `schema`, `quality`, `filters`, and
  `contracts`; its `schema.column_groups` mirrors the canonical merge schema in
  `configs/composites/{entity}.yaml` and is protected by config invariants.
- **Composite entity structure requirements**: Composite entity configs follow
  the same structural requirements as provider entity configs, including:
  - Full `schema` section with `column_groups`, `silver`, and `gold` definitions
  - Complete `quality` section with `thresholds`, `entity_field_validations`,
    and `entity_cross_field_validations` (even if empty arrays)
  - Detailed `filters` section with `input_filter`, `silver_filters`, and
    `gold_filters` definitions
  - `contracts` section defining merge behavior and versioning

## Navigation

- `configs/_schema/`: canonical JSON schemas for pipeline, source, composite, and
  related config contracts
- `configs/providers/`: provider YAML definitions
- `configs/entities/`: provider-backed and composite entity contracts
- `configs/composites/`: composite seed/enricher/merge runtime definitions
- `configs/ide/pycharm/`: reviewed portable PyCharm templates copied into the
  ignored local `.idea/` directory
- `configs/quality/`: architecture, compatibility, generated-artifact routing,
  and debt registries

For deeper usage guidance, see the active docs in
`docs/03-guides/pipeline-configuration.md` and the individual schema files.
