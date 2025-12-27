# Консолидированный Архитектурный Обзор BioETL

*Версия: 1.0 | Дата: 2025-12-27*
*Консолидация планов: 2026-01, 2026-02, 2026-06*

> **ПРОТОКОЛ ДВОЙНОЙ ВЕРИФИКАЦИИ (REQ-ARCH-040)**
>
> Все утверждения в этом документе прошли **двойную верификацию** согласно `RULES.md` §7:
> - Первая проверка — при обнаружении проблемы (ссылки на код)
> - Вторая проверка — при документировании (дата 2025-12-27)

---

## 1. Анализ исходных планов

### 1.1. Обнаруженные неточности и ошибки

| План | Утверждение | Статус | Обоснование |
|------|-------------|--------|-------------|
| **2026-01** | "Дублирование обогащения метаданными Silver" | ❌ **ЛОЖНОЕ** | `batch_writer.py:178-184` обновляет `_source_batch_id` как "batch-specific context" — это **намеренное переопределение**, не дублирование |
| **2026-02** | "Нет валидации write mode через Enum" | ❌ **УСТАРЕЛО** | `SilverWriteMode` (`delta_writer.py:55-66`) и `GoldWriteMode` (`gold_writer.py:42-54`) **УЖЕ реализованы** |
| **2026-02** | "Bronze сериализация без separators" | ⚠️ **ЧАСТИЧНО** | `bronze_writer.py:332-333` использует `separators=(",", ":")`, но `batch_writer.py:135` — нет |
| **2026-06** | Оценка 8.64 балла | ⚠️ **ЗАВЫШЕНА** | Не учтены проблемы silent degradation в BatchWriter и отсутствие HTTP observability |

### 1.2. Подтверждённые проблемы (сводная таблица)

| ID | Проблема | Файл:строки | Источник |
|----|----------|-------------|----------|
| **P1** | Silent degradation write-mode `overwrite→append` | `batch_writer.py:192-195,244-247` | 2026-01, 2026-02 |
| **P2** | Domain config использует строки, а не enum | `domain/config.py:79-80,114-115` | 2026-01, 2026-02 |
| **P3** | HTTP-клиент без observability | `http/client.py:52-199` | 2026-01 |
| **P4** | Ручное управление spans (`__enter__/__exit__`) | `executor.py:186,289,302,312,428,452` | 2026-06 |
| **P5** | Несогласованность separators в JSON сериализации | `batch_writer.py:135` vs `bronze_writer.py:332-333` | 2026-02 |
| **P6** | Дублирование PipelineConfig/TableConfig полей | `domain/config.py:67-92,95-170` | 2026-02 |
| **P7** | Документационная фрагментация | 4 отдельных обзора в `docs/` | 2026-06 |

---

## 2. Интегральная оценка (пересчитанная)

| Категория | Вес | Оценка | Балл | Комментарий |
|-----------|-----|--------|------|-------------|
| Слоистая архитектура | 0.12 | 8.5 | 1.02 | Порты в domain, матрица соблюдена |
| Порты/адаптеры и DI | 0.10 | 8.0 | 0.80 | DI корректен, HTTP-клиент без портов observability |
| Доменная модель | 0.10 | 7.5 | 0.75 | Frozen dataclasses, но write-mode как строки |
| Medallion инварианты | 0.10 | 6.5 | 0.65 | Silent degradation нарушает политику |
| Обработка ошибок | 0.10 | 8.0 | 0.80 | Классификация, circuit breaker работают |
| Наблюдаемость | 0.10 | 6.5 | 0.65 | Трансформеры покрыты, HTTP-клиент — нет |
| Тестирование | 0.10 | 8.0 | 0.80 | 187 arch-тестов, VCR покрытие |
| Детерминизм | 0.10 | 8.0 | 0.80 | D1-D3 выполнены, separators — частично |
| Производительность | 0.08 | 7.5 | 0.60 | Async I/O, batching корректны |
| Документация | 0.10 | 6.0 | 0.60 | Фрагментация, 4 разных обзора |
| **Итого** | **1.00** | | **7.47** | **Рабочее состояние, требуются улучшения** |

**Интерпретация:** 7.47 → диапазон 5.0–7.9 (рабочая архитектура с зоной укрепления)

---

## 3. Верифицированный план рефакторинга

### Приоритеты

| Уровень | Задачи | Влияние на балл |
|---------|--------|-----------------|
| 🔴 **Критично** | R1: Write-mode типобезопасность | +0.4 (Medallion, Domain) |
| 🟠 **Высокий** | R2: HTTP observability | +0.3 (Observability) |
| 🟡 **Средний** | R3: Spans helper, R4: JSON separators | +0.2 (Observability, Детерминизм) |
| 🟢 **Желательно** | R5: Документация | +0.1 (Документация) |

---

