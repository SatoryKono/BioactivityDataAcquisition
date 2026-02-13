# Architecture Audit Report

Date: 2026-02-13
Scope: `src/bioetl/**`, `tests/**`, `docs/00-project/**`

## Контекст проверки входных документов

- Прочитан: `docs/00-project/agents/AGENT.md`.
- Прочитан: `docs/00-project/RULES.md`.
- Запрошенные документы `01-domain-objects.md`, `02-etl-layers.md`, `03-data-flow.md`, `04-duplication-reduction.md`, `05-physical-layout.md` в репозитории не найдены (поиск по `docs/`).

## Часть 1. Объективные метрики

| Метрика                        | Команда/метод                                                                  | Значение                                                            |
| ------------------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------------------- |
| Покрытие тестами               | `.venv/Scripts/python.exe -m pytest tests/ --cov=src/bioetl --cov-report=term` | [данные отсутствуют: путь Windows не существует в Linux контейнере] |
| Покрытие тестами (proxy)       | `python - <<PY ... coverage.json ... PY`                                       | `89.54%`                                                            |
| Ошибки mypy                    | `mypy src/bioetl --strict 2>&1` + `rg -c 'error:'`                             | `39`                                                                |
| Циклические импорты            | `PYTHONPATH=src python -c "from bioetl.domain import *"`                       | `fail` (импорт падает на `ModuleNotFoundError: pandera`)            |
| Количество классов             | `rg '^class ' src/ --glob '*.py' \| wc -l`                                     | `884`                                                               |
| Количество файлов .py          | `find src/ -name '*.py' \| wc -l`                                              | `533`                                                               |
| Средний размер модуля          | Python-скрипт (sum(lines)/count) для `src/bioetl/**/*.py`                      | `223.38` строк                                                      |
| TODO/FIXME в коде              | \`rg -n -e '(TODO                                                              | FIXME                                                               |
| Использование print()          | `rg 'print\(' src/bioetl --glob '*.py' \| wc -l`                               | `0`                                                                 |
| Hardcoded secrets (regex hits) | \`rg -n -e '(api_key                                                           | password                                                            |

______________________________________________________________________

## Часть 2. Оценка по 10 категориям

## [MUST] 1. Соблюдение слоистой архитектуры — **9/10**

**Проверка границ (по критерию задачи):**

- `domain -> infrastructure`: не обнаружено.
- `domain -> application`: не обнаружено.
- `application -> interfaces`: не обнаружено.

**Доказательства (позитивные):**

- Поиск запрещённых импортов не дал совпадений для `src/bioetl/domain/**` и `src/bioetl/application/**`.

**Наблюдение (контекст):**

- В `infrastructure` есть активные импорты из `domain` (не только `ports`), например `bioetl.domain.entities`, `bioetl.domain.config`.
  - `src/bioetl/infrastructure/adapters/chembl/client.py:19-37`
  - `src/bioetl/infrastructure/config/_base.py:34-36`
  - `src/bioetl/infrastructure/checkpoint/local_checkpoint.py:27-28`

**Влияние:**

- По матрице из задания эта связь может трактоваться как нарушение; по текущему коду она используется системно.

**Verification:**

- `rg -n '^(from|import) bioetl\.infrastructure' src/bioetl/domain`
- `rg -n '^(from|import) bioetl\.application' src/bioetl/domain`
- `rg -n '^(from|import) bioetl\.interfaces' src/bioetl/application`

______________________________________________________________________

## [SHOULD] 2. Контракты и Ports — **6/10**

**Позитив:**

- Порты оформлены через `Protocol` в `domain/ports`, напр. `StoragePort`, `LockPort`.
  - `src/bioetl/domain/ports/storage.py:31`
  - `src/bioetl/domain/ports/locking.py:14`

**Нарушения/риск:**

- В `infrastructure` 97 импортов `bioetl.domain.*` вне `ports` (по строгой трактовке hex-границ из пользовательского промпта).
  - Пример: `src/bioetl/infrastructure/adapters/chembl/client.py:19-37`
  - Пример: `src/bioetl/infrastructure/config/_base.py:34-36`

**Verification:**

- `rg -n --pcre2 '^(from|import) bioetl\.domain\.(?!ports\b)' src/bioetl/infrastructure --glob '*.py' | wc -l`

______________________________________________________________________

## [SHOULD] 3. Medallion Architecture — **9/10**

**Доказательства:**

- Bronze: JSONL + zstd описано и реализовано в writer.
  - `src/bioetl/infrastructure/storage/bronze_writer.py:1-16`
- Silver: Delta Lake writer.
  - `src/bioetl/infrastructure/storage/silver_writer.py` (использование DeltaWriter по модулю)
- Gold: strict validation (`schema strict=True` проверяется), поддержка SCD2.
  - `src/bioetl/infrastructure/storage/gold_writer.py:214-233`

**Отклонение:**

- Формально путь Bronze в docstring `bronze/{provider}/{entity}/{date}` без явного `v1`.

______________________________________________________________________

## [SHOULD] 4. Обработка ошибок и Circuit Breaker — **9/10**

**Доказательства:**

- Circuit breaker с порогом 5, timeout 300s, состояниями CLOSED/OPEN/HALF_OPEN.
  - `src/bioetl/infrastructure/adapters/http/circuit_breaker.py:67-69`
  - `src/bioetl/infrastructure/adapters/http/circuit_breaker.py:116-126`
- Метрики CB (`state`, `trips_total`) эмитятся.
  - `src/bioetl/infrastructure/adapters/http/circuit_breaker.py:93-109`

______________________________________________________________________

## [SHOULD] 5. Блокировки и конкурентность — **8/10**

**Доказательства:**

- `MemoryLock` с TTL, фоновым проверяющим циклом и heartbeat.
  - `src/bioetl/infrastructure/locking/memory_lock.py:43-64`
  - `src/bioetl/infrastructure/locking/memory_lock.py:186-214`
- Lock TTL/heartbeat по дефолту 90/30.
  - `src/bioetl/application/core/config.py:53-57`
- Safety guard через `validate_owner` присутствует.
  - `src/bioetl/domain/ports/locking.py:76-96`

**Ограничение:**

- Fencing token в явном виде не обнаружен.

______________________________________________________________________

## [SHOULD] 6. Валидация и DQ — **8/10**

**Доказательства:**

- DQ thresholds 5%/20% зафиксированы в схеме.
  - `src/bioetl/infrastructure/schemas/dq_config.py:57-68`
- Quarantine реализован в единой Delta-таблице.
  - `src/bioetl/infrastructure/quarantine/unified.py:39-47`
  - `src/bioetl/infrastructure/quarantine/unified.py:115-130`
- Content hash с нормализацией/исключением meta-полей.
  - `src/bioetl/domain/transformations.py:85-100`
  - `src/bioetl/domain/transformations.py:112-120`

**Риск:**

- mypy strict в DQ/Schema модулях падает (часть схем не типобезопасна).

______________________________________________________________________

## [SHOULD] 7. Логирование и наблюдаемость — **9/10**

**Доказательства:**

- UnifiedLogger с обязательными `run_id` и `pipeline`.
  - `src/bioetl/infrastructure/observability/unified_logger.py:1-8`
  - `src/bioetl/infrastructure/observability/unified_logger.py:97-103`
- Prometheus adapter реализован.
  - `src/bioetl/infrastructure/observability/prometheus_metrics.py:68-107`
- `print()` в `src/bioetl` не обнаружен.

______________________________________________________________________

## [SHOULD] 8. Тестирование — **6/10**

**Доказательства:**

- Репозиторий содержит обширные architecture/integration tests.
- Локально: `tests/architecture/test_code_formatting.py` падает (ruff format/isort).
  - `src/bioetl/__init__.py`
  - `src/bioetl/infrastructure/adapters/pubmed/_fetch.py`
  - `src/bioetl/infrastructure/storage/gold_writer.py`

**Ограничения данных:**

- Полный запуск `pytest tests/ --cov=...` не завершён в рамках аудита.
- Команда пользователя с Windows-интерпретатором не применима в текущем Linux-окружении.

______________________________________________________________________

## [SHOULD] 9. Безопасность и секреты — **7/10**

**Позитив:**

- PII hashing с salt и поддержкой rotation.
  - `src/bioetl/infrastructure/security/pii_hasher.py:77-100`
  - `src/bioetl/infrastructure/security/pii_hasher.py:185-187`

**Риск/замечание:**

- Regex-метрика дала 14 срабатываний по `api_key/password/secret`, но это в основном переменные/параметры, а не literal secrets.
  - `src/bioetl/infrastructure/adapters/semanticscholar/fallback.py:73`
  - `src/bioetl/composition/providers/registration.py:235-239`

______________________________________________________________________

## [SHOULD] 10. Документация и сопровождаемость — **8/10**

**Позитив:**

- В проекте есть актуальные ADR и архитектурная документация.
- В коде много docstring для портов/инфраструктурных сервисов.

**Пробелы:**

- Пять запрошенных документов (01/02/03/04/05) отсутствуют по указанным именам.

______________________________________________________________________

## Часть 3. Сводная таблица

| #         | Категория                       |      Вес | Оценка |   Взвеш. балл | Ключевые находки                                        |
| --------- | ------------------------------- | -------: | -----: | ------------: | ------------------------------------------------------- |
| 1         | Слоистая архитектура            |      15% |      9 |          1.35 | Прямых нарушений domain→infra/app не найдено            |
| 2         | Контракты и Ports               |      12% |      6 |          0.72 | Порты есть, но много infra→domain non-port импортов     |
| 3         | Medallion Architecture          |      12% |      9 |          1.08 | Bronze JSONL+zstd, Silver/Gold через Delta/strict       |
| 4         | Ошибки и Circuit Breaker        |      10% |      9 |          0.90 | CB с threshold=5, timeout=300, метрики есть             |
| 5         | Блокировки и конкурентность     |      10% |      8 |          0.80 | MemoryLock+heartbeat+safety guard, fencing не выявлен   |
| 6         | Валидация и DQ                  |      10% |      8 |          0.80 | thresholds 5/20, quarantine, content hash               |
| 7         | Логирование и observability     |       8% |      9 |          0.72 | UnifiedLogger + Prometheus, print=0                     |
| 8         | Тестирование                    |       8% |      6 |          0.48 | Formatting tests fail; full coverage run не завершён    |
| 9         | Безопасность и секреты          |       8% |      7 |          0.56 | Salted hashing ок; regex hits требуют ревью             |
| 10        | Документация и сопровождаемость |       7% |      8 |          0.56 | ADR/docstrings есть, часть ожидаемых файлов отсутствует |
| **Итого** |                                 | **100%** |        | **7.97 / 10** |                                                         |

### 3.2 Интерпретация общего балла

**7.97/10** — *Требуется рефакторинг, но система работоспособна* (верхняя граница диапазона 6.0–7.9).

### 3.3 План рефакторинга

### [P1] Нормализовать import-границы infrastructure ↔ domain

**Категория**: 1, 2
**Текущий балл → Целевой балл**: 9/6 → 10/9
**Влияние на общий балл**: +0.7

**Проблема**: массовые `infrastructure -> domain(non-ports)` импорты.
**Решение**: оставить в domain только Protocol/VO/DTO-контракты, вынести infra-specific маппинг/типы в adapter-local DTO.
**Файлы**: `src/bioetl/infrastructure/adapters/chembl/client.py`, `src/bioetl/infrastructure/config/_base.py`, смежные адаптеры.
**Риски**: каскадные изменения сигнатур, регресс в сериализации.
**Критерий готовности**: `rg`-проверка non-port импортов = 0; architecture tests зелёные.
**Трудозатраты**: L (1-2 недели).

### [P1] Починить архитектурные formatting-gates

**Категория**: 8
**Текущий балл → Целевой балл**: 6 → 8
**Влияние на общий балл**: +0.16

**Проблема**: `tests/architecture/test_code_formatting.py` падает.
**Решение**: применить `ruff format src tests` и `ruff check --fix` для импортов.
**Файлы**: минимум `src/bioetl/__init__.py`, `src/bioetl/infrastructure/adapters/pubmed/_fetch.py`, `src/bioetl/infrastructure/storage/gold_writer.py`, `tests/...`.
**Риски**: минимальные (только форматирование).
**Критерий готовности**: тест `test_code_formatting.py` проходит.
**Трудозатраты**: S (часы).

### [P2] Закрыть mypy --strict до 0

**Категория**: 6, 8
**Текущий балл → Целевой балл**: 8/6 → 9/8
**Влияние на общий балл**: +0.36

**Проблема**: 39 ошибок strict typing.
**Решение**: типизировать Pandera декораторы, убрать redundant cast, исправить arg-type несовместимости.
**Файлы**: `src/bioetl/domain/schemas/uniprot/*.py`, `src/bioetl/application/core/preflight_service.py`, `src/bioetl/composition/factories/services_factory.py`, и др.
**Риски**: изменение контрактов и узких мест runtime валидации.
**Критерий готовности**: `mypy src/bioetl --strict` → 0 errors.
**Трудозатраты**: M (2-4 дня).

### [P3] Уточнить и синхронизировать архитектурные документы

**Категория**: 10
**Текущий балл → Целевой балл**: 8 → 9
**Влияние на общий балл**: +0.07

**Проблема**: отсутствуют запрошенные документы по именам.
**Решение**: добавить mapping-файл «старое имя → актуальный путь» или создать недостающие docs-обёртки.
**Файлы**: `docs/00-project/index.md`, `docs/00-project/00-map.md`, новые alias-документы.
**Риски**: низкие.
**Критерий готовности**: все ссылки в инструкциях резолвятся.
**Трудозатраты**: S.

### 3.4 Roadmap

- **Фаза 1 (неделя 1-2)**: P1 (import boundaries + formatting gates). Ожидаемый общий балл: **~8.4**.
- **Фаза 2 (неделя 3-4)**: P2 (mypy strict cleanup). Ожидаемый общий балл: **~8.8**.
- **Фаза 3 (неделя 5+)**: P3 (doc sync, оптимизация). Ожидаемый общий балл: **~8.9**.

______________________________________________________________________

## Часть 4. Метрики контроля регресса (CI)

| Метрика                                 | Порог    | Команда                                                  | Блокирует PR                                                                       |
| --------------------------------------- | -------- | -------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Coverage                                | ≥85%     | `pytest --cov=src/bioetl --cov-fail-under=85`            | Да                                                                                 |
| mypy errors                             | 0        | `mypy src/bioetl --strict`                               | Да                                                                                 |
| Импорт domain public API                | pass     | `PYTHONPATH=src python -c "from bioetl.domain import *"` | Да                                                                                 |
| Нарушения слоёв (domain->infra/app)     | 0        | \`rg -n '^(from                                          | import) bioetl\\.(infrastructure                                                   |
| print() в коде                          | 0        | `rg 'print\\(' src/bioetl --glob '*.py'`                 | Да                                                                                 |
| Infra->Domain non-ports (строгий режим) | 0        | \`rg -n --pcre2 '^(from                                  | import) bioetl\\.domain\\.(?!ports\\b)' src/bioetl/infrastructure --glob '\*.py'\` |
| Ruff formatting                         | 0 issues | `ruff format --check src tests && ruff check src tests`  | Да                                                                                 |

## Verification Log (использованные команды)

- `find .. -name AGENTS.md -o -path '*/agents/AGENT.md'`
- `cat docs/00-project/agents/AGENT.md`
- `find docs -type f | rg ...`
- `.venv/Scripts/python.exe -m pytest tests/ --cov=src/bioetl --cov-report=term`
- `.venv/bin/python -m pytest tests/ --cov=src/bioetl --cov-report=term` (прервано)
- `python - <<PY ... coverage.json ... PY`
- `mypy src/bioetl --strict 2>&1 | ...`
- `PYTHONPATH=src python -c "from bioetl.domain import *"`
- `rg`/`find`/`wc` метрики и import-аудит
- `.venv/bin/python -m pytest tests/architecture/test_code_formatting.py -q`
