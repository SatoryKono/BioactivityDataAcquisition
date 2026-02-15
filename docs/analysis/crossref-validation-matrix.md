# CrossRef Publication — Validation Matrix

> Сравнение: standalone-пайплайн `crossref_publication` vs. **enricher** в `composite_publication`.

## 1. DQ-пороги

| Параметр | Standalone | Composite (enricher) |
|----------|-----------|----------------------|
| soft_fail | 0.10 (provider) | 0.10 (composite default) |
| hard_fail | 0.30 (provider) | 0.30 (composite default) |

> Пороги совпадают — CrossRef provider defaults = composite defaults.

## 2. Общий Silver-слой

Оба режима записывают в одну таблицу `silver/crossref/publication` и применяют идентичную валидацию:

- **Pandera-схема**: `PublicationEnrichedSchema` (наследует `PublicationBaseSchema`)
- **DQ-конфиг**: `configs/quality/entities/crossref/publication.yaml`
- **Provider DQ**: `configs/quality/providers/crossref.yaml`

## 3. Матрица валидации полей

Обозначения: **S** — Silver (Pandera + DQ), **G** — Gold-контракт, **F** — Gold-фильтр.
`NN` = not null, `N` = nullable.

### Первичный ключ и идентификаторы

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `doi` | **S**: str/NN, pattern `^10\.\d{4,}/\S+$` (Pandera + DQ, not null) · **G**: str/NN, DOI pattern (strict) · **F**: required | **S**: идентично · **G**: qualified `crossref.publication.doi`, strict=False — нет поле-проверки · **F**: не required отдельно |
| `pmid` | **S**: str/N, pattern `^[1-9]\d*$` (base) · **G**: отсутствует (CrossRef не предоставляет pmid) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `pmc_id` | **S**: str/N, pattern `^PMC\d+$` (base) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `alternative_id` | **S**: object/N · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Основной контент

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `title` | **S**: str/N; DQ: max_length 2000, not_null (warn), non-empty (warn); title_not_empty (Pandera) · **G**: str/N (strict) · **F**: required | **S**: идентично · **G**: strict=False · **F**: required (composite `gold_filters`) |
| `abstract` | **S**: str/N (base) · **G**: отсутствует (нет в CrossRef Gold) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `authors` | **S**: str/N (base, JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `affiliation_list` | **S**: str/N (base, JSON) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: json_array/N · **F**: — |
| `author_orcids` | **S**: str/N (base); ORCID format check · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: json_array/N · **F**: — |
| `author_details` | **S**: str/N (JSON array of author objects) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: json_array/N · **F**: — |
| `references` | **S**: str/N (JSON array of cited refs) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: json_array/N · **F**: — |

### Метаданные публикации

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `publication_type` | **S**: str/N · DQ: enum `[journal-article, book-chapter, proceedings-article, posted-content, book, report, dataset, standard]` · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication_type_unified` | **S**: str/N (base) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication_subclass` | **S**: str/N (base) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication_class` | **S**: str/N, isin `[EXP, REV, PEER]` (base) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication_year` | **S**: Int64/N, 1950–2050 (Pandera); DQ: range 1500–2100 · **G**: float/N, 1500–2100, coerce (strict) · **F**: range 1950–2050 | **S**: идентично · **G**: strict=False · **F**: нет range filter |
| `publication_date` | **S**: str/N, pattern `^\d{4}-\d{2}-\d{2}$` (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `published` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `published_print` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `published_online` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `language` | **S**: str/N, length 2–3 (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Журнал и ISSN

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `journal` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `journal_name_short` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publisher` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `issn` | **S**: str/N, ISSN pattern `^\d{4}-\d{3}[\dX]$` · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `issn_list` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `issn_print` | **S**: str/N, ISSN pattern · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `issn_electronic` | **S**: str/N, ISSN pattern · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Пагинация

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `volume` | **S**: отсутствует в schema (base `page_first`/`page_last` only) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `issue` | **S**: аналогично · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `page_first` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `page_last` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Метрики

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `citations_received` | **S**: Int64/N, ≥0 (base); DQ: range ≥0, warn 0–10M · **G**: float/N, ≥0, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `citations_made` | **S**: Int64/N, ≥0 (base); DQ: range ≥0 · **G**: float/N, ≥0, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Open Access и лицензии

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `is_oa` | **S**: bool/N (base) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `license_url` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `subject_keywords` | **S**: str/N (JSON) · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Content Domain (CrossRef-специфичные)

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `content_domain_domains` | **S**: object/N · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `content_domain_crossmark_restriction` | **S**: bool/N, coerce · **G**: bool/N, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Системные поля

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `_source` | **S**: str/NN, eq `"crossref"` · **G**: str/NN (strict) · **F**: — | **S**: идентично · **G**: str/N (composite ослаблено) · **F**: — |
| `_lookup_method` | **S**: str/NN, isin LOOKUP_METHODS · **G**: str/NN, isin LOOKUP_METHODS (strict) · **F**: — | **S**: идентично · **G**: str/N (composite ослаблено, нет isin) · **F**: — |
| `_original_id` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: str/N · **F**: — |
| `entity_id` | **S**: str/NN · **G**: str/NN (strict) · **F**: — | **S**: идентично · **G**: str/NN · **F**: — |
| `content_hash` | **S**: str/NN, 64-hex · **G**: str/NN (strict) · **F**: — | **S**: идентично · **G**: str/NN · **F**: — |
| `_dq_warn` | **S**: bool/NN · **G**: bool/NN (strict) · **F**: — | **S**: идентично · **G**: bool/NN · **F**: — |
| `_dq_error` | **S**: bool/NN · **G**: bool/NN (strict) · **F**: — | **S**: идентично · **G**: bool/NN · **F**: — |
| `_run_id` | **S**: str/NN · **G**: str/NN (strict) · **F**: — | **S**: идентично · **G**: str/NN · **F**: — |
| `_run_type` | **S**: str/NN, isin runs · **G**: str/NN (strict) · **F**: — | **S**: идентично · **G**: str/NN · **F**: — |
| `_ingestion_ts` | **S**: str/NN, ISO 8601 · **G**: str/NN (strict) · **F**: — | **S**: идентично · **G**: str/NN · **F**: — |
| `_index` | **S**: int/NN, ≥0 · **G**: int/NN (strict) · **F**: — | **S**: идентично · **G**: int/NN · **F**: — |
| `_source_batch_id` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: str/N · **F**: — |

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
| `publication_identifiable` | `doi` AND `title` — all_present (error) | Не применяется на composite level |

## 5. Conditional валидации

| Правило | Standalone | Composite |
|---------|-----------|-----------|
| `article_requires_title` | Если `type` in `[journal-article, proceedings-article]` → title not null (error) | Не применяется на composite level |

## 6. Gold-фильтры

| Параметр | Standalone | Composite |
|----------|-----------|-----------|
| required_fields | `doi`, `title` | `title` |
| column filter | — | — |
| range filter | `publication_year: 1950–2050` | — |

## 7. Ключевые различия

1. **Strict vs. Loose Gold**: standalone использует `CrossRefPublicationGoldSchema` (strict=True, ~40 полей) — каждое поле типизировано. Composite Gold (strict=False) проверяет только системные поля.
2. **doi required в Gold**: standalone Gold требует `doi` not null с DOI-паттерном. В composite Gold нет per-field проверки doi.
3. **Filter relaxation**: standalone требует `doi` + `title` + year range. Composite требует только `title`.
4. **Conditional validation coverage**: standalone проверяет, что articles/proceedings имеют title. В composite этот conditional не применяется.
5. **DQ-пороги**: совпадают (soft=0.10, hard=0.30 — CrossRef provider = composite default).
6. **Qualified column names**: в composite CrossRef-поля получают префикс `crossref.publication.*`.
7. **Composite field_validations**: composite добавляет валидацию JSON-array полей (`author_orcids`, `author_details`, `references`, `affiliation_list`) через `field_validations` в конфиге composite.
8. **Lineage-поля**: composite добавляет 4 поля lineage, отсутствующие в standalone.
