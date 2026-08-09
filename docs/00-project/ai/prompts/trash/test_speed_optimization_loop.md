# Test Speed Optimization Loop

*Статус: internal (working prompt artifact)*

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
