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

- Every listed concern MUST have one accountable owner, one canonical target, one `introduced_in` marker, one `migration_path`, and one explicit remove-by or review date.
- New first-party `src/` imports MUST go through the canonical target named below.
- Compatibility entrypoints remain only as controlled transition surfaces.
- Allowed call sites are explicit. Adding new ones is a regression unless the inventory is updated first.
- For `retained-entrypoint` rows, the remove-by field is interpreted as a mandatory review date, not an automatic deletion date.

## Inventory

| Path | Compatibility role | Canonical target | Status | Owner | Introduced in | Allowed call sites | Remove by / review date | Migration path | Exit criteria |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `src/bioetl/composition/factories/pipeline/facade.py` | Temporary pipeline factory facade that re-exports legacy assembly and service helpers. | `bioetl.composition.factories.pipeline.pipeline_assembler`, `bioetl.composition.factories.services.bundle`, `bioetl.composition.factories.dq.context_resolver` | `deprecated-warn` | `bioetl.composition.factories.pipeline` | `2026-03 pipeline cleanup` | `src`: none; `tests`: `tests/unit/composition/factories/test_factory_decoupling_contracts.py`, `tests/architecture/test_deprecation_warnings.py` | `2026-06-30` | Move imports and call sites to `bioetl.composition.factories.pipeline.pipeline_assembler`, `bioetl.composition.factories.services.bundle`, and `bioetl.composition.factories.dq.context_resolver`; keep only deprecation coverage on the facade. | Non-compat imports disappear and only dedicated deprecation coverage remains before removal. |
| `src/bioetl/composition/entrypoints.py` | Canonical composition entrypoint that intentionally shields internal `_pipeline_execution` and `_resource_management` module paths. | `bioetl.composition.entrypoints` | `retained-entrypoint` | `bioetl.composition` | `2026-03 entrypoint freeze` | `src`: canonical entrypoint usage allowed; `tests`: CLI and composition entrypoint boundary coverage | `2026-09-30` | Use `bioetl.composition.entrypoints` as the public seam; do not import `bioetl.composition._pipeline_execution` or `bioetl.composition._resource_management` directly. | Internal implementation-module imports outside `composition/` stay at zero and entrypoint-only compatibility coverage remains explicit. |
| `src/bioetl/composition/factories/storage/facade.py` | Storage re-export facade that keeps split storage modules import-compatible. | `bioetl.composition.factories.storage.factory`, `bioetl.composition.factories.storage.adapter` | `compat-shim` | `bioetl.composition.factories.storage` | `legacy-pre-2026-03` | `src`: none; `tests`: none beyond explicit compatibility review | `2026-06-30` | Import `bioetl.composition.factories.storage.factory` or `bioetl.composition.factories.storage.adapter` directly; keep the facade only for compatibility smoke coverage. | Internal callers move to split modules or package-root exports and facade-only patch points are retired. |
| `src/bioetl/composition/factories/datasource/factory.py` | Legacy datasource facade that re-exports the canonical `data_source_factory.py` module and the retained `DataSourceRegistry` compatibility shim. | `bioetl.composition.factories.datasource.data_source_factory`, `bioetl.composition.providers.provider_registry.ProviderRegistry` | `compat-shim` | `bioetl.composition.providers` | `2026-03 datasource cleanup` | `src`: none; `tests`: legacy module-path import allowed only in `tests/unit/composition/test_canonical_module_paths.py`; `DataSourceRegistry` imports allowed only in `tests/unit/composition/factories/datasource/test_data_source_registry.py`, `tests/unit/composition/test_registry_protocol.py`, and `tests/architecture/test_registry_contracts.py`; ordinary tests use `get_data_source_creator` or `ProviderRegistry` directly | `2026-09-30` | Import `bioetl.composition.factories.datasource.data_source_factory` or `bioetl.composition.providers.provider_registry.ProviderRegistry` directly; keep `datasource.factory` only for dedicated compatibility coverage. | First-party source no longer imports `datasource.factory`, and `DataSourceRegistry` remains only in canonical exports plus dedicated compatibility/contract coverage. |
| `src/bioetl/composition/runtime_builders/runner_builder.py` | Mixed runtime builder that retains only the `VacuumConfig` alias while the active runner-input flow resolves directly through split subservices. | `bioetl.composition.runtime_builders.inputs_resolver`, `bioetl.composition.runtime_builders.observability_builder` | `mixed-module` | `bioetl.composition.runtime_builders` | `2026-03 runner-builder cleanup` | `src`: canonical runner-builder usage allowed; `tests`: `tests/unit/composition/runtime_builders/test_runner_builder.py` covers canonical default wiring and absence of legacy wrapper patch-points | `2026-09-30` | Route new code to `bioetl.composition.runtime_builders.inputs_resolver` and `bioetl.composition.runtime_builders.observability_builder`; remove the `VacuumConfig` alias after callers migrate. | The `VacuumConfig` alias is no longer needed and runner_builder remains a thin composition leaf without reintroduced compatibility wrappers. |
| `src/bioetl/application/composite/join_planner_compat_mixin.py` | Compatibility delegation mixin preserving legacy join-planner helper API inside the canonical join planner service. | `bioetl.application.composite.join_planner.JoinPlannerService` | `compat-shim` | `bioetl.application.composite` | `legacy-pre-2026-03` | `src`: allowed only in `src/bioetl/application/composite/join_planner.py`; `tests`: none beyond architecture review | `2026-09-30` | Keep callers on `bioetl.application.composite.join_planner.JoinPlannerService`; do not add new imports of the compatibility mixin. | Join-planner compatibility wrappers are inlined or retired and no new imports appear outside the canonical service module. |
| `src/bioetl/application/composite/merger_compat_mixin.py` | Compatibility delegation mixin preserving legacy MergeService helper API while collaborator services own the real behavior. | `bioetl.application.composite.merger.MergeService` | `compat-shim` | `bioetl.application.composite` | `legacy-pre-2026-03` | `src`: allowed only in `src/bioetl/application/composite/merger.py`; `tests`: none beyond architecture review | `2026-09-30` | Keep callers on `bioetl.application.composite.merger.MergeService`; do not add new imports of the compatibility mixin. | MergeService no longer needs the compatibility wrapper mixin and no new imports appear outside the canonical merger module. |
| `src/bioetl/application/composite/runner.py` | Root runner facade kept for backward-compatible imports while the canonical implementation lives under `runner_pkg`. | `bioetl.application.composite.runner_pkg` | `compat-shim` | `bioetl.application.composite` | `legacy-pre-2026-03` | `src`: none; `tests`: `tests/unit/application/composite/test_runner_root_facade_reexport.py` | `2026-06-30` | Import from `bioetl.application.composite.runner_pkg` or package-root exports directly; leave the facade only for compatibility smoke coverage. | First-party code continues using `runner_pkg` or package-root exports directly and only dedicated compatibility smoke coverage exercises the root runner facade. |
| `src/bioetl/domain/composite/config.py` | Canonical public entrypoint for composite config models that shields split config internals. | `bioetl.domain.composite.config` | `retained-entrypoint` | `bioetl.domain.composite` | `legacy-pre-2026-03` | `src`: canonical entrypoint usage allowed; internal split modules stay inside `src/bioetl/domain/composite/`; `tests`: facade coverage in `tests/unit/domain/composite/test_composite_config_facade.py` and ordinary imports may continue using the root config entrypoint | `2026-09-30` | Keep using `bioetl.domain.composite.config`; do not import split `config_*` internals outside the owning package. | Direct imports of split config internals remain confined to the owning package and the root config entrypoint stays the stable public path. |
| `src/bioetl/domain/value_objects/activity_values.py` | Canonical public entrypoint for activity-related value objects that shields split concentration/type/pChEMBL modules. | `bioetl.domain.value_objects.activity_values` | `retained-entrypoint` | `bioetl.domain.value_objects` | `legacy-pre-2026-03` | `src`: canonical entrypoint usage allowed; internal split modules stay inside `src/bioetl/domain/value_objects/`; `tests`: facade coverage in `tests/unit/domain/value_objects/test_value_object_facade_reexports.py` and ordinary imports may continue using the public entrypoint | `2026-09-30` | Keep using `bioetl.domain.value_objects.activity_values`; do not import split value-object internals outside the owning package. | Direct imports of split activity-value internals remain confined to the owning package and the facade stays the stable public path. |
| `src/bioetl/domain/value_objects/publication_field_groups.py` | Canonical public entrypoint for publication field-group definitions that shields private split config/type modules. | `bioetl.domain.value_objects.publication_field_groups` | `retained-entrypoint` | `bioetl.domain.value_objects` | `legacy-pre-2026-03` | `src`: canonical entrypoint usage allowed; private split modules stay inside `src/bioetl/domain/value_objects/`; `tests`: facade coverage in `tests/unit/domain/value_objects/test_value_object_facade_reexports.py` and ordinary imports may continue using the public entrypoint | `2026-09-30` | Keep using `bioetl.domain.value_objects.publication_field_groups`; do not import split value-object internals outside the owning package. | Direct imports of private publication-field-group internals remain confined to the owning package and the facade stays the stable public path. |
| `src/bioetl/application/core/base_transformer/dependencies.py` | Typing-only compatibility facade that preserves legacy `TransformerDependencyContext` imports while concrete default collaborator assembly stays composition-owned. | `bioetl.application.core.base_transformer.types.TransformerDependencyContext` | `compat-shim` | `bioetl.application.core.base_transformer` | `legacy-pre-2026-03` | `src`: none; `tests`: `tests/unit/application/core/test_base_transformer_dependencies_reexport.py` | `2026-06-30` | Import `TransformerDependencyContext` from `bioetl.application.core.base_transformer.types.TransformerDependencyContext` or package-root exports directly. | First-party imports migrate to the package root or `types.py` directly and only compatibility coverage continues exercising the facade. |
| `src/bioetl/composition/services/metadata_coordinator.py` | Composition-level re-export shim for metadata coordinator service. | `bioetl.application.services.metadata_coordinator` | `compat-shim` | `bioetl.application.services` | `legacy-pre-2026-03` | `src`: none; `tests`: `tests/unit/composition/services/test_metadata_coordinator_reexport.py` | `2026-06-30` | Import `bioetl.application.services.metadata_coordinator` directly; keep shim usage only in dedicated compatibility tests. | First-party `src/` imports have migrated; keep only package-level compatibility coverage and explicit shim tests. |
| `src/bioetl/composition/services/metadata_assemblers.py` | Composition-level re-export shim for metadata assembler services. | `bioetl.application.services.metadata_assemblers` | `compat-shim` | `bioetl.application.services` | `legacy-pre-2026-03` | `src`: none; `tests`: `tests/unit/composition/services/test_metadata_assemblers_reexport.py` | `2026-06-30` | Import `bioetl.application.services.metadata_assemblers` directly; keep shim usage only in dedicated compatibility tests. | First-party `src/` imports have migrated; keep only compatibility smoke coverage for the shim. |
| `src/bioetl/infrastructure/adapters/_error_classifier.py` | Thin compatibility re-export for adapter error classification helpers. | `bioetl.infrastructure.adapters.adapter_error_classifier` | `compat-shim` | `bioetl.infrastructure.adapters` | `legacy-pre-2026-03` | `src`: none; `tests`: `tests/unit/infrastructure/adapters/test_adapter_error_classifier_compat.py` | `2026-06-30` | Import `bioetl.infrastructure.adapters.adapter_error_classifier` directly; keep the shim only for compatibility smoke coverage. | First-party imports stay on `adapter_error_classifier` directly and only dedicated compatibility smoke coverage exercises the shim. |
| `src/bioetl/infrastructure/adapters/chembl/fetch_mixin.py` | Thin compatibility shim for the legacy ChEMBL fetch mixin module path. | `bioetl.infrastructure.adapters.chembl.fetch_adapter_mixin` | `compat-shim` | `bioetl.infrastructure.adapters.chembl` | `legacy-pre-2026-03` | `src`: none; `tests`: `tests/unit/infrastructure/adapters/chembl/test_fetch_mixin.py`, `tests/architecture/test_adapter_contracts.py` | `2026-06-30` | Import `bioetl.infrastructure.adapters.chembl.fetch_adapter_mixin` directly; keep the shim only for compatibility smoke coverage. | First-party imports stay on `fetch_adapter_mixin` directly and only dedicated compatibility coverage exercises the legacy shim. |
| `src/bioetl/infrastructure/adapters/openalex/client_helpers_mixin.py` | Thin compatibility shim for the legacy OpenAlex helper mixin module path. | `bioetl.infrastructure.adapters.openalex.client_helpers_adapter_mixin` | `compat-shim` | `bioetl.infrastructure.adapters.openalex` | `legacy-pre-2026-03` | `src`: none; `tests`: `tests/unit/infrastructure/adapters/openalex/test_client_helpers_mixin.py`, `tests/architecture/test_adapter_contracts.py` | `2026-06-30` | Import `bioetl.infrastructure.adapters.openalex.client_helpers_adapter_mixin` directly; keep the shim only for compatibility smoke coverage. | First-party imports stay on `client_helpers_adapter_mixin` directly and only dedicated compatibility coverage exercises the legacy shim. |
| `src/bioetl/infrastructure/adapters/uniprot/metadata_mixin.py` | Thin compatibility shim for the legacy UniProt metadata mixin module path. | `bioetl.infrastructure.adapters.uniprot.metadata_adapter_mixin` | `compat-shim` | `bioetl.infrastructure.adapters.uniprot` | `legacy-pre-2026-03` | `src`: none; `tests`: `tests/unit/infrastructure/adapters/uniprot/test_metadata_mixin.py`, `tests/architecture/test_adapter_contracts.py` | `2026-06-30` | Import `bioetl.infrastructure.adapters.uniprot.metadata_adapter_mixin` directly; keep the shim only for compatibility smoke coverage. | First-party imports stay on `metadata_adapter_mixin` directly and only dedicated compatibility coverage exercises the legacy shim. |
| `src/bioetl/infrastructure/storage/delta_writer.py` | Legacy alias wrapper that preserves `DeltaWriter` imports over `SilverWriter`. | `bioetl.infrastructure.storage.silver_writer.SilverWriter` | `compat-shim` | `bioetl.infrastructure.storage` | `legacy-pre-2026-03` | `src`: none; `tests`: `tests/unit/infrastructure/storage/test_delta_writer_compat.py` | `2026-06-30` | Import `bioetl.infrastructure.storage.silver_writer.SilverWriter` directly; leave `delta_writer.py` only for compatibility coverage. | Benchmarks and tests stop importing `DeltaWriter` and use the canonical storage writer directly. |
| `src/bioetl/infrastructure/adapters/pubmed/client.py` | Canonical package entrypoint that shields older `pubmed_client` imports while exporting the current adapter surface and public `create_pubmed_adapter` factory alias. | `bioetl.infrastructure.adapters.pubmed.client` | `retained-entrypoint` | `bioetl.infrastructure.adapters.pubmed` | `2026-03 pubmed entrypoint hardening` | `src`: canonical entrypoint usage allowed; `tests`: `tests/unit/infrastructure/adapters/test_provider_entrypoints.py`, `tests/architecture/test_adapter_contracts.py` | `2026-09-30` | Use package-root imports or `bioetl.infrastructure.adapters.pubmed.client` with public `create_pubmed_adapter`; do not import `bioetl.infrastructure.adapters.pubmed.pubmed_client` directly. | RF-035 decision is `retain`: private `_create_pubmed_adapter` stays unexported from the retained entrypoint, and legacy-path references remain reduced to dedicated compatibility coverage. |
| `src/bioetl/infrastructure/adapters/semanticscholar/client.py` | Canonical package entrypoint that shields older `adapter` imports. | `bioetl.infrastructure.adapters.semanticscholar.client` | `retained-entrypoint` | `bioetl.infrastructure.adapters.semanticscholar` | `legacy-pre-2026-03` | `src`: canonical entrypoint usage allowed; `tests`: `tests/unit/infrastructure/adapters/test_provider_entrypoints.py`, `tests/architecture/test_adapter_contracts.py` | `2026-09-30` | Use package-root imports or `bioetl.infrastructure.adapters.semanticscholar.client`; do not import `bioetl.infrastructure.adapters.semanticscholar.adapter` directly. | RF-035 decision is `retain`: re-review only after the retained client shim no longer carries compatibility value beyond dedicated compatibility coverage. |
| `src/bioetl/application/core/checkpoint_manager.py` | Thin compatibility shim for historical application-core checkpoint manager imports. | `bioetl.application.core.lifecycle.checkpoint_manager` | `compat-shim` | `bioetl.application.core.lifecycle` | `legacy-pre-2026-03` | `src`: none; `tests`: `tests/unit/application/core/test_lifecycle_shim_reexports.py` | `2026-06-30` | Import `bioetl.application.core.lifecycle.checkpoint_manager` directly; keep the shim only for lifecycle compatibility smoke coverage. | First-party imports remain on lifecycle modules directly and only dedicated compatibility smoke coverage continues exercising the shim. |
| `src/bioetl/application/core/batch_transformer_helpers.py` | Compatibility facade for historical batch-transform helper imports spread across split helper modules. | `bioetl.application.core.batch_transformer_state`, `bioetl.application.core.batch_transformer_attempts`, `bioetl.application.core.batch_transformer_quarantine`, `bioetl.application.core.batch_transformer_orchestration` | `compat-shim` | `bioetl.application.core` | `legacy-pre-2026-03` | `src`: none; `tests`: `tests/unit/application/core/test_batch_transformer_helpers_reexport.py` | `2026-06-30` | Import the canonical batch helper modules or package-root exports directly; keep `batch_transformer_helpers.py` only for compatibility smoke coverage. | First-party imports remain on canonical helper modules directly and only dedicated compatibility smoke coverage continues exercising the facade. |
| `src/bioetl/application/core/cleanup_service.py` | Thin compatibility shim for historical application-core cleanup service imports. | `bioetl.application.core.lifecycle.cleanup_service` | `compat-shim` | `bioetl.application.core.lifecycle` | `legacy-pre-2026-03` | `src`: none; `tests`: `tests/unit/application/core/test_lifecycle_shim_reexports.py` | `2026-06-30` | Import `bioetl.application.core.lifecycle.cleanup_service` directly; keep the shim only for lifecycle compatibility smoke coverage. | First-party imports remain on lifecycle modules directly and only dedicated compatibility smoke coverage continues exercising the shim. |
| `src/bioetl/application/core/heartbeat.py` | Thin compatibility shim for historical application-core heartbeat imports. | `bioetl.application.core.lifecycle.heartbeat` | `compat-shim` | `bioetl.application.core.lifecycle` | `legacy-pre-2026-03` | `src`: none; `tests`: `tests/unit/application/core/test_lifecycle_shim_reexports.py` | `2026-06-30` | Import `bioetl.application.core.lifecycle.heartbeat` directly; keep the shim only for lifecycle compatibility smoke coverage. | First-party imports remain on lifecycle modules directly and only dedicated compatibility smoke coverage continues exercising the shim. |
| `src/bioetl/application/core/lock_manager.py` | Thin compatibility shim for historical application-core lock manager imports. | `bioetl.application.core.lifecycle.lock_manager` | `compat-shim` | `bioetl.application.core.lifecycle` | `legacy-pre-2026-03` | `src`: none; `tests`: `tests/unit/application/core/test_lifecycle_shim_reexports.py` | `2026-06-30` | Import `bioetl.application.core.lifecycle.lock_manager` directly; keep the shim only for lifecycle compatibility smoke coverage. | First-party imports remain on lifecycle modules directly and only dedicated compatibility smoke coverage continues exercising the shim. |
| `src/bioetl/application/core/shutdown.py` | Thin compatibility shim for historical application-core shutdown imports. | `bioetl.application.core.lifecycle.shutdown` | `compat-shim` | `bioetl.application.core.lifecycle` | `legacy-pre-2026-03` | `src`: none; `tests`: `tests/unit/application/core/test_lifecycle_shim_reexports.py` | `2026-06-30` | Import `bioetl.application.core.lifecycle.shutdown` directly; keep the shim only for lifecycle compatibility smoke coverage. | First-party imports remain on lifecycle modules directly and only dedicated compatibility smoke coverage continues exercising the shim. |

