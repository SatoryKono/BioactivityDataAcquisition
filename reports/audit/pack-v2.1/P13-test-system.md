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
- `E2 STATIC`: `configs/quality/flaky_test_inventory.yaml` - Current inventory of flaky tests.
- `E3 EXECUTABLE`: `grep -rn "@pytest.mark.skip(" tests/` and `grep -rn "pytest.skip(" tests/` - Verifying skip reason governance.
- `E3 EXECUTABLE`: `uv run python -m scripts.engineering.qa.report_flaky_test_burndown_review --check` (Returns: `[flaky-test-burndown-review] artifact is current`)
- `E4 RUNTIME`: `reports/test-telemetry/coverage-summary.json` (Fresh, Refreshed 2026-11-06T17:54:37.543230+00:00).
- `E4 RUNTIME`: `reports/test-telemetry/slowest-tests.json` (Freshness linked to coverage-summary.json run).
- `E4 RUNTIME`: `reports/test-telemetry/s7-governance-hotspots.json` (Refreshed 2026-07-13T08:58:53.124004+00:00).

## D. Findings Register

### pack-v2.1/P13-TEST-001
- **finding_id**: `pack-v2.1/P13-TEST-001`
- **root_cause_id**: `flaky-test-burndown-tool-crash`
- **owner_prompt**: P13
- **concern**: Изначально предполагался сбой инструмента `report_flaky_test_burndown_review.py`. Однако анализ показал, что ошибка «Unsupported flaky_test_inventory schema_version» возникала из-за подачи в `--inventory` отчета о покрытии (`coverage-summary.json`), тогда как скрипт ожидает структуру `configs/quality/flaky_test_inventory.yaml`. С корректными входами инструмент работает штатно и сообщает «artifact is current».
- **severity**: P3
- **confidence**: high
- **status**: REJECTED
- **expected**: Скрипт корректно валидирует схему и отклоняет несовместимые входы с явной ошибкой.
- **actual**: Скрипт отклоняет несовместимые входы (выдает ошибку о несоответствии версии/схемы), а с корректным файлом `flaky_test_inventory.yaml` работает без ошибок.
- **evidence_ids**: E3 (вызов `uv run python -m scripts.engineering.qa.report_flaky_test_burndown_review --check`)
- **attempted_disproof**: Проверен вызов без аргументов-заменителей (`--check`), который успешно прочитал штатный inventory `configs/quality/flaky_test_inventory.yaml`.
- **exceptions_checked**: N/A
- **impact**: Никакого. Инструмент функционирует корректно при подаче ожидаемых аргументов.
- **root cause**: Некорректный ввод при ручном прогоне инструмента в рамках аудита. Инструментальной ошибки нет.
- **recommendation**: Нет (дефект не подтвердился).
- **scope**: `scripts/engineering/qa/report_flaky_test_burndown_review.py`
- **acceptance criteria**: Скрипт успешно выполняется с `--check` в штатном CI.
- **verification command**: `uv run python -m scripts.engineering.qa.report_flaky_test_burndown_review --check`

## E. Quantitative Scorecard
- **Coverage Enforcement**: 5 (Строгий контроль покрытия, фактический уровень 99.5%).
- **Deterministic Runs**: 5 (Механизмы встроены, flaky-инвентаризация функционирует штатно).
- **Test Organization**: 5 (Четкое разделение на unit/integration/architecture и repo-backed).

## F. Cross-cutting/root-cause clusters
- No systemic defects found. The test system shows high maturity.

## G. Prioritized roadmap P0→P3
- No immediate items.

## H. Verification Matrix
- All static checks performed against pinned SHA (8476a5afba6f86b453d91e81669b3a7bacd2c65c).
- Coverage limits validated: Actual 99.5% >= 85.0% Threshold.

## I. NOT_VERIFIABLE и missing evidence
- None.

## J. Self-check
- Revision matched.
- Read-only constraint respected.
- Contract constraints validated against evidence.
- False-positive rejected through correct usage of the tooling.

## K. Verdict
- Тестовая система обладает высоким уровнем зрелости (99.5% покрытие, строгая архитектурная проверка, функционирующая отчетность). Критических и системных дефектов не обнаружено.
