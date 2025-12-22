# Руководство: Добавление нового провайдера данных
*Версия 2.0 (Детальное руководство) | Синхронизировано с RULES.md v5.0*

Это руководство проведет вас через весь процесс добавления нового источника данных (провайдера) в BioETL. В качестве примера мы добавим гипотетический провайдер `OpenTargets`.

**Цель:** Создать новый пайплайн `open_targets_associations`, который извлекает данные из API OpenTargets, обрабатывает их и сохраняет в Data Lake.

---

## Обзор процесса

Добавление нового провайдера включает в себя создание нескольких компонентов в разных слоях архитектуры:

1.  **Адаптер (Infrastructure):** Код, который напрямую взаимодействует с внешним API.
2.  **Конфигурация (Configs):** YAML-файлы, определяющие параметры пайплайна.
3.  **Пайплайн (Application):** Класс, который оркестрирует процесс ETL (Extract, Transform, Load).
4.  **Фабрика (Composition):** Код, который "собирает" пайплайн и его зависимости.
5.  **Тесты (Tests):** Интеграционные и модульные тесты для обеспечения корректности.

---

### Шаг 1: Создание Адаптера (Adapter)

Адаптер отвечает за всю логику взаимодействия с внешним API: HTTP-запросы, обработка ответов, пагинация и Rate Limiting.

**1.1. Создайте структуру файлов:**

Создайте новый файл для вашего адаптера.

```bash
touch src/bioetl/infrastructure/adapters/open_targets_client.py
```

**1.2. Реализуйте Адаптер:**

Откройте `open_targets_client.py` и создайте класс адаптера. Он должен инкапсулировать логику для `fetch` (извлечение данных) и `health_check`.

```python
# src/bioetl/infrastructure/adapters/open_targets_client.py
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, AsyncIterator

from bioetl.domain.exceptions import ApiError
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

if TYPE_CHECKING:
    from bioetl.domain.types import Watermark

OPENTARGETS_API_BASE = "https://api.opentargets.io/v3/"

@dataclass
class OpenTargetsAdapter:
    """Адаптер для извлечения данных из OpenTargets."""
    http_client: UnifiedHTTPClient
    batch_size: int = 100

    provider_name: str = "open_targets"

    async def fetch(
        self,
        entity_type: str, # например, "associations"
        watermark: Watermark | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Извлекает записи из OpenTargets."""
        # Здесь будет логика пагинации по API OpenTargets
        # Например, с использованием параметра 'from'
        offset = 0
        total_fetched = 0
        
        while True:
            params = {"size": self.batch_size, "from": offset}
            url = f"{OPENTARGETS_API_BASE}/platform/public/association/filter"
            
            try:
                response = await self.http_client.post(url, json={"target": ["CHEMBL123"]}) # Пример POST-запроса
                records = response.json().get("data", [])

                if not records:
                    break

                for record in records:
                    yield record
                    total_fetched += 1
                    if limit and total_fetched >= limit:
                        return

                offset += len(records)

            except Exception as e:
                raise ApiError(f"Ошибка API OpenTargets: {e}") from e

    async def health_check(self) -> HealthStatus:
        """Проверяет доступность API OpenTargets."""
        try:
            # OpenTargets не имеет специального health-endpoint,
            # поэтому делаем легкий запрос для проверки.
            response = await self.http_client.get(f"{OPENTARGETS_API_BASE}/platform/public/utils/stats")
            return HealthStatus.HEALTHY if response.status_code == 200 else HealthStatus.UNHEALTHY
        except Exception:
            return HealthStatus.UNHEALTHY

    async def aclose(self) -> None:
        pass
```

---

### Шаг 2: Создание Конфигурации Пайплайна

Конфигурация определяет поведение пайплайна без изменения кода.

**2.1. Создайте файл конфигурации:**

```bash
mkdir -p configs/pipelines/open_targets
touch configs/pipelines/open_targets/associations.yaml
```

**2.2. Заполните конфигурацию:**

Откройте `associations.yaml` и определите параметры.

