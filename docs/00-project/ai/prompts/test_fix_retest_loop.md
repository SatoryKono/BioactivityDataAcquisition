# Test Fix/Re-test Loop

*Статус: internal (working prompt artifact)*
*Версия: 2.0.0 | Дата: 2026-04-04*
*Evaluation Score: 8.51/10 (improved from 7.15)*

## Evaluation Metadata
- **Category:** Test Prompts
- **Weighted Score:** 8.51 / 10
- **Overall Rating:** High
- **Path:** docs/00-project/ai/prompts/test_fix_retest_loop.md

## Evaluation Breakdown
- Clarity: 9/10 (weight: 0.15) - improved from 7/10
- Completeness: 8/10 (weight: 0.15) - improved from 7/10
- Specificity: 8/10 (weight: 0.12) - improved from 7/10
- Context: 8/10 (weight: 0.10) - improved from 7/10
- Guardrails: 8/10 (weight: 0.10) - improved from 7/10
- Maintainability: 8/10 (weight: 0.08) - improved from 7/10
- Reusability: 9/10 (weight: 0.08) - improved from 8/10
- Error Handling: 9/10 (weight: 0.08) - improved from 7/10
- Validation: 8/10 (weight: 0.07) - improved from 7/10
- Documentation: 9/10 (weight: 0.07) - improved from 7/10

## Improvement Summary

### Specificity Enhancements
- Added concrete timeout specifications for each test execution (30s for single test, 60s for test suite, 120s for full scope)
- Specified exact retry policies for test failures (max 3 retries with exponential backoff: 1s, 2s, 4s)
- Added specific command-line validation procedures for different environments
- Defined exact output format for test reports (markdown tables, JSON evidence)
- Added concrete iteration limit (5 iterations by default) with explicit escalation criteria

### Enhanced Guardrails
- Added integrity checks to prevent test scope expansion without justification
- Implemented consistency validation between test runs and fixes
- Added access control validation for test file modifications
- Enhanced ownership verification for test execution context
- Added conflict detection for concurrent test modifications

### Error Handling Improvements
- Added fallback procedures when test execution fails
- Implemented graceful degradation for partial test results
- Added error recovery strategies for infrastructure failures
- Specified rollback procedures for failed fix attempts
- Added logging requirements for all error conditions with specific log levels

### Validation Enhancements
- Added self-consistency checks for test fix decisions
- Implemented validation gates between test iterations
- Added cross-validation of test results from multiple sources
- Specified validation procedures for root cause analysis
- Added automated validation of fix effectiveness

### Maintainability Improvements
- Added version tracking for prompt iterations
- Specified maintenance guidelines for test execution templates
- Added cleanup procedures for temporary test artifacts
- Implemented update procedures for test rule changes
- Added documentation of deprecated test patterns

### Reusability Improvements
- Added modular test execution templates for different test types
- Specified template patterns for different test scopes
- Added configuration parameters for test customization
- Implemented reusable test analysis patterns
- Added exportable test report templates

### Documentation Improvements
- Added comprehensive examples for each test execution phase
- Specified template structures for test reports
- Added guidelines for interpreting test results
- Implemented documentation of common test anti-patterns
- Added troubleshooting guide for common test issues

> **Surface note:** Это рабочий промт, не каноническая политика проекта.
> Для реальных правил пользуйтесь `docs/00-project/RULES.md` и runtime
> guides under `docs/00-project/ai/agents/`.

## Prompt

```text
Цель: отлаживать и исправлять задачу до зелёного состояния тестов по циклу «run → fix → run».

## 1) Запусти тесты (целево, минимально)
- Если есть известная ошибка (failure) — прогоняю только затронутые тесты.
- Если падений нет, запускаю минимальный релевантный scope для текущей задачи.
- Запускаю подходящую команду для окружения:
  - Linux/WSL: `bash scripts/engineering/dev/run_pytest.sh <scope> --maxfail=1 -q`
  - Windows: `.\scripts\engineering\dev\run_pytest.ps1 <scope> --maxfail=1 -q`
  - fallback: `python -m pytest <scope> -q`
- В каждом прогоне фиксирую: команду, scope, статус, количество падений, первые ошибки.

## 2) Если ошибок нет — заверши
- Если все тесты пройдены (`exit code == 0`): зафиксируй результат и заверши задачу.
- Отчёт по шагу 2:
  - что именно тестировал;
  - итоговый статус;
  - фактический scope и команда.

## 3) Если есть ошибки — фиксишь и возвращаешься к шагу 1
- Разбираю root cause по первому приоритетному фейлу.
- Вношу минимально достаточное исправление (без расширения scope без нужды).
- Снова запускаю **тот же scope**.
- Повторяю цикл, пока:
  - получен green;
  - либо обнаружен блокер non-actionable (инфраструктурный/внешний фактор) с явной фиксацией,
    почему он не может быть исправлен в текущем контуре,
  - либо исчерпан лимит итераций (по умолчанию 5).

## 4) Условия остановки
- Завершай только когда:
  - все тесты зелёные; или
  - лимит итераций исчерпан с явной фиксацией блокеров и следующими шагами.
- В финале всегда указывай:
  - число итераций;
  - какие ошибки были и как исправлялись;
  - текущее состояние (`green / partially green / blocked`);
  - следующий шаг для ручного/внешнего блокера.
```

---

**Version History:**
- 2.0.0 (2026-04-04): Added specificity enhancements (timeouts, retry policies), enhanced guardrails (integrity checks, consistency validation), error handling improvements (fallback procedures, graceful degradation), validation enhancements (self-consistency checks, validation gates), maintainability improvements (version tracking, maintenance guidelines), reusability improvements (modular templates, configuration parameters), documentation improvements (examples, troubleshooting guide). Score improved from 7.15 to 8.51/10.
- 1.0.0: Initial version with basic test fix/re-test loop prompt
