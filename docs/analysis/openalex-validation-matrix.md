# OpenAlex Publication — Validation Matrix

> Сравнение: standalone-пайплайн `openalex-publication` vs. **enricher** в `composite-publication`.

## 1. DQ-пороги

| Параметр | Standalone | Composite (enricher) |
|----------|-----------|----------------------|
| soft-fail | 0.08 (provider) | 0.10 (composite default) |
| hard-fail | 0.25 (provider) | 0.30 (composite default) |

> Composite пороги мягче, чем standalone OpenAlex.

## 2. Общий Silver-слой

Оба режима записывают в одну таблицу `silver/openalex/publication` и применяют идентичную валидацию:

- **Pandera-схема**: `OpenAlexPublicationSchema` (наследует `PublicationBaseSchema`)
- **DQ-конфиг**: `configs/quality/entities/openalex/publication.yaml`
- **Provider DQ**: `configs/quality/providers/openalex.yaml`

## 3. Матрица валидации полей

Обозначения: **S** — Silver (Pandera + DQ), **G** — Gold-контракт, **F** — Gold-фильтр.

### Первичный ключ и идентификаторы

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `openalex-id` | **S**: str/NN, pattern `^W\d+$` (Pandera + DQ) · **G**: str/NN (strict) · **F**: required | **S**: идентично · **G**: strict=False — нет поле-проверки · **F**: не required |
| `doi` | **S**: str/N, DOI pattern `^10\.\d{4,}/\S+$` (Pandera + DQ) · **G**: str/N, DOI pattern (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `pmid` | **S**: str/N, pattern `^[1-9]\d*$` (base); DQ: range 1–10B · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `pmc-id` | **S**: str/N, pattern `^PMC\d+$` (base) · **G**: отсутствует в Gold · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `mag-id` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: string/N · **F**: — |

### Основной контент

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `title` | **S**: str/N; DQ: max-length 2000, not-null (warn), non-empty (warn); title-not-empty (Pandera) · **G**: str/N (strict) · **F**: required | **S**: идентично · **G**: strict=False · **F**: required (composite `gold-filters`) |
| `abstract` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `authors` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `affiliation-list` | **S**: str/N (base, JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: json-array/N · **F**: — |
| `author-orcids` | **S**: str/N (base); ORCID format check · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: json-array/N · **F**: — |
| `author-openalex-ids` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: json-array/N · **F**: — |

### Метаданные публикации

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `publication-type` | **S**: str/N; DQ: enum `[article, book-chapter, book, dataset, dissertation, editorial, letter, review, preprint, other]` · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication-type-unified` | **S**: str/N (base) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication-subclass` | **S**: str/N (base) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication-class` | **S**: str/N, isin `[EXP, REV, PEER]` (base) · **G**: отсутствует · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication-year` | **S**: Int64/N, 1950–2050 (Pandera); DQ: range 1500–2100 · **G**: float/N, 1500–2100, coerce (strict) · **F**: range 1950–2050 | **S**: идентично · **G**: strict=False · **F**: нет range filter |
| `publication-date` | **S**: str/N, pattern `^\d{4}-\d{2}-\d{2}$` (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `language` | **S**: str/N, length 2–3 (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Журнал

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `journal` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `issn` | **S**: str/N, ISSN pattern `^\d{4}-\d{3}[\dX]$` · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publisher` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `volume` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `issue` | **S**: str/N · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Пагинация

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `page-first` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `page-last` | **S**: str/N (base) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Метрики

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `citations-received` | **S**: Int64/N, ≥0 (base); DQ: range ≥0, warn 0–10M · **G**: float/N, ≥0, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `citations-made` | **S**: Int64/N, ≥0 (base); DQ: range ≥0 · **G**: float/N, ≥0, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `fwci` | **S**: float/N, ≥0 (Pandera + DQ) · **G**: float/N, ≥0 (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: float/N, min-value=0.0 · **F**: — |

### Качество данных

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `is-retracted` | **S**: bool/NN (Pandera, non-nullable) · **G**: bool/NN, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: boolean/NN · **F**: — |

### Open Access

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `is-oa` | **S**: bool/N (base) · **G**: bool/N, coerce (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `oa-status` | **S**: str/N, isin `[gold, green, hybrid, bronze, closed]` · **G**: str/N, isin OA-STATUS (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Темы и классификация

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `subject-topics` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: json-array/N · **F**: — |
| `primary-topic` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: json-object/N · **F**: — |
| `subject-mesh` | **S**: str/N (JSON) · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `subject-keywords` | **S**: str/N (JSON) · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Гранты и институции

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `grants` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: json-array/N · **F**: — |
| `institution-ids` | **S**: str/N (JSON) · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: json-array/N · **F**: — |
| `institution-country-codes` | **S**: str/N (JSON) · **G**: object/N (strict) · **F**: — | **S**: идентично · **G**: strict=False; composite `field-validations`: json-array/N · **F**: — |
| `ror-ids` | **S**: str/N (JSON) · **G**: str/N (strict) · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Системные поля

| Поле | Standalone | Composite (enricher) |
|------|-----------|----------------------|
| `-source` | **S**: str/NN, eq `"openalex"` · **G**: str/NN (strict) · **F**: — | **S**: идентично · **G**: str/N (composite ослаблено) · **F**: — |
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
| `publication-identifiable` | `openalex-id` AND `title` — all-present (error) | Не применяется на composite level |

## 5. Conditional валидации

| Правило | Standalone | Composite |
|---------|-----------|-----------|
| `article-requires-title` | Если `type` in `[article, review]` → title not null (error) | Не применяется на composite level |

## 6. Gold-фильтры

| Параметр | Standalone | Composite |
|----------|-----------|-----------|
| required-fields | `openalex-id`, `title` | `title` |
| column filter | — | — |
| range filter | `publication-year: 1950–2050` | — |

## 7. Ключевые различия

1. **Strict vs. Loose Gold**: standalone `OpenAlexPublicationGoldSchema` (strict=True, ~45 полей) проверяет каждое поле. Composite Gold (strict=False) — только системные.
2. **openalex-id required**: standalone Gold и Filter требуют `openalex-id`. В composite — не required.
3. **Filter relaxation**: standalone требует `openalex-id` + `title` + year range. Composite — только `title`.
4. **DQ-пороги мягче в composite**: standalone (soft=0.08, hard=0.25) → composite (soft=0.10, hard=0.30).
5. **Composite field-validations**: composite добавляет типизацию JSON-полей (`subject-topics`, `primary-topic`, `grants`, `institution-ids`, `institution-country-codes`, `author-orcids`, `author-openalex-ids`, `affiliation-list`), а также `is-retracted: boolean/NN` и `fwci: float/N, ≥0`.
6. **Qualified column names**: в composite OpenAlex-поля получают префикс `openalex.publication.*`.
7. **Lineage-поля**: composite добавляет 4 поля lineage.
8. **Gold type coercion**: standalone Gold использует `coerce=True` для int→float (nullable ints). Composite Gold тоже использует coerce=True, но не проверяет business-поля.
