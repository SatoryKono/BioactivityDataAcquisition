______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Compatibility Facade Inventory

`Status:` active

## Purpose

This document is the curated inventory of module-level compatibility facades and shims that
remain in the BioETL source tree to preserve import stability during refactoring.

Scope rules:

- The inventory is curated, not exhaustive for every single deprecated symbol or alias.
- Only module-level facades with architectural significance are listed here.
- Symbol-level compatibility aliases inside otherwise canonical modules are governed in
  code and targeted docs first; they stay outside this ledger unless they become a
  sanctioned public seam or a promoted transition-alias family that needs explicit
  facade governance.
- New code must prefer the canonical target module named in the inventory row.

## Status Model

| Status                | Meaning                                                                                                                    | New code policy                                                                                                                                                                    | Exit trigger                                                                                    |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `deprecated-warn`     | Facade already emits `DeprecationWarning` on compatibility calls.                                                          | Do not add new imports or new call sites. Migrate existing usage to canonical modules.                                                                                             | First-party imports disappear outside dedicated compatibility tests.                            |
| `compat-shim`         | Thin re-export or alias kept only to avoid a breaking import rename.                                                       | Freeze the surface. New code imports the canonical module directly.                                                                                                                | Internal call sites migrate and only package-level compatibility coverage remains.              |
| `mixed-module`        | Module contains both canonical logic and compatibility surface, so deprecation applies only to part of the API.            | New helpers should land in canonical submodules, not in the mixed module compatibility surface.                                                                                    | Compatibility-only symbols no longer needed and tests stop patching them.                       |
| `retained-entrypoint` | Canonical public entrypoint that intentionally shields older implementation-module paths.                                  | Keep using the sanctioned public seam for new code (entrypoint module directly or owning package root that re-exports it); avoid the older implementation-module path it replaces. | Legacy implementation-path imports reach zero and the remaining surface is explicitly reviewed. |
| `public-entrypoint`   | Permanent public entrypoint intentionally kept as the stable patch/import seam over internal split implementation modules. | Use the public entrypoint directly for runtime wiring, tests, and patch targets; do not import the internal owner module outside approved boundary coverage.                       | No automatic removal target; review only if the public API contract itself changes.             |

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

- `configs/quality/compatibility_facade_inventory.yaml`
- `configs/quality/compatibility_twin_module_ratchet.yaml`
- `configs/quality/infrastructure_config_root_facade_inventory.yaml`
- `docs/02-architecture/generated/module-dependency-map.md`
- `docs/02-architecture/generated/module-dependency-map.json`
- `docs/02-architecture/07-compatibility-facade-snapshot.md`
- `docs/02-architecture/07-compatibility-facade-inventory.md`
- `reports/quality/compatibility-importer-census.json`
- `reports/quality/compatibility-importer-census.md`
- active config docs synchronized by config/schema guardrails

Canonical commands for this cycle:

```bash
uv run python -m pytest tests/architecture/test_architecture_dependency_docs_drift.py -q
uv run python -m scripts.engineering.qa report-dep-map --check
uv run python -m scripts.engineering.qa report-dep-map --update
uv run python -m scripts.engineering.qa report-compatibility-importer-census
./.venv/Scripts/python.exe scripts/engineering/qa/generate_architecture_dependency_map.py --check
./.venv/Scripts/python.exe scripts/engineering/qa/generate_architecture_dependency_map.py --update
uv run python scripts/engineering/qa/generate_compatibility_facade_snapshot.py --check
uv run python scripts/engineering/qa/generate_compatibility_facade_snapshot.py --update
./.venv/Scripts/python.exe scripts/engineering/qa/generate_compatibility_facade_snapshot.py --check
./.venv/Scripts/python.exe scripts/engineering/qa/generate_compatibility_facade_snapshot.py --update
uv run python -m pytest tests/architecture/test_compatibility_facade_inventory.py -q
./.venv/Scripts/python.exe -m pytest tests/architecture/test_compatibility_facade_inventory.py -q
uv run python -m pytest tests/architecture/test_config_schema_legacy_status.py -q
uv run python -m pytest tests/architecture/test_documentation_sync.py -q
uv run python -m scripts.docs check-links --configs
```

