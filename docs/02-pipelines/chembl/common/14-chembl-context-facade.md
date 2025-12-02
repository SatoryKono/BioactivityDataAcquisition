# 14 ChEMBL Context Facade

## Описание

`ChemblContextFacade` — "фасад" контекста ChEMBL. Структура для передачи в дескриптор фабрику необходимых компонентов: фабрики транспорта, стратегии пагинации и её имени, набора фабрик пагинации, номера релиза, готового клиента Chembl (если уже создан), либо фабрики клиента.

## Модуль

`src/bioetl/clients/chembl/descriptor_factory.py`

## Наследование

Класс является dataclass и наследуется от `object`.

## Структура

Facade содержит следующие поля:

- `transport_factory` — фабрика транспорта для HTTP-запросов
- `pagination_strategy` — стратегия пагинации
- `pagination_strategy_name` — имя стратегии пагинации (опционально)
- `pagination_factories` — набор фабрик пагинации
- `chembl_release` — номер релиза ChEMBL (опционально)
- `chembl_client` — готовый клиент ChEMBL (опционально)
- `client_factory` — фабрика клиента ChEMBL (опционально)

## Использование

Facade используется в `ChemblDescriptorFactory` для передачи контекста в дескрипторы:

```python
from bioetl.clients.chembl.descriptor_factory import ChemblContextFacade

facade = ChemblContextFacade(
    transport_factory=transport_factory,
    pagination_strategy=pagination_strategy,
    chembl_release="33",
    client_factory=client_factory
)
```

## Related Components

- **ChemblDescriptorFactory**: использует facade для создания дескрипторов (см. `docs/02-pipelines/chembl/common/07-chembl-descriptor-factory.md`)
- **ChemblClient**: клиент ChEMBL API (см. `docs/02-pipelines/chembl/common/01-chembl-client.md`)

