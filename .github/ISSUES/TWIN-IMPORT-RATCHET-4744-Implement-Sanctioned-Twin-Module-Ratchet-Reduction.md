# Sanctioned twin-module import ratchet reduction

**Status**: completed_in_repo
**Priority**: P1 (High)
**Labels**: `architecture`, `tech-debt`, `compatibility`, `governance`
**GitHub Issue**: [#4744](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4744)
**Issue State**: open
**Last synced**: 2026-05-29

## Problem

Residual twin-module split-import families required live revalidation after the
2026-05-19 tech-debt audit. Current `main` already contains the main caller
migration for the ChEMBL policy registry family; the remaining task was to sync
the sanctioned ratchet metadata with the reduced import graph and refresh the
committed census.

## Execution Plan

1. Регенерировать baseline импорта и подтвердить метрики в:
   - `scripts/engineering/qa/report_compatibility_importer_census.py`
2. Обновить и синхронизировать caps/owner metadata по residual twin-family в:
   - `configs/quality/compatibility_twin_module_ratchet.yaml`
3. Добавить/обновить governance-тест:
   - `tests/architecture/test_compatibility_importer_census_governance.py`
4. Зафиксировать owner-only reduction plan для каждой residual family и прогнать повторную сверку.

## Suggested File Targets

- `configs/quality/compatibility_twin_module_ratchet.yaml`
- `scripts/engineering/qa/report_compatibility_importer_census.py`
- `tests/architecture/test_compatibility_importer_census_governance.py`
- `docs/02-architecture/07-compatibility-facade-snapshot.md`

## Acceptance

- Live census зафиксирован в committed report artifacts и совпадает с
  `compatibility_twin_module_ratchet.yaml`.
- `domain.normalization.profiles.chembl_policy_registry` tightened до
  `11 public / 1 private`, `composition.runtime_builders.run_manifest_support`
  tightened до `12 public / 0 private`.
- Governance metadata и regression checks ссылаются на `#4744`, а не на
  исторический predecessor issue.
