# Руководство: Добавление пайплайна для существующего провайдера

> **Терминология**: В BioETL термин **провайдер** (provider) обозначает внешний API-источник данных.
> См. [glossary.md](../00-project/glossary.md) для полного словаря терминов.

Этот документ описывает процесс добавления нового ETL-пайплайна для провайдера, который уже интегрирован в систему (например, добавление новой сущности `Target` для провайдера `ChEMBL`).

В качестве примера мы рассмотрим добавление сущности `Target` в провайдер `chembl`.

## Общий алгоритм

1. **Анализ данных**: Изучить структуру данных новой сущности в API провайдера.
1. **Конфигурация**: Создать YAML-файл конфигурации.
1. **Реализация пайплайна**: Создать класс пайплайна в слое Application.
1. **Регистрация**: Добавить пайплайн в `bootstrap.py`.

----------------------------------------------------------------------

## Шаг 1: Конфигурация

Создайте файл конфигурации в директории `configs/pipelines/<provider>/<entity>.yaml`.

**Пример:** `configs/pipelines/chembl/target.yaml`

```yaml
# Inherits defaults from ../-base.yaml
pipeline-name: chembl-target
provider: chembl
entity-type: target
version: "1.2.0"
description: "Extract biological targets from ChEMBL API"

business-primary-keys: ["target-chembl-id"]
silver-table: "chembl-target"
gold-table: "chembl-target"

source-file: ../../sources/chembl.yaml

# DQ rules loaded from hierarchical config files (ADR-027):
#   1. configs/quality/-defaults.yaml
#   2. configs/quality/providers/chembl.yaml
#   3. configs/quality/entities/chembl/target.yaml
dq-config-file: ../../quality/entities/chembl/target.yaml

# Paths auto-computed by convention (ADR-029),
# override only when different from default
sink:
  bronze:
    path: "data/output/bronze/chembl/target"
  silver:
    path: "data/output/silver/chembl/target"
    primary-key: ["target-chembl-id"]
    partition-by: ["target-type"]
  gold:
    path: "data/output/gold/chembl/target"
```

## Шаг 2: Реализация трансформера (Domain/Application Boundary)

Создайте отдельный трансформер в `src/bioetl/application/pipelines/<provider>/` (или в выделенном модуле трансформаций, если он уже используется в проекте).
Логика Bronze -> Silver должна находиться в классе трансформера, а не в классе пайплайна.

Класс должен наследовать `BaseChemblTransformer` (или `BaseTransformer`) и реализовывать `-transform-impl`.

**Пример:** `src/bioetl/application/pipelines/chembl/target-transformer.py`

```python
from --future-- import annotations

from typing import Any

from bioetl.application.pipelines.chembl.base-transformer import BaseChemblTransformer
from bioetl.domain.transformations import generate-content-hash, generate-entity-id


class ChEMBLTargetTransformer(BaseChemblTransformer):
    """Bronze -> Silver трансформация для сущности ChEMBL Target."""

    def -transform-impl(self, record: dict[str, Any]) -> dict[str, Any] | None:
        if not record.get("target-chembl-id"):
            return None

        target-id = str(record["target-chembl-id"])

        entity-id = generate-entity-id(
            record={"target-chembl-id": target-id},
            provider=self.provider,
            id-field="target-chembl-id",
        )

        return {
            "entity-id": entity-id,
            "target-chembl-id": target-id,
            "pref-name": record.get("pref-name"),
            "target-type": record.get("target-type"),
            "organism": record.get("organism"),
            "content-hash": generate-content-hash(record, self.provider),
        }
```

## Шаг 3: Регистрация (Composition Layer)

В v5.1 вам больше не нужно вручную менять `bootstrap.py`. Достаточно зарегистрировать новый экземпляр `GenericPipelineFactory`.

Откройте `src/bioetl/composition/factories/pipeline-factories.py` и добавьте определение:

```python
from bioetl.application.pipelines.chembl.target-transformer import (
    ChEMBLTargetTransformer,
)
from bioetl.application.pipelines.generic import GenericPipeline
from bioetl.infrastructure.schemas.silver import CHEMBL-TARGET-SCHEMA

# Определение фабрики
chembl-target-factory = GenericPipelineFactory(
    pipeline-name="chembl-target",
    pipeline-class=GenericPipeline,
    provider="chembl",
    silver-schema=CHEMBL-TARGET-SCHEMA,
    transformer-class=ChEMBLTargetTransformer,
)


def register-all-pipelines() -> None:
    # ...
    PipelineRegistry.register-factory(chembl-target-factory)
```

Теперь пайплайн доступен для запуска:

```bash
python -m bioetl run --pipeline chembl-target
```

## Чек-лист

- [ ] Конфиг YAML создан.
- [ ] Класс трансформера реализован (Silver трансформация).
- [ ] Схема Silver (PyArrow) определена в `infrastructure/schemas/silver.py`.
- [ ] Пайплайн зарегистрирован в `pipeline-factories.py`.
- [ ] Тесты добавлены.
