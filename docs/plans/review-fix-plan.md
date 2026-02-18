# План исправления замечаний из рецензии на проект

**Дата:** 2026-02-16
**Версия:** 1.0
**Статус:** DRAFT

---

## Резюме рецензии

Рецензия выявила три категории замечаний:

| # | Замечание | Severity | Тип |
|---|-----------|----------|-----|
| R1 | `interfaces → infrastructure` — допущение в матрице импортов | RED | Архитектурный риск |
| R2 | Рассинхрон observability-документации с кодом | RED | Документация / конфигурация |
| R3 | TracingPort привязан к OpenTelemetry API | MEDIUM | Архитектурный дизайн |
| R4 | Конкурирующие источники правды по observability | COSMETIC | Документация |

---

## R1: interfaces → infrastructure (архитектурная утечка)

### Текущее состояние

Единственное нарушение — файл `src/bioetl/interfaces/observability.py:14`:
```python
from bioetl.infrastructure.observability import start_metrics_server
```
Это задокументировано в ADR-005 как осознанное допущение и покрыто архитектурным тестом `test_observability_allowed_infrastructure()`.

### План исправления

**Цель:** Устранить прямой импорт interfaces → infrastructure, маршрутизировав через composition.

#### Шаг 1: Экспортировать `start_metrics_server` через composition

**Файл:** `src/bioetl/composition/entrypoints.py`

Добавить фабричную функцию или re-export:
```python
# В composition/entrypoints.py (или отдельный composition/observability.py)
from bioetl.infrastructure.observability import start_metrics_server

def create_metrics_server() -> ...:
    """Factory for metrics server — routes infrastructure through composition."""
    return start_metrics_server
```

#### Шаг 2: Обновить interfaces/observability.py

**Файл:** `src/bioetl/interfaces/observability.py`

```python
# БЫЛО:
from bioetl.infrastructure.observability import start_metrics_server

# СТАЛО:
from bioetl.composition.entrypoints import start_metrics_server
# или:
from bioetl.composition.observability import create_metrics_server
```

#### Шаг 3: Обновить архитектурные тесты

**Файл:** `tests/architecture/test_interfaces_no_infrastructure.py`

- Удалить тест `test_observability_allowed_infrastructure()` (исключение больше не нужно)
- Добавить/обновить тест, что interfaces не импортирует infrastructure напрямую

#### Шаг 4: Ужесточить import-linter

**Файл:** `.importlinter`

Добавить контракт:
```ini
[importlinter:contract:interfaces-no-direct-infrastructure]
name = Interfaces must not import infrastructure directly
type = forbidden
source_modules =
    bioetl.interfaces
forbidden_modules =
    bioetl.infrastructure
```

#### Шаг 5: Обновить ADR-005

**Файл:** `docs/02-architecture/decisions/ADR-005-composition-layer-separation.md`

Обновить секцию "Note (2026-01-05)" — указать, что допущение закрыто и interfaces теперь маршрутизируется через composition.

#### Шаг 6: Обновить матрицу импортов в документации

**Файлы:**
- `docs/02-architecture/00-overview.md`
- `docs/00-project/RULES.md` (если содержит матрицу)
- `.claude/rules/ai-selfreview-rules.md`

Изменить `interfaces → infrastructure` с "ALLOWED (допущение)" на "FORBIDDEN".

**Риски:** Минимальные — единственный импорт, маршрутизация через composition — штатный паттерн.

---

## R2: Рассинхрон observability-документации

### 2.1 Env var format (CRITICAL)

**Проблема:** Документация использует плоский формат `BIOETL_TRACING_ENABLED`, а pydantic-settings с `env_nested_delimiter="__"` требует `BIOETL_OBSERVABILITY__TRACING_ENABLED`.

**Затронутые файлы:**

| Файл | Строки | Что исправить |
|------|--------|---------------|
| `docs/03-guides/metrics-monitoring.md` | ~42, 54, 210, 399, 427 | Все env vars `BIOETL_*_ENABLED/PORT` → `BIOETL_OBSERVABILITY__*` |
| `docs/04-reference/cli.md` | ~469 | `BIOETL_TRACING_ENABLED` → `BIOETL_OBSERVABILITY__TRACING_ENABLED` |
| `docs/04-reference/api/infrastructure/observability.md` | ~211 | Аналогичная замена |
| `docs/05-operations/runbooks/observability-checklist.md` | Проверить все env vars | Аналогичная замена |

**Действие:** Глобальная замена по документации. Добавить примечание о вложенной структуре настроек:

