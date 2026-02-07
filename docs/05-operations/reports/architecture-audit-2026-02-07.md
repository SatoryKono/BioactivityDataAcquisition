# Architecture Audit Report — BioETL
Date: 2026-02-07
Scope: `src/bioetl`, `tests`, `docs/00-project/RULES.md`, ADR/контракты

## Ограничения входных документов
Запрошенные документы `01-domain-objects.md`, `02-etl-layers.md`, `03-data-flow.md`, `04-duplication-reduction.md`, `05-physical-layout.md` в репозитории не обнаружены (`rg --files`). Для аудита использованы `docs/00-project/RULES.md` и релевантные ADR/реализация. 

## Часть 1. Объективные метрики

| Метрика | Команда/метод | Значение |
|---|---|---:|
| Покрытие тестами | `.venv/Scripts/python.exe -m pytest tests/ --cov=src/bioetl --cov-report=term` → не найден бинарник; fallback: `python -m pytest tests/ --cov=src/bioetl --cov-report=term` | **89.40%** |
| Ошибки mypy | `mypy src/bioetl --strict 2>&1 | grep -c "error:"` | **10** |
| Циклические импорты | `PYTHONPATH=src python -c "from bioetl.domain import *"` | **pass** |
| Количество классов | `grep -r "^class " src/ --include="*.py" | wc -l` | **945** |
| Количество файлов .py | `find src/ -name "*.py" | wc -l` | **533** |
| Средний размер модуля | `find src/bioetl -name "*.py" -print0 | xargs -0 wc -l | tail -1` / число файлов (510) | **223.22 строк** |
| TODO/FIXME в коде | `rg -n "TODO|FIXME|XXX|HACK" src/ -g "*.py" | wc -l` | **23** |
| Использование print() | `grep -r "print(" src/bioetl --include="*.py" | wc -l` | **0** |
| Hardcoded secrets | `rg -n "(api_key|password|secret)\s*=" src/ -g "*.py" | wc -l` | **14** *(паттерн-метрика; не равно hardcode автоматически)* |

## Часть 2. Оценка по 10 категориям

### 1) Соблюдение слоистой архитектуры — **3/10** (вес 15%)
**Нарушения:**
- Зафиксированы импорты `infrastructure -> domain` (кроме ports), например:
  - `src/bioetl/infrastructure/storage/silver_writer.py:41-47`
  - `src/bioetl/infrastructure/storage/gold_writer.py:30-33`
  - `src/bioetl/infrastructure/storage/bronze_writer.py:42-44`
- Проверкой найдено 93 строк импорта вида `from bioetl.domain.*` внутри `infrastructure` вне `domain.ports`.

**Позитив:**
- `domain -> infrastructure/application` не найдено.
- `application -> interfaces` не найдено.

### 2) Контракты и Ports — **8/10** (вес 12%)
**Что работает:**
- Порты системно объявлены через `Protocol` в `domain/ports`.
- Примеры: `CircuitBreakerPort`, `RateLimiterPort`, `StoragePort`, `SilverValidatorPort`, `PiiHasherPort`.

**Ограничение:**
- Из-за большого числа прямых `infrastructure -> domain` зависимостей контрактная изоляция частично размыта.

### 3) Medallion Architecture — **9/10** (вес 12%)
**Соответствие:**
- Bronze: JSONL + zstd, append-only и атомарная запись.
- Silver: Delta Lake + merge/upsert + VACUUM retention.
- Gold: strict validation через Pandera и режим SCD2.

**Замечание:**
- В docstring Bronze указан паттерн пути `bronze/{provider}/{entity}/{date}/`; в пользовательском запросе ожидается `bronze/v1/...` — в коде префикс `v1` на уровне writer не enforced.

### 4) Обработка ошибок и Circuit Breaker — **9/10** (вес 10%)
**Соответствие:**
- Есть классификатор ошибок с разделением critical/recoverable/DQ.
- Circuit Breaker реализует CLOSED/OPEN/HALF_OPEN, threshold=5, recovery timeout=300s.
- Есть метрики CB (`circuit_breaker_state`, `circuit_breaker_trips_total`).

### 5) Блокировки и конкурентность — **8/10** (вес 10%)
**Соответствие:**
- Реализован `MemoryLock` (ADR-010 local-only), TTL checker, heartbeat, owner validation (Safety Guard).
- Конфиги по умолчанию: heartbeat 30s, lock TTL 90s.

**Замечание:**
- Явного monotonic fencing token счётчика для межпроцессного split-brain в local-only модели нет (ожидаемо для ADR-010).

