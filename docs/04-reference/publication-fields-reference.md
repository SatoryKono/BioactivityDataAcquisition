# Справочник полей публикаций (Publication Fields Reference)

**Версия:** 1.0.0
**Дата:** 2026-02-06
**Источник:** `publication_validation_schema_v3.xlsx`
**Охват:** 191 поле × 5 провайдеров

---

## Содержание

1. [Обзор](#обзор)
2. [Общая статистика](#общая-статистика)
3. [Общие поля базовой схемы](#общие-поля-базовой-схемы)
4. [ChEMBL](#chembl)
5. [PubMed](#pubmed)
6. [CrossRef](#crossref)
7. [OpenAlex](#openalex)
8. [Semantic Scholar](#semantic-scholar)
9. [Легенда символов](#легенда-символов)

---

## Обзор

Данный справочник содержит детальное описание всех **191 полей** из пяти провайдеров биомедицинских публикаций:

- **ChEMBL** — база данных биоактивных молекул (EMBL-EBI)
- **PubMed** — база медицинских и life sciences публикаций (NCBI)
- **CrossRef** — агрегатор метаданных научных публикаций (DOI authority)
- **OpenAlex** — открытая база научных публикаций и цитирований
- **Semantic Scholar** — AI-платформа для научных публикаций (Allen Institute)

Каждое поле описано с точки зрения:
- **Тип данных** (string, integer, boolean, date)
- **Nullable** (допускается NULL или нет)
- **Regex** (регулярное выражение для валидации формата)
- **Primary Key** (первичный ключ провайдера)
- **Категория** (группировка по назначению)

---

## Общая статистика

| Провайдер | Кол-во полей | Primary Key | Non-nullable | Nullable |
|-----------|--------------|-------------|--------------|----------|
| **ChEMBL** | 28 | `document_chembl_id` | 1 | 27 |
| **PubMed** | 52 | `pmid` | 1 | 51 |
| **CrossRef** | 37 | `doi` | 1 | 36 |
| **OpenAlex** | 39 | `openalex_id` | 1 | 38 |
| **Semantic Scholar** | 35 | `paper_id` | 1 | 34 |
| **ИТОГО** | **191** | — | **5** | **186** |

**Важно:**
- ⭐ — Primary Key (первичный ключ, non-nullable)
- ✅ — Nullable (допускается NULL)
- ❌ — Non-nullable (обязательное поле)

---

## Общие поля базовой схемы

Эти поля наследуются всеми провайдерами от `PublicationBaseSchema` и присутствуют в каждой записи:

| Поле | Тип | Nullable | Описание |
|------|-----|----------|----------|
| `title` | string/integer/boolean | nullable | Заголовок публикации |
| `abstract` | string/integer/boolean | nullable | Аннотация (краткое содержание) |
| `authors` | string/integer/boolean | nullable | Список авторов (JSON/CSV) |
| `journal` | string/integer/boolean | nullable | Название журнала |
| `publication_year` | string/integer/boolean | nullable | Год публикации |
| `publication_date` | string/integer/boolean | nullable | Дата публикации (YYYY-MM-DD) |
| `_source` | string/integer/boolean | nullable | Провайдер-источник (chembl, pubmed, crossref, openalex, semanticscholar) |
| `lookup_method` | string/integer/boolean | nullable | Метод извлечения записи (api, direct, cached) |
| `original_id` | string/integer/boolean | nullable | Исходный идентификатор записи у провайдера |
| `_dq_warn` | string/integer/boolean | nullable | DQ флаг: запись прошла с предупреждениями |
| `_dq_error` | string/integer/boolean | nullable | DQ флаг: запись заблокирована из-за критической ошибки |
| `content_hash` | string/integer/boolean | nullable | SHA-256 хеш контента для дедупликации |

**Примечания:**
- `_source` — фиксированное значение, соответствует провайдеру (`chembl`, `pubmed`, `crossref`, `openalex`, `semanticscholar`)
- `content_hash` — SHA-256 хеш полей `[title, abstract, authors, publication_year, journal, doi]` для детерминированной дедупликации
- `_dq_warn`, `_dq_error` — устанавливаются автоматически валидационным пайплайном (ADR-027)

---

## ChEMBL

**Кол-во полей:** 28 | **Primary Key:** `document_chembl_id`

### Идентификаторы и статусы

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `pmid` | string | ✅ | — | `^[1-9]\d*$ (positive integer)` |  |
| `doi` | string | ✅ | — | `^10\.\d{4,9}/.+$` |  |
| `pmc_id` | string | ✅ | — | `^PMC\d+$` |  |
| `publication_type` | string | ✅ | — | — |  |
| `is_oa` | boolean | ✅ | — | — |  |
| `document_chembl_id` | string | ❌ | Primary key for chembl; | `^CHEMBL\d+$` | ⭐ |
| `chembl_release` | string | ✅ | — | — |  |

### Библиографическая информация

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `title` | string | ✅ | — | — |  |
| `abstract` | string | ✅ | — | — |  |
| `journal` | string | ✅ | — | — |  |
| `page_first` | string | ✅ | — | — |  |
| `page_last` | string | ✅ | — | — |  |
| `volume` | string | ✅ | — | — |  |
| `issue` | string | ✅ | — | — |  |

### Авторы и аффилиации

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `authors` | string | ✅ | — | — |  |
| `affiliation_list` | string | ✅ | — | — |  |

### Даты и места публикации

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `publication_year` | integer | ✅ | — | — |  |
| `publication_date` | string | ✅ | — | `^\d{4}-\d{2}-\d{2}$` |  |
| `creation_date` | string | ✅ | — | `^\d{4}-\d{2}-\d{2}$` |  |

### Цитирования и ссылки

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `citations_received` | integer | ✅ | — | — |  |
| `citations_made` | integer | ✅ | — | — |  |

### Технические/устаревшие поля

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `language` | string | ✅ | — | — |  |
| `lookup_method` | string | ✅ | Tracking field for record resolution strategy | — |  |
| `original_id` | string | ✅ | — | — |  |
| `_source` | string | ✅ | Fixed value: 'chembl' | — |  |
| `src_id` | integer | ✅ | — | — |  |
| `_dq_warn` | boolean | ✅ | DQ flag field; auto-set by validation pipeline | — |  |
| `_dq_error` | boolean | ✅ | DQ flag field; auto-set by validation pipeline | — |  |

---

## PubMed

**Кол-во полей:** 52 | **Primary Key:** `pmid`

### Идентификаторы и статусы

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `pmid` | string | ❌ | Primary key for pubmed; | `^[1-9]\d*$ (positive integer)` | ⭐ |
| `doi` | string | ✅ | — | `^10\.\d{4,9}/.+$` |  |
| `pmc_id` | string | ✅ | — | `^PMC\d+$` |  |
| `publication_type` | string | ✅ | — | — |  |
| `is_oa` | boolean | ✅ | — | — |  |
| `nlm_unique_id` | string | ✅ | — | — |  |
| `publication_status` | string | ✅ | — | — |  |

### Библиографическая информация

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `title` | string | ✅ | — | — |  |
| `abstract` | string | ✅ | — | — |  |
| `journal` | string | ✅ | — | — |  |
| `page_first` | string | ✅ | — | — |  |
| `page_last` | string | ✅ | — | — |  |
| `abstract_structured` | boolean | ✅ | — | — |  |
| `journal_name_short` | string | ✅ | — | — |  |
| `journal_iso_abbrev` | string | ✅ | — | — |  |
| `issn` | string | ✅ | — | `^\d{4}-\d{3}[\dX]$` |  |
| `journal_issn_type` | string | ✅ | — | `^\d{4}-\d{3}[\dX]$` |  |
| `page_range` | string | ✅ | — | — |  |

### Авторы и аффилиации

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `authors` | string | ✅ | — | — |  |
| `affiliation_list` | string | ✅ | — | — |  |
| `affiliation_structured` | string | ✅ | — | — |  |
| `author_count` | integer | ✅ | — | — |  |
| `authors_with_affiliations` | string | ✅ | — | — |  |

### Даты и места публикации

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `publication_year` | integer | ✅ | — | — |  |
| `publication_date` | string | ✅ | — | `^\d{4}-\d{2}-\d{2}$` |  |
| `country` | string | ✅ | — | — |  |
| `pub_month` | integer | ✅ | — | — |  |
| `pub_day` | integer | ✅ | — | — |  |
| `date_completed` | date | ✅ | — | — |  |
| `date_revised` | date | ✅ | — | — |  |

### Цитирования и ссылки

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `citations_received` | integer | ✅ | — | — |  |
| `citations_made` | integer | ✅ | — | — |  |
| `grant_count` | integer | ✅ | — | — |  |

### Технические/устаревшие поля

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `language` | string | ✅ | — | — |  |
| `lookup_method` | string | ✅ | Tracking field for record resolution strategy | — |  |
| `original_id` | string | ✅ | — | — |  |
| `_source` | string | ✅ | Fixed value: 'pubmed' | — |  |
| `pii` | string | ✅ | — | — |  |
| `mid` | string | ✅ | — | — |  |
| `publisher_id` | string | ✅ | — | — |  |
| `medline_pgn` | string | ✅ | — | — |  |

---

## CrossRef

**Кол-во полей:** 37 | **Primary Key:** `doi`

### Идентификаторы и статусы

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `pmid` | string | ✅ | — | `^[1-9]\d*$ (positive integer)` |  |
| `doi` | string | ❌ | Primary key for crossref; | `^10\.\d{4,9}/.+$` | ⭐ |
| `pmc_id` | string | ✅ | — | `^PMC\d+$` |  |
| `publication_type` | string | ✅ | — | — |  |
| `is_oa` | boolean | ✅ | — | — |  |
| `alternative_id` | JSON object | ✅ | — | — |  |

### Библиографическая информация

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `title` | string | ✅ | — | — |  |
| `abstract` | string | ✅ | — | — |  |
| `journal` | string | ✅ | — | — |  |
| `page_first` | string | ✅ | — | — |  |
| `page_last` | string | ✅ | — | — |  |
| `issn` | string | ✅ | — | `^\d{4}-\d{3}[\dX]$` |  |
| `issn_list` | string | ✅ | — | `^\d{4}-\d{3}[\dX]$` |  |
| `publisher` | string | ✅ | — | — |  |
| `journal_name_short` | string | ✅ | — | — |  |
| `issn_print` | string | ✅ | — | `^\d{4}-\d{3}[\dX]$` |  |
| `issn_electronic` | string | ✅ | — | `^\d{4}-\d{3}[\dX]$` |  |

### Авторы и аффилиации

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `authors` | string | ✅ | — | — |  |
| `affiliation_list` | string | ✅ | — | — |  |
| `author_orcid_list` | string | ✅ | — | `^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$` |  |

### Даты и места публикации

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `publication_year` | integer | ✅ | — | — |  |
| `publication_date` | string | ✅ | — | `^\d{4}-\d{2}-\d{2}$` |  |
| `published_print` | string | ✅ | — | — |  |
| `published_online` | string | ✅ | — | — |  |
| `published` | string | ✅ | — | — |  |

### Цитирования и ссылки

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `citations_received` | integer | ✅ | — | — |  |
| `citations_made` | integer | ✅ | — | — |  |
| `references` | string | ✅ | — | — |  |

### Технические/устаревшие поля

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `language` | string | ✅ | — | — |  |
| `lookup_method` | string | ✅ | Tracking field for record resolution strategy | — |  |
| `original_id` | string | ✅ | — | — |  |
| `_source` | string | ✅ | Fixed value: 'crossref' | — |  |
| `license_url` | string | ✅ | — | — |  |
| `content_domain_domains` | JSON object | ✅ | — | — |  |
| `content_domain_crossmark_restriction` | boolean | ✅ | — | — |  |
| `author_details` | string | ✅ | — | — |  |

---

## OpenAlex

**Кол-во полей:** 39 | **Primary Key:** `openalex_id`

### Идентификаторы и статусы

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `pmid` | string | ✅ | — | `^[1-9]\d*$ (positive integer)` |  |
| `doi` | string | ✅ | — | `^10\.\d{4,9}/.+$` |  |
| `pmc_id` | string | ✅ | — | `^PMC\d+$` |  |
| `publication_type` | string | ✅ | — | — |  |
| `is_oa` | boolean | ✅ | — | — |  |
| `openalex_id` | string | ❌ | Primary key for openalex; | `^W\d+$` | ⭐ |
| `oa_status` | string | ✅ | — | — |  |
| `is_retracted` | boolean | ✅ | — | — |  |
| `mag_id` | string | ✅ | — | — |  |

### Библиографическая информация

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `title` | string | ✅ | — | — |  |
| `abstract` | string | ✅ | — | — |  |
| `journal` | string | ✅ | — | — |  |
| `page_first` | string | ✅ | — | — |  |
| `page_last` | string | ✅ | — | — |  |
| `issn` | string | ✅ | — | `^\d{4}-\d{3}[\dX]$` |  |
| `publisher` | string | ✅ | — | — |  |
| `volume` | string | ✅ | — | — |  |
| `issue` | string | ✅ | — | — |  |

### Авторы и аффилиации

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `authors` | string | ✅ | — | — |  |
| `affiliation_list` | string | ✅ | — | — |  |
| `author_orcids` | string | ✅ | — | `^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$` |  |
| `author_openalex_ids` | string | ✅ | — | — |  |
| `institution_ids` | string | ✅ | — | — |  |
| `ror_ids` | string | ✅ | — | — |  |

### Даты и места публикации

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `publication_year` | integer | ✅ | — | — |  |
| `publication_date` | string | ✅ | — | `^\d{4}-\d{2}-\d{2}$` |  |
| `institution_country_codes` | string | ✅ | — | — |  |

### Цитирования и ссылки

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `citations_received` | integer | ✅ | — | — |  |
| `citations_made` | integer | ✅ | — | — |  |
| `fwci` | float | ✅ | — | — |  |
| `grants` | string | ✅ | — | — |  |

### Технические/устаревшие поля

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `language` | string | ✅ | — | — |  |
| `lookup_method` | string | ✅ | Tracking field for record resolution strategy | — |  |
| `original_id` | string | ✅ | — | — |  |
| `_source` | string | ✅ | Fixed value: 'openalex' | — |  |

---

## Semantic Scholar

**Кол-во полей:** 35 | **Primary Key:** `paper_id`

### Идентификаторы и статусы

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `pmid` | string | ✅ | — | `^[1-9]\d*$ (positive integer)` |  |
| `doi` | string | ✅ | — | `^10\.\d{4,9}/.+$` |  |
| `pmc_id` | string | ✅ | — | `^PMC\d+$` |  |
| `publication_type` | string | ✅ | — | — |  |
| `is_oa` | boolean | ✅ | — | — |  |
| `paper_id` | string | ❌ | Primary key for semanticscholar; | `^[a-f0-9]{40}$` | ⭐ |
| `dblp_id` | string | ✅ | — | — |  |
| `corpus_id` | integer | ✅ | — | — |  |
| `open_access_url` | string | ✅ | — | — |  |
| `oa_status` | string | ✅ | — | — |  |

### Библиографическая информация

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `title` | string | ✅ | — | — |  |
| `abstract` | string | ✅ | — | — |  |
| `journal` | string | ✅ | — | — |  |
| `page_first` | string | ✅ | — | — |  |
| `page_last` | string | ✅ | — | — |  |
| `volume` | string | ✅ | — | — |  |
| `page_range` | string | ✅ | — | — |  |

### Авторы и аффилиации

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `authors` | string | ✅ | — | — |  |
| `affiliation_list` | string | ✅ | — | — |  |
| `author_s2_ids` | string | ✅ | — | — |  |
| `author_orcids` | string | ✅ | — | `^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$` |  |
| `author_h_indices` | string | ✅ | — | — |  |

### Даты и места публикации

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `publication_year` | integer | ✅ | — | — |  |
| `publication_date` | string | ✅ | — | `^\d{4}-\d{2}-\d{2}$` |  |

### Цитирования и ссылки

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `citations_received` | integer | ✅ | — | — |  |
| `citations_made` | integer | ✅ | — | — |  |
| `influential_citation_count` | integer | ✅ | — | — |  |
| `citation_contexts` | string | ✅ | — | — |  |

### Технические/устаревшие поля

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `language` | string | ✅ | — | — |  |
| `lookup_method` | string | ✅ | Tracking field for record resolution strategy | — |  |
| `original_id` | string | ✅ | — | — |  |
| `_source` | string | ✅ | Fixed value: 'semanticscholar' | — |  |

---


## Легенда символов

| Символ | Значение |
|--------|----------|
| ⭐ | Primary Key (первичный ключ провайдера) |
| ✅ | Nullable (допускается NULL) |
| ❌ | Non-nullable (обязательное поле) |
| `regex` | Регулярное выражение для валидации формата |
| — | Не применимо / информация отсутствует |

---

## Категории полей

| Категория | Описание |
|-----------|----------|
| **Идентификаторы и статусы** | Первичные ключи, DOI, PMID, статусные флаги |
| **Библиографическая информация** | Название журнала, том, выпуск, страницы |
| **Авторы и аффилиации** | Списки авторов, организации, ORCID |
| **Даты и места публикации** | Даты публикации, ревизий, страны |
| **Цитирования и ссылки** | Количество цитирований, ссылки на другие работы |
| **Метрики и импакт** | Impact Factor, h-index, FWCI, altmetrics |
| **Тематика и ключевые слова** | Ключевые слова, MeSH термины, предметные области |
| **Open Access** | Статус OA, лицензии, версии статей |
| **Финансирование** | Гранты, фонды, спонсоры |
| **Технические/устаревшие поля** | Устаревшие идентификаторы, служебные поля |

---

## Связанная документация

- **Validation Schema:** `docs/04-reference/schemas/publication_validation_schema_v3.xlsx`
- **ADR-033:** Стратегия валидации публикаций (`docs/02-architecture/decisions/ADR-033-publication-validation-strategy.md`)
- **Validation Guide:** `docs/03-guides/publication-validation-guide.md`
- **Тесты:** `tests_generated/` (471 тест, 64% покрытие)

---

**Версия документа:** 1.0.0
**Последнее обновление:** 2026-02-06
**Статус:** Готов к использованию ✅

