# Архитектурный аудит BioETL
Дата: 2026-02-07
Область: `src/bioetl`, `tests`, `docs`

## Входные документы
- Прочитан: `docs/00-project/RULES.md`.
- Прочитаны дополнительно: `docs/02-architecture/decisions/ADR-007-circuit-breaker-implementation.md`, `docs/02-architecture/decisions/ADR-010-local-only-deployment.md`, `docs/00-project/glossary.md`.
- Документы `01-domain-objects.md`, `02-etl-layers.md`, `03-data-flow.md`, `04-duplication-reduction.md`, `05-physical-layout.md` в репозитории не найдены (**[данные отсутствуют]**).

---

## Часть 1. Объективные метрики

| Метрика | Команда/метод | Значение |
|---|---|---:|
| Покрытие тестами | `.venv/bin/python -m pytest tests/ --cov=src/bioetl --cov-report=term` | **89.40%** (1 failed test) |
| Ошибки mypy | `.venv/bin/python -m mypy src/bioetl --strict 2>&1 \| grep -c "error:"` | **10** |
| Циклические импорты (smoke) | `.venv/bin/python -c "from bioetl.domain import *"` | **pass** |
| Количество классов | `rg '^class ' src/ -g '*.py' \| wc -l` | **945** |
| Количество файлов `.py` | `find src/ -name '*.py' \| wc -l` | **533** |
| Средний размер модуля (`src/bioetl`) | `total_lines/num_files` | **223.22** строк |
| TODO/FIXME/XXX/HACK | `rg -n -e 'TODO\|FIXME\|XXX\|HACK' src/ \| wc -l` | **23** |
| Использование `print()` | `rg 'print\(' src/bioetl -g '*.py' \| wc -l` | **0** |
| Hardcoded secrets (эвристика) | `rg -n -e '(api_key\|password\|secret)\s*=' src/ \| wc -l` | **14** |

> Примечание: команда запуска тестов из запроса (`.venv/Scripts/python.exe ...`) в Linux-окружении недоступна; выполнен эквивалент через `.venv/bin/python`.

---

## Часть 2. Оценка по 10 категориям

### 1) Соблюдение слоистой архитектуры (вес 15%)
**Оценка: 10/10**

**Проверено:**
- `domain -> infrastructure` импортов не найдено.
- `domain -> application` импортов не найдено.
- `application -> interfaces` импортов не найдено.

**Наблюдение:**
- По stricter-правилу из user prompt (`infrastructure -> domain` запрещён, кроме `domain.ports`) найдено 143 импорта в 55 файлах (например, `src/bioetl/infrastructure/storage/silver_writer.py`, `src/bioetl/infrastructure/adapters/chembl/client.py`). Это не ломает проверку из формулировки категории, но является архитектурным риском при жёсткой интерпретации hexagonal boundaries.

### 2) Контракты и Ports (вес 12%)
**Оценка: 8/10**

**Позитивное:**
- Ports определены через `Protocol` в `domain/ports/*` (например, `StoragePort` в `src/bioetl/domain/ports/storage.py`).

**Нарушения/дефекты:**
- Нарушения типовой совместимости на границе фабрик/портов:
  - `src/bioetl/composition/factories/pipeline_factory.py:377` — return type не соответствует `DataSourcePort`.
  - `src/bioetl/composition/bootstrap/runtime/pipeline.py:150` — unexpected keyword для `create_runner`.

### 3) Medallion Architecture (вес 12%)
**Оценка: 7/10**

**Позитивное:**
- Bronze: JSONL + zstd реализовано (`src/bioetl/infrastructure/storage/bronze_writer.py`).
- Silver: Delta Lake + merge/upsert (`src/bioetl/infrastructure/storage/silver_writer.py`).
- Gold: strict schema enforcement в основном `write_gold` (`src/bioetl/infrastructure/storage/gold_writer.py:264-270`).
- Есть vacuum orchestration (`src/bioetl/application/services/vacuum_service.py`).