```markdown
> **Примечание:** BioETL использует pydantic-settings с `env_nested_delimiter="__"`.
> Observability-настройки вложены в секцию `observability`, поэтому env var формат:
> `BIOETL_OBSERVABILITY__<FIELD_NAME>`.
```

### 2.2 ADR-022: Некорректные пути файлов (HIGH)

**Проблема:** ADR-022 ссылается на несуществующие пути.

| ADR-022 утверждает | Фактический путь | Исправление |
|--------------------|-----------------|-------------|
| `infrastructure/observability/noop_tracing.py` | `domain/ports/noop.py` | Обновить путь |
| `composition/factories/observability.py` | `composition/bootstrap/runtime/observability.py` | Обновить путь |

**Файл:** `docs/02-architecture/decisions/ADR-022-tracing-noop.md`

### 2.3 Некорректная ссылка на contracts (HIGH)

**Проблема:** `docs/02-architecture/observability-layers.md:52` ссылается на `docs/contracts/observability.md`, но фактический путь — `docs/04-reference/contracts/observability.md`.

**Файл:** `docs/02-architecture/observability-layers.md`
**Действие:** Исправить ссылку на `docs/04-reference/contracts/observability.md`.

### 2.4 Circuit breaker state values (HIGH)

**Проблема:** Конфликт значений gauge между документами.

| Источник | closed | half-open | open |
|----------|--------|-----------|------|
| **Код** (`circuit_breaker.py:36-39`) | **0** | **1** | **2** |
| `metrics-monitoring.md:102` | 0 | 1 | 2 |
| `contracts/observability.md:121` | 0 | **0.5** | **1** |

**Код — source of truth.** Значения: `0=closed, 1=half-open, 2=open`.

**Файл:** `docs/04-reference/contracts/observability.md:121`
**Действие:** Исправить `0 = closed, 0.5 = half-open, 1 = open` → `0 = closed, 1 = half-open, 2 = open`.

### 2.5 Отсутствие DQMonitorPort в ADR-017 (MEDIUM)

**Проблема:** ADR-017 документирует 3 порта (Logger, Metrics, Tracing), но фактически в `domain/ports/observability.py` определены 4 порта, включая `DQMonitorPort`.

**Файл:** `docs/02-architecture/decisions/ADR-017-observability-architecture.md`
**Действие:** Добавить описание `DQMonitorPort` и `ObservabilityBundle`.

### 2.6 Deprecated bootstrap функции не документированы (MEDIUM)

**Проблема:** В `composition/bootstrap/runtime/observability.py` deprecated-функции (`bootstrap_logger`, `bootstrap_tracer`, `bootstrap_metrics`, `bootstrap_dq_monitor`, `bootstrap_observability`) не упомянуты в документации.

**Действие:** Добавить секцию "Deprecated API" в ADR-017 или в отдельный migration guide, указав канонические имена с суффиксом `_port()`:
- `bootstrap_logger_port()`
- `bootstrap_tracer_port()`
- `bootstrap_metrics_port()`
- `bootstrap_dq_monitor_port()`
- `bootstrap_observability_bundle()`

### 2.7 Неполный перечень настроек в документации (MEDIUM)

**Проблема:** Документация не перечисляет все observability-настройки из `_base.py`.

**Недокументированные поля:**
- `metrics_server_enabled`, `metrics_fail_fast`, `metrics_retry_count`, `metrics_retry_delay`
- `dq_baseline_window`, `dq_z_score_threshold`, `dq_min_baseline_samples`
- `dq_cold_start_runs`, `dq_error_rate_max`, `dq_quality_score_min`

**Файлы:** `docs/04-reference/cli.md`, `docs/03-guides/metrics-monitoring.md`
**Действие:** Добавить полную таблицу env vars с описаниями и значениями по умолчанию.

---

## R3: TracingPort привязан к OpenTelemetry API

### Текущее состояние

`TracingPort` определяет `get_tracer(name) -> Any`, но:
- Все потребители (batch_tracing.py, base_transformer.py) вызывают OTel-специфичные методы: `start_as_current_span()`, `set_attribute()`, `record_exception()`
- `NoOpTracing` реализует `_NoOpOtelTracer` с теми же OTel-методами
- Замена backend (e.g. Jaeger-native) потребует адаптеров ко всему OTel API

### Варианты решения

#### Вариант A: Ввести SpanPort Protocol (рекомендуется)

Добавить явный контракт для span, абстрагирующий OTel API:

```python
# domain/ports/observability.py
@runtime_checkable
class SpanPort(Protocol):
    """Backend-agnostic span abstraction."""
    def set_attribute(self, key: str, value: Any) -> None: ...
    def set_status(self, status: Any) -> None: ...
    def record_error(self, exception: Exception) -> None: ...
    def __enter__(self) -> Self: ...
    def __exit__(self, *args: Any) -> None: ...

@runtime_checkable
class TracingPort(Protocol):
    """Backend-agnostic tracing port."""
    def start_span(self, name: str, attributes: dict[str, Any] | None = None) -> SpanPort: ...
    def close(self) -> None: ...
```

**Объём изменений:**
- `domain/ports/observability.py` — новый SpanPort, обновлённый TracingPort
- `domain/ports/noop.py` — обновить NoOp реализации
- `infrastructure/observability/tracing.py` — адаптировать OTel tracer
- `application/core/batch_tracing.py` — заменить `get_tracer().start_as_current_span()` → `start_span()`
- `application/core/base_transformer.py` — аналогично
- `application/observability/span_helpers.py` — аналогично
- ADR-017 — обновить контракт

#### Вариант B: Зафиксировать TracingPort = OTel facade (минимальный)

Явно задокументировать, что TracingPort — это intentional OTel facade, а не backend-agnostic абстракция.

**Объём изменений:**
- ADR-017 — добавить секцию "TracingPort Design Decision: OTel as canonical API"
- Типизировать `get_tracer() -> Any` как `get_tracer() -> OtelTracerLike` с TYPE_CHECKING
- Добавить комментарии к NoOp реализации

**Рекомендация:** Вариант B как первый шаг (документация + типизация), Вариант A — в бэклог для следующего рефакторинга.

---

## R4: Конкурирующие источники правды (COSMETIC)

### Проблема

Информация об observability разбросана по 6+ документам:
- ADR-017, ADR-022
- `metrics-monitoring.md`
- `observability-layers.md`
- `observability-checklist.md`
- `contracts/observability.md`
- `api/infrastructure/observability.md`

### План

#### Шаг 1: Определить Single Source of Truth (SSOT)

| Аспект | SSOT документ | Остальные ссылаются на него |
|--------|---------------|----------------------------|
| Env vars & настройки | `docs/04-reference/cli.md` | guides, runbooks |
| Каталог метрик | `docs/04-reference/contracts/observability.md` | guides, ADRs |
| Архитектура портов | ADR-017 | overview, guides |
| Runbook/troubleshooting | `docs/05-operations/runbooks/observability-checklist.md` | — |

#### Шаг 2: Добавить cross-references

В каждом документе-потребителе заменить дублирующую информацию ссылками:
```markdown
> Полный каталог env vars см. в [CLI Reference](../04-reference/cli.md#observability).
> Каталог метрик см. в [Observability Contract](../04-reference/contracts/observability.md).
```

---

## Приоритизация

| Приоритет | Задача | Effort | Impact |
|-----------|--------|--------|--------|
| **P0** | R2.1 — Env vars в документации | LOW | HIGH — пользователи не смогут настроить |
| **P0** | R2.4 — Circuit breaker values в contracts | LOW | HIGH — мониторинг даст ложные данные |
| **P1** | R2.2 — ADR-022 пути | LOW | MEDIUM — документация вводит в заблуждение |
| **P1** | R2.3 — Ссылка на contracts | LOW | MEDIUM |
| **P1** | R1 — interfaces→infrastructure | MEDIUM | MEDIUM — архитектурная гигиена |
| **P2** | R2.5 — DQMonitorPort в ADR-017 | LOW | LOW |
| **P2** | R2.6 — Deprecated functions | LOW | LOW |
| **P2** | R2.7 — Полный перечень настроек | MEDIUM | MEDIUM |
| **P2** | R3 (Вариант B) — TracingPort как OTel facade | LOW | LOW |
| **P3** | R4 — SSOT для observability | MEDIUM | LOW |
| **BACKLOG** | R3 (Вариант A) — SpanPort Protocol | HIGH | MEDIUM |

---

## Checklist перед мержем

- [ ] Все env vars в документации используют формат `BIOETL_OBSERVABILITY__*`
- [ ] ADR-022 ссылается на корректные пути файлов
- [ ] `contracts/observability.md` — circuit breaker values = 0/1/2
- [ ] `interfaces/observability.py` не импортирует из infrastructure
- [ ] `import-linter` запрещает interfaces→infrastructure
- [ ] Архитектурные тесты проходят
- [ ] ADR-017 содержит DQMonitorPort
- [ ] TracingPort задокументирован как OTel facade (если выбран Вариант B)
