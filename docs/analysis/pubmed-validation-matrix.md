# PubMed Publication — Validation Matrix

> Сравнение: standalone-пайплайн `pubmed_publication` vs. **enricher** в `composite_publication`.

## 1. DQ-пороги

| Параметр | Standalone | Composite (enricher) |
|----------|-----------|----------------------|
| soft_fail | 0.05 (provider) | 0.15 (composite override для `pubmed_publication`) |
| hard_fail | 0.15 (provider) | 0.40 (composite override для `pubmed_publication`) |

> Composite существенно мягче — PubMed в composite допускает больше ошибок
> из-за фильтрации pmid-less записей.

## 2. Общий Silver-слой

Оба режима записывают в одну таблицу `silver/pubmed/publication` и применяют идентичную валидацию:

- **Pandera-схема**: `PubMedPublicationSchema` (наследует `PublicationBaseSchema`)
- **DQ-конфиг**: `configs/dq/entities/pubmed/publication.yaml`
- **Provider DQ**: `configs/dq/providers/pubmed.yaml`

## 3. Матрица валидации полей

Обозначения: **S** — Silver (Pandera + DQ), **G** — Gold-контракт, **F** — Gold-фильтр.

### Первичный ключ и идентификаторы

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `pmid` | **S**: str/NN, pattern `^[1-9]\d*$` (Pandera); DQ: range 1–10B, not null · **G**: str/NN (strict) · **F**: required | **S**: идентично · **G**: strict=False — нет поле-проверки · **F**: не required отдельно (composite filter_condition: `pmid IS NOT NULL`) |
| `doi` | **S**: str/N, DOI pattern (Pandera + DQ) · **G**: str/N, DOI pattern (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `pmc_id` | **S**: str/N; pmc_id_format check `^PMC\d+$` (Pandera); DQ: pattern · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `pii` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: string/N · **F**: — |
| `mid` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: string/N · **F**: — |
| `publisher_id` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: string/N · **F**: — |
| `nlm_unique_id` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Основной контент

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `title` | **S**: str/NN (Pandera override — not null для PubMed); DQ: max_length 2000, not_null (warn), non-empty (warn); title_not_empty (Pandera) · **G**: str/NN (strict) · **F**: required | **S**: идентично · **G**: strict=False · **F**: required (composite `gold_filters`) |
| `abstract` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `abstract_structured` | **S**: bool/N · **G**: bool/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `authors` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `affiliation_list` | **S**: str/N (base, JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: json_array/N · **F**: — |
| `affiliation_structured` | **S**: str/N (JSON with ROR/GRID) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `authors_with_affiliations` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `author_orcids` | **S**: str/N (base); ORCID format check · **G**: отсутствует в PubMed Gold · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: json_array/N · **F**: — |

### Журнал и ISSN

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `journal` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `journal_name_short` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `journal_iso_abbrev` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `issn` | **S**: str/N, ISSN pattern `^\d{4}-\d{3}[\dX]$` · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `journal_issn_type` | **S**: str/N; check isin `[Print, Electronic, Linking]` · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `country` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Пагинация

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `page_first` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `page_last` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `page_range` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `medline_pgn` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Даты

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `publication_year` | **S**: Int64/N, 1950–2050 (Pandera); DQ: range 1500–2100 · **G**: float/N, 1500–2100, coerce (strict) · **F**: range 1950–2050 | **S**: идентично · **G**: strict=False · **F**: нет range filter |
| `publication_date` | **S**: str/N, pattern `^\d{4}-\d{2}-\d{2}$` (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `pub_month` | **S**: Int64/N; check range 1–12 · **G**: float/N, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `pub_day` | **S**: Int64/N; check range 1–31 · **G**: float/N, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `date_completed` | **S**: datetime/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `date_revised` | **S**: datetime/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Метаданные публикации

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `publication_type` | **S**: str/N (base) · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `pub_type` (DQ only) | DQ: enum `[Journal Article, Review, Letter, Editorial, Clinical Trial, Meta-Analysis, Case Reports, Comparative Study, Evaluation Study]` · **G**: — · **F**: — | DQ: идентично · **G**: strict=False · **F**: — |
| `publication_type_unified` | **S**: str/N (base) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication_subclass` | **S**: str/N (base) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication_class` | **S**: str/N, isin `[EXP, REV, PEER]` (base) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication_status` | **S**: str/N; check isin `[ppublish, epublish, aheadofprint]` · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication_type_list` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication_types` | **S**: str/N (JSON) · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `language` | **S**: str/N, length 2–3 (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `citation_subset` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Классификация

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `subject_mesh` | **S**: str/N (JSON) · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `subject_keywords` | **S**: str/N (JSON) · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `chemicals` | **S**: str/N (JSON) · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: json_array/N · **F**: — |
| `gene_symbols` | **S**: str/N (JSON) · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: json_array/N · **F**: — |
| `databanks` | **S**: str/N (JSON) · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: json_array/N · **F**: — |

### Метрики и счётчики

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `citations_received` | **S**: Int64/N, ≥0 (base); DQ: range ≥0, warn 0–10M · **G**: отсутствует (PubMed не предоставляет) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `citations_made` | **S**: Int64/N, ≥0 (base); DQ: range ≥0 · **G**: float/N, ≥0, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `author_count` | **S**: Int64/N; check ≥0 · **G**: float/N, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `mesh_heading_count` | **S**: Int64/N; check ≥0 · **G**: float/N, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `keyword_count` | **S**: Int64/N; check ≥0 · **G**: float/N, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `grant_count` | **S**: Int64/N; check ≥0 · **G**: float/N, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `chemical_count` | **S**: Int64/N; check ≥0 · **G**: float/N, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Open Access

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `is_oa` | **S**: bool/N (base) · **G**: отсутствует (PubMed не предоставляет) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Системные поля

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `_source` | **S**: str/NN, eq `"pubmed"` · **G**: str/NN (strict) · **F**: — | **S**: идентично · **G**: str/N (composite ослаблено) · **F**: — |
| `_lookup_method` | **S**: str/NN, isin LOOKUP_METHODS · **G**: str/NN, isin LOOKUP_METHODS (strict) · **F**: — | **S**: идентично · **G**: str/N (composite, нет isin) · **F**: — |
| `_original_id` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: str/N · **F**: — |
| `entity_id` | **S**: str/NN · **G**: str/NN (strict) · **F**: — | **S**: идентично · **G**: str/NN · **F**: — |
| `content_hash` | **S**: str/NN, 64-hex · **G**: str/NN (strict) · **F**: — | **S**: идентично · **G**: str/NN · **F**: — |
| `_dq_warn` / `_dq_error` | **S**: bool/NN · **G**: bool/NN (strict) · **F**: — | **S**: идентично · **G**: bool/NN · **F**: — |
| `_run_id` | **S**: str/NN · **G**: str/NN · **F**: — | **S**: идентично · **G**: str/NN · **F**: — |
| `_run_type` | **S**: str/NN, isin runs · **G**: str/NN · **F**: — | **S**: идентично · **G**: str/NN · **F**: — |
| `_ingestion_ts` | **S**: str/NN, ISO 8601 · **G**: str/NN · **F**: — | **S**: идентично · **G**: str/NN · **F**: — |
| `_index` | **S**: int/NN, ≥0 · **G**: int/NN · **F**: — | **S**: идентично · **G**: int/NN · **F**: — |
| `_source_batch_id` | **S**: str/N · **G**: str/N · **F**: — | **S**: идентично · **G**: str/N · **F**: — |

### Composite-only поля

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `_composite_run_id` | — | str/NN (MergeService) |
| `_source_providers` | — | str/NN, JSON list |
| `_enrichment_status` | — | str/NN, JSON dict |
| `_lineage_created_at` | — | str/NN, ISO timestamp |

## 4. Cross-field валидации

| Правило | Standalone | Composite |
|---------|-----------|-----------|
| `publication_identifiable` | `pmid` AND `title` — all_present (error) | Не применяется на composite level |
| `has_identifier` | `pmid` OR `doi` OR `pmc_id` — any_present (error) | Не применяется на composite level |

## 5. Conditional валидации

| Правило | Standalone | Composite |
|---------|-----------|-----------|
| — | Нет conditional валидаций | — |

## 6. Gold-фильтры

| Параметр | Standalone | Composite |
|----------|-----------|-----------|
| required_fields | `pmid`, `title` | `title` |
| column filter | — | — |
| range filter | `publication_year: 1950–2050` | — |
| enricher filter_condition | — | `pmid IS NOT NULL` (pre-filter записей seed) |

## 7. Ключевые различия

1. **Существенно разные DQ-пороги**: standalone (soft=0.05, hard=0.15) vs. composite override (soft=0.15, hard=0.40) — composite в 3× мягче по soft и 2.7× по hard. Обоснование: PubMed в composite фильтрует записи без pmid, что приводит к большей доле ошибок среди оставшихся.
2. **Strict vs. Loose Gold**: standalone `PubMedPublicationGoldSchema` (strict=True, ~60 полей) — каждое поле типизировано с int→float coercion. Composite Gold (strict=False) — только системные поля.
3. **title non-nullable**: PubMed Silver Schema делает `title` NN (override base). Это одинаково в обоих режимах (Silver shared).
4. **pmid required**: standalone Gold + Filter требуют `pmid`. Composite — нет (pmid фильтруется на уровне `filter_condition`).
5. **has_identifier cross-field**: standalone проверяет наличие хотя бы одного ID (pmid/doi/pmc_id). В composite отсутствует.
6. **Filter relaxation**: standalone требует `pmid` + `title` + year range. Composite — только `title`.
7. **PubMed-specific counts**: standalone Gold проверяет `author_count`, `mesh_heading_count`, `keyword_count`, `grant_count`, `chemical_count` как float с coerce. Composite Gold не проверяет эти поля.
8. **Composite field_validations**: composite добавляет json_array-проверку для `chemicals`, `gene_symbols`, `databanks`, `affiliation_list`, `author_orcids` и string-проверку для `pii`, `mid`, `publisher_id`.
9. **Qualified column names**: в composite PubMed-поля получают префикс `pubmed.publication.*`.
10. **Lineage-поля**: composite добавляет 4 поля lineage.
