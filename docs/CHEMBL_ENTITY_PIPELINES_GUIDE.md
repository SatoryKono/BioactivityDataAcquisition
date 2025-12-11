# Руководства по реализации ChEMBL пайплайнов

Данный документ содержит подробные планы реализации пайплайнов для следующих сущностей ChEMBL:
1. [Target Relation](#1-target-relation-pipeline)
2. [Compound Record](#2-compound-record-pipeline)
3. [Document Similarity](#3-document-similarity-pipeline)
4. [Document Term](#4-document-term-pipeline)
5. [Molecule Form](#5-molecule-form-pipeline)
6. [Protein Classification](#6-protein-classification-pipeline)

---

## 1. Target Relation Pipeline

### Описание
Пайплайн для извлечения данных о связях между таргетами (targets). Описывает отношения типа SUBSET OF, SUPERSET OF, OVERLAPS WITH между различными таргетами ChEMBL.

### API Endpoint
- **URL:** `https://www.ebi.ac.uk/chembl/api/data/target_relation`
- **Формат:** JSON/XML

### Шаг 1: Создание конфигурации пайплайна

**Файл:** `configs/pipelines/chembl/target_relation.yaml`

```yaml
# Target Relation Pipeline Configuration

id: chembl.target_relation
provider: chembl
entity: target_relation
primary_key: "${CHEMBL_TARGET_RELATION_PRIMARY_KEY:-target_chembl_id}"

input_mode: id_only
input_path: data/input/target_relation.csv
output_path: ./data/output/chembl/target_relation
batch_size: 50

provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
  client:
    timeout_sec: 30.0
    max_retries: 3
    rate_limit_per_sec: 10.0
  max_url_length: 2000
  batch_size: 50
  page_size: 1000
  api_version: null

csv_options:
  delimiter: ","
  header: true

pipeline:
  name: target_relation_chembl
  version: "1.0.0"
  owner: "Data Acquisition Team"
  description: "Extract target relationship data from ChEMBL API"
  enable_denormalization: false

transform:
  serialization_mode: pipe

fields:
  - name: target_chembl_id
    data_type: string
    is_nullable: false
    is_filterable: true
    description: "ChEMBL ID основного таргета"

  - name: related_target_chembl_id
    data_type: string
    is_nullable: false
    is_filterable: true
    description: "ChEMBL ID связанного таргета"

  - name: relationship
    data_type: string
    is_nullable: false
    is_filterable: true
    description: "Тип отношения между таргетами (SUBSET OF, SUPERSET OF, OVERLAPS WITH)"

quality:
  hashing:
    business_key_fields:
      - target_chembl_id
      - related_target_chembl_id

  normalization:
    case_sensitive_fields:
      - relationship
    id_fields:
      - target_chembl_id
      - related_target_chembl_id
```

### Шаг 2: Добавление endpoint mapping

**Файл:** `src/bioetl/infrastructure/clients/chembl/constants.py`

```python
ENTITY_TO_ENDPOINT: dict[str, str] = {
    # ... существующие маппинги ...
    "target_relation": "target_relation",  # <-- Добавить
}
```

### Шаг 3: Регистрация пайплайна в реестре

**Файл:** `src/bioetl/application/pipelines/registry.py`

```python
_FACTORIES: dict[str, PipelineFactoryABC] = {
    # ... существующие пайплайны ...
    "chembl.target_relation": ChemblPipelineFactory(),  # <-- Добавить
}
```

### Шаг 4: Создание схемы контракта (опционально)

**Файл:** `src/bioetl/domain/schemas/contracts/chembl_target_relation.py`

```python
"""Schema contract for ChEMBL target_relation entity."""

from bioetl.domain.schemas.pipeline_contracts import PipelineSchemaModel, FieldSchema

CHEMBL_TARGET_RELATION_CONTRACT = PipelineSchemaModel(
    pipeline_id="chembl.target_relation",
    entity="target_relation",
    fields=[
        FieldSchema(name="target_chembl_id", dtype="string", nullable=False),
        FieldSchema(name="related_target_chembl_id", dtype="string", nullable=False),
        FieldSchema(name="relationship", dtype="string", nullable=False),
    ],
)
```

### Шаг 5: Создание входных данных

**Файл:** `data/input/target_relation.csv`

```csv
target_chembl_id
CHEMBL2363965
CHEMBL2096904
CHEMBL3038518
```

### Шаг 6: Запуск пайплайна

```bash
python -m bioetl run --pipeline chembl.target_relation --output ./data/output/chembl/target_relation
```

---

## 2. Compound Record Pipeline

### Описание
Пайплайн для извлечения записей о соединениях из научных документов. Связывает конкретные соединения (molecules) с документами, в которых они упоминаются.

### API Endpoint
- **URL:** `https://www.ebi.ac.uk/chembl/api/data/compound_record`
- **Формат:** JSON/XML

### Шаг 1: Создание конфигурации пайплайна

**Файл:** `configs/pipelines/chembl/compound_record.yaml`

```yaml
# Compound Record Pipeline Configuration

id: chembl.compound_record
provider: chembl
entity: compound_record
primary_key: "${CHEMBL_COMPOUND_RECORD_PRIMARY_KEY:-record_id}"

input_mode: id_only
input_path: data/input/compound_record.csv
output_path: ./data/output/chembl/compound_record
batch_size: 50

provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
  client:
    timeout_sec: 30.0
    max_retries: 3
    rate_limit_per_sec: 10.0
  max_url_length: 2000
  batch_size: 50
  page_size: 1000
  api_version: null

csv_options:
  delimiter: ","
  header: true

pipeline:
  name: compound_record_chembl
  version: "1.0.0"
  owner: "Data Acquisition Team"
  description: "Extract compound records from ChEMBL API - links compounds to scientific documents"
  enable_denormalization: false

transform:
  serialization_mode: pipe

fields:
  - name: record_id
    data_type: integer
    is_nullable: false
    is_filterable: false
    description: "Уникальный идентификатор записи соединения"

  - name: compound_key
    data_type: string
    is_nullable: true
    is_filterable: true
    description: "Ключевой текст, идентифицирующий соединение в научном документе"

  - name: compound_name
    data_type: string
    is_nullable: true
    is_filterable: true
    description: "Название соединения, записанное в научном документе"

  - name: document_chembl_id
    data_type: string
    is_nullable: false
    is_filterable: false
    description: "ChEMBL ID документа, содержащего запись"

  - name: molecule_chembl_id
    data_type: string
    is_nullable: false
    is_filterable: false
    description: "ChEMBL ID молекулы"

  - name: src_id
    data_type: integer
    is_nullable: true
    is_filterable: true
    description: "Идентификатор источника данных"

quality:
  hashing:
    business_key_fields:
      - record_id

  normalization:
    case_sensitive_fields:
      - compound_name
      - compound_key
    id_fields:
      - record_id
      - document_chembl_id
      - molecule_chembl_id
```

### Шаг 2: Добавление endpoint mapping

**Файл:** `src/bioetl/infrastructure/clients/chembl/constants.py`

```python
ENTITY_TO_ENDPOINT: dict[str, str] = {
    # ... существующие маппинги ...
    "compound_record": "compound_record",  # <-- Добавить
}
```

### Шаг 3: Регистрация пайплайна в реестре

**Файл:** `src/bioetl/application/pipelines/registry.py`

```python
_FACTORIES: dict[str, PipelineFactoryABC] = {
    # ... существующие пайплайны ...
    "chembl.compound_record": ChemblPipelineFactory(),  # <-- Добавить
}
```

### Шаг 4: Создание схемы контракта (опционально)

**Файл:** `src/bioetl/domain/schemas/contracts/chembl_compound_record.py`

```python
"""Schema contract for ChEMBL compound_record entity."""

from bioetl.domain.schemas.pipeline_contracts import PipelineSchemaModel, FieldSchema

CHEMBL_COMPOUND_RECORD_CONTRACT = PipelineSchemaModel(
    pipeline_id="chembl.compound_record",
    entity="compound_record",
    fields=[
        FieldSchema(name="record_id", dtype="Int64", nullable=False),
        FieldSchema(name="compound_key", dtype="string", nullable=True),
        FieldSchema(name="compound_name", dtype="string", nullable=True),
        FieldSchema(name="document_chembl_id", dtype="string", nullable=False),
        FieldSchema(name="molecule_chembl_id", dtype="string", nullable=False),
        FieldSchema(name="src_id", dtype="Int64", nullable=True),
    ],
)
```

### Шаг 5: Создание входных данных

**Файл:** `data/input/compound_record.csv`

```csv
molecule_chembl_id
CHEMBL25
CHEMBL59
CHEMBL137
```

### Шаг 6: Запуск пайплайна

```bash
python -m bioetl run --pipeline chembl.compound_record --output ./data/output/chembl/compound_record
```

---

## 3. Document Similarity Pipeline

### Описание
Пайплайн для извлечения данных о похожести документов. Предоставляет метрики сходства между документами на основе Tanimoto similarity по молекулам (mol_tani) и таргетам (tid_tani).

### API Endpoint
- **URL:** `https://www.ebi.ac.uk/chembl/api/data/document_similarity`
- **Формат:** JSON/XML

### Шаг 1: Создание конфигурации пайплайна

**Файл:** `configs/pipelines/chembl/document_similarity.yaml`

```yaml
# Document Similarity Pipeline Configuration

id: chembl.document_similarity
provider: chembl
entity: document_similarity
primary_key: "${CHEMBL_DOCUMENT_SIMILARITY_PRIMARY_KEY:-document_1_chembl_id}"

input_mode: id_only
input_path: data/input/document_similarity.csv
output_path: ./data/output/chembl/document_similarity
batch_size: 50

provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
  client:
    timeout_sec: 30.0
    max_retries: 3
    rate_limit_per_sec: 10.0
  max_url_length: 2000
  batch_size: 50
  page_size: 1000
  api_version: null

csv_options:
  delimiter: ","
  header: true

pipeline:
  name: document_similarity_chembl
  version: "1.0.0"
  owner: "Data Acquisition Team"
  description: "Extract document similarity data from ChEMBL API"
  enable_denormalization: false

transform:
  serialization_mode: pipe

fields:
  - name: document_1_chembl_id
    data_type: string
    is_nullable: false
    is_filterable: true
    description: "ChEMBL ID первого документа"

  - name: document_2_chembl_id
    data_type: string
    is_nullable: false
    is_filterable: true
    description: "ChEMBL ID второго документа"

  - name: mol_tani
    data_type: number
    is_nullable: true
    is_filterable: true
    description: "Tanimoto similarity по молекулам (0.0 - 1.0)"

  - name: tid_tani
    data_type: number
    is_nullable: true
    is_filterable: true
    description: "Tanimoto similarity по таргетам (0.0 - 1.0)"

quality:
  hashing:
    business_key_fields:
      - document_1_chembl_id
      - document_2_chembl_id

  normalization:
    case_sensitive_fields: []
    id_fields:
      - document_1_chembl_id
      - document_2_chembl_id
```

### Шаг 2: Добавление endpoint mapping

**Файл:** `src/bioetl/infrastructure/clients/chembl/constants.py`

```python
ENTITY_TO_ENDPOINT: dict[str, str] = {
    # ... существующие маппинги ...
    "document_similarity": "document_similarity",  # <-- Добавить
}
```

### Шаг 3: Регистрация пайплайна в реестре

**Файл:** `src/bioetl/application/pipelines/registry.py`

```python
_FACTORIES: dict[str, PipelineFactoryABC] = {
    # ... существующие пайплайны ...
    "chembl.document_similarity": ChemblPipelineFactory(),  # <-- Добавить
}
```

### Шаг 4: Создание схемы контракта (опционально)

**Файл:** `src/bioetl/domain/schemas/contracts/chembl_document_similarity.py`

```python
"""Schema contract for ChEMBL document_similarity entity."""

from bioetl.domain.schemas.pipeline_contracts import PipelineSchemaModel, FieldSchema

CHEMBL_DOCUMENT_SIMILARITY_CONTRACT = PipelineSchemaModel(
    pipeline_id="chembl.document_similarity",
    entity="document_similarity",
    fields=[
        FieldSchema(name="document_1_chembl_id", dtype="string", nullable=False),
        FieldSchema(name="document_2_chembl_id", dtype="string", nullable=False),
        FieldSchema(name="mol_tani", dtype="Float64", nullable=True),
        FieldSchema(name="tid_tani", dtype="Float64", nullable=True),
    ],
)
```

### Шаг 5: Создание входных данных

**Файл:** `data/input/document_similarity.csv`

```csv
document_chembl_id
CHEMBL1121359
CHEMBL1123599
CHEMBL1127448
```

### Шаг 6: Запуск пайплайна

```bash
python -m bioetl run --pipeline chembl.document_similarity --output ./data/output/chembl/document_similarity
```

---

## 4. Document Term Pipeline

### Описание
Пайплайн для извлечения ключевых терминов из документов ChEMBL. Термины извлекаются с использованием алгоритма TextRank.

### API Endpoint
- **URL:** `https://www.ebi.ac.uk/chembl/api/data/document_term`
- **Формат:** JSON/XML

> **Примечание:** Этот endpoint может требовать специального формата запроса или быть доступным только для определенных документов. Рекомендуется проверить актуальность endpoint в документации ChEMBL API.

### Шаг 1: Создание конфигурации пайплайна

**Файл:** `configs/pipelines/chembl/document_term.yaml`

```yaml
# Document Term Pipeline Configuration

id: chembl.document_term
provider: chembl
entity: document_term
primary_key: "${CHEMBL_DOCUMENT_TERM_PRIMARY_KEY:-document_chembl_id}"

input_mode: id_only
input_path: data/input/document_term.csv
output_path: ./data/output/chembl/document_term
batch_size: 50

provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
  client:
    timeout_sec: 30.0
    max_retries: 3
    rate_limit_per_sec: 10.0
  max_url_length: 2000
  batch_size: 50
  page_size: 1000
  api_version: null

csv_options:
  delimiter: ","
  header: true

pipeline:
  name: document_term_chembl
  version: "1.0.0"
  owner: "Data Acquisition Team"
  description: "Extract document keywords/terms from ChEMBL API using TextRank algorithm"
  enable_denormalization: false

transform:
  serialization_mode: pipe

# Примечание: Поля требуют уточнения после проверки доступности endpoint
fields:
  - name: document_chembl_id
    data_type: string
    is_nullable: false
    is_filterable: true
    description: "ChEMBL ID документа"

  - name: term
    data_type: string
    is_nullable: false
    is_filterable: true
    description: "Ключевой термин, извлеченный из документа"

  - name: score
    data_type: number
    is_nullable: true
    is_filterable: true
    description: "TextRank score термина"

  - name: term_type
    data_type: string
    is_nullable: true
    is_filterable: true
    description: "Тип термина (например, KEYWORD, ENTITY)"

quality:
  hashing:
    business_key_fields:
      - document_chembl_id
      - term

  normalization:
    case_sensitive_fields:
      - term
    id_fields:
      - document_chembl_id
```

### Шаг 2: Добавление endpoint mapping

**Файл:** `src/bioetl/infrastructure/clients/chembl/constants.py`

```python
ENTITY_TO_ENDPOINT: dict[str, str] = {
    # ... существующие маппинги ...
    "document_term": "document_term",  # <-- Добавить
}
```

### Шаг 3: Регистрация пайплайна в реестре

**Файл:** `src/bioetl/application/pipelines/registry.py`

```python
_FACTORIES: dict[str, PipelineFactoryABC] = {
    # ... существующие пайплайны ...
    "chembl.document_term": ChemblPipelineFactory(),  # <-- Добавить
}
```

### Шаг 4: Создание схемы контракта (опционально)

**Файл:** `src/bioetl/domain/schemas/contracts/chembl_document_term.py`

```python
"""Schema contract for ChEMBL document_term entity."""

from bioetl.domain.schemas.pipeline_contracts import PipelineSchemaModel, FieldSchema

CHEMBL_DOCUMENT_TERM_CONTRACT = PipelineSchemaModel(
    pipeline_id="chembl.document_term",
    entity="document_term",
    fields=[
        FieldSchema(name="document_chembl_id", dtype="string", nullable=False),
        FieldSchema(name="term", dtype="string", nullable=False),
        FieldSchema(name="score", dtype="Float64", nullable=True),
        FieldSchema(name="term_type", dtype="string", nullable=True),
    ],
)
```

### Шаг 5: Создание входных данных

**Файл:** `data/input/document_term.csv`

```csv
document_chembl_id
CHEMBL1121359
CHEMBL1123599
CHEMBL1127448
```

### Шаг 6: Запуск пайплайна

```bash
python -m bioetl run --pipeline chembl.document_term --output ./data/output/chembl/document_term
```

---

## 5. Molecule Form Pipeline

### Описание
Пайплайн для извлечения данных о связях между родительскими молекулами и их солевыми формами. Позволяет идентифицировать родительское соединение для каждой солевой формы.

### API Endpoint
- **URL:** `https://www.ebi.ac.uk/chembl/api/data/molecule_form`
- **Формат:** JSON/XML

### Шаг 1: Создание конфигурации пайплайна

**Файл:** `configs/pipelines/chembl/molecule_form.yaml`

```yaml
# Molecule Form Pipeline Configuration

id: chembl.molecule_form
provider: chembl
entity: molecule_form
primary_key: "${CHEMBL_MOLECULE_FORM_PRIMARY_KEY:-molecule_chembl_id}"

input_mode: id_only
input_path: data/input/molecule_form.csv
output_path: ./data/output/chembl/molecule_form
batch_size: 50

provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
  client:
    timeout_sec: 30.0
    max_retries: 3
    rate_limit_per_sec: 10.0
  max_url_length: 2000
  batch_size: 50
  page_size: 1000
  api_version: null

csv_options:
  delimiter: ","
  header: true

pipeline:
  name: molecule_form_chembl
  version: "1.0.0"
  owner: "Data Acquisition Team"
  description: "Extract molecule form relationships (parent-salt) from ChEMBL API"
  enable_denormalization: false

transform:
  serialization_mode: pipe

fields:
  - name: molecule_chembl_id
    data_type: string
    is_nullable: false
    is_filterable: true
    description: "ChEMBL ID молекулы (соли или родительского соединения)"

  - name: parent_chembl_id
    data_type: string
    is_nullable: false
    is_filterable: true
    description: "ChEMBL ID родительского соединения"

  - name: is_parent
    data_type: boolean
    is_nullable: false
    is_filterable: false
    description: "Флаг: является ли данная запись родительским соединением"

quality:
  hashing:
    business_key_fields:
      - molecule_chembl_id
      - parent_chembl_id

  normalization:
    case_sensitive_fields: []
    id_fields:
      - molecule_chembl_id
      - parent_chembl_id
```

### Шаг 2: Добавление endpoint mapping

**Файл:** `src/bioetl/infrastructure/clients/chembl/constants.py`

```python
ENTITY_TO_ENDPOINT: dict[str, str] = {
    # ... существующие маппинги ...
    "molecule_form": "molecule_form",  # <-- Добавить
}
```

### Шаг 3: Регистрация пайплайна в реестре

**Файл:** `src/bioetl/application/pipelines/registry.py`

```python
_FACTORIES: dict[str, PipelineFactoryABC] = {
    # ... существующие пайплайны ...
    "chembl.molecule_form": ChemblPipelineFactory(),  # <-- Добавить
}
```

### Шаг 4: Создание схемы контракта (опционально)

**Файл:** `src/bioetl/domain/schemas/contracts/chembl_molecule_form.py`

```python
"""Schema contract for ChEMBL molecule_form entity."""

from bioetl.domain.schemas.pipeline_contracts import PipelineSchemaModel, FieldSchema

CHEMBL_MOLECULE_FORM_CONTRACT = PipelineSchemaModel(
    pipeline_id="chembl.molecule_form",
    entity="molecule_form",
    fields=[
        FieldSchema(name="molecule_chembl_id", dtype="string", nullable=False),
        FieldSchema(name="parent_chembl_id", dtype="string", nullable=False),
        FieldSchema(name="is_parent", dtype="bool", nullable=False),
    ],
)
```

### Шаг 5: Создание входных данных

**Файл:** `data/input/molecule_form.csv`

```csv
molecule_chembl_id
CHEMBL25
CHEMBL59
CHEMBL137
CHEMBL1201585
```

### Шаг 6: Запуск пайплайна

```bash
python -m bioetl run --pipeline chembl.molecule_form --output ./data/output/chembl/molecule_form
```

---

## 6. Protein Classification Pipeline

### Описание
Пайплайн для извлечения данных о классификации белков. Предоставляет иерархическую классификацию белковых семейств для компонентов таргетов (TargetComponents).

### API Endpoint
- **URL:** `https://www.ebi.ac.uk/chembl/api/data/protein_classification`
- **Формат:** JSON/XML

### Шаг 1: Создание конфигурации пайплайна

**Файл:** `configs/pipelines/chembl/protein_classification.yaml`

```yaml
# Protein Classification Pipeline Configuration

id: chembl.protein_classification
provider: chembl
entity: protein_classification
primary_key: "${CHEMBL_PROTEIN_CLASSIFICATION_PRIMARY_KEY:-protein_class_id}"

input_mode: api
input_path: null
output_path: ./data/output/chembl/protein_classification
batch_size: 100

provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
  client:
    timeout_sec: 30.0
    max_retries: 3
    rate_limit_per_sec: 10.0
  max_url_length: 2000
  batch_size: 100
  page_size: 1000
  api_version: null

csv_options:
  delimiter: ","
  header: true

pipeline:
  name: protein_classification_chembl
  version: "1.0.0"
  owner: "Data Acquisition Team"
  description: "Extract protein family classification hierarchy from ChEMBL API"
  enable_denormalization: false

transform:
  serialization_mode: pipe

fields:
  - name: protein_class_id
    data_type: integer
    is_nullable: false
    is_filterable: true
    description: "Уникальный идентификатор класса белков (Primary Key)"

  - name: class_level
    data_type: integer
    is_nullable: false
    is_filterable: true
    description: "Уровень класса в иерархии (1 = верхний уровень)"

  - name: parent_id
    data_type: integer
    is_nullable: true
    is_filterable: true
    description: "ID родительского класса белков"

  - name: pref_name
    data_type: string
    is_nullable: false
    is_filterable: true
    description: "Предпочтительное/полное название белкового семейства"

  - name: short_name
    data_type: string
    is_nullable: true
    is_filterable: true
    description: "Короткое/сокращенное название (не обязательно уникальное)"

  - name: definition
    data_type: string
    is_nullable: true
    is_filterable: true
    description: "Определение белкового семейства"

  - name: protein_class_desc
    data_type: string
    is_nullable: true
    is_filterable: true
    description: "Конкатенированное описание всей классификации для поиска"

  - name: sort_order
    data_type: integer
    is_nullable: true
    is_filterable: true
    description: "Порядок сортировки в рамках уровня"

  - name: replaced_by
    data_type: integer
    is_nullable: true
    is_filterable: false
    description: "ID класса, которым был заменен данный класс (для устаревших записей)"

quality:
  hashing:
    business_key_fields:
      - protein_class_id

  normalization:
    case_sensitive_fields:
      - definition
      - protein_class_desc
    id_fields:
      - protein_class_id
      - parent_id
      - replaced_by
```

### Шаг 2: Добавление endpoint mapping

**Файл:** `src/bioetl/infrastructure/clients/chembl/constants.py`

```python
ENTITY_TO_ENDPOINT: dict[str, str] = {
    # ... существующие маппинги ...
    "protein_classification": "protein_classification",  # <-- Добавить
}
```

### Шаг 3: Регистрация пайплайна в реестре

**Файл:** `src/bioetl/application/pipelines/registry.py`

```python
_FACTORIES: dict[str, PipelineFactoryABC] = {
    # ... существующие пайплайны ...
    "chembl.protein_classification": ChemblPipelineFactory(),  # <-- Добавить
}
```

### Шаг 4: Создание схемы контракта (опционально)

**Файл:** `src/bioetl/domain/schemas/contracts/chembl_protein_classification.py`

```python
"""Schema contract for ChEMBL protein_classification entity."""

from bioetl.domain.schemas.pipeline_contracts import PipelineSchemaModel, FieldSchema

CHEMBL_PROTEIN_CLASSIFICATION_CONTRACT = PipelineSchemaModel(
    pipeline_id="chembl.protein_classification",
    entity="protein_classification",
    fields=[
        FieldSchema(name="protein_class_id", dtype="Int64", nullable=False),
        FieldSchema(name="class_level", dtype="Int64", nullable=False),
        FieldSchema(name="parent_id", dtype="Int64", nullable=True),
        FieldSchema(name="pref_name", dtype="string", nullable=False),
        FieldSchema(name="short_name", dtype="string", nullable=True),
        FieldSchema(name="definition", dtype="string", nullable=True),
        FieldSchema(name="protein_class_desc", dtype="string", nullable=True),
        FieldSchema(name="sort_order", dtype="Int64", nullable=True),
        FieldSchema(name="replaced_by", dtype="Int64", nullable=True),
    ],
)
```

### Шаг 5: Создание входных данных (опционально)

Для protein_classification можно использовать режим `api` без входного файла, так как это справочные данные, которые можно загрузить целиком.

**Файл:** `data/input/protein_classification.csv` (если нужна фильтрация)

```csv
protein_class_id
1
2
3
```

### Шаг 6: Запуск пайплайна

```bash
# Загрузка всей классификации
python -m bioetl run --pipeline chembl.protein_classification --output ./data/output/chembl/protein_classification

# С ограничением записей
python -m bioetl run --pipeline chembl.protein_classification --limit 1000
```

---

## Сводная таблица пайплайнов

| Пайплайн | Entity | Primary Key | Input Mode | Описание |
|----------|--------|-------------|------------|----------|
| `chembl.target_relation` | target_relation | target_chembl_id | id_only | Связи между таргетами |
| `chembl.compound_record` | compound_record | record_id | id_only | Записи соединений в документах |
| `chembl.document_similarity` | document_similarity | document_1_chembl_id | id_only | Сходство между документами |
| `chembl.document_term` | document_term | document_chembl_id | id_only | Ключевые термины документов |
| `chembl.molecule_form` | molecule_form | molecule_chembl_id | id_only | Связи родитель-соль для молекул |
| `chembl.protein_classification` | protein_classification | protein_class_id | api | Иерархия классификации белков |

---

## Общий чек-лист для каждого пайплайна

### Обязательные шаги
- [ ] Создать конфигурационный файл `configs/pipelines/chembl/<entity>.yaml`
- [ ] Добавить маппинг в `ENTITY_TO_ENDPOINT` (если endpoint новый)
- [ ] Зарегистрировать в `registry.py`

### Опциональные шаги
- [ ] Создать схему контракта в `domain/schemas/contracts/`
- [ ] Зарегистрировать контракт в `pipeline_contracts.py`
- [ ] Создать входной CSV файл
- [ ] Написать unit тесты
- [ ] Написать integration тесты

### Тестирование

```bash
# Dry run
python -m bioetl run --pipeline chembl.<entity> --dry-run

# Ограниченный запуск
python -m bioetl run --pipeline chembl.<entity> --limit 10

# Полный запуск
python -m bioetl run --pipeline chembl.<entity>
```

---

## Полезные ссылки

- [ChEMBL API Documentation](https://www.ebi.ac.uk/chembl/api/data/docs)
- [ChEMBL Web Services Guide](https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services)
- [ChEMBL Python Client](https://github.com/chembl/chembl_webresource_client)
- [Основное руководство по пайплайнам](./PIPELINE_IMPLEMENTATION_GUIDE.md)
