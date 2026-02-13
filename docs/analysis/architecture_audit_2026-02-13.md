# Architecture Audit Report — BioETL

Date: 2026-02-13
Scope: `src/bioetl`, `tests/architecture`, `docs/00-project`

## Executive Summary

- Total findings: 14
- Critical (MUST): 1
- Moderate (SHOULD): 7
- Informational (MAY): 6
- Ограничение: пять запрошенных документов (`01-domain-objects.md` ... `05-physical-layout.md`) отсутствуют в `docs/00-project`.

## Часть 1. Объективные метрики

| Метрика                              | Команда/метод                                                                  |                                                                                                           Значение |
| ------------------------------------ | ------------------------------------------------------------------------------ | -----------------------------------------------------------------------------------------------------------------: |
| Покрытие тестами                     | `.venv/Scripts/python.exe -m pytest tests/ --cov=src/bioetl --cov-report=term` | `[данные отсутствуют]` (в Linux env нет `.venv/Scripts/python.exe`, полный прогон `pytest` был прерван по времени) |
| Ошибки mypy                          | `mypy src/bioetl --strict 2>&1 \| grep -c "error:"`                            |                                                                                                         **39 шт.** |
| Циклические импорты                  | `.venv/bin/python -c "from bioetl.domain import *"`                            |                                                                                                           **pass** |
| Количество классов                   | `grep -r "^class " src/ --include="*.py" \| wc -l`                             |                                                                                                        **884 шт.** |
| Количество файлов .py                | `find src/ -name "*.py" \| wc -l`                                              |                                                                                                        **533 шт.** |
| Средний размер модуля (`src/bioetl`) | python script (`rglob('*.py')`)                                                |                                                                                      **222.38 строк** (114081/513) |
| TODO/FIXME в коде                    | `grep -rE "(TODO\|FIXME\|XXX\|HACK)" src/ --include="*.py" \| wc -l`           |                                                                                                         **23 шт.** |
| Использование print()                | `grep -r "print(" src/bioetl --include="*.py" \| wc -l`                        |                                                                                                          **0 шт.** |
| Hardcoded secrets (pattern-based)    | `grep -rE "(api_key\|password\|secret)\s*=" src/ --include="*.py" \| wc -l`    |                                                **14 шт.** (в основном присваивания переменным, не literal-секреты) |

## Часть 2. Оценка по 10 категориям

### 1) Соблюдение слоистой архитектуры (вес 15%) — **9.5/10**

- Проверки `domain -> infrastructure/application` не выявили нарушений.
- Проверка `infrastructure -> application` также не выявила импортов.
- Наблюдение: в инфраструктуре есть допустимые импорты domain-портов и domain-сериализации (например `infrastructure/audit/file_audit.py`), что соответствует hexagonal-подходу.

**Нарушения:** не обнаружены.

### 2) Контракты и Ports (вес 12%) — **9.0/10**

- В `domain/ports` обнаружено 37 `Protocol`.
- Реализации в инфраструктуре присутствуют (`MemoryLock(LockPort)`, `PrometheusMetrics(MetricsPort)`, `BaseHttpAdapter(..., DataSourcePort)`).
- Риск: mypy strict выявляет типовые дефекты в application/composition, что снижает надежность контрактов при эволюции (39 ошибок).

**Нарушение (SHOULD):** 39 ошибок `mypy --strict` в публичных путях оркестрации/конфигурации.

### 3) Medallion Architecture (вес 12%) — **9.0/10**

- Bronze: отдельный writer с JSONL+zstd и append/atomic паттерном.
- Silver: отдельный Delta writer с merge/upsert и VACUUM retention в docstring/конфигурации.
- DQ-пороги 5%/20% заданы в доменной конфигурации.

**Нарушения:** явных архитектурных нарушений не найдено.

### 4) Обработка ошибок и Circuit Breaker (вес 10%) — **8.5/10**

- Реализован Circuit Breaker с `failure_threshold=5`, `recovery_timeout=300` и HALF_OPEN probe.
- Есть метрики CB (`state` gauge, `trips_total` counter).
- Ошибки mypy в сервисах preflight/medallion lifecycle снижают гарантию корректной обработки веток ошибок.

**Нарушение (SHOULD):** строгая типобезопасность error-flow нарушена (`preflight_service`, `medallion_lifecycle`).

### 5) Блокировки и конкурентность (вес 10%) — **8.5/10**

- ADR-010 соблюден: local-only `MemoryLock`.
- Реализованы TTL + heartbeat + safety guard (`validate_owner`).
- Runtime defaults соответствуют требованиям (heartbeat 30s, TTL 90s).
- Fencing token в явном виде не обнаружен как выделенный механизм.

**Нарушение (SHOULD):** отсутствие явного fencing token API в lock-порту/реализации.

### 6) Валидация и DQ (вес 10%) — **8.0/10**

- Pandera-схемы широко используются в `domain/schemas/*`.
- Есть quarantine service/aggregate и DQ-конфиг с soft/hard thresholds.
- Риск: `mypy` указывает на `DataFrameModel` как `Any` и untyped decorators в UniProt-схемах.

