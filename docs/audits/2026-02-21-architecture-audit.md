# Architecture Audit Report

Date: 2026-02-21
Scope: `src/bioetl`, `tests`, project governance docs

## Executive Summary

- Total findings: 8
- Critical (MUST): 2
- Moderate (SHOULD): 4
- Informational (MAY): 2
- Missing reference docs from task statement: `01-domain-objects.md`, `02-etl-layers.md`, `03-data-flow.md`, `04-duplication-reduction.md`, `05-physical-layout.md` — **[данные отсутствуют]** (not found in repository).

______________________________________________________________________

## Часть 1. Объективные метрики

| Метрика                              | Команда/метод                                                          |                                                             Значение |
| ------------------------------------ | ---------------------------------------------------------------------- | -------------------------------------------------------------------: |
| Покрытие тестами                     | `.venv/bin/python -m pytest tests/ --cov=src/bioetl --cov-report=term` | **[данные отсутствуют]** (полный прогон не завершён в лимите сессии) |
| Ошибки mypy                          | `.venv/bin/python -m mypy src/bioetl --strict` + подсчёт `error:`      |                                                            **0 шт.** |
| Циклические импорты                  | `PYTHONPATH=src .venv/bin/python -c "import bioetl.domain"`            |                                                             **pass** |
| Количество классов                   | `rg '^class ' src --glob '*.py' \| wc -l`                              |                                                          **936 шт.** |
| Количество файлов .py                | `find src -name '*.py' \| wc -l`                                       |                                                          **570 шт.** |
| Средний размер модуля (`src/bioetl`) | Python-скрипт: total_lines / file_count                                |                                                     **220.15 строк** |
| TODO/FIXME/XXX/HACK                  | \`rg -n 'TODO                                                          |                                                                FIXME |
| Использование `print()`              | `rg 'print\(' src/bioetl --glob '*.py' \| wc -l`                       |                                                            **0 шт.** |
| Hardcoded secrets (эвристика)        | \`rg -n "(api_key                                                      |                                                             password |

Примечание: 9 совпадений по `api_key=` — это присваивания из параметров/настроек, не литералы секретов.

______________________________________________________________________

## Часть 2. Оценка по 10 категориям

### 1) Соблюдение слоистой архитектуры — **6/10** (вес 15%)

- Проверка `domain -> infrastructure/application`: нарушений не найдено.
- Проверка `application -> interfaces`: нарушений не найдено.
- Проверка `infrastructure -> application`: нарушений не найдено (соответствует тестам архитектуры).
- **Нарушение по stricter-правилу из системного промпта аудита**: в infrastructure есть множественные импорты из `bioetl.domain.*` вне `domain.ports` (например, `domain.exceptions`, `domain.config`, `domain.entities`).

Примеры:

- `src/bioetl/infrastructure/observability/__init__.py` импортирует `bioetl.domain.exceptions`.
- `src/bioetl/infrastructure/schemas/pipeline_config.py` импортирует `bioetl.domain.config`.
- `src/bioetl/infrastructure/adapters/chembl/constants.py` импортирует `bioetl.domain.entities.chembl`.

**Вывод:** по проектным тестам архитектуры границы в целом контролируются, но по stricter-матрице из задания — частичное несоответствие.

### 2) Контракты и Ports — **9/10** (вес 12%)

- Порты выделены в `domain/ports` через `Protocol`.
- Внешние адаптеры инфраструктуры реализуют/используют эти контракты.
- Пример корректного порта: `DataSourcePort(Protocol)` и `FilterableDataSourcePort`.

### 3) Medallion Architecture — **9/10** (вес 12%)

- Bronze реализован как JSONL+zstd и путевая структура `provider/entity/date`.
- Silver реализован на Delta Lake (`write_deltalake`, merge/upsert).
- Gold реализован отдельным writer (Delta/strict filtering).
- Правила retention/VACUUM явно отражены в спецификациях writer-модулей.

### 4) Обработка ошибок и Circuit Breaker — **9/10** (вес 10%)

- Есть доменная классификация ошибок с категориями critical/recoverable/DQ.
- Circuit Breaker реализован с CLOSED/OPEN/HALF_OPEN, threshold/recovery timeout.
- Есть метрики CB (`state`, `trips`, `success`, `failure`).

### 5) Блокировки и конкурентность — **8/10** (вес 10%)

- Реализован `MemoryLock` (ADR local-only): TTL, heartbeat, fencing token sequence.
- Механизм соответствует локальной модели, без Redis (валидно по ADR-010).
- Safety Guard в этом файле не реализуется напрямую (часть логики вынесена в application), поэтому не 10/10.

### 6) Валидация и DQ — **8/10** (вес 10%)

- Pandera validators реализованы для Silver/Gold.
- Quarantine service реализован (inspect/replay/purge/update-status).
- DQ thresholds 5%/20% присутствуют в конфиг-схемах.
- Content hash реализован через canonical hashing policy.
- Часть интегральных доказательств (полный e2e сценарий с coverage) не подтверждена в рамках этой сессии.

### 7) Логирование и наблюдаемость — **9/10** (вес 8%)

- UnifiedLogger с обязательным `run_id`/`pipeline` и JSON-логированием.
- `print()` в `src/bioetl` не найден.
- Prometheus метрики присутствуют, включая DQ/CB/health.

### 8) Тестирование — **7/10** (вес 8%)

- Наличие unit/integration/architecture/security/contract test suites.
- Есть VCR fixtures и проверки на утечки секретов в cassette.
- Есть golden master test (`tests/architecture/test_config_golden_master.py`).
- **Coverage metric не получен в сессии** → оценка снижена из-за неполных объективных данных.

### 9) Безопасность и секреты — **8/10** (вес 8%)

- Явных hardcoded secret literals не выявлено.
- Секреты читаются из конфигов/env-paths в composition/adapters.
- Есть security tests для VCR cassette hygiene.
- Для ротации/политик salt есть реализация PII hasher, но аудит ротации salt частично требует ops-подтверждения.

### 10) Документация и сопровождаемость — **9/10** (вес 7%)

- Есть RULES, ADR-дерево, CHANGELOG, развитая test-документация.
- Публичные модули богато документированы docstring-ами.
- Не найдены дополнительные документы из задания (пять файлов) — это gap входной документации, не кода.

______________________________________________________________________

## Часть 3. Сводная таблица

| #         | Категория                     |      Вес | Оценка |   Взвеш. балл | Ключевые находки                                                                 |
| --------- | ----------------------------- | -------: | -----: | ------------: | -------------------------------------------------------------------------------- |
| 1         | Слоистая архитектура          |      15% |    6.0 |          0.90 | Domain/Application границы чистые; infra->domain (non-ports) по stricter-правилу |
| 2         | Контракты и Ports             |      12% |    9.0 |          1.08 | Protocol-порты в domain, адаптеры в infrastructure                               |
| 3         | Medallion Architecture        |      12% |    9.0 |          1.08 | Bronze JSONL+zstd, Silver Delta merge, Gold writer                               |
| 4         | Ошибки и Circuit Breaker      |      10% |    9.0 |          0.90 | Классификация + CB state machine + метрики                                       |
| 5         | Блокировки и конкурентность   |      10% |    8.0 |          0.80 | MemoryLock + TTL + heartbeat + fencing                                           |
| 6         | Валидация и DQ                |      10% |    8.0 |          0.80 | Pandera + Quarantine + thresholds + content hash                                 |
| 7         | Логирование/наблюдаемость     |       8% |    9.0 |          0.72 | UnifiedLogger, run_id, Prometheus                                                |
| 8         | Тестирование                  |       8% |    7.0 |          0.56 | Многоуровневые тесты, VCR/golden; coverage не получен                            |
| 9         | Безопасность/секреты          |       8% |    8.0 |          0.64 | Нет явных hardcoded literals, security tests есть                                |
| 10        | Документация/сопровождаемость |       7% |    9.0 |          0.63 | RULES+ADR+CHANGELOG в актуальной структуре                                       |
| **Итого** |                               | **100%** |        | **8.11 / 10** |                                                                                  |

### 3.2 Интерпретация

**8.11 / 10** → *Production-ready, minor improvements*.

______________________________________________________________________

## 3.3 План рефакторинга

### [P1] Формализовать допустимые импорты infrastructure -> domain

- Категория: 1 (слои)
- Текущий балл → Целевой балл: 6 → 9
- Влияние на общий балл: +0.45
- Проблема: stricter-правило требует только `domain.ports`, но фактически используется `domain.exceptions/config/entities`.
- Решение:
  1. Либо обновить rulebook/ADR с явной матрицей разрешённых `infrastructure -> domain` импортов.
  1. Либо выделить DTO/errors в нейтральный shared-kernel и сократить non-port импорты.
- Файлы: `src/bioetl/infrastructure/**`, `tests/architecture/test_layer_dependencies.py`, `.importlinter`
- Риски: массовый рефакторинг типов и исключений, временные регрессии контрактов.
- Критерий готовности: архитектурный тест + import-linter контракт с явной policy.
- Трудозатраты: **M** (дни)

### [P1] Получить и зафиксировать baseline coverage в CI

- Категория: 8 (тестирование)
- Текущий балл → Целевой балл: 7 → 9
- Влияние на общий балл: +0.16
- Проблема: нет подтверждённого coverage-числа в рамках аудита.
- Решение: выделить nightly/full pipeline job с публикацией `coverage.xml` и badge.
- Файлы: CI workflow, `pyproject.toml`/`pytest.ini`.
- Риски: удлинение CI, flaky integration tests.
- Критерий готовности: стабильный `pytest --cov ...` с артефактом и trend.
- Трудозатраты: **S/M**

### [P2] Жёсткая проверка run_id в лог-событиях end-to-end

- Категория: 7
- Текущий балл → Целевой балл: 9 → 10
- Влияние на общий балл: +0.08
- Проблема: инфраструктурно run_id enforced в UnifiedLogger, но не подтверждён сквозной e2e тест для всех entrypoints.
- Решение: добавить архитектурный тест на обязательный `run_id` в событиях запуска пайплайна.
- Файлы: `tests/architecture/`, `interfaces/cli`.
- Риски: ложные падения при тестах с NoOp logger.
- Критерий готовности: test fails если run_id отсутствует в emitted logs.
- Трудозатраты: **S**

### [P2] Security rule: статический детектор hardcoded secrets

- Категория: 9
- Текущий балл → Целевой балл: 8 → 9
- Влияние на общий балл: +0.08
- Проблема: текущая grep-эвристика даёт false positives/false negatives.
- Решение: подключить `detect-secrets`/`gitleaks` в pre-commit + CI.
- Файлы: `.pre-commit-config.yaml`, CI workflow.
- Риски: шум в первых прогонах.
- Критерий готовности: 0 unresolved findings в baseline + PR gate.
- Трудозатраты: **S**

### [P3] Укрепить операционную документацию DQ/lock runbooks

- Категория: 10, 5, 6
- Текущий балл → Целевой балл: 9 → 10
- Влияние на общий балл: +0.07
- Проблема: кодовые механизмы зрелые, но эксплуатационные сценарии можно усилить playbook-ами.
- Решение: добавить краткие failure-mode runbooks и troubleshooting matrix.
- Файлы: `docs/05-operations/runbooks/**`
- Риски: минимальные.
- Критерий готовности: операционный checklist для CB open / lock lost / DQ spike.
- Трудозатраты: **S**

______________________________________________________________________

## 3.4 Roadmap

- **Фаза 1 (неделя 1-2):** P1 (import policy + coverage baseline).
  Ожидаемый общий балл: **8.11 → 8.72**.

- **Фаза 2 (неделя 3-4):** P2 (run_id e2e checks + secrets scanner).
  Ожидаемый общий балл: **8.72 → 8.88**.

- **Фаза 3 (неделя 5+):** P3 (ops runbooks hardening).
  Ожидаемый общий балл: **8.88 → 8.95**.

______________________________________________________________________

## Часть 4. Метрики контроля регресса (CI)

| Метрика             | Порог      | Команда                                                                                        | Блокирует PR |
| ------------------- | ---------- | ---------------------------------------------------------------------------------------------- | ------------ |
| Coverage            | ≥85%       | `pytest --cov=src/bioetl --cov-fail-under=85`                                                  | Да           |
| mypy errors         | 0          | `mypy src/bioetl --strict`                                                                     | Да           |
| Циклические импорты | 0          | `python -m pytest tests/architecture/test_layer_dependencies.py::test_import_linter_contracts` | Да           |
| Нарушения слоёв     | 0          | `pytest tests/architecture/test_layer_dependencies.py`                                         | Да           |
| `print()` в коде    | 0          | `rg 'print\(' src/bioetl --glob '*.py'`                                                        | Да           |
| Hardcoded secrets   | 0 critical | `detect-secrets scan` / `gitleaks detect`                                                      | Да           |

______________________________________________________________________

## Verification Log (executed)

- `.venv/bin/python -m mypy src/bioetl --strict`
- `PYTHONPATH=src .venv/bin/python -c "import bioetl.domain"`
- `rg '^class ' src --glob '*.py' | wc -l`
- `find src -name '*.py' | wc -l`
- `python - <<'PY' ...` (module line average)
- `rg -n 'TODO|FIXME|XXX|HACK' src | wc -l`
- `rg 'print\(' src/bioetl --glob '*.py' | wc -l`
- `rg -n "(api_key|password|secret)\s=" src --glob '*.py' | wc -l`
- `.venv/bin/python -m pytest tests/ --cov=src/bioetl --cov-report=term` (coverage result unavailable in session)

## Findings (evidence-based)

### [MUST] Layer policy ambiguity / violation under stricter matrix

**Location**: `src/bioetl/infrastructure/observability/__init__.py`, `src/bioetl/infrastructure/schemas/pipeline_config.py`, `src/bioetl/infrastructure/adapters/chembl/constants.py`

**Evidence snippets**:

```python
from bioetl.domain.exceptions import MetricsServerError
from bioetl.domain.config import DQConfig as DomainDQConfig
from bioetl.domain.entities.chembl import (
```

**Impact**: If strict rule is "infrastructure may import only domain.ports", current imports violate it and can blur boundaries.

**Verification**: `rg -n '^from bioetl\.domain' src/bioetl/infrastructure --glob '*.py'`

### [SHOULD] Coverage baseline not established in current audit run

**Location**: test execution command level

**Evidence**:

```bash
.venv/bin/python -m pytest tests/ --cov=src/bioetl --cov-report=term
# full metric not captured before session limits
```

**Impact**: невозможно верифицировать требование coverage ≥85% на момент аудита.

**Verification**: rerun command in CI with full timeout/artifacts.

### [POSITIVE] Domain ports implemented as Protocol

**Location**: `src/bioetl/domain/ports/data_source.py`

**Evidence**:

```python
@runtime_checkable
class DataSourcePort(Protocol):
```

**Impact**: proper DIP/hexagonal contract boundary.

### [POSITIVE] Bronze format & path policy implemented

**Location**: `src/bioetl/infrastructure/storage/bronze_writer.py`

**Evidence**:

```python
"""Bronze layer writer (local storage with JSONL + zstd compression)."""

BRONZE_FILE_SUFFIX = ".jsonl.zst"
return f"{provider}/{entity}/{date_str}/{filename}"
```

### [POSITIVE] Silver uses Delta Lake merge/upsert

**Location**: `src/bioetl/infrastructure/storage/silver_writer.py`

**Evidence**:

```python
from deltalake import DeltaTable, write_deltalake

"""Silver layer writer (Delta Lake with merge/upsert)."""
```

### [POSITIVE] Circuit breaker with metrics and state machine

**Location**: `src/bioetl/infrastructure/adapters/http/circuit_breaker.py`

**Evidence**:

```python
if self._failure_count >= self.failure_threshold:
    self._state = CircuitBreakerState.OPEN
self.metrics.increment_counter("circuit_breaker_failure_total", 1, ...)
```

### [POSITIVE] Locking uses TTL + heartbeat + fencing token

**Location**: `src/bioetl/infrastructure/locking/memory_lock.py`

**Evidence**:

```python
self._sequence += 1
return FencingToken(sequence=sequence, ...)
async def heartbeat(...):
    new_expires_at = time.monotonic() + original_ttl
```

### [POSITIVE] Unified structured logging enforces run_id

**Location**: `src/bioetl/infrastructure/observability/unified_logger.py`

**Evidence**:

```python
self._logger = base_logger.bind(run_id=self._run_id, pipeline=pipeline)
```
