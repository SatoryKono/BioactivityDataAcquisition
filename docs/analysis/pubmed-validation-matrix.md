# PubMed Publication — Validation Matrix

> Сравнение: standalone-пайплайн `pubmed-publication` vs. **enricher** в `composite-publication`.

## 1. DQ-пороги

| Параметр | Standalone | Composite (enricher) |
|----------|-----------|----------------------|
| soft-fail | 0.05 (provider) | 0.15 (composite override для `pubmed-publication`) |
| hard-fail | 0.15 (provider) | 0.40 (composite override для `pubmed-publication`) |

> Composite существенно мягче — PubMed в composite допускает больше ошибок
> из-за фильтрации pmid-less записей.

## 2. Общий Silver-слой

Оба режима записывают в одну таблицу `silver/pubmed/publication` и применяют идентичную валидацию:

- **Pandera-схема**: `PubMedPublicationSchema` (наследует `PublicationBaseSchema`)
- **DQ-конфиг**: `configs/quality/entities/pubmed/publication.yaml`
- **Provider DQ**: `configs/quality/providers/pubmed.yaml`

## 3. Матрица валидации полей

Обозначения: **S** — Silver (Pandera + DQ), **G** — Gold-контракт, **F** — Gold-фильтр.

### Первичный ключ и идентификаторы

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `pmid` | **S**: str/NN, pattern `^[1-9]\d*$` (Pandera); DQ: range 1–10B, not null · **G**: str/NN (strict) · **F**: required | **S**: идентично · **G**: strict=False — нет поле-проверки · **F**: не required отдельно (composite filter-condition: `pmid IS NOT NULL`) |
| `doi` | **S**: str/N, DOI pattern (Pandera + DQ) · **G**: str/N, DOI pattern (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `pmc-id` | **S**: str/N; pmc-id-format check `^PMC\d+$` (Pandera); DQ: pattern · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `pii` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: string/N · **F**: — |
| `mid` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: string/N · **F**: — |
| `publisher-id` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: string/N · **F**: — |
| `nlm-unique-id` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Основной контент

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `title` | **S**: str/NN (Pandera override — not null для PubMed); DQ: max-length 2000, not-null (warn), non-empty (warn); title-not-empty (Pandera) · **G**: str/NN (strict) · **F**: required | **S**: идентично · **G**: strict=False · **F**: required (composite `gold-filters`) |
| `abstract` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `abstract-structured` | **S**: bool/N · **G**: bool/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `authors` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `affiliation-list` | **S**: str/N (base, JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: json-array/N · **F**: — |
| `affiliation-structured` | **S**: str/N (JSON with ROR/GRID) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `authors-with-affiliations` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `author-orcids` | **S**: str/N (base); ORCID format check · **G**: отсутствует в PubMed Gold · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: json-array/N · **F**: — |

### Журнал и ISSN

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `journal` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `journal-name-short` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `journal-iso-abbrev` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `issn` | **S**: str/N, ISSN pattern `^\d{4}-\d{3}[\dX]$` · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `journal-issn-type` | **S**: str/N; check isin `[Print, Electronic, Linking]` · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `country` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Пагинация

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `page-first` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `page-last` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `page-range` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `medline-pgn` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Даты

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `publication-year` | **S**: Int64/N, 1950–2050 (Pandera); DQ: range 1500–2100 · **G**: float/N, 1500–2100, coerce (strict) · **F**: range 1950–2050 | **S**: идентично · **G**: strict=False · **F**: нет range filter |
| `publication-date` | **S**: str/N, pattern `^\d{4}-\d{2}-\d{2}$` (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `pub-month` | **S**: Int64/N; check range 1–12 · **G**: float/N, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `pub-day` | **S**: Int64/N; check range 1–31 · **G**: float/N, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `date-completed` | **S**: datetime/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `date-revised` | **S**: datetime/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Метаданные публикации

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `publication-type` | **S**: str/N (base) · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `pub-type` (DQ only) | DQ: enum `[Journal Article, Review, Letter, Editorial, Clinical Trial, Meta-Analysis, Case Reports, Comparative Study, Evaluation Study]` · **G**: — · **F**: — | DQ: идентично · **G**: strict=False · **F**: — |
| `publication-type-unified` | **S**: str/N (base) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication-subclass` | **S**: str/N (base) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication-class` | **S**: str/N, isin `[EXP, REV, PEER]` (base) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication-status` | **S**: str/N; check isin `[ppublish, epublish, aheadofprint]` · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication-type-list` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication-types` | **S**: str/N (JSON) · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `language` | **S**: str/N, length 2–3 (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `citation-subset` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Классификация

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `subject-mesh` | **S**: str/N (JSON) · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `subject-keywords` | **S**: str/N (JSON) · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `chemicals` | **S**: str/N (JSON) · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: json-array/N · **F**: — |
| `gene-symbols` | **S**: str/N (JSON) · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: json-array/N · **F**: — |
| `databanks` | **S**: str/N (JSON) · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: json-array/N · **F**: — |

### Метрики и счётчики

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `citations-received` | **S**: Int64/N, ≥0 (base); DQ: range ≥0, warn 0–10M · **G**: отсутствует (PubMed не предоставляет) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `citations-made` | **S**: Int64/N, ≥0 (base); DQ: range ≥0 · **G**: float/N, ≥0, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `author-count` | **S**: Int64/N; check ≥0 · **G**: float/N, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `mesh-heading-count` | **S**: Int64/N; check ≥0 · **G**: float/N, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `keyword-count` | **S**: Int64/N; check ≥0 · **G**: float/N, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `grant-count` | **S**: Int64/N; check ≥0 · **G**: float/N, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `chemical-count` | **S**: Int64/N; check ≥0 · **G**: float/N, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Open Access

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `is-oa` | **S**: bool/N (base) · **G**: отсутствует (PubMed не предоставляет) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Системные поля

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `-source` | **S**: str/NN, eq `"pubmed"` · **G**: str/NN (strict) · **F**: — | **S**: идентично · **G**: str/N (composite ослаблено) · **F**: — |
| `-lookup-method` | **S**: str/NN, isin LOOKUP-METHODS · **G**: str/NN, isin LOOKUP-METHODS (strict) · **F**: — | **S**: идентично · **G**: str/N (composite, нет isin) · **F**: — |
| `-original-id` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: str/N · **F**: — |
| `entity-id` | **S**: str/NN · **G**: str/NN (strict) · **F**: — | **S**: идентично · **G**: str/NN · **F**: — |
| `content-hash` | **S**: str/NN, 64-hex · **G**: str/NN (strict) · **F**: — | **S**: идентично · **G**: str/NN · **F**: — |
| `-dq-warn` / `-dq-error` | **S**: bool/NN · **G**: bool/NN (strict) · **F**: — | **S**: идентично · **G**: bool/NN · **F**: — |
| `-run-id` | **S**: str/NN · **G**: str/NN · **F**: — | **S**: идентично · **G**: str/NN · **F**: — |
| `-run-type` | **S**: str/NN, isin runs · **G**: str/NN · **F**: — | **S**: идентично · **G**: str/NN · **F**: — |
| `-ingestion-ts` | **S**: str/NN, ISO 8601 · **G**: str/NN · **F**: — | **S**: идентично · **G**: str/NN · **F**: — |
| `-index` | **S**: int/NN, ≥0 · **G**: int/NN · **F**: — | **S**: идентично · **G**: int/NN · **F**: — |
| `-source-batch-id` | **S**: str/N · **G**: str/N · **F**: — | **S**: идентично · **G**: str/N · **F**: — |

### Composite-only поля

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `-composite-run-id` | — | str/NN (MergeService) |
| `-source-providers` | — | str/NN, JSON list |
| `-enrichment-status` | — | str/NN, JSON dict |
| `-lineage-created-at` | — | str/NN, ISO timestamp |

## 4. Cross-field валидации

| Правило | Standalone | Composite |
|---------|-----------|-----------|
| `publication-identifiable` | `pmid` AND `title` — all-present (error) | Не применяется на composite level |
| `has-identifier` | `pmid` OR `doi` OR `pmc-id` — any-present (error) | Не применяется на composite level |

## 5. Conditional валидации

| Правило | Standalone | Composite |
|---------|-----------|-----------|
| — | Нет conditional валидаций | — |

## 6. Gold-фильтры

| Параметр | Standalone | Composite |
|----------|-----------|-----------|
| required-fields | `pmid`, `title` | `title` |
| column filter | — | — |
| range filter | `publication-year: 1950–2050` | — |
| enricher filter-condition | — | `pmid IS NOT NULL` (pre-filter записей seed) |

## 7. Ключевые различия

1. **Существенно разные DQ-пороги**: standalone (soft=0.05, hard=0.15) vs. composite override (soft=0.15, hard=0.40) — composite в 3× мягче по soft и 2.7× по hard. Обоснование: PubMed в composite фильтрует записи без pmid, что приводит к большей доле ошибок среди оставшихся.
2. **Strict vs. Loose Gold**: standalone `PubMedPublicationGoldSchema` (strict=True, ~60 полей) — каждое поле типизировано с int→float coercion. Composite Gold (strict=False) — только системные поля.
3. **title non-nullable**: PubMed Silver Schema делает `title` NN (override base). Это одинаково в обоих режимах (Silver shared).
4. **pmid required**: standalone Gold + Filter требуют `pmid`. Composite — нет (pmid фильтруется на уровне `filter-condition`).
5. **has-identifier cross-field**: standalone проверяет наличие хотя бы одного ID (pmid/doi/pmc-id). В composite отсутствует.
6. **Filter relaxation**: standalone требует `pmid` + `title` + year range. Composite — только `title`.
7. **PubMed-specific counts**: standalone Gold проверяет `author-count`, `mesh-heading-count`, `keyword-count`, `grant-count`, `chemical-count` как float с coerce. Composite Gold не проверяет эти поля.
8. **Composite field-validations**: composite добавляет json-array-проверку для `chemicals`, `gene-symbols`, `databanks`, `affiliation-list`, `author-orcids` и string-проверку для `pii`, `mid`, `publisher-id`.
9. **Qualified column names**: в composite PubMed-поля получают префикс `pubmed.publication.*`.
10. **Lineage-поля**: composite добавляет 4 поля lineage.
