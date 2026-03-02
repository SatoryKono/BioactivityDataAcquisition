# Справочник полей публикаций (Publication Fields Reference)

**Версия:** 1.0.0
**Дата:** 2026-02-06
**Источник:** `publication-validation-schema-v3.xlsx`
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
| **ChEMBL** | 28 | `document-chembl-id` | 1 | 27 |
| **PubMed** | 52 | `pmid` | 1 | 51 |
| **CrossRef** | 37 | `doi` | 1 | 36 |
| **OpenAlex** | 39 | `openalex-id` | 1 | 38 |
| **Semantic Scholar** | 35 | `paper-id` | 1 | 34 |
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
| `publication-year` | string/integer/boolean | nullable | Год публикации |
| `publication-date` | string/integer/boolean | nullable | Дата публикации (YYYY-MM-DD) |
| `-source` | string/integer/boolean | nullable | Провайдер-источник (chembl, pubmed, crossref, openalex, semanticscholar) |
| `lookup-method` | string/integer/boolean | nullable | Метод извлечения записи (api, direct, cached) |
| `original-id` | string/integer/boolean | nullable | Исходный идентификатор записи у провайдера |
| `-dq-warn` | string/integer/boolean | nullable | DQ флаг: запись прошла с предупреждениями |
| `-dq-error` | string/integer/boolean | nullable | DQ флаг: запись заблокирована из-за критической ошибки |
| `content-hash` | string/integer/boolean | nullable | SHA-256 хеш контента для дедупликации |

**Примечания:**
- `-source` — фиксированное значение, соответствует провайдеру (`chembl`, `pubmed`, `crossref`, `openalex`, `semanticscholar`)
- `content-hash` — SHA-256 хеш полей `[title, abstract, authors, publication-year, journal, doi]` для детерминированной дедупликации
- `-dq-warn`, `-dq-error` — устанавливаются автоматически валидационным пайплайном (ADR-027)

---

## ChEMBL

**Кол-во полей:** 28 | **Primary Key:** `document-chembl-id`

### Идентификаторы и статусы

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `pmid` | string | ✅ | — | `^[1-9]\d*$ (positive integer)` |  |
| `doi` | string | ✅ | — | `^10\.\d{4,9}/.+$` |  |
| `pmc-id` | string | ✅ | — | `^PMC\d+$` |  |
| `publication-type` | string | ✅ | — | — |  |
| `is-oa` | boolean | ✅ | — | — |  |
| `document-chembl-id` | string | ❌ | Primary key for chembl; | `^CHEMBL\d+$` | ⭐ |
| `chembl-release` | string | ✅ | — | — |  |

### Библиографическая информация

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `title` | string | ✅ | — | — |  |
| `abstract` | string | ✅ | — | — |  |
| `journal` | string | ✅ | — | — |  |
| `page-first` | string | ✅ | — | — |  |
| `page-last` | string | ✅ | — | — |  |
| `volume` | string | ✅ | — | — |  |
| `issue` | string | ✅ | — | — |  |

### Авторы и аффилиации

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `authors` | string | ✅ | — | — |  |
| `affiliation-list` | string | ✅ | — | — |  |

### Даты и места публикации

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `publication-year` | integer | ✅ | — | — |  |
| `publication-date` | string | ✅ | — | `^\d{4}-\d{2}-\d{2}$` |  |
| `creation-date` | string | ✅ | — | `^\d{4}-\d{2}-\d{2}$` |  |

### Цитирования и ссылки

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `citations-received` | integer | ✅ | — | — |  |
| `citations-made` | integer | ✅ | — | — |  |

### Технические/устаревшие поля

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `language` | string | ✅ | — | — |  |
| `lookup-method` | string | ✅ | Tracking field for record resolution strategy | — |  |
| `original-id` | string | ✅ | — | — |  |
| `-source` | string | ✅ | Fixed value: 'chembl' | — |  |
| `src-id` | integer | ✅ | — | — |  |
| `-dq-warn` | boolean | ✅ | DQ flag field; auto-set by validation pipeline | — |  |
| `-dq-error` | boolean | ✅ | DQ flag field; auto-set by validation pipeline | — |  |

---

## PubMed

**Кол-во полей:** 52 | **Primary Key:** `pmid`

### Идентификаторы и статусы

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `pmid` | string | ❌ | Primary key for pubmed; | `^[1-9]\d*$ (positive integer)` | ⭐ |
| `doi` | string | ✅ | — | `^10\.\d{4,9}/.+$` |  |
| `pmc-id` | string | ✅ | — | `^PMC\d+$` |  |
| `publication-type` | string | ✅ | — | — |  |
| `is-oa` | boolean | ✅ | — | — |  |
| `nlm-unique-id` | string | ✅ | — | — |  |
| `publication-status` | string | ✅ | — | — |  |

