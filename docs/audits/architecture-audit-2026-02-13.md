# Архитектурный аудит BioETL

Дата: 2026-02-13
Область: `src/bioetl`, `tests`, `docs/00-project`

## 0) Проверка входных артефактов

Запрошенные документы `01-domain-objects.md`, `02-etl-layers.md`, `03-data-flow.md`, `04-duplication-reduction.md`, `05-physical-layout.md` в репозитории не найдены (поиск в `docs/`), поэтому оценка выполнена по фактическим артефактам: `docs/00-project/RULES.md`, `docs/00-project/agents/AGENT.md` и коду.
Статус: **[данные отсутствуют частично]**.

## 1) Объективные метрики

| Метрика                              | Команда/метод                                                          |                                                                                                                       Значение |
| ------------------------------------ | ---------------------------------------------------------------------- | -----------------------------------------------------------------------------------------------------------------------------: |
| Покрытие тестами                     | `.venv/bin/python -m pytest tests/ --cov=src/bioetl --cov-report=term` | \[данные отсутствуют: прогон не завершён, отдельный прогон с `--maxfail=1` остановлен на `detect_secrets` до отчёта покрытия\] |
| Ошибки mypy                          | \`mypy src/bioetl --strict 2>&1                                        |                                                                                                               rg -c "error:"\` |
| Циклические импорты                  | `PYTHONPATH=src .venv/bin/python -c "from bioetl.domain import *"`     |                                                                                                                       **pass** |
| Количество классов                   | `rg '^class ' src --glob '*.py' \| wc -l`                              |                                                                                                                    **887 шт.** |
| Количество файлов `.py`              | `find src -name '*.py' \| wc -l`                                       |                                                                                                                    **542 шт.** |
| Средний размер модуля (`src/bioetl`) | `find src/bioetl -name '*.py'` + расчёт `lines/files`                  |                                                                                                               **222.08 строк** |
| TODO/FIXME в коде                    | `rg -n -P '(TODO\|FIXME\|XXX\|HACK)' src \| wc -l`                     |                                                                                                                     **23 шт.** |
| Использование `print()`              | `rg 'print\\(' src/bioetl --glob '*.py' \| wc -l`                      |                                                                                                                      **0 шт.** |
| Hardcoded secrets                    | `rg -n -P '(api_key\|password\|secret)\\s*=' src \| wc -l`             |                                                               **14 совпадений (паттерн), подтверждённых hardcoded literal: 0** |

### Ключевые диагностические факты

- `pytest` ранне падает на architecture-тесте из-за отсутствующего пакета `detect_secrets` в venv (не кодовая ошибка приложения): `tests/architecture/test_antipatterns.py::test_no_hardcoded_secrets`.
- `ruff format --check src` сообщает 1 неотформатированный файл: `src/bioetl/infrastructure/storage/gold_writer.py`.

## 2) Оценка по 10 категориям

> Шкала 1-10 по критериям задачи. Ниже только подтверждённые наблюдения из кода/команд.

### 1. Соблюдение слоистой архитектуры (вес 15%)

**Оценка: 9/10**

**Что проверено**

- Нарушений `domain -> infrastructure/application` и `application -> interfaces` по прямым импортам не найдено (`rg` по слоям).
- В `infrastructure` встречаются импорты не только `domain.ports`, но и других доменных модулей (например, `domain.config`, `domain.types`, `domain.serialization`). Это допустимо в текущем governance, но усиливает связность.

**Подтверждения**

- Пример корректного порта: `domain/ports/locking.py`.
- Примеры инфраструктурных импортов доменных моделей: `infrastructure/schemas/pipeline_config.py`, `infrastructure/quarantine/operations.py`.

### 2. Контракты и Ports (вес 12%)

**Оценка: 9/10**

**Наблюдения**

- В `domain/ports/` системно используются `Protocol` (locking, storage, observability, resilience, validation, etc.).
- Реализации портов присутствуют в `infrastructure` (например, `MemoryLock`, `UnifiedLogger`, `PrometheusMetricsAdapter`, writers/validators).

**Вывод**

- Покрытие абстракциями высокое; существенных прямых привязок application к внешним библиотекам как архитектурный паттерн не выявлено.

### 3. Medallion Architecture (вес 12%)

**Оценка: 9/10**

**Наблюдения**

- Bronze: явно реализован как JSONL + zstd (`infrastructure/storage/bronze_writer.py`).
- Silver/Gold: используют Delta Lake (`write_deltalake` в `silver_writer.py`, `gold_writer.py`).
- VACUUM и retention присутствуют (CLI команды `vacuum`, сервисы retention).

**Риски/замечания**

- Паттерн путей в коде местами фиксируется через соглашения в composition; для полной валидации всех path-pattern по RULES нужен отдельный контрактный тест на layout.

### 4. Обработка ошибок и Circuit Breaker (вес 10%)

**Оценка: 8/10**

**Наблюдения**

- Circuit Breaker реализован с состояниями CLOSED/OPEN/HALF_OPEN, threshold=5, recovery_timeout=300s, probe в half-open (`infrastructure/adapters/http/circuit_breaker.py`).
- Есть метрики состояния и срабатываний (`circuit_breaker_state`, `circuit_breaker_trips_total`).
- Классификация ошибок для триггера CB ограничена сетевыми и 5xx/429.

**Ограничение**

- Унифицированная трёхклассовая матрица Critical/Recoverable/DQ в едином централизованном классификаторе не обнаружена как единая точка (распределена по компонентам).

### 5. Блокировки и конкурентность (вес 10%)

**Оценка: 9/10**

**Наблюдения**

- По ADR local-only используется `MemoryLock` (без Redis) — это корректно по проектным правилам.
- Реализованы TTL, heartbeat, валидация владельца и fencing token (`infrastructure/locking/memory_lock.py`, `domain/ports/locking.py`).
- В runtime-конфиге зафиксированы heartbeat 30s и lock_ttl 90s (`domain/config/runtime.py`).

### 6. Валидация и DQ (вес 10%)

**Оценка: 8/10**

**Наблюдения**

- Pandera-валидаторы реализованы (`infrastructure/validation/pandera_validator.py`), схемы Silver/Gold описаны.
- Quarantine реализован как отдельный контур (`infrastructure/quarantine/unified.py`).
- Content hash реализован через доменный `IdentityService` с нормализацией и исключением метаполей (`domain/services/identity_service.py` + `application/core/base_transformer.py`).
- Метрики DQ присутствуют (`infrastructure/observability/metrics.py`, `prometheus_metrics.py`).

**Риск**

- mypy-ошибки в модуле схем (в т.ч. untyped decorator/DataFrameModel typing) снижают надёжность строгой типовой валидации.

### 7. Логирование и наблюдаемость (вес 8%)

**Оценка: 9/10**

**Наблюдения**

- `UnifiedLogger` внедряет structured JSON-подход и bind run_id/pipeline в конструкторе.
- `print()` в `src/bioetl` не найдено.
- Prometheus метрики присутствуют (pipeline, DQ, vacuum и др.).

### 8. Тестирование (вес 8%)

**Оценка: 4/10**

**Наблюдения**

- Тестовый набор очень большой (11777 items), но в текущем окружении baseline-запуск падает рано из-за отсутствия `detect_secrets`.
- Не удалось получить фактический `% coverage` по полной команде.

**Вывод**

- До воспроизводимого зелёного CI-локала с покрытием ≥85% критерий не закрыт.

### 9. Безопасность и секреты (вес 8%)

**Оценка: 8/10**

**Наблюдения**

- PII hashing реализован c salt через env (`BIOETL_PII_SALT_CURRENT` и пр.) в `infrastructure/security/pii_hasher.py`.
- По regex найдено 14 мест с присваиванием полей `api_key|password|secret`, но это в основном прокидывание параметров/конфигов, не literal-секреты.

**Риск**

- Архитектурный тест на secret scan сейчас не проходит из-за missing dependency `detect_secrets`; контроль безопасности в CI/локале деградирован.

### 10. Документация и сопровождаемость (вес 7%)

**Оценка: 7/10**

**Наблюдения**

- Есть `README.md`, `CHANGELOG.md`, объёмная проектная конституция в `docs/00-project/RULES.md`.
- Есть architecture-тесты, проверяющие синхронизацию документации.

**Ограничение**

- Часть документов, запрошенных в постановке аудита, отсутствует в дереве `docs/00-project`.

## 3) Сводная таблица

| #         | Категория                       |      Вес | Оценка |   Взвеш. балл | Ключевые находки                                           |
| --------- | ------------------------------- | -------: | -----: | ------------: | ---------------------------------------------------------- |
| 1         | Слоистая архитектура            |      15% |      9 |          1.35 | Прямые запретные импорты не найдены                        |
| 2         | Контракты и Ports               |      12% |      9 |          1.08 | Широкое использование Protocol в domain/ports              |
| 3         | Medallion Architecture          |      12% |      9 |          1.08 | Bronze JSONL+zstd, Silver/Gold Delta, VACUUM               |
| 4         | Ошибки и Circuit Breaker        |      10% |      8 |          0.80 | CB реализован с метриками и half-open                      |
| 5         | Блокировки и конкурентность     |      10% |      9 |          0.90 | MemoryLock + heartbeat + fencing + safety checks           |
| 6         | Валидация и DQ                  |      10% |      8 |          0.80 | Pandera + quarantine + content hash + DQ metrics           |
| 7         | Логирование и наблюдаемость     |       8% |      9 |          0.72 | UnifiedLogger + run_id + Prometheus; print=0               |
| 8         | Тестирование                    |       8% |      4 |          0.32 | Запуск тестов/coverage не воспроизводим полностью          |
| 9         | Безопасность и секреты          |       8% |      8 |          0.64 | Env-based salts, literal-secrets не подтверждены           |
| 10        | Документация и сопровождаемость |       7% |      7 |          0.49 | База документации сильная, но есть пробелы в наборе файлов |
| **Итого** |                                 | **100%** |        | **8.18 / 10** |                                                            |

## 3.2 Интерпретация общего балла

**8.18 / 10 → Production-ready, minor improvements**.

Ограничивающий фактор: воспроизводимость quality-gates (coverage, detect-secrets, strict typing).

## 3.3 План рефакторинга

### [P1] Восстановить воспроизводимость quality gates (coverage + secrets scan)

**Категория**: 8, 9
**Текущий балл → Целевой балл**: 4→8 (Testing), 8→9 (Security)
**Влияние на общий балл**: +0.40..+0.55

- **Проблема**: `pytest`-аудит падает на отсутствии `detect_secrets`; покрытие не вычисляется.
- **Решение**: зафиксировать `detect-secrets` в dev/test зависимостях, добавить smoke-check в CI перед тестами.
- **Файлы**: `pyproject.toml`/`requirements-dev` [файл не анализировался подробно, требуется точка истины зависимостей].
- **Риски**: минимальные, возможны несовместимости версии плагина.
- **Критерий готовности**: `pytest tests/ --cov=src/bioetl --cov-report=term` стабильно даёт coverage-отчёт.
- **Трудозатраты**: S (часы).

### [P1] Закрыть mypy strict debt (56 errors)

**Категория**: 6, 10
**Текущий балл → Целевой балл**: 8→9 (DQ), 7→8 (Maintainability)
**Влияние на общий балл**: +0.22..+0.30

- **Проблема**: 56 ошибок strict typing, в т.ч. `DataFrameModel` typing и `unused-ignore`.
- **Решение**: пакетно устранить `unused-ignore`, типизировать декораторы Pandera или локально ограничить strictness точечно (с ADR/обоснованием).
- **Файлы**: `src/bioetl/domain/schemas/uniprot/*.py`, `src/bioetl/domain/contracts/gold/*.py`, `src/bioetl/infrastructure/storage/gold_writer.py` и др. из отчёта mypy.
- **Риски**: регресс в схемах валидации.
- **Критерий готовности**: `mypy src/bioetl --strict` → 0 ошибок.
- **Трудозатраты**: M (дни).

### [P2] Контрактный тест на Medallion path conventions

**Категория**: 3
**Текущий балл → Целевой балл**: 9→10
**Влияние на общий балл**: +0.12

- **Проблема**: соответствие path patterns декларируется, но требует централизованной автоматической проверки.
- **Решение**: добавить architecture-test, проверяющий генерацию путей Bronze/Silver/Gold по контракту.
- **Файлы**: `tests/architecture/` (новый тест), path-builders в `composition`/`storage`.
- **Риски**: ложные срабатывания при легаси-путях.
- **Критерий готовности**: тест блокирует отклонения формата пути.
- **Трудозатраты**: S/M.

### [P3] Документационная консолидация проектных артефактов

**Категория**: 10
**Текущий балл → Целевой балл**: 7→9
**Влияние на общий балл**: +0.14

- **Проблема**: в текущем дереве отсутствует часть документов, упомянутых в запросе аудита.
- **Решение**: добавить/актуализировать индекс документов и канонические ссылки.
- **Файлы**: `docs/00-project/index.md`, возможно `docs/03-guides/...`.
- **Риски**: низкие.
- **Критерий готовности**: верификация ссылок и наличие всех обязательных документов.
- **Трудозатраты**: S.

## 3.4 Roadmap

- **Фаза 1 (неделя 1-2)**: P1 задачи (quality gates + mypy high-priority).
  Ожидаемый общий балл: **8.18 → ~8.8**.
- **Фаза 2 (неделя 3-4)**: P2 (контрактные path-tests, укрепление архитектурных проверок).
  Ожидаемый общий балл: **~8.8 → ~9.0**.
- **Фаза 3 (неделя 5+)**: P3 (документационная консолидация, polish).
  Ожидаемый общий балл: **~9.0 → ~9.2**.

## 4) Метрики контроля регресса (CI)

| Метрика                      |      Порог | Команда                                                                                    | Блокирует PR                                                                                         |
| ---------------------------- | ---------: | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| Coverage                     |       ≥85% | `.venv/bin/python -m pytest tests/ --cov=src/bioetl --cov-report=term --cov-fail-under=85` | Да                                                                                                   |
| mypy errors                  |          0 | `.venv/bin/python -m mypy src/bioetl --strict`                                             | Да                                                                                                   |
| Циклические импорты (domain) |          0 | `PYTHONPATH=src .venv/bin/python -c "from bioetl.domain import *"`                         | Да                                                                                                   |
| Нарушения слоёв              |          0 | \`rg -n "from bioetl.infrastructure                                                        | from bioetl.application" src/bioetl/domain`и`rg -n "from bioetl.interfaces" src/bioetl/application\` |
| print() в коде               |          0 | `rg 'print\\(' src/bioetl --glob '*.py'`                                                   | Да                                                                                                   |
| Секрет-скан                  | 0 findings | `.venv/bin/python -m detect_secrets scan --all-files` (или pre-commit hook)                | Да                                                                                                   |
| Форматирование               |   0 файлов | `.venv/bin/python -m ruff format --check src tests`                                        | Да                                                                                                   |

## Приложение: Лог верификации (команды)

- `find .. -name AGENTS.md -o -path '../*/agents/AGENT.md'`
- `cat docs/00-project/agents/AGENT.md`
- `cat docs/00-project/RULES.md`
- `.venv/bin/python -m pytest tests/ --cov=src/bioetl --cov-report=term`
- `.venv/bin/python -m pytest tests/ --cov=src/bioetl --cov-report=term --maxfail=1`
- `mypy src/bioetl --strict 2>&1 | rg -c "error:"`
- `PYTHONPATH=src .venv/bin/python -c "from bioetl.domain import *"`
- `rg '^class ' src --glob '*.py' | wc -l`
- `find src -name '*.py' | wc -l`
- `rg -n -P '(TODO|FIXME|XXX|HACK)' src | wc -l`
- `rg 'print\(' src/bioetl --glob '*.py' | wc -l`
- `rg -n -P '(api_key|password|secret)\s*=' src | wc -l`
- `.venv/bin/python -m ruff format --check src`
