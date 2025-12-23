# Архитектурный обзор BioETL

*Версия: 1.0 | Дата: 2025-12-23*

---

## 1. Резюме (Executive Summary)

Проект BioETL демонстрирует **зрелую архитектуру** с хорошо структурированным разделением слоёв по принципу Hexagonal Architecture (Ports & Adapters). Проект находится в состоянии **Production Ready (v5.0)** с серьёзной документацией и развитой инфраструктурой для тестирования и мониторинга.

**Ключевые сильные стороны:**
- Чёткое разделение на 5 слоёв (domain, application, composition, infrastructure, interfaces)
- Строгие архитектурные ограничения, проверяемые тестами
- Развитая система портов (Protocols) для инверсии зависимостей
- Хорошая документация с RFC 2119 governance

**Области для улучшения:**
- Некоторое дублирование кода в трансформерах пайплайнов
- Возможна оптимизация фабричного слоя
- Требуется унификация обработки ошибок в адаптерах

---

## 2. Числовая оценка проекта по 10 категориям

### 2.1. Методология оценки

Каждая категория оценивается по 10-балльной шкале:
- **1-3**: Критично — требует немедленного вмешательства
- **4-5**: Недостаточно — существенные проблемы
- **6-7**: Удовлетворительно — есть место для улучшения
- **8-9**: Хорошо — соответствует лучшим практикам
- **10**: Отлично — образец для подражания

### 2.2. Таблица оценок

| # | Категория | Описание | Вес | Оценка | Взв. балл | Обоснование |
|---|-----------|----------|-----|--------|-----------|-------------|
| 1 | **Архитектура слоёв** | Соблюдение Hexagonal/Ports&Adapters, матрица импортов | 15% | 9 | 1.35 | Чёткое разделение 5 слоёв, автоматизированные проверки в `tests/architecture/` |
| 2 | **Модульность и связность** | Low coupling, high cohesion, чистые интерфейсы | 12% | 8 | 0.96 | PipelineServices как frozen dataclass, хорошая DI через composition root |
| 3 | **Качество доменной модели** | Чистота domain layer, Value Objects, Entities | 12% | 8 | 0.96 | Чистый домен без I/O, типизированные исключения, Protocol-based ports |
| 4 | **Тестирование** | Покрытие, уровни тестов, архитектурные тесты | 12% | 8 | 0.96 | Unit/Integration/E2E/Architecture tests, VCR.py, target 80% coverage |
| 5 | **Обработка ошибок** | Классификация, retry, circuit breaker | 10% | 9 | 0.90 | ErrorClassifier, иерархия исключений, пороги DQ, graceful shutdown |
| 6 | **Логирование и observability** | structlog, метрики, tracing | 8% | 8 | 0.64 | Prometheus metrics, correlation ID, structured logging, TracingPort |
| 7 | **Производительность** | Async/await, rate limiting, пагинация | 8% | 7 | 0.56 | TokenBucket, async generators, но Delta Lake блокирующий через run_in_executor |
| 8 | **Безопасность** | PII, secrets, SAST инструменты | 8% | 8 | 0.64 | Bandit, pip-audit, централизованные env vars, PII hashing |
| 9 | **Качество документации** | RULES.md, ADRs, docstrings, CLAUDE.md | 8% | 9 | 0.72 | Comprehensive docs, 10 ADRs, RFC 2119, Google-style docstrings |
| 10 | **Техдолг и сопровождаемость** | Dead code, complexity, type safety | 7% | 7 | 0.49 | mypy strict, vulture checks, но есть deprecated files и возможное дублирование |

### 2.3. Итоговый балл

**Интегральный балл: 8.18 / 10.0**

### 2.4. Интерпретация

| Диапазон | Статус | Рекомендации |
|----------|--------|--------------|
| 0.0 – 4.9 | Критично | Немедленный рефакторинг |
| 5.0 – 7.9 | Удовлетворительно | Планомерные улучшения |
| **8.0 – 10.0** | **Хорошо/Отлично** | **Поддержание и оптимизация** |

**Вывод:** Проект находится в состоянии **"Хорошо"** — архитектура качественная, соблюдаются стандарты, но есть возможности для точечной оптимизации.

---

## 3. Детальный анализ архитектуры

### 3.1. Структура слоёв

