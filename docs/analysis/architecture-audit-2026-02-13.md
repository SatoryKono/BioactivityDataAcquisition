# Architecture Audit Report — BioETL

Date: 2026-02-13
Scope: `src/bioetl/**`, `docs/00-project/RULES.md`, `docs/00-project/agents/AGENT.md`

## Входные документы

- Прочитаны: `docs/00-project/agents/AGENT.md`, `docs/00-project/RULES.md`.
- Запрошенные документы `01-domain-objects.md`, `02-etl-layers.md`, `03-data-flow.md`, `04-duplication-reduction.md`, `05-physical-layout.md` в `docs/00-project/` не обнаружены. Статус: **[данные отсутствуют]**.

## Часть 1. Объективные метрики

| Метрика | Команда/метод | Значение |
| --- | --- | ---: |
| Покрытие тестами | `pytest --cov=src/bioetl --cov-report=term` | 89.54%* |
| Ошибки mypy | `mypy src/bioetl --strict` + подсчёт `error:` | 39 |
| Циклические импорты | `python -c "from bioetl.domain import *"` | pass |
| Количество классов | `rg '^class ' src/ -g '*.py'` + `wc -l` | 884 |
| Количество файлов .py | `find src/ -name '*.py'` + `wc -l` | 533 |
| Средний размер модуля | `Path('src/bioetl').rglob('*.py')` + подсчёт строк | 222.38 |
| TODO/FIXME в коде | `rg -e '(TODO|FIXME|XXX|HACK)' src/` + `wc -l` | 23 |
| Использование print() | `rg 'print\(' src/bioetl -g '*.py'` + `wc -l` | 0 |
| Hardcoded secrets | `rg -e '(api_key|password|secret)\s*=' src/` + `wc -l` | 14** |

\* Значение взято из `coverage.json` (полный запуск указанной команды в текущей среде прерывался по времени из-за очень большого набора тестов).

\** Совпадения в основном относятся к присваиванию переменных `api_key`, а не к строковым литералам секретов.

## Часть 2. Оценка по 10 категориям

### 1) Соблюдение слоистой архитектуры — **10/10**

- Проверки импортов не выявили запретных зависимостей (`domain -> application/infrastructure`, `application -> interfaces`).
- Границы подтверждаются архитектурными тестами (`tests/architecture/test_layer_dependencies.py`, `test_forbidden_imports.py`).
- Нарушений MUST-правил по слоям не зафиксировано.

### 2) Контракты и Ports — **9/10**

- Пакет `domain/ports` централизует Protocol-контракты и фасад экспортов.
- Реализации в infrastructure явно опираются на порты (пример: `MemoryLock(LockPort)`).
- Минорный риск: часть инфраструктурных валидаторов допускает no-op режим (см. кат. 6).

### 3) Medallion Architecture — **9/10**

- Bronze: JSONL+zstd и path policy реализованы (`BronzeWriter`).
- Silver: Delta Lake через `write_deltalake`, merge/upsert, retention/VACUUM политика отражена в коде/комментариях.
- Gold слой и отдельный writer присутствуют; строгая проверка зависит от переданного валидатора/strict режима.

### 4) Обработка ошибок и Circuit Breaker — **9/10**

- Есть классификатор ошибок (critical/recoverable/data quality).
- Circuit breaker реализует CLOSED/OPEN/HALF_OPEN, threshold=5, recovery timeout, метрики state/trips.
- Реализация соответствует ADR-подобной схеме с probe-запросом в half-open.

### 5) Блокировки и конкурентность — **9/10**

- Для Local-Only используется `MemoryLock` (соответствует ADR-010): TTL, heartbeat, validate_owner.
- Safety Guard реализован на уровне application (`LockManager`, `BatchWriter` lock validation).
- Fencing-токеном фактически выступает `owner_id/run_id`.

### 6) Валидация и DQ — **8/10**

- Pandera-валидация реализована для Silver/Gold, есть Quarantine manager и hard/soft thresholds.
- Контент-хэш реализован через domain service с нормализацией.
- Замечание: по умолчанию `strict=False` и `NoOpValidator` допускает обход схемной валидации — это снижает гарантию «strict validation для всех сущностей».

### 7) Логирование и наблюдаемость — **9/10**

- `print()` в production-коде не найден.
- Unified observability stack присутствует (UnifiedLogger + Prometheus метрики, в т.ч. VACUUM и DQ).
- В коде активно прокидывается `run_id` в сервисы/раннеры.

### 8) Тестирование — **7/10**

- Покрытие по артефакту высокое (89.54%).
- Набор архитектурных, контрактных, e2e-тестов очень широкий.
- Но при запуске общего `pytest tests/ ...` фиксируются падения проверок форматирования (`test_code_formatting.py`), а полный прогон в среде долгий.

### 9) Безопасность и секреты — **8/10**

