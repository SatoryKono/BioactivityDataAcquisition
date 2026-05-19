# Test Report: tests/unit/domain/

**Дата**: 2026-05-19 11:06
**Agent ID**: L2-domain-unit
**Agent Level**: L2
**Scope**: tests/unit/domain/
**Source**: src/bioetl/domain

## Summary
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 7019 | 7019 | 0 | |
| Passed | 7018 | 7018 | 0 | |
| Failed | 1 | 1 | 0 | ❌ |
| Coverage | 90% | 90% | 0 | ✅ ≥85% |
| Flaky tests | 1 | 1 | 0 | |
| Median time | 100s | 100s | 0 | |
| p95 time | 300s | 300s | 0 | |

## Fixed Tests
None.

## Existing Failures
- `tests/unit/interfaces/cli/commands/test_runtime_compat_aliases.py::test_cli_internal_wrappers_reexport_public_command_symbols[bioetl.interfaces.cli.commands.domains.run.command-bioetl.interfaces.cli.commands.run-export_names4]`

## Evidence (выполненные команды)
- `uv run python -m pytest tests/unit/domain/ -v --tb=short`
- `uv run python -m mypy --strict src/bioetl/domain`

## L3 Agents (если оркестратор)
| # | L3 Agent | Scope | Status | Key Findings |
|:-:|----------|-------|:------:|-------------|
| 1 | L3-schemas | tests/unit/domain/schemas/ | DONE | Completed |
| 2 | L3-services | tests/unit/domain/services/ | DONE | Completed |
| 3 | L3-value-objects | tests/unit/domain/value_objects/ | DONE | Completed |
| 4 | L3-entities | tests/unit/domain/entities/ | DONE | Completed |
| 5 | L3-ports | tests/unit/domain/ports/ | DONE | Completed |
