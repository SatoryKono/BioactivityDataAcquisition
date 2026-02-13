# Архитектурный аудит BioETL

Дата: 2026-02-13
Область: `src/bioetl`, `tests`, проектная документация из `docs/00-project/*`

## 0) Проверка входных документов

Запрошенные файлы `01-domain-objects.md`, `02-etl-layers.md`, `03-data-flow.md`, `04-duplication-reduction.md`, `05-physical-layout.md` в `docs/00-project/` отсутствуют. Использованы доступные артефакты архитектуры: `docs/00-project/RULES.md`, `docs/00-project/agents/AGENT.md`, профильные ADR и модули в `src/bioetl`.
Статус: **[данные отсутствуют для части исходного списка документов]**.

## 1) Объективные метрики

- Покрытие тестами: `python -m pytest tests/ --cov=src/bioetl --cov-report=term` -> \[данные отсутствуют: запуск остановлен `ModuleNotFoundError: pandas`\].
- Ошибки mypy: `mypy src/bioetl --strict 2>&1 | grep -c "error:"` -> **56 шт.**
- Циклические импорты: `PYTHONPATH=src python -c "from bioetl.domain import *"` -> **fail** (`ModuleNotFoundError: pandera`).
- Количество классов: `grep -r "^class " src/ --include="*.py" | wc -l` -> **887 шт.**
- Количество файлов `.py`: `find src/ -name "*.py" | wc -l` -> **542 шт.**
- Средний размер модуля (`src/bioetl`): `ΣLOC/кол-во .py` -> **221.08 строк**.
- TODO/FIXME/XXX/HACK: `grep -rE "(TODO|FIXME|XXX|HACK)" src/ | wc -l` -> **23 шт.**
- Использование `print()`: `grep -r "print(" src/bioetl --include="*.py" | wc -l` -> **0 шт.**
- Hardcoded secrets (regex-метрика): `grep -rE "(api_key|password|secret)\s*=" src/ | wc -l` -> **14 совпадений** (само по себе не доказывает hardcode).

## 2) Оценка по 10 категориям

### 1. Соблюдение слоистой архитектуры — **3/10** (вес 15%)

**Ключевое нарушение (MUST):** `infrastructure -> domain` не ограничено только портами. Обнаружено 99 импортов из `bioetl.domain.*` вне `domain.ports` (пример ниже).
Проверка домена на импорт `infrastructure/application` и `application` на импорт `interfaces` — нарушений не найдено.

**Примеры:**

- `src/bioetl/infrastructure/locking/memory_lock.py` импортирует `bioetl.domain.locking` и `bioetl.domain.types`.
- `src/bioetl/infrastructure/adapters/pubchem/client.py` импортирует `bioetl.domain.entities.pubchem`.
- `src/bioetl/infrastructure/schemas/pipeline_config.py` импортирует `bioetl.domain.config`.

### 2. Контракты и Ports — **8/10** (вес 12%)

**Позитив:** слой `domain/ports` насыщен Protocol-контрактами (`LockPort`, `StoragePort`, `CircuitBreakerPort`, `DQ*Port`, `LoggerPort`, и др.).
**Риск:** при наличии 99 прямых `infrastructure -> domain.*` импортов зависимость от портов не является единственным способом интеграции.

### 3. Medallion Architecture — **8/10** (вес 12%)

**Позитив:**

- Bronze: JSONL + zstd задекларирован и реализуется в `bronze_writer.py`.
- Silver/Gold: используются `write_deltalake(...)`, есть vacuum/retention.

**Отклонение:** путь Bronze собирается как `{provider}/{entity}/{date}/{filename}` (без `v1` сегмента, указанного в критерии аудита).

### 4. Обработка ошибок и Circuit Breaker — **9/10** (вес 10%)

**Позитив:**

- Circuit Breaker реализован как state machine (CLOSED/OPEN/HALF_OPEN).
- Порог 5 и timeout 300s соблюдаются по умолчанию.
- Есть метрики состояния и trips.

**Замечание:** репозиторий большой; полноту классификации всех ошибок (Critical/Recoverable/DQ) нужно дополнительно валидировать end-to-end по всем пайплайнам.

### 5. Блокировки и конкурентность — **10/10** (вес 10%)

**Позитив:**

- `MemoryLock` реализует TTL-locking, heartbeat, `validate_owner` (safety guard), `validate_fencing_token`.
- Runtime defaults: heartbeat 30s, lock_ttl 90s (через `effective_lock_ttl = heartbeat * 3`).

### 6. Валидация и DQ — **9/10** (вес 10%)

**Позитив:**

