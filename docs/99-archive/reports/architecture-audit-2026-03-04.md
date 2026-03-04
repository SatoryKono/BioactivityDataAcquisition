# Architecture Audit Report

Date: 2026-03-04
Scope: `src/bioetl`, `tests/architecture`, `.importlinter`

## Executive Summary

- Total findings: 4
- Critical (P1 / MUST): 0
- Moderate (P2 / SHOULD): 3
- Informational (P3): 1
- Интегральный балл: **7.5 / 10** (зона «5.0–7.9», архитектура в целом устойчива, но с заметным техдолгом и зонами риска расширяемости).

## Методика и верификация

Аудит основан на:

1. статическом просмотре кода и архитектурных тестов;
1. запуске архитектурных тестов, mypy и ruff;
1. проверке целевых требований из RULES/AGENTS/CODEX-контекста.

Проверочные команды:

- `uv run python -m pytest tests/architecture/ -q`
- `uv run python -m mypy --strict src/bioetl`
- `uv run ruff check src/bioetl tests/architecture`
- `find src/bioetl -name '*.py' | xargs wc -l | sort -nr | head -n 20`
- `find tests -name 'test_*.py' | wc -l` (+ срез по unit/integration/e2e/architecture)

## Оценка по 10 категориям

| Категория                                 | Описание                                                                           |  Вес | Оценка (1–10) | Взвешенный балл |
| ----------------------------------------- | ---------------------------------------------------------------------------------- | ---: | ------------: | --------------: |
| 1) Слоистая архитектура                   | Соблюдение зависимостей `domain/application/infrastructure/composition/interfaces` | 0.15 |           8.0 |            1.20 |
| 2) Hexagonal (Ports & Adapters) и DDD     | Порты в домене, адаптеры в инфраструктуре, выразительность модели                  | 0.12 |           7.5 |            0.90 |
| 3) Границы модулей и import-дисциплина    | Явность контрактов и покрытие архитектурными правилами                             | 0.10 |           7.0 |            0.70 |
| 4) Модульность и связность                | Размеры модулей, SRP, отсутствие «god objects»                                     | 0.10 |           6.0 |            0.60 |
| 5) Качество доменной модели               | Чистота домена, инварианты, value objects, типы                                    | 0.10 |           8.0 |            0.80 |
| 6) Тестирование и quality gates           | Полнота тест-пирамиды, архитектурные и контрактные проверки                        | 0.12 |           8.5 |            1.02 |
| 7) Ошибки и отказоустойчивость            | Typed exceptions, DQ-пороги, circuit breaker, lock/heartbeat                       | 0.08 |           8.0 |            0.64 |
| 8) Логирование и наблюдаемость            | Структурные логи, трассировка, метрики, запрет anti-patterns                       | 0.08 |           8.0 |            0.64 |
| 9) Безопасность и секреты                 | PII hashing, конфигурация секретов, отсутствие hardcode                            | 0.07 |           7.5 |            0.53 |
| 10) Техдолг/сопровождаемость/документация | Линт-долг, ограничения на сложность/размер, актуальность правил                    | 0.08 |           6.0 |            0.48 |

**Итого:** `1.20 + 0.90 + 0.70 + 0.60 + 0.80 + 1.02 + 0.64 + 0.64 + 0.53 + 0.48 = 7.51 / 10`.

Интерпретация:

- 0–4.9: архитектура нестабильна;
- 5–7.9: архитектура рабочая, но есть системный долг;
- 8–10: зрелая и хорошо управляемая архитектура.

Текущее состояние проекта: **верхняя часть среднего диапазона (7.5)** — хороший фундамент (архтесты, mypy strict, слои), но есть признаки деградации maintainability (lint debt, крупные фабрики, частично «размытые» guardrails).

## Архитектурная оценка (по пунктам задачи)

### 1) Соблюдение слоистой структуры

- Позитив: действуют явные контракты импортов для всех слоёв и отдельные запреты на `application -> infrastructure`/`domain -> external I/O` в архитектурных тестах.
- Факт: архитектурный набор тестов проходит (`pytest tests/architecture`).

### 2) Следование Hexagonal и DDD

- Позитив: порты явно в `domain/ports`, проверяется их наличие и использование `Protocol`.
- Позитив: Silver слой реализован через Delta Lake API (не raw Parquet).
- Позитив: доменные политики для lock/circuit breaker/DQ оформлены как typed config/exceptions.

### 3) Явность границ модулей и зависимостей

- Позитив: `.importlinter` содержит контракты по слоям.
- Риск: часть правил может быть устаревшей (см. Finding P2-01), что снижает фактическое покрытие рисков.

### 4) Единообразие соглашений (naming/структура)

- Позитив: есть отдельные архитектурные тесты для naming conventions и structured logging patterns.
- Риск: линтер выявляет 26 нарушений в текущем состоянии (unused imports, B009 getattr const attr, сортировка `__all__`).

## Findings

