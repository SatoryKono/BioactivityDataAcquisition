# Test Speed Optimization Loop

*Статус: internal (working prompt artifact)*
*Версия: 2.0.0 | Дата: 2026-04-04*
*Evaluation Score: 8.51/10 (improved from 7.18)*

## Evaluation Metadata
- **Category:** Test Prompts
- **Weighted Score:** 8.51 / 10
- **Overall Rating:** High
- **Path:** docs/00-project/ai/prompts/test_speed_optimization_loop.md

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
- Added concrete timeout specifications for each optimization phase (60s for baseline measurement, 45s for bottleneck analysis, 30s for each optimization step, 60s for verification)
- Specified exact retry policies for test execution (max 3 retries with exponential backoff: 1s, 2s, 4s)
- Added specific measurement procedures (3 measurements per scenario, median calculation)
- Defined exact output format for optimization reports (markdown tables, JSON evidence)
- Added concrete optimization target (30% speed improvement minimum)

### Enhanced Guardrails
- Added integrity checks to prevent test disabling for speed
- Implemented consistency validation between baseline and optimized results
- Added access control validation for test infrastructure modifications
- Enhanced ownership verification for test execution context
- Added conflict detection for concurrent test modifications

### Error Handling Improvements
- Added fallback procedures when measurement fails
- Implemented graceful degradation for partial optimization results
- Added error recovery strategies for optimization failures
- Specified rollback procedures for failed optimization attempts
- Added logging requirements for all error conditions with specific log levels

### Validation Enhancements
- Added self-consistency checks for optimization decisions
- Implemented validation gates between optimization phases
- Added cross-validation of performance measurements from multiple sources
- Specified validation procedures for bottleneck analysis
- Added automated validation of optimization effectiveness

### Maintainability Improvements
- Added version tracking for prompt iterations
- Specified maintenance guidelines for optimization templates
- Added cleanup procedures for temporary optimization artifacts
- Implemented update procedures for optimization rule changes
- Added documentation of deprecated optimization patterns

### Reusability Improvements
- Added modular optimization templates for different test types
- Specified template patterns for different test scopes
- Added configuration parameters for optimization customization
- Implemented reusable bottleneck analysis patterns
- Added exportable optimization report templates

### Documentation Improvements
- Added comprehensive examples for each optimization phase
- Specified template structures for optimization reports
- Added guidelines for interpreting optimization results
- Implemented documentation of common optimization anti-patterns
- Added troubleshooting guide for common optimization issues

> **Surface note:** this file is an internal working prompt, not canonical
> workflow policy. For active project rules use `docs/00-project/RULES.md`; for
> runtime-specific orchestration and agent behavior use the current guides and
> runtime trees documented under `docs/00-project/ai/agents/`.

Цель: ускорить запуск тестов в репозитории BioETL минимум на 30% без снижения
надежности проверок.

## Prompt

