# Publication Pipelines — Validation Matrix

*Автоматический анализ на основе исходного кода схем и конфигураций DQ.*
*Дата: 2026-02-09*

## Обзор

Проект содержит **6 publication пайплайнов**:

| # | Pipeline | Провайдер | Primary Key | Schema (Silver) | Gold Schema |
|---|----------|-----------|-------------|-----------------|-------------|
| 1 | `pubmed_publication` | PubMed | `pmid` | `PubMedPublicationSchema` | `PubMedPublicationGoldSchema` |
| 2 | `crossref_publication` | CrossRef | `doi` | `PublicationEnrichedSchema` | `CrossRefPublicationGoldSchema` |
| 3 | `openalex_publication` | OpenAlex | `openalex_id` | `OpenAlexPublicationSchema` | `OpenAlexPublicationGoldSchema` |
| 4 | `semanticscholar_publication` | Semantic Scholar | `paper_id` | `SemanticScholarPublicationSchema` | `SemanticScholarPublicationGoldSchema` |
| 5 | `chembl_publication` | ChEMBL | `document_chembl_id` | `ChemblPublicationSchema` | — (нет отдельной Gold) |
| 6 | `chembl_publication_term` | ChEMBL | composite key | `PublicationTermSchema` | — |

Все Silver-схемы (кроме `publication_term`) наследуют от `PublicationBaseSchema`.

### DQ Thresholds

| Provider | Soft Fail | Hard Fail |
|----------|-----------|-----------|
| PubMed | 5% | 15% |
| CrossRef | 10% | 30% |
| OpenAlex | 8% | 25% |
| Semantic Scholar | 15% | 40% |
| ChEMBL | inherited | inherited |

---

## Сводная таблица валидации по полям

### Условные обозначения

- **REQ** — поле обязательное (nullable=False)
- **OPT** — поле необязательное (nullable=True)
- **—** — поле отсутствует в этом пайплайне
- **`regex`** — валидация по регулярному выражению (str_matches / pattern)
- **`range`** — валидация диапазона (ge/le/min/max)
- **`enum`** — валидация по набору допустимых значений (isin)
- **`check`** — кастомный Pandera check (метод класса)
- **`≥0`** — non-negative constraint
- **`coerce`** — принудительное приведение типа (Gold: int→float)
- **DQ** — дополнительная проверка в YAML DQ-правилах

---

### 1. Первичные ключи (Provider-Specific)

| Поле | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL Pub | ChEMBL Term |
|------|--------|----------|----------|------------------|------------|-------------|
| `pmid` | **REQ**, `regex: ^\d+$`, `check: ^[1-9]\d*$` (positive int) | — | — | — | — | — |
| `doi` | OPT, `check: ^10\.\d{4,}/.+$` | **REQ**, `regex: ^10\.\d{4,}/.+$` | OPT | OPT | OPT | — |
| `openalex_id` | — | — | **REQ**, `regex: ^W\d+$` | — | — | — |
| `paper_id` | — | — | — | **REQ**, `regex: ^[a-f0-9]{40}$` | — | — |
| `document_chembl_id` | — | — | — | — | **REQ**, `regex: ^CHEMBL\d+$` | **REQ**, `regex: ^CHEMBL\d+$` |
| `entity_id` | — | — | — | — | — | **REQ** (SHA256 hash composite key) |

---

### 2. Кросс-ссылочные идентификаторы

| Поле | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL Pub | ChEMBL Term |
|------|--------|----------|----------|------------------|------------|-------------|
| `pmid` | (см. PK выше) | — | OPT, `regex: ^[1-9]\d*$` (base) | OPT, `regex: ^[1-9]\d*$` (base) | OPT, `regex: ^[1-9]\d*$` (base) | — |
| `doi` | OPT, `check: ^10\.\d{4,}/.+$` | (см. PK выше) | OPT, `regex: ^10\.\d{4,}/.+$` (base) | OPT, `regex: ^10\.\d{4,}/.+$` (base) | OPT, `regex: ^10\.\d{4,}/.+$` (base) | — |
| `pmc_id` | OPT, `check: ^PMC\d+$` | — | OPT, `regex: ^PMC\d+$` (base) | — (excluded by design) | — | — |
| `pii` | OPT | — | — | — | — | — |
| `mid` | OPT | — | — | — | — | — |
| `publisher_id` | OPT | — | — | — | — | — |
| `dblp_id` | — | — | — | OPT | — | — |
| `corpus_id` | — | — | — | OPT, Int64, `≥0` | — | — |
| `mag_id` | — | — | OPT (legacy) | — | — | — |
| `src_id` | — | — | — | — | OPT, Int64 | — |

---

### 3. Основной контент

| Поле | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL Pub | ChEMBL Term |
|------|--------|----------|----------|------------------|------------|-------------|
| `title` | **REQ**, `check: len ≥ 1`; DQ: `≤2000 chars` | OPT; DQ: `≤2000 chars` | OPT; DQ: `≤2000 chars` | OPT; DQ: `≤2000 chars` | OPT (base) | — |
| `abstract` | OPT (base) | OPT (base) | OPT (base) | OPT (base) | OPT (base) | — |
| `abstract_structured` | OPT, bool (NLM sections) | — | — | — | — | — |
| `tldr` | — | — | — | OPT (AI-generated summary) | — | — |
| `authors` | OPT (JSON array, PII hashed) | OPT (JSON array, PII hashed) | OPT (JSON array, PII hashed) | OPT (JSON array, PII hashed) | OPT (JSON array, PII hashed) | — |
| `language` | OPT, `check: len 2-3` (MARC code) | OPT (base) | OPT (base) | — (API не возвращает) | — (API не возвращает) | — |
| `term` | — | — | — | — | — | **REQ**, `str_length ≥ 1`; DQ: `≤500 chars` |
| `term_type` | — | — | — | — | — | **REQ**, `enum: [MESH_HEADING, MESH_QUALIFIER, KEYWORD, CONCEPT]` |
| `mesh_id` | — | — | — | — | — | OPT |
| `qualifier` | — | — | — | — | — | OPT |

