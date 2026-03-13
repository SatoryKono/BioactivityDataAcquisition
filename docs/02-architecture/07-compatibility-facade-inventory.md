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
| `src/bioetl/composition/entrypoints.py` | Canonical composition entrypoint that intentionally shields internal `_pipeline_execution` and `_resource_management` module paths. | `bioetl.composition.entrypoints` | `retained-entrypoint` | Internal implementation-module imports outside `composition/` stay at zero and entrypoint-only compatibility coverage remains explicit. |
| `src/bioetl/composition/factories/storage/facade.py` | Storage re-export facade that keeps split storage modules import-compatible. | `bioetl.composition.factories.storage.factory`, `bioetl.composition.factories.storage.adapter` | `compat-shim` | Internal callers move to split modules or package-root exports and facade-only patch points are retired. |
| `src/bioetl/composition/factories/datasource/factory.py` | Mixed module: `DataSourceFactory` is active, while `DataSourceRegistry` remains a compatibility facade over `ProviderRegistry`. | `bioetl.composition.factories.datasource.data_source_factory`, `bioetl.composition.providers.provider_registry.ProviderRegistry` | `mixed-module` | First-party code uses the canonical datasource helper or `ProviderRegistry.create_data_source()` directly and `DataSourceRegistry` remains only for dedicated compatibility tests. |
| `src/bioetl/composition/runtime_builders/runner_builder.py` | Mixed runtime builder with stable monkeypatch seams kept for legacy tests. Active runtime flow should resolve through the split subservices rather than wrapper defaults. | `bioetl.composition.runtime_builders.inputs_resolver`, `bioetl.composition.runtime_builders.observability_builder` | `mixed-module` | Legacy patch-point tests migrate to submodule seams and wrapper helpers become unnecessary. |
| `src/bioetl/composition/services/metadata_coordinator.py` | Composition-level re-export shim for metadata coordinator service. | `bioetl.application.services.metadata_coordinator` | `compat-shim` | First-party `src/` imports have migrated; keep only package-level compatibility coverage and explicit shim tests. |
| `src/bioetl/composition/services/metadata_assemblers.py` | Composition-level re-export shim for metadata assembler services. | `bioetl.application.services.metadata_assemblers` | `compat-shim` | First-party `src/` imports have migrated; keep only compatibility smoke coverage for the shim. |
| `src/bioetl/infrastructure/storage/delta_writer.py` | Legacy alias wrapper that preserves `DeltaWriter` imports over `SilverWriter`. | `bioetl.infrastructure.storage.silver_writer.SilverWriter` | `compat-shim` | Benchmarks and tests stop importing `DeltaWriter` and use the canonical storage writer directly. |
| `src/bioetl/infrastructure/adapters/pubmed/client.py` | Canonical package entrypoint that shields older `pubmed_client` imports while exporting the current adapter surface. | `bioetl.infrastructure.adapters.pubmed.client` | `retained-entrypoint` | RF-035 decision is `retain`: re-review only after first-party code no longer depends on `_create_pubmed_adapter` through the entrypoint and legacy-path references are reduced to dedicated compatibility coverage. |
| `src/bioetl/infrastructure/adapters/semanticscholar/client.py` | Canonical package entrypoint that shields older `adapter` imports. | `bioetl.infrastructure.adapters.semanticscholar.client` | `retained-entrypoint` | RF-035 decision is `retain`: re-review only after the retained client shim no longer carries compatibility value beyond dedicated compatibility coverage. |

## Usage Notes

- `deprecated-warn` and `compat-shim` rows count as compatibility debt and should shrink over time.
- `mixed-module` rows require symbol-level migration, not whole-module deletion by default.
- `retained-entrypoint` rows are not removal targets in the current cycle; they exist to stabilize
  provider package imports while internal implementation modules continue to evolve.

## Current Import Inventory

Snapshot after RF-032 compatibility-only cleanup:

- `src/` direct imports of `bioetl.composition._pipeline_execution` outside `src/bioetl/composition/`: `0`
- `src/` direct imports of `bioetl.composition._resource_management` outside `src/bioetl/composition/`: `0`
- `src/` direct imports of `bioetl.composition.factories.pipeline.facade`: `0`
- `src/` direct imports of `bioetl.composition.factories.storage.facade`: `0`
- `src/` direct imports of `bioetl.infrastructure.storage.delta_writer`: `0`
- Dedicated compatibility coverage remains in tests:
  - `tests/unit/infrastructure/storage/test_delta_writer_compat.py`
  - deprecation/compat behavior around pipeline facade is exercised via
    `tests/unit/composition/factories/test_factory_decoupling_contracts.py`
    and `tests/architecture/test_deprecation_warnings.py`

Compatibility-only policy for this cycle:

- New first-party code must import canonical modules directly.
- Existing facade modules remain to preserve public/import stability.
- New non-compat usages of these module paths in `src/` or ordinary tests are regressions.

## RF-035 Retained Entrypoint Decision

Decision for this cycle:

- `src/bioetl/infrastructure/adapters/pubmed/client.py`: `retain`
- `src/bioetl/infrastructure/adapters/semanticscholar/client.py`: `retain`

Measured evidence for `retain`:

- PubMed canonical entrypoint is still part of active first-party code:
  - `src/bioetl/infrastructure/adapters/pubmed/__init__.py`
  - `src/bioetl/composition/providers/registration_biblio.py`
- Semantic Scholar canonical entrypoint is still part of active first-party code:
  - `src/bioetl/infrastructure/adapters/semanticscholar/__init__.py`
- Legacy implementation-module references in `src/` are already effectively zero outside the retained entrypoints themselves:
  - `bioetl.infrastructure.adapters.pubmed.pubmed_client` appears only inside
    `src/bioetl/infrastructure/adapters/pubmed/client.py`
  - `bioetl.infrastructure.adapters.semanticscholar.adapter` appears only inside
    `src/bioetl/infrastructure/adapters/semanticscholar/client.py`
- Test-only legacy references remain intentional and limited to compatibility coverage:
  - `tests/unit/infrastructure/adapters/test_provider_entrypoints.py`
  - `tests/architecture/test_adapter_contracts.py`

Policy implications:

- Do not start deprecation for these entrypoints in the current cycle.
- New first-party code may use package roots or the canonical `client.py` entrypoints.
- New first-party code must not import the older implementation modules
  `pubmed.pubmed_client` or `semanticscholar.adapter` directly.
- Any future deprecation proposal must include a fresh usage inventory and an explicit review
  of the PubMed private factory export surface.

Related docs:

- [Composition Layer](05-composition-layer.md)
- [Registry Pattern](../03-guides/registry-pattern.md)