Artifact-to-command policy:

- dependency map markdown/JSON: generated only by `scripts/engineering/qa/generate_architecture_dependency_map.py`
- dependency map markdown/JSON: layer-policy/topology snapshot only; hotspot, duplication, size, and churn pressure stay separate report-only signals and MUST NOT be inferred from zero layer violations alone
- compatibility registry YAML: canonical SSOT for curated rows, measured-only allowlist, and tracked docstring prefixes
- compatibility snapshot markdown: generated only by `scripts/engineering/qa/generate_compatibility_facade_snapshot.py`
- compatibility inventory: curated operational doc guarded by `tests/architecture/test_compatibility_facade_inventory.py`
- config/runtime guidance: active docs stay aligned through `tests/architecture/test_config_schema_legacy_status.py`
- internal docs references: validated through `python -m scripts.docs check-links --configs`

Fast local repair path:

1. If `test_architecture_dependency_docs_drift.py` fails, run `uv run python -m scripts.engineering.qa report-dep-map --update`.
1. If compatibility snapshot drift fails, update `configs/quality/compatibility_facade_inventory.yaml` first when policy changed, then run `uv run python scripts/engineering/qa/generate_compatibility_facade_snapshot.py --update`.
1. Re-run `test_architecture_dependency_docs_drift.py`, `test_compatibility_facade_inventory.py`, and `test_documentation_sync.py`.
1. Use `scripts/engineering/README.md` for the canonical scripts index; treat `docs/reports/**` as historical evidence only, not as repair guidance.

## Inventory

This inventory is split into two curated ledgers:

- `Transition debt ledger`: rows that still count toward the zero-compatibility target for
  the current cycle. These are the only rows that must reach `0` before the cycle can be
  considered complete.
- `Retained public entrypoints`: sanctioned public seams that intentionally remain stable.
  They are governed here for import-discipline purposes, but they are not counted as
  transition compatibility debt.

Scorecard alignment:

- `configs/quality/debt_scorecard.yaml` now treats only `transition_debt` rows plus
  active/expired sunset shims as compatibility debt.
- `public-entrypoint` rows remain visible through this inventory and a separate
  sanctioned-public-entrypoint governance metric, but they are not technical debt
  unless they regress back into transition-only compatibility shims.

### Transition Debt Ledger

| Path                                                        | Compatibility role | Canonical target | Status | Owner | Introduced in | Allowed call sites | Remove by / review date | Migration path | Exit criteria |
| ----------------------------------------------------------- | ------------------ | ---------------- | ------ | ----- | ------------- | ------------------ | ----------------------- | -------------- | ------------- |

Current baseline status: empty. The last reduction wave removed the deprecated
storage adapter shim (`composition/factories/storage/adapter.py`) and the
checkpoint anchor-context shim
(`application/composite/checkpoint/anchor_context.py`), so any new row here is
an immediate regression.

### Sanctioned Public Entrypoints