### R1: Типобезопасные write-mode и устранение silent degradation

**Статус:** 🔴 КРИТИЧНО | **Приоритет:** 1

**Проблема (верифицировано):**
- `domain/config.py:79-80,114-115` — write-mode как `Literal["merge", "append", "overwrite"]`
- `batch_writer.py:192-195,244-247` — silent degradation `overwrite → append`
- Enum'ы `SilverWriteMode`/`GoldWriteMode` существуют только в infrastructure

**Правки:**

1. **Domain enum'ы** (`domain/medallion.py` или новый `domain/write_mode.py`):
   ```python
   # domain/write_mode.py
   class SilverWriteMode(str, Enum):
       MERGE = "merge"
       APPEND = "append"
       DELETE = "delete"  # Только для rebuild

   class GoldWriteMode(str, Enum):
       APPEND = "append"
       SCD2 = "scd2"
       # OVERWRITE убран — требует явного подтверждения через CLI
   ```

2. **Domain config** (`domain/config.py:79-80,114-115`):
   ```python
   # Заменить Literal на enum
   silver_write_mode: SilverWriteMode = SilverWriteMode.MERGE
   gold_write_mode: GoldWriteMode = GoldWriteMode.APPEND
   ```

3. **BatchWriter** (`batch_writer.py:192-195,244-247`):
   ```python
   # УДАЛИТЬ silent degradation:
   # - if write_mode == "overwrite": write_mode = "append"
   # ЗАМЕНИТЬ на:
   write_mode = self._table_config.silver_write_mode
   # Передавать enum напрямую в storage
   ```

4. **Infrastructure adapters** — принимать domain enum, конвертировать внутри

**Тесты:**
- `tests/architecture/test_write_mode_types.py` — запрет строковых write-mode в domain
- `tests/unit/application/core/test_batch_writer.py` — PolicyViolationError при OVERWRITE

**Риски:** Миграция YAML-конфигов (добавить маппинг в composition)

**Критерии готовности:**
- [ ] Нет `Literal["merge", ...]` в domain/config.py
- [ ] BatchWriter не содержит silent degradation
- [ ] Все тесты проходят с enum write-modes

---

### R2: Observability HTTP-клиента

**Статус:** 🟠 ВЫСОКИЙ | **Приоритет:** 2

**Проблема (верифицировано):**
- `UnifiedHTTPClient` (`http/client.py:52-199`) не имеет `LoggerPort`/`MetricsPort`
- Нет логирования ретраев, задержек, circuit breaker событий

**Правки:**

1. **Инжекция портов** (`http/client.py`):
   ```python
   @dataclass
   class UnifiedHTTPClient:
       rate_limiter: RateLimiterPort
       circuit_breaker: CircuitBreakerPort
       logger: LoggerPort | None = None  # NEW
       metrics: MetricsPort | None = None  # NEW
       ...
   ```

2. **Логирование в `_request_with_retry`** (`client.py:136-173`):
   ```python
   # После каждого retry:
   if self.logger:
       self.logger.warning(
           "http_retry",
           url=url,
           attempt=attempt,
           delay=delay,
           error=str(exc),
       )

   # При circuit breaker open:
   if self.logger:
       self.logger.error("circuit_breaker_open", provider=self._provider)
   ```

3. **Метрики**:
   ```python
   if self.metrics:
       self.metrics.increment_counter(
           "http_retries_total",
           labels={"provider": self._provider, "status": status_code}
       )
       self.metrics.observe_histogram(
           "http_request_latency_seconds",
           value=duration,
           labels={"provider": self._provider}
       )
   ```

**Тесты:**
- `tests/unit/infrastructure/adapters/http/test_http_client_observability.py`
- Mock LoggerPort/MetricsPort, проверка вызовов при retry/error

**Риски:** Минимальный overhead при disabled observability (проверка `if self.logger`)

**Критерии готовности:**
- [ ] HTTP-клиент принимает опциональные LoggerPort/MetricsPort
- [ ] Ретраи и ошибки логируются структурированно
- [ ] Метрики latency/retries публикуются

---

### R3: Утилита для трассировки spans

**Статус:** 🟡 СРЕДНИЙ | **Приоритет:** 3

**Проблема (верифицировано):**
- `executor.py:186,289,302,312,428,452` — ручные `span.__enter__()/__exit__()`
- Дублирование логики записи атрибутов ошибок

**Правки:**

1. **Helper** (`application/core/tracing_utils.py`):
   ```python
   from contextlib import asynccontextmanager
   from typing import AsyncIterator

   @asynccontextmanager
   async def traced_operation(
       tracer: TracingPort,
       name: str,
       attributes: dict[str, str] | None = None,
   ) -> AsyncIterator[Span]:
       """Async context manager for tracing spans.

       Handles:
       - Span creation with attributes
       - Error recording on exception
       - Proper cleanup via __exit__
       """
       otel_tracer = tracer.get_tracer("bioetl")
       span = otel_tracer.start_span(name)
       if attributes:
           for k, v in attributes.items():
               span.set_attribute(k, v)
       span.__enter__()
       try:
           yield span
       except Exception as e:
           span.set_attribute("error", True)
           span.record_exception(e)
           raise
       finally:
           span.__exit__(None, None, None)
   ```

