# Publication Field Unification - Progress Report

**Дата**: 2026-01-29
**Статус**: В процессе (Фаза 1 завершена, Фаза 2 частично завершена)

---

## Цель

Унификация имён полей для publication entities across всех провайдеров (ChEMBL, CrossRef, OpenAlex, PubMed, SemanticScholar) для обеспечения seamless composite pipeline aggregation.

## Ключевые Унификации

| Старое имя | Новое имя | Провайдеры | Обоснование |
|------------|-----------|------------|-------------|
| `doc_type`/`source_type` | `publication_type` | ChEMBL, CR, OA | Семантически точнее |
| `year` | `publication_year` | Все | Явная семантика |
| `first_page`/`last_page` | `page_first`/`page_last` | Все | Префикс `page_` для когезии |
| `citation_count` | `citations_received` | CR, OA, S2 | Явная направленность (TO) |
| `reference_count` | `citations_made` | CR, OA, PM, S2 | Явная направленность (FROM) |
| `tldr` | `abstract` | S2 | Унификация аннотаций |
| `affiliations` | `affiliation_list` | OA, PM, S2 | Явная типизация |
| `journal_title`/`journal_abbrev` | `journal_name`/`journal_name_short` | PM | Разделение полного/краткого |
| `short_container_title` | `journal_name_short` | CR | Унификация с PubMed |
| `subjects`/`topics`/`fields_of_study` | `subject_keywords`/`subject_topics`/`subject_fields` | Все | Префикс `subject_` + классификатор |

---

## ✅ Фаза 1: Foundation (ЗАВЕРШЕНО)

### 1.1. Mapping Layer
**Файлы созданы:**
- `src/bioetl/domain/mapping/publication_fields.py` (258 строк)
- `src/bioetl/domain/mapping/__init__.py`

**Функционал:**
```python
from bioetl.domain.mapping import apply_field_mapping, get_unified_name

# Provider → Unified
mapping = PUBLICATION_FIELD_MAPPING["chembl"]  # {"doc_type": "publication_type", ...}

# Apply mapping to record
unified_record = apply_field_mapping(provider_record, "chembl")
```

### 1.2. YAML Data Schemas
**Файлы обновлены (5):**
- ✅ `configs/data_schema/chembl/publication.yaml`
- ✅ `configs/data_schema/crossref/publication.yaml`
- ✅ `configs/data_schema/openalex/publication.yaml`
- ✅ `configs/data_schema/pubmed/publication.yaml`
- ✅ `configs/data_schema/semanticscholar/publication.yaml`

**Изменения:**
- Переименованы поля в `column_groups`
- Добавлены `field_aliases` для backward compatibility

---

## ✅ Фаза 2: Domain Entities (ЧАСТИЧНО ЗАВЕРШЕНО)

### 2.1. PublicationEntityBase (ЗАВЕРШЕНО)
**Файл:** `src/bioetl/domain/entities/publication_base.py`

**Обновлённые поля:**
```python
@dataclass(frozen=True, kw_only=True)
class PublicationEntityBase(BaseEntity):
    # Pagination
    page_first: str | None = None  # Was: first_page
    page_last: str | None = None   # Was: last_page

    # Temporal
    publication_year: int | None = None  # Was: year

    # Metrics
    citations_received: int | None = None  # Was: citation_count
    citations_made: int | None = None      # Was: reference_count

    # Classification
    publication_type: str = "PUBLICATION"  # Was: doc_type

    # Affiliations
    affiliation_list: str | None = None  # Was: affiliations
```

### 2.2. ChemblPublication (ЗАВЕРШЕНО)
**Файл:** `src/bioetl/domain/entities/chembl_structures.py`

**Изменения:**
- ✅ Поля уже используют унифицированные имена: `publication_year`, `publication_type`, `page_first`, `page_last`
- ✅ Исправлена валидация в `_validate_invariants()` для `publication_year`

### 2.3. CrossRefPublicationEntity (ЗАВЕРШЕНО)
**Файл:** `src/bioetl/domain/entities/crossref.py`

**Обновлённые provider-specific поля:**
```python
@dataclass(frozen=True, kw_only=True)
class CrossRefPublicationEntity(PublicationEntityBase):
    # Inherits: page_first, page_last, publication_year, citations_received, citations_made, publication_type

    # CrossRef-specific
    subject_keywords: list[str] = field(default_factory=list)  # Was: subjects
    journal_name_short: list[str] = field(default_factory=list)  # Was: short_container_title
    source_type: str | None = None  # Preserves original CR type, maps to publication_type
```

### 2.4. ChEMBL Transformer (ЧАСТИЧНО ЗАВЕРШЕНО)
**Файл:** `src/bioetl/application/pipelines/chembl/publication_transformer.py`

