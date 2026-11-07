# P13. Тестовая система, coverage, flaky и governance debt

## A. Audit Manifest
- **Audit ID**: pack-v2.1/P13
- **Pinned Revision**: 8476a5afba6f86b453d91e81669b3a7bacd2c65c (main)
- **Worktree State**: Clean
- **Execution Date**: 2026-11-06T17:54:37Z
- **Scope**: tests/**, pytest/tool config, CI test lanes, quality reports
- **Environment**: Linux (sandbox), Python 3.12, uv
- **Permissions**: READ_ONLY, WRITE_AUTHORIZED=YES (for Issues only)

## B. Scope/ownership и exclusions
- **Audited**:
  - Unit/integration/contract tests (pytest configuration)
  - Test governance artifacts and CI configurations
  - Generated reports in `reports/test-telemetry` (coverage-summary.json, slowest-tests.json)
- **Excluded**:
  - Direct modifications to code, configuration, or CI workflows.

## C. Evidence Ledger
- `E1 NORMATIVE`: `configs/quality/test_matrix.yaml` - Test matrix definition and fixture governance logic.
- `E2 STATIC`: `configs/quality/test_governance_audit.yaml` - Definition of the protected testing surfaces.
- `E3 EXECUTABLE`: `grep -rn "@pytest.mark.skip(" tests/` and `grep -rn "pytest.skip(" tests/` - Verifying skip reason governance.
- `E4 RUNTIME`: `reports/test-telemetry/coverage-summary.json` (Fresh, Refreshed 2026-11-06T17:54:37.543230+00:00).
- `E4 RUNTIME`: `reports/test-telemetry/slowest-tests.json` (Freshness linked to coverage-summary.json run).
- `E4 RUNTIME`: `reports/test-telemetry/s7-governance-hotspots.json` (Refreshed 2026-07-13T08:58:53.124004+00:00).

## D. Findings Register

### pack-v2.1/P13-TEST-001
- **finding_id**: `pack-v2.1/P13-TEST-001`
- **root_cause_id**: `flaky-test-burndown-tool-crash`
- **owner_prompt**: P13
- **concern**: Инструмент `report_flaky_test_burndown_review.py` завершается с ошибкой `Expecting value: line 1 column 1 (char 0)` при парсинге входных файлов.
- **severity**: P2
- **confidence**: high
- **status**: CONFIRMED
- **expected**: Инструмент должен корректно парсить входные файлы и генерировать отчет о нестабильных тестах (`flaky_report.json`).
- **actual**: Скрипт падает на этапе парсинга из-за попытки прочитать пустой или невалидный JSON файл, либо из-за несоответствия `schema_version`.
- **evidence_ids**: E3 (вызов скрипта с параметрами `report_test_governance_audit` и `test_governance_current.json`).
- **attempted_disproof**: Попытка запустить `report_test_governance_audit.py --json-out` создала некорректный или несовместимый файл, который вызвал сбой `report_flaky_test_burndown_review.py`.
- **exceptions_checked**: Исключений для сбоя аналитических скриптов в CI пайплайне нет.
- **impact**: Невозможность автоматического отслеживания и управления flaky-тестами.
- **root cause**: Сбой при сериализации/десериализации данных инвентаризации (вероятно, `test_governance_current.json` ожидается в другом формате).
- **recommendation**: Обновить логику парсинга в `report_flaky_test_burndown_review.py` для обработки ошибок формата или исправить генерацию `test_governance.json`.
- **scope**: `scripts/engineering/qa/report_flaky_test_burndown_review.py`
- **acceptance criteria**: Скрипт успешно выполняется и генерирует валидный JSON-отчет при подаче существующих артефактов телеметрии.
- **verification command**: `uv run python -m scripts.engineering.qa.report_flaky_test_burndown_review --repo-root . --inventory reports/test-telemetry/coverage-summary.json --test-governance <file.json> --json-out flaky_report.json`

## E. Quantitative Scorecard
- **Coverage Enforcement**: 5 (Строгий контроль покрытия, фактический уровень 99.5%).
- **Deterministic Runs**: 4 (Механизмы встроены, но flaky analysis tool не функционирует штатно).
- **Test Organization**: 5 (Четкое разделение на unit/integration/architecture и repo-backed).

## F. Cross-cutting/root-cause clusters
- Tooling instability: Внутренние скрипты QA требуют улучшенной обработки ошибок входных данных и строгой проверки схем `schema_version`.

## G. Prioritized roadmap P0→P3
1. [P2] Fix `report_flaky_test_burndown_review.py` crash on invalid or unversioned JSON inputs.

## H. Verification Matrix
- All static checks performed against pinned SHA (8476a5afba6f86b453d91e81669b3a7bacd2c65c).
- Coverage limits validated: Actual 99.5% >= 85.0% Threshold.

## I. NOT_VERIFIABLE и missing evidence
- Flaky tests inventory details (due to tool crash).
- Duplicate test names (require successful execution of `report_test_governance_audit.py`).

## J. Self-check
- Revision matched.
- Read-only constraint respected.
- Contract constraints validated against evidence.

## K. Verdict
- Тестовая система обладает высоким уровнем зрелости (99.5% покрытие, строгая архитектурная проверка). Однако, инструменты анализа тестового долга (flaky) содержат критические ошибки парсинга, блокирующие генерацию отчетов.

## Issue drafts

| root_cause_id | finding_id | created Issue URL |
| :--- | :--- | :--- |
| flaky-test-burndown-tool-crash | pack-v2.1/P13-TEST-001 | draft (причина: отсутствие gh cli) |

### Draft: flaky-test-burndown-tool-crash
**Title**: Fix flaky test burndown tool crash on invalid JSON / schema parsing
**Labels**: bug, quality-debt, tooling
**Priority**: P2

**Problem:**
Скрипт `report_flaky_test_burndown_review.py` завершается с ошибкой парсинга (`Expecting value: line 1 column 1 (char 0)` или `Unsupported flaky_test_inventory schema_version`) при попытке обработать файлы инвентаризации и телеметрии.

**Evidence:**
Отчет аудита P13: `reports/audit/pack-v2.1/P13-test-system.md`
Вывод команды `uv run python -m scripts.engineering.qa.report_flaky_test_burndown_review ...` (ошибка).

**Expected vs actual:**
- *Expected*: Успешная генерация отчета `flaky_report.json`.
- *Actual*: Исключение ValueError при парсинге JSON или SchemaError.

**Impact:**
Блокирует процессы анализа стабильности тестов (flaky test analysis) в CI/QA пайплайнах.

**Scope / non-goals:**
- *Scope*: `scripts/engineering/qa/report_flaky_test_burndown_review.py`
- *Non-goals*: Исправление самих flaky-тестов.

**Architecture constraints:**
Инструменты QA не должны зависеть от скрытого состояния; они должны поддерживать валидацию входной схемы (Pydantic или jsonschema).

**Implementation outline:**
1. Добавить блок try-except в функцию загрузки JSON в `report_flaky_test_burndown_review.py`.
2. Добавить поддержку дефолтной схемы `schema_version = 1`, если она отсутствует во входном файле.

**Acceptance criteria:**
- Скрипт не падает при получении файлов без явного `schema_version`.
- Сообщения об ошибках парсинга содержат информативный текст (какой файл, какая строка).

**Verification commands/tests:**
`uv run python -m scripts.engineering.qa.report_flaky_test_burndown_review --repo-root . --inventory reports/test-telemetry/coverage-summary.json --test-governance <file.json> --json-out flaky_report.json`

**Dependencies:** None
**Rollback/risk:** Низкий риск (скрипт аналитический).
