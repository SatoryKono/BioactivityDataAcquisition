# Semantic Scholar Publication — Validation Matrix

> Сравнение: standalone-пайплайн `semanticscholar_publication` vs. **enricher** в `composite_publication`.

## 1. DQ-пороги

| Параметр | Standalone | Composite (enricher) |
|----------|-----------|----------------------|
| soft_fail | 0.15 (provider) | 0.20 (composite override для `semanticscholar_publication`) |
| hard_fail | 0.40 (provider) | 0.50 (composite override для `semanticscholar_publication`) |

> Composite ещё мягче — S2 имеет высокие rate limits и вариативные данные.

## 2. Общий Silver-слой

Оба режима записывают в одну таблицу `silver/semanticscholar/publication` и применяют идентичную валидацию:

- **Pandera-схема**: `SemanticScholarPublicationSchema` (наследует `PublicationBaseSchema`)
- **DQ-конфиг**: `configs/dq/entities/semanticscholar/publication.yaml`
- **Provider DQ**: `configs/dq/providers/semanticscholar.yaml`

## 3. Матрица валидации полей

Обозначения: **S** — Silver (Pandera + DQ), **G** — Gold-контракт, **F** — Gold-фильтр.

### Первичный ключ и идентификаторы

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `paper_id` | **S**: str/NN, pattern `^[a-f0-9]{40}$` (Pandera + DQ) · **G**: str/NN (strict) · **F**: required | **S**: идентично · **G**: strict=False — нет поле-проверки · **F**: не required |
| `doi` | **S**: str/N, DOI pattern (Pandera + DQ) · **G**: str/N, DOI pattern (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `pmid` | **S**: str/N, pattern `^[1-9]\d*$` (base); DQ: range 1–10B · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `corpus_id` | **S**: Int64/N, ≥0 · **G**: float/N, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `dblp_id` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: string/N · **F**: — |

### Основной контент

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `title` | **S**: str/N; DQ: max_length 2000, not_null (warn), non-empty (warn); title_not_empty (Pandera) · **G**: str/N (strict) · **F**: required | **S**: идентично · **G**: strict=False · **F**: required (composite `gold_filters`) |
| `abstract` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `tldr` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `authors` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `affiliation_list` | **S**: str/N (base, JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: json_array/N · **F**: — |
| `author_orcids` | **S**: str/N (base); ORCID format check · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: json_array/N · **F**: — |
| `author_s2_ids` | **S**: str/N (JSON, 40-char hex IDs) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: json_array/N · **F**: — |
| `author_h_indices` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: json_array/N · **F**: — |

### Метаданные публикации

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `publication_type` | **S**: str/N (pipe-delimited) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication_types` | **S**: str/N (JSON array) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication_type_unified` | **S**: str/N (base) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication_subclass` | **S**: str/N (base) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication_class` | **S**: str/N, isin `[EXP, REV, PEER]` (base) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication_year` | **S**: Int64/N, 1950–2050 (Pandera); DQ: range 1500–2100 · **G**: float/N, 1500–2100, coerce (strict) · **F**: range 1950–2050 | **S**: идентично · **G**: strict=False · **F**: нет range filter |
| `publication_date` | **S**: str/N, pattern `^\d{4}-\d{2}-\d{2}$` (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `language` | **S**: str/N, length 2–3 (base) · **G**: отсутствует (S2 не предоставляет) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Журнал

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `journal` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `volume` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Пагинация

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `page_first` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `page_last` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `page_range` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Метрики

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `citations_received` | **S**: Int64/N, ≥0 (base); DQ: range ≥0, warn 0–10M · **G**: float/N, ≥0, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `citations_made` | **S**: Int64/N, ≥0 (base); DQ: range ≥0 · **G**: float/N, ≥0, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `influential_citation_count` | **S**: Int64/N, ≥0 (Pandera + DQ) · **G**: float/N, ≥0, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: integer/N, min_value=0 · **F**: — |

### Open Access

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `is_oa` | **S**: bool/N (base) · **G**: bool/N, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `oa_status` | **S**: str/N, isin `[gold, green, hybrid, bronze, closed]` · **G**: str/N, isin OA_STATUS (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `open_access_url` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Классификация

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `subject_fields` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `citation_contexts` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: json_array/N · **F**: — |

### Системные поля

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `_source` | **S**: str/NN, eq `"semanticscholar"` · **G**: str/NN (strict) · **F**: — | **S**: идентично · **G**: str/N (composite ослаблено) · **F**: — |
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
| `publication_identifiable` | `paper_id` AND `title` — all_present (error) | Не применяется на composite level |

## 5. Conditional валидации

| Правило | Standalone | Composite |
|---------|-----------|-----------|
| `journal_article_requires_title` | Если `publication_type == JournalArticle` → title not null (error) | Не применяется на composite level |

## 6. Gold-фильтры

| Параметр | Standalone | Composite |
|----------|-----------|-----------|
| required_fields | `paper_id`, `title` | `title` |
| column filter | — | — |
| range filter | `publication_year: 1950–2050` | — |
| enricher filter_condition | — | `doi IS NOT NULL OR title IS NOT NULL` |

## 7. Ключевые различия

1. **DQ-пороги ещё мягче в composite**: standalone (soft=0.15, hard=0.40) → composite override (soft=0.20, hard=0.50). S2 имеет самые мягкие пороги среди всех enrichers.
2. **Strict vs. Loose Gold**: standalone `SemanticScholarPublicationGoldSchema` (strict=True, ~35 полей) типизирует каждое поле. Composite Gold (strict=False) — только системные.
3. **paper_id required**: standalone Gold + Filter требуют `paper_id` not null с 40-hex pattern. Composite — не required.
4. **Filter relaxation**: standalone требует `paper_id` + `title` + year range. Composite — только `title`.
5. **Conditional validation**: standalone проверяет `JournalArticle` → title required. Не применяется в composite.
6. **Composite field_validations**: composite добавляет `influential_citation_count: integer/N, ≥0`, а также json_array-проверку для `author_s2_ids`, `author_h_indices`, `citation_contexts`, `affiliation_list`, `author_orcids` и string для `dblp_id`.
7. **Qualified column names**: в composite S2-поля получают префикс `semanticscholar.publication.*`.
8. **Lineage-поля**: composite добавляет 4 поля lineage.
9. **Timeout**: composite использует `timeout_seconds: 7200` (2 часа) для S2 enricher, vs. standalone pipeline timeout определяется по runtime config.
