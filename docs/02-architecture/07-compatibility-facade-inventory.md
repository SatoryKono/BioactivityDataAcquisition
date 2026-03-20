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
| `retained-entrypoint` | Canonical public entrypoint that intentionally shields older implementation-module paths. | Keep using the sanctioned public seam for new code (entrypoint module directly or owning package root that re-exports it); avoid the older implementation-module path it replaces. | Legacy implementation-path imports reach zero and the remaining surface is explicitly reviewed. |

## Governance Freeze

This inventory is also the freeze ledger for compatibility debt in the current cycle.

- Every listed concern MUST have one accountable owner, one canonical target, one `introduced_in` marker, one `migration_path`, and one explicit remove-by or review date.
- New first-party `src/` imports MUST go through the canonical target named below.
- Compatibility entrypoints remain only as controlled transition surfaces.
- Allowed call sites are explicit. Adding new ones is a regression unless the inventory is updated first.
- For `retained-entrypoint` rows, the remove-by field is interpreted as a mandatory review date, not an automatic deletion date.
- Canonical documentation updates for active architecture/reference guidance MUST land only after the corresponding technical change-set is green on targeted verification.
- `docs/exports/**`, `docs/reports/**`, and `docs/99-archive/**` are evidence/history zones and MUST NOT replace canonical guidance in `docs/02-architecture/**`, `docs/03-guides/**`, or `docs/04-reference/**`.

## Mandatory Artifact Sync

The following artifacts are operational architecture/config signals and are treated as mandatory:

- `docs/02-architecture/generated/module-dependency-map.md`
- `docs/02-architecture/generated/module-dependency-map.json`
- `docs/02-architecture/07-compatibility-facade-inventory.md`
- active config docs synchronized by config/schema guardrails

Canonical commands for this cycle:

```bash
./.venv/Scripts/python.exe -m pytest tests/architecture/test_architecture_dependency_docs_drift.py -q
./.venv/Scripts/python.exe scripts/qa/generate_architecture_dependency_map.py --check
./.venv/Scripts/python.exe scripts/qa/generate_architecture_dependency_map.py --update
./.venv/Scripts/python.exe -m pytest tests/architecture/test_compatibility_facade_inventory.py -q
./.venv/Scripts/python.exe -m pytest tests/architecture/test_config_schema_legacy_status.py -q
./.venv/Scripts/python.exe -m pytest tests/architecture/test_documentation_sync.py -q
./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs
```

Artifact-to-command policy:

- dependency map markdown/JSON: generated only by `scripts/qa/generate_architecture_dependency_map.py`
- compatibility inventory: curated doc guarded by `tests/architecture/test_compatibility_facade_inventory.py`
- config/runtime guidance: active docs stay aligned through `tests/architecture/test_config_schema_legacy_status.py`
- internal docs references: validated through `scripts/docs/check_doc_links.py --configs`

Fast local repair path:

1. If `test_architecture_dependency_docs_drift.py` fails, run `./.venv/Scripts/python.exe scripts/qa/generate_architecture_dependency_map.py --update`.
2. Re-run `test_architecture_dependency_docs_drift.py`, `test_compatibility_facade_inventory.py`, and `test_documentation_sync.py`.
3. Use [`../../scripts/README.md`](../../scripts/README.md) for the canonical scripts index; treat `docs/reports/**` as historical evidence only, not as repair guidance.

## Inventory

This inventory is split into two curated ledgers:

- `Transition debt ledger`: rows that still count toward the zero-compatibility target for
  the current cycle. These are the only rows that must reach `0` before the cycle can be
  considered complete.
- `Retained public entrypoints`: sanctioned public seams that intentionally remain stable.
  They are governed here for import-discipline purposes, but they are not counted as
  transition compatibility debt.

### Transition Debt Ledger

| Path | Compatibility role | Canonical target | Status | Owner | Introduced in | Allowed call sites | Remove by / review date | Migration path | Exit criteria |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
No active transition-debt rows remain in the current cycle.

### Retained Public Entrypoints

