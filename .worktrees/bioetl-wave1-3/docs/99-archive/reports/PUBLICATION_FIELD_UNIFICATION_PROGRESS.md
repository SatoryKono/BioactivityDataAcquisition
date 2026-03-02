# Publication Field Unification - Progress Report

**Дата**: 2026-02-03
**Статус**: ✅ ЗАВЕРШЕНО (Все фазы)

---

## Цель

Унификация имён полей для publication entities across всех провайдеров (ChEMBL, CrossRef, OpenAlex, PubMed, SemanticScholar) для обеспечения seamless composite pipeline aggregation.

## Ключевые Унификации

| Старое имя | Новое имя | Провайдеры | Обоснование |
|------------|-----------|------------|-------------|
| `doc-type`/`source-type` | `publication-type` | ChEMBL, CR, OA | Семантически точнее |
| `year` | `publication-year` | Все | Явная семантика |
| `first-page`/`last-page` | `page-first`/`page-last` | Все | Префикс `page-` для когезии |
| `citation-count` | `citations-received` | CR, OA, S2 | Явная направленность (TO) |
| `reference-count` | `citations-made` | CR, OA, PM, S2 | Явная направленность (FROM) |
| `tldr` | `abstract` | S2 | Унификация аннотаций |
| `affiliations` | `affiliation-list` | OA, PM, S2 | Явная типизация |
| `journal-title`/`journal-abbrev` | `journal-name`/`journal-name-short` | PM | Разделение полного/краткого |
| `short-container-title` | `journal-name-short` | CR | Унификация с PubMed |
| `subjects`/`topics`/`fields-of-study` | `subject-keywords`/`subject-topics`/`subject-fields` | Все | Префикс `subject-` + классификатор |

---

## ✅ Фаза 1: Foundation (ЗАВЕРШЕНО)

### 1.1. Mapping Layer
**Файлы созданы:**
- `src/bioetl/domain/mapping/publication-fields.py` (275 строк)
- `src/bioetl/domain/mapping/--init--.py`

**Функционал:**
```python
from bioetl.domain.mapping import apply-field-mapping, get-unified-name

# Provider → Unified
mapping = PUBLICATION-FIELD-MAPPING["chembl"]  # {"doc-type": "publication-type", ...}

# Apply mapping to record
unified-record = apply-field-mapping(provider-record, "chembl")
```

### 1.2. YAML Data Schemas
**Файлы обновлены (5):**
- ✅ `configs/schemas/chembl/publication.yaml`
- ✅ `configs/schemas/crossref/publication.yaml`
- ✅ `configs/schemas/openalex/publication.yaml`
- ✅ `configs/schemas/pubmed/publication.yaml`
- ✅ `configs/schemas/semanticscholar/publication.yaml`

**Изменения:**
- Переименованы поля в `column-groups`
- Добавлены `field-aliases` для backward compatibility

---

## ✅ Фаза 2: Domain Entities (ЗАВЕРШЕНО)

### 2.1. PublicationEntityBase (ЗАВЕРШЕНО)
**Файл:** `src/bioetl/domain/entities/publication-base.py` (128 строк)

**Унифицированные поля:**
```python
@dataclass(frozen=True, kw-only=True)
class PublicationEntityBase(BaseEntity):
    # Pagination
    page-first: str | None = None
    page-last: str | None = None

    # Temporal
    publication-year: int | None = None

    # Metrics
    citations-received: int | None = None
    citations-made: int | None = None

    # Classification
    publication-type: str = "PUBLICATION"

    # Affiliations
    affiliation-list: str | None = None
```

### 2.2. Provider Entities (ВСЕ ЗАВЕРШЕНЫ)

| Provider | Entity | Файл | Статус |
|----------|--------|------|--------|
| ChEMBL | `ChemblPublication` | `domain/entities/chembl-structures.py` | ✅ Наследует от base |
| CrossRef | `CrossRefPublicationEntity` | `domain/entities/crossref.py` | ✅ Наследует от base |
| OpenAlex | `OpenAlexPublicationEntity` | `domain/entities/openalex.py` | ✅ Наследует от base |
| PubMed | `PubMedPublicationEntity` | `domain/entities/pubmed.py` | ✅ Наследует от base |
| SemanticScholar | `SemanticScholarPublicationEntity` | `domain/entities/semanticscholar.py` | ✅ Наследует от base |

---

## ✅ Фаза 3: Transformers (ЗАВЕРШЕНО)

Все transformers обновлены для использования unified field names:

| Provider | Transformer | Тесты |
|----------|------------|-------|
| ChEMBL | `publication-transformer.py` | ✅ 3/3 passed |
| CrossRef | `transformer.py` | ✅ 148/148 passed |
| OpenAlex | `transformer.py` | ✅ 147/147 passed |
| PubMed | `pubmed-transformer.py` | ✅ 77/77 passed |
| SemanticScholar | `transformer.py` | ✅ 177/177 passed |

---

