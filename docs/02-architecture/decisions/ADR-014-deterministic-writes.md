# ADR-014: Deterministic Writes and Retries

**Status:** Accepted
**Date:** 2025-12-24
**Decision makers:** @BioETL-Team

## Context

Для обеспечения воспроизводимости и упрощения отладки пайплайнов необходим детерминизм:

1. **Проблема отладки**: При расследовании инцидентов невозможно воспроизвести точное поведение из-за:
   - `random.uniform()` в retry jitter
   - `datetime.now()` вызывается в разных местах с микросекундными различиями

2. **Проблема тестирования**: Тесты с random/datetime.now() flaky и непредсказуемы

3. **Источники недетерминизма в кодовой базе**:

| Файл | Паттерн | Контекст |
|------|---------|----------|
| `infrastructure/adapters/http/client.py` | `random.uniform()` | Retry jitter |
| `infrastructure/storage/gold-writer.py` | `random.uniform()` | Write backoff |
| `infrastructure/storage/bronze-writer.py` | `datetime.now()` | Ingestion timestamp |
| `infrastructure/quarantine/unified.py` | `datetime.now()` | Error timestamp |

## The Decision

### 1. Детерминистичный Retry Jitter

Добавлен режим `deterministic=True` в `RetryConfig`:

```python
@dataclass
class RetryConfig:
    max-attempts: int = 3
    base-delay: float = 1.0
    jitter: float = 0.1
    deterministic: bool = False  # NEW
    jitter-seed: int | None = None  # NEW

    def calculate-delay(self, attempt: int, url: str = "") -> float:
        delay = self.base-delay * (self.multiplier ** attempt)

        if self.deterministic:
            # Hash-based deterministic jitter
            hash-input = f"{attempt}:{url}:{self.jitter-seed or 0}"
            jitter-factor = (hash(hash-input) % 1000) / 1000.0
            delay += delay * self.jitter * (jitter-factor * 2 - 1)
        else:
            delay += random.uniform(-delay * self.jitter, delay * self.jitter)

        return max(0.0, delay)
```

### 2. Запрет random в Storage Writers

- Удалён `import random` из `gold-writer.py`
- `random.uniform(0, 0.1)` заменён на фиксированный `0.05`
- Архитектурный тест `test-no-random-in-writers` блокирует регрессии

### 3. Единый Источник Времени

`PipelineContext.started-at` — единственный источник timestamps для batch:

```python
@dataclass(frozen=True)
class PipelineContext:
    run-id: RunID
    run-type: RunType
    logger: LoggerPort
    started-at: datetime = field(default_factory=-now-utc)

    @classmethod
    def create(cls, run-id, run-type, logger, started-at=None):
        return cls(..., started-at=started-at or datetime.now(UTC))
```

Infrastructure компоненты получают timestamp как параметр:

```python
# Application layer
ingestion-ts = self.-context.started-at

# Infrastructure layer - receives timestamp
await bronze-writer.write-bronze(..., ingestion-ts=ingestion-ts)
await quarantine.write(..., ingestion-ts=ingestion-ts)
```

### 4. Архитектурные Тесты

| Тест | Цель |
|------|------|
| `test-no-random-in-writers` | Блокирует `import random` в `infrastructure/storage/` |
| `test-no-datetime-now-in-infrastructure` | Блокирует `datetime.now()` в `infrastructure/` |
| `test-no-structlog-in-application-interfaces` | Блокирует прямой импорт `structlog` в `application/` и `interfaces/` |

### 5. Изоляция логирования

Application и interfaces слои **MUST NOT** импортировать `structlog` напрямую — использовать абстракцию `LoggerPort` из `domain.ports`. Это обеспечивает:
- Тестируемость (можно подменить логгер в тестах)
- Независимость от конкретной реализации
- Единообразие обработки ошибок

## Justification

### Преимущества

1. **Воспроизводимость**: Одинаковые входные данные → одинаковое поведение
2. **Тестируемость**: Детерминистичные тесты без flakiness
3. **Отладка**: Можно воспроизвести точную последовательность событий
4. **Консистентность**: Все записи в batch имеют одинаковый `-ingestion-ts`

### Компромиссы