## Measured Registry

This registry is the measurable compatibility-surface baseline for CI. It is the union of:

- curated inventory rows listed above;
- module docstrings whose first line starts with a tracked compatibility prefix.

Snapshot for this cycle:

- Curated inventory rows: `27`
- Measured tracked modules: `27`
- Measured-only modules outside curated inventory: `0`

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
- `src/` direct imports of `bioetl.application.composite.join_planner_compat_mixin` outside `src/bioetl/application/composite/join_planner.py`: `0`
- `src/` direct imports of `bioetl.application.composite.merger_compat_mixin` outside `src/bioetl/application/composite/merger.py`: `0`
- `src/` direct imports of `bioetl.application.composite.runner`: `0`
- `src/` direct imports of split `bioetl.domain.composite.config_*` internals outside `src/bioetl/domain/composite/`: `0`
- `src/` direct imports of split activity/publication value-object internals outside `src/bioetl/domain/value_objects/`: `0`
- `src/` direct imports of `bioetl.application.core.base_transformer.dependencies`: `0`
- `src/` direct imports of `bioetl.application.core.batch_transformer_helpers`: `0`
- `src/` direct imports of `bioetl.application.core.checkpoint_manager`: `0`
- `src/` direct imports of `bioetl.application.core.cleanup_service`: `0`
- `src/` direct imports of `bioetl.application.core.heartbeat`: `0`
- `src/` direct imports of `bioetl.application.core.lock_manager`: `0`
- `src/` direct imports of `bioetl.application.core.shutdown`: `0`
- `src/` direct imports of `bioetl.composition.services.metadata_coordinator`: `0`
- `src/` direct imports of `bioetl.composition.services.metadata_assemblers`: `0`
- `src/` direct imports of `bioetl.infrastructure.adapters._error_classifier`: `0`
- `src/` direct imports of `bioetl.infrastructure.adapters.chembl.fetch_mixin`: `0`
- `src/` direct imports of `bioetl.infrastructure.adapters.openalex.client_helpers_mixin`: `0`
- `src/` direct imports of `bioetl.infrastructure.adapters.uniprot.metadata_mixin`: `0`
- `src/` direct imports of `bioetl.infrastructure.storage.delta_writer`: `0`
- `tests/` direct imports of `bioetl.composition.factories.datasource.factory` outside dedicated compatibility coverage: `0`
- `src/` direct `DataSourceRegistry` usages outside explicit compatibility re-exports: `0`
- `tests/` direct `DataSourceRegistry` imports outside dedicated compatibility/contract coverage: `0`
- Dedicated compatibility coverage remains in tests:
  - `tests/unit/composition/factories/datasource/test_data_source_registry.py`
  - `tests/unit/composition/test_registry_protocol.py`
  - `tests/architecture/test_registry_contracts.py`
  - `tests/unit/composition/test_canonical_module_paths.py`
  - `tests/unit/application/composite/test_runner_root_facade_reexport.py`
  - `tests/unit/domain/value_objects/test_value_object_facade_reexports.py`
  - `tests/unit/domain/composite/test_composite_config_facade.py`
  - `tests/unit/application/core/test_batch_transformer_helpers_reexport.py`
  - `tests/unit/application/core/test_lifecycle_shim_reexports.py`
  - `tests/unit/application/core/test_base_transformer_dependencies_reexport.py`
  - `tests/unit/composition/services/test_metadata_coordinator_reexport.py`
  - `tests/unit/composition/services/test_metadata_assemblers_reexport.py`
  - `tests/unit/infrastructure/adapters/test_adapter_error_classifier_compat.py`
  - `tests/unit/infrastructure/adapters/chembl/test_fetch_mixin.py`
  - `tests/unit/infrastructure/adapters/openalex/test_client_helpers_mixin.py`
  - `tests/unit/infrastructure/adapters/uniprot/test_metadata_mixin.py`
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
  of the retained public `create_pubmed_adapter` factory surface.

Related docs:

- [Composition Layer](05-composition-layer.md)
- [Registry Pattern](../03-guides/registry-pattern.md)