## [P2] Finding P2-01: Устаревший target в import-linter снижает защищённость правил

**Location**: `.importlinter:61-64`, `src/bioetl/infrastructure/quarantine/unified.py:1`

**Rule**: Архитектурные guardrails должны быть актуальны (MUST по достоверности аудита и архитектурных контрактов).

**Evidence**:

```ini
# .importlinter
bioetl.infrastructure.quarantine.unified_quarantine
```

Но файл/модуль `unified_quarantine.py` отсутствует, фактический модуль — `unified.py`.

**Impact**: правило формально присутствует, но не защищает от импорта фактической реализации, что создаёт «ложное чувство безопасности».

**Recommendation**:

- заменить на `bioetl.infrastructure.quarantine.unified`;
- добавить тест на валидность путей в `.importlinter`.

**Verification command**: `test -f src/bioetl/infrastructure/quarantine/unified_quarantine.py; echo $?`

## [P2] Finding P2-02: Накопленный lint debt (26 нарушений ruff)

**Location**: `src/bioetl/application/composite/runner_stage_mixin.py:66-99`, `src/bioetl/composition/factories/pipeline_factory.py:14-55`, и др.

**Rule**: SHOULD поддерживать стабильные quality gates и чистоту кода.

**Evidence**:

- `B009` (constant `getattr`) в stage mixins;
- `F401` unused imports в `pipeline_factory.py` и др.;
- `RUF022` сортировка `__all__` в generated mapping.

**Impact**: ухудшение читаемости, снижение signal/noise для CI, рост стоимости ревью.

**Recommendation**:

- провести пакетное исправление (`ruff --fix`) + ручная проверка спорных мест;
- для намеренных отклонений зафиксировать explicit exemption с owner/expiry.

**Verification command**: `uv run ruff check src/bioetl tests/architecture`

## [P2] Finding P2-03: Высокий допустимый порог нарушений длины функций маскирует техдолг

**Location**: `tests/architecture/test_code_metrics.py:152-160`

**Rule**: SHOULD постепенно снижать budget техдолга, а не консервировать его.

**Evidence**:

```python
MAX_VIOLATIONS = 165
```

**Impact**: система допускает значительное количество oversized-функций, что снижает модульность и усложняет эволюцию.

**Recommendation**:

- запустить программу снижения лимита (например, 165 -> 140 -> 120 за 2-3 релиза);
- вводить per-layer budgets и burn-down график.

**Verification command**: `nl -ba tests/architecture/test_code_metrics.py | sed -n '145,205p'`

## [P3] Finding P3-01: Крупные composition-модули остаются потенциальными «god objects»

**Location**: `src/bioetl/composition/factories/pipeline_factory.py:1-789`

**Rule**: MAY улучшать SRP в composition для ускорения расширения провайдеров/пайплайнов.

**Evidence**:

- размер файла `789 LOC`;
- в модуле одновременно assembly, фабрики, DQ helper wiring, data-source wiring.

**Impact**: высокая когнитивная нагрузка, риск регрессий при изменении DI.

**Recommendation**:

- вынести runner assembly, DQ wiring и data-source creation в отдельные builder-модули с явными контрактами.

**Verification command**: `wc -l src/bioetl/composition/factories/pipeline_factory.py`

## Позитивные наблюдения

1. Архитектурный контур активно защищён большим набором архитектурных тестов (80 файлов в `tests/architecture`).
1. `mypy --strict` проходит на всём `src/bioetl` (606 модулей) — высокий уровень типовой дисциплины.
1. Silver writer использует `deltalake` и доменные исключения для schema/merge конфликтов.
1. Присутствуют доменные политики lock/circuit breaker/DQ, соответствующие целевым параметрам (TTL 90s, heartbeat 30s, failure_threshold 5, recovery_timeout 300s, DQ 5%/20%).

## Приоритизированный план рефакторинга

### Шаг 1 (Критичный): Нормализовать архитектурные guardrails

- **Цель**: убрать «слепые зоны» в import contracts.
- **Конкретные правки**:
  - обновить `.importlinter` target `...quarantine.unified_quarantine` -> `...quarantine.unified`;
  - добавить тест `tests/architecture/test_importlinter_targets_exist.py` для проверки существования module paths.
- **Риски**: ложнопозитивные падения при реорганизации модулей.
- **Минимизация**: allowlist deprecated aliases + migration window.
- **Критерии готово**:
  - `lint-imports` стабильно проходит;
  - новый тест на валидность target paths зелёный.

### Шаг 2 (Критичный): Закрыть lint debt до нуля или управляемого baseline

- **Цель**: восстановить доверие к статическим quality gates.
- **Конкретные правки**:
  - исправить `B009` (replace constant getattr with attribute access/protocol);
  - удалить `F401` imports;
  - унифицировать `__all__`/isort-порядок.
