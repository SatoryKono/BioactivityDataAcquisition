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
- Canonical documentation updates for active architecture/reference guidance MUST land only after the corresponding technical change-set is green on targeted verification.
- `docs/exports/**`, `docs/reports/**`, and `docs/99-archive/**` are evidence/history zones and MUST NOT replace canonical guidance in `docs/02-architecture/**`, `docs/03-guides/**`, or `docs/04-reference/**`.

## Inventory

| Path | Compatibility role | Canonical target | Status | Owner | Introduced in | Allowed call sites | Remove by / review date | Migration path | Exit criteria |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `src/bioetl/composition/entrypoints.py` | Canonical composition entrypoint that intentionally shields internal `_pipeline_execution`, `_resource_management`, and `_services` module paths. | `bioetl.composition.entrypoints` | `retained-entrypoint` | `bioetl.composition` | `2026-03 entrypoint freeze` | `src`: canonical entrypoint usage allowed; `tests`: CLI and composition entrypoint boundary coverage | `2026-09-30` | Use `bioetl.composition.entrypoints` as the public seam; do not import `bioetl.composition._pipeline_execution` or `bioetl.composition._resource_management` directly. | Internal implementation-module imports outside `composition/` stay at zero and entrypoint-only compatibility coverage remains explicit. |
| `src/bioetl/domain/composite/config.py` | Canonical public entrypoint for composite config models that shields split config internals. | `bioetl.domain.composite.config` | `retained-entrypoint` | `bioetl.domain.composite` | `legacy-pre-2026-03` | `src`: canonical entrypoint usage allowed; internal split modules stay inside `src/bioetl/domain/composite/`; `tests`: facade coverage in `tests/unit/domain/composite/test_composite_config_facade.py` and ordinary imports may continue using the root config entrypoint | `2026-09-30` | Keep using `bioetl.domain.composite.config`; do not import split `config_*` internals outside the owning package. | Direct imports of split config internals remain confined to the owning package and the root config entrypoint stays the stable public path. |
| `src/bioetl/domain/value_objects/activity_values.py` | Canonical public entrypoint for activity-related value objects that shields split concentration/type/pChEMBL modules. | `bioetl.domain.value_objects.activity_values` | `retained-entrypoint` | `bioetl.domain.value_objects` | `legacy-pre-2026-03` | `src`: canonical entrypoint usage allowed; internal split modules stay inside `src/bioetl/domain/value_objects/`; `tests`: facade coverage in `tests/unit/domain/value_objects/test_value_object_facade_reexports.py` and ordinary imports may continue using the public entrypoint | `2026-09-30` | Keep using `bioetl.domain.value_objects.activity_values`; do not import split value-object internals outside the owning package. | Direct imports of split activity-value internals remain confined to the owning package and the facade stays the stable public path. |
| `src/bioetl/domain/value_objects/publication_field_groups.py` | Canonical public entrypoint for publication field-group definitions that shields private split config/type modules. | `bioetl.domain.value_objects.publication_field_groups` | `retained-entrypoint` | `bioetl.domain.value_objects` | `legacy-pre-2026-03` | `src`: canonical entrypoint usage allowed; private split modules stay inside `src/bioetl/domain/value_objects/`; `tests`: facade coverage in `tests/unit/domain/value_objects/test_value_object_facade_reexports.py` and ordinary imports may continue using the public entrypoint | `2026-09-30` | Keep using `bioetl.domain.value_objects.publication_field_groups`; do not import split value-object internals outside the owning package. | Direct imports of private publication-field-group internals remain confined to the owning package and the facade stays the stable public path. |
| `src/bioetl/infrastructure/adapters/pubmed/client.py` | Canonical package entrypoint that shields older `pubmed_client` imports while exporting the current adapter surface and public `create_pubmed_adapter` factory alias. | `bioetl.infrastructure.adapters.pubmed.client` | `retained-entrypoint` | `bioetl.infrastructure.adapters.pubmed` | `2026-03 pubmed entrypoint hardening` | `src`: canonical entrypoint usage allowed; `tests`: `tests/unit/infrastructure/adapters/test_provider_entrypoints.py`, `tests/architecture/test_adapter_contracts.py` | `2026-09-30` | Use package-root imports or `bioetl.infrastructure.adapters.pubmed.client` with public `create_pubmed_adapter`; do not import `bioetl.infrastructure.adapters.pubmed.pubmed_client` directly. | RF-035 decision is `retain`: private `_create_pubmed_adapter` stays unexported from the retained entrypoint, and legacy-path references remain reduced to dedicated compatibility coverage. |
| `src/bioetl/infrastructure/adapters/semanticscholar/client.py` | Canonical package entrypoint that shields older `adapter` imports. | `bioetl.infrastructure.adapters.semanticscholar.client` | `retained-entrypoint` | `bioetl.infrastructure.adapters.semanticscholar` | `legacy-pre-2026-03` | `src`: canonical entrypoint usage allowed; `tests`: `tests/unit/infrastructure/adapters/test_provider_entrypoints.py`, `tests/architecture/test_adapter_contracts.py` | `2026-09-30` | Use package-root imports or `bioetl.infrastructure.adapters.semanticscholar.client`; do not import `bioetl.infrastructure.adapters.semanticscholar.adapter` directly. | RF-035 decision is `retain`: re-review only after the retained client shim no longer carries compatibility value beyond dedicated compatibility coverage. |