---

### 4. Журнал и пагинация

| Поле | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL Pub | ChEMBL Term |
|------|--------|----------|----------|------------------|------------|-------------|
| `journal` | OPT | OPT (base) | OPT (base) | OPT (base) | OPT (base) | — |
| `journal_name_short` | OPT | OPT | — | — | — | — |
| `journal_iso_abbrev` | OPT | — | — | — | — | — |
| `issn` | OPT, `check: ^\d{4}-\d{3}[\dX]$` | OPT, `regex: ^\d{4}-\d{3}[\dX]$` | OPT, `regex: ^\d{4}-\d{3}[\dX]$` | — | — | — |
| `issn_list` | — | OPT (JSON array) | — | — | — | — |
| `issn_print` | — | OPT, `regex: ^\d{4}-\d{3}[\dX]$` | — | — | — | — |
| `issn_electronic` | — | OPT, `regex: ^\d{4}-\d{3}[\dX]$` | — | — | — | — |
| `journal_issn_type` | OPT, `check: enum [Print, Electronic, Linking]` | — | — | — | — | — |
| `nlm_unique_id` | OPT | — | — | — | — | — |
| `publisher` | — | OPT | OPT | — | — | — |
| `volume` | — | OPT (Gold) | OPT | OPT | OPT | — |
| `issue` | — | OPT (Gold) | OPT | — | OPT | — |
| `page_first` | OPT (base) | OPT (base) | OPT (base) | OPT (base) | OPT | — |
| `page_last` | OPT (base) | OPT (base) | OPT (base) | OPT (base) | OPT | — |
| `page_range` | OPT | — | — | OPT | — | — |
| `medline_pgn` | OPT | — | — | — | — | — |
| `country` | OPT | — | — | — | — | — |

---

### 5. Даты

| Поле | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL Pub | ChEMBL Term |
|------|--------|----------|----------|------------------|------------|-------------|
| `publication_year` | OPT, Int64, `check: [1800, 2100]`; DQ: `[1800, 2100]` | OPT (base), Int64, `[1800, 2100]`; Gold: float `[1900, 2100]`, coerce | OPT (base), Int64, `[1800, 2100]`; DQ: `[1500, 2100]`; Gold: float `[1500, 2100]`, coerce | OPT (base), Int64, `[1800, 2100]`; DQ: `[1500, 2100]`; Gold: float, coerce | OPT (base), Int64, `[1800, 2100]`; DQ: `[1800, 2100]` | — |
| `publication_date` | OPT, `regex: ^\d{4}-\d{2}-\d{2}$` (base) | OPT (base) | OPT (base) | OPT (base) | — (only year available) | — |
| `pub_month` | OPT, Int64, `check: [1, 12]` | — | — | — | — | — |
| `pub_day` | OPT, Int64, `check: [1, 31]` | — | — | — | — | — |
| `published_print` | — | OPT (ISO date) | — | — | — | — |
| `published_online` | — | OPT (ISO date) | — | — | — | — |
| `published` | — | OPT (canonical YYYY-MM-DD) | — | — | — | — |
| `date_completed` | OPT, datetime | — | — | — | — | — |
| `date_revised` | OPT, datetime | — | — | — | — | — |
| `creation_date` | — | — | — | — | OPT, `regex: ^\d{4}-\d{2}-\d{2}$` | — |

---

### 6. Метрики цитирования

| Поле | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL Pub | ChEMBL Term |
|------|--------|----------|----------|------------------|------------|-------------|
| `citations_received` | OPT, Int64, `≥0` (base) | OPT, Int64, `≥0` (base); DQ: `≥0`; Gold: float, coerce | OPT, Int64, `≥0` (base); DQ: `≥0`; Gold: float, coerce | OPT, Int64, `≥0` (base); DQ: `≥0`; Gold: float, coerce | OPT (base) | — |
| `citations_made` | OPT, Int64, `≥0` (base); Gold: float, `≥0`, coerce | OPT, Int64, `≥0` (base); Gold: float, `≥0`, coerce | OPT, Int64, `≥0` (base); Gold: float, `≥0`, coerce | OPT, Int64, `≥0` (base); Gold: float, `≥0`, coerce | OPT (base) | — |
| `influential_citation_count` | — | — | — | OPT, Int64, `≥0`; DQ: `≥0`; Gold: float, coerce | — | — |
| `fwci` | — | — | OPT, float, `≥0`; DQ: `≥0` | — | — | — |

---

### 7. Open Access

| Поле | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL Pub | ChEMBL Term |
|------|--------|----------|----------|------------------|------------|-------------|
| `is_oa` | OPT, bool (base) | OPT, bool (base) | OPT, bool (base) | OPT, bool (base) | — | — |
| `oa_status` | — | — | OPT, `enum: [gold, green, hybrid, bronze, closed]` | OPT, `enum: [gold, green, hybrid, bronze, closed]` | — | — |
| `is_retracted` | — | — | **REQ**, bool | — | — | — |
| `open_access_url` | — | — | — | OPT | — | — |
| `license_url` | — | OPT | — | — | — | — |

---

### 8. Классификация и тематика

