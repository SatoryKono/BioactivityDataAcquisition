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

- The loader validates the YAML via a Pydantic schema (extra fields are forbidden).
- Disabled entries (`active: false`) are skipped with a debug log.
- For each enabled entry the loader dynamically imports the module, resolves the factory, and executes it.
- Failures to import modules, missing factories, or runtime exceptions are logged and do not stop other entries.
- The factory return value must be a `ProviderDefinition`; otherwise the entry is skipped with an error log.

## Adding a new provider

1. Implement the provider components and registration factory (e.g., `register_<provider>_provider`).
2. Ensure the provider identifier is declared in `ProviderId`.
3. Add a new entry to `configs/providers.yaml` with `active: true` once the provider is ready.
4. Commit the change along with any provider code and configuration updates.
