______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-011: Отказ от механизма Watermark

**Date:** 2025-12-23
**Status:** Accepted
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
1. **Дублирование логики**: Экстракторы содержат повторяющуюся логику обработки полей
1. **Привязка к инкрементальной модели**: Watermark предполагает наличие монотонно возрастающего ключа, что не всегда доступно
1. **Смешение ответственностей**: Checkpoint должен сохранять состояние пайплайна, а не специфичную позицию в данных

### Альтернативные подходы

1. **Cursor-based pagination**: API провайдеров (ChEMBL, UniProt) используют встроенную пагинацию
1. **Full reload**: Для небольших датасетов (< 1M записей) полная перезагрузка эффективнее
1. **Content-based deduplication**: Delta Lake merge по `content-hash` автоматически обрабатывает дубликаты

## Decision

**Удаление механизма Watermark** из проекта:

1. Удаление `Watermark` value object из domain/types.py
1. Удаление параметра `watermark` из `DataSourcePort.fetch()`
1. Удаление метода `extract-watermark()` из `BasePipeline`
1. Удаление всех `*WatermarkExtractor` классов
1. Удаление поля `watermark-field` из конфигурации
1. Упрощение `CheckpointPort` - хранение только метаданных запуска

## Justification

### 1. Упрощение пайплайнов

| До                                 | После                        |
| ---------------------------------- | ---------------------------- |
| BasePipeline + extract-watermark() | BasePipeline (без watermark) |
| \*WatermarkExtractor классы        | Удалены                      |
| watermark-field в config           | Удалено                      |
| Watermark value object             | Удалён                       |

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
) -> AsyncIterator[dict[str, Any]]: ...


# Стало
def fetch(
    self,
    entity_type: str,
    limit: int | None = None,
    query: str | None = None,
) -> AsyncIterator[dict[str, Any]]: ...
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
1. **Поддерживаемость**: Проще добавлять новые пайплайны
1. **Понятность**: Новые разработчики быстрее разбираются в коде
1. **Надёжность**: Меньше точек отказа

### Negative

1. **Нет инкрементальной загрузки**: Все запуски — полный reload
1. **Потенциально больше API вызовов**: При больших датасетах

### Mitigation

1. **Content-based deduplication**: Delta Lake merge по `content-hash` предотвращает дубликаты
1. **Limit параметр**: Ограничение количества записей для тестирования
1. **Фильтрация на стороне API**: Использование query параметра для ограничения данных

## References

- [ADR-002](ADR-002-medallion-architecture.md): Medallion Architecture — сохраняется, меняется только механизм загрузки
- [ADR-005](ADR-005-composition-layer-separation.md): Composition Layer — упрощён, удалены watermark factories
- [ADR-010](ADR-010-local-only-deployment.md): Local-Only Deployment — упрощение инфраструктуры
- [ADR-026](ADR-026-composite-pipeline-pattern.md): Composite Pipeline Pattern — использует full scan для агрегации данных
- [ADR-030](ADR-030-publication-pagination-strategy.md): Publication Pagination Strategy — развивает концепцию полной загрузки
- [ADR-031](ADR-031-loading-strategy-formalization.md): Loading Strategy Formalization — формализация стратегий загрузки

## Rollout

При обновлении:

1. Удалить поле `watermark-field` из конфигов пайплайнов
1. Удалить метод `extract-watermark()` из кастомных пайплайнов
1. Обновить тесты, использующие Watermark

## Compliance

| Control      | Requirement                                                                | Status | Evidence                                |
| ------------ | -------------------------------------------------------------------------- | ------ | --------------------------------------- |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-011-remove-watermark-mechanism.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                              |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                        |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria`    |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                            |

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [ ] The decision is documented with current status, date, and owner metadata.
- [ ] The implementation path or adoption boundary is testable and linked from the ADR.
- [ ] Supersession or migration impact is documented when the decision changes an earlier posture.
- [ ] Related docs, contracts, and operational guidance are aligned with this ADR.