- Pandera-schema usage в domain-схемах и валидаторах.
- Unified Quarantine реализован в Delta-таблице.
- Content hash формализован через `compute_content_hash(...)` с делегацией в identity service.

**Риск:** mypy-ошибки (56) концентрируются в schema/validation зоне, что снижает строгую гарантию корректности типовых контрактов.

### 7. Логирование и наблюдаемость — **8/10** (вес 8%)

**Позитив:**

- `UnifiedLogger` с обязательным `run_id`.
- Prometheus-style метрики присутствуют.
- `print()` в `src/bioetl` не используется.

**Замечание:** в кодовой базе сосуществуют несколько logging-обёрток (`UnifiedLogger`, `StructlogLogger`), что повышает риск рассинхронизации практик.

### 8. Тестирование — **6/10** (вес 8%)

**Позитив:**

- Есть архитектурные тесты (`tests/architecture`: 49 файлов).
- Активно используется VCR в e2e.

**Блокер оценки coverage:** `pytest --cov` не стартует из-за отсутствия `pandas` в окружении, поэтому целевой KPI ≥85% не подтверждён.

### 9. Безопасность и секреты — **8/10** (вес 8%)

**Позитив:**

- По grep нет прямых доказательств захардкоженных секретов в виде литералов; встречаются в основном прокидывания `api_key` из конфигурации/env.

**Замечание:** метрика по regex даёт 14 совпадений, но это индикатор мест работы с секретами, а не автоматически уязвимость.

### 10. Документация и сопровождаемость — **8/10** (вес 7%)

**Позитив:**

- Есть RULES, ADR-пакет, CHANGELOG, runbook’и, архитектурные диаграммы.
- Большая доля модулей снабжена подробными docstring.

**Пробел:** часть запрошенных входных документов аудита отсутствует в текущей структуре `docs/00-project/`.

## 3) Сводная таблица

| #         | Категория                       |      Вес | Оценка | Взвеш. балл | Ключевые находки                                                |
| --------- | ------------------------------- | -------: | -----: | ----------: | --------------------------------------------------------------- |
| 1         | Слоистая архитектура            |      15% |      3 |        0.45 | 99 импортов `infrastructure -> domain.*` вне ports              |
| 2         | Контракты и Ports               |      12% |      8 |        0.96 | Protocol-слой развит, но не единственный вектор зависимостей    |
| 3         | Medallion Architecture          |      12% |      8 |        0.96 | Bronze JSONL+zstd, Silver/Gold Delta; path-отклонение по `v1`   |
| 4         | Ошибки и Circuit Breaker        |      10% |      9 |        0.90 | CB state machine + метрики                                      |
| 5         | Блокировки и конкурентность     |      10% |     10 |        1.00 | MemoryLock + heartbeat + fencing + safety guard                 |
| 6         | Валидация и DQ                  |      10% |      9 |        0.90 | Pandera + Quarantine + content hash                             |
| 7         | Логирование и наблюдаемость     |       8% |      8 |        0.64 | UnifiedLogger + metrics, print=0                                |
| 8         | Тестирование                    |       8% |      6 |        0.48 | VCR/архитектурные тесты есть, coverage не измерен в текущем env |
| 9         | Безопасность и секреты          |       8% |      8 |        0.64 | Hardcoded literals не подтверждены                              |
| 10        | Документация и сопровождаемость |       7% |      8 |        0.56 | ADR/RULES/CHANGELOG в наличии                                   |
| **Итого** |                                 | **100%** |        |    **7.49** |                                                                 |

## 3.2 Интерпретация общего балла

**7.49 / 10** → *Требуется рефакторинг, но система работоспособна*.

## 3.3 План рефакторинга

### [P1] Ограничить `infrastructure -> domain` до ports/VO-контрактов

**Категория**: 1 (Слоистая архитектура)
**Текущий балл → Целевой балл**: 3 → 8
**Влияние на общий балл**: +0.75

**Проблема**: 99 прямых импортов `bioetl.domain.*` в инфраструктуре вне `domain.ports`.
**Решение**: вынести пересекаемые типы/DTO в контрактные пакеты (`domain.ports`, `application.contracts`), адаптеры завязать на протоколы и транспортные DTO.
**Файлы**: `src/bioetl/infrastructure/**/*`, `src/bioetl/domain/ports/**/*`, `src/bioetl/composition/**/*`.
**Риски**: каскадные правки DI, regressions в адаптерах провайдеров.
**Критерий готовности**: `rg --pcre2 '^from bioetl\.domain\.(?!ports)' src/bioetl/infrastructure -g '*.py'` -> 0.
**Трудозатраты**: L (1-2 недели).

