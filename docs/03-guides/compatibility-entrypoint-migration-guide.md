______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-09-18'

______________________________________________________________________

# Compatibility Entrypoint Migration Guide

This guide is the migration companion for the 12 retained public entrypoints
governed by `configs/quality/compatibility_facade_inventory.yaml`
(`compatibility_contract_policy`, linked issue `#10536`).

## Deprecation-Window Policy

- Silent removal stays forbidden for every retained entrypoint.
- Any future deprecation of a retained entrypoint requires a **90-day
  deprecation window**: the seam keeps working while emitting
  `DeprecationWarning`, and removal happens only after the window closes.
- Removal additionally requires importer-census proof (no unresolved
  first-party importers outside approved boundary coverage) and an update to
  this guide describing the replacement path.
- Retained entrypoints are re-reviewed quarterly; the window length and this
  guide pointer are restated per entry in its `compatibility_contract`.

## Entrypoint Lanes

| Lane | Entrypoint | Canonical target | If it ever deprecates, do this |
| ---- | ---------- | ---------------- | ------------------------------ |
| CLI | `src/bioetl/interfaces/cli/commands/run.py` | `bioetl.interfaces.cli.commands.run` | Keep public CLI wiring on the top-level module; never reintroduce the retired `domains/run/` wrapper. |
| CLI | `src/bioetl/interfaces/cli/commands/run_all.py` | `bioetl.interfaces.cli.commands.run_all` | Keep public CLI wiring on the top-level module; never reintroduce the retired `domains/run_all/` wrapper. |
| CLI | `src/bioetl/interfaces/cli/commands/run_composite.py` | `bioetl.interfaces.cli.commands.run_composite` | Route through the reviewed `domains/composite/` owner package, not around it. |
| CLI | `src/bioetl/interfaces/cli/commands/health.py` | `bioetl.interfaces.cli.commands.health` | Route through the owning `domains/health/` package, not its internal `command` module. |
| CLI | `src/bioetl/interfaces/cli/commands/diagnostics.py` | `bioetl.interfaces.cli.commands.diagnostics` | Route through the owning `domains/diagnostics/` package, not its internal `command` module. |
| CLI | `src/bioetl/interfaces/cli/commands/quarantine.py` | `bioetl.interfaces.cli.commands.quarantine` | Route through the owning `domains/quarantine/` package, not its internal `command` module. |
| Composition | `src/bioetl/composition/entrypoints.py` | `bioetl.composition.entrypoints` | Import only explicit execution-focused `__all__` symbols; never reach into `_pipeline_execution`, `_resource_management`, or `_services`. |
| Composition | `src/bioetl/composition/health_api.py` | `bioetl.composition.health_api` | External consumers stay on the facade; first-party runtime callers use `bioetl.composition.health_service_access`. |
| Composition | `src/bioetl/composition/maintenance_api.py` | `bioetl.composition.maintenance_api` | External consumers stay on the facade; first-party runtime callers use the reviewed owner seam via `bioetl.composition.entrypoints`. |
| Config | `src/bioetl/infrastructure/config/__init__.py` | `bioetl.infrastructure.config` | External convenience imports stay; first-party runtime code uses concrete owner config modules. |
| Domain | `src/bioetl/domain/composite/config.py` | `bioetl.domain.composite.config` | Import the root config entrypoint; never import split `config_*` internals outside the owning package. |
| Application | `src/bioetl/application/composite/merger.py` | `bioetl.application.composite.merger` | External callers stay on the seam; first-party wiring uses `MergeService` plus the `MergeCollaboratorGroup` bundle. |

## Related Docs

- [Compatibility Facade Inventory](../02-architecture/07-compatibility-facade-inventory.md)
- [CLI Reference](../04-reference/cli.md)