| Path | Compatibility role | Canonical target | Status | Owner | Introduced in | Allowed call sites | Remove by / review date | Migration path | Exit criteria |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `src/bioetl/composition/entrypoints.py` | Canonical composition entrypoint that intentionally shields internal `_pipeline_execution`, `_resource_management`, and `_services` module paths. | `bioetl.composition.entrypoints` | `retained-entrypoint` | `bioetl.composition` | `2026-03 entrypoint freeze` | `src`: canonical entrypoint usage allowed; `tests`: public entrypoint imports may appear in interface/composition boundary coverage, but direct internal-module patch targets stay confined to `tests/unit/composition/test_entrypoints.py`, `tests/unit/composition/test_resource_management.py`, and `tests/unit/composition/test_services_entrypoints.py` | `2026-09-30` | Use `bioetl.composition.entrypoints` as the public seam; do not import `bioetl.composition._pipeline_execution`, `bioetl.composition._resource_management`, or `bioetl.composition._services` directly outside dedicated entrypoint-boundary coverage. | Internal implementation-module imports outside `composition/` stay at zero and internal-module patch coverage remains confined to the dedicated entrypoint-boundary tests. |
| `src/bioetl/domain/composite/config.py` | Canonical public entrypoint for composite config models that shields split config internals. | `bioetl.domain.composite.config` | `retained-entrypoint` | `bioetl.domain.composite` | `legacy-pre-2026-03` | `src`: canonical entrypoint usage allowed; internal split modules stay inside `src/bioetl/domain/composite/`; `tests`: direct split-internal coverage stays confined to `tests/unit/domain/composite/test_composite_config_facade.py` and `tests/unit/domain/composite/test_composite_config_edge_cases.py`, while ordinary tests keep importing the root config entrypoint | `2026-09-30` | Keep using `bioetl.domain.composite.config`; do not import split `config_*` internals outside the owning package or the dedicated composite-config coverage tests. | Direct imports of split config internals remain confined to the owning package plus the dedicated composite-config coverage tests, and the root config entrypoint stays the stable public path. |
| `src/bioetl/domain/value_objects/activity_values.py` | Canonical public entrypoint for activity-related value objects that shields split concentration/type/pChEMBL modules. | `bioetl.domain.value_objects.activity_values` | `retained-entrypoint` | `bioetl.domain.value_objects` | `legacy-pre-2026-03` | `src`: canonical entrypoint usage allowed; internal split modules stay inside `src/bioetl/domain/value_objects/`; `tests`: direct split-internal coverage stays confined to `tests/unit/domain/value_objects/test_value_object_facade_reexports.py`, while ordinary tests keep importing the public entrypoint | `2026-09-30` | Keep using `bioetl.domain.value_objects.activity_values`; do not import split value-object internals outside the owning package or the dedicated facade-coverage test. | Direct imports of split activity-value internals remain confined to the owning package plus the dedicated facade-coverage test, and the facade stays the stable public path. |
| `src/bioetl/domain/value_objects/publication_field_groups.py` | Canonical public entrypoint for publication field-group definitions that shields private split config/type modules. | `bioetl.domain.value_objects.publication_field_groups` | `retained-entrypoint` | `bioetl.domain.value_objects` | `legacy-pre-2026-03` | `src`: canonical entrypoint usage allowed; private split modules stay inside `src/bioetl/domain/value_objects/`; `tests`: direct split-internal coverage stays confined to `tests/unit/domain/value_objects/test_value_object_facade_reexports.py`, while ordinary tests keep importing the public entrypoint | `2026-09-30` | Keep using `bioetl.domain.value_objects.publication_field_groups`; do not import split value-object internals outside the owning package or the dedicated facade-coverage test. | Direct imports of private publication-field-group internals remain confined to the owning package plus the dedicated facade-coverage test, and the facade stays the stable public path. |
| `src/bioetl/application/composite/merger.py` | Canonical composite merge module that requires `MergeCollaboratorGroup` bundle; legacy per-collaborator keyword wiring removed in RF-009.2. | `bioetl.application.composite.merger` | `retained-entrypoint` | `bioetl.application.composite` | `2026-03 merge collaborator migration` | `src`: all wiring passes `collaborators=MergeCollaboratorGroup(...)`; `tests`: `tests/unit/application/composite/test_merger.py`, `tests/unit/application/composite/merge_test_support.py`, `tests/unit/composition/bootstrap/runtime/test_composite_support_services_factory.py` | `2026-09-30` | Use `bioetl.application.composite.merger` with `collaborators=MergeCollaboratorGroup(...)`. | All composition paths use collaborator bundles; legacy keyword wiring fully removed. |
| `src/bioetl/infrastructure/adapters/pubmed/client.py` | Retained client entrypoint that shields older `pubmed_client` imports while exporting the current adapter surface and public `create_pubmed_adapter` factory alias. | `bioetl.infrastructure.adapters.pubmed.client` | `retained-entrypoint` | `bioetl.infrastructure.adapters.pubmed` | `2026-03 pubmed entrypoint hardening` | `src`: direct `bioetl.infrastructure.adapters.pubmed.client` imports stay confined to `src/bioetl/infrastructure/adapters/pubmed/__init__.py`; first-party code imports the provider package root; `tests`: `tests/unit/infrastructure/adapters/test_provider_entrypoints.py`, `tests/architecture/test_adapter_contracts.py`, `tests/architecture/test_retained_adapter_entrypoint_policy.py` | `2026-09-30` | Use the provider package root `bioetl.infrastructure.adapters.pubmed` in new first-party code; keep `bioetl.infrastructure.adapters.pubmed.client` only as the retained public seam and do not import `bioetl.infrastructure.adapters.pubmed.pubmed_client` directly. | RF-035 decision is `retain`: direct `client.py` imports stay confined to the provider package root plus dedicated compatibility coverage, and private `_create_pubmed_adapter` remains unexported from the retained entrypoint. |
| `src/bioetl/infrastructure/adapters/semanticscholar/client.py` | Retained client entrypoint that shields older `adapter` imports. | `bioetl.infrastructure.adapters.semanticscholar.client` | `retained-entrypoint` | `bioetl.infrastructure.adapters.semanticscholar` | `legacy-pre-2026-03` | `src`: direct `bioetl.infrastructure.adapters.semanticscholar.client` imports stay confined to `src/bioetl/infrastructure/adapters/semanticscholar/__init__.py`; first-party code imports the provider package root; `tests`: `tests/unit/infrastructure/adapters/test_provider_entrypoints.py`, `tests/architecture/test_adapter_contracts.py`, `tests/architecture/test_retained_adapter_entrypoint_policy.py` | `2026-09-30` | Use the provider package root `bioetl.infrastructure.adapters.semanticscholar` in new first-party code; keep `bioetl.infrastructure.adapters.semanticscholar.client` only as the retained public seam and do not import `bioetl.infrastructure.adapters.semanticscholar.adapter` directly. | RF-035 decision is `retain`: direct `client.py` imports stay confined to the provider package root plus dedicated compatibility coverage, and legacy-path references remain reduced to that retained seam. |