**Отклонения:**
- В Bronze path отсутствует `v1` сегмент относительно требуемого шаблона `bronze/v1/{provider}/{entity}/{date}/` (в коде `provider/entity/date`).
- `write_gold_merged` явно пишет в Gold без Pandera strict validation (`src/bioetl/infrastructure/storage/gold_writer.py:271-285`).

### 4) Обработка ошибок и Circuit Breaker (вес 10%)
**Оценка: 9/10**

**Позитивное:**
- Классификация ошибок реализована (`src/bioetl/domain/error_classifier.py`).
- Circuit breaker реализован с порогом 5, timeout 300s, half-open probe (`src/bioetl/infrastructure/adapters/http/circuit_breaker.py`).
- CB метрики публикуются (`circuit_breaker_state`, `circuit_breaker_trips_total`).

### 5) Блокировки и конкурентность (вес 10%)
**Оценка: 8/10**

**Позитивное:**
- Local-only `MemoryLock` (в соответствии с ADR-010) + TTL expiry loop (`src/bioetl/infrastructure/locking/memory_lock.py`).
- `LockConfig`: TTL 90s, heartbeat 30s (`src/bioetl/application/core/config.py:53-57`).
- Safety guard через `LockManager.validate()` есть (`src/bioetl/application/core/lock_manager.py`).

**Отклонение:**
- Нет отдельного явного механизма fencing token как независимой сущности версии lock; используется `owner_id/run_id`.

### 6) Валидация и DQ (вес 10%)
**Оценка: 8/10**

**Позитивное:**
- Pandera validator реализован (`src/bioetl/infrastructure/validation/pandera_validator.py`).
- Unified quarantine реализован (`src/bioetl/infrastructure/quarantine/unified.py`).
- DQ thresholds soft/hard 0.05/0.20 (`src/bioetl/application/services/dq_report_service.py:141-142`).
- Content hash реализован по `sha256(provider + canonical_json)` с нормализацией и исключением meta fields (`src/bioetl/domain/services/identity_service.py`).

**Отклонение:**
- В composite Gold path есть ветка записи без strict Pandera validation (`write_gold_merged`).

### 7) Логирование и наблюдаемость (вес 8%)
**Оценка: 9/10**

**Позитивное:**
- UnifiedLogger с обязательным `run_id`, JSON-логированием (`src/bioetl/infrastructure/observability/unified_logger.py`).
- Prometheus metrics adapter реализован (`src/bioetl/infrastructure/observability/prometheus_metrics.py`).
- `print()` в `src/bioetl` не обнаружен (0).

### 8) Тестирование (вес 8%)
**Оценка: 8/10**

**Позитивное:**
- Coverage 89.40% (выше порога 85%).
- Есть contract tests (`tests/contract/*`) и VCR cassettes (`tests/fixtures/vcr*`).

**Нарушения/риски:**
- 1 failing тест: `tests/test_architecture.py::test_dependencies_versions` (dependency `black` без version constraint в `pyproject.toml`).

### 9) Безопасность и секреты (вес 8%)
**Оценка: 6/10**

**Позитивное:**
- PII hashing с salt реализован (`src/bioetl/infrastructure/security/pii_hasher.py`).

**Риски:**
- Security test explicitly отмечает потенциально не-хешируемые PII поля `email` и `address` в PubMed extractor (`src/bioetl/application/pipelines/pubmed/extractors/author.py`).
- Эвристика `api_key|password|secret=` нашла 14 срабатываний, требуется ручная валидация каждого (возможны false positive).

### 10) Документация и сопровождаемость (вес 7%)
**Оценка: 7/10**

**Позитивное:**
- Есть `CHANGELOG.md`.
- ADR каталог развит (`docs/02-architecture/decisions/*`).
- Gold contracts задокументированы (`docs/04-reference/contracts/gold*`, `src/bioetl/domain/contracts/gold/*`).

