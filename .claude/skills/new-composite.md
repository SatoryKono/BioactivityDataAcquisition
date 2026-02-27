# /new-composite

Создание нового composite pipeline для BioETL.

## Использование

```
/new-composite [name]
```

**Примеры:**
```
/new-composite protein                      # новый composite для protein
/new-composite                              # интерактивный режим
```

---

## Инструкции для Claude

### Шаг 1: Сбор информации

Если аргумент не передан, запросить через AskUserQuestion:

1. **Composite name** — snake_case, singular (e.g., `protein`, `pathway`, `interaction`)
2. **Seed pipeline** — какой pipeline будет seed (e.g., `uniprot_protein`)
3. **Output keys** — primary keys для join (e.g., `[protein_id, uniprot_id]`)
4. **Enrichers** — список enricher pipelines (e.g., `chembl_target`, `openalex_publication`)
5. **Merge strategy** — `left_outer` (default) | `inner` | `union`
6. **Conflict resolution** — `seed_priority` (default) | `enricher_priority` | `coalesce`

### Шаг 2: Валидация

- [ ] Composite config `configs/composites/{name}.yaml` НЕ существует
- [ ] Seed pipeline существует в `configs/entities/`
- [ ] Все enricher pipelines существуют в `configs/entities/`
- [ ] Output keys — валидные поля seed entity

### Шаг 3: Изучить существующие composites

```bash
ls configs/composites/
```

Прочитать один для reference (например `configs/composites/activity.yaml`).

### Шаг 4: Загрузить JSON-схему

Прочитать `configs/_schema/composite.json` для валидации структуры.

### Шаг 5: Генерация composite config

Создать `configs/composites/{name}.yaml` по шаблону:

```yaml
composite:
  name: composite_{name}
  version: "1.0.0"

  seed:
    pipeline: {seed_pipeline}
    output_keys: [{output_keys}]
    silver_table: silver/{provider}/{entity}

  dependencies: []  # если нужны зависимости — добавить

  enrichers:
    - pipeline: {enricher_pipeline}
      join_keys: [{join_keys}]
      required: false
      timeout_seconds: 600
      silver_table: silver/{enricher_provider}/{enricher_entity}
      cardinality: many_to_one
      fallback_strategy: skip

  merge:
    strategy: {merge_strategy}
    conflict_resolution: {conflict_resolution}
    preserve_all_sources: false
    output:
      silver: data/output/silver/composite/{name}
      gold: data/output/gold/composite/{name}
    field_priorities: {{}}
    column_groups: []
    # column_groups_file: configs/composites/field_groups/{name}.yaml

  dq_overrides:
    soft_fail_threshold: 0.1
    hard_fail_threshold: 0.3

  execution:
    max_concurrency: 2
    checkpoint_enabled: true
    retry:
      max_attempts: 3
      backoff_multiplier: 2.0

  lineage:
    track_field_sources: true
    track_timestamps: true
    track_status: true
```

### Шаг 6: Создать Gold filter config (опционально)

Если нужны фильтры, создать `configs/filters/entities/composite/{name}.yaml`.

### Шаг 7: Валидация

```bash
# Валидация против JSON-схемы
uv run python -c "
import json, yaml, jsonschema
schema = json.load(open('configs/_schema/composite.json'))
data = yaml.safe_load(open('configs/composites/{name}.yaml'))
jsonschema.validate(data, schema)
print('OK: config valid')
"
```

### Шаг 8: Обновить golden master

```bash
UPDATE_SNAPSHOTS=1 uv run python -m pytest tests/architecture/test_config_golden_master.py -v
```

### Шаг 9: Вывести итог

```
Created composite pipeline: {name}
Files:
  - configs/composites/{name}.yaml
  - configs/filters/entities/composite/{name}.yaml (если создан)

Next steps:
  1. Настроить column_groups для семантической группировки полей
  2. Определить field_priorities для конфликтующих полей
  3. Запустить: uv run python -m bioetl composite {name}
  4. Обновить документацию: docs/04-reference/pipelines/composite-{name}.md
```