## Measured Registry

This registry is the measurable compatibility-surface baseline for CI. It is the union of:

- curated inventory rows listed above;
- module docstrings whose first line starts with a tracked compatibility prefix.

Snapshot for this cycle:

- Curated inventory rows: `6`
- Measured tracked modules: `6`
- Measured-only modules outside curated inventory: `0`

Tracked module paths:

- `src/bioetl/composition/entrypoints.py`
- `src/bioetl/domain/composite/config.py`
- `src/bioetl/domain/value_objects/activity_values.py`
- `src/bioetl/domain/value_objects/publication_field_groups.py`
- `src/bioetl/infrastructure/adapters/pubmed/client.py`
- `src/bioetl/infrastructure/adapters/semanticscholar/client.py`

## Usage Notes

- `deprecated-warn` and `compat-shim` rows count as compatibility debt and should shrink over time.
- `mixed-module` rows require symbol-level migration, not whole-module deletion by default.
- `retained-entrypoint` rows are not removal targets in the current cycle; they exist to stabilize
  provider package imports while internal implementation modules continue to evolve.

## Current Import Inventory

Snapshot after RF-002 controlled removal wave:

- `src/` direct imports of `bioetl.composition._pipeline_execution` outside `src/bioetl/composition/`: `0`
- `src/` direct imports of `bioetl.composition._resource_management` outside `src/bioetl/composition/`: `0`
- `src/` direct imports of `bioetl.composition._services` outside `src/bioetl/composition/`: `0`
- `src/` direct imports of split `bioetl.domain.composite.config_*` internals outside `src/bioetl/domain/composite/`: `0`
- `src/` direct imports of split activity/publication value-object internals outside `src/bioetl/domain/value_objects/`: `0`
- `src/` direct `DataSourceRegistry` usages outside explicit compatibility re-exports: `0`
- `tests/` direct `DataSourceRegistry` imports outside dedicated compatibility/contract coverage: `0`
- Dedicated compatibility coverage remains in tests:
- `tests/unit/composition/factories/datasource/test_data_source_registry.py`
- `tests/unit/composition/test_registry_protocol.py`
- `tests/architecture/test_registry_contracts.py`
- `tests/unit/domain/value_objects/test_value_object_facade_reexports.py`
- `tests/unit/domain/composite/test_composite_config_facade.py`
- `tests/unit/composition/test_services_entrypoints.py`
- `tests/unit/composition/test_entrypoints.py`
- `tests/unit/composition/test_resource_management.py`

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
