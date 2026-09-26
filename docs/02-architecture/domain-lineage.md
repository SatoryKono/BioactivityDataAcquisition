# Domain Lineage Implementation

## Обзор

Domain Lineage Implementation обеспечивает queryable provenance tracking для данных, проходящих через пайплайны BioETL. Эта реализация предоставляет immutable graph fragments для отслеживания происхождения данных от source systems до gold layer.

**Связанные ADR:** (проверить наличие ADR для lineage)

## Архитектура

### Основные компоненты

```
src/bioetl/domain/lineage/
├── __init__.py              # Публичный API
├── models.py                # Public lineage model re-export
├── graph.py                 # Lineage edges and fragments
├── refs.py                  # Lineage node references
├── metadata_bundle.py       # Metadata lineage bundle
└── _shared.py               # Shared utilities
```

## Ключевые сущности

### 1. LineageNodeRef

**Файл:** `refs.py`

**Назначение:** Каноническая ссылка на один узел lineage graph.

**Поля:**
- `node_type: LineageNodeType` - тип узла
- `node_id: str` - идентификатор узла
- `label: str | None` - метка узла
- `attributes: dict[str, object]` - атрибуты узла

**Методы:**
- `to_dict()` - сериализация в JSON
- `from_dict()` - десериализация из JSON

**Invariants:**
- `attributes` нормализуются для deterministic storage

### 2. LineageNodeType

**Файл:** `refs.py`

**Назначение:** Канонические типы узлов для lineage graph fragments.

**Типы:**
- `SOURCE_SYSTEM` - внешняя source system
- `SOURCE_REQUEST` - запрос к source system
- `BRONZE_BATCH` - bronze batch
- `DATASET` - логический dataset (bronze/silver/gold)
- `TRANSFORM` - transform stage
- `SCHEMA` - schema/contract
- `RUN` - pipeline run
- `MANIFEST` - run manifest
- `CONSUMPTION` - потребление данных downstream

### 3. DatasetRef

**Файл:** `refs.py`

**Назначение:** Логическая ссылка на dataset для Bronze/Silver/Gold lineage.

**Поля:**
- `layer: Layer | str` - слой (bronze/silver/gold)
- `logical_name: str` - логическое имя dataset
- `version: int | str | None` - версия dataset
- `provider: str | None` - провайдер данных
- `entity: str | None` - сущность данных
- `path: str | None` - путь к dataset
- `manifest_id: str | None` - ID manifest
- `run_id: str | None` - ID run

**Свойства:**
- `node_id` - канонический идентификатор узла dataset (формат: `{layer}:{logical_name}@{version}`)

**Методы:**
- `to_node_ref()` - конвертация в generic lineage node
- `to_dict()` - сериализация в JSON
- `from_dict()` - десериализация из JSON

**Invariants:**
- `layer` нормализуется к stable string value

### 4. TransformRef

**Файл:** `refs.py`

**Назначение:** Ссылка на transform stage в lineage graph.

**Поля:**
- `name: str` - имя transform
- `version: str | None` - версия transform
- `step_index: int | None` - индекс шага
- `pipeline_name: str | None` - имя пайплайна
- `code_ref: str | None` - ссылка на код

**Свойства:**
- `node_id` - канонический идентификатор узла transform (формат: `transform:{pipeline_name}:{name}:{version}:{step_index}`)

**Методы:**
- `to_node_ref()` - конвертация в generic lineage node
- `to_dict()` - сериализация в JSON
- `from_dict()` - десериализация из JSON

### 5. SchemaRef

**Файл:** `refs.py`

**Назначение:** Ссылка на schema/contract version в lineage.

**Поля:**
- `contract_path: str` - путь к контракту
- `version: str | None` - версия контракта
- `validation_mode: str | None` - режим валидации
- `dataset_name: str | None` - имя dataset

**Свойства:**
- `node_id` - канонический идентификатор узла schema (формат: `schema:{contract_path}:{version}`)