```
src/bioetl/
├── domain/           # ✅ Чистый, без I/O
│   ├── ports.py      # 9 Protocol-based ports
│   ├── types.py      # NewType aliases, Enums
│   ├── entities.py   # Frozen dataclasses
│   ├── exceptions.py # Hierarchical exceptions
│   └── transformations.py # Pure functions
│
├── application/      # ✅ Use Cases, оркестрация
│   ├── core/         # Runner, Executor, RecordProcessor
│   ├── pipelines/    # Entity-specific pipelines
│   └── observability/# PipelineObserver
│
├── composition/      # ✅ DI Container
│   ├── bootstrap.py  # Composition Root
│   ├── registry.py   # PipelineRegistry
│   └── factories/    # GenericPipelineFactory pattern
│
├── infrastructure/   # ✅ Adapters, реализация портов
│   ├── adapters/     # chembl, pubchem, uniprot, http
│   ├── storage/      # Bronze/Silver/Gold writers
│   ├── locking/      # MemoryLock
│   ├── checkpoint/   # LocalCheckpoint
│   ├── quarantine/   # UnifiedQuarantine
│   └── observability/# PrometheusMetrics, structlog
│
└── interfaces/       # ✅ CLI, Signals
    ├── cli.py        # Click-based CLI
    └── orchestration/# Shutdown handlers
```

### 3.2. Соответствие матрице импортов

Проверка архитектурных ограничений (`tests/architecture/test_layer_dependencies.py`):

| Из ↓ / В → | domain | application | composition | infrastructure | interfaces |
|------------|--------|-------------|-------------|----------------|------------|
| **domain** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **application** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **composition** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **infrastructure** | ✅ | ❌* | ❌ | ✅ | ❌ |
| **interfaces** | ✅ | ✅ | ✅ | ✅ | ✅ |

*Исключение: `infrastructure/config.py` может импортировать `PipelineConfig` для валидации

**Статус:** Полное соответствие матрице. Проверяется 16+ архитектурными тестами.

### 3.3. Следование Ports & Adapters

**Сильные стороны:**
1. Все порты определены как `typing.Protocol` с `@runtime_checkable`
2. Адаптеры реализуют порты через структурное соответствие
3. Composition Root (`bootstrap.py`) — единственное место сборки зависимостей
4. `PipelineServices` — frozen dataclass с инжектированными зависимостями

**Найденные порты (9):**
- `DataSourcePort` — fetch данных из внешних API
- `StoragePort` — запись Bronze/Silver/Gold
- `LockPort` — блокировки
- `CheckpointPort` — чекпоинты
- `QuarantinePort` — карантин ошибок
- `MetricsPort` — метрики (sync)
- `LoggerPort` — структурированное логирование (sync)
- `TracingPort` — distributed tracing
- `InputFilterPort` — загрузка фильтров

### 3.4. Единообразие соглашений

| Аспект | Статус | Комментарий |
|--------|--------|-------------|
| Именование файлов | ✅ | snake_case, согласованное |
| Именование классов | ✅ | PascalCase, суффиксы Port/Adapter |
| Конфиги | ✅ | YAML в `configs/pipelines/{provider}/{entity}.yaml` |
| Тесты | ✅ | `tests/{unit,integration,e2e,architecture}/` |
| Docstrings | ✅ | Google Style, на русском |

---

## 4. Выявленные проблемы

### 4.1. Критические (блокеры)

**Нет критических проблем.** Архитектура стабильна.

### 4.2. Важные (требуют внимания)

#### P1: Дублирование в трансформерах пайплайнов

**Локация:** `src/bioetl/application/pipelines/{provider}/*_transformer.py`

**Проблема:** Каждый трансформер (ActivityTransformer, MoleculeTransformer, etc.) содержит похожий boilerplate код для:
- Создания domain entity
- Генерации content hash
- Конвертации в Silver record

**Пример дублирования:**
```python
# В каждом трансформере повторяется:
content_hash = self.compute_content_hash(business_data)
entity = Activity(..., content_hash=content_hash, ...)
return self.entity_to_silver_record(entity)
```

**Риск:** Растущий технический долг при добавлении новых сущностей

---

#### P2: Смешение ответственностей в RecordProcessor

**Локация:** `src/bioetl/application/core/record_processor.py:256-284`

