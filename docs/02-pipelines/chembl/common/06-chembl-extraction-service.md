# 06 ChEMBL Extraction Service

## Описание

`ChemblExtractionService` — сервис, инкапсулирующий общие шаги извлечения данных из ChEMBL. Управляет определением актуального релиза ChEMBL, формированием контекста выборки, побатчевой загрузкой записей через клиент ChEMBL и финализацией объединённого DataFrame результатов.

## Модуль

`src/bioetl/pipelines/chembl/common/chembl_extraction_service.py`

## Основные свойства и методы

### `chembl_release(self) -> str | None`

Свойство, возвращающее кешированную версию релиза ChEMBL (определяется при первом запросе).

### `resolve_chembl_release(self, chembl_client: BaseClient) -> str`

Определяет версию релиза ChEMBL через вызов метода `status()` у клиента, кеширует и возвращает её.

**Параметры:**
- `chembl_client` — клиент ChEMBL API

**Возвращает:** версию релиза ChEMBL.

### `build_context(self, descriptor: Any, pipeline: Any, *, metadata_filters: Mapping[str, Any] | None = None, fetch_mode: str = "default") -> dict[str, Any]`

Создаёт контекст выполнения для выборки: дополняет контекст дескриптора параметрами (фильтры, режим выборки, версия релиза).

**Параметры:**
- `descriptor` — дескриптор извлечения
- `pipeline` — пайплайн
- `metadata_filters` — фильтры метаданных (опционально)
- `fetch_mode` — режим выборки (по умолчанию "default")

**Возвращает:** словарь с контекстом выполнения.

### `finalize_dataframe(self, dataframe: pd.DataFrame, finalizer: Any, stats: BatchExtractionStats) -> tuple[pd.DataFrame, BatchExtractionStats]`

Применяет функцию-финализатор к объединённому DataFrame и обновляет статистику (кол-во строк, длительность).

**Параметры:**
- `dataframe` — объединённый DataFrame
- `finalizer` — функция финализации
- `stats` — статистика извлечения

**Возвращает:** кортеж из финализированного DataFrame и обновлённой статистики.

### `run_descriptor_extraction(self, pipeline: Any, descriptor: Any, ids: Sequence[str] | None, *, summary_event: str, metadata_filters: Mapping[str, Any] | None = None, fetch_mode: str = "default", **batch_kwargs) -> tuple[pd.DataFrame, BatchExtractionStats]`

Выполняет извлечение данных по дескриптору: формирует контекст, запускает итеративную выборку через fetcher (с учётом paging и batch_size) и возвращает объединённый DataFrame и статистику.

**Параметры:**
- `pipeline` — пайплайн
- `descriptor` — дескриптор извлечения
- `ids` — последовательность идентификаторов (опционально)
- `summary_event` — событие для логирования
- `metadata_filters` — фильтры метаданных (опционально)
- `fetch_mode` — режим выборки (по умолчанию "default")
- `**batch_kwargs` — дополнительные параметры батчирования

**Возвращает:** кортеж из DataFrame с данными и статистики извлечения.

## Внутренние методы

### `_normalize_ids(self, ids: Sequence[str] | None, context: Mapping[str, Any]) -> list[str] | None`

Нормализует список идентификаторов (приводит к строкам) либо извлекает их из контекста.

**Параметры:**
- `ids` — последовательность идентификаторов (опционально)
- `context` — контекст выполнения

**Возвращает:** нормализованный список идентификаторов или `None`.

### `_resolve_page_size(self, context: Mapping[str, Any], default: int = 1000) -> int`

Определяет размер страницы (лимит) для запросов из контекста или берёт значение по умолчанию.

**Параметры:**
- `context` — контекст выполнения
- `default` — значение по умолчанию (1000)

**Возвращает:** размер страницы для пагинации.

### `_resolve_client_settings(self, context: Mapping[str, Any]) -> Mapping[str, Any]`

Получает доп. настройки клиента из контекста (если заданы).

**Параметры:**
- `context` — контекст выполнения

**Возвращает:** словарь с настройками клиента или пустой словарь.

### `_build_client_fetcher(self, chembl_client: BaseClient, *, page_size: int, client_settings: Mapping[str, Any] | None = None) -> Callable[[Sequence[str] | None], Any]`

Возвращает функцию для выборки батча: формирует объект `ClientRequest` и использует `chembl_client.iter_records` для получения результатов.

**Параметры:**
- `chembl_client` — клиент ChEMBL
- `page_size` — размер страницы
- `client_settings` — дополнительные настройки клиента (опционально)

**Возвращает:** функцию-выборку для получения данных.

### `_resolve_fetcher(self, descriptor: Any, context: Mapping[str, Any], *, page_size: int, client_settings: Mapping[str, Any] | None = None) -> Callable[[Sequence[str] | None], Any]`

Выбирает функцию выборки: если в дескрипторе определена фабрика fetcher, использует её; иначе строит fetcher через ChemblClient (вызывая `_build_client_fetcher`).

**Параметры:**
- `descriptor` — дескриптор извлечения
- `context` — контекст выполнения
- `page_size` — размер страницы
- `client_settings` — дополнительные настройки клиента (опционально)

**Возвращает:** функцию-выборку для получения данных.

## Related Components

- **ChemblExtractionServiceDescriptor**: дескриптор извлечения (см. `docs/02-pipelines/chembl/common/08-chembl-extraction-service-descriptor.md`)
- **ChemblBasePipeline**: использует сервис для извлечения данных (см. `docs/02-pipelines/chembl/common/05-chembl-base-pipeline.md`)