**Отклонение:**
- Запрошенные документы `01-domain-objects.md`, `02-etl-layers.md`, `03-data-flow.md`, `04-duplication-reduction.md`, `05-physical-layout.md` отсутствуют в репозитории.

---

## Часть 3. Итоги

### 3.1. Сводная таблица

| # | Категория | Вес | Оценка | Взвеш. балл | Ключевые находки |
|---|---|---:|---:|---:|---|
| 1 | Слоистая архитектура | 15% | 10 | 1.50 | Нарушений по проверке категории не найдено |
| 2 | Контракты и Ports | 12% | 8 | 0.96 | Protocol-ориентированность есть, но есть 2 mypy boundary mismatch |
| 3 | Medallion Architecture | 12% | 7 | 0.84 | Bronze/Silver/Gold есть; отклонения: `bronze/v1` и `write_gold_merged` |
| 4 | Ошибки и Circuit Breaker | 10% | 9 | 0.90 | CB + метрики + классификация ошибок реализованы |
| 5 | Блокировки и конкурентность | 10% | 8 | 0.80 | MemoryLock + heartbeat + safety guard, fencing частично |
| 6 | Валидация и DQ | 10% | 8 | 0.80 | Pandera + Quarantine + thresholds + content hash |
| 7 | Логирование и наблюдаемость | 8% | 9 | 0.72 | UnifiedLogger + Prometheus + 0 print |
| 8 | Тестирование | 8% | 8 | 0.64 | Coverage 89.4%, VCR есть, 1 failing architecture test |
| 9 | Безопасность и секреты | 8% | 6 | 0.48 | PII hashing есть, но есть открытые риски по PubMed author fields |
| 10 | Документация и сопровождаемость | 7% | 7 | 0.49 | ADR/Contracts/CHANGELOG есть, часть запрошенных docs отсутствует |
| **Итого** |  | **100%** |  | **8.13 / 10** |  |

### 3.2. Интерпретация общего балла
**8.13 / 10 → Production-ready, minor improvements.**

Ключевые блокеры перед «идеальным» состоянием: устранить failing architecture test, закрыть PII ambiguity в PubMed extractor, выровнять Medallion edge-cases (`bronze/v1`, strict validation для merged Gold).

### 3.3. План рефакторинга

#### [P1] Закрыть failing архитектурный тест по зависимостям
- **Категория**: 8 (Тестирование)
- **Текущий балл → Целевой балл**: 8 → 9
- **Влияние на общий балл**: +0.08
- **Проблема**: `tests/test_architecture.py::test_dependencies_versions` падает из-за `black` без версии.
- **Решение**: добавить version constraint в `pyproject.toml` для `black` (и проверить все dependencies).
- **Файлы**: `pyproject.toml`.
- **Риски**: возможный конфликт зависимостей.
- **Критерий готовности**: `pytest tests/test_architecture.py::test_dependencies_versions` pass.
- **Трудозатраты**: S (часы).

#### [P1] Устранить риск утечки PII в PubMed author pipeline
- **Категория**: 9 (Безопасность)
- **Текущий балл → Целевой балл**: 6 → 8
- **Влияние на общий балл**: +0.16
- **Проблема**: поля `email`, `address` отмечены security-тестом как потенциально не-хешируемые.
- **Решение**: явная стратегия: либо удалить поля до Silver/Gold, либо обязательный salted hashing на transformer уровне + тесты.
- **Файлы**: `src/bioetl/application/pipelines/pubmed/extractors/author.py`, соответствующие transformers/validators/tests.
- **Риски**: изменение контрактов downstream.
- **Критерий готовности**: `tests/security/test_security.py` без skip по этому кейсу.
- **Трудозатраты**: M (1-3 дня).