| Поле | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL Pub | ChEMBL Term |
|------|--------|----------|----------|------------------|------------|-------------|
| `publication_type` | OPT (base) | OPT (raw CrossRef type) | OPT (raw OpenAlex type) | OPT (pipe-delimited) | OPT, `enum: [PUBLICATION, PATENT, DATASET, BOOK]` | — |
| `publication_types` | OPT (JSON array) | — | — | OPT (JSON array) | — | — |
| `publication_type_list` | OPT (JSON array) | — | — | — | — | — |
| `publication_status` | OPT, `check: enum [ppublish, epublish, aheadofprint]` | — | — | — | — | — |
| `subject_mesh` | OPT (JSON array) | — | OPT (JSON array) | — | — | — |
| `subject_keywords` | OPT (JSON array) | OPT (JSON array) | OPT (JSON array) | — | — | — |
| `subject_topics` | — | — | OPT (JSON array, 4-level hierarchy) | — | — | — |
| `primary_topic` | — | — | OPT (JSON object) | — | — | — |
| `subject_fields` | — | — | — | OPT (JSON array) | — | — |
| `chemicals` | OPT (JSON array) | — | — | — | — | — |
| `databanks` | OPT (JSON array) | — | — | — | — | — |
| `gene_symbols` | OPT (JSON array) | — | — | — | — | — |
| `citation_subset` | OPT | — | — | — | — | — |
| `citation_contexts` | — | — | — | OPT (JSON array) | — | — |

---

### 9. Авторы и аффилиации

| Поле | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL Pub | ChEMBL Term |
|------|--------|----------|----------|------------------|------------|-------------|
| `affiliation_list` | OPT (base, JSON array) | OPT (base) | OPT (base, JSON array) | OPT (base) | OPT (base) | — |
| `affiliation_structured` | OPT (JSON array + ROR/GRID) | — | — | — | — | — |
| `authors_with_affiliations` | OPT (JSON array) | — | — | — | — | — |
| `author_count` | OPT, Int64, `check: ≥0` | — | — | — | — | — |
| `author_orcid_list` | — | OPT, `check: ORCID format` (JSON array) | — | — | — | — |
| `author_orcids` | — | — | OPT, `check: ORCID format` (JSON array) | OPT, `check: ORCID format` (JSON array) | — | — |
| `author_details` | — | OPT (JSON: given, family, orcid, sequence, affiliations) | — | — | — | — |
| `author_openalex_ids` | — | — | OPT (JSON array) | — | — | — |
| `author_s2_ids` | — | — | — | OPT (JSON array, 40-char hex) | — | — |
| `author_h_indices` | — | — | — | OPT (JSON array) | — | — |
| `institution_ids` | — | — | OPT (JSON array) | — | — | — |
| `institution_country_codes` | — | — | OPT (JSON array, ISO 2-letter) | — | — | — |
| `ror_ids` | — | — | OPT (JSON array, ROR URLs) | — | — | — |
| `references` | — | OPT (JSON array: DOI, title, author, year) | — | — | — | — |

---

### 10. Гранты и финансирование

| Поле | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL Pub | ChEMBL Term |
|------|--------|----------|----------|------------------|------------|-------------|
| `grant_count` | OPT, Int64, `check: ≥0` | — | — | — | — | — |
| `grants` | — | — | OPT (JSON array) | — | — | — |

---

### 11. Денормализованные счётчики

| Поле | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL Pub | ChEMBL Term |
|------|--------|----------|----------|------------------|------------|-------------|
| `author_count` | OPT, Int64, `check: ≥0`; Gold: float, coerce | — | — | — | — | — |
| `mesh_heading_count` | OPT, Int64, `check: ≥0`; Gold: float, coerce | — | — | — | — | — |
| `keyword_count` | OPT, Int64, `check: ≥0`; Gold: float, coerce | — | — | — | — | — |
| `chemical_count` | OPT, Int64, `check: ≥0`; Gold: float, coerce | — | — | — | — | — |

---

### 12. Системные / Служебные поля

| Поле | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL Pub | ChEMBL Term |
|------|--------|----------|----------|------------------|------------|-------------|
| `_source` | OPT (base) | **REQ**, `eq: "crossref"` | **REQ** | **REQ**, `eq: "semanticscholar"` | **REQ**, default `"chembl"` | — (inherited from ETLRecordSchema) |
| `_lookup_method` | OPT, `enum: LOOKUP_METHODS` (base) | OPT, `enum: LOOKUP_METHODS` (base) | **REQ**, `enum: LOOKUP_METHODS` | **REQ**, `enum: LOOKUP_METHODS` | **REQ**, `enum: LOOKUP_METHODS` | — |
| `_original_id` | OPT (base) | OPT (base) | OPT (base) | OPT (base) | OPT (base) | — |
| `_dq_warn` | — | — | — | — | OPT, BooleanDtype, default False | — |
| `_dq_error` | — | — | — | — | OPT, BooleanDtype, default False | — |
| `chembl_release` | — | — | — | — | OPT | — |

---

### 13. Метаданные домена (CrossRef-specific)

| Поле | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL Pub | ChEMBL Term |
|------|--------|----------|----------|------------------|------------|-------------|
| `content_domain_domains` | — | OPT, object (list) | — | — | — | — |
| `content_domain_crossmark_restriction` | — | OPT, bool, coerce | — | — | — | — |
| `alternative_id` | — | OPT, object (list) | — | — | — | — |

---

## Cross-Field (DQ) валидации

| Правило | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL Pub | ChEMBL Term |
|---------|--------|----------|----------|------------------|------------|-------------|
| Идентификация записи | `pmid` AND `title` — all_present | `doi` AND `title` — all_present | `openalex_id` AND `title` — all_present | `paper_id` AND `title` — all_present | `pubmed_id` OR `doi` OR `title` — any_present | `document_chembl_id` AND `term` AND `term_type` — all_present |
| Наличие хотя бы одного ID | `pmid` OR `doi` OR `pmc_id` — any_present | — | — | — | — | — |
| Предупреждение о ретракции | — | — | `is_retracted == true` → warn | — | — | — |

