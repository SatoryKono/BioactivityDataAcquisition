# Sanctioned twin-module import ratchet reduction

**Status**: active
**Priority**: P1 (High)
**Labels**: `architecture`, `tech-debt`, `compatibility`, `governance`
**GitHub Issue**: [#4744](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4744)
**Issue State**: open
**Last synced**: 2026-05-29

## Problem

Residual twin-module split-import families still show measurable first-party private imports.
Without active remediation, compatibility-facing package topology can drift toward additional, uncontrolled seams.

## Execution Plan

1. Регенерировать baseline импорта и подтвердить метрики в:
   - `scripts/engineering/qa/report_compatibility_importer_census.py`
2. Обновить и синхронизировать caps/owner-owners по residual twin-family в:
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

- Имеется evidence-based target reduction plan и no-growth boundary for residual families.
- Результат census-репорта согласован с governance тестами.
