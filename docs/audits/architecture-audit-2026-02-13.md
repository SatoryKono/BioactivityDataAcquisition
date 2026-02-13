# Архитектурный аудит BioETL

Дата: 2026-02-13
Область: `src/bioetl`, `tests/`, `docs/00-project/*`

## Проверенные документы

- ✅ Прочитан `docs/00-project/agents/AGENT.md`.
- ✅ Прочитан `docs/00-project/RULES.md`.
- ⚠️ Документы `01-domain-objects.md`, `02-etl-layers.md`, `03-data-flow.md`, `04-duplication-reduction.md`, `05-physical-layout.md` в репозитории не найдены.

______________________________________________________________________

## Часть 1. Объективные метрики

| Метрика                              | Команда/метод                                            |                                                             Значение |
| ------------------------------------ | -------------------------------------------------------- | -------------------------------------------------------------------: |
| Покрытие тестами                     | `pytest tests/ --cov=src/bioetl --cov-report=term`       | [данные отсутствуют] (запуск прерван: `ModuleNotFoundError: pandas`) |
| Ошибки mypy                          | `mypy src/bioetl --strict 2>&1` + подсчёт `error:`       |                                                           **39 шт.** |
| Циклические импорты                  | `PYTHONPATH=src python -c "from bioetl.domain import *"` |            **fail** (импорт прерван: `ModuleNotFoundError: pandera`) |
| Количество классов                   | `rg "^class " src --glob '*.py'` + `wc -l`               |                                                          **884 шт.** |
| Количество файлов .py                | `find src -name '*.py'` + `wc -l`                        |                                                          **533 шт.** |
| Средний размер модуля (`src/bioetl`) | python-скрипт: сумма строк / число `.py`                 |                                                     **222.38 строк** |
| TODO/FIXME в коде                    | \`rg -n -e "TODO                                         |                                                                FIXME |
| Использование `print()`              | `rg "print\(" src/bioetl --glob '*.py'` + `wc -l`        |                                                            **0 шт.** |
| Hardcoded secrets (по шаблону)       | \`rg -n -e "(api_key                                     |                                                             password |

______________________________________________________________________

## Часть 2. Оценка по 10 категориям

### 1) Соблюдение слоистой архитектуры — **4/10**

**Нарушения/риски:**

- В `infrastructure` есть многочисленные прямые импорты из `domain` (не только `domain.ports`), напр. `domain.exceptions`, `domain.resilience`, `domain.entities`.
  - Примеры: `src/bioetl/infrastructure/adapters/http/client.py`, `src/bioetl/infrastructure/adapters/pubchem/client.py`, `src/bioetl/infrastructure/storage/silver_writer.py`.
- По метрике grep: 97 импортов `domain.*` (не `domain.ports`) внутри `infrastructure`.

**Положительное:**

- Прямых импортов `infrastructure`/`application` из `domain` не найдено.

______________________________________________________________________

### 2) Контракты и Ports — **6/10**

**Положительное:**

- В `domain/ports` реализовано большое число Protocol-контрактов (минимум 38 объявлений).
- `StoragePort` декларирует операции Bronze/Silver/Gold и lock-invariant на уровне контракта.

**Нарушения/риски:**

- Значимая часть `infrastructure` зависит от конкретных domain-моделей/исключений, что снижает долю «чистых» зависимостей через ports.

______________________________________________________________________

### 3) Medallion Architecture — **8/10**

**Положительное:**

- Bronze: JSONL + zstd подтверждено в `BronzeWriter`.
- Silver: Delta Lake (`write_deltalake`, `DeltaTable`), merge/upsert присутствуют.
- Gold: строгая валидация через Pandera (`strict=True` обязателен).

**Отклонения:**

- Формат Bronze path в коде: `{provider}/{entity}/{date}/...`, без явного `bronze/v1/...` префикса в самом writer.

______________________________________________________________________

### 4) Обработка ошибок и Circuit Breaker — **9/10**

**Положительное:**

- Есть классификатор ошибок с раздельными классами (critical/recoverable/dq-паттерны).
- Circuit Breaker реализован с порогом 5, timeout 300s, Half-Open probe.
- Есть метрики по состоянию и trip-событиям (`circuit_breaker_state`, `circuit_breaker_trips_total`).

**Нарушения:**

- Критических нарушений не выявлено по проверенным файлам.

______________________________________________________________________

### 5) Блокировки и конкурентность — **8/10**

**Положительное:**

- Используется `MemoryLock` (local-only, как в ADR-010 контексте), поддержаны TTL, heartbeat, owner validation (safety guard).
- Конфиг runtime: `lock_ttl=90`, `heartbeat_interval=30`, `effective_lock_ttl = heartbeat*3`.

**Отклонения/риски:**

- Нет явного отдельного fencing token объекта; роль fencing фактически выполняет `owner_id` в lock-состоянии.

______________________________________________________________________

### 6) Валидация и DQ — **8/10**

**Положительное:**

- DQ thresholds 5%/20% заданы в domain-конфиге.
- Unified quarantine реализован (`common`-подход, payload truncate 64KB, purge по 30 дням).
- Content hash реализован канонически: `sha256(provider + canonical_json)` с нормализацией и исключением meta-fields.

**Риски:**

- Полный охват «Pandera для всех сущностей» в рамках аудита не подтверждён автоматически (нужен полный inventory схем и pipeline mapping).

______________________________________________________________________

### 7) Логирование и наблюдаемость — **9/10**

**Положительное:**

- `UnifiedLogger` требует `run_id` и `pipeline`, stage автоматически нормализуется.
- JSON/structured logging и централизованная конфигурация.
- Присутствуют Prometheus-метрики и сервер метрик.
- `print()` в `src/bioetl` не найден.

______________________________________________________________________

### 8) Тестирование — **5/10**

**Положительное:**

- Большой массив тестов архитектуры (`tests/architecture`), есть использование VCR и golden-подхода.

**Проблемы:**

- Фактическое покрытие не подтверждено из-за отсутствующих зависимостей (`pandas`) в окружении аудита.
- Оценка снижена из-за невозможности подтвердить ключевой KPI (`coverage >=85%`).

______________________________________________________________________

### 9) Безопасность и секреты — **8/10**

**Положительное:**

- API keys и PII salts хранятся через `SecretStr`/settings.
- PII hashing с salt реализован.

**Риски:**

- grep-метрика по паттерну находит 14 совпадений, но это в основном переменные/проброс, а не hardcoded literals; требуется периодический ручной review.

______________________________________________________________________

### 10) Документация и сопровождаемость — **8/10**

**Положительное:**

- Актуальные правила (`RULES.md`), глоссарий, карта docs.
- Ведётся `CHANGELOG.md`.
- В коде широкое покрытие docstrings в ключевых модулях.

**Ограничения:**

- Запрошенные документы `01..05` отсутствуют в дереве `docs/00-project`.

______________________________________________________________________

## Часть 3. Сводный результат

### 3.1. Сводная таблица

| #         | Категория                       |      Вес | Оценка |   Взвеш. балл | Ключевые находки                                              |
| --------- | ------------------------------- | -------: | -----: | ------------: | ------------------------------------------------------------- |
| 1         | Слоистая архитектура            |      15% |      4 |          0.60 | 97 импортов `infrastructure -> domain.* (не ports)`           |
| 2         | Контракты и Ports               |      12% |      6 |          0.72 | Ports есть, но не везде используются как единственная граница |
| 3         | Medallion Architecture          |      12% |      8 |          0.96 | Bronze JSONL+zstd, Silver Delta, Gold strict                  |
| 4         | Ошибки и Circuit Breaker        |      10% |      9 |          0.90 | CB + метрики + классификация ошибок                           |
| 5         | Блокировки и конкурентность     |      10% |      8 |          0.80 | MemoryLock TTL/heartbeat/safety guard                         |
| 6         | Валидация и DQ                  |      10% |      8 |          0.80 | Thresholds, Quarantine, Content Hash                          |
| 7         | Логирование и наблюдаемость     |       8% |      9 |          0.72 | UnifiedLogger + structured logs + metrics                     |
| 8         | Тестирование                    |       8% |      5 |          0.40 | Coverage не получен в текущем окружении                       |
| 9         | Безопасность и секреты          |       8% |      8 |          0.64 | SecretStr + salted hashing                                    |
| 10        | Документация и сопровождаемость |       7% |      8 |          0.56 | RULES/AGENT/CHANGELOG в наличии                               |
| **Итого** |                                 | **100%** |        | **7.10 / 10** |                                                               |

### 3.2. Интерпретация общего балла

**7.10 / 10** → *«Требуется рефакторинг, но система работоспособна»*.

### 3.3. План рефакторинга

### [P1] Ужесточить границы `infrastructure -> domain` через ports-only

- **Категория**: 1, 2
- **Текущий балл → Целевой балл**: 4 → 8 (архитектура), 6 → 8 (ports)
- **Влияние на общий балл**: **+0.84**
- **Проблема**: Прямые импорты `domain.*` (кроме ports) в инфраструктуре.
- **Решение**:
  1. вынести нужные типы/ошибки в `domain.ports`/DTO контракты,
  1. заменить прямые импорты на port-абстракции,
  1. добавить CI-check на запрет `from bioetl.domain.(?!ports)` в `infrastructure`.
- **Файлы**: `src/bioetl/infrastructure/adapters/*`, `src/bioetl/infrastructure/storage/*`, `src/bioetl/domain/ports/*`.
- **Риски**: регрессии сериализации/обработки ошибок.
- **Критерий готовности**: 0 нарушений по grep-правилу + зелёные architecture tests.
- **Трудозатраты**: **L** (1-2 недели).

### [P2] Зафиксировать Medallion path-contract в коде и тестах

- **Категория**: 3
- **Текущий балл → Целевой балл**: 8 → 9
- **Влияние на общий балл**: **+0.12**
- **Проблема**: path в BronzeWriter не фиксирует `v1` в явном виде.
- **Решение**: добавить версионированный path-builder (`bronze/v1/...`) + контрактные тесты путей.
- **Файлы**: `src/bioetl/infrastructure/storage/bronze_writer.py`, `tests/architecture/`, `tests/unit/infrastructure/storage/`.
- **Риски**: несовместимость с существующими каталогами данных.
- **Критерий готовности**: тесты на path-format + миграционный fallback.
- **Трудозатраты**: **M** (2-4 дня).

### [P2] Стабилизировать quality gates окружения (coverage/mypy/import check)

- **Категория**: 8
- **Текущий балл → Целевой балл**: 5 → 8
- **Влияние на общий балл**: **+0.24**
- **Проблема**: в текущем окружении аудит не смог воспроизвести test coverage.
- **Решение**: зафиксировать dev bootstrap в CI/job templates; добавить smoke-check зависимостей перед тестами.
- **Файлы**: `pyproject.toml`, CI workflow files, `dev_setup.sh`.
- **Риски**: увеличение времени CI.
- **Критерий готовности**: coverage job стабильно выдаёт процент на каждом PR.
- **Трудозатраты**: **S-M** (1-3 дня).

### [P3] Автоматизировать triage потенциальных secret-pattern совпадений

- **Категория**: 9
- **Текущий балл → Целевой балл**: 8 → 9
- **Влияние на общий балл**: **+0.08**
- **Проблема**: regex-срабатывания смешивают безопасный код и риск.
- **Решение**: semgrep/ruff-rule для hardcoded literal secrets + allowlist для безопасных переменных.
- **Файлы**: `.pre-commit-config.yaml`, CI config, policy docs.
- **Риски**: ложные срабатывания на старте.
- **Критерий готовности**: 0 ложных блокировок на 3 последовательных PR.
- **Трудозатраты**: **S** (0.5-1 день).

### 3.4. Roadmap

- **Фаза 1 (неделя 1-2)**: P1 (границы слоёв) + частично P2 (quality gates).
  Ожидаемый общий балл: **7.1 → 7.8**.
- **Фаза 2 (неделя 3-4)**: P2 (Medallion path-contract + CI стабилизация).
  Ожидаемый общий балл: **7.8 → 8.2**.
- **Фаза 3 (неделя 5+)**: P3 (security triage automation, polishing).
  Ожидаемый общий балл: **8.2 → 8.3+**.

______________________________________________________________________

## Часть 4. Метрики контроля регресса (для CI)

| Метрика                   |                Порог | Команда                                                                              | Блокирует PR |
| ------------------------- | -------------------: | ------------------------------------------------------------------------------------ | ------------ |
| Coverage                  |                 ≥85% | `pytest --cov=src/bioetl --cov-fail-under=85`                                        | Да           |
| mypy errors               |                    0 | `mypy src/bioetl --strict`                                                           | Да           |
| Циклические импорты       |                    0 | `PYTHONPATH=src python -c "from bioetl.domain import *"` + custom import graph check | Да           |
| Нарушения слоёв           |                    0 | `rg -nP "^from bioetl\.domain\.(?!ports)" src/bioetl/infrastructure`                 | Да           |
| `print()` в коде          |                    0 | `rg "print\(" src/bioetl --glob '*.py'`                                              | Да           |
| Hardcoded secret literals |                    0 | `semgrep --config <ruleset>` / custom regex + AST                                    | Да           |
| Bronze format guard       | 100% path compliance | unit tests for bronze path resolver                                                  | Да           |
| Silver format guard       |           Delta only | grep/test forbidding parquet writes in silver writers                                | Да           |

______________________________________________________________________

## Verification Log (команды)

- `pytest tests/ --cov=src/bioetl --cov-report=term`
- `mypy src/bioetl --strict 2>&1`
- `PYTHONPATH=src python -c "from bioetl.domain import *"`
- `rg "^class " src --glob '*.py' | wc -l`
- `find src -name '*.py' | wc -l`
- Python script: average module lines in `src/bioetl`
- `rg -n -e "TODO|FIXME|XXX|HACK" src | wc -l`
- `rg "print\(" src/bioetl --glob '*.py' | wc -l`
- `rg -n -e "(api_key|password|secret)\s*=" src | wc -l`
- `rg -nP "^from bioetl\.domain\.(?!ports)" src/bioetl/infrastructure --glob '*.py' | wc -l`