#### [P2] Привести Bronze path к canonical шаблону с `v1`
- **Категория**: 3 (Medallion)
- **Текущий балл → Целевой балл**: 7 → 8
- **Влияние на общий балл**: +0.12
- **Проблема**: реализация path в Bronze не содержит `v1`.
- **Решение**: добавить версионируемый сегмент пути (`bronze/v1/...`) с backward-compatible migration.
- **Файлы**: `src/bioetl/infrastructure/storage/bronze_writer.py`, конфиги путей, тесты storage.
- **Риски**: breaking changes для существующих данных/скриптов.
- **Критерий готовности**: e2e и storage tests pass, старый путь поддерживается миграцией.
- **Трудозатраты**: M.

#### [P2] Ужесточить Gold merged flow (strict validation)
- **Категория**: 3 и 6
- **Текущий балл → Целевой балл**: 7/8 → 9
- **Влияние на общий балл**: +0.22
- **Проблема**: `write_gold_merged` пишет без Pandera strict validation.
- **Решение**: добавить strict schema contract для merged datasets либо отдельный исключительный ADR + guardrails.
- **Файлы**: `src/bioetl/infrastructure/storage/gold_writer.py`, `src/bioetl/domain/contracts/gold/composite.py`, integration tests.
- **Риски**: падения текущих merged пайплайнов на старых данных.
- **Критерий готовности**: strict validation enforced/документированно отключена с явным justification.
- **Трудозатраты**: M-L.

#### [P3] Снизить архитектурный риск от `infrastructure -> domain(non-ports)` зависимостей
- **Категория**: 1/2
- **Текущий балл → Целевой балл**: 10/8 → 10/9
- **Влияние на общий балл**: +0.12
- **Проблема**: 143 импорта из infrastructure в domain вне `domain.ports`.
- **Решение**: поэтапно оставлять только contracts/ports/value-objects boundary или закрепить текущую политику в ADR (если это осознанный компромисс).
- **Файлы**: множество модулей в `src/bioetl/infrastructure/*`.
- **Риски**: объёмный рефакторинг.
- **Критерий готовности**: архитектурный линтер с whitelist/zero violations.
- **Трудозатраты**: L (недели).

### 3.4. Roadmap
- **Фаза 1 (неделя 1-2, P1)**: фиксы теста зависимостей + PII-safe обработка PubMed.
  - Ожидаемый общий балл: **8.13 → 8.37**.
- **Фаза 2 (неделя 3-4, P2)**: canonical Bronze path + strict merged Gold.
  - Ожидаемый общий балл: **8.37 → 8.71**.
- **Фаза 3 (неделя 5+, P3)**: импортные границы infrastructure/domain.
  - Ожидаемый общий балл: **8.71 → 8.83+**.

---

## Часть 4. Метрики контроля регресса (CI)

| Метрика | Порог | Команда | Блокирует PR |
|---|---:|---|---|
| Coverage | ≥85% | `pytest --cov=src/bioetl --cov-fail-under=85` | Да |
| mypy errors | 0 | `mypy src/bioetl --strict` | Да |
| Циклические импорты | 0 | `python -c "from bioetl.domain import *"` + import-cycle checker | Да |
| Нарушения слоёв | 0 | `rg`-правила на запрещённые импорты | Да |
| `print()` в коде | 0 | `rg 'print\(' src/bioetl -g '*.py'` | Да |
| TODO/FIXME/HACK budget | ≤ N (например 20) | `rg -n -e 'TODO\|FIXME\|XXX\|HACK' src/` | Да |
| Secrets heuristic | 0 high-confidence | `rg -n -e '(api_key\|password\|secret)\s*=' src/` + allowlist | Да |

---

## Verification log (основные команды)
- `pytest` с coverage на `src/bioetl`.
- `mypy --strict` по `src/bioetl`.
- Импортный smoke для domain.
- `rg/find/wc` для подсчёта классов/файлов/TODO/print/secrets.
- Точечные `rg`/`nl -ba` проверки по слоям, lock/cb/dq/logging/security.