**Нарушение (SHOULD):** типизация DQ/Pandera слоя неполная (`domain/schemas/uniprot/*`).

### 7) Логирование и наблюдаемость (вес 8%) — **8.5/10**

- `print()` в `src/bioetl` отсутствует.
- Есть `LoggerPort`, `MetricsPort` и concrete `PrometheusMetrics`.
- Риск: без сквозной автоматической проверки присутствия `run_id` в каждом log event остаются потенциальные пробелы.

**Нарушение (MAY):** не найдено централизованного автоматического gate для run_id во всех событиях.

### 8) Тестирование (вес 8%) — **6.0/10**

- Тестовая база большая (`collected 11741 items` в запуске pytest).
- Архитектурные тесты присутствуют (`tests/architecture/*`).
- Фактический coverage % не получен в рамках доступного времени запуска.
- На ранней фазе прогона были падения форматных тестов (`test_ruff_formatting_src/tests`, `test_ruff_isort_check`).

**Нарушение (MUST):** нет подтвержденного coverage ≥85% для текущего состояния.

### 9) Безопасность и секреты (вес 8%) — **7.5/10**

- Прямых literal-секретов в обнаруженных совпадениях не видно; в основном flow через переменные/config.
- Есть salt-based hashing в domain service.
- Тем не менее, 14 pattern hits требуют triage в CI как потенциальный риск регрессии.

**Нарушение (SHOULD):** отсутствует нулевой baseline по pattern hits для секретов (автогейт).

### 10) Документация и сопровождаемость (вес 7%) — **5.5/10**

- Запрошенные проектные документы отсутствуют:
  - `docs/00-project/01-domain-objects.md`
  - `docs/00-project/02-etl-layers.md`
  - `docs/00-project/03-data-flow.md`
  - `docs/00-project/04-duplication-reduction.md`
  - `docs/00-project/05-physical-layout.md`
- Это блокирует полную трассировку требований к реализации.

**Нарушение (SHOULD):** неполнота документального baseline для архитектурного аудита.

## Часть 3. Сводная таблица

| #         | Категория                       |      Вес | Оценка |   Взвеш. балл | Ключевые находки                                                           |
| --------- | ------------------------------- | -------: | -----: | ------------: | -------------------------------------------------------------------------- |
| 1         | Слоистая архитектура            |      15% |    9.5 |          1.43 | Нарушений импорт-границ не найдено                                         |
| 2         | Контракты и Ports               |      12% |    9.0 |          1.08 | 37 Protocol, но 39 mypy ошибок                                             |
| 3         | Medallion Architecture          |      12% |    9.0 |          1.08 | Bronze JSONL+zstd, Silver Delta, DQ thresholds                             |
| 4         | Ошибки и Circuit Breaker        |      10% |    8.5 |          0.85 | CB реализован с метриками, типовые дефекты в flow                          |
| 5         | Блокировки и конкурентность     |      10% |    8.5 |          0.85 | MemoryLock + heartbeat + safety guard; fencing неявен                      |
| 6         | Валидация и DQ                  |      10% |    8.0 |          0.80 | Pandera+Quarantine, но typed gaps в UniProt schema                         |
| 7         | Логирование и наблюдаемость     |       8% |    8.5 |          0.68 | print=0, Ports+Prometheus есть                                             |
| 8         | Тестирование                    |       8% |    6.0 |          0.48 | Coverage не подтвержден, форматные тесты падали                            |
| 9         | Безопасность и секреты          |       8% |    7.5 |          0.60 | Literal secrets не выявлены, но 14 pattern hits                            |
| 10        | Документация и сопровождаемость |       7% |    5.5 |          0.39 | 5 ключевых документов отсутствуют                                          |
| **Итого** |                                 | **100%** |        | **8.24 / 10** | Система близка к production-ready, но есть блокеры по верификации качества |

## 3.2 Интерпретация

**8.24/10** → *Production-ready, minor improvements* с оговоркой: отсутствует подтвержденный coverage и есть strict typing debt.

## 3.3 План рефакторинга

### [P1] Зафиксировать quality gates в CI (coverage + ruff + mypy strict)

**Категория**: 8, 2, 4
**Текущий балл → Целевой балл**: 6.0 → 8.5
**Влияние на общий балл**: +0.45

- **Проблема**: отсутствует подтвержденный coverage ≥85%; форматные тесты падали; 39 mypy ошибок.
- **Решение**: добавить жесткие CI-гейты и поэтапно устранить strict-ошибки.
- **Файлы**: CI pipeline + `src/bioetl/application/core/preflight_service.py`, `src/bioetl/application/services/medallion_lifecycle.py`, `src/bioetl/composition/factories/services_factory.py`, `src/bioetl/domain/schemas/uniprot/*`.
- **Риски**: временная деградация velocity из-за ужесточения quality gates.
- **Критерий готовности**: green CI при `pytest --cov-fail-under=85`, `mypy --strict`, `ruff check`.
- **Трудозатраты**: M (2-5 дней).

