# Консолидированный План Рефакторинга BioETL

*Версия: 1.0 | Дата: 2025-12-27 | Источник: Анализ 4 планов с верификацией кодом*

> **Методология**: Все утверждения верифицированы согласно протоколу двойной проверки (CLAUDE.md §0).
> Каждое утверждение содержит ссылку на код `файл:строка` и дату проверки.

---

## 1. Анализ Исходных Планов

### 1.1. Проанализированные Документы

| # | Документ | Дата | Оценка | Фокус |
|---|----------|------|--------|-------|
| 1 | `06-architecture-review-2026-02-05.md` | 2026-02-05 | 7.74 | Lock/Vacuum/CLI |
| 2 | `07-architecture-review-2026-05.md` | 2026-05 | 7.12 | DI/Tracing/Tests |
| 3 | `07-architecture-review-2026-09.md` | 2026-09 | 7.42 | HTTP observability |
| 4 | Inline план (без файла) | — | 7.96 | DQ/Import linter |

### 1.2. Сводная Статистика

- **Всего уникальных задач**: 12
- **Перекрывающихся задач**: 5
- **Ложных утверждений**: 4
- **Подтверждённых проблем**: 6

---

## 2. Выявленные Ложные Утверждения

> **ВАЖНО**: Эти утверждения НЕВЕРНЫ. Не использовать как основу для рефакторинга!

| Ложное утверждение | Источник | Почему неверно | Верификация |
|--------------------|----------|----------------|-------------|
| "BaseTransformer не закрывает tracing span" | Plan 4 (май 2026) | Span закрывается в `finally` блоке через `span.__exit__(None, None, None)` | `base_transformer.py:211` |
| "Нет import-linter / проверки матрицы импортов" | Plan 3 (inline) | import-linter настроен с 5 контрактами, CI workflow существует | `.importlinter:1-71`, `.github/workflows/import-linter.yml` |
| "Невалидные write-mode проявятся в рантайме" | Plan 1 (сент 2026) | ValueError выбрасывается сразу в `__post_init__` через `SilverWriteMode.from_string()` | `domain/config.py:98-117`, `medallion.py:63-82` |
| "lock-loss ветка пустая — критическая проблема" | Plan 2 (фев 2026) | `pass` намеренный с детальными комментариями; сигнал уже отправляется через `PipelineShutdownError` | `lock_manager.py:166-190` |

---

## 3. Подтверждённые Проблемы (После Верификации)

### 3.1. Высокий Приоритет

| Проблема | Файл:строки | Описание | Источник |
|----------|-------------|----------|----------|
| **HTTP клиент без observability** | `client.py:51-84` | `UnifiedHTTPClient` не принимает tracer/logger/metrics в конструкторе. Сетевые ошибки не коррелируются с run_id | Plan 1, 4 |
| **PipelineExecutor нарушает DI** | `executor.py:100-104` | Создаёт `NoOpTracing()` внутри конструктора вместо получения через инъекцию | Plan 4 |
| **Vacuum CLI перезаписывает YAML** | `entrypoints.py:127-128` | `vacuum_after_run or False` принудительно устанавливает False если флаг не указан | Plan 2 |

### 3.2. Средний Приоритет

| Проблема | Файл:строки | Описание | Источник |
|----------|-------------|----------|----------|
| **Ручное управление span в writers** | `batch_writer.py:72-116` | `_start_span()` использует `span.__enter__()`, `_end_span()` — `span.__exit__()` вручную | Plan 1 |
| **CSV фильтр требует все 3 параметра** | `entrypoints.py:115-122` | Невозможно использовать `filter_field` из YAML если CSV указан без column | Plan 2 |

### 3.3. Желательно

| Проблема | Файл:строки | Описание | Источник |
|----------|-------------|----------|----------|
| **Фрагментация архитектурной документации** | `docs/` | Несколько обзоров с потенциально противоречивой информацией | Plan 1, 3 |

---

## 4. Консолидированный План Рефакторинга

### Фаза 1: Наблюдаемость HTTP-Клиента (Высокий)

> **Цель**: Обеспечить трассировку и метрики для всех HTTP операций

**Файлы для изменения**:
- `src/bioetl/infrastructure/adapters/http/client.py`
- `src/bioetl/composition/factories/` (фабрики)

**Текущее состояние** (верифицировано 2025-12-27):
```python
# client.py:51-84
@dataclass
class UnifiedHTTPClient:
    rate_limiter: RateLimiterPort
    circuit_breaker: CircuitBreakerPort
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    timeout: float = 30.0
    run_id: RunID | None = None  # Есть run_id, но нет tracer/logger/metrics
    user_agent: str = "BioETL/5.0.0"
```

**Требуемые изменения**:

1. Добавить зависимости observability в конструктор:
```python
tracer: TracingPort | None = None
metrics: MetricsPort | None = None
logger: LoggerPort | None = None
```

