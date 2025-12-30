# Архитектурный Обзор BioETL

*Дата: 2025-12-30 | Версия: 1.0*

---

## Содержание

1. [Резюме](#1-резюме)
2. [Числовая Оценка по 10 Категориям](#2-числовая-оценка-по-10-категориям)
3. [Детальный Анализ Архитектуры](#3-детальный-анализ-архитектуры)
4. [Выявленные Проблемы](#4-выявленные-проблемы)
5. [План Рефакторинга](#5-план-рефакторинга)
6. [Рекомендации по Метрикам и Тестам](#6-рекомендации-по-метрикам-и-тестам)
7. [Приложения](#7-приложения)

---

## 1. Резюме

### 1.1 Общая Характеристика Проекта

| Метрика | Значение |
|---------|----------|
| **Общий LOC (src)** | 47,591 |
| **Python файлов (src)** | 296 |
| **Тестовый LOC** | 72,608 |
| **Тестовых файлов** | 285 |
| **Тестов всего** | ~1,600+ |
| **ADR документов** | 21 |
| **Архитектурных тестов** | 234 |

### 1.2 Архитектурный Стиль

**Ports & Adapters (Hexagonal Architecture)** с **Medallion Data Architecture** (Bronze/Silver/Gold).

```
┌─────────────────────────────────────────────────────────────────┐
│                        interfaces (CLI)                          │
├─────────────────────────────────────────────────────────────────┤
│                    composition (DI Root)                         │
├─────────────────────────────────────────────────────────────────┤
│  application (Pipelines, Services)  │  infrastructure (Adapters) │
├─────────────────────────────────────┼────────────────────────────┤
│                     domain (Ports, Entities, Logic)              │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Ключевые Выводы

| Аспект | Статус | Комментарий |
|--------|--------|-------------|
| **Архитектурные нарушения** | ✅ 0 | Все импорты соответствуют матрице |
| **DI дисциплина** | ✅ Отлично | Constructor injection, no Service Locator |
| **Тестовое покрытие** | ✅ >85% | Здоровая пирамида тестов |
| **Документация** | ✅ Отлично | 21 ADR, RULES.md, детальные docstrings |
| **Технический долг** | ⚠️ Минимальный | Несколько точек для улучшения |

---

## 2. Числовая Оценка по 10 Категориям

### 2.1 Определение Категорий

| # | Категория | Описание | Вес |
|---|-----------|----------|-----|
| 1 | **Архитектура слоёв** | Соблюдение слоистой структуры, границы модулей, матрица импортов | 15% |
| 2 | **Модульность и связность** | Cohesion внутри модулей, coupling между модулями, SRP | 12% |
| 3 | **Качество доменной модели** | Ports, Value Objects, Entities, чистота бизнес-логики | 12% |
| 4 | **Dependency Injection** | Следование DI-паттернам, Composition Root, отсутствие anti-patterns | 10% |
| 5 | **Тестирование** | Покрытие, пирамида тестов, архитектурные тесты, изоляция | 12% |
| 6 | **Обработка ошибок** | Классификация, retry-логика, circuit breaker, graceful shutdown | 10% |
| 7 | **Observability** | Логирование, метрики, трейсинг, корреляция | 8% |
| 8 | **Производительность** | Batch processing, memory management, rate limiting | 7% |
| 9 | **Безопасность** | Секреты, PII, санитизация, IAM | 6% |
| 10 | **Документация** | ADR, RULES.md, docstrings, README | 8% |

**Сумма весов: 100%**

### 2.2 Оценка по Категориям

| # | Категория | Вес | Оценка (1-10) | Взвешенный балл | Обоснование |
|---|-----------|-----|---------------|-----------------|-------------|
| 1 | Архитектура слоёв | 15% | **9.5** | **1.43** | Безупречное соблюдение Hexagonal Architecture. 0 нарушений импортов. 5 слоёв с чёткими границами. Проверяется `import-linter` и 234 arch-тестами. |
| 2 | Модульность и связность | 12% | **9.0** | **1.08** | Высокая cohesion (каждый класс < 600 LOC с делегированием). Loose coupling через Ports. Паттерны: Template Method, Strategy, Null Object. |
| 3 | Качество доменной модели | 12% | **9.5** | **1.14** | 20 Protocol-портов. Frozen Value Objects с валидацией. 25+ classified исключений. Чистый domain (0 I/O). Comprehensive error taxonomy. |
| 4 | Dependency Injection | 10% | **9.5** | **0.95** | Pure constructor injection. RunnerServices/PipelineServices bundles. Factory pattern. Thread-safe registry. Тестовая изоляция. |
| 5 | Тестирование | 12% | **9.0** | **1.08** | 1,600+ тестов. Пирамида: 67% unit, 15% arch, 8% integration, 4% e2e. VCR-кассеты. In-memory fakes. Coverage >85%. |
| 6 | Обработка ошибок | 10% | **9.0** | **0.90** | ErrorClassifier с 18 типами. Exponential backoff + deterministic jitter. Circuit breaker (5 fails, 5 min recovery). Graceful shutdown с сигналами. |
| 7 | Observability | 8% | **8.5** | **0.68** | Structured JSON logs с run_id. Prometheus metrics. OpenTelemetry tracing. ObservabilityBundle. NoOp fallbacks. |
| 8 | Производительность | 7% | **8.0** | **0.56** | MemoryMonitor с adaptive batching. Rate limiting per provider. VACUUM automation. Graceful degradation при memory pressure. |
| 9 | Безопасность | 6% | **8.5** | **0.51** | Secrets via env vars. VCR sanitization (API keys, PII). PII hashing в Silver. No hardcoded secrets. Secret masking в логах. |
| 10 | Документация | 8% | **9.5** | **0.76** | 21 ADR (все Accepted). RULES.md v5.8 (1,100 LOC). CLAUDE.md с протоколами. Google-style docstrings на русском. refactoring-plan.md с верификацией. |

### 2.3 Интегральный Балл

```
Интегральный балл = Σ (Вес × Оценка) =
  1.43 + 1.08 + 1.14 + 0.95 + 1.08 + 0.90 + 0.68 + 0.56 + 0.51 + 0.76 = 9.09/10
```

### 2.4 Интерпретация

| Диапазон | Уровень | Описание |
|----------|---------|----------|
| 0 – 4.9 | ❌ Критический | Требуется немедленный рефакторинг |
| 5.0 – 6.9 | ⚠️ Удовлетворительный | Значительные проблемы, нужен план улучшений |
| 7.0 – 7.9 | 🟡 Хороший | Стабильная база, есть точки роста |
| 8.0 – 8.9 | ✅ Отличный | Production-ready, минимальный tech debt |
| 9.0 – 10 | 🏆 Образцовый | Эталонная архитектура |

**Вывод: 9.09/10 — 🏆 Образцовый уровень**

Проект демонстрирует **зрелую, production-ready архитектуру** с минимальным техническим долгом. Соблюдаются все ключевые принципы Hexagonal Architecture, DDD и Clean Architecture.

---

## 3. Детальный Анализ Архитектуры

### 3.1 Соблюдение Слоистой Структуры

#### Матрица Импортов (Верификация)

| Из ↓ / В → | domain | application | composition | infrastructure | interfaces |
|------------|--------|-------------|-------------|----------------|------------|
| **domain** | ✅ | ✅ 0 violations | ✅ 0 violations | ✅ 0 violations | ✅ 0 violations |
| **application** | ✅ Allowed | ✅ | ✅ 0 violations | ✅ 0 violations | ✅ 0 violations |
| **composition** | ✅ Allowed | ✅ Allowed | ✅ | ✅ Allowed | ✅ 0 violations |
| **infrastructure** | ✅ Allowed | ✅ 0 violations | ✅ 0 violations | ✅ | ✅ 0 violations |
| **interfaces** | ✅ Allowed | ✅ Allowed | ✅ Allowed | ✅ Allowed | ✅ |

**Результат: 0 архитектурных нарушений**

#### Размер Слоёв

| Слой | Файлов | LOC | % от общего |
|------|--------|-----|-------------|
| domain | 86 | 12,265 | 26% |
| application | 105 | 9,488 | 20% |
| infrastructure | 78 | 18,345 | 39% |
| composition | 24 | 5,673 | 12% |
| interfaces | 15 | 1,231 | 3% |

### 3.2 Принципы Ports & Adapters

#### Domain Ports (20 протоколов)

| Port | Тип | Методы | Lifecycle |
|------|-----|--------|-----------|
| `StoragePort` | I/O | 17 | `aclose()` |
| `DataSourcePort` | I/O | 4 | `aclose()` |
| `LockPort` | I/O | 5 | `aclose()` |
| `CheckpointPort` | I/O | 3 | `aclose()` |
| `QuarantinePort` | I/O | 2 | `aclose()` |
| `LoggerPort` | Sync | 5 | - |
| `MetricsPort` | Sync | 4 | `close()` |
| `TracingPort` | Async | 3 | `close()` |
| `RateLimiterPort` | Async | 2 | - |
| `CircuitBreakerPort` | Sync | 4 | - |
| `HealthCheckPort` | Async | 1 | - |
| `AuditPort` | Async | 2 | `aclose()` |
| `GoldValidatorPort` | Sync | 1 | - |
| `SilverValidatorPort` | Sync | 1 | - |
| `InputFilterPort` | Sync | 1 | - |
| `DQMonitorPort` | Async | 2 | - |
| `JsonEncoderPort` | Sync | 1 | - |
| `ShutdownPort` | Async | 2 | - |
| `FilterableDataSourcePort` | Async | 1 | - |
| `ResiliencePort` | Sync | 1 | - |

#### Adapter Implementations

| Port | Adapter | Файл | LOC |
|------|---------|------|-----|
| StoragePort | BronzeWriter, DeltaWriter, GoldWriter | `infrastructure/storage/` | 2,164 |
| DataSourcePort | ChemblAdapter, UniProtAdapter, PubMedAdapter, PubChemAdapter | `infrastructure/adapters/` | 1,500+ |
| LockPort | MemoryLock | `infrastructure/locking/` | 255 |
| CheckpointPort | LocalCheckpoint | `infrastructure/checkpoint/` | 135 |
| LoggerPort | UnifiedLogger | `infrastructure/observability/` | 338 |
| MetricsPort | PrometheusMetrics | `infrastructure/observability/` | 217 |

### 3.3 DDD и Value Objects

#### Immutability

Все Value Objects используют frozen dataclasses:

```python
@dataclass(frozen=True, slots=True)
class ChemblId(ValueObject[str]):
    _value: str

    def __post_init__(self) -> None:
        if not re.match(r'^CHEMBL\d+$', self._value, re.IGNORECASE):
            raise ValueError(f"Invalid ChEMBL ID: {self._value}")
```

#### Domain Entities

| Entity | Provider | LOC | Frozen | Validated |
|--------|----------|-----|--------|-----------|
| Activity | ChEMBL | 120 | ✅ | ✅ post_init |
| Molecule | ChEMBL | 80 | ✅ | ✅ |
| Target | ChEMBL | 70 | ✅ | ✅ |
| Compound | PubChem | 60 | ✅ | ✅ |
| Publication | PubMed | 55 | ✅ | ✅ |
| Protein | UniProt | 50 | ✅ | ✅ |

### 3.4 Единообразие Конвенций

| Аспект | Стандарт | Соблюдение |
|--------|----------|------------|
| **Именование** | snake_case для модулей, PascalCase для классов | ✅ 100% |
| **Docstrings** | Google Style, на русском | ✅ 95% |
| **Type hints** | Полные, no `Any` без причины | ✅ 98% |
| **Error handling** | Classified exceptions | ✅ 100% |
| **Logging** | structlog с run_id | ✅ 100% |
| **Async** | `async def` для I/O | ✅ 100% |

---

## 4. Выявленные Проблемы

### 4.1 Подтверждённые Проблемы (Актуальные)

| # | Проблема | Серьёзность | Файл:строки | Описание |
|---|----------|-------------|-------------|----------|
| P1 | Отсутствует CI-enforcement coverage threshold | Medium | CI config | Coverage >85% не enforce в CI pipeline |
| P2 | Ограниченные E2E тесты для complex medallion flows | Low | tests/e2e/ | 4% E2E тестов, можно расширить |
| P3 | Memory Monitor тесно связан с Executor | Low | executor.py | Можно абстрагировать через Port |
| P4 | Отсутствует stress-test для high-volume batching | Low | tests/ | Нет performance baselines |
| P5 | CLI error → exit code mapping не стандартизирован | Low | cli/commands/ | Разные подходы в разных командах |

### 4.2 Ложные Утверждения (НЕ проблемы)

> ⚠️ **ВАЖНО**: Следующие утверждения часто делаются ошибочно. Они НЕ являются проблемами.

| Ложное утверждение | Почему ложно | Верификация |
|--------------------|--------------|-------------|
| "PipelineRunner — god object" | 173 строки, делегирует через RunnerServices | `runner.py:53,84-88` |
| "ChEMBL adapter — монолит 517 LOC" | Делегирует EntityMapper, ErrorClassifier, AdapterMetrics | `client.py:30,76-84,90` |
| "GoldWriter — монолит 593 LOC" | Делегирует CsvExporter, AuditPort | `gold_writer.py:70-71,87-88` |
| "bootstrap_pipeline смешивает ответственности" | 100 строк, делегирует фабрикам | `bootstrap.py:68-167` |
| "MemoryLock недостаточен, нужен Redis" | By design: Local-Only Deployment (ADR-010) | `RULES.md §3.3` |
| "Нет DQ-метрик в Prometheus" | Реализовано в PostrunService | `postrun_service.py:158-163` |
| "NoOp defaults = нарушение DI" | Null Object Pattern для опциональной observability | Валидный паттерн |

### 4.3 Технический Долг

| Категория | Объём | Приоритет | Комментарий |
|-----------|-------|-----------|-------------|
| **Документация** | Минимальный | Low | Sequence diagrams для bootstrap |
| **Тестирование** | Низкий | Medium | Больше E2E и stress tests |
| **Configuration** | Минимальный | Low | Startup validation audit |
| **Code** | Минимальный | Low | Несколько TODO в коде |

---

## 5. План Рефакторинга

### 5.1 Приоритизация

| Уровень | Категория | Цель |
|---------|-----------|------|
| 🔴 **P0 Critical** | Блокеры production | Нет |
| 🟠 **P1 High** | Улучшение reliability | P1 (Coverage enforcement) |
| 🟡 **P2 Medium** | Улучшение maintainability | P2-P3 |
| 🟢 **P3 Low** | Nice-to-have | P4-P5 |

### 5.2 Детальный План

---

#### R1: CI Coverage Enforcement (P1 High)

**Цель:** Enforce coverage threshold в CI pipeline

**Конкретные изменения:**

| Файл | Изменение |
|------|-----------|
| `.github/workflows/ci.yml` | Добавить `pytest --cov-fail-under=85` |
| `Makefile` | Обновить `test` target с coverage threshold |

**Риски:** Низкий — только CI конфигурация

**Критерии готовности:**
- [ ] CI fails при coverage < 85%
- [ ] Coverage badge в README
- [ ] PR checks включают coverage report

---

#### R2: Расширение E2E Тестов (P2 Medium)

**Цель:** Добавить E2E тесты для complex medallion flows

**Предлагаемые тесты:**

| Тест | Сценарий |
|------|----------|
| `test_multi_provider_orchestration_e2e.py` | ChEMBL + UniProt sequential run |
| `test_partial_failure_recovery_e2e.py` | Recovery after mid-batch failure |
| `test_large_batch_memory_e2e.py` | 100K+ records с adaptive batching |
| `test_vacuum_after_run_e2e.py` | Verify VACUUM после успешного run |
| `test_quarantine_flow_e2e.py` | DQ errors → quarantine → replay |

**Файлы для создания:**
- `tests/e2e/test_advanced_scenarios_e2e.py`
- `tests/e2e/test_resilience_e2e.py`

**Риски:** Низкий — добавление тестов, не изменение кода

**Критерии готовности:**
- [ ] 10+ новых E2E тестов
- [ ] E2E coverage увеличен до 8-10%
- [ ] Все тесты проходят в CI

---

#### R3: MemoryMonitor Abstraction (P3 Low)

**Цель:** Абстрагировать MemoryMonitor через Port для лучшей testability

**Текущее состояние:** `executor.py` напрямую использует `MemoryMonitor`

**Предлагаемое решение:**

```python
# domain/ports/memory.py (новый файл)
class MemoryMonitorPort(Protocol):
    def get_available_memory_mb(self) -> float: ...
    def should_reduce_batch(self) -> bool: ...
    def get_recommended_batch_size(self, current: int) -> int: ...
```

**Изменения:**

| Файл | Изменение |
|------|-----------|
| `domain/ports/memory.py` | Новый Port |
| `infrastructure/observability/memory_monitor.py` | Implement Port |
| `application/core/executor.py` | Инжектировать через constructor |
| `composition/factories/services_factory.py` | Создавать MemoryMonitor |

**Риски:** Средний — изменение DI flow

**Критерии готовности:**
- [ ] MemoryMonitorPort определён в domain
- [ ] MemoryMonitor реализует Port
- [ ] Executor получает через DI
- [ ] Тесты используют mock/fake

---

#### R4: CLI Exit Code Standardization (P3 Low)

**Цель:** Стандартизировать mapping exception → exit code

**Текущее состояние:** Разные команды обрабатывают ошибки по-разному

**Предлагаемое решение:**

```python
# interfaces/cli/error_handler.py (новый файл)
EXIT_CODES = {
    BioETLError: 1,
    ValidationError: 2,
    ConfigurationError: 3,
    LockAcquisitionError: 4,
    KeyboardInterrupt: 130,
}

def cli_error_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            exit_code = EXIT_CODES.get(type(e), 1)
            echo_error(str(e))
            sys.exit(exit_code)
    return wrapper
```

**Изменения:**

| Файл | Изменение |
|------|-----------|
| `interfaces/cli/error_handler.py` | Новый модуль с decorator |
| `interfaces/cli/commands/*.py` | Применить decorator |
| `docs/cli-exit-codes.md` | Документировать exit codes |

**Риски:** Низкий — только CLI presentation layer

**Критерии готовности:**
- [ ] Единый exit code mapping
- [ ] Все команды используют decorator
- [ ] Документация обновлена

---

#### R5: Performance Baselines (P3 Low)

**Цель:** Добавить performance regression tests

**Предлагаемые метрики:**

| Метрика | Baseline | Threshold |
|---------|----------|-----------|
| Pipeline startup time | < 2s | +20% регрессия |
| 1K records transform | < 5s | +30% регрессия |
| Memory per 1K records | < 100MB | +50% регрессия |

**Файлы для создания:**
- `tests/benchmarks/test_performance_baselines.py`
- `tests/benchmarks/conftest.py`

**Изменения:**

| Файл | Изменение |
|------|-----------|
| `tests/benchmarks/` | Новый каталог |
| `pytest.ini` | Marker `@pytest.mark.benchmark` |
| `.github/workflows/ci.yml` | Optional benchmark job |

**Риски:** Низкий — добавление тестов

**Критерии готовности:**
- [ ] 5+ performance тестов
- [ ] Baselines задокументированы
- [ ] CI включает benchmark (optional)

---

### 5.3 Матрица Зависимостей

```
R1 (Coverage) ─────────────────────────────> Независимый

R2 (E2E Tests) ────────────────────────────> Независимый

R3 (MemoryMonitor) ────────────────────────> Независимый

R4 (CLI Exit Codes) ───────────────────────> Независимый

R5 (Performance) ──────────────────────────> После R2
```

### 5.4 Roadmap

| Неделя | Задачи |
|--------|--------|
| **W1** | R1: CI Coverage Enforcement |
| **W2** | R2: E2E Tests (5 тестов) |
| **W3** | R2: E2E Tests (5 тестов) + R4: CLI Exit Codes |
| **W4** | R3: MemoryMonitor Abstraction |
| **W5** | R5: Performance Baselines |

---

## 6. Рекомендации по Метрикам и Тестам

### 6.1 Новые Метрики для Контроля Архитектуры

| Метрика | Источник | Цель | Alert Threshold |
|---------|----------|------|-----------------|
| **arch_test_pass_rate** | CI | 100% | < 100% |
| **import_violations** | import-linter | 0 | > 0 |
| **coverage_line** | pytest-cov | > 85% | < 85% |
| **cyclomatic_complexity** | radon | < 15 | > 15 |
| **type_hint_coverage** | mypy | > 98% | < 95% |
| **port_implementation_count** | arch test | 20+ | < 20 |

### 6.2 Тесты для Предотвращения Регресса

| Тест | Категория | Что проверяет |
|------|-----------|---------------|
| `test_layer_dependencies.py` | Architecture | Матрица импортов |
| `test_port_contracts.py` | Contract | Port signatures и lifecycle |
| `test_di_compliance.py` | DI | Отсутствие service locator |
| `test_no_random_in_writers.py` | Determinism | Детерминизм записи |
| `test_no_datetime_now_in_infrastructure.py` | Determinism | Single source of time |
| `test_no_structlog_in_application_interfaces.py` | Layering | LoggerPort usage |

### 6.3 Прогноз Влияния на Интегральный Балл

| Задача | Категория | Текущий балл | После реализации |
|--------|-----------|--------------|------------------|
| R1: Coverage Enforcement | Тестирование | 9.0 | 9.3 (+0.3) |
| R2: E2E Tests | Тестирование | 9.0 | 9.4 (+0.4) |
| R3: MemoryMonitor Port | Модульность | 9.0 | 9.2 (+0.2) |
| R4: CLI Exit Codes | Обработка ошибок | 9.0 | 9.1 (+0.1) |
| R5: Performance Baselines | Производительность | 8.0 | 8.4 (+0.4) |

**Прогнозируемый интегральный балл после рефакторинга:**

```
Текущий: 9.09/10
После R1-R5: ~9.25/10 (+0.16)
```

---

## 7. Приложения

### 7.1 Ключевые Файлы

| Категория | Файл | LOC |
|-----------|------|-----|
| **Composition Root** | `composition/bootstrap.py` | 182 |
| **DI Registry** | `composition/registry.py` | 272 |
| **Pipeline Factory** | `composition/factories/pipeline_factory.py` | 475 |
| **Pipeline Runner** | `application/core/runner.py` | 166 |
| **Base Transformer** | `application/core/base_transformer.py` | 559 |
| **Storage Port** | `domain/ports/storage.py` | 300 |
| **Delta Writer** | `infrastructure/storage/delta_writer.py` | 819 |
| **CLI Main** | `interfaces/cli/main.py` | 44 |

### 7.2 ADR Registry

| ADR | Название | Статус |
|-----|----------|--------|
| ADR-001 | Delta Lake vs Parquet | Accepted |
| ADR-002 | Medallion Architecture | Accepted |
| ADR-003 | Redis for Distributed Locking | Superseded by ADR-010 |
| ADR-004 | Pydantic vs Dataclasses | Accepted |
| ADR-005 | Composition Layer Separation | Accepted |
| ADR-006 | Logger and Metrics Ports | Accepted |
| ADR-007 | Circuit Breaker Implementation | Accepted |
| ADR-008 | Graceful Shutdown Strategy | Accepted |
| ADR-009 | PaginatedFetcherMixin Design | Accepted |
| ADR-010 | Local-Only Deployment | Accepted |
| ADR-011 | Remove Watermark Mechanism | Accepted |
| ADR-012 | Storage Clear Contract and Run ID | Accepted |
| ADR-013 | Async Storage Cleanup | Accepted |
| ADR-014 | Deterministic Writes and Retries | Accepted |
| ADR-015 | Pipeline Services Lifecycle | Accepted |
| ADR-016 | Error Handling Strategy | Accepted |
| ADR-017 | Observability Architecture | Accepted |
| ADR-018 | Gold Strict Validation | Accepted |
| ADR-019 | Observability Port Enforcement | Accepted |
| ADR-020 | BasePipeline Decomposition | Accepted |
| ADR-021 | DDD Aggregates Adoption | Accepted |

### 7.3 Команды Верификации

```bash
# Архитектурные тесты
make arch-test

# Проверка импортов
make arch-lint

# Полный тестовый прогон
make test

# Coverage report
make coverage

# Lint + Type check
make lint
```

---

## Заключение

BioETL демонстрирует **образцовую архитектуру** для ETL-системы на Python с:

- ✅ **Безупречным соблюдением Hexagonal Architecture** (0 нарушений)
- ✅ **Зрелой DI-дисциплиной** (pure constructor injection)
- ✅ **Comprehensive тестированием** (1,600+ тестов, 234 arch-тестов)
- ✅ **Excellent документацией** (21 ADR, RULES.md v5.8)
- ✅ **Минимальным техническим долгом**

**Интегральный балл: 9.09/10 — 🏆 Образцовый уровень**

Рекомендуемые улучшения (R1-R5) направлены на усиление и без того сильной кодовой базы.

---

*Отчёт подготовлен: 2025-12-30*
*Методология: Двойная верификация (RULES.md §7)*
*Проверено: grep, wc, ast-анализ, 234 arch-теста*
