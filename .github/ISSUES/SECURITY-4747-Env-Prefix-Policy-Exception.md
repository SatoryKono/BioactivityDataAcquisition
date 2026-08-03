# Security hygiene: resolve legacy env-var prefix xfail

**Status**: completed_in_repo
**Priority**: P2 (Medium)
**Labels**: `security`, `testing`, `governance`
**GitHub Issue**: [#4747](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4747)
**Issue State**: closed
**Last synced**: 2026-05-30

## Problem

В `tests/security/test_security.py` существует легаси-исключение по префиксам переменных окружения.
Нужно либо убрать технический долг, либо явно зафиксировать исключение с явным сроком и scope.

## Execution Plan

1. Проанализировать все `os.getenv/os.environ.get` переменные через существующие
   security-скрипты.
2. Для каждый legacy переменной выбрать вариант:
   - убрать/переименовать в `BIOETL_*`
   - или зафиксировать явный documented waiver, если перенос невозможен.
3. Обновить `tests/security/test_security.py`:
   - убрать `xfail` при устранении legacy
   - или заменить на explicit, проверяемое exception/waiver с ограничением срока.
4. Прогнать:
   - `uv run python -m pytest tests/security/test_security.py -q`

## Suggested File Targets

- `tests/security/test_security.py`
- `docs/00-project/RULES.md`
- `docs/00-project/governance/03-file-policy.md`

## Acceptance

- `pytest tests/security/test_security.py` no longer contains undocumented `xfail`.
- Любое оставшееся исключение имеет explicit justification и owner.

## Completion Update (2026-05-30)

- `tests/security/test_security.py::TestNoHardcodedSecrets::test_env_vars_use_correct_prefix`
  passes on `src/bioetl/**` scan scope (no undocumented xfail on current main).
- Non-`BIOETL_` env usage in `src/tools/neo4j_audit.py` remains outside the
  production `src/bioetl` scan boundary and is governed as tooling-only surface.
