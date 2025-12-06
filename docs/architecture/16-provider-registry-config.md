# 16 Provider Registry Config

## Purpose

This note documents the YAML-driven provider registry that powers dynamic provider registration for BioETL. It explains the file format, validation rules, and the workflow for adding new providers.

## Configuration file

- Location: `configs/providers.yaml`
- Format: YAML object with a `providers` array
- Fields per entry:
  - `id` *(required)* — provider identifier matching `ProviderId` (snake_case string)
  - `module` *(required)* — fully-qualified Python module that exports the factory
  - `factory` *(required)* — callable name that performs provider registration and returns `ProviderDefinition`
  - `active` *(optional, default: true)* — toggle to enable/disable loading
  - `description` *(optional)* — human-readable description for documentation

### Example

```yaml
providers:
  - id: chembl
    module: bioetl.infrastructure.clients.chembl.provider
    factory: register_chembl_provider
    active: true
    description: "ChEMBL data provider"
```

A reference sample is available at `configs/providers.example.yaml`.

## Loader behavior

- Entrypoints: `ProviderRegistryLoader.load` and helper `load_provider_registry` (returns the populated registry).
- Pydantic validation with `extra="forbid"`; invalid shapes raise `ProviderRegistryValidationError`.
- Missing config file raises `ProviderRegistryConfigNotFoundError`.
- Disabled entries (`active: false`) are skipped with a debug log.
- Import errors, missing factories, runtime exceptions, and wrong return types are logged; processing continues for other entries.
- Duplicate provider ids reuse the existing definition (logged at debug); no exception is propagated to callers.
- Successful calls return a list of registered `ProviderDefinition` objects in config order.
- Dependencies (`registry`, `logger`, `config_path`) are injectable for tests and custom runs.

## Error handling

- `ProviderRegistryConfigNotFoundError` — raised when `config_path` is absent.
- `ProviderRegistryValidationError` — wraps Pydantic validation errors with the source path.

## Adding a new provider

1. Implement the provider components and registration factory (e.g., `register_<provider>_provider`).
2. Ensure the provider identifier is declared in `ProviderId`.
3. Add a new entry to `configs/providers.yaml` with `active: true` once the provider is ready.
4. Commit the change along with any provider code and configuration updates.
