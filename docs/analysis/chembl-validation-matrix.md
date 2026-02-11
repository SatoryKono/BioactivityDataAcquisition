# ChEMBL Publication — Validation Matrix

> Сравнение: standalone-пайплайн `chembl_publication` vs. **seed** в `composite_publication`.

## 1. DQ-пороги

| Параметр | Standalone | Composite (seed) |
|----------|-----------|------------------|
| soft_fail | 0.05 (provider) | 0.10 (composite default) |
| hard_fail | 0.15 (provider) | 0.30 (composite default) |

## 2. Общий Silver-слой

Оба режима записывают в одну таблицу `silver/chembl/publication` и применяют идентичную валидацию:

- **Pandera-схема**: `ChemblPublicationSchema` (наследует `PublicationBaseSchema`)
- **DQ-конфиг**: `configs/dq/entities/chembl/publication.yaml`
- **Provider DQ**: `configs/dq/providers/chembl.yaml`

## 3. Матрица валидации полей

Обозначения: **S** — Silver (Pandera + DQ), **G** — Gold-контракт, **F** — Gold-фильтр.
`NN` = not null, `N` = nullable. Silver-валидация идентична в обоих режимах.

### Первичный ключ и идентификаторы

| Поле | Standalone | Composite (seed) |
|------|-----------|------------------|
| `document_chembl_id` | **S**: str/NN, pattern `^CHEMBL\d+$` (Pandera + DQ) · **G**: нет отдельного Gold-контракта · **F**: required | **S**: идентично · **G**: ожидается как `chembl.publication.document_chembl_id`, strict=False — нет поле-специфичной проверки · **F**: required (composite `required_fields`) |
| `doi` | **S**: str/N, pattern `^10\.\d{4,}/\S+$` (Pandera + DQ) · **G**: — · **F**: не required | **S**: идентично · **G**: qualified имя, strict=False · **F**: не required |
| `pmid` | **S**: str/N, pattern `^[1-9]\d*$` (Pandera); DQ: range 1–10B · **G**: — · **F**: не required | **S**: идентично · **G**: strict=False · **F**: не required |
| `pmc_id` | **S**: str/N, pattern `^PMC\d+$` (base) · **G**: — · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `src_id` | **S**: Int64/N · **G**: — · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Основной контент

| Поле | Standalone | Composite (seed) |
|------|-----------|------------------|
| `title` | **S**: str/N; DQ: max_length 2000, not_null (warn), non-empty pattern (warn); title_not_empty check (Pandera) · **G**: — · **F**: required | **S**: идентично · **G**: strict=False · **F**: required (composite `required_fields` + `gold_filters`) |
| `abstract` | **S**: str/N (base) · **G**: — · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `authors` | **S**: str/N (base, JSON array) · **G**: — · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `affiliation_list` | **S**: str/N (base, JSON array) · **G**: — · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: json_array/N · **F**: — |
| `author_orcids` | **S**: str/N (base); ORCID format check (Pandera) · **G**: — · **F**: — | **S**: идентично · **G**: strict=False; composite `field_validations`: json_array/N · **F**: — |

### Метаданные публикации

| Поле | Standalone | Composite (seed) |
|------|-----------|------------------|
| `publication_type` | **S**: str/N, isin `{PUBLICATION, PATENT, DATASET, BOOK}` (Pandera) · DQ: enum PUBLICATION/BOOK/DATASET/PATENT · **G**: — · **F**: column filter `doc_type=[PUBLICATION]` | **S**: идентично · **G**: strict=False · **F**: нет column filter для type |
| `publication_type_unified` | **S**: str/N (base) · **G**: — · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication_subclass` | **S**: str/N (base) · **G**: — · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication_class` | **S**: str/N, isin `[EXP, REV, PEER]` (base) · **G**: — · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `publication_year` | **S**: Int64/N, 1950–2050 (Pandera); DQ: range 1500–2100 · **G**: — · **F**: range 1950–2050 | **S**: идентично · **G**: strict=False · **F**: нет range filter в composite |
| `publication_date` | **S**: str/N, pattern `^\d{4}-\d{2}-\d{2}$` (base) · **G**: — · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `language` | **S**: str/N, length 2–3 (base) · **G**: — · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `journal` | **S**: str/N (base) · **G**: — · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Пагинация и библиография

| Поле | Standalone | Composite (seed) |
|------|-----------|------------------|
| `volume` | **S**: str/N · **G**: — · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `issue` | **S**: str/N · **G**: — · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `page_first` | **S**: str/N (base) · **G**: — · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `page_last` | **S**: str/N (base) · **G**: — · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Метрики

| Поле | Standalone | Composite (seed) |
|------|-----------|------------------|
| `citations_received` | **S**: Int64/N, ≥0 (base); DQ: range ≥0 + warn 0–10M · **G**: — · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `citations_made` | **S**: Int64/N, ≥0 (base); DQ: range ≥0 · **G**: — · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Open Access