**Проблема:** `_write_gold_batch()` выполняет валидацию Pandera внутри метода записи:
```python
async def _write_gold_batch(self, records: list[dict[str, Any]]) -> None:
    if self._gold_schema:
        import pandas as pd
        df = pd.DataFrame(records)
        self._gold_schema.validate(df, lazy=True)  # Валидация здесь
    await self._storage.write_gold(...)
```

**Риск:** Смешение валидации и персистенции, сложность тестирования

---

#### P3: Жёстко закодированные значения в HTTP Client

**Локация:** `src/bioetl/infrastructure/adapters/http/client.py:102-105`

**Проблема:**
```python
headers: dict[str, str] = {
    "User-Agent": "BioETL/0.1.0 (contact@example.com)",  # Hardcoded
}
```

**Риск:** Несоответствие реальной версии (5.0.0), placeholder email

---

### 4.3. Желательные улучшения

#### D1: Унификация создания Domain Entities

Трансформеры создают entities по-разному. Можно унифицировать через метод `BaseTransformer.create_entity()`.

#### D2: Отсутствие интерфейса для Gold Writer

`StoragePort.write_gold()` принимает `mode: Literal["overwrite", "append", "scd2"]`, но SCD2 не реализован.

#### D3: Deprecated файлы в корне

`cleanup_cache.py`, `debug_import.py`, `verify_bootstrap.py` — пустые или debug-скрипты.

---

## 5. План рефакторинга

### 5.1. Приоритизация

| Приоритет | ID | Шаг | Сложность | Риск |
|-----------|-----|-----|-----------|------|
| 🔴 HIGH | R1 | Устранить hardcoded значения | Low | Low |
| 🟡 MEDIUM | R2 | Выделить GoldValidator | Medium | Medium |
| 🟡 MEDIUM | R3 | Унифицировать entity creation в BaseTransformer | Medium | Medium |
| 🟢 LOW | R4 | Удалить deprecated файлы | Low | Low |
| 🟢 LOW | R5 | Добавить SCD2 в GoldWriter (или удалить из type hints) | Medium | Low |

---

### 5.2. Детальное описание шагов

#### R1: Устранить hardcoded значения в HTTP Client

**Цель:** Конфигурируемость User-Agent и контактов

**Изменения:**
```python
# src/bioetl/infrastructure/adapters/http/client.py
@dataclass
class UnifiedHTTPClient:
    rate_limiter: TokenBucket
    circuit_breaker: CircuitBreaker
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    timeout: float = 30.0
    run_id: RunID | None = None
    user_agent: str = "BioETL/5.0.0"  # NEW: Параметризация
    contact_email: str = "bioetl@example.com"  # NEW
```

**Риски:** Минимальные — обратно совместимо через default values

**Критерий готово:**
- User-Agent содержит версию из pyproject.toml
- Тесты `test_http_client.py` проходят

---

#### R2: Выделить GoldValidator из RecordProcessor

**Цель:** Разделение ответственностей (SRP)

**Изменения:**

1. Создать `src/bioetl/application/core/gold_validator.py`:
```python
class GoldValidator:
    """Validates records before Gold layer write."""

    def __init__(self, schema: PanderaSchema | None):
        self._schema = schema

    def validate(self, records: list[dict]) -> ValidationResult:
        if not self._schema:
            return ValidationResult(valid=True)
        df = pd.DataFrame(records)
        self._schema.validate(df, lazy=True)
        return ValidationResult(valid=True)
```

2. Обновить `RecordProcessor`:
```python
async def _write_gold_batch(self, records: list[dict]) -> None:
    self._gold_validator.validate(records)  # Делегирование
    await self._storage.write_gold(...)
```

**Риски:**
- Изменение сигнатуры конструктора RecordProcessor
- Требуется обновление фабрик

**Минимизация:**
- Добавить параметр `gold_validator` в конструктор с default factory
- Backward compatible через conditional creation

**Критерий готово:**
- Валидация в отдельном классе
- Unit-тесты для GoldValidator
- RecordProcessor использует новый класс

---

#### R3: Унифицировать Entity Creation в BaseTransformer

**Цель:** DRY для создания domain entities

**Изменения:**

