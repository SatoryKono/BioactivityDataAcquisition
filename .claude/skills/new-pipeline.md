# /new-pipeline

Создание нового ETL-пайплайна для `provider/entity` в текущей архитектуре BioETL (unified configs + GenericPipeline + DI).

## Использование

```text
/new-pipeline [provider] [entity]
```

Примеры:
- `/new-pipeline chembl mechanism`
- `/new-pipeline myprovider publication`

---

## Инструкции для агента

### Шаг 1: Сбор входных данных

Собери/уточни:
1. `provider` (snake_case)
2. `entity` (snake_case, singular)
3. `primary_key` (snake_case)
4. список бизнес-полей (`name:type:nullable`)
5. это новый provider или существующий

### Шаг 2: Валидация before-write

Проверь:
- `configs/entities/{provider}/{entity}.yaml` еще не существует
- naming соответствует snake_case
- для нового provider отсутствует `configs/providers/{provider}.yaml`

### Шаг 3: Создай/обнови обязательные артефакты

#### 3.1 Unified entity config
- `configs/entities/{provider}/{entity}.yaml`
- использовать шаблон из `docs/04-reference/templates/config.yaml.tpl`

#### 3.2 Transformer
- `src/bioetl/application/pipelines/{provider}/{entity}_transformer.py`
- наследование от `BaseTransformer`

#### 3.3 Schemas/contracts
- Silver schema: `src/bioetl/domain/schemas/{provider}/{entity}.py`
- Gold schema: `src/bioetl/domain/contracts/gold/{provider}.py` (create or extend)
- экспорты:
  - `src/bioetl/domain/contracts/gold/__init__.py`
  - `src/bioetl/domain/contracts/__init__.py`

#### 3.4 Composition registration
- `src/bioetl/composition/factories/transformer_factory.py`
  - import transformer
  - `register_transformer("{provider}", "{entity}", TransformerClass)`
- `src/bioetl/composition/factories/pipeline_factories.py`
  - imports transformer/schemas/contracts
  - add `PipelineFactoryConfig(...)` to `PIPELINE_CONFIGS`

#### 3.5 Если provider новый
- создать `configs/providers/{provider}.yaml` (см. `docs/04-reference/templates/provider.yaml.tpl`)
- добавить adapter в `src/bioetl/infrastructure/adapters/{provider}/client.py`
- обновить `src/bioetl/composition/providers/registration.py`:
  - `_create_{provider}_data_source(...)`
  - `ProviderRegistry.register(...)` в `register_all_providers()`

### Шаг 4: Тесты

Минимум:
- `tests/unit/application/pipelines/{provider}/test_{entity}_transformer.py`
- (опционально) integration/e2e для нового provider

### Шаг 5: Верификация

```bash
python scripts/validate_pipeline_configs.py --verbose
python -c "from bioetl.infrastructure.config_loader import load_pipeline_config; load_pipeline_config('{provider}_{entity}'); print('ok')"
python -m pytest tests/architecture/test_registry_contracts.py -q
python -m pytest tests/unit/application/pipelines/{provider}/ -q
```

---

## Быстрый шаблон: Unified Entity Config

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
  cross_field_validations: []
  conditional_validations: []

filters:
  version: "1.0.0"
  provider: {provider}
  entity: {entity}
  input_filter: {enabled: false}
  gold_filters: {required_fields: [{primary_key}], columns: {}}

contracts:
  primary_key: [{primary_key}]
  merge_keys: [{primary_key}]
  rename_map:
    run_id: _run_id
    run_type: _run_type
    source_batch_id: _source_batch_id
    ingestion_ts: _ingestion_ts
    source: _source
  hash_include: []
  hash_exclude: [_ingestion_ts, _run_id, _run_type, _dq_error, _dq_warn]
```

---

## Быстрый шаблон: PipelineFactoryConfig entry

```python
PipelineFactoryConfig(
    pipeline_name="{provider}_{entity}",
    provider="{provider}",
    entity_type="{entity}",
    transformer_class={Provider}{Entity}Transformer,
    silver_schema={PROVIDER}_{ENTITY}_SCHEMA,
    gold_schema={Provider}{Entity}GoldSchema,
    pandera_silver_schema={Provider}{Entity}Schema,
)
```

---

## Naming Convention

- Pipeline id: `{provider}_{entity}`
- Transformer class: `{Provider}{Entity}Transformer`
- Gold schema class: `{Provider}{Entity}GoldSchema`
- Silver schema class: `{Provider}{Entity}Schema`

