# ADR-012: Storage Clear Contract and Run ID Consistency

## Status

Accepted

## Date

2025-12-23

## Context

Два архитектурных вопроса требовали решения:

### Проблема 1: Дублирование run_id

`BasePipeline` генерировал новый `run_id` в конструкторе (`base.py:60`), игнорируя `run_id`, переданный из CLI через `PipelineRunContext`. Это приводило к рассинхронизации:

- CLI логировал один `run_id`
- Записи в Silver содержали другой `run_id` в метаполе `_run_id`
- Чекпоинты и блокировки использовали третий идентификатор

### Проблема 2: Reflection для очистки хранилища

`PipelineRunner._clear_exports()` использовал `hasattr()` для проверки наличия методов `clear_csv()` и `clear_delta()`:

```python
if hasattr(storage, "clear_csv"):
    storage.clear_csv(table_name)
```

Это нарушало принцип явных контрактов и затрудняло статический анализ.

### Проблема 3: Нарушение Medallion-инвариантов

Очистка Silver/Gold выполнялась для **всех** типов запусков, включая `incremental`. Это противоречило семантике merge/upsert для инкрементальных обновлений.

## Decision

### 1. Единый run_id от CLI до метаполей

- `BasePipeline.__init__()` принимает `run_id` как обязательный параметр
- `run_id` генерируется **только** в CLI (`cli.py:86`)
- Все компоненты (logger, context, checkpoints, locks) используют один `run_id`

**Изменённая сигнатура:**

```python
class BasePipeline(ABC):
    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineServices,
        run_id: RunID,  # NEW: обязательный параметр
    ) -> None:
```

### 2. Формализация API очистки в StoragePort

Добавлены методы в `StoragePort` (`domain/ports.py`):

```python
def clear_silver(self, table_name: str) -> int:
    """Clear Silver layer data for a specific table."""
    ...

def clear_gold(self, table_name: str) -> int:
    """Clear Gold layer data for a specific table."""
    ...
```

Удалён `hasattr()` из `runner.py` — теперь используются явные вызовы методов порта.

### 3. Medallion-инварианты по run_type

Очистка выполняется **только** для destructive run types:

```python
should_clear = self._runtime.run_type in (RunType.REBUILD, RunType.BACKFILL)
```

| Run Type | Очистка | Обоснование |
|----------|---------|-------------|
| `incremental` | НЕТ | Merge/upsert по content_hash |
| `backfill` | ДА | Заполнение исторических данных |
| `rebuild` | ДА | Полная перестройка таблицы |

## Consequences

### Positive

- **Трассируемость**: Один `run_id` во всех слоях и компонентах
- **Типобезопасность**: Явные методы в `StoragePort` вместо reflection
- **Data Integrity**: Incremental runs не удаляют существующие данные
- **Тестируемость**: Можно проверить контракт через type checking

### Negative

- **Breaking Change**: Сигнатура `BasePipeline.__init__()` изменилась (4 параметра вместо 3)
- **Миграция тестов**: Все тесты, создающие pipeline напрямую, требуют обновления

### Risks

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Чекпоинты со старым форматом | Низкая | `load()` игнорирует `run_id` в файле |
| Дубликаты при incremental | Средняя | Merge по `content_hash` предотвращает дубли |

## Related ADRs

- [ADR-001](ADR-001-delta-lake-vs-parquet.md): Delta Lake vs Parquet — storage format being cleared
- [ADR-002](ADR-002-medallion-architecture.md): Medallion Architecture — Medallion invariants for clear operations
- [ADR-013](ADR-013-async-storage-cleanup.md): Async Storage Cleanup — async implementation of clear methods

## References

- RULES.md §1.1 — Ports & Adapters architecture
- CLAUDE.md §3.2 — Content Hash нормализация