---

## Gold Layer — Особенности валидации

Все Gold-схемы используют `strict = True` (запрещены лишние колонки). Основные отличия от Silver:

| Аспект | Silver | Gold |
|--------|--------|------|
| Режим | `strict=False` (допускает extra columns) | `strict=True` (только определённые колонки) |
| Int→Float | `pd.Int64Dtype` (nullable int) | `float` с `coerce=True` (nullable int → float) |
| Обязательные мета-поля | — | `entity_id`, `content_hash`, `_run_id`, `_run_type`, `_ingestion_ts`, `_index`, `_dq_warn`, `_dq_error` |
| CrossRef `publication_year` | `[1800, 2100]` | `[1900, 2100]` (сужен нижний предел) |
| OpenAlex `publication_year` | `[1800, 2100]` (schema) / `[1500, 2100]` (DQ) | `[1500, 2100]` |

---

## Анализ расхождений: одноимённые поля с различной валидацией

Ниже перечислены **все поля**, которые присутствуют в ≥2 пайплайнах под одним именем,
но имеют **различающуюся** валидацию (nullable, диапазон, regex, enum, механизм проверки)
на каком-либо из слоёв (Silver Schema / DQ YAML / Gold Schema).

---

### D-01. `publication_year` — расхождение диапазонов

Самое масштабное расхождение: **4 разных диапазона** на пересечении слоёв и провайдеров.

| Слой | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|------|--------|----------|----------|------------------|--------|
| **Silver schema** | Int64, `[1800, 2100]` (base + explicit check) | Int64, `[1800, 2100]` (base) | Int64, `[1800, 2100]` (base) | Int64, `[1800, 2100]` (base) | Int64, `[1800, 2100]` (base) |
| **DQ YAML** | `[1800, 2100]` | `[1800, 2100]` | **`[1500, 2100]`** | **`[1500, 2100]`** | `[1800, 2100]` |
| **Gold schema** | float, coerce — **нет диапазона!** | float, **`[1900, 2100]`**, coerce | float, **`[1500, 2100]`**, coerce | float, coerce — **нет диапазона!** | — |

**Выявленные проблемы:**
1. Silver schema для всех пайплайнов использует `[1800, 2100]`, но DQ-правила OpenAlex и S2 расширяют нижнюю границу до `1500` — DQ может пропустить записи, отклонённые Silver.
2. Gold CrossRef **сужает** нижнюю границу до `1900` (было `1800`) — записи XVIII–XIX века пройдут Silver, но упадут на Gold.
3. Gold PubMed и Gold S2 **вообще не имеют** ограничения диапазона — любой год будет принят.
4. PubMed Silver дублирует check `[1800, 2100]`, который уже задан в base через `ge`/`le` — избыточность.

**План унификации:**

| # | Действие | Приоритет | Файлы |
|---|----------|-----------|-------|
| 1 | Определить единый диапазон: предлагается **`[1500, 2100]`** для всех пайплайнов (OpenAlex и S2 содержат записи ≥1500, исторические научные журналы существуют с XVII века) | HIGH | `validation.py`: `MIN_PUBLICATION_YEAR = 1500` |
| 2 | Обновить DQ-правила PubMed, CrossRef, ChEMBL: `min: 1500` | HIGH | `configs/dq/entities/*/publication.yaml` |
| 3 | Добавить range constraints в Gold PubMed и Gold S2: `ge=1500, le=2100` | HIGH | `contracts/gold/publications.py` |
| 4 | Исправить Gold CrossRef: `ge=1500` вместо `ge=1900` | HIGH | `contracts/gold/publications.py` |
| 5 | Удалить дублирующий `_check_year` из PubMed Silver (уже покрыт base `ge`/`le`) | LOW | `schemas/pubmed/publication.py` |

---

### D-02. `doi` — расхождение nullable, механизма и regex

| Слой | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|------|--------|----------|----------|------------------|--------|
| **Silver nullable** | True | **False** (PK) | True | True | True |
| **Silver механизм** | `@pa.check` (метод класса) | `str_matches` (Field param) | `str_matches` (base) | `str_matches` (base) | `str_matches` (base) |
| **Silver regex** | `^10\.\d{4,}/.+$` | `^10\.\d{4,}/.+$` | `^10\.\d{4,}/.+$` | `^10\.\d{4,}/.+$` | `^10\.\d{4,}/.+$` |
| **DQ regex** | `^10\.\d{4,}/.*$` | `^10\.\d{4,}/.*$` | `^10\.\d{4,}/.*$` | `^10\.\d{4,}/.*$` | `^10\.\d{4,}/.*$` |
| **Gold** | nullable=True, **нет regex** | nullable=False, **нет regex** | nullable=True, **нет regex** | nullable=True, **нет regex** | — |

**Выявленные проблемы:**
1. **Regex `.+` vs `.*`:** Silver schema требует ≥1 символ после `/` (`/.+$`), но DQ-правила допускают пустую строку после `/` (`/.*$`). DOI вида `10.1234/` пройдёт DQ, но упадёт на Silver.
2. **Механизм валидации:** PubMed использует `@pa.check` (метод класса), остальные — `str_matches` (параметр Field). Семантически одинаково, но стилистически неконсистентно и усложняет поддержку.
3. **Gold теряет regex:** ни одна Gold-схема не валидирует формат DOI — невалидный DOI может попасть в Gold слой.
4. **CrossRef: nullable=False** — единственный провайдер с обязательным DOI, что корректно (DOI = primary key для CrossRef).

**План унификации:**