- **Риски**: случайное изменение поведения в рефлексивных местах.
- **Минимизация**: точечные unit tests на affected mixins/factories до и после замены.
- **Критерии готово**:
  - `uv run ruff check src/bioetl tests/architecture` без ошибок;
  - ключевые unit/architecture тесты зелёные.

### Шаг 3 (Высокий): Декомпозиция `pipeline_factory.py`

- **Цель**: снизить связность и размер composition entrypoint.
- **Конкретные правки**:
  - выделить `PipelineAssemblyBuilder`, `RunnerAssemblyBuilder`, `DQWiringBuilder`;
  - оставить в `pipeline_factory.py` только facade/API + thin orchestration.
- **Риски**: поломка DI-графа и порядка инициализации.
- **Минимизация**: golden tests на построение runner/services + snapshot зависимостей.
- **Критерии готово**:
  - модуль < 350 LOC;
  - no behavior diff по интеграционным тестам pipeline bootstrap.

### Шаг 4 (Высокий): Снизить budget техдолга по длине функций

- **Цель**: планомерный burn-down oversized функций.
- **Конкретные правки**:
  - ревизия top-20 длинных функций (extract method / strategy objects);
  - уменьшение `MAX_VIOLATIONS` в 2-3 итерации.
- **Риски**: churn и рост количества мелких сущностей.
- **Минимизация**: target только hot modules (composite runner, large adapters), code owners review.
- **Критерии готово**:
  - снижение `MAX_VIOLATIONS` минимум на 15–20% без роста исключений.

### Шаг 5 (Средний): Формализовать портовые интерфейсы для composite orchestration

- **Цель**: снизить утечки абстракций и зависимость от приватных методов mixin-цепочек.
- **Конкретные правки**:
  - вместо `getattr(..."_private")` — явный `Protocol`/ABC для stage-support контрактов;
  - типизировать зависимости через constructor injection.
- **Риски**: необходимость массовой правки нескольких mixins.
- **Минимизация**: временные adapter/shim классы + постепенная миграция.
- **Критерии готово**:
  - отсутствуют B009-паттерны;
  - stage helpers используют явные типовые контракты.

### Шаг 6 (Желательный): Усилить архитектурную наблюдаемость прогресса

- **Цель**: сделать деградации заметными раньше PR-review.
- **Конкретные правки**:
  - weekly trend-репорт по LOC/CC/ruff/mypy/arch-tests;
  - quality dashboard в CI-артефактах.
- **Риски**: «шумные» отчёты.
- **Минимизация**: пороги тревог, SLA только по трендам/регрессам.
- **Критерии готово**:
  - есть автоматический отчёт, привязанный к PR/ночному пайплайну;
  - регресс по метрикам блокирует merge только при выходе за budget.

## Метрики и тесты для предотвращения регресса

### Рекомендуемые дополнительные метрики

1. **Architecture Contract Coverage**: доля слоёв/зон, покрытых import-контрактами (цель > 95%).
1. **Lint Debt Index**: число ruff-ошибок на 1k LOC (цель < 0.2).
1. **Oversized Function Ratio**: доля функций > 50 строк (цель -30% за квартал).
1. **God-Module Index**: число модулей > 400 LOC вне allowlist (цель -50%).
1. **Type Strictness Health**: mypy strict pass-rate (цель 100%).
1. **Arch Test Stability**: % passed/skipped в `tests/architecture` (цель: снижение skip-доли).
1. **DQ Enforcement Reliability**: % прогонов с корректным soft/hard threshold поведением.

### Какие тесты добавить/обновить

- `tests/architecture/test_importlinter_targets_exist.py` (валидность module path в `.importlinter`).
- `tests/architecture/test_ruff_clean_gate.py` (опционально: smoke на zero critical lint).
- Расширить `test_code_metrics.py` трендовыми ассертами (снижение baseline, не только upper cap).
- Добавить regression tests для composite stage helpers после замены `getattr` на Protocol.

## Как метрики связать с интегральным баллом

Предлагаемая динамика после выполнения ключевых шагов:

- После Шагов 1–2: +0.6…+0.9 (рост категорий 3, 8, 10).
- После Шага 3: +0.4…+0.6 (рост категорий 4 и 10).
- После Шагов 4–5: +0.3…+0.5 (рост категорий 2, 4, 6, 10).

Ожидаемый целевой диапазон через 2–3 итерации: **8.4–8.9 / 10**.

## Verification Log (факт выполнения)

- `uv run python -m pytest tests/architecture/ -q` → PASS (есть ожидаемые skip по legacy/optional-кейсам).
- `uv run python -m mypy --strict src/bioetl` → PASS (`Success: no issues found in 606 source files`).
- `uv run ruff check src/bioetl tests/architecture` → FAIL (26 issues, фиксируем как текущий техдолг).
- `find src/bioetl -name '*.py' | xargs wc -l | sort -nr | head -n 20` → выполнено (идентифицированы самые крупные модули).
- `find tests -name 'test_*.py' | wc -l` (+разбивка) → выполнено (подтверждена широкая тестовая пирамида).
