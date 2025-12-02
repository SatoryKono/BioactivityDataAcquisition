# 21 ChEMBL Descriptor Factory

## Описание

`ChemblDescriptorFactory` — фабрика для создания дескрипторов ChEMBL. Инкапсулирует *ChemblContextFacade* (контекст подключения: транспорт, параметры пагинации, фабрику клиента и пр.) и словарь стратегий выборки данных. Метод `build(entity)` у фабрики (реализован через внутренний builder) возвращает сконфигурированный экземпляр дескриптора *ChemblExtractionServiceDescriptor* или аналогичный для указанной сущности.

## Модуль

`src/bioetl/clients/chembl/descriptor_factory.py`

## Наследование

Класс является dataclass.

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

Фабрика используется в `ChemblCommonPipeline` для создания дескрипторов извлечения:

```python
factory = ChemblDescriptorFactory(...)
descriptor = factory.build("activity")
```

## Related Components

- **ChemblExtractionServiceDescriptor**: дескриптор извлечения (см. `docs/02-pipelines/chembl/common/22-chembl-extraction-service-descriptor.md`)
- **ChemblCommonPipeline**: использует фабрику для создания дескрипторов (см. `docs/02-pipelines/chembl/common/18-chembl-common-pipeline.md`)

