# ADR-035: JSON Field Typing Policy

**Status:** Accepted
**Date:** 2026-02-17
**Decision makers:** @BioETL-Team
**Related:** RULES.md §Schema Typing Policy, ADR-018

## Context

В Silver/Gold схемах исторически смешивались 2 подхода для JSON-like полей:

- `Series[str]` с JSON-serialized payload;
- `Series[object]` с нативными `list/dict`.

Это приводило к drift по типам между провайдерами, нестабильному контракту для downstream и неоднозначности в трансформерах.

## Decision

Стандартизировать JSON-like поля в Silver и Gold как **canonical JSON string**.

### Canonical format

- Тип в Pandera: `Series[str]`.
- Сериализация: canonical compact JSON (`sort_keys=True`, UTF-8).
- Пустые коллекции: `None`.

### Non-goals

- Нативные nested/list типы в Delta для Silver/Gold в рамках текущей ADR не вводятся.

## Inventory (Silver + Gold)

Инвентарь JSON-like полей зафиксирован по схемам Silver (`src/bioetl/domain/schemas/**`) и Gold (`src/bioetl/domain/contracts/gold/**`).

### Поля, приведённые к единому стандарту в этом решении

#### Silver

- `chembl.target`: `component_accessions`, `component_descriptions`, `component_ids`, `component_types`, `component_relationships`.
- `chembl.target_component`: `protein_classification_ids`.
- `crossref.publication`: `content_domain_domains`, `alternative_id`.

#### Gold

- `gold.chembl`: `component_accessions`, `component_ids`, `component_types`, `component_relationships`, `protein_classification_ids`.
- `gold.publications`: `publication_type`, `publication_types`, `subject_keywords`, `subject_mesh`, `chemicals`, `databanks`, `gene_symbols`, `content_domain_domains`, `alternative_id`, `institution_ids`, `institution_country_codes`.
- `gold.uniprot`: `gene_names`.

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

## Breaking impact

Это **breaking change** для потребителей, ожидающих нативные `list/dict` в DataFrame/Delta для перечисленных полей.

### Compatibility window

- **14 дней** dual-read window.
- Consumers MUST поддерживать чтение обоих форматов: legacy object + canonical JSON string.
- По окончании окна legacy-формат удаляется из контрактов.

## Delta migration / backfill plan

1. Обновить Pandera контракты на `Series[str]`.
1. Деплой трансформеров с canonical serialization.
1. Запустить backfill для затронутых таблиц Silver и Gold:
   - `run_type=backfill` с `:exclusive` lock.
   - Перезапись/merge partition-by-partition.
1. Провести валидацию:
   - schema pass;
   - выборочный `json.loads()` для migrated columns;
   - compare row counts/content hash invariants.
1. По завершении окна совместимости отключить legacy reader paths.

## Consequences

### Positive

- Единый контракт типов по провайдерам.
- Прогнозируемая сериализация и проще downstream parsing.
- Исключение `Series[object]` drift в Gold strict validation.

### Trade-offs

- Нужно явное `json.loads()` у downstream клиентов.
- Временный рост сложности из-за dual-read периода.