### [P1] Восстановить документальный baseline проекта

**Категория**: 10
**Текущий балл → Целевой балл**: 5.5 → 8.0
**Влияние на общий балл**: +0.18

- **Проблема**: отсутствуют 5 ключевых документов в `docs/00-project`.
- **Решение**: добавить/восстановить документы и связать с `RULES.md`/ADR ссылками.
- **Файлы**: `docs/00-project/01-domain-objects.md` ... `05-physical-layout.md`.
- **Риски**: расхождение текста с реализацией.
- **Критерий готовности**: документы существуют, покрывают фактические модули и проверяются линтером markdown.
- **Трудозатраты**: S-M (1-3 дня).

### [P2] Устранить strict typing debt в Pandera/UniProt

**Категория**: 6, 2
**Текущий балл → Целевой балл**: 8.0 → 9.0
**Влияние на общий балл**: +0.18

- **Проблема**: `DataFrameModel` и decorators дают `Any/untyped` в strict режиме.
- **Решение**: адаптировать typing stubs/обертки для Pandera decorators и schema base classes.
- **Файлы**: `src/bioetl/domain/schemas/uniprot/_core.py`, `_features.py`, `_annotations.py`, `_xrefs.py`.
- **Риски**: ложные positive при изменении проверки схем.
- **Критерий готовности**: 0 mypy errors в `domain/schemas/uniprot`.
- **Трудозатраты**: M.

### [P2] Явный fencing token контракт для lock-port

**Категория**: 5
**Текущий балл → Целевой балл**: 8.5 → 9.5
**Влияние на общий балл**: +0.10

- **Проблема**: safety guard есть, но явный fencing token контракт не выделен.
- **Решение**: расширить `LockPort` возвращаемым fencing token и верификацией при write.
- **Файлы**: `src/bioetl/domain/ports/locking.py`, `src/bioetl/infrastructure/locking/memory_lock.py`, писатели storage.
- **Риски**: обратная несовместимость API lock service.
- **Критерий готовности**: архитектурные тесты на fencing + owner validation.
- **Трудозатраты**: M.

### [P3] Секреты: точный детектор вместо regex-only

**Категория**: 9
**Текущий балл → Целевой балл**: 7.5 → 8.5
**Влияние на общий балл**: +0.08

- **Проблема**: текущая regex-метрика даёт шум (переменные без literal).
- **Решение**: добавить semgrep/detect-secrets policy с allowlist для безопасных паттернов.
- **Файлы**: CI configs + pre-commit.
- **Риски**: false positives на старте.
- **Критерий готовности**: 0 high-severity findings, документированный allowlist.
- **Трудозатраты**: S.

## 3.4 Roadmap

- **Фаза 1 (неделя 1-2): P1**

  - CI gates + восстановление документов.
  - Ожидаемый общий балл: **8.24 → 8.87**.

- **Фаза 2 (неделя 3-4): P2**

  - Typing debt (Pandera) + fencing token contract.
  - Ожидаемый общий балл: **8.87 → 9.15**.

- **Фаза 3 (неделя 5+): P3**

  - Security scanner hardening.
  - Ожидаемый общий балл: **9.15 → 9.23**.

## Часть 4. Метрики контроля регресса (CI)

| Метрика                     |        Порог | Команда                                                   | Блокирует PR |
| --------------------------- | -----------: | --------------------------------------------------------- | ------------ |
| Coverage                    |         ≥85% | `pytest --cov=src/bioetl --cov-fail-under=85`             | Да           |
| mypy errors                 |            0 | `mypy src/bioetl --strict`                                | Да           |
| Циклические импорты         |            0 | `.venv/bin/python -c "from bioetl.domain import *"`       | Да           |
| Нарушения слоёв             |            0 | `pytest tests/architecture/test_layer_dependencies.py -q` | Да           |
| print() в коде              |            0 | `grep -r "print(" src/bioetl --include="*.py"`            | Да           |
| Hardcoded secrets (literal) |            0 | `detect-secrets scan --baseline .secrets.baseline`        | Да           |
| Форматирование              | 0 violations | `ruff check src tests && ruff format --check src tests`   | Да           |

## Verification Log (ключевые команды)

- `mypy src/bioetl --strict 2>&1 | tee /tmp/mypy.out; rg -c "error:" /tmp/mypy.out`
- `.venv/bin/python -c "from bioetl.domain import *"`
- `grep -r "^class " src/ --include="*.py" | wc -l`
- `find src/ -name "*.py" | wc -l`
- `grep -rE "(TODO|FIXME|XXX|HACK)" src/ --include="*.py" | wc -l`
- `grep -r "print(" src/bioetl --include="*.py" | wc -l`
- `grep -rE "(api_key|password|secret)\s*=" src/ --include="*.py" | wc -l`
- `grep -r "from bioetl.infrastructure" src/bioetl/domain/ --include="*.py"`
- `grep -r "from bioetl.application" src/bioetl/domain/ --include="*.py"`
- `grep -r "from bioetl.application" src/bioetl/infrastructure/ --include="*.py"`