| # | Действие | Приоритет | Файлы |
|---|----------|-----------|-------|
| 1 | Исправить DQ regex: `^10\.\d{4,}/.+$` (`.+` вместо `.*`) для согласованности с Silver | HIGH | все `configs/dq/entities/*/publication.yaml` |
| 2 | PubMed Silver: заменить `@pa.check` на `str_matches=DOI_REGEX_PATTERN` для единообразия с другими провайдерами | MEDIUM | `schemas/pubmed/publication.py` |
| 3 | Добавить DOI regex validation в Gold-схемы (хотя бы для CrossRef, где DOI — PK) | MEDIUM | `contracts/gold/publications.py` |

---

### D-03. `title` — расхождение nullable и Silver→Gold регрессия

| Слой | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|------|--------|----------|----------|------------------|--------|
| **Silver nullable** | **False** (required) | True | True | True | True |
| **Silver check** | `len ≥ 1` (`@pa.check`) | — | — | — | — |
| **DQ max length** | `≤2000 chars` | `≤2000 chars` | `≤2000 chars` | `≤2000 chars` | **нет правила** |
| **Gold nullable** | **True** | True | True | True | — |

**Выявленные проблемы:**
1. **Silver→Gold регрессия (PubMed):** Silver требует `title` (nullable=False), но Gold разрешает NULL (nullable=True). Запись без title не пройдёт Silver, но Gold-схема этого не гарантирует — если данные попадут в Gold минуя Silver, инвариант нарушится.
2. **DQ max length отсутствует для ChEMBL:** 4 из 5 провайдеров ограничивают title до 2000 символов, ChEMBL — нет.
3. **Только PubMed проверяет non-empty:** Остальные провайдеры допускают пустую строку `""` как title.

**План унификации:**

| # | Действие | Приоритет | Файлы |
|---|----------|-----------|-------|
| 1 | Gold PubMed: установить `nullable=False` для `title` (соответствие Silver) | HIGH | `contracts/gold/publications.py` |
| 2 | Добавить DQ-правило `title ≤2000 chars` для ChEMBL | MEDIUM | `configs/dq/entities/chembl/publication.yaml` |
| 3 | Рассмотреть non-empty check для всех провайдеров в base schema или DQ: пустой title бессмыслен | LOW | `publication_base.py` или DQ YAML |

---

### D-04. `_source` — расхождение nullable и eq-constraints

| Слой | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|------|--------|----------|----------|------------------|--------|
| **Silver nullable** | True (base) | **False** | **False** | **False** | **False** |
| **Silver eq** | — | `eq="crossref"` | — | `eq="semanticscholar"` | `default="chembl"` |
| **Gold nullable** | True | **True** | **False** | **True** | — |
| **Gold eq** | — | — | — | — | — |

**Выявленные проблемы:**
1. **PubMed Silver: nullable=True** — единственный провайдер, не требующий `_source`. Все остальные требуют.
2. **Silver→Gold регрессия:** CrossRef и S2 требуют `_source` в Silver (nullable=False), но Gold делает его optional (nullable=True). Инвариант «источник данных всегда известен» не гарантирован в Gold.
3. **Неконсистентные eq-constraints:** CrossRef и S2 фиксируют значение через `eq`, OpenAlex и ChEMBL — нет (хотя должны иметь фиксированное значение). ChEMBL использует `default` вместо `eq`.
4. **Gold полностью теряет eq-constraints:** ни одна Gold-схема не проверяет значение `_source`.

**План унификации:**

| # | Действие | Приоритет | Файлы |
|---|----------|-----------|-------|
| 1 | PubMed Silver: переопределить `_source` как nullable=False (все провайдеры должны иметь источник) | HIGH | `schemas/pubmed/publication.py` |
| 2 | OpenAlex Silver: добавить `eq="openalex"` | MEDIUM | `schemas/openalex/publication.py` |
| 3 | ChEMBL Silver: заменить `default="chembl"` на `eq="chembl"` для строгой валидации | MEDIUM | `schemas/chembl/publication.py` |
| 4 | Все Gold-схемы: установить `nullable=False` для `_source` | HIGH | `contracts/gold/publications.py` |
| 5 | Рассмотреть вынос `_source` в base как nullable=False (после п.1) | LOW | `publication_base.py` |

---

### D-05. `_lookup_method` — расхождение nullable и потеря isin в Gold

| Слой | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|------|--------|----------|----------|------------------|--------|
| **Silver nullable** | True (base) | True (base) | **False** | **False** | **False** |
| **Silver isin** | LOOKUP_METHODS | LOOKUP_METHODS | LOOKUP_METHODS | LOOKUP_METHODS | LOOKUP_METHODS |
| **Gold nullable** | True | True | **False** | **True** | — |
| **Gold isin** | **нет** | **нет** | **нет** | **нет** | — |

**Выявленные проблемы:**
1. **Silver nullable разнобой:** PubMed и CrossRef наследуют nullable=True из base, OpenAlex/S2/ChEMBL переопределяют как nullable=False. Все enricher-пайплайны (CrossRef, OpenAlex, S2) должны знать метод поиска.
2. **Gold S2 регрессия:** Silver требует `_lookup_method` (nullable=False), Gold разрешает NULL (nullable=True).
3. **Gold полностью теряет enum-валидацию:** ни одна Gold-схема не использует `isin=LOOKUP_METHODS` — произвольное значение метода будет принято.

**План унификации:**