### 6) Валидация и DQ — **9/10** (вес 10%)
**Соответствие:**
- Pandera-валидация в Silver/Gold.
- DQ пороги soft/hard: 5%/20%.
- Quarantine policy и DQ-метрики присутствуют.
- Content hash реализован по правилу `sha256(provider + canonical_json)` с нормализацией и исключением мета-полей.

### 7) Логирование и наблюдаемость — **9/10** (вес 8%)
**Соответствие:**
- `UnifiedLogger` с обязательным `run_id`, структурным JSON-логированием.
- `print()` в `src/bioetl` отсутствует.
- Реализован Prometheus adapter (`PrometheusMetrics`) и реестр метрик.

### 8) Тестирование — **8/10** (вес 8%)
**Факты:**
- Coverage: 89.40% (выше 85%).
- Запущено 10k+ тестов: `10151 passed`, `1 failed`, `37 skipped`.
- Есть contract/integration test-suite (часть live-тестов отключена через env).

**Проблема:**
- Падающий архитектурный тест: `tests/test_architecture.py::test_dependencies_versions` (`No version for black`).

### 9) Безопасность и секреты — **7/10** (вес 8%)
**Позитив:**
- PII hashing с salt через env (`BIOETL_PII_SALT_CURRENT`, rotation flags) реализован.
- По grep не найден явный hardcoded credential literal вида `secret="..."`.

**Риск/долг:**
- В тестовом прогоне есть security-skip с пометкой на PII-поля `email`/`address` в PubMed extractor (требует ручной triage).
- Метрика `api_key|password|secret =` даёт 14 совпадений (в основном присваивание переменных, не literal-утечка).

### 10) Документация и сопровождаемость — **8/10** (вес 7%)
**Позитив:**
- Есть актуальный `CHANGELOG.md`.
- Есть ADR (включая ADR-010 local-only).
- Есть набор Gold contracts (`docs/04-reference/contracts/gold/*.json`).

**Пробел:**
- Запрошенные в задаче документы `01..05` отсутствуют в текущем дереве, что ухудшает трассируемость именно к требуемому комплекту.

## Часть 3. Сводная оценка

### 3.1. Сводная таблица

| # | Категория | Вес | Оценка | Взвеш. балл | Ключевые находки |
|---|---|---:|---:|---:|---|
| 1 | Слоистая архитектура | 15% | 3 | 0.45 | 93 импорта `infrastructure -> domain` вне ports |
| 2 | Контракты и Ports | 12% | 8 | 0.96 | Protocol-ориентированный слой ports выражен явно |
| 3 | Medallion Architecture | 12% | 9 | 1.08 | Bronze JSONL+zstd, Silver Delta merge, Gold strict |
| 4 | Ошибки и Circuit Breaker | 10% | 9 | 0.90 | ErrorClassifier + CB state machine + metrics |
| 5 | Блокировки и конкурентность | 10% | 8 | 0.80 | MemoryLock TTL/heartbeat/safety guard |
| 6 | Валидация и DQ | 10% | 9 | 0.90 | Pandera + thresholds + content hash + quarantine |
| 7 | Логирование/наблюдаемость | 8% | 9 | 0.72 | UnifiedLogger + Prometheus + run_id |
| 8 | Тестирование | 8% | 8 | 0.64 | Coverage 89.4%, но 1 failing test |
| 9 | Безопасность/секреты | 8% | 7 | 0.56 | Salted PII OK, но есть flagged PII path |
| 10 | Документация/сопровождаемость | 7% | 8 | 0.56 | ADR+contracts+changelog присутствуют |
| **Итого** |  | **100%** |  | **7.57 / 10** |  |

### 3.2. Интерпретация
**7.57 / 10** → *Требуется рефакторинг, но система работоспособна*.

### 3.3. План рефакторинга

#### [P1] Декомпозиция зависимостей infrastructure → domain
- **Категория**: 1 (Слои), 2 (Ports)
- **Текущий балл → Целевой**: 3 → 8
- **Влияние на общий балл**: +0.75 … +1.0
- **Проблема**: множественные импорты `infrastructure` из `domain` (не ports), особенно в `storage/*`.
- **Решение**: ввести DTO/Result модели на границе application, перенести shared-типы в `domain.ports`/`application contracts`, убрать прямой импорт domain entities из adapters.
- **Файлы**: `src/bioetl/infrastructure/storage/*.py`, `src/bioetl/domain/value_objects/*.py`, `src/bioetl/domain/models/*.py`
- **Риски**: регрессии сериализации/metadata sidecars.
- **Критерий готовности**: 0 нарушений по CI-правилу импорта слоёв.
- **Трудозатраты**: **L** (1–2 недели).

