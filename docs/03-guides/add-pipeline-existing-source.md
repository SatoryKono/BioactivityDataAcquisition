# Руководство: Добавление пайплайна для существующего провайдера

> **Терминология**: В BioETL термин **провайдер** (provider) обозначает внешний API-источник данных.
> См. [glossary.md](../glossary.md) для полного словаря терминов.

Этот документ описывает процесс добавления нового ETL-пайплайна для провайдера, который уже интегрирован в систему (например, добавление новой сущности `Target` для провайдера `ChEMBL`).

В качестве примера мы рассмотрим добавление сущности `Target` в провайдер `chembl`.

## Общий алгоритм

1.  **Анализ данных**: Изучить структуру данных новой сущности в API провайдера.
2.  **Конфигурация**: Создать YAML-файл конфигурации.
3.  **Реализация пайплайна**: Создать класс пайплайна в слое Application.
4.  **Регистрация**: Добавить пайплайн в `bootstrap.py`.

---

## Шаг 1: Конфигурация

Создайте файл конфигурации в директории `configs/pipelines/<provider>/<entity>.yaml`.

**Пример:** `configs/pipelines/chembl/target.yaml`

```yaml
# Inherits defaults from ../_base.yaml
pipeline_name: chembl_target
provider: chembl
entity_type: target
version: "1.2.0"
description: "Extract biological targets from ChEMBL API"

primary_keys: ["target_chembl_id"]
silver_table: "chembl_target"
gold_table: "chembl_target"

source_file: ../../sources/chembl.yaml

# DQ rules loaded from hierarchical config files (ADR-027):
#   1. configs/dq/_defaults.yaml
#   2. configs/dq/providers/chembl.yaml
#   3. configs/dq/entities/chembl/target.yaml
dq_config_file: ../../dq/entities/chembl/target.yaml

# Paths auto-computed by convention (ADR-029),
# override only when different from default
sink:
  bronze:
    path: "data/output/bronze/chembl/target"
  silver:
    path: "data/output/silver/chembl/target"
    primary_key: ["target_chembl_id"]
    partition_by: ["target_type"]
  gold:
    path: "data/output/gold/chembl/target"
```

## Шаг 2: Реализация пайплайна (Application Layer)

Создайте новый файл в `src/bioetl/application/pipelines/<provider>/`. Имя файла должно отражать сущность (например, `target.py` внутри `chembl/`).

Класс должен наследовать `BasePipeline` и реализовывать методы трансформации.

**Пример:** `src/bioetl/application/pipelines/chembl/target.py`

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
    silver_table="chembl_target",
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

## Шаг 3: Регистрация (Composition Layer)

В v5.1 вам больше не нужно вручную менять `bootstrap.py`. Достаточно зарегистрировать новый экземпляр `GenericPipelineFactory`.

Откройте `src/bioetl/composition/factories/pipeline_factories.py` и добавьте определение:

```python
from bioetl.application.pipelines.chembl.target import ChEMBLTargetPipeline
from bioetl.infrastructure.schemas.silver import CHEMBL_TARGET_SCHEMA

# Определение фабрики
chembl_target_factory = GenericPipelineFactory(
    pipeline_name="chembl_target",
    pipeline_class=ChEMBLTargetPipeline,
    provider="chembl",
    silver_schema=CHEMBL_TARGET_SCHEMA,
)

def register_all_pipelines() -> None:
    # ...
    PipelineRegistry.register_factory(chembl_target_factory)
```

Теперь пайплайн доступен для запуска:
```bash
python -m bioetl run --pipeline chembl_target
```

## Чек-лист

- [ ] Конфиг YAML создан.
- [ ] Класс пайплайна реализован (Silver трансформация).
- [ ] Схема Silver (PyArrow) определена в `infrastructure/schemas/silver.py`.
- [ ] Пайплайн зарегистрирован в `pipeline_factories.py`.
- [ ] Тесты добавлены.
