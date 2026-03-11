# configs/

Pipeline, quality, and filter configuration for BioETL.

## Directory Structure

```
configs/
├── base/               # Shared defaults (merged first)
│   ├── pipeline.yaml   # Pipeline defaults + contract_defaults + filter_defaults
│   └── quality.yaml    # Base DQ thresholds and field validations
├── providers/          # Provider-level overrides (merged second)
│   └── {provider}.yaml # Source config + provider DQ + provider filters
├── entities/           # Entity-level configs (merged last, highest priority)
│   └── {provider}/
│       └── {entity}.yaml  # Unified: pipeline + schema + contracts + quality + filters
├── composites/         # Composite pipeline definitions (seed/enrichers/merge)
├── quality/            # Standalone DQ override files
│   └── entities/
│       └── {provider}/{entity}.yaml
├── enums/              # Externalized enum value sets
├── _schema/            # JSON Schemas for config validation
└── naming_exceptions.yaml  # Allowed naming convention exceptions
```

## 3-Layer Merge Hierarchy

Configuration is assembled by deep-merging three layers:

```
base/pipeline.yaml  →  providers/{provider}.yaml  →  entities/{provider}/{entity}.yaml
     (defaults)            (provider overrides)          (entity overrides)
```

**Merge semantics** (via `config_merge()`):
- Scalar values: entity wins over provider wins over base
- Lists: entity replaces (no append)
- Dicts: recursive deep merge

### Contract Policy (separate path)

`contract_defaults` in `base/pipeline.yaml` provides `rename_map` and
`hash_exclude` defaults. Entity `contracts:` section overrides via shallow
merge (`{**base, **entity}`). Loaded by `contract_policy_loader.py`.

### DQ Config (separate path)

DQ config uses its own 4-layer hierarchy:
`base/quality.yaml → providers/{p}.yaml → entities/{p}/{e}.yaml → inline overrides`

Loaded by `DQConfigLoader`, which merges `field_validations` lists by field name.

### Filter Config (separate path)

Filter defaults from `base/pipeline.yaml` section `filter_defaults` are
merged into entity-level `silver_filters` / `gold_filters` by
`normalize_pipeline_config_payload()`.

## Key Config Sections (entity YAML)

| Section | Purpose |
|---------|---------|
| `pipeline` | Pipeline name, provider, entity, batch_size, sink modes |
| `schema` | Column groups, content_hash include/exclude |
| `contracts` | primary_key, merge_keys, hash_include (rename_map from base) |
| `quality` | DQ thresholds, field_validations, required_fields |
| `silver_filters` | Pre-gold filtering rules for Silver layer |
| `gold_filters` | Gold layer column/range/list filters |
| `source` | API-specific: endpoint, params (merged from provider YAML) |

## Relevant Code

| File | Role |
|------|------|
| `src/bioetl/infrastructure/config_loader.py` | Main 3-layer merge |
| `src/bioetl/infrastructure/config_merge.py` | Deep merge utility |
| `src/bioetl/infrastructure/config/contract_policy_loader.py` | Contract defaults |
| `src/bioetl/infrastructure/config/dq_config_loader.py` | DQ hierarchy |
| `src/bioetl/infrastructure/config/filter_config_loader.py` | Filter hierarchy |
| `src/bioetl/infrastructure/config/source_config_loader.py` | Source section merge |
