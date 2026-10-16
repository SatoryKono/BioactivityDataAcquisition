# Tech Debt Audit 2026-05-19 Issue Pack

## Scope

This pack maps the 2026-05-19 technical-debt audit to the current `main`
state and selects only follow-up issues that remain actionable today.

## Current Assessment

The original audit is directionally useful, but several high-severity claims are
already resolved on the current tree:

- `configs/contracts/chembl/activity.yaml` no longer contains the `truebc` typo.
- `src/bioetl/interfaces/cli/commands/domains/health/command.py` is now a thin
  wrapper and no longer imports infrastructure config directly.
- `src/bioetl/composition/bootstrap/assembly/storage.py` no longer synthesizes
  runtime identity or wall-clock timestamps internally.
- `configs/base/bronze_fixture_gaps.yaml` is empty.
- `configs/base/contract_registry.yaml` currently covers all active
  `configs/entities/*` surfaces.
- Gold strictness is enforced in
  `src/bioetl/infrastructure/storage/gold/validation_mixin.py`.

## Publish-Ready Follow-Up Issues

### 1. Sanctioned Twin-Module Ratchet

Create a follow-up issue for sanctioned public/private twin families that still
attract split first-party imports even after the earlier compatibility cleanup
waves.

Current evidence:

- `reports/quality/compatibility-importer-census.md`
- `docs/02-architecture/07-compatibility-facade-snapshot.md`
- `docs/reports/evidence/technical-debt/SUMMARY.md`

Examples from the live census:

- `bioetl.application.core.span_helpers`: `1` public vs `7` private src imports
- `bioetl.composition.runtime_builders.run_manifest_support`: `3` public vs `9`
  private src imports
- `bioetl.domain.normalization.profiles.chembl_policy_registry`: `1` public vs
  `11` private src imports

Related closed work:

- `#4211` Build repo-wide importer census for sanctioned public seams and
  compatibility twins
- `#4191` Collapse unsanctioned compatibility facades and underscore/public twin
  modules

Why a new issue is still justified:

- the census exists, but residual twin families remain live on `main`
- current compatibility inventory tracks sanctioned entrypoints, not the
  remaining split-import ratchet for twin families

### 2. Config Convenience-Seam Re-Review

Create a follow-up issue for the retained `bioetl.infrastructure.config`
package-root facade and its convenience loader/API exports.

Current evidence:

- `src/bioetl/infrastructure/config/__init__.py`
- `src/bioetl/infrastructure/config/pipeline_config_loader.py`
- `docs/reports/evidence/pipeline-config-loader-ownership/04-decisions/SUMMARY.md`
- `docs/reports/evidence/pipeline-config-loader-ownership/03-synthesis/SYN-pipeline-config-loader-ownership.md`
- `docs/reports/evidence/technical-debt/SUMMARY.md`

Current posture:

- canonical ownership already lives in `pipeline_config_api.py` and
  `domain_config_resolver.py`
- `PipelineConfigLoader` is explicitly retained only as a convenience seam
- the package root still re-exports and lazily exposes broad config APIs

Why a new issue is still justified:

- current evidence says "retain and thin", but does not yet enforce a
  zero-growth rule for first-party use of the broad package-root facade
- this is a residual ownership/watchlist topic, not a request to delete the
  seam immediately

## Do Not Create New Issues For These Audit Claims

- CLI health direct infra import: stale on current `main`
- synthetic storage bootstrap context: stale on current `main`
- contract registry coverage gap: not reproduced on current `main`
- active Bronze fixture gap backlog: not reproduced on current `main`
- Gold strict validation gap for composite outputs: not reproduced on current
  `main`