2. **Рефакторинг executor.py** — заменить ручные вызовы на `async with traced_operation(...)`

**Тесты:**
- `tests/unit/application/core/test_tracing_utils.py`

**Критерии готовности:**
- [ ] Все spans в executor/record_processor используют helper
- [ ] Атрибуты ошибок записываются единообразно

---

### R4: Единообразие JSON separators

**Статус:** 🟡 СРЕДНИЙ | **Приоритет:** 4

**Проблема (верифицировано):**
- `batch_writer.py:135` — `json.dumps(r, sort_keys=True)` без separators
- `bronze_writer.py:332-333` — с `separators=(",", ":")`

**Правки:**

1. **batch_writer.py:135**:
   ```python
   # Было:
   json_strings = [json.dumps(r, sort_keys=True) for r in records]

   # Стало:
   json_strings = [
       json.dumps(r, sort_keys=True, separators=(",", ":"))
       for r in records
   ]
   ```

2. **Альтернатива** — использовать `CanonicalJsonEncoder` из `infrastructure/serialization/encoders.py`

**Тесты:**
- `tests/architecture/test_deterministic_json.py` — проверка единообразия

**Критерии готовности:**
- [ ] Все JSON-сериализации Bronze используют compact separators
- [ ] Arch-test подтверждает

---

### R5: Консолидация документации

**Статус:** 🟢 ЖЕЛАТЕЛЬНО | **Приоритет:** 5

**Проблема:**
- 4 архитектурных обзора с разными датами и оценками
- Фрагментация усложняет поддержку

**Правки:**

1. **Объединить** в единый `docs/06-architecture-review-consolidated.md` (этот документ)
2. **Пометить устаревшие** как archived:
   - `docs/06-architecture-review-2026-01.md` → `docs/archive/`
   - `docs/06-architecture-review-2026-02.md` → `docs/archive/`
   - `docs/06-architecture-review-2026-06.md` → `docs/archive/`
3. **Обновить `docs/index.md`** — ссылка только на consolidated

**Критерии готовности:**
- [ ] Один актуальный обзор в `docs/`
- [ ] Устаревшие файлы в `docs/archive/`

---

## 4. Метрики и тесты

| Категория | Метрика | Целевое значение |
|-----------|---------|------------------|
| Write-mode | `write_mode_policy_violations_total` | 0 в production |
| HTTP | `http_request_latency_seconds` (p99) | < 5s |
| HTTP | `http_retries_total` / `http_requests_total` | < 5% |
| Tracing | Spans без ошибок закрытия | 100% |
| Детерминизм | `bronze_content_hash_stable` | true |

### Архитектурные тесты (добавить)

```python
# tests/architecture/test_write_mode_types.py
def test_no_string_write_modes_in_domain():
    """Domain config MUST use WriteMode enums, not Literal strings."""
    ...

# tests/architecture/test_json_separators.py
def test_bronze_serialization_uses_compact_separators():
    """All Bronze JSON serialization MUST use separators=(',', ':')."""
    ...
```

---

## 5. Ожидаемый результат

После выполнения R1-R5:

| Категория | До | После | Δ |
|-----------|-----|-------|---|
| Доменная модель | 7.5 | 8.5 | +1.0 |
| Medallion инварианты | 6.5 | 8.0 | +1.5 |
| Наблюдаемость | 6.5 | 8.0 | +1.5 |
| Детерминизм | 8.0 | 8.5 | +0.5 |
| Документация | 6.0 | 8.0 | +2.0 |
| **Итого** | **7.47** | **8.25** | **+0.78** |

---

## 6. Связь с существующим REFACTORING_PLAN.md

Этот консолидированный обзор **дополняет** существующий `REFACTORING_PLAN.md`:

| REFACTORING_PLAN.md | Этот документ |
|---------------------|---------------|
| D1-D3 (Детерминизм) ✅ | Подтверждено выполнение |
| M1-M2 (Write mode enums) ✅ | R1 расширяет до domain layer |
| T1-T5 (Timestamps) ✅ | Подтверждено выполнение |
| O1 (Tracing) ✅ | R3 расширяет на executor |
| — | R2 (HTTP observability) — НОВОЕ |
| — | R4 (JSON separators) — НОВОЕ |
| — | R5 (Документация) — НОВОЕ |

---

*Верифицировано: 2025-12-27 | Следующий обзор: после выполнения R1-R2*