## Measured Registry

This registry is the measurable compatibility-surface baseline for CI. It is the union of:

- curated inventory rows listed above;
- module docstrings whose first line starts with a tracked compatibility prefix.

Snapshot for this cycle:

- Curated inventory rows: `7`
- Transition debt rows: `0`
- Retained public entrypoints: `7`
- Measured tracked modules: `9`
- Measured-only modules outside curated inventory: `2`

Tracked module paths:

- `src/bioetl/composition/entrypoints.py`
- `src/bioetl/domain/composite/config.py`
- `src/bioetl/domain/value_objects/activity_values.py`
- `src/bioetl/domain/value_objects/publication_field_groups.py`
- `src/bioetl/application/composite/merger.py`
- `src/bioetl/application/pipelines/chembl/_pipelines.py`
- `src/bioetl/infrastructure/adapters/pubmed/client.py`
- `src/bioetl/infrastructure/adapters/semanticscholar/client.py`
- `src/bioetl/composition/factories/services/creation_api.py`

## Usage Notes

- `deprecated-warn`, `compat-shim`, and `mixed-module` rows in the transition debt ledger
  must remain at `0` for the current cycle.
- `mixed-module` rows require symbol-level migration, not whole-module deletion by default.
- `retained-entrypoint` rows live in the retained public-entrypoint ledger and are not counted
  as transition compatibility debt for the current cycle.
- Top-level CLI command modules under `bioetl.interfaces.cli.commands` now count as sanctioned
  public entrypoints/support seams rather than compatibility-only shims; they are no longer
  tracked in the measured compatibility registry unless a module is explicitly marked as
  transition-only again.
- For provider adapters, first-party code should prefer provider package roots when those roots are
  the documented canonical path; retained `client.py` modules remain stable compatibility seams.

## Current Import Inventory

Snapshot for the current compatibility-governance cycle:

