# ADR-011: Отказ от механизма Watermark

**Status:** Accepted
**Date:** 2025-12-23
**Decision makers:** @BioETL-Team

## Context

Механизм Watermark был реализован для поддержки инкрементальной загрузки данных:
- `Watermark` value object в domain слое для хранения позиции (timestamp, offset, ID)
- `extract_watermark()` метод в каждом пайплайне
- Отдельные классы `*WatermarkExtractor` для каждого типа сущности
- Поле `watermark_field` в конфигурации пайплайнов
- Параметр `watermark` в `DataSourcePort.fetch()` и `CheckpointPort`

### Проблемы текущего подхода

1. **Избыточная сложность**: Каждый новый пайплайн требует создания отдельного WatermarkExtractor класса
2. **Дублирование логики**: Экстракторы содержат повторяющуюся логику обработки полей
3. **Привязка к инкрементальной модели**: Watermark предполагает наличие монотонно возрастающего ключа, что не всегда доступно
4. **Смешение ответственностей**: Checkpoint должен сохранять состояние пайплайна, а не специфичную позицию в данных

### Альтернативные подходы

1. **Cursor-based pagination**: API провайдеров (ChEMBL, UniProt) используют встроенную пагинацию
2. **Full reload**: Для небольших датасетов (< 1M записей) полная перезагрузка эффективнее
3. **Content-based deduplication**: Delta Lake merge по `content_hash` автоматически обрабатывает дубликаты

## The Decision

**Удаление механизма Watermark** из проекта:

1. Удаление `Watermark` value object из domain/types.py
2. Удаление параметра `watermark` из `DataSourcePort.fetch()`
3. Удаление метода `extract_watermark()` из `BasePipeline`
4. Удаление всех `*WatermarkExtractor` классов
5. Удаление поля `watermark_field` из конфигурации
6. Упрощение `CheckpointPort` - хранение только метаданных запуска

## Justification

### 1. Упрощение пайплайнов

| До | После |
|---|---|
| BasePipeline + extract_watermark() | BasePipeline (без watermark) |
| *WatermarkExtractor классы | Удалены |
| watermark_field в config | Удалено |
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
- `transform_bronze_to_silver()` — основная логика
- `should_write_gold()` — опциональная фильтрация

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
    run_id: RunID,
    metadata: dict[str, Any],
) -> None:
    ...

# Стало
async def save(
    self,
    pipeline: str,
    run_id: RunID,
    metadata: dict[str, Any],
) -> None:
    ...
```

### BasePipeline

```python
# Было
class BasePipeline(ABC):
    @abstractmethod
    def extract_watermark(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> Watermark:
        ...

# Стало
class BasePipeline(ABC):
    # Метод extract_watermark удалён
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

1. **Content-based deduplication**: Delta Lake merge по `content_hash` предотвращает дубликаты
2. **Limit параметр**: Ограничение количества записей для тестирования
3. **Фильтрация на стороне API**: Использование query параметра для ограничения данных

## Related ADRs

- **ADR-010**: Local-Only Deployment — упрощение инфраструктуры
- **ADR-002**: Medallion Architecture — сохраняется, меняется только механизм загрузки
- **ADR-005**: Composition Layer — упрощён, удалены watermark factories

## Migration Notes

При обновлении:
1. Удалить поле `watermark_field` из конфигов пайплайнов
2. Удалить метод `extract_watermark()` из кастомных пайплайнов
3. Обновить тесты, использующие Watermark
