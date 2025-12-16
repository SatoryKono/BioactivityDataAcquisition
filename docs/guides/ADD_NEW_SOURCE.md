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

## Шаг 4: Фабрика и Bootstrap (Composition Root)

Создайте фабрику, которая соберет все зависимости для нового источника. Рекомендуется создавать отдельный файл в `src/bioetl/infrastructure/factories/`.

**Пример:** `src/bioetl/infrastructure/factories/pubmed.py`

```python
from bioetl.infrastructure.config import Settings
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.infrastructure.adapters.pubmed.client import PubMedAdapter
# ... другие импорты

class PubMedPipelineFactory:
    @staticmethod
    def build_services(settings: Settings, logger, **kwargs) -> PipelineServices:
        # 1. Создаем HTTP клиент
        http_client = UnifiedHTTPClient(...) # с RateLimiter для PubMed

        # 2. Создаем специфичный адаптер
        data_source = PubMedAdapter(http_client, api_key=settings.pubmed_api_key)

        # 3. Собираем стандартные сервисы (storage, lock, checkpoint...)
        # (код аналогичен другим фабрикам)

        return PipelineServices(
            data_source=data_source,
            # ...
        )
```

### Регистрация в `bootstrap.py`

```python
from bioetl.infrastructure.factories.pubmed import PubMedPipelineFactory
from bioetl.application.pipelines.pubmed_publication import PubMedPublicationPipeline

# ...

def bootstrap_pipeline(pipeline_name: str, ...):
    # ...
    elif pipeline_name == "pubmed_publication":
        services = PubMedPipelineFactory.build_services(settings, logger)
        pipeline = PubMedPublicationPipeline.create(runtime, services)
    # ...
```

## Чек-лист

- [ ] Адаптер источника реализован.
- [ ] Конфиг YAML создан.
- [ ] Пайплайн реализован.
- [ ] Фабрика создана и подключена в `bootstrap.py`.
