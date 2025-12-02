# 02 Client Factory Registry

## Описание

`ClientFactoryRegistry` — реестр фабрик клиентов, используемый в пайплайнах. Хранит словарь фабрик (*ClientFactory*) по именам (namespace), например `"chembl"` для фабрики клиентов ChEMBL. Пайплайн Chembl при инициализации создаёт *chembl_factory* и регистрирует её в реестре, после чего может получать фабрику через `get("chembl")` и создавать конкретные клиенты/дескрипторы для сущностей.

## Модуль

`src/bioetl/pipelines/client_registry.py`

## Основные методы

### `get(self, name: str) -> ClientFactory[Any]`

Возвращает фабрику клиента по заданному имени или выбрасывает исключение, если такая не зарегистрирована.

**Параметры:**
- `name` — имя фабрики (namespace), например `"chembl"`

**Возвращает:** фабрику клиента для указанного имени.

**Исключения:**
- `KeyError` — если фабрика с указанным именем не зарегистрирована

## Использование

Реестр используется в пайплайнах для получения фабрик клиентов:

```python
registry = ClientFactoryRegistry()
chembl_factory = registry.get("chembl")
client = chembl_factory.create_client(...)
```

## Related Components

- **ChemblCommonPipeline**: использует реестр для получения фабрик клиентов (см. `docs/02-pipelines/chembl/common/05-chembl-base-pipeline.md`)
- **ChemblDescriptorFactory**: использует реестр для создания дескрипторов (см. `docs/02-pipelines/chembl/common/07-chembl-descriptor-factory.md`)