**Методы:**
- `to_node_ref()` - конвертация в generic lineage node
- `to_dict()` - сериализация в JSON
- `from_dict()` - десериализация из JSON

### 6. LineageEdge

**Файл:** `graph.py`

**Назначение:** Направленная каноническая связь между двумя узлами lineage.

**Поля:**
- `edge_type: LineageEdgeType` - тип связи
- `source: LineageNodeRef` - исходный узел
- `target: LineageNodeRef` - целевой узел
- `run_id: str | None` - ID run
- `manifest_id: str | None` - ID manifest
- `created_at: datetime | None` - время создания
- `attributes: dict[str, object]` - атрибуты связи

**Методы:**
- `to_dict()` - сериализация в JSON
- `from_dict()` - десериализация из JSON

**Invariants:**
- `attributes` нормализуются для deterministic storage

### 7. LineageEdgeType

**Файл:** `graph.py`

**Назначение:** Каноническая семантика lineage edges.

**Типы:**
- `DERIVED_FROM` - данные получены из другого источника
- `PRODUCED_BY` - данные произведены transform/run
- `USED_SCHEMA` - использован schema/contract
- `EXECUTED_IN` - выполнен в контексте run
- `CONSUMED_BY` - потреблены downstream
- `EXPLAINS` - объясняет другой artifact

### 8. LineageGraphFragment

**Файл:** `graph.py`

**Назначение:** Один appendable lineage graph fragment, привязанный к run/manifest.

**Поля:**
- `fragment_id: str` - идентификатор fragment
- `nodes: tuple[LineageNodeRef, ...]` - узлы fragment
- `edges: tuple[LineageEdge, ...]` - связи fragment
- `run_id: str | None` - ID run
- `manifest_id: str | None` - ID manifest
- `created_at: datetime | None` - время создания
- `stored_fragment_id: str | None` - ID хранимого fragment (исключается из сравнения)

**Методы:**
- `to_dict()` - сериализация в JSON
- `from_dict()` - десериализация из JSON

**Invariants:**
- `nodes` и `edges` нормализуются к tuples для immutability

### 9. MetadataLineageBundleResult

**Файл:** `metadata_bundle.py`

**Назначение:** Domain-level bundle для sidecar metadata и lineage fragments.

**Type Variable:**
- `MetadataT` - тип metadata (BronzeMetadata | SilverMetadata | GoldMetadata)

**Ключевые функции:**
- `_resolve_primary_artifact_id()` - резолвинг primary artifact ID для fragment
- `_produced_artifact_ids()` - извлечение IDs произведенных artifacts
- `_produced_artifact_id_for_edge()` - извлечение artifact ID из edge
- `_attach_fragment_anchor()` - прикрепление lineage anchors к metadata
- `_set_missing_anchor()` - установка missing anchor

**Invariants:**
- Fragment должен expose ровно один produced artifact node
- Multiple produced artifacts вызывают ValueError

## Workflow

### Lineage Capture Flow

1. **Source System Capture**
   - Создание `LineageNodeRef` с типом `SOURCE_SYSTEM`
   - Создание `LineageNodeRef` с типом `SOURCE_REQUEST`
   - Связь через `LineageEdge` типа `DERIVED_FROM`

2. **Bronze Ingestion**
   - Создание `DatasetRef` для bronze dataset
   - Создание `LineageNodeRef` с типом `BRONZE_BATCH`
   - Связь через `LineageEdge` типа `PRODUCED_BY` с source request
   - Связь через `LineageEdge` типа `USED_SCHEMA` с schema

3. **Silver Transformation**
   - Создание `TransformRef` для transform stage
   - Создание `DatasetRef` для silver dataset
   - Связь через `LineageEdge` типа `DERIVED_FROM` с bronze dataset
   - Связь через `LineageEdge` типа `PRODUCED_BY` с transform

4. **Gold Aggregation**
   - Создание `DatasetRef` для gold dataset
   - Связь через `LineageEdge` типа `DERIVED_FROM` с silver datasets
   - Связь через `LineageEdge` типа `EXECUTED_IN` с run

