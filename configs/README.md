# Configuration Files

This directory contains project configuration assets, JSON schemas, provider
configs, and compatibility policy documents for BioETL.

## File Types

- `YAML` / `JSON` / `TOML`: configuration and schema files
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

## Navigation

- `configs/_schema/`: canonical JSON schemas for pipeline, source, composite, and
  related config contracts
- `configs/providers/`: provider YAML definitions
- `configs/quality/`: architecture, compatibility, generated-artifact routing,
  and debt registries

For deeper usage guidance, see the active docs in
`docs/03-guides/pipeline-configuration.md` and the individual schema files.
