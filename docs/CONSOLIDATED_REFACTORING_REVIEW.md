# Консолидированный Обзор Планов Рефакторинга

*Версия: 1.0 | Дата: 2025-12-27*
*Источники: 4 архитектурных обзора (06/07-architecture-review-2026-*)*

> **Протокол REQ-ARCH-040**: Все утверждения верифицированы кодом согласно `RULES.md` §7.

---

## Сводка Исходных Планов

| План | Файл | Оценка | Ключевые темы |
|------|------|--------|---------------|
| #1 | `07-architecture-review-2026-09.md` | 7.28 | HTTP observability, span'ы, write-mode, документация |
| #2 | `07-architecture-review-2026-02-05.md` | 7.72 | Lifecycle сервисы, tracing, регистрация пайплайнов |
| #3 | `07-architecture-review-2026-06.md` | 6.48 | Трассировка, кэш конфигов, фильтры, политики |
| #4 | `06-architecture-review-2026-09.md` | 7.63 | HTTP observability, span'ы, метрики, документация |

---

## Выявленные Неточности и Ошибки

### ❌ Ложные Утверждения (НЕ реализовывать)

| Утверждение | Источник | Почему Ложно | Верификация |
|-------------|----------|--------------|-------------|
| "Write-mode принимает строки с runtime-конвертацией" | План #1 | **Уже реализовано**: `SilverWriteMode`, `GoldWriteMode` enum'ы с `from_string()` | `medallion.py:47-120`, M1/M2 в REFACTORING_PLAN.md |
| "Модульная регистрация пайплайнов требуется" | План #2 | **Не требуется**: `register_all_pipelines()` уже thread-safe с параметром `registry` для изоляции | `pipeline_factories.py:177-235` |
| "Дублирование CleanupService / MedallionLifecycleService" | План #2 | **Разные ответственности**: CleanupService — CLI/preview; MedallionLifecycleService — lifecycle операции (clear по policy, vacuum, archive) | `cleanup_service.py:105-181`, `medallion_lifecycle.py:71-203` |
| "Tracer опционален = проблема" | План #3 | **By design**: Null Object Pattern для опциональной observability. Проблема только в HTTP-клиенте. | NoOp* классы в `infrastructure/observability/` |

### ⚠️ Частично Верные Утверждения (требуют уточнения)

| Утверждение | Источник | Уточнение |
|-------------|----------|-----------|
| "lru_cache без инвалидации" | План #3 | Верно для `load_pipeline_config()`, но низкий приоритет: YAML перечитывается при рестарте процесса |
| "Ручное управление span'ами" | Планы #1, #4 | Верно для `executor.py`, но span'ы закрываются в `finally` блоках — риск низкий |

### ✅ Подтверждённые Проблемы (реализовывать)

| Проблема | Источники | Верификация |
|----------|-----------|-------------|
| **HTTP-клиент без LoggerPort/MetricsPort** | Планы #1, #3, #4 | `client.py:52-84` — нет `logger`/`metrics` полей |
| **Нет метрик ретраев/latency** | Планы #1, #4 | `_request_with_retry()` не публикует метрики |
| **Ручные span'ы в executor** | Планы #1, #4 | `executor.py:186,289,302,312,428,451` — `__enter__/__exit__` |

---

## Консолидированный План Рефакторинга

### Приоритет 1: 🔴 КРИТИЧНО

#### 1.1 Observability в UnifiedHTTPClient

**Упоминается в**: Планы #1, #3, #4
**Файл**: `src/bioetl/infrastructure/adapters/http/client.py`

**Проблема** (верифицировано):
```python
# client.py:52-84 — отсутствуют logger/metrics
@dataclass
class UnifiedHTTPClient:
    rate_limiter: RateLimiterPort
    circuit_breaker: CircuitBreakerPort
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    # ... НЕТ logger: LoggerPort | None
    # ... НЕТ metrics: MetricsPort | None
```

**Решение**:
1. Добавить опциональные поля `logger: LoggerPort | None = None`, `metrics: MetricsPort | None = None`
2. В `_request_with_retry()` логировать попытки и публиковать метрики:
   - `http_request_latency_seconds` (histogram)
   - `http_retries_total` (counter)
   - `circuit_breaker_state_changes_total` (counter)
3. Обновить composition factories для прокидывания портов

**Критерии готовности**:
- [ ] Логи ретраев появляются при `logger is not None`
- [ ] Метрики публикуются при `metrics is not None`
- [ ] Существующие тесты проходят (backward compatible)
- [ ] Новые unit-тесты покрывают observability

**Риски**: Дополнительные вызовы могут влиять на latency при высоком RPS.
**Митигация**: Проверки `if logger/metrics` и семплирование.

---

### Приоритет 2: 🟠 ВЫСОКИЙ

#### 2.1 Унифицировать Span-обёртки

**Упоминается в**: Планы #1, #4
**Файлы**: `executor.py`, `batch_writer.py`, `record_processor.py`

**Проблема** (верифицировано):
```python
# executor.py:186-187
span = otel_tracer.start_as_current_span(...)
span.__enter__()  # Ручное управление

# executor.py:289,302,312
span.__exit__(None, None, None)  # Дублирование в 3+ местах
```

**Решение**:
1. Создать helper в `application/core/observability/span_context.py`:
```python
@contextlib.asynccontextmanager
async def traced_operation(tracer: TracingPort | None, name: str, **attrs):
    if not tracer:
        yield None
        return
    span = tracer.get_tracer("bioetl").start_as_current_span(name, attributes=attrs)
    with span:
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            raise
```
2. Заменить ручные `__enter__/__exit__` на `async with traced_operation(...)`