## ✅ Фаза 4: Pandera Schemas (ЗАВЕРШЕНО)

### 4.1. Base Schema (ЗАВЕРШЕНО)
**Файл:** `src/bioetl/domain/schemas/common/publication-base.py` (157 строк)

Содержит все унифицированные поля:
- `publication-year: Series[pd.Int64Dtype]`
- `page-first: Series[str]`
- `page-last: Series[str]`
- `citations-received: Series[pd.Int64Dtype]`
- `citations-made: Series[pd.Int64Dtype]`
- `publication-type: Series[str]`
- `affiliation-list: Series[str]`

### 4.2. Provider Schemas (ВСЕ НАСЛЕДУЮТ ОТ BASE)

| Provider | Schema | Наследование |
|----------|--------|--------------|
| ChEMBL | `ChemblPublicationSchema` | ✅ `PublicationBaseSchema` |
| CrossRef | `PublicationEnrichedSchema` | ✅ `PublicationBaseSchema` |
| OpenAlex | `OpenAlexPublicationSchema` | ✅ `PublicationBaseSchema` |
| PubMed | `PubMedPublicationSchema` | ✅ `PublicationBaseSchema` |
| SemanticScholar | `SemanticScholarPublicationSchema` | ✅ `PublicationBaseSchema` |

---

## ✅ Фаза 5: Composite Schema (ЗАВЕРШЕНО)

**Файл:** `configs/schemas/composite/publication.yaml` (10,735 bytes)

**Содержит:**
- Unified field names в `column-groups`
- `field-aliases` для backward compatibility:
  ```yaml
  field-aliases:
    year: publication-year
    first-page: page-first
    last-page: page-last
    citation-count: citations-received
    reference-count: citations-made
  ```

---

## ✅ Фаза 6: Tests (ЗАВЕРШЕНО)

### Статус тестов по провайдерам

| Провайдер | Unit Tests | E2E Tests | Статус |
|-----------|------------|-----------|--------|
| ChEMBL | 3 passed | 2 passed | ✅ |
| CrossRef | 148 passed | - | ✅ |
| OpenAlex | 147 passed | - | ✅ |
| PubMed | 77 passed | - | ✅ |
| SemanticScholar | 177 passed | - | ✅ |

### Общая статистика тестов

- **Всего тестов:** 9,954 (35 deselected)
- **Unit tests по трансформерам:** 552 passed
- **Architecture tests:** All passed
- **E2E tests:** 16 passed

---

## ⚠️ Фаза 7: Migration Script (НЕ ТРЕБУЕТСЯ)

**Статус:** ❌ Не создан (пока не требуется)

**Обоснование:**
- Проект ещё не имеет production Delta Lake таблиц с legacy field names
- Все новые данные будут записываться с unified field names
- При необходимости миграции в будущем — создать `scripts/migrate-publication-columns.py`

---

## Архитектурные Решения

### Наследование Entity → Schema

```
PublicationEntityBase (domain/entities/publication-base.py)
    ↓ наследуют
ChemblPublication, CrossRefPublicationEntity, OpenAlexPublicationEntity,
PubMedPublicationEntity, SemanticScholarPublicationEntity

PublicationBaseSchema (domain/schemas/common/publication-base.py)
    ↓ наследуют
ChemblPublicationSchema, PublicationEnrichedSchema, OpenAlexPublicationSchema,
PubMedPublicationSchema, SemanticScholarPublicationSchema
```

### Field Aliases для Backward Compatibility

YAML data schemas и composite schema содержат `field-aliases` для поддержки legacy field names:
- `year` → `publication-year`
- `first-page` → `page-first`
- `last-page` → `page-last`
- `citation-count` → `citations-received`
- `reference-count` → `citations-made`
- `doc-type` → `publication-type`

---

## Метрики Проекта (2026-02-03)

| Метрика | Значение |
|---------|----------|
| **Python-файлов** | ~1,040 |
| **Тестов** | ~9,954 |
| **Провайдеров** | 7 (ChEMBL, CrossRef, OpenAlex, PubMed, SemanticScholar, PubChem, UniProt) |
| **Publication entities** | 5 (все унифицированы) |
| **Unified fields** | 10 ключевых полей |

---

## Команды для Проверки

```bash
# Проверить линтинг
make lint

# Запустить все unit tests по трансформерам
pytest tests/unit/application/pipelines/*/test-*transformer*.py -v

# Запустить architecture tests
make arch-test

# Полный тестовый suite
make test
```

---

## Связанные Документы

- [ADR-029: Output Metadata Unification](../../02-architecture/decisions/ADR-029-output-metadata-unification.md)
- [RULES.md §2.6: Int→Float Coercion](../../00-project/RULES.md)
- [Composite Publication Schema](https://github.com/SatoryKono/BioactivityDataAcquisition2/blob/main/configs/schemas/composite/publication.yaml)

---

**Последнее обновление:** 2026-02-03
**Автор:** Claude Code
**Версия:** 2.0 (Все фазы завершены)