### Библиографическая информация

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `title` | string | ✅ | — | — |  |
| `abstract` | string | ✅ | — | — |  |
| `journal` | string | ✅ | — | — |  |
| `page-first` | string | ✅ | — | — |  |
| `page-last` | string | ✅ | — | — |  |
| `abstract-structured` | boolean | ✅ | — | — |  |
| `journal-name-short` | string | ✅ | — | — |  |
| `journal-iso-abbrev` | string | ✅ | — | — |  |
| `issn` | string | ✅ | — | `^\d{4}-\d{3}[\dX]$` |  |
| `journal-issn-type` | string | ✅ | — | `^\d{4}-\d{3}[\dX]$` |  |
| `page-range` | string | ✅ | — | — |  |

### Авторы и аффилиации

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `authors` | string | ✅ | — | — |  |
| `affiliation-list` | string | ✅ | — | — |  |
| `affiliation-structured` | string | ✅ | — | — |  |
| `author-count` | integer | ✅ | — | — |  |
| `authors-with-affiliations` | string | ✅ | — | — |  |

### Даты и места публикации

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `publication-year` | integer | ✅ | — | — |  |
| `publication-date` | string | ✅ | — | `^\d{4}-\d{2}-\d{2}$` |  |
| `country` | string | ✅ | — | — |  |
| `pub-month` | integer | ✅ | — | — |  |
| `pub-day` | integer | ✅ | — | — |  |
| `date-completed` | date | ✅ | — | — |  |
| `date-revised` | date | ✅ | — | — |  |

### Цитирования и ссылки

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `citations-received` | integer | ✅ | — | — |  |
| `citations-made` | integer | ✅ | — | — |  |
| `grant-count` | integer | ✅ | — | — |  |

### Технические/устаревшие поля

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `language` | string | ✅ | — | — |  |
| `lookup-method` | string | ✅ | Tracking field for record resolution strategy | — |  |
| `original-id` | string | ✅ | — | — |  |
| `-source` | string | ✅ | Fixed value: 'pubmed' | — |  |
| `pii` | string | ✅ | — | — |  |
| `mid` | string | ✅ | — | — |  |
| `publisher-id` | string | ✅ | — | — |  |
| `medline-pgn` | string | ✅ | — | — |  |

---

## CrossRef

**Кол-во полей:** 37 | **Primary Key:** `doi`

### Идентификаторы и статусы

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `pmid` | string | ✅ | — | `^[1-9]\d*$ (positive integer)` |  |
| `doi` | string | ❌ | Primary key for crossref; | `^10\.\d{4,9}/.+$` | ⭐ |
| `pmc-id` | string | ✅ | — | `^PMC\d+$` |  |
| `publication-type` | string | ✅ | — | — |  |
| `is-oa` | boolean | ✅ | — | — |  |
| `alternative-id` | JSON object | ✅ | — | — |  |

### Библиографическая информация

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `title` | string | ✅ | — | — |  |
| `abstract` | string | ✅ | — | — |  |
| `journal` | string | ✅ | — | — |  |
| `page-first` | string | ✅ | — | — |  |
| `page-last` | string | ✅ | — | — |  |
| `issn` | string | ✅ | — | `^\d{4}-\d{3}[\dX]$` |  |
| `issn-list` | string | ✅ | — | `^\d{4}-\d{3}[\dX]$` |  |
| `publisher` | string | ✅ | — | — |  |
| `journal-name-short` | string | ✅ | — | — |  |
| `issn-print` | string | ✅ | — | `^\d{4}-\d{3}[\dX]$` |  |
| `issn-electronic` | string | ✅ | — | `^\d{4}-\d{3}[\dX]$` |  |

### Авторы и аффилиации

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `authors` | string | ✅ | — | — |  |
| `affiliation-list` | string | ✅ | — | — |  |
| `author-orcid-list` | string | ✅ | — | `^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$` |  |

### Даты и места публикации

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `publication-year` | integer | ✅ | — | — |  |
| `publication-date` | string | ✅ | — | `^\d{4}-\d{2}-\d{2}$` |  |
| `published-print` | string | ✅ | — | — |  |
| `published-online` | string | ✅ | — | — |  |
| `published` | string | ✅ | — | — |  |

### Цитирования и ссылки

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `citations-received` | integer | ✅ | — | — |  |
| `citations-made` | integer | ✅ | — | — |  |
| `references` | string | ✅ | — | — |  |

### Технические/устаревшие поля

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `language` | string | ✅ | — | — |  |
| `lookup-method` | string | ✅ | Tracking field for record resolution strategy | — |  |
| `original-id` | string | ✅ | — | — |  |
| `-source` | string | ✅ | Fixed value: 'crossref' | — |  |
| `license-url` | string | ✅ | — | — |  |
| `content-domain-domains` | JSON object | ✅ | — | — |  |
| `content-domain-crossmark-restriction` | boolean | ✅ | — | — |  |
| `author-details` | string | ✅ | — | — |  |

---

## OpenAlex

**Кол-во полей:** 39 | **Primary Key:** `openalex-id`