**Критерии готовности**:
- [ ] Нет прямых вызовов `__enter__/__exit__` в application слое
- [ ] Helper покрыт unit-тестами
- [ ] Существующие span атрибуты сохранены

---

#### 2.2 Метрики Medallion-операций

**Упоминается в**: Планы #2, #4
**Файлы**: `medallion_lifecycle.py`, `batch_writer.py`

**Проблема** (верифицировано):
```python
# medallion_lifecycle.py:68-112 — нет MetricsPort
@dataclass
class MedallionLifecycleService:
    storage: StoragePort
    logger: LoggerPort
    # НЕТ metrics: MetricsPort | None
```

**Решение**:
1. Добавить `metrics: MetricsPort | None = None` в `MedallionLifecycleService`
2. Публиковать метрики:
   - `medallion_clear_duration_seconds` (histogram)
   - `medallion_clear_records_total` (counter)
   - `medallion_vacuum_duration_seconds` (histogram)
   - `medallion_vacuum_files_total` (counter)

**Критерии готовности**:
- [ ] Метрики публикуются при очистке/vacuum
- [ ] Unit-тесты с mock MetricsPort

---

### Приоритет 3: 🟡 СРЕДНИЙ

#### 3.1 Трассировка Lifecycle-операций

**Упоминается в**: Планы #2, #3
**Файлы**: `medallion_lifecycle.py`, `cleanup_service.py`

**Проблема**: Операции `clear()`, `vacuum()`, `preview()` не попадают в distributed traces.

**Решение**:
1. Добавить `tracer: TracingPort | None = None` в сервисы
2. Обернуть операции в span'ы используя helper из 2.1

**Критерии готовности**:
- [ ] Span'ы lifecycle видны в traces
- [ ] Атрибуты: table, policy, dry_run, result

---

#### 3.2 Инвалидация Кэша Конфигов (низкий приоритет)

**Упоминается в**: План #3
**Файл**: `infrastructure/config.py:87-97`

**Проблема** (верифицировано):
```python
@lru_cache(maxsize=10)
def load_pipeline_config(pipeline_name: str) -> PipelineYamlConfig:
    # Нет инвалидации по mtime
```

**Решение** (опционально):
- Добавить параметр `force_reload: bool = False`
- Или использовать `functools.cache` с ручной очисткой

**Примечание**: Низкий приоритет, т.к. конфиги перечитываются при рестарте процесса.

---

### Приоритет 4: 🟢 ЖЕЛАТЕЛЬНО

#### 4.1 Консолидация Документации

**Упоминается в**: Планы #1, #4

**Проблема**: 4+ архитектурных обзора с перекрывающимися темами.

**Решение**:
1. Данный документ (`CONSOLIDATED_REFACTORING_REVIEW.md`) — единый источник
2. Пометить старые обзоры как superseded
3. Добавить ссылку в README/docs index

---

## ❌ НЕ Реализовывать (отклонённые задачи)

| Задача | Причина Отклонения |
|--------|-------------------|
| Модульная регистрация пайплайнов по провайдерам | Уже реализовано через `register_all_pipelines(registry)` |
| Объединение CleanupService + MedallionLifecycleService | Разные ответственности, не дублирование |
| Ужесточение write-mode до enum-only | Уже реализовано (M1, M2 в REFACTORING_PLAN.md) |
| Обязательный tracer (не опциональный) | Нарушает Null Object Pattern для тестов |

---

## Метрики Успеха

### Новые Метрики (после реализации 1.1, 2.2)

```
http_request_latency_seconds{provider, method, status_class}
http_retries_total{provider, status_class}
circuit_breaker_trips_total{provider}
medallion_clear_duration_seconds{table, policy}
medallion_clear_records_total{table, layer}
medallion_vacuum_duration_seconds{table}
medallion_vacuum_files_total{table}
```

### Новые Тесты

| Файл | Покрытие |
|------|----------|
| `tests/unit/infrastructure/adapters/http/test_client_observability.py` | HTTP logger/metrics |
| `tests/unit/application/core/test_span_context.py` | Traced operation helper |
| `tests/unit/application/services/test_lifecycle_metrics.py` | Lifecycle метрики |

### Прогноз Улучшения Интегральной Оценки

| Шаг | Категория | Улучшение |
|-----|-----------|-----------|
| 1.1 HTTP observability | Наблюдаемость | +0.8 → 1.0 |
| 2.1 Span helper | Обработка ошибок | +0.1 |
| 2.2 Medallion metrics | Medallion инварианты | +0.2 |
| 3.1 Lifecycle tracing | Наблюдаемость | +0.1 |
| **Итого** | | +1.2 → **~8.5** |

---

## Порядок Выполнения

```
1.1 HTTP Observability ──────┬──▶ 2.1 Span Helper ──▶ 3.1 Lifecycle Tracing
                              │
                              └──▶ 2.2 Medallion Metrics
```

**Зависимости**:
- 2.1 Span Helper может использоваться в 3.1 Lifecycle Tracing
- 1.1 и 2.2 независимы, могут выполняться параллельно

---

## Чек-лист Перед Реализацией

- [ ] `make lint && make test` проходят
- [ ] Прочитан `docs/REFACTORING_PLAN.md` (секция "ЛОЖНЫЕ УТВЕРЖДЕНИЯ")
- [ ] Верифицирован целевой файл (`wc -l`, `grep "def "`)
- [ ] Понятны критерии готовности задачи
- [ ] Git branch создан

---

*Строй надёжно. Верифицируй кодом. Документируй с доказательствами.*