| Path                                                           | Compatibility role                                                                                                                                                          | Canonical target                                        | Status              | Owner                                            | Introduced in                          | Allowed call sites                                                                                                                                                                                                                                                                                                                                                                                                                             | Remove by / review date | Migration path                                                                                                                                                                                                                                                                                  | Exit criteria                                                                                                                                                                                                                                    |
| -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- | ------------------- | ------------------------------------------------ | -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/bioetl/interfaces/cli/commands/run.py` | Permanent public run command seam over the retained domain helper modules under `bioetl.interfaces.cli.commands.domains.run`. | `bioetl.interfaces.cli.commands.run` | `public-entrypoint` | `bioetl.interfaces.cli.commands` | `2026-03 RF-024` | `src`: use `bioetl.interfaces.cli.commands.run` as the public seam; `src/bioetl/interfaces/cli/commands/domains/run/__init__.py` may re-export that public module for package compatibility only. `tests`: patch/import coverage may target `bioetl.interfaces.cli.commands.run`; retired wrapper module `bioetl.interfaces.cli.commands.domains.run.command` must stay absent | `2026-09-30` | Use `bioetl.interfaces.cli.commands.run` for public CLI wiring and patch targets; do not reintroduce `bioetl.interfaces.cli.commands.domains.run.command` as an internal owner wrapper. | The top-level module remains the sanctioned public CLI patch/import seam, the domain package resolves directly to that public module, and the retired `domains.run.command` wrapper stays absent. |
| `src/bioetl/interfaces/cli/commands/run_all.py` | Permanent public run-all command seam over the split internal owner module `bioetl.interfaces.cli.commands.domains.run_all.command`. | `bioetl.interfaces.cli.commands.run_all` | `public-entrypoint` | `bioetl.interfaces.cli.commands` | `2026-03 RF-024` | `src`: use `bioetl.interfaces.cli.commands.run_all` as the public seam; direct internal-owner imports stay confined to `src/bioetl/interfaces/cli/commands/domains/run_all/__init__.py`; `tests`: patch/import coverage may target `bioetl.interfaces.cli.commands.run_all`, while direct `bioetl.interfaces.cli.commands.domains.run_all.command` imports stay confined to dedicated boundary coverage | `2026-09-30` | Use `bioetl.interfaces.cli.commands.run_all` for public CLI wiring and patch targets; do not import `bioetl.interfaces.cli.commands.domains.run_all.command` directly outside the owning package or dedicated boundary tests. | The top-level module remains the sanctioned public CLI patch/import seam, and direct internal-owner imports remain confined to the owning package plus dedicated boundary tests. |
| `src/bioetl/interfaces/cli/commands/run_composite.py` | Permanent public run-composite command seam over the internal owner module `bioetl.interfaces.cli.commands.domains.composite.command`. | `bioetl.interfaces.cli.commands.run_composite` | `public-entrypoint` | `bioetl.interfaces.cli.commands` | `2026-03 RF-024` | `src`: use `bioetl.interfaces.cli.commands.run_composite` as the public seam; direct internal-owner imports stay confined to `src/bioetl/interfaces/cli/commands/domains/composite/__init__.py`; `tests`: patch/import coverage may target `bioetl.interfaces.cli.commands.run_composite`, while direct `bioetl.interfaces.cli.commands.domains.composite.command` imports stay confined to dedicated boundary coverage | `2026-09-30` | Use `bioetl.interfaces.cli.commands.run_composite` for public CLI wiring and patch targets; do not import `bioetl.interfaces.cli.commands.domains.composite.command` directly outside the owning package or dedicated boundary tests. | The top-level module remains the sanctioned public CLI patch/import seam, and direct internal-owner imports remain confined to the owning package plus dedicated boundary tests. |
| `src/bioetl/interfaces/cli/commands/health.py` | Permanent public health command seam over the internal owner module `bioetl.interfaces.cli.commands.domains.health.command`. | `bioetl.interfaces.cli.commands.health` | `public-entrypoint` | `bioetl.interfaces.cli.commands` | `2026-03 RF-024` | `src`: use `bioetl.interfaces.cli.commands.health` as the public seam; direct internal-owner imports stay confined to `src/bioetl/interfaces/cli/commands/domains/health/__init__.py`; `tests`: patch/import coverage may target `bioetl.interfaces.cli.commands.health`, while direct `bioetl.interfaces.cli.commands.domains.health.command` imports stay confined to dedicated boundary coverage | `2026-09-30` | Use `bioetl.interfaces.cli.commands.health` for public CLI wiring and patch targets; do not import `bioetl.interfaces.cli.commands.domains.health.command` directly outside the owning package or dedicated boundary tests. | The top-level module remains the sanctioned public CLI patch/import seam, and direct internal-owner imports remain confined to the owning package plus dedicated boundary tests. |
| `src/bioetl/interfaces/cli/commands/diagnostics.py` | Permanent public diagnostics command seam over the internal owner module `bioetl.interfaces.cli.commands.domains.diagnostics.command`. | `bioetl.interfaces.cli.commands.diagnostics` | `public-entrypoint` | `bioetl.interfaces.cli.commands` | `2026-03 RF-024` | `src`: use `bioetl.interfaces.cli.commands.diagnostics` as the public seam; direct internal-owner imports stay confined to `src/bioetl/interfaces/cli/commands/domains/diagnostics/__init__.py`; `tests`: patch/import coverage may target `bioetl.interfaces.cli.commands.diagnostics`, while direct `bioetl.interfaces.cli.commands.domains.diagnostics.command` imports stay confined to dedicated boundary coverage | `2026-09-30` | Use `bioetl.interfaces.cli.commands.diagnostics` for public CLI wiring and patch targets; do not import `bioetl.interfaces.cli.commands.domains.diagnostics.command` directly outside the owning package or dedicated boundary tests. | The top-level module remains the sanctioned public CLI patch/import seam, and direct internal-owner imports remain confined to the owning package plus dedicated boundary tests. |
| `src/bioetl/interfaces/cli/commands/quarantine.py` | Permanent public quarantine command seam over the internal owner module `bioetl.interfaces.cli.commands.domains.quarantine.command`. | `bioetl.interfaces.cli.commands.quarantine` | `public-entrypoint` | `bioetl.interfaces.cli.commands` | `2026-03 RF-024` | `src`: use `bioetl.interfaces.cli.commands.quarantine` as the public seam; direct internal-owner imports stay confined to `src/bioetl/interfaces/cli/commands/domains/quarantine/__init__.py`; `tests`: patch/import coverage may target `bioetl.interfaces.cli.commands.quarantine`, while direct `bioetl.interfaces.cli.commands.domains.quarantine.command` imports stay confined to dedicated boundary coverage | `2026-09-30` | Use `bioetl.interfaces.cli.commands.quarantine` for public CLI wiring and patch targets; do not import `bioetl.interfaces.cli.commands.domains.quarantine.command` directly outside the owning package or dedicated boundary tests. | The top-level module remains the sanctioned public CLI patch/import seam, and direct internal-owner imports remain confined to the owning package plus dedicated boundary tests. |
| `src/bioetl/interfaces/cli/commands/maintenance.py` | Permanent public maintenance command seam over the internal owner module `bioetl.interfaces.cli.commands.domains.maintenance.command`. | `bioetl.interfaces.cli.commands.maintenance` | `public-entrypoint` | `bioetl.interfaces.cli.commands` | `2026-03 RF-024` | `src`: use `bioetl.interfaces.cli.commands.maintenance` as the public seam; direct internal-owner imports stay confined to `src/bioetl/interfaces/cli/commands/domains/maintenance/__init__.py`; `tests`: import coverage may target `bioetl.interfaces.cli.commands.maintenance`, while direct `bioetl.interfaces.cli.commands.domains.maintenance.command` imports stay confined to dedicated boundary coverage | `2026-09-30` | Use `bioetl.interfaces.cli.commands.maintenance` for public CLI wiring; do not import `bioetl.interfaces.cli.commands.domains.maintenance.command` directly outside the owning package or dedicated boundary tests. | The top-level module remains the sanctioned public CLI patch/import seam, and direct internal-owner imports remain confined to the owning package plus dedicated boundary tests. |
| `src/bioetl/composition/entrypoints.py` | Permanent public composition entrypoint that intentionally shields internal `_pipeline_execution`, `_resource_management`, and `_services` module paths. | `bioetl.composition.entrypoints` | `public-entrypoint` | `bioetl.composition` | `2026-03 entrypoint freeze` | `src`: only explicit execution-focused public symbols from `__all__` may be imported from `bioetl.composition.entrypoints`; removed service/resource compatibility symbols must stay absent from first-party source. `tests`: public entrypoint imports may appear in interface/composition boundary coverage, but direct internal-module patch targets stay confined to `tests/unit/composition/test_entrypoints.py`, `tests/unit/composition/test_resource_management.py`, and `tests/unit/composition/test_services_entrypoints.py` | `2026-09-30` | Use `bioetl.composition.entrypoints` as the sanctioned public seam; do not import `bioetl.composition._pipeline_execution`, `bioetl.composition._resource_management`, or `bioetl.composition._services` directly outside dedicated entrypoint-boundary coverage. | The public entrypoint remains sanctioned, removed service/resource symbol imports in first-party source stay at zero, internal implementation-module imports outside `composition/` stay at zero, and internal-module patch coverage remains confined to the dedicated entrypoint-boundary tests. |
| `src/bioetl/domain/composite/config.py` | Permanent public entrypoint for composite config models that shields split config internals. | `bioetl.domain.composite.config` | `public-entrypoint` | `bioetl.domain.composite` | `legacy-pre-2026-03` | `src`: canonical entrypoint usage allowed; internal split modules stay inside `src/bioetl/domain/composite/`; `tests`: direct split-internal coverage stays confined to `tests/unit/domain/composite/test_composite_config_facade.py` and `tests/unit/domain/composite/test_composite_config_edge_cases.py`, while ordinary tests keep importing the root config entrypoint | `2026-09-30` | Use `bioetl.domain.composite.config` as the sanctioned public seam; do not import split `config_*` internals outside the owning package or the dedicated composite-config coverage tests. | The root config entrypoint remains the sanctioned public path and direct imports of split config internals stay confined to the owning package plus the dedicated composite-config coverage tests. |
| `src/bioetl/domain/value_objects/activity_values.py` | Permanent public entrypoint for activity-related value objects that shields split concentration/type/pChEMBL modules. | `bioetl.domain.value_objects.activity_values` | `public-entrypoint` | `bioetl.domain.value_objects` | `legacy-pre-2026-03` | `src`: canonical entrypoint usage allowed; internal split modules stay inside `src/bioetl/domain/value_objects/`; `tests`: direct split-internal coverage stays confined to `tests/unit/domain/value_objects/test_value_object_facade_reexports.py`, while ordinary tests keep importing the public entrypoint | `2026-09-30` | Use `bioetl.domain.value_objects.activity_values` as the sanctioned public seam; do not import split value-object internals outside the owning package or the dedicated facade-coverage test. | The facade remains the sanctioned public path and direct imports of split activity-value internals stay confined to the owning package plus the dedicated facade-coverage test. |
| `src/bioetl/application/composite/merger.py` | Permanent public composite merge module that requires `MergeCollaboratorGroup` bundle; legacy per-collaborator keyword wiring removed in RF-009.2. | `bioetl.application.composite.merger` | `public-entrypoint` | `bioetl.application.composite` | `2026-03 merge collaborator migration` | `src`: all wiring passes `collaborators=MergeCollaboratorGroup(...)`; `tests`: `tests/unit/application/composite/test_merger.py`, `tests/unit/application/composite/merge_test_support.py`, `tests/unit/composition/bootstrap/runtime/test_composite_support_services_factory.py` | `2026-09-30` | Use `bioetl.application.composite.merger` as the sanctioned public seam with `collaborators=MergeCollaboratorGroup(...)`. | The merge module remains the sanctioned public seam and all composition paths use collaborator bundles with only the canonical `order_service` ordering collaborator. |

## Generated Snapshot

The measured compatibility snapshot is generated into
[`07-compatibility-facade-snapshot.md`](07-compatibility-facade-snapshot.md).

That companion file is the only place where measured tracked-module counts and
docstring-scan validation are rendered. Keep this document curated and
operational; do not copy generated snapshot counters back into it by hand.

## Usage Notes

- `deprecated-warn`, `compat-shim`, and `mixed-module` rows in the transition debt ledger
  count toward the zero-compatibility target for the current cycle and must only
  shrink unless the registry is explicitly reviewed first.
- Scorecard compatibility debt MUST stay synchronized with the transition ledger,
  not with the sanctioned public-entrypoint ledger.
- `mixed-module` rows require symbol-level migration, not whole-module deletion by default.
- `retained-entrypoint` and `public-entrypoint` rows live in the sanctioned public-entrypoint
  ledger and are not counted as transition compatibility debt for the current cycle.
- Top-level CLI command modules under `bioetl.interfaces.cli.commands` now count as sanctioned
  public entrypoints/support seams rather than compatibility-only shims; they are no longer
  tracked in the measured compatibility registry unless a module is explicitly marked as
  transition-only again.
- The importer census is the operational ratchet for sanctioned public/private twin families
  and for the retained `bioetl.infrastructure.config` package-root convenience facade.
  New first-party growth in those surfaces requires an explicit inventory update first.
- For provider adapters, first-party code should prefer provider package roots when those roots are
  the documented canonical path. Public entrypoint modules may live in `adapter.py` or `client.py`,
  but retired provider-specific `client.py` shims must not be treated as stable sanctioned seams.
- `retained-entrypoint` rows are reviewed public seams that still exist mainly to shield older
  implementation-module paths and have not yet been promoted to permanent public status.
- `public-entrypoint` rows are permanent sanctioned import and patch targets, even though their
  implementations remain partitioned behind internal owner modules.
- Measured-only modules are not sanctioned public import targets for first-party `src/`; they
  remain tracked only to prevent silent compatibility-surface drift while owners decide whether to
  retain, promote, or remove them.

## Measured-Only Policy

Measured-only modules are tracked by docstring-prefix measurement and the YAML allowlist, but they
are not curated ledger rows by default.

Current cycle status: the measured-only allowlist is empty, so any new measured-only module is an immediate ratchet regression until it is explicitly reviewed.

- A module may remain measured-only while it is still an unsanctioned compatibility helper and new
  first-party imports are not being added.
- Measured-only modules do not count as transition-debt rows and do not require the full curated
  ledger fields such as `canonical_target`, `allowed_call_sites`, or `exit_criteria`.
- A measured-only module must be promoted into the curated ledger before or when it becomes a
  sanctioned public seam that needs explicit canonical-target, call-site, or exit-criteria
  governance.
- Measured-only modules are not sanctioned public import targets. New first-party `src/` imports
  must point at the canonical package/module seam instead of the measured-only wrapper.
- The machine-readable policy for measured-only rows lives in
  `configs/quality/compatibility_facade_inventory.yaml` via `new_code_policy` and
  `promotion_trigger`; keep that contract aligned with tests and snapshot generation.

## Measured-Only Lifecycle Review

Measured-only review cadence is quarterly.

- Every quarterly review must re-run the measured-only import scan, docstring-tracking validation,
  owner tests, and compatibility snapshot generation before making a lifecycle decision.
- Allowed review outcomes are `retain`, `promote`, and `remove`.
- `retain` means the wrapper remains unsanctioned and measured-only for one more review cycle.
- `promote` means the wrapper becomes a sanctioned public seam with a curated ledger row and full
  governance fields.
- `remove` means the wrapper has no remaining justified compatibility role and can be deleted once
  targeted verification is green.
- Promotions into the curated ledger are required before a measured-only seam can be treated as a
  sanctioned public import path.

## Measured-Only Ratchet

Ratchet budgets are enforced through the YAML SSOT and architecture tests.

- The repo-level measured-only cap prevents silent growth of compatibility residue.
- Scoped caps keep `application/services` compatibility wrappers from regrowing after the lineage
  retirement wave.
- Raising a ratchet budget requires an explicit policy review, registry update, snapshot refresh,
  and issue-level justification.

## Historical Review Log

Historical retained-entrypoint decisions and review narratives now live in
[`history/compatibility-facade-review-history.md`](history/compatibility-facade-review-history.md).

Related docs:

- [Composition Layer](05-composition-layer.md)
- [Registry Pattern](../03-guides/registry-pattern.md)