### Идентификаторы и статусы

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `pmid` | string | ✅ | — | `^[1-9]\d*$ (positive integer)` |  |
| `doi` | string | ✅ | — | `^10\.\d{4,9}/.+$` |  |
| `pmc-id` | string | ✅ | — | `^PMC\d+$` |  |
| `publication-type` | string | ✅ | — | — |  |
| `is-oa` | boolean | ✅ | — | — |  |
| `openalex-id` | string | ❌ | Primary key for openalex; | `^W\d+$` | ⭐ |
| `oa-status` | string | ✅ | — | — |  |
| `is-retracted` | boolean | ✅ | — | — |  |
| `mag-id` | string | ✅ | — | — |  |

### Библиографическая информация

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `title` | string | ✅ | — | — |  |
| `abstract` | string | ✅ | — | — |  |
| `journal` | string | ✅ | — | — |  |
| `page-first` | string | ✅ | — | — |  |
| `page-last` | string | ✅ | — | — |  |
| `issn` | string | ✅ | — | `^\d{4}-\d{3}[\dX]$` |  |
| `publisher` | string | ✅ | — | — |  |
| `volume` | string | ✅ | — | — |  |
| `issue` | string | ✅ | — | — |  |

### Авторы и аффилиации

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `authors` | string | ✅ | — | — |  |
| `affiliation-list` | string | ✅ | — | — |  |
| `author-orcids` | string | ✅ | — | `^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$` |  |
| `author-openalex-ids` | string | ✅ | — | — |  |
| `institution-ids` | string | ✅ | — | — |  |
| `ror-ids` | string | ✅ | — | — |  |

### Даты и места публикации

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `publication-year` | integer | ✅ | — | — |  |
| `publication-date` | string | ✅ | — | `^\d{4}-\d{2}-\d{2}$` |  |
| `institution-country-codes` | string | ✅ | — | — |  |

### Цитирования и ссылки

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `citations-received` | integer | ✅ | — | — |  |
| `citations-made` | integer | ✅ | — | — |  |
| `fwci` | float | ✅ | — | — |  |
| `grants` | string | ✅ | — | — |  |

### Технические/устаревшие поля

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `language` | string | ✅ | — | — |  |
| `lookup-method` | string | ✅ | Tracking field for record resolution strategy | — |  |
| `original-id` | string | ✅ | — | — |  |
| `-source` | string | ✅ | Fixed value: 'openalex' | — |  |

---

## Semantic Scholar

**Кол-во полей:** 35 | **Primary Key:** `paper-id`

### Идентификаторы и статусы

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `pmid` | string | ✅ | — | `^[1-9]\d*$ (positive integer)` |  |
| `doi` | string | ✅ | — | `^10\.\d{4,9}/.+$` |  |
| `pmc-id` | string | ✅ | — | `^PMC\d+$` |  |
| `publication-type` | string | ✅ | — | — |  |
| `is-oa` | boolean | ✅ | — | — |  |
| `paper-id` | string | ❌ | Primary key for semanticscholar; | `^[a-f0-9]{40}$` | ⭐ |
| `dblp-id` | string | ✅ | — | — |  |
| `corpus-id` | integer | ✅ | — | — |  |
| `open-access-url` | string | ✅ | — | — |  |
| `oa-status` | string | ✅ | — | — |  |

### Библиографическая информация

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `title` | string | ✅ | — | — |  |
| `abstract` | string | ✅ | — | — |  |
| `journal` | string | ✅ | — | — |  |
| `page-first` | string | ✅ | — | — |  |
| `page-last` | string | ✅ | — | — |  |
| `volume` | string | ✅ | — | — |  |
| `page-range` | string | ✅ | — | — |  |

### Авторы и аффилиации

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `authors` | string | ✅ | — | — |  |
| `affiliation-list` | string | ✅ | — | — |  |
| `author-s2-ids` | string | ✅ | — | — |  |
| `author-orcids` | string | ✅ | — | `^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$` |  |
| `author-h-indices` | string | ✅ | — | — |  |

### Даты и места публикации

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `publication-year` | integer | ✅ | — | — |  |
| `publication-date` | string | ✅ | — | `^\d{4}-\d{2}-\d{2}$` |  |

### Цитирования и ссылки

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `citations-received` | integer | ✅ | — | — |  |
| `citations-made` | integer | ✅ | — | — |  |
| `influential-citation-count` | integer | ✅ | — | — |  |
| `citation-contexts` | string | ✅ | — | — |  |

### Технические/устаревшие поля

| Поле | Тип | Nullable | Описание | Regex | PK |
|------|-----|----------|----------|-------|-------|
| `language` | string | ✅ | — | — |  |
| `lookup-method` | string | ✅ | Tracking field for record resolution strategy | — |  |
| `original-id` | string | ✅ | — | — |  |
| `-source` | string | ✅ | Fixed value: 'semanticscholar' | — |  |

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

- **Validation Schema:** `docs/04-reference/schemas/publication-validation-schema-v3.xlsx`
- **ADR-033:** Стратегия валидации публикаций (`docs/02-architecture/decisions/ADR-033-publication-validation-strategy.md`)
- **Validation Guide:** `docs/03-guides/publication-validation-guide.md`
- **Тесты:** `tests-generated/` (471 тест, 64% покрытие)

---

**Версия документа:** 1.0.0
**Последнее обновление:** 2026-02-06
**Статус:** Готов к использованию ✅

