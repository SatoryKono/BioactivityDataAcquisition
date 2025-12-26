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

В v5.2 сборка пайплайнов декларативна и централизована через `ProviderRegistry`.

### 4.1 Регистрация провайдера в ProviderRegistry

Добавьте конфигурацию провайдера в `src/bioetl/composition/providers/registration.py`:

```python
from bioetl.composition.providers import ProviderConfig, ProviderRegistry
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer

def _create_pubmed_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create PubMed data source."""
    http_client = HttpClientFactory.create_for_provider("pubmed", settings, logger)
    adapter = PubMedAdapter(http_client, api_key=settings.pubmed_api_key)
    return _wrap_with_filter(adapter, filter_config, logger, pipeline_name)

# Регистрация в _register_providers():
ProviderRegistry.register(
    "pubmed",
    ProviderConfig(
        data_source_creator=_create_pubmed_data_source,
        transformers={"publication": PubMedPublicationTransformer},
        pipelines=["pubmed_publications"],
    ),
)
```

### 4.2 Создание трансформера

Создайте `src/bioetl/application/pipelines/pubmed/transformer.py`:

```python
from bioetl.application.core.base_transformer import BaseTransformer

class PubMedPublicationTransformer(BaseTransformer):
    """Трансформер для PubMed публикаций."""

    def _extract_business_data(self, record: dict) -> dict:
        """Извлечение бизнес-данных из Bronze записи."""
        return {
            "pmid": record.get("pmid"),
            "title": record.get("title"),
            "abstract": record.get("abstract"),
            # ... другие поля
        }
```

### 4.3 Регистрация пайплайна

Добавьте фабрику пайплайна в `src/bioetl/composition/factories/pipeline_factories.py`:

```python
from bioetl.application.pipelines.pubmed.publications import PubMedPublicationsPipeline
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer
from bioetl.infrastructure.schemas.gold import PubMedPublicationGoldSchema

pubmed_publications_factory = GenericPipelineFactory(
    pipeline_name="pubmed_publications",
    pipeline_class=PubMedPublicationsPipeline,
    provider="pubmed",
    transformer_class=PubMedPublicationTransformer,  # DI через GenericPipelineFactory
    gold_schema=PubMedPublicationGoldSchema,
)

def register_all_pipelines() -> None:
    # ...
    PipelineRegistry.register_factory(pubmed_publications_factory)
```

Теперь ваш пайплайн автоматически доступен через CLI по имени `pubmed_publications`.

## Чек-лист

- [ ] Адаптер источника реализован (`infrastructure/adapters/pubmed/`)
- [ ] Конфиг YAML создан (`configs/pipelines/pubmed/publication.yaml`)
- [ ] Трансформер реализован с наследованием от `BaseTransformer`
- [ ] Пайплайн реализован с наследованием от `BasePipeline`
- [ ] Провайдер зарегистрирован в `ProviderRegistry` (`registration.py`)
- [ ] Пайплайн зарегистрирован в `pipeline_factories.py` с `transformer_class`
- [ ] Unit-тесты с инъекцией трансформера
- [ ] Integration-тесты с VCR-кассетами
