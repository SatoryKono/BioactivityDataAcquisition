# План унификации колонок publication (ChEMBL, CrossRef, OpenAlex, PubMed, SemanticScholar)

## 1. Где определяются имена колонок

### 1.1. Общая точка истины
- **`PublicationBaseSchema`** задаёт общий набор полей публикаций (pmid/doi/pmc_id, title, abstract, authors, journal, publication_year, publication_date, publication_type, language, page_first/page_last, citations_received/citations_made, is_oa и метаданные lookup/source). Это базовый контракт для Silver-уровня.
- **`PublicationEntityBase`** закрепляет унифицированные имена полей на уровне доменных сущностей (dataclass), от которых наследуются провайдеры.

### 1.2. Провайдеры (Silver-уровень)

#### ChEMBL
- **Transformer**: `src/bioetl/application/pipelines/chembl/publication_transformer.py`
  - Маппинг через `FieldGroup`/`FieldSpec`: `doc_type -> publication_type`, `year -> publication_year`, `first_page/last_page -> page_first/page_last`, `pubmed_id -> pmid`.
- **Schema**: `src/bioetl/domain/schemas/chembl/publication.py`
  - Валидация `publication_type`, `publication_year`, `page_first/page_last`, `chembl_release`, `creation_date` и т.д.
- **Entity**: `src/bioetl/domain/entities/chembl_structures.py` (`ChemblPublication`)

#### CrossRef
- **Transformer**: `src/bioetl/application/pipelines/crossref/transformer.py`
  - Нормализованные ключи: `publication_type`, `publication_date`, `citations_received`, `citations_made`, `journal_name_short`, `subject_keywords`, `author_orcids`, `author_details`, `references`.
- **Schema**: `src/bioetl/domain/schemas/crossref/publication.py`
- **Entity**: `src/bioetl/domain/entities/crossref.py` (`CrossRefPublicationEntity`)

#### OpenAlex
- **Transformer**: `src/bioetl/application/pipelines/openalex/transformer.py`
  - Ключи: `openalex_id`, `publication_year`, `publication_date`, `publication_type`, `citations_received`, `citations_made`, `subject_topics`, `primary_topic`, `subject_mesh`, `subject_keywords`, `author_orcids`, `author_openalex_ids`, `institution_ids`, `institution_country_codes`, `ror_ids`.
- **Schema**: `src/bioetl/domain/schemas/openalex/publication.py`
- **Entity**: `src/bioetl/domain/entities/openalex.py` (`OpenAlexPublicationEntity`)

#### PubMed
- **Transformer**: `src/bioetl/application/pipelines/pubmed/transformer.py`
  - Ключи: `publication_date`, `publication_year`, `publication_type`, `publication_types`, `page_range`, `page_first/page_last`, `journal_name_short`, `journal_iso_abbrev`, `subject_mesh`, `subject_keywords`, `affiliation_list`, `affiliation_structured`.
- **Schema**: `src/bioetl/domain/schemas/pubmed/publication.py`
- **Entity**: `src/bioetl/domain/entities/pubmed.py` (`PubMedPublicationEntity`)

#### Semantic Scholar
- **Transformer**: `src/bioetl/application/pipelines/semanticscholar/transformer.py`
  - Ключи: `paper_id`, `publication_date`, `publication_year`, `citations_received`, `citations_made`, `publication_types`, `subject_fields`, `author_s2_ids`, `author_orcids`, `author_h_indices`, `page_range`, `page_first/page_last`, `open_access_url`, `oa_status`.
- **Schema**: `src/bioetl/domain/schemas/semanticscholar/publication.py`
- **Entity**: `src/bioetl/domain/entities/semanticscholar.py` (`SemanticScholarPublicationEntity`)

### 1.3. Семантические группы (композитный слой)
- Группы полей и семантические соответствия уже зафиксированы в `configs/composite/field_groups/publication.yaml`.
  - **ID & Status**
  - **Bibliography**
  - **Author & Affiliations**
  - **Terms & Keywords & Topics**
  - **Citations & Reference**
  - **Date & Places**
  - **Publication Types**
  - **Trash (Excluded)**

## 2. Семантически сходные группы полей

Ниже — целевые унифицированные группы (ориентир — `PublicationBaseSchema` + `configs/composite/field_groups/publication.yaml`):

### 2.1. Идентификаторы и статус
- **doi / pmid / pmc_id / openalex_id / paper_id / document_chembl_id**
- **oa_status / is_oa / is_retracted**
- **publication_status**

### 2.2. Библиография
- **title / abstract / journal / journal_name_short / journal_name**
- **volume / issue / page_first / page_last / page_range / pages**
- **issn / issn_print / issn_electronic**
- **publisher / venue**

