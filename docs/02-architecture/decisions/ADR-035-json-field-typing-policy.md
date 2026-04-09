______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-035: JSON Field Typing Policy (Silver ↔ Gold)

**Date:** 2026-02-17
**Status:** Accepted
**Decision makers:** @BioETL-Team
**Related:** RULES.md §Schema Typing Policy, ADR-018, ADR-034

## Context

В Silver/Gold схемах исторически смешивались 2 подхода для JSON-like полей:

- `Series[str]` с JSON-serialized payload (`pa.string()`)
- `Series[object]` с нативными `list/dict` (`pa.list-(...)`)

Это приводило к drift по типам между провайдерами, нестабильному контракту для downstream и неоднозначности в трансформерах. Повышается риск ошибок strict validation.

## Decision

Стандартизировать JSON-like поля в Silver и Gold как **canonical JSON string**.

### Canonical format

- Тип в Pandera: `Series[str]`.
- **Serialization (MUST)**: canonical JSON helper with stable key ordering, compact separators, and ASCII-safe deterministic output.
- **Null semantics (MUST)**: отсутствие данных хранится как `NULL` (`None`).
- **MUST NOT**: новые JSON-like поля задавать как `pa.list-(...)` или `Series[object]`.
- **MAY (временно)**: legacy поля native list/object остаются до controlled migration.

### Non-goals

- Нативные nested/list типы в Delta для Silver/Gold в рамках текущей ADR не вводятся.

## Appendix A: Inventory (required scope)

Полная инвентаризация JSON-like полей и статус согласованности типов размещены в:

- `docs/03-data-model/json-field-typing-inventory.md`

### A.1 Ключевые расхождения типов (MISMATCH)

- `chemicals`: Silver `canonical-string`, Gold `native-object`
- `databanks`: Silver `canonical-string`, Gold `native-object`
- `gene-symbols`: Silver `canonical-string`, Gold `native-object`
- `publication-types`: mixed on both layers (`canonical-string` + `native`)

### A.2 Legacy, но согласованные native-типы (требуют миграции)

- `component-accessions`, `component-ids`, `component-types`, `component-relationships`
- `protein-classification-ids`, `alternative-id`, `content-domain-domains`
- `institution-ids`, `institution-country-codes`, `subject-keywords`, `subject-mesh`, `gene-names`

### A.3 Уже согласованные canonical string поля

Примеры: `authors`, `affiliation-list`, `variant-sequence-json`, `features-json`,
`all-mappings`, `citation-contexts`, `subject-topics`, `primary-topic`,
`references`, `issn-list`, `ror-ids`, `chembl-ids`, `drugbank-ids`, `go-terms`.

### Reproducible inventory command

```bash
python - <<'PY'
import re
from pathlib import Path
for root in (Path('src/bioetl/domain/schemas'), Path('src/bioetl/domain/contracts/gold')):
    for p in sorted(root.rglob('*.py')):
        lines=p.read-text().splitlines()
        for i,l in enumerate(lines,1):
            m=re.match(r'\s*([a-zA-Z-][a-zA-Z0-9-]*):\s*Series\[([^\]]+)\]', l)
            if not m:
                continue
            field, typ = m.groups()
            block='\n'.join(lines[max(0,i-2):min(len(lines),i+4)])
            if 'JSON' in block or field.endswith('-list'):
                print(f"{p}:{field}:Series[{typ}]")
PY
```

## Transformer alignment

Трансформеры теперь всегда сериализуют JSON-like массивы/объекты до строки перед Silver:

- ChEMBL Target / TargetComponent
- CrossRef Publication
- OpenAlex Publication
- PubMed Publication
- UniProt Protein (`gene-names`)

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
   - Для backfill использовать `run-type=backfill` с exclusive lock.
1. **Phase 3 (strict enforcement)**
   - Удалить `Series[object]` из Gold контрактов для JSON-like полей.
   - Включить fail-fast в schema checks при обнаружении native list/object.

## Delta Migration Steps

1. Добавить migration notebook/script:
   - read Delta table;
   - для JSON-like legacy columns выполнить каноническую сериализацию;
   - write to shadow table `*-v2` (Delta).
1. Сверить row-count, null-rate и content hash стабильность для non-JSON полей.
1. Переключить readers на `*-v2`.
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

## References

- [ADR-018](ADR-018-gold-strict-validation.md): strict validation опирается на консистентные типы.
- [ADR-034](ADR-034-schema-domain-pairs.md): выравнивание контрактов между слоями.

## Compliance

| Control      | Requirement                                                                | Status | Evidence                              |
| ------------ | -------------------------------------------------------------------------- | ------ | ------------------------------------- |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-035-json-field-typing-policy.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                            |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                      |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria`  |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                          |

## Rollout

- Rollout steps MUST be sequenced before broad adoption.
- Documentation, configuration, and test surfaces SHOULD be updated in the same change set when the decision is implemented.
- Breaking or migration-sensitive adoption SHOULD include an explicit transition window.

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [ ] The decision is documented with current status, date, and owner metadata.
- [ ] The implementation path or adoption boundary is testable and linked from the ADR.
- [ ] Supersession or migration impact is documented when the decision changes an earlier posture.
- [ ] Related docs, contracts, and operational guidance are aligned with this ADR.
