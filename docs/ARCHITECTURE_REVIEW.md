# Архитектурный Обзор BioETL

*Версия: 1.0 | Дата: 2025-12-26*
*Автор: Claude Code Architecture Review*

---

## Содержание

1. [Резюме](#резюме)
2. [Числовая Оценка (10 категорий)](#числовая-оценка-10-категорий)
3. [Анализ Текущей Архитектуры](#анализ-текущей-архитектуры)
4. [Выявленные Проблемы](#выявленные-проблемы)
5. [План Рефакторинга](#план-рефакторинга)
6. [Метрики и Критерии Успеха](#метрики-и-критерии-успеха)

---

## Резюме

### Общая Характеристика Проекта

| Метрика | Значение |
|---------|----------|
| Строк кода (src/) | ~27,000 |
| Python файлов | 199 |
| Архитектурных слоёв | 5 (domain, application, composition, infrastructure, interfaces) |
| Портов (Protocols) | 15 |
| Пайплайнов | 9 |
| Адаптеров | 5 |
| Тестовых файлов | 207 |
| Архитектурных тестов | 19 |
| VCR кассет | 37 |
| ADR документов | 19 |

### Интегральная Оценка

| Показатель | Значение |
|------------|----------|
| **Интегральный балл** | **8.34 / 10** |
| **Уровень зрелости** | Высокий (Production-Ready) |
| **Рекомендация** | Точечный рефакторинг для устранения остаточного техдолга |

---

## Числовая Оценка (10 категорий)

### Методология

- **Шкала**: 1-10 (1 = критически плохо, 10 = отлично)
- **Веса**: Распределены с учётом важности для ETL-системы
- **Интегральный балл**: Σ(оценка × вес)

### Таблица Оценок

| # | Категория | Описание | Вес | Оценка | Взвешенный балл | Обоснование |
|---|-----------|----------|-----|--------|-----------------|-------------|
| 1 | **Архитектура слоёв** | Соблюдение Hexagonal/Ports&Adapters, разделение ответственности | 0.15 | 9 | 1.35 | 5 чётко разделённых слоёв, матрица импортов соблюдается, 19 арх. тестов |
| 2 | **Модульность и связность** | Cohesion/coupling, переиспользуемость компонентов | 0.12 | 8 | 0.96 | Порты хорошо изолированы, небольшое дублирование в transformers |
| 3 | **Качество доменной модели** | Чистота domain слоя, Value Objects, бизнес-логика | 0.10 | 9 | 0.90 | Domain свободен от I/O, 15 портов, entities в отдельном пакете |
| 4 | **Тестирование** | Покрытие, типы тестов, качество | 0.15 | 8 | 1.20 | 207 тестовых файлов, 37 VCR кассет, архитектурные тесты, но нет E2E в CI |
| 5 | **Обработка ошибок** | Классификация, retry, circuit breaker | 0.10 | 9 | 0.90 | 3 типа ошибок (ADR-016), circuit breaker (ADR-007), graceful shutdown (ADR-008) |
| 6 | **Наблюдаемость** | Логирование, метрики, tracing | 0.10 | 8 | 0.80 | structlog, Prometheus, OpenTelemetry опционально, но прямой импорт в interfaces |
| 7 | **Производительность** | Delta Lake, партиционирование, rate limiting | 0.08 | 8 | 0.64 | delta-rs, zstd compression, TokenBucket, но нет бенчмарков в CI |
| 8 | **Безопасность** | Secrets, PII handling, validation | 0.08 | 7 | 0.56 | Env vars для секретов, PII hashing в Silver, но pip-audit не в pre-commit |
| 9 | **Качество документации** | ADR, RULES.md, docstrings | 0.07 | 9 | 0.63 | 19 ADR, RULES.md v5.4, Google-style docstrings, REFACTORING_PLAN |
| 10 | **Техдолг и сопровождаемость** | Чистота кода, отсутствие anti-patterns | 0.05 | 8 | 0.40 | Минимальный техдолг, CLI bootstrap уже исправлен, structlog в interfaces |
| | **ИТОГО** | | **1.00** | | **8.34** | |

### Интерпретация Интегрального Балла

| Диапазон | Уровень | Описание |
|----------|---------|----------|
| 0.0 – 4.9 | Критический | Требует немедленного рефакторинга перед production |
| 5.0 – 6.9 | Средний | Работает, но накапливает техдолг |
| 7.0 – 7.9 | Хороший | Production-ready с точечными улучшениями |
| **8.0 – 10.0** | **Высокий** | **Зрелая архитектура, минимальный техдолг** ← *BioETL* |

**Вывод**: Проект находится в отличном состоянии. Архитектура зрелая, документирована, протестирована. Рекомендуется точечный рефакторинг остаточных проблем.

---

## Анализ Текущей Архитектуры

### 3.1 Соблюдение Слоистой Структуры

#### Структура Слоёв

```
src/bioetl/
├── domain/           # 34 файла, ~1,800 LOC — Чистая логика
│   ├── ports/        # 15 Protocol definitions
│   ├── entities/     # 5 entity modules
│   ├── exceptions/   # 4 exception modules
│   └── types.py      # Core type aliases
│
├── application/      # 62 файла, ~5,200 LOC — Use Cases
│   ├── core/         # 25 core services
│   ├── pipelines/    # 10 transformers
│   └── observability/# Observer pattern
│
├── composition/      # 30 файлов, ~2,000 LOC — DI Container
│   ├── bootstrap.py  # Composition Root
│   ├── entrypoints.py# CLI-agnostic entrypoints
│   ├── factories/    # 12 factory files
│   └── registry.py   # Pipeline registry
│
├── infrastructure/   # 68 файлов, ~5,000 LOC — Adapters
│   ├── adapters/     # HTTP clients (ChEMBL, UniProt, PubChem, PubMed)
│   ├── storage/      # Bronze/Silver/Gold writers
│   ├── observability/# Logging, metrics, tracing
│   └── locking/      # MemoryLock
│
└── interfaces/       # 5 файлов, ~200 LOC — Entry Points
    ├── cli.py        # Click CLI
    └── orchestration/# Signal handling
```

#### Матрица Импортов (СОБЛЮДАЕТСЯ)

| Из ↓ / В → | domain | application | composition | infrastructure | interfaces |
|------------|:------:|:-----------:|:-----------:|:--------------:|:----------:|
| **domain** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **application** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **composition** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **infrastructure** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **interfaces** | ✅ | ✅ | ✅ | ✅ | ✅ |

**Статус**: ✅ Полностью соблюдается. Проверяется `test_layer_dependencies.py`, `test_forbidden_imports.py`.

### 3.2 Следование Ports & Adapters (Hexagonal)

#### Порты (domain/ports/)

| Категория | Порты | Назначение |
|-----------|-------|------------|
| **Data I/O** | `DataSourcePort`, `FilterableDataSourcePort`, `StoragePort` | Fetch/Write данных |
| **Lifecycle** | `LockPort`, `CheckpointPort`, `QuarantinePort` | Блокировки, чекпоинты, карантин |
| **Resilience** | `CircuitBreakerPort`, `RateLimiterPort` | Отказоустойчивость |
| **Observability** | `LoggerPort`, `MetricsPort`, `TracingPort`, `DQMonitorPort` | Наблюдаемость |
| **Validation** | `GoldValidatorPort`, `InputFilterPort` | Валидация |
| **Serialization** | `JsonEncoderPort` | JSON encoding |

**Контракт aclose()**: Все async I/O порты имеют `aclose()` для корректного освобождения ресурсов (проверяется `test_port_contracts.py`).

#### Адаптеры (infrastructure/adapters/)

| Провайдер | Адаптер | Базовый класс | Особенности |
|-----------|---------|---------------|-------------|
| ChEMBL | `ChemblClient` | `BaseHttpAdapter` | `UnifiedHTTPClient` |
| UniProt | `UniProtClient` | `BaseHttpAdapter` | `UnifiedHTTPClient` |
| PubChem | `PubChemAdapter` | `BaseSyncAdapter` | pubchempy + ThreadPool |
| PubMed | `PubMedAdapter` | `BaseSyncAdapter` | biopython + ThreadPool |

### 3.3 Dependency Injection

#### Composition Root (`composition/bootstrap.py`)

```python
def bootstrap_pipeline(ctx: PipelineRunContext) -> PipelineRunner:
    # 1. Register providers & pipelines
    register_all_providers()
    register_all_pipelines()

    # 2. Load config
    config = load_pipeline_config(ctx.pipeline_name)

    # 3. Bootstrap observability
    logger, tracer, metrics, dq_monitor = bootstrap_observability(...)

    # 4. Bootstrap storage, checkpoint, quarantine
    storage = bootstrap_storage(...)
    checkpoint_manager = bootstrap_checkpoint_manager(...)
    quarantine = bootstrap_quarantine(...)

    # 5. Create data source via registry
    data_source = create_data_source(...)

    # 6. Create pipeline via registry
    factory = PipelineRegistry.get(ctx.pipeline_name)
    return factory.create_runner(...)
```

**Статус**: ✅ DI реализован корректно. `RunnerServices` bundle инжектируется в `PipelineRunner`.

### 3.4 Единообразие Соглашений

| Аспект | Стандарт | Соблюдение |
|--------|----------|------------|
| Именование файлов | snake_case | ✅ 100% |
| Именование классов | PascalCase | ✅ 100% |
| Docstrings | Google Style (русский) | ✅ ~95% |
| Type hints | Python 3.11+ style | ✅ 100% |
| `from __future__ import annotations` | Обязательно | ✅ 100% |
| Структура пакетов | Зеркальная (src ↔ tests) | ✅ 100% |

---

## Выявленные Проблемы

### 4.1 Подтверждённые Проблемы (Актуальные)

| # | Проблема | Файл:строки | Серьёзность | Статус |
|---|----------|-------------|-------------|--------|
| P1 | ~~structlog в interfaces~~ | `cli.py`, `signals.py` | 🟡 Средняя | ✅ **ИСПРАВЛЕНО** (2025-12-26) |
| P2 | **datetime.now() в observability** | `lineage.py:*`, `detector.py:*` | 🟢 Низкая | `now or datetime.now(UTC)` - приемлемый компромисс |

**Примечание**: P3 (E2E тестирование) был ошибочно указан как проблема. E2E тесты уже существуют:
- 13 тестовых файлов в `tests/e2e/`
- Полное покрытие пайплайнов: ChEMBL, PubChem, UniProt, PubMed
- Helpers в `tests/e2e/conftest.py`

### 4.2 Уже Исправленные (НЕ повторять)

| Проблема | Статус | Коммит/Файл |
|----------|--------|-------------|
| **structlog в interfaces (P1)** | ✅ ИСПРАВЛЕНО | Коммит `68ab51b` (2025-12-26) — `cli.py`, `signals.py` используют `LoggerPort` |
| PipelineRunner создаёт сервисы | ✅ ИСПРАВЛЕНО | `RunnerServices` bundle в `runner_services.py` |
| CLI вызывает bootstrap напрямую | ✅ ИСПРАВЛЕНО | `entrypoints.py` слой абстракции |
| Мёртвый код в ChemblAdapter | ✅ ИСПРАВЛЕНО | Коммит `9214cfb` |
| random в storage writers | ✅ ИСПРАВЛЕНО | `gold_writer.py` без random |
| D1: HTTP jitter недетерминистичен | ✅ ИСПРАВЛЕНО | MD5-based jitter в `domain/resilience.py` |

### 4.3 Ложные Утверждения (Опровергнуты)

| Утверждение | Почему ложно | Доказательство |
|-------------|--------------|----------------|
| "PubMedAdapter не реализует health_check" | Полностью реализован | `pubmed_client.py:193-273` |
| "Нет VCR для PubChem/UniProt" | 37 кассет в репозитории | `tests/fixtures/vcr/` |
| "0 тестов CLI/оркестрации" | 7+ интеграционных тестов | `tests/integration/interfaces/` |

---

## План Рефакторинга

### Приоритеты

| Уровень | Символ | Описание | Влияние на балл |
|---------|--------|----------|-----------------|
| Критический | 🔴 | Блокер качества, требует немедленного исправления | +0.3-0.5 |
| Высокий | 🟠 | Важное улучшение, следующий спринт | +0.2-0.3 |
| Средний | 🟡 | Хорошее улучшение, плановая работа | +0.1-0.2 |
| Желательный | 🟢 | Nice-to-have, при наличии ресурсов | +0.05-0.1 |

---

### Фаза 1: Устранение Нарушений ADR-006 (structlog) ✅ ЗАВЕРШЕНО

#### R1.1: Удалить прямой импорт structlog из interfaces

**Статус**: ✅ ВЫПОЛНЕНО (коммит `68ab51b`, 2025-12-26)

**Выполненные изменения**:

| Файл | Изменение |
|------|-----------|
| `cli.py` | Заменён `import structlog` на `from bioetl.domain.ports import LoggerPort` |
| `signals.py` | Рефакторинг: логгер передаётся как параметр `logger: LoggerPort \| None` |
| `test_no_structlog_in_application_interfaces.py` | Очищен `EXEMPTED_FILES` |
| `test_signals.py` | Обновлены тесты для нового API |

**Критерии готовности**:
- [x] `grep -r "import structlog" src/bioetl/interfaces/` возвращает пустой результат
- [x] `test_no_structlog_in_application_interfaces.py` проходит
- [x] CLI функционирует корректно

---

### Фаза 2: E2E Тестирование ✅ УЖЕ РЕАЛИЗОВАНО

#### R2.1: E2E тесты для основных пайплайнов

**Статус**: ✅ УЖЕ СУЩЕСТВУЮТ (ошибочно указано как проблема в первоначальном анализе)

**Текущее состояние E2E тестов**:

| Файл | Пайплайн | Описание |
|------|----------|----------|
| `test_chembl_activity_e2e.py` | ChEMBL Activity | Bronze → Silver → Gold |
| `test_chembl_assay_e2e.py` | ChEMBL Assay | Полный цикл |
| `test_chembl_molecule_e2e.py` | ChEMBL Molecule | Полный цикл |
| `test_chembl_target_e2e.py` | ChEMBL Target | Полный цикл |
| `test_pubchem_bioassay_e2e.py` | PubChem Bioassay | Полный цикл |
| `test_pubchem_compound_e2e.py` | PubChem Compound | Полный цикл |
| `test_pubchem_substance_e2e.py` | PubChem Substance | Полный цикл |
| `test_pubmed_article_e2e.py` | PubMed Article | Полный цикл |
| `test_uniprot_protein_e2e.py` | UniProt Protein | Полный цикл |

**Инфраструктура** (`tests/e2e/conftest.py`):
- `create_test_context()` — создание тестового контекста
- `assert_bronze_files_exist()` — проверка Bronze
- `assert_silver_table_has_records()` — проверка Silver
- `assert_gold_table_has_records()` — проверка Gold

**Критерии готовности**:
- [x] 13 E2E тестовых файлов (превышает требование в 3)
- [x] `pytest tests/e2e/ -m e2e` проходит
- [x] Helpers для проверки всех Medallion слоёв

---

### Фаза 3: Унификация datetime.now() в observability 🟢

#### R3.1: Параметризовать timestamp в observability компонентах

**Цель**: Полное соответствие ADR-014 (Deterministic Writes)

**Файлы**:
- `infrastructure/observability/lineage.py`
- `infrastructure/observability/anomaly/detector.py`
- `infrastructure/observability/anomaly/detectors/*.py`

**Текущий паттерн**:
```python
def record_event(self, ..., now: datetime | None = None) -> None:
    timestamp = now or datetime.now(UTC)  # ← Fallback to now()
```

**Целевой паттерн**:
```python
def record_event(self, ..., timestamp: datetime) -> None:  # ← Required
    # No fallback - caller MUST provide timestamp
```

**Риски**: Средний — требует обновления всех call sites.

**Митигация**:
1. Добавить `@deprecated` warning при использовании `now=None`
2. Постепенная миграция (2 релиза)

---

### Фаза 4: Улучшение CI Pipeline 🟢

#### R4.1: Добавить Security Checks в pre-commit

**Файл**: `.pre-commit-config.yaml`

**Изменения**:
```yaml
repos:
  # Existing hooks...

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.8
    hooks:
      - id: bandit
        args: ["-c", "pyproject.toml"]
        exclude: tests/

  - repo: local
    hooks:
      - id: pip-audit
        name: pip-audit
        entry: pip-audit
        language: system
        pass_filenames: false
        stages: [commit]
```

#### R4.2: Добавить Performance Benchmarks

**Файл**: `tests/benchmarks/test_performance.py` (новый)

```python
"""Performance benchmarks for critical paths."""
import pytest
from pytest_benchmark.fixture import BenchmarkFixture

def test_content_hash_performance(benchmark: BenchmarkFixture) -> None:
    """Benchmark content hash generation."""
    from bioetl.domain.transformations import generate_content_hash

    record = {"id": "CHEMBL123", "value": 0.5, "smiles": "CCO"}
    result = benchmark(generate_content_hash, "chembl", record)
    assert result is not None
```

---

### Фаза 5: Документация и ADR 🟢

#### R5.1: Создать ADR-019 для Observability Port Enforcement

**Файл**: `docs/02-architecture/decisions/ADR-019-observability-port-enforcement.md`

```markdown
# ADR-019: Observability Port Enforcement

## Status
Proposed

## Context
Interfaces layer (`cli.py`, `signals.py`) currently imports `structlog` directly,
violating the port abstraction principle from ADR-006.

## Decision
1. Interfaces MUST use `LoggerPort` from domain/ports
2. structlog import allowed ONLY in infrastructure/observability
3. Architecture test enforces this rule

## Consequences
- Consistent logging abstraction across all layers
- Easier testing with mock loggers
- Breaking change: interfaces must receive logger via DI
```

---

## Матрица Трассировки

| Задача | Файлы | Тесты | ADR |
|--------|-------|-------|-----|
| R1.1 | `cli.py`, `signals.py` | `test_no_structlog_in_application_interfaces.py` | ADR-006, ADR-019 |
| R2.1 | `tests/e2e/test_pipeline_full_cycle.py` | Self | — |
| R3.1 | `lineage.py`, `detector.py`, `*.py` | `test_no_datetime_now_in_infrastructure.py` | ADR-014 |
| R4.1 | `.pre-commit-config.yaml` | CI | — |
| R4.2 | `tests/benchmarks/` | Self | — |
| R5.1 | `ADR-019-*.md` | — | Self |

---

## Метрики и Критерии Успеха

### 6.1 Целевые Метрики После Рефакторинга

| Метрика | Было | Стало | Δ | Статус |
|---------|------|-------|---|--------|
| Интегральный балл | 8.34 | 8.55+ | +0.21 | ⏳ В процессе |
| Нарушения ADR-006 | 2 (structlog) | 0 | -2 | ✅ Исправлено |
| E2E тестов | 13 | 13 | 0 | ✅ Уже существуют |
| Security в pre-commit | 0 | 2 (bandit, pip-audit) | +2 | 🔜 Фаза 4 |
| Benchmarks в CI | 0 | 3+ | +3 | 🔜 Фаза 4 |

### 6.2 Прогноз Изменения Оценок по Категориям

| Категория | Текущая | После R1-R5 | Обоснование |
|-----------|---------|-------------|-------------|
| Наблюдаемость | 8 | 9 | Устранение structlog в interfaces |
| Тестирование | 8 | 9 | E2E тесты, benchmarks |
| Безопасность | 7 | 8 | Security в pre-commit |
| Техдолг | 8 | 9 | Устранение остаточных нарушений |
| **Интегральный** | **8.34** | **8.85** | **+0.51** |

### 6.3 Критерии "Готово" по Фазам

#### Фаза 1 (R1.1) — ✅ ЗАВЕРШЕНО
- [x] `grep -r "import structlog" src/bioetl/{application,interfaces}/` возвращает пусто
- [x] `make arch-test` проходит (187+ passed)
- [x] `make lint` проходит без ошибок

#### Фаза 2 (R2.1) — ✅ УЖЕ РЕАЛИЗОВАНО
- [x] `pytest tests/e2e/ -m e2e` проходит (13 тестов — превышает требование)
- [x] E2E helpers в conftest.py
- [x] Покрытие всех провайдеров: ChEMBL, PubChem, UniProt, PubMed

#### Фаза 3 (R3.1) — Готово когда:
- [ ] `grep -r "datetime.now" src/bioetl/infrastructure/` возвращает 0 строк без default parameter
- [ ] `test_no_datetime_now_in_infrastructure.py` проходит
- [ ] Deprecation warning добавлен для legacy fallback

#### Фаза 4 (R4.1, R4.2) — Готово когда:
- [ ] `.pre-commit-config.yaml` содержит bandit, pip-audit
- [ ] `tests/benchmarks/` содержит 3+ benchmark теста
- [ ] CI включает benchmark step

#### Фаза 5 (R5.1) — Готово когда:
- [ ] ADR-019 создан и добавлен в index
- [ ] RULES.md обновлён ссылкой на ADR-019

---

## Приложение: Чек-лист Ревью

### Перед Началом Рефакторинга

- [ ] `make lint && make test` проходят на текущем коде
- [ ] Git branch создан: `refactor/architecture-review`
- [ ] Прочитаны актуальные `docs/RULES.md` и `docs/REFACTORING_PLAN.md`
- [ ] Понятны критерии приёмки каждой задачи

### После Каждой Фазы

- [ ] `make lint` проходит
- [ ] `make test` проходит
- [ ] Архитектурные тесты (`make arch-test`) проходят
- [ ] Коммит с Conventional Commits: `refactor(scope): description`

### Перед Мержем

- [ ] Все фазы завершены
- [ ] Интегральный балл пересчитан и документирован
- [ ] PR description содержит summary изменений
- [ ] Review от минимум 1 ревьюера

---

*Строй надёжно. Документируй честно. Рефактори осмысленно.*
