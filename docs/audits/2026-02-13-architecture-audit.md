# Architecture Audit Report — BioETL

Date: 2026-02-13
Scope: `src/bioetl`, `tests/architecture`, `docs/00-project`

## 0) Входные документы и ограничения

- Прочитан `docs/00-project/agents/AGENT.md`.
- Прочитан `docs/00-project/RULES.md`.
- Запрошенные документы `01-domain-objects.md`, `02-etl-layers.md`, `03-data-flow.md`, `04-duplication-reduction.md`, `05-physical-layout.md` в репозитории не найдены (`[данные отсутствуют]`).

## 1) Объективные метрики

| Метрика                               | Команда/метод                                                                                           |                                                             Значение |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------: |
| Покрытие тестами                      | `.venv/bin/python -m pytest tests/ --cov=src/bioetl --cov-report=term`                                  | `[данные отсутствуют: полный прогон не завершён в отведённое время]` |
| Покрытие тестами (последний артефакт) | `python -c "import json; print(json.load(open("coverage.json"))["totals"]["percent_covered_display"])"` |                                                            `89.54 %` |
| Ошибки mypy                           | `mypy strict + подсчёт error`                                                                           |                                                                 `37` |
| Циклические импорты                   | `.venv/bin/python -c "from bioetl.domain import *" && echo pass`                                        |                                                               `pass` |
| Количество классов                    | `grep по pattern class в src/*.py`                                                                      |                                                                `887` |
| Количество файлов .py                 | `find src -name *.py`                                                                                   |                                                                `542` |
| Средний размер модуля (`src/bioetl`)  | `python rglob(*.py) + подсчёт строк`                                                                    |                                                       `222.08` строк |
| TODO/FIXME в коде                     | `grep TODO/FIXME/XXX/HACK в src/*.py`                                                                   |                                                                 `23` |
| Использование print()                 | `grep print( в src/bioetl/*.py`                                                                         |                                                                  `0` |
| Hardcoded secrets (heuristic)         | `grep api_key/password/secret assignments в src/*.py`                                                   |                                                                 `14` |

## 2) Проверки и findings по 10 категориям

### 2.1. Слоистая архитектура (вес 15%)

**Оценка: 4/10**

**Позитивные факты:**

- `domain` не импортирует `infrastructure`/`application` (проверка grep без совпадений).

**Нарушения (по строгой матрице из пользовательского аудиторского профиля):**

- В `infrastructure` есть прямые импорты из `domain` вне `domain.ports` (99 совпадений), например:
  - `src/bioetl/infrastructure/storage/silver_writer.py` → `from bioetl.domain.medallion ...`
  - `src/bioetl/infrastructure/locking/memory_lock.py` → `from bioetl.domain.locking import FencingToken`
  - `src/bioetl/infrastructure/adapters/chembl/client.py` → `from bioetl.domain.exceptions ...`

**Комментарий по интерпретации:**

- В рамках классического hexagonal такой импорт часто допустим (инфраструктура может использовать доменные типы), но в данном аудите применена именно заданная пользователем строгая матрица (`infrastructure -> domain` как violation, кроме `domain.ports`).

### 2.2. Контракты и Ports (вес 12%)

**Оценка: 7/10**

- Порты оформлены через `Protocol` в `domain/ports` (минимум 37 Protocol-контрактов).
- Есть явные реализации в infrastructure (`MemoryLock`, `StructlogLogger`, `PanderaSilverValidator`, `PanderaGoldValidator`).
- Но часть связей идёт напрямую на доменные модели/исключения вместо портов (см. категорию 1), что снижает оценку.

### 2.3. Medallion Architecture (вес 12%)

**Оценка: 8/10**

- Bronze: JSONL + zstd, append/atomic поведение реализовано (`bronze_writer.py`).
- Silver: Delta Lake + merge/upsert + VACUUM/retention (`silver_writer.py`).
- Gold: strict validation (Pandera strict), Delta write (`gold_writer.py`).
- Отклонение: в `bronze_writer` path format описан как `{provider}/{entity}/{date}` (без `v1`), что расходится с шаблоном из задания `bronze/v1/{provider}/{entity}/{date}/`.

### 2.4. Обработка ошибок и Circuit Breaker (вес 10%)

**Оценка: 9/10**

- Реализован CB state machine (CLOSED/OPEN/HALF_OPEN), порог 5 ошибок, timeout 300s.
- Есть метрики CB (`circuit_breaker_state`, `circuit_breaker_trips_total`).
- Классификация ошибок поддерживается доменными исключениями и error-handling адаптерами.

### 2.5. Блокировки и конкурентность (вес 10%)

**Оценка: 9/10**

- `MemoryLock` реализует acquire/release/heartbeat/owner validation/fencing token.
- TTL + heartbeat присутствуют; есть safety-guard методы `validate_owner`/`validate_fencing_token`.
- Параметры локального деплоя (TTL 90, heartbeat 30) централизованы в runtime config.

