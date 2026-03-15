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

## Governance Freeze

This inventory is also the freeze ledger for compatibility debt in the current cycle.

- Every listed concern MUST have one accountable owner, one canonical target, and one explicit sunset or review date.
- New first-party `src/` imports MUST go through the canonical target named below.
- Compatibility entrypoints remain only as controlled transition surfaces.
- Allowed call sites are explicit. Adding new ones is a regression unless the inventory is updated first.

## Inventory

| Path | Compatibility role | Canonical target | Status | Owner | Allowed call sites | Sunset / review date | Exit criteria |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `src/bioetl/composition/factories/pipeline/facade.py` | Temporary pipeline factory facade that re-exports legacy assembly and service helpers. | `bioetl.composition.factories.pipeline.pipeline_assembler`, `bioetl.composition.factories.services.bundle`, `bioetl.composition.factories.dq.context_resolver` | `deprecated-warn` | `bioetl.composition.factories.pipeline` | `src`: none; `tests`: `tests/unit/composition/factories/test_factory_decoupling_contracts.py`, `tests/architecture/test_deprecation_warnings.py` | `2026-06-30` | Non-compat imports disappear and only dedicated deprecation coverage remains before removal. |
| `src/bioetl/composition/entrypoints.py` | Canonical composition entrypoint that intentionally shields internal `_pipeline_execution` and `_resource_management` module paths. | `bioetl.composition.entrypoints` | `retained-entrypoint` | `bioetl.composition` | `src`: canonical entrypoint usage allowed; `tests`: CLI and composition entrypoint boundary coverage | `2026-09-30` | Internal implementation-module imports outside `composition/` stay at zero and entrypoint-only compatibility coverage remains explicit. |
| `src/bioetl/composition/factories/storage/facade.py` | Storage re-export facade that keeps split storage modules import-compatible. | `bioetl.composition.factories.storage.factory`, `bioetl.composition.factories.storage.adapter` | `compat-shim` | `bioetl.composition.factories.storage` | `src`: none; `tests`: none beyond explicit compatibility review | `2026-06-30` | Internal callers move to split modules or package-root exports and facade-only patch points are retired. |
| `src/bioetl/composition/factories/datasource/factory.py` | Legacy datasource facade that re-exports the canonical `data_source_factory.py` module and the retained `DataSourceRegistry` compatibility shim. | `bioetl.composition.factories.datasource.data_source_factory`, `bioetl.composition.providers.provider_registry.ProviderRegistry` | `compat-shim` | `bioetl.composition.providers` | `src`: none; `tests`: legacy module-path import allowed only in `tests/unit/composition/test_canonical_module_paths.py`; behavior/contract tests import the canonical `data_source_factory.py` module | `2026-09-30` | First-party source no longer imports `datasource.factory`, and `DataSourceRegistry` remains only in canonical exports plus dedicated compatibility coverage. |
| `src/bioetl/composition/runtime_builders/runner_builder.py` | Mixed runtime builder that retains only the `VacuumConfig` alias while the active runner-input flow resolves directly through split subservices. | `bioetl.composition.runtime_builders.inputs_resolver`, `bioetl.composition.runtime_builders.observability_builder` | `mixed-module` | `bioetl.composition.runtime_builders` | `src`: canonical runner-builder usage allowed; `tests`: `tests/unit/composition/runtime_builders/test_runner_builder.py` covers canonical default wiring and absence of legacy wrapper patch-points | `2026-09-30` | The `VacuumConfig` alias is no longer needed and runner_builder remains a thin composition leaf without reintroduced compatibility wrappers. |
| `src/bioetl/application/core/base_transformer/dependencies.py` | Typing-only compatibility facade that preserves legacy `TransformerDependencyContext` imports while concrete default collaborator assembly stays composition-owned. | `bioetl.application.core.base_transformer.types.TransformerDependencyContext` | `compat-shim` | `bioetl.application.core.base_transformer` | `src`: none; `tests`: `tests/unit/application/core/test_base_transformer_dependencies_reexport.py` | `2026-06-30` | First-party imports migrate to the package root or `types.py` directly and only compatibility coverage continues exercising the facade. |
| `src/bioetl/composition/services/metadata_coordinator.py` | Composition-level re-export shim for metadata coordinator service. | `bioetl.application.services.metadata_coordinator` | `compat-shim` | `bioetl.application.services` | `src`: none; `tests`: `tests/unit/composition/services/test_metadata_coordinator_reexport.py` | `2026-06-30` | First-party `src/` imports have migrated; keep only package-level compatibility coverage and explicit shim tests. |
| `src/bioetl/composition/services/metadata_assemblers.py` | Composition-level re-export shim for metadata assembler services. | `bioetl.application.services.metadata_assemblers` | `compat-shim` | `bioetl.application.services` | `src`: none; `tests`: `tests/unit/composition/services/test_metadata_assemblers_reexport.py` | `2026-06-30` | First-party `src/` imports have migrated; keep only compatibility smoke coverage for the shim. |
| `src/bioetl/infrastructure/storage/delta_writer.py` | Legacy alias wrapper that preserves `DeltaWriter` imports over `SilverWriter`. | `bioetl.infrastructure.storage.silver_writer.SilverWriter` | `compat-shim` | `bioetl.infrastructure.storage` | `src`: none; `tests`: `tests/unit/infrastructure/storage/test_delta_writer_compat.py` | `2026-06-30` | Benchmarks and tests stop importing `DeltaWriter` and use the canonical storage writer directly. |
| `src/bioetl/infrastructure/adapters/pubmed/client.py` | Canonical package entrypoint that shields older `pubmed_client` imports while exporting the current adapter surface. | `bioetl.infrastructure.adapters.pubmed.client` | `retained-entrypoint` | `bioetl.infrastructure.adapters.pubmed` | `src`: canonical entrypoint usage allowed; `tests`: `tests/unit/infrastructure/adapters/test_provider_entrypoints.py`, `tests/architecture/test_adapter_contracts.py` | `2026-09-30` | RF-035 decision is `retain`: re-review only after first-party code no longer depends on `_create_pubmed_adapter` through the entrypoint and legacy-path references are reduced to dedicated compatibility coverage. |
| `src/bioetl/infrastructure/adapters/semanticscholar/client.py` | Canonical package entrypoint that shields older `adapter` imports. | `bioetl.infrastructure.adapters.semanticscholar.client` | `retained-entrypoint` | `bioetl.infrastructure.adapters.semanticscholar` | `src`: canonical entrypoint usage allowed; `tests`: `tests/unit/infrastructure/adapters/test_provider_entrypoints.py`, `tests/architecture/test_adapter_contracts.py` | `2026-09-30` | RF-035 decision is `retain`: re-review only after the retained client shim no longer carries compatibility value beyond dedicated compatibility coverage. |
| `src/bioetl/application/core/checkpoint_manager.py` | Thin compatibility shim for historical application-core checkpoint manager imports. | `bioetl.application.core.lifecycle.checkpoint_manager` | `compat-shim` | `bioetl.application.core.lifecycle` | `src`: none; `tests`: `tests/unit/application/core/test_lifecycle_shim_reexports.py` | `2026-06-30` | First-party imports remain on lifecycle modules directly and only dedicated compatibility smoke coverage continues exercising the shim. |
| `src/bioetl/application/core/batch_transformer_helpers.py` | Compatibility facade for historical batch-transform helper imports spread across split helper modules. | `bioetl.application.core.batch_transformer_state`, `bioetl.application.core.batch_transformer_attempts`, `bioetl.application.core.batch_transformer_quarantine`, `bioetl.application.core.batch_transformer_orchestration` | `compat-shim` | `bioetl.application.core` | `src`: none; `tests`: `tests/unit/application/core/test_batch_transformer_helpers_reexport.py` | `2026-06-30` | First-party imports remain on canonical helper modules directly and only dedicated compatibility smoke coverage continues exercising the facade. |
| `src/bioetl/application/core/cleanup_service.py` | Thin compatibility shim for historical application-core cleanup service imports. | `bioetl.application.core.lifecycle.cleanup_service` | `compat-shim` | `bioetl.application.core.lifecycle` | `src`: none; `tests`: `tests/unit/application/core/test_lifecycle_shim_reexports.py` | `2026-06-30` | First-party imports remain on lifecycle modules directly and only dedicated compatibility smoke coverage continues exercising the shim. |
| `src/bioetl/application/core/heartbeat.py` | Thin compatibility shim for historical application-core heartbeat imports. | `bioetl.application.core.lifecycle.heartbeat` | `compat-shim` | `bioetl.application.core.lifecycle` | `src`: none; `tests`: `tests/unit/application/core/test_lifecycle_shim_reexports.py` | `2026-06-30` | First-party imports remain on lifecycle modules directly and only dedicated compatibility smoke coverage continues exercising the shim. |
| `src/bioetl/application/core/lock_manager.py` | Thin compatibility shim for historical application-core lock manager imports. | `bioetl.application.core.lifecycle.lock_manager` | `compat-shim` | `bioetl.application.core.lifecycle` | `src`: none; `tests`: `tests/unit/application/core/test_lifecycle_shim_reexports.py` | `2026-06-30` | First-party imports remain on lifecycle modules directly and only dedicated compatibility smoke coverage continues exercising the shim. |
| `src/bioetl/application/core/shutdown.py` | Thin compatibility shim for historical application-core shutdown imports. | `bioetl.application.core.lifecycle.shutdown` | `compat-shim` | `bioetl.application.core.lifecycle` | `src`: none; `tests`: `tests/unit/application/core/test_lifecycle_shim_reexports.py` | `2026-06-30` | First-party imports remain on lifecycle modules directly and only dedicated compatibility smoke coverage continues exercising the shim. |

