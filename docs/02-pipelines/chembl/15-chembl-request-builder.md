# 15 ChEMBL Request Builder

## Описание

`ChemblRequestBuilder` — конструктор запросов ChEMBL. Инкапсулирует объект конфигурации источника (`SourceConfig`) и на его основе строит стандартные объекты запроса `ClientRequest` для различных маршрутов API ChEMBL.

## Модуль

`bioetl/clients/chembl/client.py`

## Структура

ChemblRequestBuilder является dataclass и содержит:

- `source_config: SourceConfig` — конфигурация источника данных ChEMBL

## Основной метод

### `build(self, *, route: str, ids: Sequence[str] | None = None, filters: Mapping[str, object] | None = None, pagination: PaginationParams | None = None, context: RequestContext | None = None) -> ClientRequest`

Формирует экземпляр `ClientRequest` с указанным маршрутом и параметрами.

**Параметры:**
- `route` — маршрут API (например, `"activity"`)
- `ids` — последовательность идентификаторов для запроса (опционально)
- `filters` — фильтры для запроса (опционально)
- `pagination` — параметры пагинации (опционально)
- `context` — контекст запроса (опционально)

**Процесс построения:**

1. Формирование URL: создание URL на основе базового адреса из `SourceConfig` и маршрута
2. Добавление параметров: включение IDs, фильтров и параметров пагинации в запрос
3. Создание запроса: формирование объекта `ClientRequest` с полной информацией

**Возвращает:** объект `ClientRequest` для выполнения запроса.

## Использование

Builder используется внутри `ChemblClient` для построения запросов:

```python
builder = ChemblRequestBuilder(source_config=config)
request = builder.build(
    route="activity",
    ids=["CHEMBL123"],
    filters={"assay_type": "B"},
    pagination=PaginationParams(limit=100, offset=0)
)
```

## Related Components

- **ChemblClient**: использует builder для построения запросов (см. `docs/02-pipelines/chembl/14-chembl-client.md`)
- **SourceConfig**: конфигурация источника данных

