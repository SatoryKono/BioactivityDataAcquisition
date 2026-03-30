---
Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# ADR-011: Отказ от механизма Watermark

**Date:** 2025-12-23
**Decision makers:** @BioETL-Team

## Context

Механизм Watermark был реализован для поддержки инкрементальной загрузки данных:
- `Watermark` value object в domain слое для хранения позиции (timestamp, offset, ID)
- `extract-watermark()` метод в каждом пайплайне
- Отдельные классы `*WatermarkExtractor` для каждого типа сущности
- Поле `watermark-field` в конфигурации пайплайнов
- Параметр `watermark` в `DataSourcePort.fetch()` и `CheckpointPort`

### Проблемы текущего подхода

1. **Избыточная сложность**: Каждый новый пайплайн требует создания отдельного WatermarkExtractor класса
2. **Дублирование логики**: Экстракторы содержат повторяющуюся логику обработки полей
3. **Привязка к инкрементальной модели**: Watermark предполагает наличие монотонно возрастающего ключа, что не всегда доступно
4. **Смешение ответственностей**: Checkpoint должен сохранять состояние пайплайна, а не специфичную позицию в данных

### Альтернативные подходы

1. **Cursor-based pagination**: API провайдеров (ChEMBL, UniProt) используют встроенную пагинацию
2. **Full reload**: Для небольших датасетов (< 1M записей) полная перезагрузка эффективнее
3. **Content-based deduplication**: Delta Lake merge по `content-hash` автоматически обрабатывает дубликаты

## The Decision

**Удаление механизма Watermark** из проекта:

1. Удаление `Watermark` value object из domain/types.py
2. Удаление параметра `watermark` из `DataSourcePort.fetch()`
3. Удаление метода `extract-watermark()` из `BasePipeline`
4. Удаление всех `*WatermarkExtractor` классов
5. Удаление поля `watermark-field` из конфигурации
6. Упрощение `CheckpointPort` - хранение только метаданных запуска

## Justification

### 1. Упрощение пайплайнов

| До | После |
|---|---|
| BasePipeline + extract-watermark() | BasePipeline (без watermark) |
| *WatermarkExtractor классы | Удалены |
| watermark-field в config | Удалено |
| Watermark value object | Удалён |

### 2. Уменьшение кода

- Удаление ~500 строк кода (extractors, tests)
- Упрощение сигнатур методов
- Меньше абстракций для понимания

### 3. Соответствие реальным use cases

Анализ показал:
- Большинство загрузок выполняются как полный rebuild
- Инкрементальная загрузка редко используется
- Content-based deduplication через Delta Lake merge эффективнее

### 4. Упрощение добавления новых пайплайнов

Новый пайплайн требует только:
- `transform-bronze-to-silver()` — основная логика
- `should-write-gold()` — опциональная фильтрация

## Implementation

### DataSourcePort

```python
# Было
def fetch(
    self,
    entity_type: str,
    watermark: Watermark | None = None,
    limit: int | None = None,
) -> AsyncIterator[dict[str, Any]]:
    ...

# Стало
def fetch(
    self,
    entity_type: str,
    limit: int | None = None,
    query: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    ...
```

### CheckpointPort

```python
# Было
async def save(
    self,
    pipeline: str,
    watermark: Watermark,
    run-id: RunID,
    metadata: dict[str, Any],
) -> None:
    ...

# Стало
async def save(
    self,
    pipeline: str,
    run-id: RunID,
    metadata: dict[str, Any],
) -> None:
    ...
```

### BasePipeline

```python
# Было
class BasePipeline(ABC):
    @abstractmethod
    def extract-watermark(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> Watermark:
        ...

# Стало
class BasePipeline(ABC):
    # Метод extract-watermark удалён
    pass
```

## Consequences

### Positive

1. **Простота**: Меньше кода, меньше абстракций
2. **Поддерживаемость**: Проще добавлять новые пайплайны
3. **Понятность**: Новые разработчики быстрее разбираются в коде
4. **Надёжность**: Меньше точек отказа

### Negative

1. **Нет инкрементальной загрузки**: Все запуски — полный reload
2. **Потенциально больше API вызовов**: При больших датасетах

### Mitigation

1. **Content-based deduplication**: Delta Lake merge по `content-hash` предотвращает дубликаты
2. **Limit параметр**: Ограничение количества записей для тестирования
3. **Фильтрация на стороне API**: Использование query параметра для ограничения данных

## Related ADRs

- [ADR-002](ADR-002-medallion-architecture.md): Medallion Architecture — сохраняется, меняется только механизм загрузки
- [ADR-005](ADR-005-composition-layer-separation.md): Composition Layer — упрощён, удалены watermark factories
- [ADR-010](ADR-010-local-only-deployment.md): Local-Only Deployment — упрощение инфраструктуры
- [ADR-026](ADR-026-composite-pipeline-pattern.md): Composite Pipeline Pattern — использует full scan для агрегации данных
- [ADR-030](ADR-030-publication-pagination-strategy.md): Publication Pagination Strategy — развивает концепцию полной загрузки
- [ADR-031](ADR-031-loading-strategy-formalization.md): Loading Strategy Formalization — формализация стратегий загрузки

## Migration Notes

При обновлении:
1. Удалить поле `watermark-field` из конфигов пайплайнов
2. Удалить метод `extract-watermark()` из кастомных пайплайнов
3. Обновить тесты, использующие Watermark