## Measured Registry

This registry is the measurable compatibility-surface baseline for CI. It is the union of:

- curated inventory rows listed above;
- module docstrings whose first line starts with a tracked compatibility prefix.

Snapshot for this cycle:

- Curated inventory rows: `17`
- Measured tracked modules: `27`
- Measured-only modules outside curated inventory: `10`

Tracked module paths:

- `src/bioetl/application/composite/join_planner_compat_mixin.py`
- `src/bioetl/application/composite/merger_compat_mixin.py`
- `src/bioetl/application/composite/runner.py`
- `src/bioetl/application/core/base_transformer/dependencies.py`
- `src/bioetl/application/core/batch_transformer_helpers.py`
- `src/bioetl/application/core/checkpoint_manager.py`
- `src/bioetl/application/core/cleanup_service.py`
- `src/bioetl/application/core/heartbeat.py`
- `src/bioetl/application/core/lock_manager.py`
- `src/bioetl/application/core/shutdown.py`
- `src/bioetl/composition/entrypoints.py`
- `src/bioetl/composition/factories/datasource/factory.py`
- `src/bioetl/composition/factories/pipeline/facade.py`
- `src/bioetl/composition/factories/storage/facade.py`
- `src/bioetl/composition/runtime_builders/runner_builder.py`
- `src/bioetl/composition/services/metadata_assemblers.py`
- `src/bioetl/composition/services/metadata_coordinator.py`
- `src/bioetl/domain/composite/config.py`
- `src/bioetl/domain/value_objects/activity_values.py`
- `src/bioetl/domain/value_objects/publication_field_groups.py`
- `src/bioetl/infrastructure/adapters/_error_classifier.py`
- `src/bioetl/infrastructure/adapters/chembl/fetch_mixin.py`
- `src/bioetl/infrastructure/adapters/openalex/client_helpers_mixin.py`
- `src/bioetl/infrastructure/adapters/pubmed/client.py`
- `src/bioetl/infrastructure/adapters/semanticscholar/client.py`
- `src/bioetl/infrastructure/adapters/uniprot/metadata_mixin.py`
- `src/bioetl/infrastructure/storage/delta_writer.py`

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
- `src/` direct imports of `bioetl.application.core.base_transformer.dependencies`: `0`
- `src/` direct imports of `bioetl.application.core.batch_transformer_helpers`: `0`
- `src/` direct imports of `bioetl.application.core.checkpoint_manager`: `0`
- `src/` direct imports of `bioetl.application.core.cleanup_service`: `0`
- `src/` direct imports of `bioetl.application.core.heartbeat`: `0`
- `src/` direct imports of `bioetl.application.core.lock_manager`: `0`
- `src/` direct imports of `bioetl.application.core.shutdown`: `0`
- `src/` direct imports of `bioetl.composition.services.metadata_coordinator`: `0`
- `src/` direct imports of `bioetl.composition.services.metadata_assemblers`: `0`
- `src/` direct imports of `bioetl.infrastructure.storage.delta_writer`: `0`
- `tests/` direct imports of `bioetl.composition.factories.datasource.factory` outside dedicated compatibility coverage: `0`
- `src/` direct `DataSourceRegistry` usages outside explicit compatibility re-exports: `0`
- Dedicated compatibility coverage remains in tests:
  - `tests/unit/application/core/test_batch_transformer_helpers_reexport.py`
  - `tests/unit/application/core/test_lifecycle_shim_reexports.py`
  - `tests/unit/application/core/test_base_transformer_dependencies_reexport.py`
  - `tests/unit/composition/services/test_metadata_coordinator_reexport.py`
  - `tests/unit/composition/services/test_metadata_assemblers_reexport.py`
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
