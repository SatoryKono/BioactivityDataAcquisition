______________________________________________________________________

## description: Валидация YAML-конфигов BioETL против JSON-схем и golden master. Действия: validate, golden-master, diff, list. Пример: /config-validate validate chembl

# /config-validate

Валидация YAML-конфигураций BioETL против JSON-схем и golden master.

## Использование

```
/config-validate [action] [target]
```

**Действия:**

- `validate` — валидировать конфиги против JSON-схем (по умолчанию)
- `golden-master` — проверить/обновить golden master snapshot
- `diff` — показать различия между конфигами и ожидаемыми значениями
- `list` — перечислить все конфиги с их статусом валидации

**Target (опционально):**

- `all` — все конфиги (по умолчанию)
- `{provider}` — конфиги конкретного провайдера (chembl, pubmed, etc.)
- `composites` — только composite конфиги
- `entities` — только entity конфиги
- Путь к конкретному YAML файлу

______________________________________________________________________

## Инструкции

### Действие: `validate` (по умолчанию)

**Шаг 1: Определить scope**

| Target       | Paths                                                                             |
| ------------ | --------------------------------------------------------------------------------- |
| `all`        | `configs/entities/`, `configs/composites/`, `configs/providers/`, `configs/base/` |
| `{provider}` | `configs/entities/{provider}/`, `configs/providers/{provider}.yaml`               |
| `composites` | `configs/composites/`                                                             |
| `entities`   | `configs/entities/`                                                               |

**Шаг 2: Загрузить JSON-схемы**

- Pipeline schema: `configs/_schema/pipeline.json`
- Composite schema: `configs/_schema/composite.json`

**Шаг 3: Валидация**

```bash
# Entity конфиги против pipeline schema
for f in configs/entities/{target}/*.yaml; do
  uv run python -c "
import json, yaml, jsonschema
schema = json.load(open('configs/_schema/pipeline.json'))
data = yaml.safe_load(open('$f'))
jsonschema.validate(data, schema)
print(f'OK: $f')
"
done

# Composite конфиги против composite schema
for f in configs/composites/*.yaml; do
  uv run python -c "
import json, yaml, jsonschema
schema = json.load(open('configs/_schema/composite.json'))
data = yaml.safe_load(open('$f'))
jsonschema.validate(data, schema)
print(f'OK: $f')
"
done
```

**Шаг 4: Проверить обязательные поля**

Entity конфиги: `pipeline`, `schema` (bronze/silver/gold), `quality` (DQ rules), `hash_policy`.
Composite конфиги: `seed` с `pipeline`+`output_keys`, `merge` с `strategy`+`output`, semver `version`.

**Шаг 5: Отчёт**

```
Config Validation Report
========================
Provider: {provider}
Date: YYYY-MM-DD

| Config File | Schema | Status | Errors |
|-------------|--------|:------:|--------|
| chembl/activity.yaml | pipeline.json | ✅ | — |

Total: N valid, M invalid
```

### Действие: `golden-master`

```bash
# Проверить
uv run python -m pytest tests/architecture/test_config_golden_master.py -v --tb=short
# Обновить (если --update)
UPDATE_SNAPSHOTS=1 uv run python -m pytest tests/architecture/test_config_golden_master.py
```

### Действие: `diff`

```bash
uv run python -m pytest tests/architecture/test_config_golden_master.py -v --tb=long 2>&1
```

### Действие: `list`

```bash
find configs/ -name "*.yaml" -type f | sort
```

Для каждого показать: путь, тип (entity/composite/provider/base), провайдер, размер.
