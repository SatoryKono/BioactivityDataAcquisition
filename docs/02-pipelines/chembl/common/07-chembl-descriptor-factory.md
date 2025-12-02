# 07 ChEMBL Descriptor Factory

## Описание

`ChemblDescriptorFactory` — фабрика для создания дескрипторов ChEMBL. Инкапсулирует *ChemblContextFacade* (контекст подключения: транспорт, параметры пагинации, фабрику клиента и пр.) и словарь стратегий выборки данных. Метод `build(entity)` у фабрики (реализован через внутренний builder) возвращает сконфигурированный экземпляр дескриптора *ChemblExtractionServiceDescriptor* или аналогичный для указанной сущности.

## Модуль

`src/bioetl/clients/chembl/descriptor_factory.py`

## Наследование

Класс является dataclass и наследуется от `object`.

## Структура

Фабрика содержит следующие поля:

- `context_facade: ChemblContextFacade` — фасад контекста ChEMBL
- `fetcher_strategies: dict[str, FetcherStrategy]` — набор стратегий получения данных по типам сущностей
- `fallback_rows: Callable[[Any, Exception], list[dict[str, Any]]] | None` — функция для генерации фолбэк-значений при ошибках (опционально)
- `sort_fields: Mapping[str, Sequence[str]] | None` — поля сортировки для детерминизма (опционально)

## Основной метод

### `build(self, entity_name: str) -> ChemblExtractionServiceDescriptor`

Создать дескриптор извлечения для сущности с именем `entity_name` (использует предварительно сконфигурированные стратегии и контекст).

**Параметры:**
- `entity_name` — имя сущности (например, "activity", "assay", "target")

**Процесс создания:**
1. Получение конфигурации сущности из фасада контекста
2. Создание стратегии выборки для сущности
3. Настройка пагинации и клиента API
4. Создание функций выборки и финализации

**Возвращает:** дескриптор извлечения для указанной сущности.

## Использование

Фабрика используется в `ChemblBasePipeline` для создания дескрипторов извлечения:

```python
factory = ChemblDescriptorFactory(...)
descriptor = factory.build("activity")
```

## Related Components

- **ChemblContextFacade**: фасад контекста ChEMBL (см. `docs/02-pipelines/chembl/common/14-chembl-context-facade.md`)
- **ChemblExtractionServiceDescriptor**: дескриптор извлечения (см. `docs/02-pipelines/chembl/common/08-chembl-extraction-service-descriptor.md`)
- **ChemblBasePipeline**: использует фабрику для создания дескрипторов (см. `docs/02-pipelines/chembl/common/05-chembl-base-pipeline.md`)

