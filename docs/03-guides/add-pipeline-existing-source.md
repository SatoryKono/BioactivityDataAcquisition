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
#   1. configs/quality/_defaults.yaml
#   2. configs/quality/providers/chembl.yaml
#   3. configs/quality/entities/chembl/target.yaml
dq_config_file: ../../quality/entities/chembl/target.yaml

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

## Шаг 2: Реализация трансформера (Domain/Application Boundary)

Создайте отдельный трансформер в `src/bioetl/application/pipelines/<provider>/` (или в выделенном модуле трансформаций, если он уже используется в проекте).
Логика Bronze -> Silver должна находиться в классе трансформера, а не в классе пайплайна.

Класс должен наследовать `BaseChemblTransformer` (или `BaseTransformer`) и реализовывать `_transform_impl`.

**Пример:** `src/bioetl/application/pipelines/chembl/target_transformer.py`

```python
from __future__ import annotations

from typing import Any

from bioetl.application.pipelines.chembl.base_transformer import BaseChemblTransformer
from bioetl.domain.transformations import generate_content_hash, generate_entity_id


class ChEMBLTargetTransformer(BaseChemblTransformer):
    """Bronze -> Silver трансформация для сущности ChEMBL Target."""

    def _transform_impl(self, record: dict[str, Any]) -> dict[str, Any] | None:
        if not record.get("target_chembl_id"):
            return None

        target_id = str(record["target_chembl_id"])

        entity_id = generate_entity_id(
            record={"target_chembl_id": target_id},
            provider=self.provider,
            id_field="target_chembl_id",
        )

        return {
            "entity_id": entity_id,
            "target_chembl_id": target_id,
            "pref_name": record.get("pref_name"),
            "target_type": record.get("target_type"),
            "organism": record.get("organism"),
            "content_hash": generate_content_hash(record, self.provider),
        }
```

## Шаг 3: Регистрация (Composition Layer)

В v5.1 вам больше не нужно вручную менять `bootstrap.py`. Достаточно зарегистрировать новый экземпляр `GenericPipelineFactory`.

Откройте `src/bioetl/composition/factories/pipeline_factories.py` и добавьте определение:

```python
from bioetl.application.pipelines.chembl.target_transformer import ChEMBLTargetTransformer
from bioetl.application.pipelines.generic import GenericPipeline
from bioetl.infrastructure.schemas.silver import CHEMBL_TARGET_SCHEMA

# Определение фабрики
chembl_target_factory = GenericPipelineFactory(
    pipeline_name="chembl_target",
    pipeline_class=GenericPipeline,
    provider="chembl",
    silver_schema=CHEMBL_TARGET_SCHEMA,
    transformer_class=ChEMBLTargetTransformer,
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
- [ ] Класс трансформера реализован (Silver трансформация).
- [ ] Схема Silver (PyArrow) определена в `infrastructure/schemas/silver.py`.
- [ ] Пайплайн зарегистрирован в `pipeline_factories.py`.
- [ ] Тесты добавлены.