1. **API усложнение**: Дополнительные параметры (`ingestion-ts`, `deterministic`)
2. **Миграция**: Требуется обновление всех вызовов infrastructure компонентов
3. **Backward compatibility**: Fallback на `datetime.now()` при отсутствии параметра

## Implementation

### Изменённые файлы

| Файл | Изменение |
|------|-----------|
| `domain/context.py` | Добавлен `started-at` field |
| `application/core/record-processor.py` | Использует `context.started-at` |
| `application/core/base.py` | Использует `PipelineContext.create()` |
| `infrastructure/adapters/http/client.py` | Добавлен `deterministic` mode |
| `infrastructure/storage/gold-writer.py` | Удалён `random`, фиксированный backoff |
| `infrastructure/storage/bronze-writer.py` | Принимает `ingestion-ts` параметр |
| `infrastructure/quarantine/unified.py` | Принимает `ingestion-ts` параметр |
| `domain/ports/quarantine.py` | Обновлён `QuarantinePort.write()` |

### Архитектурные тесты

- `tests/architecture/test-no-random-in-writers.py`
- `tests/architecture/test-no-datetime-now-in-infrastructure.py`
- `tests/architecture/test-no-structlog-in-application-interfaces.py`

### Исключения для datetime.now() (ALLOWED-FILES)

Следующие файлы имеют **обоснованные исключения** для использования `datetime.now()`.
Исключения определены в `tests/architecture/test-no-datetime-now-in-infrastructure.py`:

| Файл | Модуль | Обоснование | Использование |
|------|--------|-------------|---------------|
| `operations.py` | `infrastructure/quarantine/` | Вычисление retention cutoff для cleanup | `datetime.now(UTC) - timedelta(days=max-age-days)` для определения записей на удаление |
| `gold-writer.py` | `infrastructure/storage/` | SCD2 `valid-from`/`valid-to` timestamps | Установка временных меток при merge-операциях для Slowly Changing Dimensions Type 2 |
| `lineage.py` | `infrastructure/observability/` | Provenance tracking | Real-time timestamps для `record-run-start()`, `record-run-end()`, и фильтрации по дате |
| `detector.py` | `infrastructure/observability/anomaly/` | Anomaly detection monitoring | Timestamp в `AnomalyResult` при обнаружении критических аномалий |
| `iqr.py` | `infrastructure/observability/anomaly/detectors/` | IQR-based anomaly detection | Timestamp в результате детекции при обнаружении аномалии |
| `mad.py` | `infrastructure/observability/anomaly/detectors/` | MAD-based anomaly detection | Timestamp в результате детекции при обнаружении аномалии |
| `zscore.py` | `infrastructure/observability/anomaly/detectors/` | Z-score anomaly detection | Timestamp в результате детекции при обнаружении аномалии |
| `client.py` | `infrastructure/adapters/` | Caching logic (reserved) | Зарезервировано для TTL-based кэширования HTTP-ответов |

**Критерии для исключения:**
1. Timestamp не влияет на детерминизм batch-операций
2. Timestamp необходим для real-time мониторинга/операций
3. Timestamp не используется в данных Bronze/Silver/Gold

## Alternatives Considered

### 1. Глобальная фиксация времени через context manager

```python
with frozen-time(timestamp):
    await pipeline.run()
```

**Отвергнуто**: Слишком магически, сложно отлаживать, не работает с async.

### 2. Injection через DI container

**Отвергнуто**: Over-engineering для простой задачи.

### 3. Полный запрет datetime.now() везде

**Отвергнуто**: Есть легитимные случаи (TTL расчёт в operations.py, SCD2 timestamps).

## Consequences

### Положительные

- Пайплайны детерминистичны при одинаковых входных данных
- Упрощение unit-тестов (можно передать фиксированный timestamp)
- Консистентные metadata в Bronze/Silver записях

### Отрицательные

- Небольшое усложнение API (дополнительные параметры)
- Требуется обновление существующего кода

### Нейтральные

- Production по умолчанию использует random jitter (`deterministic=False`)
- Backward-compatible fallbacks сохранены

## Related

- RULES.md §4.3 Детерминизм и Воспроизводимость
- `tests/architecture/test-no-random-in-writers.py`
- `tests/architecture/test-no-datetime-now-in-infrastructure.py`
- `tests/architecture/test-no-structlog-in-application-interfaces.py`
- ADR-006 Logger and Metrics Ports