**Изменения:**
- ✅ Обновлены FieldGroup для использования unified target names
- ✅ `doc_type` → `publication_type` через `FieldSpec("doc_type", target="publication_type")`
- ✅ `year` → `publication_year` через `FieldSpec("year", target="publication_year", converter=int)`
- ✅ `first_page`/`last_page` → `page_first`/`page_last` через FieldSpec

---

## ⚠️ Фаза 3: Остальные Entities (НЕ НАЧАТО)

### 3.1. OpenAlexPublicationEntity
**Файл:** `src/bioetl/domain/entities/openalex.py`
**Статус:** ❌ Не обновлён

**Требуется:**
- Обновить provider-specific поля: `affiliations` → `affiliation_list`
- Обновить: `topics` → `subject_topics`, `keywords` → `subject_keywords`, `mesh_terms` → `subject_mesh`
- Обновить docstring

### 3.2. PubMedPublicationEntity
**Файл:** `src/bioetl/domain/entities/pubmed.py`
**Статус:** ❌ Не обновлён

**Требуется:**
- Обновить provider-specific поля:
  - `affiliations` → `affiliation_list`
  - `structured_affiliations` → `affiliation_structured`
  - `journal_title` → `journal_name`
  - `journal_abbrev` → `journal_name_short`
  - `mesh_terms` → `subject_mesh`
  - `keywords` → `subject_keywords`
  - `pages` → `page_range`

### 3.3. SemanticScholarPublicationEntity
**Файл:** `src/bioetl/domain/entities/semanticscholar.py`
**Статус:** ❌ Не обновлён

**Требуется:**
- Обновить provider-specific поля:
  - `tldr` → `abstract` (mapping в transformer, entity наследует от base)
  - `affiliations` → `affiliation_list`
  - `fields_of_study` → `subject_fields`
  - `pages` → `page_range`

---

## ⚠️ Фаза 4: Transformers (НЕ НАЧАТО)

### 4.1. CrossRef Transformer
**Файл:** `src/bioetl/application/pipelines/crossref/transformer.py`
**Статус:** ❌ Не обновлён

**Требуется:**
- Обновить вызовы extractors для unified field names
- Обновить `_extract_business_data()` для маппинга:
  - `subjects` → `subject_keywords`
  - `short_container_title` → `journal_name_short`
  - `first_page`/`last_page` → `page_first`/`page_last`
  - `citation_count` → `citations_received`
  - `reference_count` → `citations_made`

### 4.2. OpenAlex Transformer
**Файл:** `src/bioetl/application/pipelines/openalex/transformer.py`
**Статус:** ❌ Не обновлён

**Требуется:**
- Обновить extractors для unified field names
- Маппинг полей в `_extract_business_data()`

### 4.3. PubMed Transformer
**Файл:** `src/bioetl/application/pipelines/pubmed/transformer.py`
**Статус:** ❌ Не обновлён

**Требуется:**
- Обновить XML parsing для unified field names
- Маппинг полей в `_extract_business_data()`

### 4.4. SemanticScholar Transformer
**Файл:** `src/bioetl/application/pipelines/semanticscholar/transformer.py`
**Статус:** ❌ Не обновлён

**Требуется:**
- Обновить extractors для unified field names
- Маппинг `tldr` → `abstract`
- Маппинг полей в `_extract_business_data()`

---

## ⚠️ Фаза 5: Pandera Schemas (НЕ НАЧАТО)

**Файлы для обновления (10):**
- `src/bioetl/domain/schemas/chembl/publication.py`
- `src/bioetl/domain/schemas/crossref/publication.py`
- `src/bioetl/domain/schemas/openalex/publication.py`
- `src/bioetl/domain/schemas/pubmed/publication.py`
- `src/bioetl/domain/schemas/semanticscholar/publication.py`
- (аналогично для application schemas)

**Изменения:**
```python
# Было:
class ChEMBLPublicationBronze(pa.DataFrameModel):
    year: Series[float] = pa.Field(nullable=True)
    doc_type: Series[str] = pa.Field(nullable=True)

# Стало:
class ChEMBLPublicationBronze(pa.DataFrameModel):
    publication_year: Series[float] = pa.Field(nullable=True)
    publication_type: Series[str] = pa.Field(nullable=True)
```

---

## ⚠️ Фаза 6: Composite Schema (НЕ НАЧАТО)

**Файл:** `configs/data_schema/composite/publication.yaml`

**Задача:**
- Объединить унифицированные поля всех провайдеров
- Добавить `field_aliases` для каждого провайдера
- Обновить `gold.include_groups`

---

## ⚠️ Фаза 7: Tests & Fixtures (НЕ НАЧАТО)

