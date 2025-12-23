# Архитектурный Обзор BioETL

*Версия: 1.0*
*Дата: 2025-12-23*
*Автор: Claude Code Architecture Review*

---

## Содержание

1. [Резюме](#1-резюме)
2. [Числовая оценка по 10 категориям](#2-числовая-оценка-по-10-категориям)
3. [Детальный анализ архитектуры](#3-детальный-анализ-архитектуры)
4. [Выявленные проблемы](#4-выявленные-проблемы)
5. [План рефакторинга](#5-план-рефакторинга)
6. [Приложения](#6-приложения)

---

## 1. Резюме

### 1.1 Общая характеристика

**BioETL** — production-grade фреймворк для ETL биоактивных данных, построенный на принципах:
- **Hexagonal Architecture (Ports & Adapters)** — строгое разделение слоёв
- **Medallion Architecture** — Bronze/Silver/Gold data layers
- **Domain-Driven Design** — изолированная доменная логика

### 1.2 Ключевые метрики

| Метрика | Значение |
|---------|----------|
| Python файлов (src/) | 95 |
| Тестовых файлов | 124 |
| Классов (всего) | 178 |
| Протоколов (Ports) | 9 |
| ADR документов | 12 |
| Покрытие тестами (цель) | >80% |

### 1.3 Интегральный балл: **7.4 / 10** (пересмотрено 2025-12-23)

**Интерпретация**: Проект находится в зоне **«Хорошо»** (5.0–7.9). Архитектура зрелая, документация обширная, но обнаружены **критические проблемы** (undefined variable, нарушение DI), требующие немедленного исправления.

> ⚠️ **Внимание**: Балл снижен с 7.6 до 7.4 из-за обнаружения BLOCKER-проблемы P1-NEW.

---

## 2. Числовая оценка по 10 категориям

### 2.1 Методология

- **Шкала**: 1-10 (1 — критические проблемы, 10 — эталонная реализация)
- **Веса**: Распределены по важности для production-системы (сумма = 100%)
- **Взвешенный балл**: Оценка × Вес

### 2.2 Таблица оценок

| # | Категория | Описание | Вес | Оценка | Взвешенный балл | Обоснование |
|---|-----------|----------|-----|--------|-----------------|-------------|
| 1 | **Архитектура слоёв** | Соблюдение Hexagonal Architecture, разделение domain/app/infra | 15% | 9 | 1.35 | Строгое соблюдение матрицы импортов. 4 контракта import-linter. 16 архитектурных тестов. |
| 2 | **Модульность и связность** | Низкая связанность, высокая связность модулей, чёткие границы | 12% | 8 | 0.96 | Хорошее разделение по провайдерам. Минус: отсутствуют `__init__.py` в 4 пакетах. |
| 3 | **Качество доменной модели** | Чистота domain layer, Value Objects, Entities, типизация | 12% | 9 | 1.08 | Frozen dataclasses, 9 Protocol-портов, NewType для семантики, CC ≤5. |
| 4 | **Тестирование** | Покрытие, стратегия (unit/integration/e2e/arch), VCR | 12% | 8 | 0.96 | 124 тест-файла. VCR.py для HTTP. Hypothesis. Минус: нет mutation testing в CI. |
| 5 | **Обработка ошибок** | Классификация, retry, circuit breaker, graceful shutdown | 10% | 9 | 0.90 | 20+ custom исключений. ADR-007 (CB), ADR-008 (Shutdown). Threshold-политики. |
| 6 | **Логирование и наблюдаемость** | Structured logging, метрики, tracing, correlation ID | 10% | 8 | 0.80 | structlog с run_id. Prometheus метрики. OpenTelemetry опционально. |
| 7 | **Производительность** | Delta Lake, батчинг, rate limiting, асинхронность | 8% | 7 | 0.56 | Async I/O. Delta merge. Минус: нет документированных бенчмарков. |
| 8 | **Безопасность** | Секреты, PII, валидация входных данных | 8% | 7 | 0.56 | Env-based secrets. PII hashing в Silver. Минус: нет pip-audit в CI. |
| 9 | **Качество документации** | ADR, RULES.md, README, docstrings, inline comments | 8% | 9 | 0.72 | 66 markdown файлов. 12 ADR. RULES.md v5.2. Полные docstrings. |
| 10 | **Технический долг и сопровождаемость** | Dead code, complexity, DRY, code smells | 5% | 7 | 0.35 | Vulture проверки. Минус: некоторые пустые файлы, дублирование в transformers. |

### 2.3 Расчёт интегрального балла

```
Интегральный балл = Σ (Взвешенный балл)
                  = 1.35 + 0.96 + 1.08 + 0.96 + 0.90 + 0.80 + 0.56 + 0.56 + 0.72 + 0.35
                  = 7.6
```

### 2.4 Интерпретация

| Диапазон | Статус | Описание |
|----------|--------|----------|
| 0.0 – 4.9 | 🔴 Критический | Требуется немедленный рефакторинг |
| 5.0 – 7.9 | 🟡 Хорошо | Есть области для улучшения |
| 8.0 – 10.0 | 🟢 Отлично | Production-ready, минимальные улучшения |

**Текущий статус**: 🟡 **Хорошо** (7.6)

---

## 3. Детальный анализ архитектуры

### 3.1 Соблюдение слоистой структуры

```
src/bioetl/
├── domain/          [9/10] ✓ Чистая логика, Protocols, frozen dataclasses
├── application/     [8/10] ✓ Пайплайны, Use Cases, оркестрация
├── composition/     [9/10] ✓ DI-контейнер, factories, bootstrap
├── infrastructure/  [8/10] ✓ Адаптеры, storage, observability
└── interfaces/      [7/10] ⚠ CLI минималистичен, orchestration пуст
```

### 3.2 Ports & Adapters (Hexagonal)

**Сильные стороны:**
- 9 Protocol-based портов в `domain/ports.py`
- Все порты используют `@runtime_checkable`
- Строгая типизация через `typing.Protocol`
- Асинхронные методы с `async/await`

**Порты:**
| Port | Назначение | Адаптеры |
|------|------------|----------|
| `DataSourcePort` | Источники данных | ChemblAdapter, PubChemAdapter, UniProtAdapter, PubMedClient |
| `StoragePort` | Хранение (Bronze/Silver/Gold) | BronzeWriter, DeltaWriter, GoldWriter |
| `LockPort` | Блокировки | MemoryLock |
| `CheckpointPort` | Чекпоинты | LocalCheckpoint |
| `QuarantinePort` | Карантин | UnifiedQuarantine |
| `MetricsPort` | Метрики | PrometheusMetrics, NoOpMetrics |
| `LoggerPort` | Логирование | structlog wrapper |
| `InputFilterPort` | Фильтрация | CsvFilterReader |
| `TracingPort` | Tracing | OpenTelemetryTracer, NoOpTracer |

### 3.3 Матрица импортов (СОБЛЮДАЕТСЯ)

```
| Из ↓ / В → | domain | application | composition | infrastructure | interfaces |
|------------|--------|-------------|-------------|----------------|------------|
| domain     | ✅     | ❌           | ❌           | ❌              | ❌          |
| application| ✅     | ✅           | ❌           | ❌              | ❌          |
| composition| ✅     | ✅           | ✅           | ✅              | ❌          |
| infrastructure| ✅  | ❌           | ❌           | ✅              | ❌          |
| interfaces | ✅     | ✅           | ✅           | ✅              | ✅          |
```

**Механизмы проверки:**
1. `.importlinter` — 4 контракта
2. `tests/architecture/test_layer_dependencies.py` — 16 тестов
3. `mypy --strict` — статическая проверка типов

### 3.4 Dependency Injection

**Реализация:**
- `composition/bootstrap.py` — Composition Root
- `composition/factories/` — Factory классы
- `composition/registry.py` — PipelineRegistry (singleton)

**Паттерн:**
```python
# bootstrap.py
def bootstrap_pipeline(ctx: PipelineRunContext) -> PipelineRunner:
    settings = get_settings()
    logger = bootstrap_logger(...)
    tracer = bootstrap_tracer()
    # ...
    return factory.create_runner(
        run_id=ctx.run_id,
        runtime=runtime_config,
        settings=settings,
        logger=logger,
        tracer=tracer,
        ...
    )
```

### 3.5 Единообразие соглашений

**Именование классов:**
| Паттерн | Пример |
|---------|--------|
| `{Provider}{Entity}Pipeline` | `ChEMBLActivityPipeline` |
| `{Entity}Transformer` | `ActivityTransformer` |
| `{Provider}Adapter` | `ChemblAdapter` |
| `{Service}Port` | `DataSourcePort` |
| `{Error}Error` | `SchemaViolationError` |

**Именование файлов:**
- snake_case для модулей: `base_transformer.py`
- `test_{module}.py` для тестов

---

## 4. Выявленные проблемы

### 4.1 Критические проблемы (Блокеры)

| ID | Проблема | Локация | Влияние |
|----|----------|---------|---------|
| ~~**P1**~~ | ~~Отсутствуют `__init__.py` в 4 пакетах~~ | — | ✅ **ИСПРАВЛЕНО** (2025-12-23) |
| **P1-NEW** | **Undefined variable `validated_records`** | `application/core/record_processor.py:279` | 🔴 **Код не работает!** Запись в Gold слой невозможна |
| **P2-NEW** | **Дублирование GoldValidator (нарушение DI)** | `application/core/record_processor.py:51-73` | 🔴 GoldValidator создаётся напрямую вместо инъекции |

#### P1-NEW: Undefined Variable `validated_records`

```python
# record_processor.py:262-282
async def _write_gold_batch(self, records: list[dict[str, Any]]) -> None:
    result = self._gold_validator.validate(records)
    if not result.valid:
        raise SchemaViolationError("gold", result.errors)
    # ...
    await self._storage.write_gold(
        # ...
        records=validated_records,  # ❌ UNDEFINED! Должно быть `records`
    )
```

**Исправление:**
```python
records=records,  # ✅ Использовать входной параметр
```

#### P2-NEW: Дублирование GoldValidator

```python
# record_processor.py:51-73
def __init__(
    self,
    # ...
    gold_validator: GoldValidatorPort | None = None,  # Инжектируется
):
    # ...
    self._gold_validator = gold_validator  # ❌ Затирается ниже!
    # ...
    # Gold layer validator (SRP)
    self._gold_validator = GoldValidator(config.gold_schema)  # ❌ Создаётся напрямую!
```

**Проблема:** Инжектированный `gold_validator` перезаписывается созданием нового экземпляра.

**Исправление:** Удалить строку 73, использовать только инжектированный валидатор.

### 4.2 Высокий приоритет

| ID | Проблема | Локация | Влияние |
|----|----------|---------|---------|
| **P2** | Дублирование логики трансформации | `*_transformer.py` файлы | DRY violation, увеличение maintenance cost |
| **P3** | Пустой модуль orchestration | `interfaces/orchestration/` | Incomplete abstraction |
| **P4** | Отсутствие pip-audit в CI | `pyproject.toml`, CI config | Security vulnerability exposure |

### 4.3 Средний приоритет

| ID | Проблема | Локация | Влияние |
|----|----------|---------|---------|
| **P5** | Нет бенчмарков производительности | — | Невозможно отслеживать регрессии |
| **P6** | PROJECT_CONTEXT.md не синхронизирован | `.claude/PROJECT_CONTEXT.md` | Устаревшая информация (Redis вместо MemoryLock) |
| **P7** | Некоторые пустые файлы | `composition/factories/clients.py` | Dead code |

### 4.4 Низкий приоритет

| ID | Проблема | Локация | Влияние |
|----|----------|---------|---------|
| **P8** | Mutation testing не в CI | — | Пропуск слабых тестов |
| **P9** | Нет contract tests в CI | — | Breakage detection delay |
| **P10** | Дублирование в документации | `CLAUDE.md`, `AGENT.md`, `PROJECT_CONTEXT.md` | Sync overhead |

---

## 5. План рефакторинга

### 5.1 Фаза 1: Критические исправления (Immediate)

#### 5.1.0 [BLOCKER] Исправить undefined variable `validated_records`

**Приоритет:** 🔴🔴🔴 **BLOCKER**
**Усилия:** 5 минут
**Файл:** `src/bioetl/application/core/record_processor.py:279`

```python
# Было (строка 279):
records=validated_records,

# Стало:
records=records,
```

**Критерии готовности:**
- [ ] Код изменён
- [ ] `make lint` проходит
- [ ] Тесты Gold слоя проходят

#### 5.1.1 [CRITICAL] Исправить дублирование GoldValidator

**Приоритет:** 🔴🔴 Критический
**Усилия:** 30 минут
**Файл:** `src/bioetl/application/core/record_processor.py:51-73`

```python
# Удалить строку 73:
self._gold_validator = GoldValidator(config.gold_schema)

# Изменить параметр на обязательный:
gold_validator: GoldValidatorPort,  # НЕ Optional
```

**Критерии готовности:**
- [ ] `gold_validator` — обязательный параметр
- [ ] Нет прямого создания `GoldValidator` в application layer
- [ ] Удалён импорт `from bioetl.application.core.gold_validator import GoldValidator`
- [ ] Architecture tests проходят

#### ~~5.1.2 Добавить отсутствующие `__init__.py`~~

~~**Приоритет:** 🔴 Критический~~
~~**Статус:** ✅ **ВЫПОЛНЕНО** (2025-12-23)~~

### 5.2 Фаза 2: Рефакторинг структуры (Short-term)

#### 5.2.1 Унификация трансформеров

**Приоритет:** 🟡 Высокий
**Усилия:** 2-4 часа

**Текущее состояние:**
- 12 файлов `*_transformer.py`
- Дублирование: валидация, логирование, метрики

**Предложение:**
1. Создать `BaseTransformer` с template methods
2. Вынести общую логику в base class
3. Использовать composition для специфичных операций

```python
# application/core/base_transformer.py (улучшенный)
class BaseTransformer(ABC):
    """Template pattern для трансформаций."""

    def transform(self, records: list[dict]) -> list[dict]:
        """Template method."""
        validated = self._validate_input(records)
        transformed = self._transform_records(validated)
        return self._validate_output(transformed)

    @abstractmethod
    def _transform_records(self, records: list[dict]) -> list[dict]:
        """Hook для специфичной логики."""
        ...
```

#### 5.2.2 Удалить пустые файлы

**Приоритет:** 🟡 Средний
**Усилия:** 30 минут

```bash
# Проверить и удалить
rm src/bioetl/composition/factories/clients.py
# Или добавить TODO с причиной существования
```

#### 5.2.3 Синхронизировать PROJECT_CONTEXT.md

**Приоритет:** 🟡 Средний
**Усилия:** 1 час

Обновить секции:
- §4 Блокировки → MemoryLock (не Redis)
- §8 Стек технологий → убрать Redis

### 5.3 Фаза 3: Улучшение качества (Medium-term)

#### 5.3.1 Добавить security scanning в CI

**Приоритет:** 🟡 Высокий
**Усилия:** 1-2 часа

```yaml
# .github/workflows/security.yml
name: Security Scan
on: [push, pull_request]
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: pip-audit
        run: pip-audit --strict
      - name: bandit
        run: bandit -r src/
```

#### 5.3.2 Добавить бенчмарки

**Приоритет:** 🟡 Средний
**Усилия:** 4-8 часов

```python
# tests/benchmarks/test_pipeline_performance.py
import pytest

@pytest.mark.benchmark
def test_transform_throughput(benchmark):
    """Измерение throughput трансформации."""
    records = generate_sample_records(1000)
    transformer = ActivityTransformer()
    result = benchmark(transformer.transform, records)
    assert len(result) == 1000
```

#### 5.3.3 Реализовать mutation testing

**Приоритет:** 🟢 Низкий
**Усилия:** 2-4 часа

```bash
# Добавить в CI
mutmut run --paths-to-mutate=src/bioetl/domain/
mutmut results
```

### 5.4 Фаза 4: Архитектурные улучшения (Long-term)

#### 5.4.1 Завершить orchestration layer

**Приоритет:** 🟢 Низкий
**Усилия:** 8-16 часов

Текущее состояние: `interfaces/orchestration/` содержит только `signals.py`.

**Предложение:**
1. Создать `PrefectOrchestrator` (если нужен Prefect)
2. Или удалить пустой модуль и документировать решение в ADR

#### 5.4.2 Консолидировать документацию

**Приоритет:** 🟢 Низкий
**Усилия:** 4-8 часов

**Текущее состояние:**
- `CLAUDE.md` — справочник для Claude Code
- `AGENT.md` — инструкции для агента
- `PROJECT_CONTEXT.md` — компактный контекст
- `docs/RULES.md` — конституция

**Предложение:**
1. Автоматическая генерация `PROJECT_CONTEXT.md` из `RULES.md`
2. Или объединить `CLAUDE.md` и `AGENT.md`

---

## 5.5 Сводная таблица плана

| Фаза | Задача | Приоритет | Усилия | Статус |
|------|--------|-----------|--------|--------|
| **1** | **Исправить `validated_records`** | 🔴🔴🔴 BLOCKER | 5 мин | ⏳ Ожидает |
| **1** | **Исправить дублирование GoldValidator** | 🔴🔴 | 30 мин | ⏳ Ожидает |
| ~~**1**~~ | ~~Добавить `__init__.py`~~ | ~~🔴~~ | ~~15 мин~~ | ✅ Выполнено |
| **2** | Унификация трансформеров | 🟡 | 2-4 ч | ⏳ Планируется |
| **2** | Удалить пустые файлы | 🟡 | 30 мин | ⏳ Планируется |
| **2** | Синхронизировать docs | 🟡 | 1 ч | ⏳ Планируется |
| **3** | Security scanning в CI | 🟡 | 1-2 ч | ⏳ Планируется |
| **3** | Бенчмарки | 🟡 | 4-8 ч | ⏳ Планируется |
| **3** | Mutation testing | 🟢 | 2-4 ч | ⏳ Планируется |
| **4** | Orchestration layer | 🟢 | 8-16 ч | ⏳ Планируется |
| **4** | Консолидация docs | 🟢 | 4-8 ч | ⏳ Планируется |

### 5.6 Ожидаемое изменение интегрального балла

| Этап | Задача | Изменение балла | Новый балл |
|------|--------|-----------------|------------|
| После 5.1.0 | Исправление `validated_records` | +0.10 | 7.50 |
| После 5.1.1 | Исправление DI GoldValidator | +0.15 | 7.65 |
| После Фазы 2 | Унификация, cleanup | +0.20 | 7.85 |
| После Фазы 3 | Security, benchmarks | +0.20 | **8.05** |

> 📈 После исправления критических проблем и выполнения Фазы 3 проект достигнет зоны **«Отлично»** (≥8.0).

---

## 6. Метрики и Критерии Качества

### 6.1 Автоматизированные Метрики

| Метрика | Инструмент | Текущее значение | Целевое значение | Связь с категорией |
|---------|------------|------------------|------------------|-------------------|
| **Line Coverage** | pytest-cov | — | ≥80% | #4 Тестирование |
| **Cyclomatic Complexity** | radon/xenon | — | CC ≤5 (domain), ≤10 (others) | #10 Сопровождаемость |
| **Architecture Contracts** | import-linter | — | 0 violations | #1 Архитектура слоёв |
| **Type Coverage** | mypy --strict | — | 0 errors | #3 Качество модели |
| **Linting** | ruff | — | 0 errors | #10 Сопровождаемость |
| **Security Issues** | bandit, pip-audit | — | 0 HIGH severity | #8 Безопасность |
| **Dead Code** | vulture | — | 0 items (conf 100%) | #10 Сопровождаемость |

### 6.2 Команды для Проверки

```bash
# Полная проверка качества
make quality            # lint + arch-lint + complexity + typecheck

# Отдельные проверки
make lint               # ruff + mypy
make arch-lint          # import-linter
make complexity         # xenon (CC thresholds)
make test               # pytest с coverage
make security           # pip-audit
```

### 6.3 CI/CD Рекомендации

1. **Pre-commit hooks:**
   - `make lint` перед каждым коммитом
   - Блокировка коммита при ошибках

2. **CI Pipeline:**
   - `make ci-lint` — все linting проверки
   - `make ci-test` — тесты + архитектурные тесты
   - `make security` — security scanning
   - Fail on coverage < 80%

3. **PR Gates:**
   - Все CI jobs должны пройти
   - Обязательный code review
   - Architecture test failures = blocker

### 6.4 Связь Метрик с Интегральным Баллом

| Категория | Автоматические метрики | Влияние на балл |
|-----------|------------------------|-----------------|
| #1 Архитектура | import-linter violations | -0.5 за каждое нарушение |
| #3 Доменная модель | mypy errors | -0.1 за каждые 10 ошибок |
| #4 Тестирование | coverage % | -0.2 за каждые 10% ниже 80% |
| #8 Безопасность | HIGH severity CVEs | -0.3 за каждую |
| #10 Сопровождаемость | CC > threshold | -0.1 за каждую функцию |

---

## 7. Приложения

### 7.1 Архитектурные решения (ADR)

| ADR | Название | Статус |
|-----|----------|--------|
| ADR-001 | Delta Lake vs Parquet | ✅ Accepted |
| ADR-002 | Medallion Architecture | ✅ Accepted |
| ADR-003 | Redis for Distributed Locking | ⛔ Superseded by ADR-010 |
| ADR-004 | Pydantic vs Dataclasses | ✅ Accepted |
| ADR-005 | Composition Layer Separation | ✅ Accepted |
| ADR-006 | Logger and Metrics Ports | ✅ Accepted |
| ADR-007 | Circuit Breaker Implementation | ✅ Accepted |
| ADR-008 | Graceful Shutdown Strategy | ✅ Accepted |
| ADR-009 | PaginatedFetcherMixin Design | ✅ Accepted |
| ADR-010 | Local-Only Deployment | ✅ Accepted |
| ADR-011 | Remove Watermark Mechanism | ✅ Accepted |

### 7.2 Статистика кода

```
src/bioetl/
├── domain/           9 файлов,  63 класса
├── application/     34 файла,  36 классов
├── composition/     11 файлов,  14 классов
├── infrastructure/  42 файла,  65 классов
└── interfaces/       4 файла,   0 классов (только функции)

tests/              124 файла
docs/                66 markdown файлов
configs/             13 YAML файлов
```

### 7.3 Зависимости проекта

**Core:**
- `httpx>=0.27` — async HTTP
- `pydantic>=2.0` — validation
- `polars>=1.0` — data processing
- `deltalake>=0.18` — Delta Lake
- `pyarrow>=15.0` — Arrow format
- `pandera>=0.20` — schema validation

**Observability:**
- `prometheus-client>=0.20` — metrics
- `structlog>=24.0` — logging
- `opentelemetry-*` — tracing (optional)

**Dev:**
- `pytest>=8.0`, `hypothesis>=6.100` — testing
- `mypy>=1.10`, `ruff>=0.4` — static analysis
- `import-linter>=2.0` — architecture enforcement
- `vulture>=2.11`, `radon>=6.0` — code quality

---

## Заключение

Проект **BioETL** демонстрирует зрелую архитектуру с:
- ✅ Строгим соблюдением Hexagonal Architecture
- ✅ Comprehensive error handling и observability
- ✅ Обширной документацией (12 ADR, 66 docs)
- ✅ Автоматизированными архитектурными проверками

**Области для улучшения:**
- 🔴 Структурные дефекты (отсутствующие `__init__.py`)
- 🟡 Дублирование в трансформерах
- 🟡 Security scanning в CI
- 🟢 Бенчмарки и mutation testing

**Рекомендация:** Начать с Фазы 1 (критические исправления), затем последовательно выполнять Фазы 2-4 в рамках sprint planning.

---

*Документ сгенерирован автоматически на основе анализа кодовой базы.*