### 2.3. Авторы и аффилиации
- **authors / affiliation_list / affiliation_structured / authors_with_affiliations**
- **author_orcids / author_openalex_ids / author_s2_ids / author_h_indices**

### 2.4. Темы, ключевые слова, классификация
- **subject_keywords / subject_mesh / subject_topics / primary_topic / subject_fields**
- **keywords / mesh_terms / topics / fields_of_study** (кандидаты на алиасы)

### 2.5. Цитирования и ссылки
- **citations_received / citations_made / influential_citation_count**
- **references / citation_contexts**

### 2.6. Даты
- **publication_year / publication_date / published_print / published_online / published**
- **pub_date / pub_month / pub_day / date_completed / date_revised / creation_date**

### 2.7. Типы публикаций
- **publication_type** (single canonical)
- **publication_types / publication_type_list** (массив/JSON)
- **type** (raw provider type, кандидат на алиас)

## 3. План унификации наименований

### 3.1. Целевые принципы
1. **Единая база** — использовать `PublicationBaseSchema` как контракт унифицированных полей.
2. **Provider-specific поля** — оставлять, но привести имена к шаблону `snake_case`, без пересечения с базой.
3. **Алиасы** — временно поддерживать старые имена через `field_aliases`/переиспользование в трансформерах.

### 3.2. Предлагаемые правила унификации
- **publication_type** — одиночное значение (строка). Любые `type`, `doc_type`, `source_type` маппить сюда.
- **publication_types** — массив/JSON. `publication_type_list` и provider-specific списки маппить сюда (при необходимости).
- **citations_received / citations_made** — заменить `citation_count`/`reference_count` везде, где ещё встречаются.
- **page_first / page_last** — привести `first_page`/`last_page` и `pages` к паре полей + при необходимости `page_range`.
- **journal_name_short** — унифицировать `journal_abbrev`, `short_container_title`, `journal_title`.
- **subject_* префиксы** — все классификационные списки привести к `subject_keywords`, `subject_mesh`, `subject_topics`, `subject_fields`.

## 4. План корректировок в коде

### 4.1. Transformer слой (application)
- В каждом `*_publication` трансформере:
  - Проверить ключи в `_extract_business_data` и привести к унифицированным именам.
  - Добавить временный вывод старых ключей как alias-поля (если требуется обратная совместимость).

### 4.2. Domain entities
- Для каждого провайдера:
  - Привести provider-specific поля к унифицированным именам (особенно: `publication_type`, `citations_*`, `page_*`, `subject_*`).
  - Удалить/задепрекейтить устаревшие имена, если они ещё живут как атрибуты.

### 4.3. Pandera schemas
- Обновить `src/bioetl/domain/schemas/*/publication.py`:
  - Добавить `alias=` для старых имён (временно),
  - ИЛИ удалить старые имена и корректно обновить все источники данных.

### 4.4. Composite config
- Обновить `configs/composite/field_groups/publication.yaml`:
  - Убедиться, что только унифицированные имена являются base fields.
  - Старые имена оставить только в `Trash` или в `field_aliases`.

### 4.5. Документация и тесты
- Обновить provider docs (`docs/providers/*/publication.md`), чтобы перечислялись только унифицированные поля.
- Добавить тесты на наличие унифицированных полей в Silver слое.

## 5. Набор промтов для реализации

Ниже — примерный набор промтов для итеративной реализации:

1. **Инвентаризация полей**
   - "Собери таблицу всех полей publication для ChEMBL/CrossRef/OpenAlex/PubMed/SemanticScholar из трансформеров и Pandera schemas. Верни в Markdown-таблице с источниками файлов."

2. **Унификация base-полей**
   - "Обнови `PublicationBaseSchema` и provider schemas так, чтобы все ключевые поля publication соответствовали unified-именам (publication_year, publication_date, publication_type, citations_received, citations_made, page_first, page_last). Добавь временные alias-колонки для legacy имён."

3. **Обновление transformers**
   - "Приведи `_extract_business_data()` в каждом publication transformer к unified-именам. Удали/задепрекейтить старые ключи и добавь временные alias-поля при необходимости."

4. **Обновление entities**
   - "Приведи provider-specific publication entities к unified-именам. Удали/задепрекейтить `doc_type`, `citation_count`, `reference_count`, `short_container_title` и аналогичные legacy поля."

5. **Обновление composite config**
   - "Обнови `configs/composite/field_groups/publication.yaml`: base_name должен быть только унифицированным. Добавь legacy в `Trash` или `field_aliases`."

6. **Тесты и документация**
   - "Добавь тесты, которые проверяют наличие unified-полей в Silver схемах. Обнови docs/providers/*/publication.md, чтобы список полей совпадал с унифицированным контрактом."