1. Добавить в `BaseTransformer`:
```python
def create_entity(
    self,
    entity_class: type[T],
    context: PipelineContext,
    entity_id: EntityID,
    business_data: dict[str, Any],
    batch_id: BatchID,
) -> T:
    """Factory method for domain entity creation.

    Handles:
    - content_hash generation
    - ingestion_ts
    - run_id / run_type binding
    """
    content_hash = self.compute_content_hash(business_data)
    return entity_class(
        entity_id=entity_id,
        content_hash=content_hash,
        run_id=context.run_id,
        run_type=context.run_type,
        source_batch_id=batch_id,
        ingestion_ts=datetime.now(UTC),
        **business_data,
    )
```

2. Упростить конкретные трансформеры:
```python
# Было:
content_hash = self.compute_content_hash(business_data)
entity = Activity(
    entity_id=...,
    content_hash=content_hash,
    run_id=context.run_id,
    ...
)

# Стало:
entity = self.create_entity(Activity, context, entity_id, business_data, batch_id)
```

**Риски:**
- Изменение сигнатуры abstract method transform()
- Несовместимость с entities без unified constructor

**Минимизация:**
- Сохранить старый интерфейс transform() как есть
- Добавить create_entity() как helper method (не abstract)
- Постепенная миграция трансформеров

**Критерий готово:**
- create_entity() в BaseTransformer
- Минимум 3 трансформера мигрированы
- Без breaking changes в публичном API

---

#### R4: Удалить deprecated файлы

**Цель:** Чистота кодовой базы

**Изменения:**
```bash
rm cleanup_cache.py debug_import.py verify_bootstrap.py
```

**Риски:** Нулевые — файлы пустые или debug-only

**Критерий готово:**
- Файлы удалены
- git status чистый

---

#### R5: SCD2 в GoldWriter

**Цель:** Консистентность типов или реализация функционала

**Опции:**

A) Реализовать SCD2:
```python
async def write_gold(
    self, ..., mode: Literal["overwrite", "append", "scd2"] = "overwrite"
) -> None:
    if mode == "scd2":
        await self._write_scd2(...)
```

B) Удалить из type hints:
```python
mode: Literal["overwrite", "append"] = "overwrite"  # Удалить scd2
```

**Рекомендация:** Вариант B (удалить) — SCD2 не используется, добавить когда понадобится

---

## 6. Метрики контроля качества

### 6.1. Существующие метрики

| Метрика | Инструмент | Цель | Текущее |
|---------|------------|------|---------|
| Line Coverage | pytest-cov | ≥80% | Настроен |
| Type Safety | mypy --strict | 0 errors | Настроен |
| Code Style | ruff | 0 violations | Настроен |
| Architecture | tests/architecture/ | 16 tests pass | Настроен |
| Complexity | xenon | CC ≤ 10 | Настроен |
| Dead Code | vulture | 0 unused | Настроен |
| Security | bandit, pip-audit | 0 HIGH | Настроен |

### 6.2. Рекомендуемые дополнительные метрики

| Метрика | Инструмент | Цель | Влияние на балл |
|---------|------------|------|-----------------|
| Duplication | pylint --duplicate-code | <5% | +0.2 к категории 10 |
| Docstring Coverage | interrogate | ≥90% | +0.1 к категории 9 |
| Integration Test Time | pytest --durations | <5min | +0.1 к категории 4 |

### 6.3. Прогноз изменения интегрального балла

| Шаг | Категории | Δ Балла | Итог |
|-----|-----------|---------|------|
| Текущее | — | 8.18 | 8.18 |
| R1 | 8, 10 | +0.05 | 8.23 |
| R2 | 2, 4 | +0.10 | 8.33 |
| R3 | 2, 10 | +0.12 | 8.45 |
| R4 | 10 | +0.03 | 8.48 |

**Прогноз после рефакторинга: 8.4 – 8.5 / 10.0**

---

## 7. Заключение

Проект BioETL демонстрирует **зрелую и качественную архитектуру** уровня Production Ready. Выявленные проблемы носят **косметический характер** и не влияют на работоспособность системы.

**Приоритетные действия (ближайший спринт):**
1. ✅ R1: Устранить hardcoded User-Agent
2. ✅ R4: Удалить deprecated файлы

**Рекомендации на будущее:**
- R2, R3: Планировать при добавлении новых пайплайнов
- R5: Решить при необходимости SCD2

---

*Документ подготовлен: 2025-12-23*
*Следующий обзор: 2026-03*