- `src/` direct imports of `bioetl.composition._pipeline_execution` outside `src/bioetl/composition/`: `0`
- `src/` direct imports of `bioetl.composition._resource_management` outside `src/bioetl/composition/`: `0`
- `src/` direct imports of `bioetl.composition._services` outside `src/bioetl/composition/`: `0`
- `src/` direct imports of split `bioetl.domain.composite.config_*` internals outside `src/bioetl/domain/composite/`: `0`
- `src/` direct imports of split activity/publication value-object internals outside `src/bioetl/domain/value_objects/`: `0`
- `src/` direct imports of `bioetl.infrastructure.storage.metadata_builder_composite_helpers`: module removed
- `tests/` string patch mentions of local CLI `get_default_registry` compat aliases: `0`
- `src/` direct imports of `bioetl.infrastructure.adapters.pubmed.client` outside `src/bioetl/infrastructure/adapters/pubmed/__init__.py`: `0`
- `src/` direct imports of `bioetl.infrastructure.adapters.semanticscholar.client` outside `src/bioetl/infrastructure/adapters/semanticscholar/__init__.py`: `0`
- `src/` direct `DataSourceRegistry` usages outside explicit compatibility re-exports: `0`
- `tests/` direct `DataSourceRegistry` imports outside dedicated compatibility/contract coverage: `0`
- `tests/` direct imports of `bioetl.infrastructure.storage.metadata_builder_composite_helpers`: `0`
- `tests/` direct imports of retained adapter client entrypoints outside dedicated compatibility/contract coverage: `0`
- Dedicated compatibility coverage remains in tests:
- `tests/unit/composition/factories/datasource/test_data_source_registry.py`
- `tests/unit/composition/test_registry_protocol.py`
- `tests/architecture/test_registry_contracts.py`
- `tests/unit/domain/value_objects/test_value_object_facade_reexports.py`
- `tests/unit/domain/composite/test_composite_config_facade.py`
- `tests/unit/domain/composite/test_composite_config_edge_cases.py`
- `tests/unit/infrastructure/adapters/test_provider_entrypoints.py`
- `tests/architecture/test_adapter_contracts.py`
- `tests/architecture/test_retained_adapter_entrypoint_policy.py`
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
- New first-party code should use provider package roots; retained `client.py` entrypoints exist for stability and dedicated compatibility coverage only.
- New first-party code must not import the older implementation modules
  `pubmed.pubmed_client` or `semanticscholar.adapter` directly.
- Any future deprecation proposal must include a fresh usage inventory and an explicit review
  of the retained public `create_pubmed_adapter` factory surface.

## Retained Entrypoint Review Wave (2026-03-15)

Review outcome for the remaining curated inventory rows:

- `src/bioetl/composition/entrypoints.py`: `retain`
  because active first-party interface code still uses it as the public seam while
  `_pipeline_execution`, `_resource_management`, and `_services` remain confined to
  `composition/` and dedicated entrypoint tests.
- `src/bioetl/domain/composite/config.py`: `retain`
  because application, composition, infrastructure, and tests depend on the root config
  entrypoint while split `config_*` internals remain confined to `domain/composite/`
  and the dedicated facade test.
- `src/bioetl/domain/value_objects/activity_values.py`: `retain`
  because domain/application code uses the public activity value-object entrypoint and
  the split implementation modules remain confined to `domain/value_objects/`.
- `src/bioetl/domain/value_objects/publication_field_groups.py`: `retain`
  because public field-group types are consumed through the root entrypoint while
  private `_publication_field_group_*` modules remain internal.
- `src/bioetl/infrastructure/adapters/pubmed/client.py`: `retain`
  because the package root and provider registration still use the canonical client
  entrypoint while direct `client.py` imports are already confined to the package
  root and dedicated compatibility coverage, and legacy `pubmed_client`
  references stay confined to the retained entrypoint plus dedicated coverage.
- `src/bioetl/infrastructure/adapters/semanticscholar/client.py`: `retain`
  because the package root still uses the canonical client entrypoint, direct
  `client.py` imports are already confined to the package root plus dedicated
  compatibility coverage, and legacy `adapter` references remain confined to the
  retained entrypoint plus dedicated coverage.

Wave decision:

- No retained-entrypoint row graduates to removal in the current cycle.
- Next action is policy enforcement and re-review by `2026-09-30`, not deprecation.

Related docs:

- [Composition Layer](05-composition-layer.md)
- [Registry Pattern](../03-guides/registry-pattern.md)