5. **Fragment Creation**
   - Создание `LineageGraphFragment` с nodes и edges
   - Привязка к `run_id` и `manifest_id`
   - Сохранение в lineage store

6. **Metadata Bundle**
   - Создание `MetadataLineageBundleResult`
   - Прикрепление lineage anchors к metadata
   - Связь metadata с lineage fragment

## Graph Structure

### Typical Lineage Graph

```
SOURCE_SYSTEM
  └─ DERIVED_FROM → SOURCE_REQUEST
       └─ PRODUCED_BY → BRONZE_BATCH
            ├─ USED_SCHEMA → SCHEMA
            └─ DERIVED_FROM → DATASET (silver)
                 ├─ PRODUCED_BY → TRANSFORM
                 └─ DERIVED_FROM → DATASET (gold)
                      └─ EXECUTED_IN → RUN
                           └─ HAS_MANIFEST → MANIFEST
```

## Связанные ADR

- (Проверить наличие ADR для lineage architecture)

## Зависимости

### Internal
- `bioetl.domain.medallion` - Layer enum
- `bioetl.domain.models.metadata` - Metadata models (BronzeMetadata, SilverMetadata, GoldMetadata)
- `bioetl.domain.composite.lineage` - CompositeLineageMetadata

### External
- `dataclasses` - для dataclass моделей
- `datetime` - для timestamps
- `enum` - для enum типов
- `typing` - для type hints

## Примеры использования

### Создание DatasetRef

```python
from bioetl.domain.lineage import DatasetRef
from bioetl.domain.medallion import Layer

dataset_ref = DatasetRef(
    layer=Layer.BRONZE,
    logical_name="pubchem_bioactivity",
    version=1,
    provider="pubchem",
    entity="bioactivity",
    path="data/output/bronze/pubchem/bioactivity",
    manifest_id="manifest-001",
    run_id="run-001",
)

# Конвертация в node reference
node_ref = dataset_ref.to_node_ref()
print(node_ref.node_id)  # "bronze:pubchem_bioactivity@1"
```

### Создание LineageGraphFragment

```python
from bioetl.domain.lineage import (
    LineageGraphFragment,
    LineageNodeRef,
    LineageEdge,
    LineageEdgeType,
    LineageNodeType,
)
from datetime import datetime, UTC

source_node = LineageNodeRef(
    node_type=LineageNodeType.SOURCE_SYSTEM,
    node_id="source:pubchem",
    label="PubChem",
)

dataset_node = LineageNodeRef(
    node_type=LineageNodeType.DATASET,
    node_id="bronze:pubchem_bioactivity@1",
    label="PubChem Bioactivity",
)

edge = LineageEdge(
    edge_type=LineageEdgeType.DERIVED_FROM,
    source=source_node,
    target=dataset_node,
    run_id="run-001",
    manifest_id="manifest-001",
    created_at=datetime.now(UTC),
)

fragment = LineageGraphFragment(
    fragment_id="fragment-001",
    nodes=(source_node, dataset_node),
    edges=(edge,),
    run_id="run-001",
    manifest_id="manifest-001",
    created_at=datetime.now(UTC),
)
```

### Создание TransformRef

```python
from bioetl.domain.lineage import TransformRef

transform_ref = TransformRef(
    name="normalize_activity",
    version="1.0.0",
    step_index=0,
    pipeline_name="pubchem_pipeline",
    code_ref="src/bioetl/application/pipelines/pubchem/transformer.py",
)

# Конвертация в node reference
node_ref = transform_ref.to_node_ref()
print(node_ref.node_id)  # "transform:pubchem_pipeline:normalize_activity:1.0.0:0"
```

## Тестирование

Тесты для lineage implementation находятся в:
- `tests/unit/domain/lineage/` - unit тесты
- `tests/integration/domain/lineage/` - integration тесты

## Метрики качества

- Покрытие тестами: >90%
- Cyclomatic complexity: <10 для всех функций
- Type coverage: 100% (strict mode)
- Immutability: все key artifacts frozen (dataclass frozen=True)