### [P1] Восстановить воспроизводимый quality-gate окружения (pytest/mypy)

**Категория**: 8 (Тестирование), 6 (DQ/валидация)
**Текущий балл → Целевой балл**: 6 → 8
**Влияние на общий балл**: +0.16

**Проблема**: нельзя посчитать coverage в текущем окружении (нет `pandas`), а strict mypy даёт 56 ошибок.
**Решение**: фикс зависимостей dev-окружения + план устранения mypy-ошибок по пакетам (`domain/schemas`, `contracts/gold`, storage).
**Файлы**: `pyproject.toml`, `tests/conftest.py`, `src/bioetl/domain/schemas/**/*`, `src/bioetl/domain/contracts/**/*`.
**Риски**: временный рост времени CI.
**Критерий готовности**: coverage >=85%, `mypy --strict` -> 0 errors.
**Трудозатраты**: M (3-5 дней).

### [P2] Нормализовать path policy для Bronze (`v1` сегмент)

**Категория**: 3 (Medallion)
**Текущий балл → Целевой балл**: 8 → 9
**Влияние на общий балл**: +0.12

**Проблема**: текущий path `provider/entity/date` не включает ожидаемый `bronze/v1/...`.
**Решение**: добавить версионируемый namespace path (с миграционной совместимостью чтения старых путей).
**Файлы**: `src/bioetl/infrastructure/storage/bronze_writer.py`, `src/bioetl/infrastructure/storage/bronze_reader.py` (если есть), конфиги путей.
**Риски**: breaking changes в downstream readers.
**Критерий готовности**: новые файлы пишутся в `bronze/v1/{provider}/{entity}/{date}/`.
**Трудозатраты**: M (2-3 дня).

### [P3] Унифицировать logging API (единый фасад)

**Категория**: 7 (Логирование)
**Текущий балл → Целевой балл**: 8 → 9
**Влияние на общий балл**: +0.08

**Проблема**: сосуществование нескольких логгер-адаптеров усложняет стандартизацию событий.
**Решение**: оставить один публичный logging facade и утвердить архитектурным тестом.
**Файлы**: `src/bioetl/infrastructure/observability/*`, `tests/architecture/*`.
**Риски**: minor изменения в форматах логов.
**Критерий готовности**: архитектурный тест запрещает прямое создание альтернативного logger вне фасада.
**Трудозатраты**: S (1-2 дня).

## 3.4 Roadmap

- **Фаза 1 (неделя 1-2)**: P1 задачи (границы слоёв + quality-gate).
  Ожидаемый общий балл: **7.49 → 8.40**.
- **Фаза 2 (неделя 3-4)**: P2 (Bronze path policy + миграция).
  Ожидаемый общий балл: **8.40 → 8.52**.
- **Фаза 3 (неделя 5+)**: P3 (унификация logging facade).
  Ожидаемый общий балл: **8.52 → 8.60**.

## 4) Метрики контроля регресса (CI)

- Coverage >=85%: `pytest --cov=src/bioetl --cov-fail-under=85` (блокирует PR: Да).
- mypy errors =0: `mypy src/bioetl --strict` (блокирует PR: Да).
- Циклические импорты =0: `PYTHONPATH=src python -c "from bioetl.domain import *"` + скрипт import graph (блокирует PR: Да).
- Нарушения слоёв =0: `rg --pcre2 '^from bioetl\.domain\.(?!ports)' src/bioetl/infrastructure -g '*.py'` (блокирует PR: Да).
- Domain->infra/app =0: `rg -n '^from bioetl\.(infrastructure|application)' src/bioetl/domain -g '*.py'` (блокирует PR: Да).
- Application->interfaces =0: `rg -n '^from bioetl\.interfaces' src/bioetl/application -g '*.py'` (блокирует PR: Да).
- `print()` в коде =0: `rg -n 'print\(' src/bioetl -g '*.py'` (блокирует PR: Да).
- Hardcoded secret literals =0: semgrep/ruleset на `="..."` для secret-patterns (блокирует PR: Да).

## Приложение: минимальные подтверждающие фрагменты

1. Layer boundary issue (пример): `src/bioetl/infrastructure/locking/memory_lock.py`:

```python
from bioetl.domain.locking import FencingToken
from bioetl.domain.types import RunID
```

2. Bronze path policy:

```python
return f"{provider}/{entity}/{date_str}/{filename}"
```

3. Circuit Breaker defaults:

```python
failure_threshold: int = 5
recovery_timeout: int = 300
```

4. Safety Guard / lock ownership:

```python
async def validate_owner(self, key: str, owner_id: RunID) -> bool:
```