| # | Действие | Приоритет | Файлы |
|---|----------|-----------|-------|
| 1 | PubMed и CrossRef Silver: переопределить как nullable=False (lookup_method всегда должен быть известен) | HIGH | `schemas/pubmed/publication.py`, `schemas/crossref/publication.py` |
| 2 | Или: изменить nullable=False в base schema (если все провайдеры поддерживают) | HIGH | `publication_base.py` |
| 3 | Gold S2: установить nullable=False | HIGH | `contracts/gold/publications.py` |
| 4 | Все Gold-схемы: добавить isin-валидацию для `_lookup_method` | MEDIUM | `contracts/gold/publications.py` |

---

### D-06. `publication_type` — разные enum-наборы, разная семантика

| Слой | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|------|--------|----------|----------|------------------|--------|
| **Silver schema** | nullable=True, нет enum | nullable=True, нет enum | nullable=True, нет enum | nullable=True, нет enum | nullable=True, **isin: [PUBLICATION, PATENT, DATASET, BOOK]** |
| **DQ enum** | [Journal Article, Review, Letter, Editorial, Clinical Trial, Meta-Analysis, Case Reports, Comparative Study, Evaluation Study] | [journal-article, book-chapter, proceedings-article, posted-content, book, report, dataset, standard] | [article, book-chapter, book, dataset, dissertation, editorial, letter, review, preprint, other] | — (нет DQ enum) | [PUBLICATION, BOOK, DATASET, PATENT] |
| **Gold schema** | nullable=True, нет enum | nullable=True, нет enum | nullable=True, нет enum | nullable=True, нет enum | — |

**Выявленные проблемы:**
1. **Семантический разнобой:** Каждый провайдер использует свой набор типов документов. PubMed — заглавные с пробелами (`Journal Article`), CrossRef — kebab-case (`journal-article`), OpenAlex — lowercase (`article`), ChEMBL — UPPER_CASE (`PUBLICATION`).
2. **Только ChEMBL имеет enum в Silver:** Остальные провайдеры полагаются только на DQ-правила для enum-валидации.
3. **DQ использует raw API имена полей:** PubMed DQ проверяет `pub_type`, CrossRef — `type`, OpenAlex — `type`. Это имена исходных полей API, не унифицированного `publication_type`. Эффективность этих DQ-правил зависит от момента маппинга.
4. **S2 не имеет DQ enum** вообще.
5. **Gold не валидирует тип** ни для одного провайдера.

**План унификации:**

| # | Действие | Приоритет | Файлы |
|---|----------|-----------|-------|
| 1 | Определить единую таксономию типов публикаций и маппинг для каждого провайдера (например: `ARTICLE`, `REVIEW`, `BOOK`, `BOOK_CHAPTER`, `DATASET`, `PREPRINT`, `PATENT`, `EDITORIAL`, `LETTER`, `OTHER`) | HIGH | Новый маппинг в `domain/mapping/` или `domain/types.py` |
| 2 | Добавить enum-валидацию (isin) в Silver base schema для унифицированных типов | MEDIUM | `publication_base.py` |
| 3 | Обновить трансформеры для маппинга raw типов в унифицированные | HIGH | Трансформеры каждого провайдера |
| 4 | Обновить DQ-правила: использовать unified field name `publication_type` вместо raw API names | MEDIUM | `configs/dq/entities/*/publication.yaml` |
| 5 | Добавить DQ enum для S2 | LOW | `configs/dq/entities/semanticscholar/publication.yaml` |

---

### D-07. `language` — валидация только в PubMed, потеря в Gold

| Слой | PubMed | CrossRef | OpenAlex |
|------|--------|----------|----------|
| **Silver** | nullable=True, **check: len 2-3** (MARC code) | nullable=True, нет валидации (base) | nullable=True, нет валидации (base) |
| **Gold** | nullable=True, **нет валидации** | nullable=True, нет валидации | nullable=True, нет валидации |

*S2 и ChEMBL не имеют поля `language`.*

**Выявленные проблемы:**
1. **Только PubMed валидирует длину:** CrossRef и OpenAlex могут содержать произвольные строки в `language`.
2. **PubMed теряет check в Gold:** Silver проверяет len 2-3, Gold — нет.
3. **Нет стандартизации формата:** PubMed использует MARC-коды (3 символа, например `eng`), CrossRef и OpenAlex могут использовать ISO 639-1 (2 символа, например `en`) или другие форматы.

**План унификации:**

| # | Действие | Приоритет | Файлы |
|---|----------|-----------|-------|
| 1 | Перенести check `len 2-3` в base schema (все провайдеры, возвращающие language, должны иметь корректный код) | MEDIUM | `publication_base.py` |
| 2 | Стандартизировать на ISO 639-1 (2-char) или ISO 639-3 (3-char). Предлагается ISO 639-3 (3-char) как более полный | LOW | Трансформеры + base schema |
| 3 | Добавить length check в Gold PubMed для консистентности с Silver | LOW | `contracts/gold/publications.py` |

---

### D-08. `issn` — разный механизм валидации, потеря regex в Gold

| Слой | PubMed | CrossRef | OpenAlex |
|------|--------|----------|----------|
| **Silver механизм** | `@pa.check` (метод класса) | `str_matches=ISSN_PATTERN` (Field param, из constants) | `str_matches` (inline regex) |
| **Silver regex** | `^\d{4}-\d{3}[\dX]$` | `^\d{4}-\d{3}[\dX]$` | `^\d{4}-\d{3}[\dX]$` |
| **Gold** | nullable=True, **нет regex** | nullable=True, **нет regex** | nullable=True, **нет regex** |

*S2 и ChEMBL не имеют поля `issn`.*

**Выявленные проблемы:**
1. **Три разных механизма для одного regex:** PubMed использует `@pa.check`, CrossRef — ссылку на константу, OpenAlex — inline regex. Regex идентичен, но стиль неконсистентен.
2. **Gold полностью теряет ISSN validation:** невалидный ISSN может попасть в Gold слой.

**План унификации:**

