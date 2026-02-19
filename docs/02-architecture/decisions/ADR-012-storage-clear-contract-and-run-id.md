# ADR-012: Storage Clear Contract and Run ID Consistency

**Status:** Accepted
**Date:** 2025-12-23
**Decision makers:** @BioETL-Team

## Context

Два архитектурных вопроса требовали решения:

### Проблема 1: Дублирование run-id

`BasePipeline` генерировал новый `run-id` в конструкторе (`base.py:60`), игнорируя `run-id`, переданный из CLI через `PipelineRunContext`. Это приводило к рассинхронизации:

- CLI логировал один `run-id`
- Записи в Silver содержали другой `run-id` в метаполе `-run-id`
- Чекпоинты и блокировки использовали третий идентификатор

### Проблема 2: Reflection для очистки хранилища

`PipelineRunner.-clear-exports()` использовал `hasattr()` для проверки наличия методов `clear-csv()` и `clear-delta()`:

```python
if hasattr(storage, "clear-csv"):
    storage.clear-csv(table-name)
```

Это нарушало принцип явных контрактов и затрудняло статический анализ.

### Проблема 3: Нарушение Medallion-инвариантов

Очистка Silver/Gold выполнялась для **всех** типов запусков, включая `incremental`. Это противоречило семантике merge/upsert для инкрементальных обновлений.

## Decision

### 1. Единый run-id от CLI до метаполей

- `BasePipeline.--init--()` принимает `run-id` как обязательный параметр
- `run-id` генерируется **только** в CLI (`cli.py:86`)
- Все компоненты (logger, context, checkpoints, locks) используют один `run-id`

**Изменённая сигнатура:**

```python
class BasePipeline(ABC):
    def --init--(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineServices,
        run-id: RunID,  # NEW: обязательный параметр
    ) -> None:
```

### 2. Формализация API очистки в StoragePort

Добавлены методы в `StoragePort` (`domain/ports/storage.py`, импорт из фасада `domain/ports/`):

```python
def clear-silver(self, table-name: str) -> int:
    """Clear Silver layer data for a specific table."""
    ...

def clear-gold(self, table-name: str) -> int:
    """Clear Gold layer data for a specific table."""
    ...
```

Удалён `hasattr()` из `runner.py` — теперь используются явные вызовы методов порта.

### 3. Medallion-инварианты по run-type

Очистка выполняется **только** для destructive run types:

```python
should-clear = self.-runtime.run-type in (RunType.REBUILD, RunType.BACKFILL)
```

| Run Type | Очистка | Обоснование |
|----------|---------|-------------|
| `incremental` | НЕТ | Merge/upsert по content-hash |
| `backfill` | ДА | Заполнение исторических данных |
| `rebuild` | ДА | Полная перестройка таблицы |

## Consequences

### Positive

- **Трассируемость**: Один `run-id` во всех слоях и компонентах
- **Типобезопасность**: Явные методы в `StoragePort` вместо reflection
- **Data Integrity**: Incremental runs не удаляют существующие данные
- **Тестируемость**: Можно проверить контракт через type checking

### Negative

- **Breaking Change**: Сигнатура `BasePipeline.--init--()` изменилась (4 параметра вместо 3)
- **Миграция тестов**: Все тесты, создающие pipeline напрямую, требуют обновления

### Risks

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Чекпоинты со старым форматом | Низкая | `load()` игнорирует `run-id` в файле |
| Дубликаты при incremental | Средняя | Merge по `content-hash` предотвращает дубли |

## Related ADRs

- [ADR-001](ADR-001-delta-lake-vs-parquet.md): Delta Lake vs Parquet — storage format being cleared
- [ADR-002](ADR-002-medallion-architecture.md): Medallion Architecture — Medallion invariants for clear operations
- [ADR-013](ADR-013-async-storage-cleanup.md): Async Storage Cleanup — async implementation of clear methods

## References

- RULES.md §1.1 — Ports & Adapters architecture
- CLAUDE.md §3.2 — Content Hash нормализация