#### [P1] Починить падающий архитектурный тест зависимостей
- **Категория**: 8 (Тестирование)
- **Текущий балл → Целевой**: 8 → 9
- **Влияние на общий балл**: +0.08 … +0.12
- **Проблема**: `No version for black` в `pyproject.toml`.
- **Решение**: зафиксировать version constraints для зависимостей или скорректировать тест policy.
- **Файлы**: `pyproject.toml`, `tests/test_architecture.py`
- **Риски**: конфликт с pinning strategy.
- **Критерий готовности**: `pytest tests/test_architecture.py::test_dependencies_versions` PASS.
- **Трудозатраты**: **S** (до 2 часов).

#### [P2] Уточнение политики PII в PubMed extractor
- **Категория**: 9 (Безопасность)
- **Текущий балл → Целевой**: 7 → 8
- **Влияние на общий балл**: +0.08
- **Проблема**: email/address фигурируют как потенциальный PII-risk в security checks.
- **Решение**: либо хеширование на этапе трансформации, либо явный allowlist + документированное исключение.
- **Файлы**: `src/bioetl/application/pipelines/pubmed/extractors/author.py`, `tests/security/*`
- **Риски**: изменение downstream-полей.
- **Критерий готовности**: security-check не флагирует путь без justification.
- **Трудозатраты**: **M** (0.5–1 день).

#### [P2] Формализовать path-конвенцию Bronze `v1`
- **Категория**: 3 (Medallion)
- **Текущий балл → Целевой**: 9 → 10
- **Влияние на общий балл**: +0.12
- **Проблема**: writer не enforce `bronze/v1/...` на уровне API.
- **Решение**: добавить policy-валидацию base path / build-path helper с version segment.
- **Файлы**: `src/bioetl/infrastructure/storage/bronze_writer.py`, docs/runbooks
- **Риски**: несовместимость путей в существующих данных.
- **Критерий готовности**: path-policy test + миграционный note.
- **Трудозатраты**: **M** (1 день).

#### [P3] Восстановить/добавить архитектурные документы 01..05
- **Категория**: 10 (Документация)
- **Текущий балл → Целевой**: 8 → 9
- **Влияние на общий балл**: +0.07
- **Проблема**: отсутствуют документы, явно запрошенные в аудит-чеклисте.
- **Решение**: добавить алиасы или индекс с mapping на актуальные docs.
- **Файлы**: `docs/00-project/`, `docs/02-architecture/`, `docs/03-guides/`
- **Риски**: дублирование/дрейф документации.
- **Критерий готовности**: навигация из RULES.md к 01..05 без 404.
- **Трудозатраты**: **S/M** (0.5 дня).

### 3.4. Roadmap
- **Фаза 1 (неделя 1-2)**: P1 (слои + падение теста). Ожидаемый общий балл: **7.57 → ~8.3**.
- **Фаза 2 (неделя 3-4)**: P2 (PII-policy + path policy). Ожидаемый общий балл: **~8.3 → ~8.5**.
- **Фаза 3 (неделя 5+)**: P3 (документация/оптимизация). Ожидаемый общий балл: **~8.5 → ~8.6+**.

## Часть 4. Метрики контроля регресса (CI)

| Метрика | Порог | Команда | Блокирует PR |
|---|---|---|---|
| Coverage | ≥85% | `pytest --cov=src/bioetl --cov-fail-under=85` | Да |
| mypy errors | 0 | `mypy src/bioetl --strict` | Да |
| Циклические импорты (domain) | 0 | `PYTHONPATH=src python -c "from bioetl.domain import *"` | Да |
| Нарушения слоёв (`domain -> infra/app`) | 0 | `rg -n "^from bioetl\.(infrastructure|application)" src/bioetl/domain -g '*.py'` | Да |
| Нарушения слоёв (`infrastructure -> domain (кроме ports)`) | 0 | `rg --pcre2 -n "^from bioetl\.domain\.(?!ports)" src/bioetl/infrastructure -g '*.py'` | Да |
| print() в коде | 0 | `rg -n "print\(" src/bioetl -g '*.py'` | Да |
| Secrets literals | 0 | custom semgrep/trufflehog rule (literal secrets only) | Да |
| Architecture tests | all pass | `pytest tests/architecture -q` | Да |

## Verification log (ключевые команды)
- `python -m pytest tests/ --cov=src/bioetl --cov-report=term`
- `mypy src/bioetl --strict 2>&1 | grep -c "error:"`
- `PYTHONPATH=src python -c "from bioetl.domain import *"`
- `grep -r "^class " src/ --include="*.py" | wc -l`
- `find src/ -name "*.py" | wc -l`
- `rg -n "TODO|FIXME|XXX|HACK" src/ -g "*.py" | wc -l`
- `grep -r "print(" src/bioetl --include="*.py" | wc -l`
- `rg -n "(api_key|password|secret)\s*=" src/ -g "*.py" | wc -l`
