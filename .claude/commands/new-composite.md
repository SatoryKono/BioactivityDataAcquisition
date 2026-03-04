---
description: "Создание нового composite pipeline BioETL. Генерирует YAML-конфиг с seed, enrichers, merge strategy."
---

# /new-composite

## Использование
```
/new-composite [name]
```

## Инструкции

### Шаг 1: Сбор информации
Ask via AskUserQuestion: composite name (snake_case), seed pipeline, output keys, enrichers, merge strategy (`left_outer`|`inner`|`union`), conflict resolution (`seed_priority`|`enricher_priority`|`coalesce`).

### Шаг 2: Валидация
- `configs/composites/{name}.yaml` must NOT exist
- Seed and enricher pipelines must exist in `configs/entities/`

### Шаг 3: Study existing
```bash
ls configs/composites/
```
Read one for reference. Load `configs/_schema/composite.json`.

### Шаг 4: Generate config
Create `configs/composites/{name}.yaml`:
```yaml
composite:
  name: composite_{name}
  version: "1.0.0"
  seed:
    pipeline: {seed_pipeline}
    output_keys: [{output_keys}]
    silver_table: silver/{provider}/{entity}
  enrichers:
    - pipeline: {enricher}
      join_keys: [{join_keys}]
      required: false
      timeout_seconds: 600
      cardinality: many_to_one
      fallback_strategy: skip
  merge:
    strategy: {merge_strategy}
    conflict_resolution: {conflict_resolution}
    output:
      silver: data/output/silver/composite/{name}
      gold: data/output/gold/composite/{name}
  dq_overrides:
    soft_fail_threshold: 0.1
    hard_fail_threshold: 0.3
  execution:
    max_concurrency: 2
    checkpoint_enabled: true
    retry: {max_attempts: 3, backoff_multiplier: 2.0}
```

### Шаг 5: Validate
```bash
uv run python -c "
import json, yaml, jsonschema
schema = json.load(open('configs/_schema/composite.json'))
data = yaml.safe_load(open('configs/composites/{name}.yaml'))
jsonschema.validate(data, schema)
print('OK')
"
```

### Шаг 6: Update golden master
```bash
UPDATE_SNAPSHOTS=1 uv run python -m pytest tests/architecture/test_config_golden_master.py -v
```