| # | Действие | Приоритет | Файлы |
|---|----------|-----------|-------|
| 1 | Унифицировать механизм: все провайдеры должны использовать `str_matches=ISSN_PATTERN` (из constants.py) | MEDIUM | `schemas/pubmed/publication.py`, `schemas/openalex/publication.py` |
| 2 | PubMed: заменить `@pa.check` на `str_matches=ISSN_PATTERN` | LOW | `schemas/pubmed/publication.py` |
| 3 | OpenAlex: заменить inline regex на ссылку `ISSN_PATTERN` из constants.py | LOW | `schemas/openalex/publication.py` |

---

### D-09. `pmid` — расхождение nullable, regex, тип валидации

| Слой | PubMed (как PK) | OpenAlex / S2 / ChEMBL (как cross-ref) | DQ PubMed | DQ ChEMBL |
|------|-----------------|----------------------------------------|-----------|-----------|
| **Silver nullable** | **False** | True (base) | — | — |
| **Silver type** | str | str | — | — |
| **Silver regex** | `^\d+$` (str_matches) + `^[1-9]\d*$` (@pa.check) | `^[1-9]\d*$` (base str_matches) | — | — |
| **DQ** | — | — | range `[1, 100_000_000]` (numeric) | range `[1, 100_000_000]` (as `pubmed_id`) |
| **Gold** | str, nullable=False, **нет regex** | str, nullable=True, **нет regex** | — | — |

**Выявленные проблемы:**
1. **PubMed двойной regex:** Silver PubMed сначала проверяет `^\d+$` (включая `0`), затем через check `^[1-9]\d*$` (исключая `0`). Первый regex избыточен — `^[1-9]\d*$` уже подразумевает `^\d+$`.
2. **DQ использует numeric range вместо regex:** DQ проверяет `[1, 100_000_000]` как число, Silver проверяет regex. Семантически это ограничивает PMID до 100M, что может быть слишком строго в будущем.
3. **DQ ChEMBL использует имя `pubmed_id`, не `pmid`:** Несоответствие имени поля.
4. **Gold теряет все regex:** PMID валидируется только по типу `str` и nullable.

**План унификации:**

| # | Действие | Приоритет | Файлы |
|---|----------|-----------|-------|
| 1 | PubMed Silver: убрать `str_matches=r"^\d+$"`, оставить только `@pa.check` с `^[1-9]\d*$` | LOW | `schemas/pubmed/publication.py` |
| 2 | Согласовать имя поля в DQ ChEMBL: `pubmed_id` → `pmid` (если DQ работает с unified names) или документировать маппинг | MEDIUM | `configs/dq/entities/chembl/publication.yaml` |
| 3 | DQ: увеличить max до `999_999_999` или убрать верхнюю границу (PMID — автоинкрементный ID) | LOW | DQ YAML файлы |

---

### D-10. `is_retracted` — Silver→Gold регрессия

| Слой | OpenAlex |
|------|----------|
| **Silver** | **nullable=False** (required, bool) |
| **Gold** | nullable=**True**, coerce=True |

*Поле присутствует только в OpenAlex.*

**Выявленные проблемы:**
1. **Регрессия:** Silver гарантирует, что `is_retracted` всегда заполнен, но Gold допускает NULL. Это критичный quality indicator — потеря значения может привести к использованию ретрактированных публикаций.

**План унификации:**

| # | Действие | Приоритет | Файлы |
|---|----------|-----------|-------|
| 1 | Gold OpenAlex: установить `nullable=False` для `is_retracted` | **CRITICAL** | `contracts/gold/publications.py` |

---

### D-11. `citations_received` — неравномерное покрытие DQ

| Слой | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|------|--------|----------|----------|------------------|--------|
| **Silver** | Int64, `≥0` (base) | Int64, `≥0` (base) | Int64, `≥0` (base) | Int64, `≥0` (base) | Int64, `≥0` (base) |
| **DQ поле** | **нет правила** | `is_referenced_by_count` | `cited_by_count` | `citation_count` | **нет правила** |
| **DQ min** | — | 0 | 0 | 0 | — |
| **Gold** | **не в схеме** | float, `≥0`, coerce | float, `≥0`, coerce | float, `≥0`, coerce | — |

**Выявленные проблемы:**
1. **DQ field names не унифицированы:** CrossRef использует `is_referenced_by_count`, OpenAlex — `cited_by_count`, S2 — `citation_count`. Это raw API имена, не unified `citations_received`.
2. **PubMed и ChEMBL не имеют DQ-правила:** Хотя поле наследуется из base, DQ-проверка не дублирует schema validation для этих провайдеров.
3. **PubMed Gold не содержит поле:** `citations_received` отсутствует в `PubMedPublicationGoldSchema` (PubMed API не предоставляет метрики цитирования). Это корректно.

**План унификации:**

| # | Действие | Приоритет | Файлы |
|---|----------|-----------|-------|
| 1 | Унифицировать DQ field names: использовать `citations_received` (unified name) вместо raw API names, либо документировать маппинг DQ field → schema field | MEDIUM | `configs/dq/entities/*/publication.yaml` |
| 2 | Добавить DQ-правило для ChEMBL если `citations_received` может быть заполнен (или документировать, что ChEMBL не предоставляет метрики) | LOW | `configs/dq/entities/chembl/publication.yaml` |

---

### D-12. `oa_status` — потеря enum-валидации в Gold

| Слой | OpenAlex | Semantic Scholar |
|------|----------|------------------|
| **Silver** | nullable=True, **isin: [gold, green, hybrid, bronze, closed]** | nullable=True, **isin: [gold, green, hybrid, bronze, closed]** |
| **Gold** | nullable=True, **нет isin** | nullable=True, **нет isin** |

