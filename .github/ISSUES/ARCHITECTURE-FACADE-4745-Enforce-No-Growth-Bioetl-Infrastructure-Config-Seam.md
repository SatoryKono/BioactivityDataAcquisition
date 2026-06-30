# Enforce no-growth facade rule for `bioetl.infrastructure.config`

**Status**: completed_in_repo
**Priority**: P1 (High)
**Labels**: `architecture`, `tech-debt`, `compatibility`, `governance`
**GitHub Issue**: [#4745](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4745)
**Issue State**: closed
**Last synced**: 2026-05-29

## Problem

`bioetl.infrastructure.config` package-root convenience seam остаётся
санкционированным external-facing convenience surface, но на current `main`
first-party growth уже удерживается на нуле. Residual action для этого issue
сводился к синхронизации inventory metadata и regression checks с текущим
follow-up issue.

## Execution Plan

1. Снять baseline first-party imports с помощью существующего census.
2. Зафиксировать no-growth/targeted-reduction правила в:
   - `configs/quality/infrastructure_config_root_facade_inventory.yaml`
3. Прогнать governance test:
   - `tests/architecture/test_public_surface_importer_census_governance.py`
4. Проверить/обновить контрактные тесты фасадов:
   - `tests/unit/composition/runtime_builders/test_runner_builder_contracts.py`

## Suggested File Targets

- `configs/quality/infrastructure_config_root_facade_inventory.yaml`
- `tests/architecture/test_public_surface_importer_census_governance.py`
- `src/bioetl/infrastructure/config/__init__.py`
- `tests/unit/composition/runtime_builders/test_runner_builder_contracts.py`

## Acceptance

- Нет first-party `src/` importer growth для `Settings`, `get_settings`,
  `load_pipeline_contract_policy`.
- Inventory metadata и regression checks ссылаются на `#4745`, а не на
  исторический predecessor issue.
- Canonical owner targets и zero-growth budgets остаются неизменными.
