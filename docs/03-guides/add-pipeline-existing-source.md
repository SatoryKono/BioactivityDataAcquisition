# Руководство: Добавление пайплайна для существующего источника

Этот документ описывает процесс добавления нового ETL-пайплайна для источника, который уже интегрирован в систему (например, добавление новой сущности `Target` для источника `ChEMBL`).

В качестве примера мы рассмотрим добавление сущности `Target` в провайдер `chembl`.

## Общий алгоритм

1.  **Анализ данных**: Изучить структуру данных новой сущности в API источника.
2.  **Конфигурация**: Создать YAML-файл конфигурации.
3.  **Реализация пайплайна**: Создать класс пайплайна в слое Application.
4.  **Регистрация**: Добавить пайплайн в `bootstrap.py`.

---

## Шаг 1: Конфигурация

Создайте файл конфигурации в директории `configs/pipelines/<provider>/<entity>.yaml`.

**Пример:** `configs/pipelines/chembl/target.yaml`

```yaml
pipeline:
    name: chembl_target
    provider: chembl
    entity: target

source:
    type: api
    load_strategy: incremental
    watermark_field: target_chembl_id

transform:
    version: "1.0.0"
    steps:
        - normalize_fields
        - generate_content_hash

sink:
    bronze:
        path: "s3://bioetl-bronze/chembl/target/"
        format: json
    silver:
        path: "s3://bioetl-silver/chembl/target/"
        format: delta
        mode: merge
        primary_key: ["target_chembl_id"]
```

## Шаг 2: Реализация пайплайна (Application Layer)

Создайте новый файл в `src/bioetl/application/pipelines/`. Имя файла должно отражать провайдера и сущность (например, `chembl_target.py`).

Класс должен наследовать `BasePipeline` и реализовывать методы трансформации.

**Пример:** `src/bioetl/application/pipelines/chembl_target.py`

```python
from typing import Any
from bioetl.application.core.base import BasePipeline
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.domain.config import PipelineConfig, RuntimeConfig  # Consolidated in domain
from bioetl.domain.context import PipelineContext
from bioetl.domain.transformations import generate_content_hash, generate_entity_id

# Дефолтная конфигурация (можно переопределить через YAML)
CHEMBL_TARGET_CONFIG = PipelineConfig(
    pipeline_name="chembl_target",
    provider="chembl",
    entity_type="target",
    primary_keys=["target_chembl_id"],
    silver_table="chembl.target",
    checkpoint_interval=1000,
)

class ChEMBLTargetPipeline(BasePipeline):
    @classmethod
    def create(cls, runtime: RuntimeConfig, services: PipelineServices, config: PipelineConfig | None = None):
        return cls(config or CHEMBL_TARGET_CONFIG, runtime, services)

    async def transform_bronze_to_silver(self, context: PipelineContext, record: dict[str, Any]) -> dict[str, Any] | None:
        """Трансформация сырых данных в Silver слой."""
        if not record.get("target_chembl_id"):
            return None

        target_id = str(record["target_chembl_id"])

        # Генерация стабильного ID
        entity_id = generate_entity_id(
            record={"target_chembl_id": target_id},
            provider=self.provider,
            id_field="target_chembl_id"
        )

        normalized = {
            "entity_id": entity_id,
            "target_chembl_id": target_id,
            "pref_name": record.get("pref_name"),
            "target_type": record.get("target_type"),
            "organism": record.get("organism"),
            "content_hash": generate_content_hash(record, self.provider)
        }

        return normalized

    def should_write_gold(self, context: PipelineContext, record: dict[str, Any]) -> bool:
        # Логика фильтрации для Gold слоя (если требуется)
        return True
```

## Шаг 3: Регистрация в Bootstrap (Composition Root)

Откройте `src/bioetl/composition/bootstrap.py` и зарегистрируйте новый пайплайн.

1.  **Импортируйте** новый класс пайплайна и его конфиг.
2.  **Создайте фабрику** в `src/bioetl/composition/factories/` (или обновите существующую).
3.  **Добавьте условие** в функцию `bootstrap_pipeline`.

**Пример фабрики в `src/bioetl/composition/factories/chembl_target.py`:**

```python
from bioetl.application.pipelines.chembl_target import ChEMBLTargetPipeline, CHEMBL_TARGET_CONFIG
from bioetl.composition.factories.chembl_activity import ChEMBLActivityPipelineFactory

class ChEMBLTargetPipelineFactory:
    """Фабрика для Target пайплайна (переиспользует сервисы ChEMBL)."""
    @staticmethod
    def create_with_services(runtime, settings, logger):
        # Переиспользование логики создания сервисов (http client, storage и т.д.)
        services = ChEMBLActivityPipelineFactory.build_services(settings, logger)

        return ChEMBLTargetPipeline.create(
            runtime=runtime,
            services=services,
            config=CHEMBL_TARGET_CONFIG
        )
```

**Пример изменений в `src/bioetl/composition/bootstrap.py`:**

```python
from bioetl.composition.factories.chembl_target import ChEMBLTargetPipelineFactory

def bootstrap_pipeline(pipeline_name: str, ...):
    # ...
    if pipeline_name == "chembl_activity":
        # ... (существующий код)
    elif pipeline_name == "chembl_target":
        pipeline = ChEMBLTargetPipelineFactory.create_with_services(
            runtime=runtime_config,
            settings=settings,
            logger=logger,
        )
    # ...
```

## Чек-лист

- [ ] Конфиг YAML создан.
- [ ] Класс пайплайна реализован (Silver трансформация).
- [ ] Пайплайн зарегистрирован в `bootstrap.py`.
- [ ] Тесты добавлены (unit тесты трансформации).
