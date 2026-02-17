# ADR-035: JSON Field Typing Policy (Silver ↔ Gold)

**Status:** Accepted
**Date:** 2026-02-17
**Decision makers:** @BioETL-Team
**Related:** ADR-018, ADR-034

## Context

В текущем коде JSON-like поля представлены непоследовательно:

- часть полей хранится как canonical JSON string (`pa.string()` / `Series[str]`)
- часть — как native list/object (`pa.list_(...)` / `Series[object]`)

Из-за этого возникают типовые расхождения между `src/bioetl/infrastructure/schemas/silver.py` и `src/bioetl/domain/contracts/gold/*.py`, что повышает риск ошибок strict validation.

## The Decision

Для JSON-like полей вводится единый стандарт:

1. **MUST**: Silver и Gold используют **canonical JSON string в обоих слоях**.
1. **MUST**: сериализация выполняется как:
   `json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True)`.
1. **MUST**: отсутствие значения представляется `NULL`.
1. **MUST NOT**: новые JSON-like поля задавать как `pa.list_(...)` или `Series[object]`.
1. **MAY (временно)**: legacy поля native list/object остаются до controlled migration.

## Appendix A: Inventory (required scope)

Полная инвентаризация JSON-like полей и статус согласованности типов размещены в:

- `docs/03-data-model/json-field-typing-inventory.md`

### A.1 Ключевые расхождения типов (MISMATCH)

- `chemicals`: Silver `canonical_string`, Gold `native_object`
- `databanks`: Silver `canonical_string`, Gold `native_object`
- `gene_symbols`: Silver `canonical_string`, Gold `native_object`
- `publication_types`: mixed on both layers (`canonical_string` + `native`)

### A.2 Legacy, но согласованные native-типы (требуют миграции)

- `component_accessions`, `component_ids`, `component_types`, `component_relationships`
- `protein_classification_ids`, `alternative_id`, `content_domain_domains`
- `institution_ids`, `institution_country_codes`, `subject_keywords`, `subject_mesh`, `gene_names`

### A.3 Уже согласованные canonical string поля

Примеры: `authors`, `affiliation_list`, `variant_sequence_json`, `features_json`,
`all_mappings`, `citation_contexts`, `subject_topics`, `primary_topic`,
`references`, `issn_list`, `ror_ids`, `chembl_ids`, `drugbank_ids`, `go_terms`.

## Breaking Impact

Перевод legacy native list/object полей в canonical JSON string является **breaking change** для downstream, которые:

- ожидают Python list/object после чтения Parquet/Delta;
- используют Pandera контракты с `Series[object]`.

Риски:

- поломка BI/ML скриптов с `.explode()` без явного `json.loads()`;
- падение strict validation при смешанном наборе контрактов;
- временный dual-compat слой в потребителях.

## Backfill Strategy

1. **Phase 0 (inventory + freeze)**
   - Заморозить добавление новых native list/object JSON-like полей.
1. **Phase 1 (dual-read)**
   - Gold transformers читают оба представления (list/object и string) с нормализацией в canonical string.
1. **Phase 2 (backfill)**
   - Перезаписать Silver/Gold таблицы по сущностям с legacy native types.
   - Для backfill использовать `run_type=backfill` с exclusive lock.
1. **Phase 3 (strict enforcement)**
   - Удалить `Series[object]` из Gold контрактов для JSON-like полей.
   - Включить fail-fast в schema checks при обнаружении native list/object.

## Delta Migration Steps

1. Добавить migration notebook/script:
   - read Delta table;
   - для JSON-like legacy columns выполнить каноническую сериализацию (`to_json` + sorting keys where applicable);
   - write to shadow table `*_v2` (Delta).
1. Сверить row-count, null-rate и content hash стабильность для non-JSON полей.
1. Переключить readers на `*_v2`.
1. Выполнить smoke validation через Gold Pandera contracts.
1. Архивировать старую таблицу, обновить catalog pointers.

## Consequences

### Positive

- Единая типизация JSON-like полей в Silver/Gold.
- Детерминированная strict validation.
- Меньше provider-specific исключений в трансформерах.

### Negative

- Требуется backfill и обновление downstream-кода.
- На миграционный период повышается сложность (dual-read).

## Related ADRs

- [ADR-018](ADR-018-gold-strict-validation.md): strict validation опирается на консистентные типы.
- [ADR-034](ADR-034-schema-domain-pairs.md): выравнивание контрактов между слоями.