- Явных hardcoded secret literals по быстрым grep-проверкам не обнаружено.
- Использование `api_key` в адаптерах/композиции в основном через конфиг/DI.
- Рекомендуется добавить точечный детектор «литерал-секрет» в CI, чтобы исключить ложноположительные совпадения.

### 10) Документация и сопровождаемость — **8/10**

- RULES/ADR-контур обширный, архитектурные тесты синхронизации документации присутствуют.
- По этой задаче часть запрошенных проектных документов не найдена в ожидаемом месте.
- Докстринги в ключевых слоях присутствуют, но оценка снижена из-за отсутствующих артефактов контекста.

## Evidence (file:line)

- Layer boundaries: `src/bioetl/domain/ports/__init__.py:1-21`, `tests/architecture/test_layer_dependencies.py`.
- Ports/Protocols: `src/bioetl/domain/ports/__init__.py:23-92`, `src/bioetl/infrastructure/locking/memory_lock.py:19-25`.
- Bronze/Silver Medallion: `src/bioetl/infrastructure/storage/bronze_writer.py:1-10`, `src/bioetl/infrastructure/storage/silver_writer.py:1-11`, `src/bioetl/infrastructure/storage/silver_writer.py:36`.
- Error classification: `src/bioetl/domain/error_classifier.py:17-57`, `src/bioetl/domain/error_classifier.py:97-126`.
- Circuit Breaker: `src/bioetl/infrastructure/adapters/http/circuit_breaker.py:66-69`, `src/bioetl/infrastructure/adapters/http/circuit_breaker.py:111-127`, `src/bioetl/infrastructure/adapters/http/circuit_breaker.py:146-155`.
- Locking/heartbeat/safety guard: `src/bioetl/infrastructure/locking/memory_lock.py:111-153`, `src/bioetl/infrastructure/locking/memory_lock.py:186-214`, `src/bioetl/infrastructure/locking/memory_lock.py:216-248`.
- DQ thresholds/quarantine: `src/bioetl/application/core/batch_transformer.py:163-207`, `src/bioetl/application/core/quarantine_manager.py:37-64`.
- Content hash normalization: `src/bioetl/domain/services/identity_service.py:96-124`, `src/bioetl/domain/services/identity_service.py:136-142`.
- Logging/run_id: `src/bioetl/infrastructure/observability/unified_logger.py:97-103`, `src/bioetl/application/services/pipeline_runner_service.py:251-266`.
- Medallion paths in settings: `src/bioetl/infrastructure/config/_base.py:384-406`.
- Validator caveat: `src/bioetl/infrastructure/validation/pandera_validator.py:36-46`, `src/bioetl/infrastructure/validation/pandera_validator.py:64-71`, `src/bioetl/infrastructure/validation/pandera_validator.py:192-210`.

## Часть 3. Сводная таблица

| # | Категория | Вес | Оценка | Взвеш. балл | Ключевые находки |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | Слоистая архитектура | 15% | 10 | 1.50 | Нарушений импорт-границ не найдено |
| 2 | Контракты и Ports | 12% | 9 | 1.08 | Protocol-first, реализации в infrastructure |
| 3 | Medallion Architecture | 12% | 9 | 1.08 | Bronze JSONL+zstd, Silver Delta, Gold есть |
| 4 | Ошибки и Circuit Breaker | 10% | 9 | 0.90 | Error taxonomy + CB state machine + metrics |
| 5 | Блокировки и конкурентность | 10% | 9 | 0.90 | MemoryLock TTL/heartbeat + safety guard |
| 6 | Валидация и DQ | 10% | 8 | 0.80 | Pandera + Quarantine + thresholds, но есть NoOp/strict=False |
| 7 | Логирование и observability | 8% | 9 | 0.72 | Нет print, есть unified logging/metrics |
| 8 | Тестирование | 8% | 7 | 0.56 | Высокое покрытие, но есть падающие formatting checks |
| 9 | Безопасность и секреты | 8% | 8 | 0.64 | Явного hardcode нет, нужны более точные CI-детекторы |
| 10 | Документация и сопровождаемость | 7% | 8 | 0.56 | Сильная база, но не все запрошенные документы найдены |
| **Итого** |  | **100%** |  | **8.74** |  |

### 3.2 Интерпретация общего балла

**8.74 / 10** → **Production-ready, minor improvements**.

### 3.3 План рефакторинга

#### [P1] Закрыть статический долг типов (`mypy --strict`)

- **Категория**: 8 (Тестирование), 1/2 (Архитектурная дисциплина API)
- **Текущий балл → Целевой балл**: 7 → 9
- **Влияние на общий балл**: +0.16
- **Проблема**: 39 ошибок strict-типизации.
- **Решение**: поэтапно убрать `Any`-утечки/несовпадения типов в публичных API.
- **Файлы**: по отчёту mypy (`/tmp/mypy_out.txt`).
- **Риски**: регрессии контрактов при ужесточении сигнатур.
- **Критерий готовности**: `mypy src/bioetl --strict` = 0 ошибок.
- **Трудозатраты**: M (2-5 дней).

