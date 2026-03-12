---
description: "Создание нового ETL-пайплайна для провайдера и сущности в BioETL. Генерирует файлы по шаблонам."
---

# /new-pipeline

## Использование
```
/new-pipeline [provider] [entity]
```

## Инструкции

### Шаг 1: Сбор данных
Collect: `provider` (snake_case), `entity` (snake_case, singular), `primary_key`, business fields, new/existing provider.

### Шаг 2: Валидация
- `configs/entities/{provider}/{entity}.yaml` must NOT exist
- Naming must be snake_case

### Шаг 3: Создать артефакты

**3.1 Config:** `configs/entities/{provider}/{entity}.yaml` — use template:
```yaml
version: "1.0.0"
provider: {provider}
entity: {entity}
pipeline:
  pipeline_name: {provider}_{entity}
  provider: {provider}
  entity_type: {entity}
  business_primary_keys: [{primary_key}]
schema:
  content_hash: {include: [], exclude: []}
  column_groups: []
  silver: {include_groups: [system, business, dq], exclude_fields: [], alias_policy: preserve}
  gold: {include_groups: [system, business], exclude_fields: [_dq_*, _source_batch_id, _index], alias_policy: canonical}
quality:
  version: "1.0.0"
  provider: {provider}
  entity: {entity}
  field_validations: []
contracts:
  primary_key: [{primary_key}]
  merge_keys: [{primary_key}]
  rename_map: {run_id: _run_id, run_type: _run_type, source_batch_id: _source_batch_id, ingestion_ts: _ingestion_ts, source: _source}
  hash_include: []
  hash_exclude: [_ingestion_ts, _run_id, _run_type, _dq_error, _dq_warn]
```

**3.2 Transformer:** `src/bioetl/application/pipelines/{provider}/{entity}_transformer.py` — inherit `BaseTransformer`

**3.3 Schemas:** Silver: `src/bioetl/domain/schemas/{provider}/{entity}.py`, Gold: `src/bioetl/domain/contracts/gold/{provider}.py`

**3.4 Registration:** Update `composition/factories/transformer_factory.py` and `pipeline_factories.py`

**3.5 If new provider:** create provider config, adapter client, update `composition/providers/registration.py`

### Шаг 4: Tests
`tests/unit/application/pipelines/{provider}/test_{entity}_transformer.py`

### Шаг 5: Verify
```bash
python -m scripts.schema validate-configs --verbose
python -m pytest tests/architecture/test_registry_contracts.py -q
python -m pytest tests/unit/application/pipelines/{provider}/ -q
```

## Naming Convention
- Pipeline: `{provider}_{entity}`
- Transformer: `{Provider}{Entity}Transformer`
- Gold schema: `{Provider}{Entity}GoldSchema`
- Silver schema: `{Provider}{Entity}Schema`
