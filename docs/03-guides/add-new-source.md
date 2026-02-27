# Руководство: Подключение нового провайдера

> **Терминология**: В BioETL термин **провайдер** (provider) обозначает внешний API-источник данных
> (ChEMBL, PubChem, UniProt и т.д.). См. [glossary.md](../00-project/glossary.md) для полного словаря терминов.

Этот документ описывает полный цикл подключения нового провайдера в BioETL.

В качестве примера мы рассмотрим подключение провайдера **PubMed** (сущность `Publication`).

## Общий алгоритм

1.  **Инфраструктура**: Создать адаптер (клиент API) для взаимодействия с внешним провайдером.
2.  **Конфигурация**: Определить настройки подключения (URL, ключи API) и конфиг пайплайна.
3.  **Приложение**: Реализовать класс пайплайна.
4.  **Сборка**: Создать фабрику и зарегистрировать провайдера в `ProviderRegistry`.

---

## Шаг 1: Создание адаптера (Infrastructure Layer)

Создайте клиент для API в `src/bioetl/infrastructure/adapters/<provider>/`.
Адаптер должен использовать `UnifiedHTTPClient` или специфичную библиотеку, обернутую в наш интерфейс.

**Пример:** `src/bioetl/infrastructure/adapters/pubmed/client.py`

```python
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

class PubMedAdapter:
    """Адаптер для PubMed API."""
    def --init--(self, http-client: UnifiedHTTPClient, api-key: str | None = None):
        self.http-client = http-client
        self.base-url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.api-key = api-key

    async def fetch-publications(self, query: str, retmax: int = 100):
        """Получение публикаций."""
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": retmax
        }
        if self.api-key:
            params["api-key"] = self.api-key

        # Используем UnifiedHTTPClient для запросов (с метриками и повторами)
        return await self.http-client.get(f"{self.base-url}/esearch.fcgi", params=params)
```

## Шаг 2: Конфигурация

### 2.1 Настройки приложения
Убедитесь, что настройки (например, API ключи) доступны через `src/bioetl/infrastructure/config.py`.

### 2.2 Конфиг пайплайна
Создайте `configs/entities/pubmed/publication.yaml`.

```yaml
pipeline:
    name: pubmed_publication
    provider: pubmed
    entity: publication

source:
    type: api
    load-strategy: incremental

sink:
    silver:
        path: "data/output/silver/pubmed/publication"
        format: delta
        primary-key: ["pmid"]
```

## Шаг 3: Реализация пайплайна (Application Layer)

Создайте `src/bioetl/application/pipelines/pubmed_publication.py`.

```python
from bioetl.application.core.base import BasePipeline
# ... (см. шаблоны и примеры для ChEMBL)

class PubMedPublicationPipeline(BasePipeline):
    # Реализация методов transform-bronze-to-silver и др.
    pass
```

## Шаг 4: Регистрация (Composition Layer)

В v5.2 сборка пайплайнов декларативна и централизована через `ProviderRegistry`.

### 4.1 Регистрация провайдера в ProviderRegistry

Добавьте конфигурацию провайдера в `src/bioetl/composition/providers/registration.py`:

```python
from bioetl.composition.providers import ProviderConfig, ProviderRegistry
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer

def -create-pubmed-data-source(
    settings: Settings,
    pipeline-config: PipelineYamlConfig,
    logger: LoggerPort,
    filter-config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline-name: str = "unknown",
) -> DataSourcePort:
    """Create PubMed data source."""
    http-client = HttpClientFactory.create-for-provider("pubmed", settings, logger)
    adapter = PubMedAdapter(http-client, api-key=settings.pubmed-api-key)
    return -wrap-with-filter(adapter, filter-config, logger, pipeline-name)

# Регистрация в -register-providers():
ProviderRegistry.register(
    "pubmed",
    ProviderConfig(
        data-source-creator=-create-pubmed-data-source,
        transformers={"publication": PubMedPublicationTransformer},
        pipelines=["pubmed_publication"],
    ),
)
```

### 4.2 Создание трансформера

Создайте `src/bioetl/application/pipelines/pubmed/transformer.py`:

```python
from bioetl.application.core.base-transformer import BaseTransformer

class PubMedPublicationTransformer(BaseTransformer):
    """Трансформер для PubMed публикаций."""

    def -extract-business-data(self, record: dict) -> dict:
        """Извлечение бизнес-данных из Bronze записи."""
        return {
            "pmid": record.get("pmid"),
            "title": record.get("title"),
            "abstract": record.get("abstract"),
            # ... другие поля
        }
```

### 4.3 Регистрация пайплайна

Добавьте фабрику пайплайна в `src/bioetl/composition/factories/pipeline-factories.py`:

```python
from bioetl.application.pipelines.pubmed.publication import PubMedPublicationPipeline
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer
from bioetl.infrastructure.schemas.gold import PubMedPublicationGoldSchema

pubmed_publication-factory = GenericPipelineFactory(
    pipeline-name="pubmed_publication",
    pipeline-class=PubMedPublicationPipeline,
    provider="pubmed",
    transformer-class=PubMedPublicationTransformer,  # DI через GenericPipelineFactory
    gold-schema=PubMedPublicationGoldSchema,
)

def register-all-pipelines() -> None:
    # ...
    PipelineRegistry.register-factory(pubmed_publication-factory)
```

Теперь ваш пайплайн автоматически доступен через CLI по имени `pubmed_publication`.

## Чек-лист

- [ ] Адаптер провайдера реализован (`infrastructure/adapters/pubmed/`)
- [ ] Конфиг YAML создан (`configs/entities/pubmed/publication.yaml`)
- [ ] Трансформер реализован с наследованием от `BaseTransformer`
- [ ] Пайплайн реализован с наследованием от `BasePipeline`
- [ ] Провайдер зарегистрирован в `ProviderRegistry` (`registration.py`)
- [ ] Пайплайн зарегистрирован в `pipeline-factories.py` с `transformer-class`
- [ ] Unit-тесты с инъекцией трансформера
- [ ] Integration-тесты с VCR-кассетами
