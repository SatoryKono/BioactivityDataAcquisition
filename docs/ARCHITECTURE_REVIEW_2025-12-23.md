# Архитектурный Обзор BioETL

**Дата:** 2025-12-23
**Версия проекта:** v5.2 (Local-Only Deployment)
**Автор:** Claude Code (Architecture Review)

---

## Содержание

1. [Резюме](#1-резюме)
2. [Числовая оценка по 10 категориям](#2-числовая-оценка-по-10-категориям)
3. [Детальный анализ архитектуры](#3-детальный-анализ-архитектуры)
4. [Выявленные проблемы](#4-выявленные-проблемы)
5. [План рефакторинга](#5-план-рефакторинга)
6. [Рекомендации](#6-рекомендации)

---

## 1. Резюме

### Общие метрики

| Метрика | Значение |
|---------|----------|
| Python файлов (src) | 125 |
| Python файлов (tests) | 122 |
| Строк кода (src) | ~10,400 |
| Пайплайнов | 8 |
| Провайдеров | 4 (ChEMBL, PubChem, PubMed, UniProt) |
| Портов (Protocols) | 10 |
| Архитектурных тестов | 16 |
| VCR кассет | 10 |
| ADR документов | 10 |

### Интегральная оценка

| Показатель | Значение |
|------------|----------|
| **Общий балл** | **8.56 / 10** |
| **Уровень зрелости** | Высокий (Production-Ready) |
| **Статус** | ✅ Соответствует Hexagonal Architecture |

---

## 2. Числовая оценка по 10 категориям

### Методология

- **Шкала:** 1-10 (1 = критично плохо, 10 = образцово)
- **Веса:** Распределены по важности для ETL-системы
- **Взвешенный балл:** Оценка × Вес

### Таблица оценок

| # | Категория | Описание | Вес | Оценка | Взвешенный балл | Обоснование |
|---|-----------|----------|-----|--------|-----------------|-------------|
| 1 | **Архитектура слоёв** | Соблюдение Ports & Adapters, изоляция слоёв, направление зависимостей | 0.15 | **9.5** | 1.425 | Идеальное разделение: domain→application→infrastructure. Матрица импортов соблюдена на 100%. 16 архитектурных тестов + import-linter. |
| 2 | **Модульность и связность** | Low coupling, high cohesion, чёткие границы модулей | 0.12 | **9.0** | 1.080 | Каждый слой имеет чёткую ответственность. GenericPipelineFactory снижает boilerplate. BaseTransformer обеспечивает DRY. |
| 3 | **Качество доменной модели** | Богатство домена, инварианты, Value Objects, бизнес-логика | 0.12 | **8.5** | 1.020 | 8 полноценных entity (Activity, Compound, Protein и др.). Frozen dataclasses, валидация в __post_init__. Порты через Protocol. |
| 4 | **Тестирование** | Покрытие, стратегия тестирования, качество тестов | 0.12 | **7.5** | 0.900 | 122 тестовых файла. Unit + Integration + Architecture тесты. VCR.py для HTTP. **Минус:** E2E тесты почти отсутствуют (только conftest.py). |
| 5 | **Обработка ошибок** | Классификация, retry, circuit breaker, quarantine | 0.10 | **9.0** | 0.900 | 3-уровневая классификация (Critical/Recoverable/DQ). Circuit Breaker (ADR-007). Graceful Shutdown (ADR-008). Unified Quarantine. |
| 6 | **Логирование и Observability** | Структурированные логи, метрики, трассировка | 0.08 | **8.5** | 0.680 | structlog с run_id. PrometheusMetrics. OpenTelemetry tracing. Log Schema соответствует RULES.md §3.2.1. |
| 7 | **Производительность** | Async I/O, batching, rate limiting, Delta Lake | 0.08 | **8.0** | 0.640 | Async httpx. Batch processing с configurable size. RateLimiter + TokenBucket. Delta Lake для ACID. **Минус:** нет профилирования. |
| 8 | **Безопасность** | Secrets management, PII handling, input validation | 0.08 | **7.5** | 0.600 | Secrets через os.environ (BIOETL_*). VCR санитизация. **Минус:** salted hashing для PII в Silver документирован, но не проверен в коде. |
| 9 | **Качество документации** | RULES.md, ADR, docstrings, CLAUDE.md | 0.08 | **9.0** | 0.720 | Превосходная документация: RULES.md v5.2, 10 ADR, CLAUDE.md, AGENT.md. Google-style docstrings. RFC 2119 governance. |
| 10 | **Технический долг и сопровождаемость** | Чистота кода, отсутствие хаков, расширяемость | 0.07 | **8.5** | 0.595 | Чистый код. Type hints везде. Ruff + mypy. PipelineRegistry для расширения. **Минус:** некоторые TODO в коде. |

### Итоговый расчёт

```
Σ(Оценка × Вес) = 1.425 + 1.080 + 1.020 + 0.900 + 0.900 + 0.680 + 0.640 + 0.600 + 0.720 + 0.595
                = 8.56

Сумма весов = 1.00 (проверка: 0.15+0.12+0.12+0.12+0.10+0.08+0.08+0.08+0.08+0.07 = 1.00) ✓

Интегральный балл: 8.56 / 10
```

### Интерпретация

| Диапазон | Статус | Описание |
|----------|--------|----------|
| 0.0 – 4.9 | 🔴 Критично | Требуется срочный рефакторинг |
| 5.0 – 7.9 | 🟡 Удовлетворительно | Есть значительные проблемы |
| **8.0 – 10.0** | **🟢 Хорошо/Отлично** | **Production-ready, минорные улучшения** |

**Вывод:** Проект BioETL демонстрирует **высокий уровень архитектурной зрелости (8.56/10)**. Это production-ready система с образцовым соблюдением Hexagonal Architecture.

---

## 3. Детальный анализ архитектуры

### 3.1. Структура слоёв

```
src/bioetl/
├── domain/           # 10 файлов - Чистая логика, Protocols, Entities
├── application/      # 36 файлов - Pipelines, Use Cases, Core
│   ├── core/         # Runner, Executor, RecordProcessor
│   ├── pipelines/    # ChEMBL, PubChem, PubMed, UniProt
│   └── observability/
├── composition/      # 13 файлов - DI, Factories, Registry
├── infrastructure/   # 62 файла - Adapters, Storage, Observability
└── interfaces/       # 6 файлов - CLI
```

### 3.2. Соблюдение матрицы импортов

| Из ↓ / В → | domain | application | composition | infrastructure | interfaces |
|------------|--------|-------------|-------------|----------------|------------|
| **domain** | ✅ | ✅ Нет | ✅ Нет | ✅ Нет | ✅ Нет |
| **application** | ✅ | ✅ | ✅ Нет | ✅ Нет | ✅ Нет |
| **composition** | ✅ | ✅ | ✅ | ✅ | ✅ Нет |
| **infrastructure** | ✅ | ✅ Нет* | ✅ Нет | ✅ | ✅ Нет |
| **interfaces** | ✅ | ✅ | ✅ | ✅ | ✅ |

*Исключение: `infrastructure/config.py` может импортировать PipelineConfig (документировано в тестах).

**Результат: ~100% соответствие** — практически ни одного нарушения матрицы импортов.

### 3.3. Ports & Adapters

**10 определённых портов (domain/ports.py):**

| Port | Реализация(и) | Статус |
|------|---------------|--------|
| `DataSourcePort` | ChemblAdapter, PubChemAdapter, PubMedAdapter, UniProtAdapter | ✅ |
| `StoragePort` | StorageAdapter (Bronze+Delta+Gold Writers) | ✅ |
| `LockPort` | MemoryLock | ✅ |
| `CheckpointPort` | LocalCheckpoint | ✅ |
| `QuarantinePort` | UnifiedQuarantine | ✅ |
| `MetricsPort` | PrometheusMetrics, NoOpMetrics | ✅ |
| `LoggerPort` | structlog BoundLogger | ✅ |
| `TracingPort` | OpenTelemetryTracer, NoOpTracer | ✅ |
| `OrchestrationPort` | **УДАЛИТЬ** — мёртвый код | ❌ |
| `InputFilterPort` | CSVFilterReader | ✅ |

### 3.4. Dependency Injection

**Composition Root:** `src/bioetl/composition/bootstrap.py`

```python
# Образцовый паттерн DI
def bootstrap_pipeline(ctx: PipelineRunContext) -> PipelineRunner:
    settings = get_settings()
    logger = bootstrap_logger(pipeline=ctx.pipeline_name, run_id=ctx.run_id)
    tracer = bootstrap_tracer()
    yaml_config = load_pipeline_config(ctx.pipeline_name)

    # Factory создаёт Runner со всеми зависимостями
    pipeline_def = PipelineRegistry.get(ctx.pipeline_name)
    factory = pipeline_def.factory

    return factory.create_runner(
        run_id=ctx.run_id,
        runtime=runtime_config,
        settings=settings,
        logger=logger,
        tracer=tracer,
        ...
    )
```

**Оценка:** Зависимости инжектируются через конструкторы. Никакого `new` внутри бизнес-логики.

### 3.5. Domain-Driven Design

**Entities (frozen dataclasses):**
- `BaseEntity` — базовый класс с lineage metadata
- `Activity`, `Compound`, `Protein`, `Publication`, `Document`, `Target`, `Molecule`, `Assay`

**Инварианты:**
```python
@dataclass(frozen=True, kw_only=True)
class Activity(BaseEntity):
    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.activity_id:
            raise ValueError("Activity ID is required")
        if self.pchembl_value is not None and self.pchembl_value < 0:
            raise ValueError(f"pChemBL value must be non-negative")
```

**Оценка:** Богатая доменная модель с явными инвариантами.

### 3.6. Circuit Breaker и Resilience

```python
# infrastructure/adapters/http/circuit_breaker.py
@dataclass
class CircuitBreaker:
    provider: str
    failure_threshold: int = 5      # 5 consecutive errors
    recovery_timeout: int = 300     # 5 minutes

    # State machine: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
```

**Паттерны устойчивости:**
- ✅ Circuit Breaker (ADR-007)
- ✅ Graceful Shutdown (ADR-008)
- ✅ Rate Limiting (TokenBucket)
- ✅ Retry with Exponential Backoff

---

## 4. Выявленные проблемы

### 4.1. Критические (Blockers) — 0 шт.

Критических нарушений архитектуры не обнаружено.

### 4.2. Значительные (Major) — 3 шт.

| # | Проблема | Локация | Влияние | Приоритет |
|---|----------|---------|---------|-----------|
| M1 | **E2E тесты отсутствуют** | `tests/e2e/` | Нет сквозного тестирования полного цикла pipeline | P1 |
| M2 | **OrchestrationPort — мёртвый код** | `domain/ports.py` | Порт определён, но не используется и не планируется. **MUST удалить.** | P2 |
| M3 | **Недостаточно VCR кассет** | `tests/fixtures/vcr/` | 10 кассет для 8 пайплайнов = неполное покрытие | P2 |

### 4.3. Минорные (Minor) — 6 шт.

| # | Проблема | Локация | Рекомендация |
|---|----------|---------|--------------|
| m1 | TODO комментарии в коде | Разбросаны | Создать Issues в трекере |
| m2 | Дублирование логики в transformers | `pipelines/*/transformer.py` | Вынести общую логику в BaseTransformer |
| m3 | Hardcoded batch_size=100 | `executor.py:27` | Вынести в конфиг |
| m4 | Gold layer недоиспользован | `storage/gold_writer.py` | Добавить агрегации и витрины |
| m5 | Нет health check для всех провайдеров | adapters | Унифицировать health probes |
| m6 | Отсутствует профилирование | — | Добавить py-spy / cProfile интеграцию |

### 4.4. Архитектурные наблюдения

**Сильные стороны:**
1. ✅ Идеальное соблюдение Hexagonal Architecture
2. ✅ Полная изоляция слоёв (0 критических нарушений)
3. ✅ 16 автоматических архитектурных тестов
4. ✅ import-linter с 4 контрактами
5. ✅ BaseTransformer — DRY для трансформаций
6. ✅ GenericPipelineFactory — уменьшает boilerplate
7. ✅ Circuit Breaker + Graceful Shutdown
8. ✅ Unified Quarantine для DQ errors
9. ✅ 10 ADR документов с историей решений

**Потенциальные риски:**
1. ⚠️ Зависимость от Delta Lake (vendor lock-in, но обоснован в ADR-001)
2. ⚠️ MemoryLock не подходит для распределённой среды (документировано в ADR-010)
3. ⚠️ Нет автоматического backup/restore

---

## 5. План рефакторинга

### Фаза 1: Критические улучшения (P1)

#### 1.1. Добавить E2E тесты
**Файлы:** `tests/e2e/`

```python
# tests/e2e/test_pipeline_e2e.py
@pytest.mark.e2e
async def test_chembl_activity_full_cycle():
    """E2E: ChEMBL Activity pipeline от fetch до Gold."""
    ctx = create_test_context("chembl_activity", limit=10)
    runner = bootstrap_pipeline(ctx)

    await runner.run()

    # Verify Bronze
    assert_bronze_files_exist(ctx)
    # Verify Silver
    assert_silver_table_has_records(ctx, expected_count=10)
    # Verify Gold
    assert_gold_aggregations_computed(ctx)
```

**Оценка трудозатрат:** 2-3 дня

### Фаза 2: Улучшение тестового покрытия (P2)

#### 2.1. Расширить VCR кассеты
**Цель:** Минимум 2 кассеты на pipeline (success + error case)

| Pipeline | Текущие | Цель |
|----------|---------|------|
| chembl_activity | 2 | 3 |
| chembl_molecule | 1 | 2 |
| chembl_target | 1 | 2 |
| chembl_assay | 1 | 2 |
| chembl_document | 1 | 2 |
| pubchem_compound | 1 | 2 |
| pubmed_publications | 1 | 2 |
| uniprot_protein | 2 | 3 |

**Оценка трудозатрат:** 1-2 дня

#### 2.2. Удалить OrchestrationPort (MUST)
**Решение:** Порт не используется и не планируется к реализации. Удалить мёртвый код.

**Файлы для изменения:**
1. `src/bioetl/domain/ports.py` — удалить класс `OrchestrationPort`
2. `src/bioetl/domain/ports.py` — удалить из `__all__`
3. Проверить отсутствие импортов в других модулях

```python
# Удалить из domain/ports.py:
@runtime_checkable
class OrchestrationPort(Protocol):
    """Port for pipeline orchestration."""
    ...
```

**Оценка трудозатрат:** 0.5 дня

### Фаза 3: Консолидация и DRY (P3)

#### 3.1. Вынести общую логику transformers
**Проблема:** Дублирование в `_transform_record()` разных transformers.

**Решение:**
```python
# application/core/base_transformer.py
class BaseTransformer:
    def _normalize_dates(self, record: dict) -> dict:
        """Общая нормализация дат ISO 8601."""
        ...

    def _handle_null_values(self, record: dict) -> dict:
        """Общая обработка NULL/None."""
        ...
```

**Оценка трудозатрат:** 1 день

#### 3.2. Параметризовать batch_size
**Текущее:** `DEFAULT_BATCH_SIZE = 100` hardcoded

**Решение:**
```yaml
# configs/pipelines/chembl/activity.yaml
pipeline:
  batch_size: 100
  checkpoint_interval: 1000
```

**Оценка трудозатрат:** 0.5 дня

### Фаза 4: Gold Layer развитие (P3)

#### 4.1. Добавить агрегации
**Цель:** Gold слой должен содержать бизнес-витрины, а не просто копию Silver.

```python
# application/gold/aggregations.py
async def compute_activity_stats_by_target() -> DataFrame:
    """Агрегация активностей по target_chembl_id."""
    ...

async def compute_compound_drug_properties() -> DataFrame:
    """Витрина drug-like свойств молекул."""
    ...
```

**Оценка трудозатрат:** 3-5 дней

### Сводная таблица плана

| Фаза | Задача | Приоритет | Трудозатраты | Результат |
|------|--------|-----------|--------------|-----------|
| 1 | E2E тесты | P1 | 2-3 дня | +E2E coverage |
| 2.1 | Расширить VCR | P2 | 1-2 дня | +Integration coverage |
| 2.2 | **Удалить OrchestrationPort** | P2 (MUST) | 0.5 дня | -Мёртвый код |
| 3.1 | DRY transformers | P3 | 1 день | -Дублирование |
| 3.2 | Параметризация batch | P3 | 0.5 дня | +Гибкость |
| 4.1 | Gold агрегации | P3 | 3-5 дней | +Business value |

**Общая оценка:** 7.5-12 дней разработки

---

## 6. Рекомендации

### Краткосрочные (1-2 недели)

1. **Добавить E2E тесты** — критически важно для уверенности в production
2. **Расширить VCR покрытие** — предотвращает регрессии при изменениях API
3. **Убрать TODO** — перенести в Issue tracker

### Среднесрочные (1 месяц)

1. **Развить Gold Layer** — добавить бизнес-агрегации
2. **Добавить профилирование** — py-spy для production debugging
3. **Автоматизировать Game Days** — DR тестирование

### Долгосрочные (квартал)

1. **Подготовить к распределённому развёртыванию** — Redis locks (ADR-003), S3 checkpoints
2. **Добавить Data Contracts тестирование** — consumer-driven contracts
3. **Расширить провайдеры** — OpenAlex, Semantic Scholar, Crossref

---

## Приложение A: Архитектурные метрики

### Cyclomatic Complexity (Domain Layer)

| Файл | Max CC | Статус |
|------|--------|--------|
| entities.py | 3 | ✅ ≤5 |
| transformations.py | 4 | ✅ ≤5 |
| error_classifier.py | 4 | ✅ ≤5 |
| ports.py | 1 | ✅ ≤5 |

### Coupling (между модулями)

```
domain ← application ← composition → infrastructure
                ↑
            interfaces
```

Направление зависимостей корректное. Циклических зависимостей нет.

### Cohesion Score

| Слой | Cohesion | Описание |
|------|----------|----------|
| domain | Высокий | Все сущности связаны с биоактивностью |
| application | Высокий | Core + Pipelines логически разделены |
| infrastructure | Средний | Много разнородных адаптеров |
| composition | Высокий | Только DI и фабрики |
| interfaces | Высокий | Только CLI |

---

## Приложение B: Архитектурные тесты

**16 тестов в `tests/architecture/test_layer_dependencies.py`:**

1. `test_domain_layer_no_infrastructure_imports` — Domain не импортирует I/O библиотеки
2. `test_domain_layer_no_application_imports` — Domain не зависит от Application
3. `test_domain_layer_no_infrastructure_layer_imports` — Domain не импортирует Infrastructure
4. `test_application_layer_no_infrastructure_implementation_imports` — Application не зависит от конкретных адаптеров
5. `test_ports_defined_in_domain_layer` — Порты определены в Domain
6. `test_infrastructure_imports_domain_ports` — Infrastructure реализует Domain порты
7. `test_import_linter_contracts` — Проверка import-linter контрактов
8. `test_infrastructure_does_not_import_application` — Infrastructure не импортирует Application
9. `test_domain_layer_uses_protocol_for_ports` — Порты используют Protocol
10. `test_cyclomatic_complexity_domain_layer` — CC ≤ 5 в Domain
11. `test_no_empty_source_files` — Нет пустых файлов
12. `test_no_orphan_directories` — Нет "мёртвых" директорий
13. `test_dead_code_vulture` — Нет неиспользуемого кода (vulture)
14. `test_application_layer_no_orchestration_imports` — Application не импортирует Prefect/Celery
15. `test_application_layer_no_infrastructure_imports` — Application не импортирует Infrastructure
16. `test_domain_value_objects_are_frozen` — Domain entities immutable (frozen=True)

---

## Приложение C: ADR (Architecture Decision Records)

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

---

## История изменений

| Версия | Дата | Автор | Изменения |
|--------|------|-------|-----------|
| 1.0 | 2025-12-23 | Claude Code | Полный архитектурный обзор |

---

*Строй надёжно. Документируй честно. Спрашивай смело.*
