# Руководство: Подключение нового источника данных

Этот документ описывает полный цикл подключения совершенно нового источника данных (провайдера) в BioETL.

В качестве примера мы рассмотрим подключение источника **PubMed** (сущность `Publication`).

## Общий алгоритм

1.  **Инфраструктура**: Создать адаптер (клиент API) для взаимодействия с внешним источником.
2.  **Конфигурация**: Определить настройки подключения (URL, ключи API) и конфиг пайплайна.
3.  **Приложение**: Реализовать класс пайплайна.
4.  **Сборка**: Создать фабрику и зарегистрировать источник в `bootstrap.py`.

---

## Шаг 1: Создание адаптера (Infrastructure Layer)

Создайте клиент для API в `src/bioetl/infrastructure/adapters/<provider>/`.
Адаптер должен использовать `UnifiedHTTPClient` или специфичную библиотеку, обернутую в наш интерфейс.

**Пример:** `src/bioetl/infrastructure/adapters/pubmed/client.py`

```python
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

class PubMedAdapter:
    """Адаптер для PubMed API."""
    def __init__(self, http_client: UnifiedHTTPClient, api_key: str | None = None):
        self.http_client = http_client
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.api_key = api_key

    async def fetch_publications(self, query: str, retmax: int = 100):
        """Получение публикаций."""
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": retmax
        }
        if self.api_key:
            params["api_key"] = self.api_key

        # Используем UnifiedHTTPClient для запросов (с метриками и повторами)
        return await self.http_client.get(f"{self.base_url}/esearch.fcgi", params=params)
```

## Шаг 2: Конфигурация

### 2.1 Настройки приложения
Убедитесь, что настройки (например, API ключи) доступны через `src/bioetl/infrastructure/config.py`.

### 2.2 Конфиг пайплайна
Создайте `configs/pipelines/pubmed/publication.yaml`.

```yaml
pipeline:
    name: pubmed_publication
    provider: pubmed
    entity: publication

source:
    type: api
    load_strategy: incremental

sink:
    silver:
        path: "s3://bioetl-silver/pubmed/publication/"
        format: delta
        primary_key: ["pmid"]
```

## Шаг 3: Реализация пайплайна (Application Layer)

Создайте `src/bioetl/application/pipelines/pubmed_publication.py`.

```python
from bioetl.application.core.base import BasePipeline
# ... (см. шаблоны и примеры для ChEMBL)

class PubMedPublicationPipeline(BasePipeline):
    # Реализация методов transform_bronze_to_silver и др.
    pass
```

## Шаг 4: Регистрация (Composition Layer)

В v5.1 сборка пайплайнов декларативна и централизована.

### 4.1 Регистрация создателя DataSource
Добавьте функцию создания вашего адаптера в `src/bioetl/composition/factories/data_source_registry.py`.

```python
def create_pubmed_data_source(settings, pipeline_config, filter_config=None):
    http_client = HttpClientFactory.create_for_provider("pubmed", settings)
    data_source = PubMedAdapter(http_client, api_key=settings.pubmed_api_key)
    return _wrap_with_filter(data_source, filter_config)

# Зарегистрируйте в словаре _creators класса DataSourceRegistry
_creators = {
    # ...
    "pubmed": create_pubmed_data_source,
}
```

### 4.2 Регистрация пайплайна
Добавьте определение пайплайна в `src/bioetl/composition/factories/pipeline_factories.py`.

```python
from bioetl.application.pipelines.pubmed.publications import PubMedPublicationsPipeline
from bioetl.infrastructure.schemas.silver import PUBMED_PUBLICATION_SCHEMA

pubmed_publications_factory = GenericPipelineFactory(
    pipeline_name="pubmed_publications",
    pipeline_class=PubMedPublicationsPipeline,
    provider="pubmed",
    silver_schema=PUBMED_PUBLICATION_SCHEMA,
)

def register_all_pipelines() -> None:
    # ...
    PipelineRegistry.register_factory(pubmed_publications_factory)
```

Теперь ваш пайплайн автоматически доступен через CLI по имени `pubmed_publications`.

## Чек-лист

- [ ] Адаптер источника реализован.
- [ ] Конфиг YAML создан.
- [ ] Пайплайн реализован.
- [ ] Источник зарегистрирован в `DataSourceRegistry`.
- [ ] Пайплайн зарегистрирован в `pipeline_factories.py`.