```yaml
# configs/pipelines/open_targets/associations.yaml
pipeline_name: open_targets_associations
provider: open_targets
entity_type: associations
version: "1.0.0"
description: "Извлекает 'target-disease associations' из OpenTargets."

primary_keys: ["id"]
silver_table: "open_targets_associations"

# Настройки для извлечения данных
source:
  load_strategy: full # OpenTargets не поддерживает инкрементальную загрузку по дате
  watermark_field: id # Используем ID для возобновления в случае сбоя

# Настройки для сохранения данных
sink:
  bronze:
    path: "data/output/bronze"
    format: jsonl
  silver:
    path: "data/output/silver"
    format: delta
    mode: merge
    primary_key: ["id"]
  gold:
    enabled: false # Для этого примера золотой слой не создаем
```

---

### Шаг 3: Создание Класса Пайплайна (Application)

Этот класс содержит бизнес-логику трансформации данных.

**3.1. Создайте файл пайплайна:**

```bash
mkdir -p src/bioetl/application/pipelines/open_targets
touch src/bioetl/application/pipelines/open_targets/__init__.py
touch src/bioetl/application/pipelines/open_targets/associations.py
```

**3.2. Реализуйте логику трансформации:**

Откройте `associations.py` и напишите код для преобразования сырых записей (Bronze) в очищенный формат (Silver).

```python
# src/bioetl/application/pipelines/open_targets/associations.py
from __future__ import annotations
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base import BasePipeline
from bioetl.domain.entities import Association # Предполагаем, что такая сущность есть
from bioetl.domain.transformations import generate_content_hash, generate_entity_id

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord

class OpenTargetsAssociationsPipeline(BasePipeline):
    """Пайплайн для данных 'associations' из OpenTargets."""

    async def transform_bronze_to_silver(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Трансформирует сырую запись в формат Silver."""
        association_id = record.get("id")
        if not association_id:
            return None

        # 1. Подготовка данных
        business_data = {
            "association_id": str(association_id),
            "target_chembl_id": record.get("target", {}).get("id"),
            "disease_id": record.get("disease", {}).get("id"),
            "score": record.get("association_score", {}).get("overall"),
        }

        # 2. Создание доменной сущности для валидации и бизнес-логики
        try:
            entity_id = generate_entity_id(
                record={"association_id": str(association_id)},
                provider=self.provider,
                id_field="association_id",
            )
            content_hash = generate_content_hash(business_data, self.provider)

            # entity = Association(entity_id=entity_id, content_hash=content_hash, **business_data)
        except ValueError as e:
            self.logger.warning("Ошибка валидации", error=str(e), id=association_id)
            return None

        # 3. Преобразование в SilverRecord (словарь для записи)
        silver_record: dict[str, Any] = {
            "entity_id": entity_id,
            "content_hash": content_hash,
            "association_id": business_data["association_id"],
            "target_chembl_id": business_data["target_chembl_id"],
            "disease_id": business_data["disease_id"],
            "association_score": business_data["score"],
            "_run_id": str(context.run_id),
            "_run_type": str(context.run_type.value),
            "_ingestion_ts": context.run_start_time.isoformat(),
        }

        return cast(SilverRecord, silver_record)
```

---

### Шаг 4: Создание Фабрики (Composition)

Фабрика — это клей, который соединяет конфигурацию, адаптер и пайплайн вместе.

**4.1. Создайте файл фабрики:**

```bash
touch src/bioetl/composition/factories/open_targets_associations.py
```

**4.2. Реализуйте фабрику и зарегистрируйте пайплайн:**

Фабрика должна уметь создавать экземпляр пайплайна и его зависимостей (включая наш новый адаптер). В конце файла пайплайн регистрируется в `PipelineRegistry`, чтобы CLI мог его найти.

