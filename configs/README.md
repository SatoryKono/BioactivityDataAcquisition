# configs/

Pipeline, quality, and filter configuration for BioETL.

## Directory Structure

```
configs/
├── base/               # Shared defaults (applied first; unified-friendly)
│   ├── pipeline.yaml   # Pipeline defaults + contract_defaults + filter_defaults
│   └── quality.yaml    # Base DQ thresholds and entity_field_validations
├── providers/          # Optional provider overlays (applied after base)
│   └── {provider}.yaml # Provider DQ/filter defaults; no schema splits
├── entities/           # Canonical unified configs (single YAML per entity)
│   └── {provider}/{entity}.yaml  # pipeline + schema + contracts + quality + filters + hash_policy
├── composites/         # Composite pipeline definitions (seed/enrichers/merge)
├── quality/            # DQ override files (hierarchy; still active)
│   └── entities/{provider}/{entity}.yaml
├── enums/              # Externalized enum value sets
├── _schema/            # JSON Schemas for config validation
└── naming_exceptions.yaml  # Allowed naming convention exceptions and stable public naming surface
```

## 3-Layer Merge Hierarchy

Configuration is assembled by deep-merging base → provider (optional) → entity unified YAML. The entity file is authoritative; base/provider layers only supply defaults. Merge semantics (`config_merge()`): scalar override, list replace, dict deep merge.

### Contract Policy (separate path)

`contract_defaults` in `base/pipeline.yaml` provides `rename_map` and
`hash_exclude` defaults. Entity `contracts:` overrides via shallow merge
(`{**base, **entity}`). Loaded by `contract_policy_loader.py`.

### DQ Config (separate path)

DQ config uses its own 4-layer hierarchy:
`base/quality.yaml → providers/{p}.yaml → entities/{p}/{e}.yaml → inline overrides`

Loaded by `DQConfigLoader`, which merges `entity_field_validations` lists by field name.
The active DQ key-space follows the hierarchical naming used by
`configs/base/quality.yaml`, `configs/providers/{provider}.yaml`, and
`configs/entities/{provider}/{entity}.yaml`: `common_*`,
`provider_field_validations`, and `entity_*`.

### Filter Config (separate path)

Filter defaults from `base/pipeline.yaml` section `filter_defaults` are
merged into entity-level `silver_filters` / `gold_filters` by
`normalize_pipeline_config_payload()`.

### Composite Config (separate path)

Composite pipeline config is loaded from `configs/composites/*.yaml` through
`src/bioetl/infrastructure/config/composite_config_api.py`. External
`dq_overrides.dq_config_file` payloads are merged there before schema
validation; composition-facing modules keep only thin compatibility/access seams.

## Key Config Sections (entity YAML)

| Section | Purpose |
|---------|---------|
| `pipeline` | pipeline_name, provider, entity_type, batch_size, business_primary_keys, sink modes |
| `schema` | column_groups, content_hash include/exclude, silver/gold include_groups/alias_policy |
| `contracts` | primary_key, merge_keys, hash_include/hash_exclude, rename_map (via defaults) |
| `quality` | common/provider/entity validation lists, entity_conditional_validations, key_nullability |
| `filters` | extraction_params, silver_filters, gold_filters |
| `hash_policy` | canonical hash policy for bronze→silver/gold promotion |
| `source` | API-specific params merged from provider-level defaults (no legacy source_file) |

Legacy file-reference keys follow explicit status rules:
- Normative CI/source-of-truth constants for active, retired, and transitional config keys live in `src/bioetl/infrastructure/config/config_ci_contract.py`. Pre-commit `scripts/schema/check_config_invariants.py` and [test_config_ci_invariants.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/architecture/test_config_ci_invariants.py) both import that shared contract.
- Retired now: pipeline `schema_file`, `data_schema_file`, `column_groups_file`, `source_file`, source `batch_size`, source `provider_config.batch_size/page_size/max_url_length/cursor_pagination`, and composite `merge.column_groups_file` are not part of the active runtime contract.
- Required canonical composite contract: composite `composite.version` must be present; YAML files that omit it are no longer accepted by runtime validation.
- Transitional migration-only: pipeline `filter_batch_size` remains a compatibility alias and is deprecated in schema/models.
- Canonical current: provider source `pagination.*` and pipeline `page_size_override`. Pipeline configs may override pagination only through `page_size_override`.

## Relevant Code

| File | Role |
|------|------|
| `src/bioetl/infrastructure/config/pipeline_config_api.py` | Canonical staged pipeline-config merge |
| `src/bioetl/infrastructure/config/composite_config_api.py` | Canonical composite-config load + external DQ merge |
| `src/bioetl/infrastructure/config_merge.py` | Deep merge utility |
| `src/bioetl/infrastructure/config/contract_policy_loader.py` | Contract defaults |
| `src/bioetl/infrastructure/config/dq_config_loader.py` | DQ hierarchy |
| `src/bioetl/infrastructure/config/filter_config_loader.py` | Filter hierarchy |
| `src/bioetl/infrastructure/config/source_config_loader.py` | Source section merge |
