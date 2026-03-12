# Compatibility Facade Inventory

`Status:` active

## Purpose

This document is the curated inventory of module-level compatibility facades and shims that
remain in the BioETL source tree to preserve import stability during refactoring.

Scope rules:

- The inventory is curated, not exhaustive for every single deprecated symbol or alias.
- Only module-level facades with architectural significance are listed here.
- New code must prefer the canonical target module named in the inventory row.

## Status Model

| Status | Meaning | New code policy | Exit trigger |
| --- | --- | --- | --- |
| `deprecated-warn` | Facade already emits `DeprecationWarning` on compatibility calls. | Do not add new imports or new call sites. Migrate existing usage to canonical modules. | First-party imports disappear outside dedicated compatibility tests. |
| `compat-shim` | Thin re-export or alias kept only to avoid a breaking import rename. | Freeze the surface. New code imports the canonical module directly. | Internal call sites migrate and only package-level compatibility coverage remains. |
| `mixed-module` | Module contains both canonical logic and compatibility surface, so deprecation applies only to part of the API. | New helpers should land in canonical submodules, not in the mixed module compatibility surface. | Compatibility-only symbols no longer needed and tests stop patching them. |
| `retained-entrypoint` | Canonical public entrypoint that intentionally shields older implementation-module paths. | Keep using the entrypoint for new code; avoid the older implementation-module path it replaces. | Legacy implementation-path imports reach zero and the remaining surface is explicitly reviewed. |

## Inventory

| Path | Compatibility role | Canonical target | Status | Exit criteria |
| --- | --- | --- | --- | --- |
| `src/bioetl/composition/factories/pipeline/facade.py` | Temporary pipeline factory facade that re-exports legacy assembly and service helpers. | `bioetl.composition.factories.pipeline.pipeline_assembler`, `bioetl.composition.factories.services.bundle`, `bioetl.composition.factories.dq.context_resolver` | `deprecated-warn` | Non-compat imports disappear and only dedicated deprecation coverage remains before removal. |
| `src/bioetl/composition/factories/storage/facade.py` | Storage re-export facade that keeps split storage modules import-compatible. | `bioetl.composition.factories.storage.factory`, `bioetl.composition.factories.storage.adapter` | `compat-shim` | Internal callers move to split modules or package-root exports and facade-only patch points are retired. |
| `src/bioetl/composition/factories/datasource/factory.py` | Mixed module: `DataSourceFactory` is active, while `DataSourceRegistry` remains a compatibility facade over `ProviderRegistry`. | `bioetl.composition.providers.provider_registry.ProviderRegistry` | `mixed-module` | First-party code stops calling `DataSourceRegistry` outside dedicated compatibility tests. |
| `src/bioetl/composition/runtime_builders/runner_builder.py` | Mixed runtime builder with stable monkeypatch seams kept for legacy tests. | `bioetl.composition.runtime_builders.inputs_resolver`, `bioetl.composition.runtime_builders.observability_builder` | `mixed-module` | Legacy patch-point tests migrate to submodule seams and wrapper helpers become unnecessary. |
| `src/bioetl/composition/services/metadata_coordinator.py` | Composition-level re-export shim for metadata coordinator service. | `bioetl.application.services.metadata_coordinator` | `compat-shim` | Composition callers import the application service directly and shim-only coverage is the only remaining dependency. |
| `src/bioetl/composition/services/metadata_assemblers.py` | Composition-level re-export shim for metadata assembler services. | `bioetl.application.services.metadata_assemblers` | `compat-shim` | Internal imports migrate to application services and only compatibility smoke coverage remains. |
| `src/bioetl/infrastructure/storage/delta_writer.py` | Legacy alias wrapper that preserves `DeltaWriter` imports over `SilverWriter`. | `bioetl.infrastructure.storage.silver_writer.SilverWriter` | `compat-shim` | Benchmarks and tests stop importing `DeltaWriter` and use the canonical storage writer directly. |
| `src/bioetl/infrastructure/adapters/pubmed/client.py` | Canonical package entrypoint that shields older `pubmed_client` imports while exporting the current adapter surface. | `bioetl.infrastructure.adapters.pubmed.client` | `retained-entrypoint` | Legacy `pubmed_client` imports reach zero and the private factory export decision is reviewed separately. |
| `src/bioetl/infrastructure/adapters/semanticscholar/client.py` | Canonical package entrypoint that shields older `adapter` imports. | `bioetl.infrastructure.adapters.semanticscholar.client` | `retained-entrypoint` | Legacy `adapter` imports reach zero and the entrypoint surface is re-reviewed after migration. |

## Usage Notes

- `deprecated-warn` and `compat-shim` rows count as compatibility debt and should shrink over time.
- `mixed-module` rows require symbol-level migration, not whole-module deletion by default.
- `retained-entrypoint` rows are not removal targets in the current cycle; they exist to stabilize
  provider package imports while internal implementation modules continue to evolve.

Related docs:

- [Composition Layer](05-composition-layer.md)
- [Registry Pattern](../03-guides/registry-pattern.md)
