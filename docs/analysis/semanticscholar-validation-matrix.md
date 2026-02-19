# Semantic Scholar Publication — Validation Matrix

> Сравнение: standalone-пайплайн `semanticscholar-publication` vs. **enricher** в `composite-publication`.

## 1. DQ-пороги

| Параметр | Standalone | Composite (enricher) |
|----------|-----------|----------------------|
| soft-fail | 0.15 (provider) | 0.20 (composite override для `semanticscholar-publication`) |
| hard-fail | 0.40 (provider) | 0.50 (composite override для `semanticscholar-publication`) |

> Composite ещё мягче — S2 имеет высокие rate limits и вариативные данные.

## 2. Общий Silver-слой

Оба режима записывают в одну таблицу `silver/semanticscholar/publication` и применяют идентичную валидацию:

- **Pandera-схема**: `SemanticScholarPublicationSchema` (наследует `PublicationBaseSchema`)
- **DQ-конфиг**: `configs/quality/entities/semanticscholar/publication.yaml`
- **Provider DQ**: `configs/quality/providers/semanticscholar.yaml`

## 3. Матрица валидации полей

Обозначения: **S** — Silver (Pandera + DQ), **G** — Gold-контракт, **F** — Gold-фильтр.

### Первичный ключ и идентификаторы

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `paper-id` | **S**: str/NN, pattern `^[a-f0-9]{40}$` (Pandera + DQ) · **G**: str/NN (strict) · **F**: required | **S**: идентично · **G**: strict=False — нет поле-проверки · **F**: не required |
| `doi` | **S**: str/N, DOI pattern (Pandera + DQ) · **G**: str/N, DOI pattern (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `pmid` | **S**: str/N, pattern `^[1-9]\d*$` (base); DQ: range 1–10B · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `corpus-id` | **S**: Int64/N, ≥0 · **G**: float/N, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `dblp-id` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: string/N · **F**: — |

### Основной контент

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `title` | **S**: str/N; DQ: max-length 2000, not-null (warn), non-empty (warn); title-not-empty (Pandera) · **G**: str/N (strict) · **F**: required | **S**: идентично · **G**: strict=False · **F**: required (composite `gold-filters`) |
| `abstract` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `tldr` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `authors` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `affiliation-list` | **S**: str/N (base, JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: json-array/N · **F**: — |
| `author-orcids` | **S**: str/N (base); ORCID format check · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: json-array/N · **F**: — |
| `author-s2-ids` | **S**: str/N (JSON, 40-char hex IDs) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: json-array/N · **F**: — |
| `author-h-indices` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: json-array/N · **F**: — |

### Метаданные публикации

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `publication-type` | **S**: str/N (pipe-delimited) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication-types` | **S**: str/N (JSON array) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication-type-unified` | **S**: str/N (base) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication-subclass` | **S**: str/N (base) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication-class` | **S**: str/N, isin `[EXP, REV, PEER]` (base) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication-year` | **S**: Int64/N, 1950–2050 (Pandera); DQ: range 1500–2100 · **G**: float/N, 1500–2100, coerce (strict) · **F**: range 1950–2050 | **S**: идентично · **G**: strict=False · **F**: нет range filter |
| `publication-date` | **S**: str/N, pattern `^\d{4}-\d{2}-\d{2}$` (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `language` | **S**: str/N, length 2–3 (base) · **G**: отсутствует (S2 не предоставляет) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Журнал

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `journal` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `volume` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Пагинация

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `page-first` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `page-last` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `page-range` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Метрики

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `citations-received` | **S**: Int64/N, ≥0 (base); DQ: range ≥0, warn 0–10M · **G**: float/N, ≥0, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `citations-made` | **S**: Int64/N, ≥0 (base); DQ: range ≥0 · **G**: float/N, ≥0, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `influential-citation-count` | **S**: Int64/N, ≥0 (Pandera + DQ) · **G**: float/N, ≥0, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: integer/N, min-value=0 · **F**: — |

### Open Access

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `is-oa` | **S**: bool/N (base) · **G**: bool/N, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `oa-status` | **S**: str/N, isin `[gold, green, hybrid, bronze, closed]` · **G**: str/N, isin OA-STATUS (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `open-access-url` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Классификация

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `subject-fields` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `citation-contexts` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: json-array/N · **F**: — |

### Системные поля

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `-source` | **S**: str/NN, eq `"semanticscholar"` · **G**: str/NN (strict) · **F**: — | **S**: идентично · **G**: str/N (composite ослаблено) · **F**: — |
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
| `publication-identifiable` | `paper-id` AND `title` — all-present (error) | Не применяется на composite level |

## 5. Conditional валидации

| Правило | Standalone | Composite |
|---------|-----------|-----------|
| `journal-article-requires-title` | Если `publication-type == JournalArticle` → title not null (error) | Не применяется на composite level |

## 6. Gold-фильтры

| Параметр | Standalone | Composite |
|----------|-----------|-----------|
| required-fields | `paper-id`, `title` | `title` |
| column filter | — | — |
| range filter | `publication-year: 1950–2050` | — |
| enricher filter-condition | — | `doi IS NOT NULL OR title IS NOT NULL` |

## 7. Ключевые различия

1. **DQ-пороги ещё мягче в composite**: standalone (soft=0.15, hard=0.40) → composite override (soft=0.20, hard=0.50). S2 имеет самые мягкие пороги среди всех enrichers.
2. **Strict vs. Loose Gold**: standalone `SemanticScholarPublicationGoldSchema` (strict=True, ~35 полей) типизирует каждое поле. Composite Gold (strict=False) — только системные.
3. **paper-id required**: standalone Gold + Filter требуют `paper-id` not null с 40-hex pattern. Composite — не required.
4. **Filter relaxation**: standalone требует `paper-id` + `title` + year range. Composite — только `title`.
5. **Conditional validation**: standalone проверяет `JournalArticle` → title required. Не применяется в composite.
6. **Composite field-validations**: composite добавляет `influential-citation-count: integer/N, ≥0`, а также json-array-проверку для `author-s2-ids`, `author-h-indices`, `citation-contexts`, `affiliation-list`, `author-orcids` и string для `dblp-id`.
7. **Qualified column names**: в composite S2-поля получают префикс `semanticscholar.publication.*`.
8. **Lineage-поля**: composite добавляет 4 поля lineage.
9. **Timeout**: composite использует `timeout-seconds: 7200` (2 часа) для S2 enricher, vs. standalone pipeline timeout определяется по runtime config.
