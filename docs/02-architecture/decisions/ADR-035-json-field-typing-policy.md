# ADR-035: JSON Field Typing Policy (Silver ↔ Gold)

**Status:** Accepted
**Date:** 2026-02-17
**Decision makers:** @BioETL-Team
**Related:** RULES.md §Schema Typing Policy, ADR-018, ADR-034

## Context

В Silver/Gold схемах исторически смешивались 2 подхода для JSON-like полей:

- `Series[str]` с JSON-serialized payload (`pa.string()`)
- `Series[object]` с нативными `list/dict` (`pa.list_(...)`)

Это приводило к drift по типам между провайдерами, нестабильному контракту для downstream и неоднозначности в трансформерах. Повышается риск ошибок strict validation.

## Decision

Стандартизировать JSON-like поля в Silver и Gold как **canonical JSON string**.

### Canonical format

- Тип в Pandera: `Series[str]`.
- **Serialization (MUST)**: `json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True)`.
- **Null semantics (MUST)**: отсутствие данных хранится как `NULL` (`None`).
- **MUST NOT**: новые JSON-like поля задавать как `pa.list_(...)` или `Series[object]`.
- **MAY (временно)**: legacy поля native list/object остаются до controlled migration.

### Non-goals

- Нативные nested/list типы в Delta для Silver/Gold в рамках текущей ADR не вводятся.

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

### Reproducible inventory command

```bash
python - <<'PY'
import re
from pathlib import Path
for root in (Path('src/bioetl/domain/schemas'), Path('src/bioetl/domain/contracts/gold')):
    for p in sorted(root.rglob('*.py')):
        lines=p.read_text().splitlines()
        for i,l in enumerate(lines,1):
            m=re.match(r'\s*([a-zA-Z_][a-zA-Z0-9_]*):\s*Series\[([^\]]+)\]', l)
            if not m:
                continue
            field, typ = m.groups()
            block='\n'.join(lines[max(0,i-2):min(len(lines),i+4)])
            if 'JSON' in block or field.endswith('_list'):
                print(f"{p}:{field}:Series[{typ}]")
PY
```

## Transformer alignment

Трансформеры теперь всегда сериализуют JSON-like массивы/объекты до строки перед Silver:

- ChEMBL Target / TargetComponent
- CrossRef Publication
- OpenAlex Publication
- PubMed Publication
- UniProt Protein (`gene_names`)

## Breaking Impact

Перевод legacy native list/object полей в canonical JSON string является **breaking change** для downstream, которые:

- ожидают Python list/object после чтения Parquet/Delta;
- используют Pandera контракты с `Series[object]`.

Риски:

- поломка BI/ML скриптов с `.explode()` без явного `json.loads()`;
- падение strict validation при смешанном наборе контрактов;
- временный dual-compat слой в потребителях.

### Compatibility window

- **14 дней** dual-read window.
- Consumers MUST поддерживать чтение обоих форматов: legacy object + canonical JSON string.
- По окончании окна legacy-формат удаляется из контрактов.

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
   - для JSON-like legacy columns выполнить каноническую сериализацию;
   - write to shadow table `*_v2` (Delta).
1. Сверить row-count, null-rate и content hash стабильность для non-JSON полей.
1. Переключить readers на `*_v2`.
1. Выполнить smoke validation через Gold Pandera contracts.
1. Архивировать старую таблицу, обновить catalog pointers.

## Consequences

### Positive

- Единый контракт типов по провайдерам.
- Прогнозируемая сериализация и проще downstream parsing.
- Исключение `Series[object]` drift в Gold strict validation.
- Детерминированная strict validation.
- Меньше provider-specific исключений в трансформерах.

### Trade-offs

- Нужно явное `json.loads()` у downstream клиентов.
- Требуется backfill и обновление downstream-кода.
- На миграционный период повышается сложность (dual-read).

## Related ADRs

- [ADR-018](ADR-018-gold-strict-validation.md): strict validation опирается на консистентные типы.
- [ADR-034](ADR-034-schema-domain-pairs.md): выравнивание контрактов между слоями.
