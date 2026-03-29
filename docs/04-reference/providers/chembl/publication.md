# Пайплайн: ChEMBL Publication

**Имя пайплайна:** `chembl_publication`
**Провайдер:** `chembl`
**Сущность:** `publication`

---

## 1. Что делает пайплайн

`chembl_publication` нормализует публикационные записи ChEMBL в unified
Silver-модель `ChemblPublication`.

Source of truth для текущего поведения:

- `configs/entities/chembl/publication.yaml`
- `src/bioetl/application/pipelines/chembl/publication_transformer.py`
- `src/bioetl/domain/schemas/chembl/publication.py`
- `src/bioetl/infrastructure/schemas/silver_chembl_core.py`

---

## 2. Конфигурация

Текущая config-поверхность задаёт:

- `quality.entity_field_validations` для `publication_id`, `publication_type`, `publication_year`, `publication_pmid`, `publication_doi`, `title`, `citations_received`, `citations_made`
- `quality.entity_cross_field_validations`:
  - `publication_id` + `title`
  - `publication_pmid` or `publication_doi`
- `filters.extraction_params`:
  - `doc_type: PUBLICATION`
  - `year__gte: 1950`
  - `year__lte: 2050`
- `filters.silver_filters.required_fields`:
  - `publication_id`
  - `publication_type`
  - `title`
- `filters.gold_filters.required_fields`:
  - `publication_id`
  - `publication_type`
  - `title`

---

## 3. Silver surface

### 3.1. Основные обязательные поля

Current Silver contract жёстко опирается на:

| Поле | Где закреплено |
|------|----------------|
| `publication_id` | YAML required + Arrow + Pandera |
| `publication_type` | YAML required + Arrow + Pandera |
| `title` | YAML required + Arrow + Pandera |

### 3.2. Маппинг входных полей

`PublicationTransformer` поддерживает и нормализует:

- primary id: `publication_id` или legacy `document_chembl_id`
- cross-reference поля:
  - `pubmed_id -> publication_pmid`
  - `doi -> publication_doi`
  - `pmid` и `doi` как unified aliases
- журнал и пагинацию:
  - `year -> publication_year`
  - `first_page -> page_first`
  - `last_page -> page_last`
- тип публикации:
  - `doc_type -> publication_type`
  - затем `normalize_publication_type(...)`

### 3.3. Runtime/service поля в Silver

Трансформер явно добавляет в Silver surface:

- `_lookup_method = "direct"`
- `_original_id`
- `_source = "chembl"`
- `chembl_release`
- `creation_date`

Эти поля не являются drift-артефактами: они присутствуют в Arrow/Pandera
контрактах и входят в текущую модель публикации.

### 3.4. Авторы и текстовые поля

- `title` и `abstract` проходят через `DataNormalizationService`
- `authors` нормализуются в сериализованное представление
- `author_keys` вычисляются отдельно для downstream matching/join сценариев

---

## 4. Валидация

### 4.1. Arrow schema

Silver Arrow schema определяется в
`src/bioetl/infrastructure/schemas/silver_chembl_core.py` как
`CHEMBL_PUBLICATION_SCHEMA`.

### 4.2. Pandera schema

Silver Pandera schema определяется в
`src/bioetl/domain/schemas/chembl/publication.py` как
`ChemblPublicationSchema`.

Страница не фиксирует literal-формулу `entity_id`: текущая реализация использует
общий identity service/base transformer.

---

## 5. CLI

```bash
bioetl run --pipeline chembl_publication
bioetl run --pipeline chembl_publication --limit 1000
```

---

## 6. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/entities/chembl/publication.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/publication_transformer.py` |
| Arrow schema | `src/bioetl/infrastructure/schemas/silver_chembl_core.py` |
| Pandera schema | `src/bioetl/domain/schemas/chembl/publication.py` |
| Pipeline defs | `src/bioetl/application/pipelines/chembl/_pipelines.py` |