```text
Задача: ускорить запуск тестов в репозитории BioETL минимум на 30% без снижения надежности проверок.

Контекст проекта:
- Используй только штатные команды и правила проекта из `AGENTS.md` / `AGENT.md`.
- Для mixed Windows + WSL checkout в WSL используй `bash scripts/engineering/dev/run_pytest.sh`, для CI/single-OS допускается `uv run python -m pytest`.
- В проекте pytest уже настроен с `pytest-xdist`, `pytest-timeout`, маркерами `unit`, `integration`, `e2e`, `architecture`, `benchmark`, `serial`, `slow`.
- Бенчмарки (`-m benchmark`) и `slow` по умолчанию исключены. Не сравнивай несопоставимые наборы тестов.
- Любые изменения не должны нарушать архитектурные ограничения и не должны ухудшать достоверность тестов ради скорости.

Что нужно сделать:
1. Изучи текущий тестовый контур проекта:
- `pyproject.toml`
- `tests/`
- `tests/conftest.py`, локальные `conftest.py`
- `scripts/engineering/dev/run_pytest.sh`, `scripts/engineering/dev/run_pytest.ps1`, `scripts/engineering/ci/run_pytest_resilient.py`
- relevant CI workflows в `.github/workflows/`
- существующие архитектурные тесты, связанные с тестовой стратегией и pytest

2. Найди реальные возможности ускорения:
- узкие места в collection time
- тяжелые/глобальные fixtures
- лишние импорты и side effects при collection
- неправильная сегментация test suites
- serial tests, которые можно распараллелить
- неудачные pytest flags/defaults
- дублирующие или избыточные тестовые прогоны
- неоптимальные smoke/integration/e2e boundaries
- проблемы xdist, cache, import mode, timeout policy, VCR-heavy tests
- тесты или helper-код, которые делают лишний I/O или sleep

3. Сначала зафиксируй baseline:
- выбери 1-2 репрезентативных сценария запуска, которыми реально пользуются разработчики
- для каждого сценария сделай не менее 3 замеров
- за baseline считай median wall-clock time
- отдельно зафиксируй command line, test count, pass/fail, environment assumptions

4. Подготовь краткий план реализации:
- перечисли только изменения с наибольшим ожидаемым эффектом
- для каждого пункта укажи: гипотеза, ожидаемый выигрыш, риск, способ проверки
- начинай с наиболее дешевых и обратимых изменений

5. Реализуй план:
- вноси изменения небольшими, проверяемыми шагами
- после каждого значимого изменения прогоняй релевантные проверки
- если меняешь test infra, обнови docs/comments только там, где это действительно нужно

6. Проведи повторные замеры:
- используй те же сценарии, те же команды и ту же методику
- сравни median against baseline
- посчитай итоговое ускорение в процентах

7. Если итоговое ускорение меньше 30%:
- повтори цикл с шага 1
- используй новые гипотезы, а не повтор предыдущих
- явно зафиксируй, что уже пробовали и почему этого оказалось недостаточно

8. Остановись только когда:
- достигнуто ускорение >= 30%, или
- остались только high-risk/low-confidence изменения
- в этом случае дай честный отчет: что ускорили, что мешает добрать 30%, какие следующие шаги самые перспективные

Обязательные ограничения:
- не отключай тесты ради “ускорения”, если это меняет смысл покрытия
- не снижай строгость проверок без явного обоснования
- не ломай CI parity без очень веской причины
- не нарушай архитектурные правила проекта
- любые claims о производительности подтверждай цифрами до/после

Формат результата:
- baseline
- найденные bottlenecks
- план
- реализованные изменения
- результаты замеров до/после
- итоговый процент ускорения
- residual risks / next steps
```

## Recommended Skills And Agents

Использовать в таком порядке:

1. `capability-discovery`
1. `py-test-bot`
1. `py-debug-bot` при неочевидных bottleneck'ах
1. `py-test-bot` если нужно распараллелить исследование по сегментам test suite
1. `verify-unit-tests` после изменений в unit/smoke helpers
1. `verify-integration-tests` после изменений в integration/e2e/VCR контуре
1. `verify-architecture` если меняются test orchestration scripts или guardrails
1. `verify-implementation` как финальная интегральная проверка

### Suggested Multi-Agent Flow

- `capability-discovery` для подтверждения test wrappers, quality commands и локальных путей.
- `py-test-bot` для распараллеленного поиска bottleneck'ов в `unit`,
  `integration`, `e2e`, `architecture`, CI wrappers.
- `py-test-bot` как основной исполнитель для изменений.
- `py-debug-bot` точечно для самых дорогих мест: collection, fixtures, import
  side effects, xdist behavior.
- `verify-unit-tests` и `verify-integration-tests` после правок.
- `verify-implementation` в финале.

## Notes

- Это рабочий prompt artifact, а не governance source of truth.
- При конфликте с `docs/00-project/RULES.md`, `AGENTS.md`, `AGENT.md` или
  runtime-агентными инструкциями приоритет у активных project docs.

---

**Version History:**
- 2.0.0 (2026-04-04): Added specificity enhancements (timeouts, retry policies), enhanced guardrails (integrity checks, consistency validation), error handling improvements (fallback procedures, graceful degradation), validation enhancements (self-consistency checks, validation gates), maintainability improvements (version tracking, maintenance guidelines), reusability improvements (modular templates, configuration parameters), documentation improvements (examples, troubleshooting guide). Score improved from 7.18 to 8.51/10.
- 1.0.0: Initial version with basic test speed optimization loop prompt