2. Обернуть `_request_with_retry` в tracing span:
```python
span = tracer.start_span("http_request", attributes={
    "http.method": method,
    "http.url": url,
    "bioetl.run_id": str(self.run_id),
})
```

3. Добавить метрики:
   - `http_request_duration_seconds` (histogram)
   - `http_request_errors_total` (counter)
   - `http_retries_total` (counter)

**Критерии готовности**:
- [ ] Все HTTP операции создают spans с корректными атрибутами
- [ ] Метрики экспортируются при успехе/ошибке
- [ ] Тесты в `tests/unit/infrastructure/adapters/http/` покрывают observability
- [ ] `make lint && make test` проходят

---

### Фаза 2: Устранение DI-нарушения в PipelineExecutor (Высокий)

> **Цель**: Соблюдать DI-принципы — все зависимости передаются через конструктор

**Файлы для изменения**:
- `src/bioetl/application/core/executor.py`
- `src/bioetl/composition/factories/` (фабрики создающие executor)

**Текущее состояние** (верифицировано 2025-12-27):
```python
# executor.py:100-104
if tracer is None:
    from bioetl.domain.ports import NoOpTracing
    tracer = NoOpTracing()  # Нарушение DI — создание внутри конструктора
self._tracer: TracingPort = tracer
```

**Требуемые изменения**:

1. Удалить создание NoOpTracing в конструкторе executor
2. Сделать tracer обязательным параметром (или передавать NoOpTracing из composition)
3. Обновить фабрики для передачи tracer из bootstrap

**Критерии готовности**:
- [ ] `PipelineExecutor` не импортирует `NoOpTracing`
- [ ] Все фабрики передают tracer явно
- [ ] Архитектурный тест проверяет отсутствие создания зависимостей в application слое
- [ ] `make arch-test` проходит

---

### Фаза 3: Tri-state для VACUUM в CLI (Средний)

> **Цель**: Сохранить дефолты из YAML при отсутствии CLI-флага

**Файлы для изменения**:
- `src/bioetl/composition/entrypoints.py`

**Текущее состояние** (верифицировано 2025-12-27):
```python
# entrypoints.py:127-128
vacuum = VacuumConfig(
    enabled=options.vacuum_after_run or False,  # Принудительно False если None
    retention_days=options.vacuum_retention_days or 7,
)
```

**Требуемые изменения**:

1. Изменить логику на tri-state (None = использовать YAML):
```python
vacuum = VacuumConfig(
    enabled=options.vacuum_after_run,  # None = использовать YAML
    retention_days=options.vacuum_retention_days,
)
```

2. Обновить `bootstrap_pipeline` для корректного слияния None с YAML:
```python
# В bootstrap_pipeline
if ctx.vacuum.enabled is None:
    ctx.vacuum.enabled = yaml_config.maintenance.auto_vacuum
```

**Критерии готовности**:
- [ ] CLI без флага vacuum использует YAML значение
- [ ] CLI с `--vacuum` явно включает
- [ ] CLI с `--no-vacuum` явно выключает
- [ ] Интеграционные тесты покрывают все три случая

---

### Фаза 4: Span Helper для Унификации Tracing (Средний)

> **Цель**: Устранить ручное управление span через context manager

**Файлы для изменения**:
- Создать: `src/bioetl/application/observability/span_helpers.py`
- Изменить: `src/bioetl/application/core/batch_writer.py`

**Текущее состояние** (верифицировано 2025-12-27):
```python
# batch_writer.py:72-116
def _start_span(self, name: str, ...) -> SpanType | None:
    span = self._tracer.get_tracer(...).start_as_current_span(name, attributes=attrs)
    span.__enter__()  # Ручной вызов
    return span

def _end_span(self, span: SpanType | None, error: Exception | None = None) -> None:
    if error:
        span.record_exception(error)
    span.__exit__(None, None, None)  # Ручной вызов
```

**Требуемые изменения**:

1. Создать async context manager helper:
```python
# span_helpers.py
@asynccontextmanager
async def traced_operation(
    tracer: TracingPort,
    name: str,
    attributes: dict[str, Any] | None = None,
):
    span = tracer.get_tracer("bioetl").start_as_current_span(name, attributes=attributes or {})
    try:
        with span:
            yield span
    except Exception as e:
        span.set_attribute("error", True)
        span.record_exception(e)
        raise
```

2. Заменить ручное управление в batch_writer:
```python
async def write_bronze(self, ...):
    async with traced_operation(self._tracer, "write_bronze", {...}) as span:
        # операции записи
```

**Критерии готовности**:
- [ ] Нет прямых вызовов `span.__enter__()` / `span.__exit__()` в application
- [ ] Unit-тесты helper проверяют закрытие при исключениях
- [ ] Tracing spans корректно закрываются во всех сценариях

---

### Фаза 5: Гибкое Комбинирование CSV-Фильтров с YAML (Желательно)