| Поле | Standalone | Composite (seed) |
|------|-----------|------------------|
| `is_oa` | **S**: bool/N (base) · **G**: — · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### ChEMBL-специфичные поля

| Поле | Standalone | Composite (seed) |
|------|-----------|------------------|
| `chembl_release` | **S**: str/N · **G**: — · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |
| `creation_date` | **S**: str/N, ISO date pattern `^\d{4}-\d{2}-\d{2}$` · **G**: — · **F**: — | **S**: идентично · **G**: strict=False · **F**: — |

### Системные поля

| Поле | Standalone | Composite (seed) |
|------|-----------|------------------|
| `_source` | **S**: str/NN, eq `"chembl"` · **G**: — · **F**: — | **S**: идентично · **G**: str/N (composite schema) · **F**: — |
| `_lookup_method` | **S**: str/NN, isin `[direct, doi, pmid, title_fallback, title_only, unknown]` · **G**: — · **F**: — | **S**: идентично · **G**: str/N (composite ослаблено) · **F**: — |
| `_original_id` | **S**: str/N · **G**: — · **F**: — | **S**: идентично · **G**: str/N · **F**: — |
| `entity_id` | **S**: str/NN (base) · **G**: — · **F**: — | **S**: идентично · **G**: str/NN (composite required) · **F**: — |
| `content_hash` | **S**: str/NN, 64-hex (base) · **G**: — · **F**: — | **S**: идентично · **G**: str/NN (composite required) · **F**: — |
| `_dq_warn` | **S**: bool/NN (base) · **G**: — · **F**: — | **S**: идентично · **G**: bool/NN · **F**: — |
| `_dq_error` | **S**: bool/NN (base) · **G**: — · **F**: — | **S**: идентично · **G**: bool/NN · **F**: — |
| `_run_id` | **S**: str/NN (base) · **G**: — · **F**: — | **S**: идентично · **G**: str/NN · **F**: — |
| `_run_type` | **S**: str/NN, isin `[incremental, backfill, rebuild]` (base) · **G**: — · **F**: — | **S**: идентично · **G**: str/NN · **F**: — |
| `_ingestion_ts` | **S**: str/NN, ISO 8601 (base) · **G**: — · **F**: — | **S**: идентично · **G**: str/NN · **F**: — |
| `_index` | **S**: int/NN, ≥0 (base) · **G**: — · **F**: — | **S**: идентично · **G**: int/NN · **F**: — |

### Composite-only поля (отсутствуют в standalone)

| Поле | Standalone | Composite (seed) |
|------|-----------|------------------|
| `_composite_run_id` | — | str/NN (добавляется MergeService) |
| `_source_providers` | — | str/NN, JSON list |
| `_enrichment_status` | — | str/NN, JSON dict |
| `_lineage_created_at` | — | str/NN, ISO timestamp |

## 4. Cross-field валидации

| Правило | Standalone | Composite |
|---------|-----------|-----------|
| `publication_identifiable` | `document_chembl_id` AND `title` — all_present (error) | Нет специфичного cross-field; `required_fields: [document_chembl_id, title]` в DQ-конфиге |
| `has_cross_reference` | `pmid` OR `doi` — any_present (warn) | Не применяется на уровне composite |

## 5. Conditional валидации

| Правило | Standalone | Composite |
|---------|-----------|-----------|
| `publication_requires_title` | Если `doc_type == PUBLICATION` → title not null (error) | Не применяется (нет conditional в composite DQ) |

## 6. Gold-фильтры

| Параметр | Standalone | Composite |
|----------|-----------|-----------|
| required_fields | `document_chembl_id`, `doc_type`, `title` | `title` |
| column filter | `doc_type: [PUBLICATION]` | — |
| range filter | `publication_year: 1950–2050` | — |

## 7. Ключевые различия

1. **Нет отдельного Gold-контракта для ChEMBL**: standalone-пайплайн не имеет `ChEMBLPublicationGoldSchema` — валидация Gold-слоя опирается только на filter rules.
2. **Composite Gold — strict=False**: `CompositePublicationGoldSchema` валидирует только системные/lineage-поля; бизнес-поля не проверяются на уровне Gold.
3. **Ослабленные фильтры в composite**: standalone фильтрует по `doc_type=[PUBLICATION]` и `publication_year: 1950–2050`; composite требует только `title`.
4. **Повышенные DQ-пороги**: composite (soft=0.10, hard=0.30) мягче, чем standalone ChEMBL (soft=0.05, hard=0.15).
5. **Qualified column names**: в composite все ChEMBL-поля получают префикс `chembl.publication.*`.
6. **Lineage-поля**: composite добавляет 4 поля lineage (`_composite_run_id`, `_source_providers`, `_enrichment_status`, `_lineage_created_at`).