**Выявленные проблемы:**
1. **Gold теряет enum-валидацию:** Silver гарантирует одно из 5 значений, Gold принимает любую строку.

**План унификации:**

| # | Действие | Приоритет | Файлы |
|---|----------|-----------|-------|
| 1 | Добавить isin-валидацию в Gold-схемы для `oa_status` | LOW | `contracts/gold/publications.py` |

---

### D-13. `author_orcid_list` vs `author_orcids` — расхождение имён одного концепта

Не расхождение валидации, но расхождение **именования** одного концепта:

| Провайдер | Поле | ORCID Validation |
|-----------|------|------------------|
| CrossRef | `author_orcid_list` | `@pa.check` JSON array с ORCID regex |
| OpenAlex | `author_orcids` | `@pa.check` JSON array с ORCID regex |
| Semantic Scholar | `author_orcids` | `@pa.check` JSON array с ORCID regex |

**Проблема:** CrossRef использует `author_orcid_list`, а OpenAlex и S2 — `author_orcids`. Код кастомной проверки идентичен.

**План унификации:**

| # | Действие | Приоритет | Файлы |
|---|----------|-----------|-------|
| 1 | Решить на едином имени: `author_orcids` (2 из 3 провайдеров уже используют) | MEDIUM | CrossRef Silver + Gold schemas, трансформер |
| 2 | Вынести общий ORCID check в base schema или shared mixin | LOW | `publication_base.py` или `schemas/common/` |

---

## Сводная матрица расхождений

| ID | Поле | Тип расхождения | Severity | Затронутые провайдеры |
|----|------|-----------------|----------|----------------------|
| D-01 | `publication_year` | Диапазоны: 4 варианта, Gold без range | HIGH | Все 5 |
| D-02 | `doi` | Nullable, механизм, `.+` vs `.*`, Gold без regex | HIGH | Все 5 |
| D-03 | `title` | Nullable Silver→Gold регрессия (PubMed) | HIGH | PubMed + ChEMBL (DQ gap) |
| D-04 | `_source` | Nullable + eq разнобой, Silver→Gold регрессия | HIGH | CrossRef, S2 (регрессия); PubMed, OpenAlex, ChEMBL (eq gap) |
| D-05 | `_lookup_method` | Nullable разнобой, Gold без isin | MEDIUM | PubMed, CrossRef (nullable); S2 (регрессия) |
| D-06 | `publication_type` | Разные enum, разные форматы | MEDIUM | Все 5 |
| D-07 | `language` | Check только в PubMed, нет стандартизации | LOW | PubMed, CrossRef, OpenAlex |
| D-08 | `issn` | Разный механизм, Gold без regex | LOW | PubMed, CrossRef, OpenAlex |
| D-09 | `pmid` | Двойной regex, DQ name mismatch | LOW | PubMed, ChEMBL (DQ) |
| D-10 | `is_retracted` | **Silver→Gold регрессия** | **CRITICAL** | OpenAlex |
| D-11 | `citations_received` | DQ names не унифицированы | LOW | CrossRef, OpenAlex, S2 |
| D-12 | `oa_status` | Gold без enum | LOW | OpenAlex, S2 |
| D-13 | `author_orcid*` | Расхождение именования | MEDIUM | CrossRef vs OpenAlex/S2 |

---

## Приоритеты исправления

### CRITICAL (исправить немедленно)

- **D-10:** `is_retracted` Silver→Gold регрессия — OpenAlex Gold допускает NULL для критичного quality indicator

### HIGH (следующий спринт)

- **D-01:** Унификация диапазона `publication_year` — 4 разных варианта на 3 слоях
- **D-02:** Унификация DOI regex (`.+` vs `.*`) — DQ пропускает невалидные DOI
- **D-03:** `title` nullable регрессия в Gold PubMed
- **D-04:** `_source` nullable/eq унификация — Silver→Gold регрессия для CrossRef и S2

### MEDIUM (плановый рефакторинг)

- **D-05:** `_lookup_method` nullable унификация + isin в Gold
- **D-06:** `publication_type` единая таксономия
- **D-13:** `author_orcid*` именование → `author_orcids`

### LOW (tech debt)

- **D-07:** `language` — length check в base + стандартизация формата
- **D-08:** `issn` — унификация механизма (str_matches из constants)
- **D-09:** `pmid` — убрать избыточный regex, согласовать DQ field name
- **D-11:** `citations_received` — унифицировать DQ field names
- **D-12:** `oa_status` — добавить isin в Gold

---

## Источники

| Файл | Назначение |
|------|------------|
| `src/bioetl/domain/schemas/common/publication_base.py` | Базовая схема для всех publication |
| `src/bioetl/domain/schemas/pubmed/publication.py` | PubMed Silver schema |
| `src/bioetl/domain/schemas/crossref/publication.py` | CrossRef Silver schema |
| `src/bioetl/domain/schemas/openalex/publication.py` | OpenAlex Silver schema |
| `src/bioetl/domain/schemas/semanticscholar/publication.py` | Semantic Scholar Silver schema |
| `src/bioetl/domain/schemas/chembl/publication.py` | ChEMBL Publication Silver schema |
| `src/bioetl/domain/schemas/chembl/publication_term.py` | ChEMBL Publication Term Silver schema |
| `src/bioetl/domain/contracts/gold/publications.py` | Все Gold-схемы publication |
| `src/bioetl/domain/schemas/constants.py` | Regex-паттерны и enum-значения |
| `src/bioetl/domain/validation.py` | Константы и функции валидации |
| `configs/dq/entities/*/publication.yaml` | DQ-правила по провайдерам |
| `configs/dq/entities/chembl/publication_term.yaml` | DQ-правила для publication_term |