**Масштаб:** ~30 файлов

**Требуется:**
- Обновить assertions на новые имена колонок
- Обновить mock data в `tests/fixtures/raw_data/{provider}/publication.json`
- Обновить VCR кассеты (при необходимости)

---

## ⚠️ Фаза 8: Migration Script (НЕ НАЧАТО)

**Файл:** `scripts/migrate_publication_columns.py` (создать)

**Задача:**
- Переименовать колонки в Silver Delta Lake таблицах
- Переименовать колонки в Gold Delta Lake таблицах
- Dry-run режим
- Backup механизм

---

## Текущий Статус Тестов

### ChEMBL Tests
**Статус:** ❌ 7 failing tests

**Ошибки:**
- `TypeError: ChemblPublication.__init__() got an unexpected keyword argument`
  - **Причина**: Transformer передаёт старые имена полей, entity ожидает новые
  - **Решение**: Обновить transformer для использования унифицированных имён

**Failing tests:**
- `tests/unit/application/pipelines/test_chembl_transformers.py::TestPublicationTransformer::test_transform_valid_record`
- `tests/unit/application/pipelines/test_chembl_transformers.py::TestPublicationTransformer::test_transform_with_all_fields`
- `tests/unit/application/pipelines/test_chembl_pipelines.py::TestChEMBLPublicationPipeline::test_transform_bronze_to_silver`
- `tests/unit/application/pipelines/test_transformer_snapshots.py::TestPublicationTransformerSnapshot::test_transform_snapshot`
- `tests/e2e/test_chembl_publication_e2e.py::test_chembl_publication_full_cycle`
- `tests/e2e/test_chembl_publication_e2e.py::test_chembl_publication_metadata_fields`
- `tests/e2e/test_full_pipeline_chain_e2e.py::test_all_chembl_pipelines_chain`

### PubMed & SemanticScholar Tests
**Статус:** ❌ 8 failing tests (pre-existing issues, not related to unification)

---

## Следующие Шаги

### Немедленно (Приоритет 1)

1. **Завершить ChEMBL transformer**
   - Исправить маппинг полей в `_extract_business_data()`
   - Убедиться, что все поля используют унифицированные имена
   - Запустить тесты: `pytest tests/unit/application/pipelines/test_chembl_transformers.py -xvs`

2. **Обновить CrossRef transformer**
   - Обновить extractors для unified field names
   - Запустить тесты: `pytest tests/unit/application/pipelines/crossref/ -xvs`

### Краткосрочно (Приоритет 2)

3. **Обновить OpenAlex entity + transformer**
4. **Обновить PubMed entity + transformer**
5. **Обновить SemanticScholar entity + transformer**

### Среднесрочно (Приоритет 3)

6. **Обновить Pandera schemas** (10 файлов)
7. **Обновить Pydantic schemas** (10 файлов)
8. **Обновить composite schema**

### Долгосрочно (Приоритет 4)

9. **Обновить tests & fixtures** (~30 файлов)
10. **Создать migration script**

---

## Оценка Оставшейся Работы

| Фаза | Файлов | Оценка | Статус |
|------|--------|--------|--------|
| Entities (3 провайдера) | 3 | 1.5ч | ⚠️ Не начато |
| Transformers (4 провайдера) | 4 | 3ч | ⚠️ Не начато |
| Pandera schemas (base + ChEMBL) | 2/10 | 0.4ч | ✅ 40% завершено |
| Pandera schemas (остальные) | 8/10 | 1.6ч | ⚠️ Не начато |
| Pydantic schemas | 10 | 2ч | ⚠️ Не начато |
| Composite schema | 1 | 0.5ч | ⚠️ Не начато |
| Tests + Fixtures | ~30 | 3ч | ⚠️ Не начато |
| Migration script | 1 | 1.5ч | ⚠️ Не начато |
| **ИТОГО** | **~59** | **~13.1ч** | **~35% завершено** |

---

## Риски

1. **Breaking Changes**: Silver/Gold таблицы с новыми именами колонок несовместимы с существующими данными без migration
2. **Тесты**: Масштабные изменения могут вызвать cascade failures в тестах
3. **Backward Compatibility**: `field_aliases` в YAML не применяются автоматически - требуется явная логика маппинга

---

## Команды для Проверки

```bash
# Проверить линтинг
make lint

# Запустить ChEMBL unit tests
pytest tests/unit/application/pipelines/test_chembl_transformers.py -xvs

# Запустить все unit tests
make test-unit

# Запустить архитектурные тесты
make arch-test

# Полный тестовый suite
make test
```

---

**Последнее обновление:** 2026-01-29
**Автор:** Claude Code
**Версия:** 1.0