### 2.6. Валидация и DQ (вес 10%)

**Оценка: 9/10**

- DQ thresholds 5%/20% заданы в `DQConfig`.
- Quarantine реализован как unified Delta table с purge/replay/statistics.
- Pandera-валидаторы для Silver/Gold присутствуют.
- Content hash реализован через `IdentityService` и canonical normalization.

### 2.7. Логирование и наблюдаемость (вес 8%)

**Оценка: 8/10**

- `UnifiedLogger` с обязательным `run_id`, JSON/console configuration через structlog.
- Метрики Prometheus присутствуют (`infrastructure/observability/metrics.py`).
- `print()` в `src/bioetl` отсутствует.

### 2.8. Тестирование (вес 8%)

**Оценка: 8/10**

- Архитектурные/контрактные/e2e тесты представлены массово (11k+ collected).
- В `pytest.ini` выставлен `--cov-fail-under=85`.
- Полный прогон в текущей сессии не завершён; есть точечные проблемы окружения/инструментов (см. verification log).

### 2.9. Безопасность и секреты (вес 8%)

**Оценка: 6/10**

- PII hashing с salt реализован (`Sha256PiiHasher`, env-driven salts, rotation flags).
- Heuristic grep обнаружил 14 присваиваний по шаблону `api_key|password|secret` — требуется ручной triage.
- Архитектурный тест `test_no_hardcoded_secrets` падает в окружении из-за отсутствия `detect_secrets` пакета, поэтому автоматическая верификация секрета в этой сессии неполная.

### 2.10. Документация и сопровождаемость (вес 7%)

**Оценка: 8/10**

- Есть `CHANGELOG.md`, ADR-реестр, развитый блок docs.
- Отдельные документы, запрошенные в задаче (`01..05`), в текущем репозитории отсутствуют.

## 3) Сводная оценка

| #         | Категория                       |      Вес | Оценка |   Взвеш. балл | Ключевые находки                                      |
| --------- | ------------------------------- | -------: | -----: | ------------: | ----------------------------------------------------- |
| 1         | Слоистая архитектура            |      15% |      4 |          0.60 | 99 импортов `infrastructure -> domain(!=ports)`       |
| 2         | Контракты и Ports               |      12% |      7 |          0.84 | 37 Protocol, но есть прямые доменные зависимости      |
| 3         | Medallion Architecture          |      12% |      8 |          0.96 | Bronze/Silver/Gold реализованы; path mismatch по `v1` |
| 4         | Ошибки и Circuit Breaker        |      10% |      9 |          0.90 | CB + метрики, threshold=5, recovery=300               |
| 5         | Блокировки и конкурентность     |      10% |      9 |          0.90 | lock + heartbeat + fencing + safety guard             |
| 6         | Валидация и DQ                  |      10% |      9 |          0.90 | Pandera + Quarantine + thresholds + content hash      |
| 7         | Логирование/наблюдаемость       |       8% |      8 |          0.64 | UnifiedLogger + run_id + metrics                      |
| 8         | Тестирование                    |       8% |      8 |          0.64 | Тестов много, gate 85%, полный прогон не завершён     |
| 9         | Безопасность и секреты          |       8% |      6 |          0.48 | PII salted ok, secret-scan в окружении неполон        |
| 10        | Документация и сопровождаемость |       7% |      8 |          0.56 | ADR/CHANGELOG есть, часть документов отсутствует      |
| **Итого** |                                 | **100%** |        | **7.42 / 10** |                                                       |

### Интерпретация общего балла

**7.42 / 10** → «Требуется рефакторинг, но система работоспособна».

## 4) План рефакторинга

### [P1] Формализация матрицы импортов и устранение спорных пересечений

- **Категория**: 1, 2
- **Текущий балл → Целевой балл**: 4 → 8
- **Влияние на общий балл**: +0.60
- **Проблема**: 99 импортов `infrastructure -> domain(!=ports)` при строгом профиле аудита.
- **Решение**:
  1. Утвердить единый policy (ADR): разрешены ли доменные типы в infrastructure.
  1. Если нет — ввести DTO/ports-only адаптацию.
  1. Добавить статическую CI-проверку на запрещённые импорты.
- **Файлы**: `src/bioetl/infrastructure/**`, `tests/architecture/*layer*`, `docs/adr/*`.
- **Риски**: масштабный рефакторинг сигнатур, каскадные изменения типов.
- **Критерий готовности**: 0 нарушений новой формальной матрицы.
- **Трудозатраты**: L.

### [P1] Восстановить security gate `detect-secrets` в CI/локальном env

- **Категория**: 9, 8
- **Текущий балл → Целевой балл**: 6 → 8
- **Влияние на общий балл**: +0.16
- **Проблема**: архитектурный тест секрета падает из-за отсутствия модуля `detect_secrets`.
- **Решение**: добавить/зафиксировать зависимость, проверить baseline/правила исключений.
- **Файлы**: `pyproject.toml`, `requirements*.txt`, `tests/architecture/test_antipatterns.py`.
- **Риски**: ложноположительные срабатывания в CI.
- **Критерий готовности**: тест `test_no_hardcoded_secrets` стабильно pass.
- **Трудозатраты**: S.