#### [P1] Привести CI formatting к зелёному состоянию

- **Категория**: 8
- **Текущий балл → Целевой балл**: 7 → 9
- **Влияние на общий балл**: +0.16
- **Проблема**: падают архитектурные проверки форматирования.
- **Решение**: прогнать `ruff format`/`ruff check --fix`, зафиксировать baseline.
- **Файлы**: затронутые python-модули/тесты.
- **Риски**: большие массовые diff.
- **Критерий готовности**: `pytest tests/architecture/test_code_formatting.py` pass.
- **Трудозатраты**: S (0.5-1 день).

#### [P2] Ужесточить strict validation для Gold/Silver

- **Категория**: 6
- **Текущий балл → Целевой балл**: 8 → 9
- **Влияние на общий балл**: +0.10
- **Проблема**: валидаторы допускают `strict=False` и `NoOpValidator`.
- **Решение**: для production-пайплайнов запретить NoOp и включить strict schema enforcement.
- **Файлы**: `infrastructure/validation/pandera_validator.py`, composition factories.
- **Риски**: падение пайплайнов на исторических drift-данных.
- **Критерий готовности**: smoke-run с mandatory schema validation.
- **Трудозатраты**: M (2-4 дня).

#### [P2] Ввести точный scanner секретов в CI

- **Категория**: 9
- **Текущий балл → Целевой балл**: 8 → 9
- **Влияние на общий балл**: +0.08
- **Проблема**: текущий grep даёт шум по `api_key=` без literal.
- **Решение**: gitleaks/trufflehog rule-set + allowlist.
- **Файлы**: CI-конфиг, pre-commit.
- **Риски**: ложноположительные блокировки PR.
- **Критерий готовности**: 0 high-severity secret findings в CI.
- **Трудозатраты**: S (0.5-1 день).

#### [P3] Восстановить/добавить навигационные архитектурные документы

- **Категория**: 10
- **Текущий балл → Целевой балл**: 8 → 9
- **Влияние на общий балл**: +0.07
- **Проблема**: часть запрошенных документов отсутствует в ожидаемом каталоге.
- **Решение**: добавить актуальные docs-индексы/redirects на заменившие документы.
- **Файлы**: `docs/00-project/*`, `docs/index.md`.
- **Риски**: минимум.
- **Критерий готовности**: все ссылки из onboarding-а резолвятся.
- **Трудозатраты**: S (0.5 дня).

### 3.4 Roadmap

- **Фаза 1 (неделя 1-2, P1)**: mypy strict debt + formatting green. Ожидаемый общий балл: **8.74 → 9.06**.
- **Фаза 2 (неделя 3-4, P2)**: strict validation policy + secret scanning. Ожидаемый общий балл: **9.06 → 9.24**.
- **Фаза 3 (неделя 5+, P3)**: документационные улучшения. Ожидаемый общий балл: **9.24 → 9.31**.

## Часть 4. Метрики контроля регресса (CI)

| Метрика | Порог | Команда | Блокирует PR |
| --- | --- | --- | --- |
| Coverage | ≥85% | `pytest --cov=src/bioetl --cov-fail-under=85` | Да |
| mypy errors | 0 | `mypy src/bioetl --strict` | Да |
| Циклические импорты | 0 | `python -c "from bioetl.domain import *"` + import graph check | Да |
| Нарушения слоёв | 0 | `pytest tests/architecture/test_layer_dependencies.py` | Да |
| print() в коде | 0 | `rg 'print\(' src/bioetl -g '*.py'` | Да |
| Форматирование | 0 нарушений | `pytest tests/architecture/test_code_formatting.py` | Да |
| Hardcoded secrets | 0 high severity | `gitleaks detect --source .` | Да |

## Verification Log (ключевые команды)

- `mypy src/bioetl --strict 2>&1 | tee /tmp/mypy_out.txt >/dev/null; rg -c "error:" /tmp/mypy_out.txt`
- `.venv/bin/python -c "from bioetl.domain import *" && echo pass || echo fail`
- `rg '^class ' src/ -g '*.py' | wc -l`
- `find src/ -name '*.py' | wc -l`
- `python - <<'PY' ... Path('src/bioetl').rglob('*.py') ... PY`
- `rg -e '(TODO|FIXME|XXX|HACK)' src/ | wc -l`
- `rg 'print\(' src/bioetl -g '*.py' | wc -l`
- `rg -e '(api_key|password|secret)\s*=' src/ | wc -l`
- `rg 'from bioetl\.infrastructure|import bioetl\.infrastructure|from bioetl\.application|import bioetl\.application' src/bioetl/domain -n`
- `rg 'from bioetl\.interfaces|import bioetl\.interfaces' src/bioetl/application -n`