```python
# src/bioetl/composition/factories/open_targets_associations.py
from __future__ import annotations
from typing import TYPE_CHECKING

from bioetl.application.pipelines.open_targets.associations import OpenTargetsAssociationsPipeline
from bioetl.application.registry import PipelineRegistry
from bioetl.infrastructure.adapters.open_targets_client import OpenTargetsAdapter
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.composition.factories.base_pipeline_factory import BasePipelineFactory
from bioetl.infrastructure.schemas.silver import SOME_GENERIC_SCHEMA # Замените на реальную схему

if TYPE_CHECKING:
    from bioetl.domain.ports import DataSourcePort
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class OpenTargetsAssociationsPipelineFactory(BasePipelineFactory[OpenTargetsAssociationsPipeline]):
    """Фабрика для создания пайплайна OpenTargets Associations."""

    pipeline_name = "open_targets_associations"
    pipeline_class = OpenTargetsAssociationsPipeline
    silver_schema = SOME_GENERIC_SCHEMA # Укажите Pandera схему для Silver

    @classmethod
    def create_data_source(
        cls,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
    ) -> DataSourcePort:
        """Создает источник данных OpenTargets."""
        http_client = UnifiedHTTPClient(
            TokenBucket(rate=5.0, capacity=10), # Лимиты для OpenTargets
            CircuitBreaker(provider="open_targets")
        )
        return OpenTargetsAdapter(http_client=http_client)

# Регистрация делает пайплайн доступным для запуска через CLI
# Создаем экземпляр фабрики и регистрируем
factory = OpenTargetsAssociationsPipelineFactory()
PipelineRegistry.register_factory(factory)
```

---

### Шаг 5: Написание Тестов

Тестирование — обязательный шаг. Для адаптера нужен интеграционный тест с `VCR.py`.

**5.1. Создайте файл теста:**

```bash
mkdir -p tests/integration/adapters
touch tests/integration/adapters/test_open_targets.py
```

**5.2. Напишите интеграционный тест:**

Этот тест делает реальный запрос к API и записывает его в "кассету" (`cassettes/test_open_targets.yaml`), чтобы последующие запуски не требовали доступа к сети.

```python
# tests/integration/adapters/test_open_targets.py
import pytest
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.adapters.open_targets_client import OpenTargetsAdapter

@pytest.mark.integration
@pytest.mark.vcr
async def test_fetch_associations():
    """Тестирует извлечение данных из OpenTargets с записью VCR кассеты."""
    http_client = UnifiedHTTPClient(
        TokenBucket(rate=5.0, capacity=10),
        CircuitBreaker(provider="open_targets")
    )
    
    async with http_client:
        adapter = OpenTargetsAdapter(http_client=http_client, batch_size=2)
        
        records = []
        async for record in adapter.fetch("associations", limit=3):
            records.append(record)
            
        assert len(records) == 3
        assert "id" in records[0]
        assert "association_score" in records[0]

@pytest.mark.integration
@pytest.mark.vcr
async def test_health_check():
    """Тестирует health check для OpenTargets."""
    http_client = UnifiedHTTPClient(
        TokenBucket(rate=5.0, capacity=10),
        CircuitBreaker(provider="open_targets")
    )
    async with http_client:
        adapter = OpenTargetsAdapter(http_client=http_client)
        status = await adapter.health_check()
        assert status == HealthStatus.HEALTHY
```

**5.3. Запишите VCR-кассету:**

Выполните команду. `VCR.py` перехватит HTTP-запрос и сохранит ответ.

```bash
# Для записи новой "кассеты"
pytest tests/integration/adapters/test_open_targets.py --vcr-record=new_episodes
```

---

### Шаг 6: Запуск Нового Пайплайна

После того как все компоненты созданы и протестированы, вы можете запустить свой новый пайплайн.

```bash
# Убедитесь, что вы в активированном окружении (.venv)
# Запускаем пайплайн с лимитом в 100 записей
python -m bioetl.main run --pipeline open_targets_associations --limit 100
```

Эта команда найдет ваш пайплайн через `PipelineRegistry`, создаст его с помощью вашей фабрики и запустит процесс ETL.

Поздравляем! Вы успешно расширили BioETL, добавив новый источник данных, строго следуя архитектурным принципам проекта.