> **Цель**: Позволить использовать filter_field из YAML при указании только CSV

**Файлы для изменения**:
- `src/bioetl/composition/entrypoints.py`

**Текущее состояние** (верифицировано 2025-12-27):
```python
# entrypoints.py:115-122
if options.input_csv and options.filter_column and options.filter_field:
    input_filter = InputFilterContext.from_csv(...)
else:
    input_filter = InputFilterContext.disabled()  # Всё или ничего
```

**Требуемые изменения**:

1. Разрешить частичные параметры и подставлять из YAML:
```python
if options.input_csv:
    filter_column = options.filter_column or yaml_config.default_filter_column
    filter_field = options.filter_field or yaml_config.filter_field
    if filter_column and filter_field:
        input_filter = InputFilterContext.from_csv(...)
    else:
        raise ValueError("filter_column и filter_field обязательны при использовании input_csv")
```

**Критерии готовности**:
- [ ] CSV + колонка без filter_field берёт filter_field из YAML
- [ ] Ясное сообщение об ошибке при недостающих параметрах
- [ ] Unit-тесты на смешанные источники конфигурации

---

### Фаза 6: Консолидация Документации (Желательно)

> **Цель**: Единый источник истины для архитектурных обзоров

**Файлы для изменения**:
- `docs/` — архивация/удаление устаревших обзоров
- `README.md` — обновление ссылок

**Текущее состояние**:
- `06-architecture-review-2026-02-05.md`
- `07-architecture-review-2026-05.md`
- `07-architecture-review-2026-09.md`
- `ARCHITECTURAL_REVIEW_MARCH_2026.md`
- `ARCHITECTURE_REVIEW_2025-12-27.md`
- `CONSOLIDATED_REFACTORING_ANALYSIS.md`
- `REFACTORING_PLAN.md` (основной)

**Требуемые изменения**:

1. Пометить устаревшие документы как Archived в заголовке
2. Обновить README с указанием на актуальный документ
3. Добавить index документов в `docs/README.md`

**Критерии готовности**:
- [ ] Один актуальный обзор с датой последнего обновления
- [ ] Устаревшие файлы помечены `[ARCHIVED]`
- [ ] README указывает на единственный источник

---

## 5. Зависимости Между Фазами

```
┌─────────────────────────────────────────────────┐
│              ФАЗА 1: HTTP Observability          │
│                   (независима)                   │
└─────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────┐
│              ФАЗА 2: PipelineExecutor DI         │
│           (зависит от factories Фазы 1)          │
└─────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────┐
│              ФАЗА 4: Span Helpers                │
│           (использует шаблоны из Фазы 1-2)       │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│              ФАЗА 3: Vacuum Tri-state            │
│                   (независима)                   │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│              ФАЗА 5: CSV Filters                 │
│                   (независима)                   │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│              ФАЗА 6: Документация                │
│           (после завершения остальных)           │
└─────────────────────────────────────────────────┘
```

---

## 6. Метрики Качества

### 6.1. Новые Тесты

| Тест | Категория | Покрывает |
|------|-----------|-----------|
| `test_http_client_creates_spans` | unit | Фаза 1 |
| `test_http_client_records_metrics` | unit | Фаза 1 |
| `test_executor_receives_tracer_from_factory` | arch | Фаза 2 |
| `test_vacuum_cli_none_uses_yaml` | integration | Фаза 3 |
| `test_span_helper_closes_on_exception` | unit | Фаза 4 |
| `test_csv_filter_uses_yaml_field` | unit | Фаза 5 |

### 6.2. Связь с Интегральным Баллом

| Фаза | Категории улучшения | Ожидаемый рост |
|------|---------------------|----------------|
| 1 | Наблюдаемость, Устойчивость | +0.4 |
| 2 | Ports & Adapters, DI | +0.2 |
| 3 | Конфигурация и детерминизм | +0.2 |
| 4 | Наблюдаемость, Техдолг | +0.2 |
| **Итого** | | **+1.0** |

Ожидаемый интегральный балл после всех фаз: **~8.2-8.5**

---

## 7. Риски и Митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Регрессия HTTP-логики при добавлении observability | Низкая | VCR кассеты фиксируют поведение |
| Ломающие изменения в factory сигнатурах | Средняя | Deprecation aliases, постепенная миграция |
| Фрагментация при частичной реализации | Низкая | Фазы независимы, каждая самодостаточна |

---

## 8. Чек-лист Перед Началом Работы

- [ ] Прочитать `docs/REFACTORING_PLAN.md` — раздел "ЛОЖНЫЕ УТВЕРЖДЕНИЯ"
- [ ] `make lint && make test` проходят
- [ ] Git branch создан для работы
- [ ] Понятны критерии приёмки выбранной фазы

---

*Строй надёжно. Верифицируй перед утверждением. Документируй с ссылками на код.*