### [P2] Нормализация Bronze path contract (`v1`)

- **Категория**: 3
- **Текущий балл → Целевой балл**: 8 → 9
- **Влияние на общий балл**: +0.12
- **Проблема**: фактический шаблон пути Bronze не фиксирует `v1`.
- **Решение**: стандартизовать path builder + миграционный shim.
- **Файлы**: `src/bioetl/infrastructure/storage/bronze_writer.py`, storage config, integration tests.
- **Риски**: совместимость старых данных/путей.
- **Критерий готовности**: запись/чтение через новый path pattern + backward compatibility tests.
- **Трудозатраты**: M.

### [P2] Закрыть mypy strict debt

- **Категория**: 2, 10
- **Текущий балл → Целевой балл**: 7 → 8
- **Влияние на общий балл**: +0.12
- **Проблема**: 37 mypy errors.
- **Решение**: устранить ошибки приоритезированно по слоям (domain→application→infrastructure).
- **Файлы**: согласно `/tmp/mypy_bioetl.txt`.
- **Риски**: исправления типов могут вскрыть runtime дефекты.
- **Критерий готовности**: `mypy --strict` = 0 errors.
- **Трудозатраты**: M.

### [P3] Точечная чистка TODO/FIXME + единообразие formatter

- **Категория**: 10, 8
- **Текущий балл → Целевой балл**: 8 → 9
- **Влияние на общий балл**: +0.07
- **Проблема**: 23 TODO/FIXME, `ruff format --check` указывает минимум 1 файл.
- **Решение**: triage TODO + приведение к formatter policy.
- **Файлы**: `src/**`, в т.ч. `src/bioetl/infrastructure/storage/gold_writer.py`.
- **Риски**: низкие.
- **Критерий готовности**: `ruff format --check src` pass, TODO backlog классифицирован.
- **Трудозатраты**: S.

## 5) Roadmap

- **Фаза 1 (неделя 1-2)**: оба P1 пункта (import policy + detect-secrets gate).
  - Ожидаемый балл: **7.42 → ~8.18**.
- **Фаза 2 (неделя 3-4)**: P2 пункты (Bronze path contract + mypy debt).
  - Ожидаемый балл: **~8.18 → ~8.42**.
- **Фаза 3 (неделя 5+)**: P3 улучшения (TODO/format/doc hygiene).
  - Ожидаемый балл: **~8.42 → ~8.49**.

## 6) CI метрики контроля регресса

| Метрика                          |     Порог | Команда                                                                  | Блокирует PR |
| -------------------------------- | --------: | ------------------------------------------------------------------------ | ------------ |
| Coverage                         |      ≥85% | `.venv/bin/python -m pytest tests/ --cov=src/bioetl --cov-fail-under=85` | Да           |
| mypy errors                      |         0 | `.venv/bin/python -m mypy src/bioetl --strict`                           | Да           |
| Циклические импорты domain       |         0 | `.venv/bin/python -c "from bioetl.domain import *"`                      | Да           |
| Нарушения слоёв (strict profile) |         0 | `rg "^from bioetl\\.domain\\.(?!ports)" src/bioetl/infrastructure -P`    | Да           |
| print() в коде                   |         0 | `grep -r "print(" src/bioetl --include="*.py"`                           | Да           |
| detect-secrets availability      | installed | `.venv/bin/python -m detect_secrets --version`                           | Да           |

## 7) Verification log (executed commands)

```bash
.venv/Scripts/python.exe -m pytest tests/ --cov=src/bioetl --cov-report=term
.venv/bin/python -m pytest tests/ --cov=src/bioetl --cov-report=term
.venv/bin/python -m mypy src/bioetl --strict 2>&1 | rg -c "error:"
.venv/bin/python -c "from bioetl.domain import *"
grep -r "^class " src/ --include="*.py" | wc -l
find src/ -name "*.py" | wc -l
python - <<'PY' ... average module size ... PY
grep -rE "(TODO|FIXME|XXX|HACK)" src/ --include="*.py" | wc -l
grep -r "print(" src/bioetl --include="*.py" | wc -l
grep -rE "(api_key|password|secret)\s*=" src/ --include="*.py" | wc -l
grep -r "from bioetl.infrastructure" src/bioetl/domain/ --include='*.py'
grep -r "from bioetl.application" src/bioetl/domain/ --include='*.py'
rg "^from bioetl\.domain\.(?!ports)|^import bioetl\.domain\.(?!ports)" src/bioetl/infrastructure -P -n
.venv/bin/python -m pytest tests/architecture/test_antipatterns.py::test_no_hardcoded_secrets -q
.venv/bin/python -m pytest tests/architecture/test_code_formatting.py::TestCodeFormatting::test_ruff_formatting_src -q
```
