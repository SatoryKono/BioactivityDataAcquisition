# Enforce no-growth facade rule for `bioetl.infrastructure.config`

**Status**: active
**Priority**: P1 (High)
**Labels**: `architecture`, `tech-debt`, `compatibility`, `governance`
**GitHub Issue**: [#4745](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4745)
**Issue State**: open
**Last synced**: 2026-05-29

## Problem

`bioetl.infrastructure.config` package-root convenience seam остаётся критичным архитектурным узлом.
Ключевая защита — не допускать growth first-party imports по пути через root-модуль без контролируемой миграции.

## Execution Plan

1. Снять baseline first-party imports с помощью существующего census.
2. Зафиксировать no-growth/targeted-reduction правила в:
   - `configs/quality/infrastructure_config_root_facade_inventory.yaml`
3. Прогнать governance test:
   - `tests/architecture/test_compatibility_importer_census_governance.py`
4. Проверить/обновить контрактные тесты фасадов:
   - `tests/unit/composition/runtime_builders/test_runner_builder_contracts.py`

## Suggested File Targets

- `configs/quality/infrastructure_config_root_facade_inventory.yaml`
- `tests/architecture/test_compatibility_importer_census_governance.py`
- `src/bioetl/infrastructure/config/__init__.py`
- `tests/unit/composition/runtime_builders/test_runner_builder_contracts.py`

## Acceptance

- Нет unreviewed роста first-party import usage через `bioetl.infrastructure.config`.
- Правила growth/reduction в тестах подтверждены и непротиворечат текущему canonical seam.
