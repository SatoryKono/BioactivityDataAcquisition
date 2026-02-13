# RF-CONFIG-STRUCTURE: Prompts for Execution

**Companion to:** `RF-CONFIG-STRUCTURE-consolidated.md` v2.0.0
**Date:** 2026-02-13

Each prompt below is a self-contained instruction for an AI agent.
Execute them in order (Phase 1 → 6). Within a phase, steps can be
parallelized where noted.

---

## Phase 1: Code-Level Type Fixes

### Prompt 1.1: Narrow `silver_filters` type

```
TASK: Narrow the type of `silver_filters` field from `SilverFilterConfig | GoldFilterConfig | None`
to `SilverFilterConfig | None` across the entire codebase.

CONTEXT:
- `PipelineConfig.silver_filters` in `src/bioetl/domain/config/pipeline.py:49` currently has
  type `SilverFilterConfig | GoldFilterConfig | None`. The `| GoldFilterConfig` is a type leak —
  Silver filters should always be typed as `SilverFilterConfig`.
- All infrastructure code already wraps Gold configs via `SilverFilterConfig.from_gold_filter_config()`.

FILES TO MODIFY (verify each with grep first):
1. src/bioetl/domain/config/pipeline.py — field declaration (line 49) and TYPE_CHECKING import (line 19)
2. src/bioetl/application/core/base_transformer.py — constructor signature accepting silver_filters
3. src/bioetl/application/pipelines/*/transformer.py — all ~10 transformer files
4. src/bioetl/composition/factories/pipeline_factory.py — where PipelineConfig is constructed
5. src/bioetl/composition/factories/transformer_factory.py — where transformers receive filters

STEPS:
1. Run: grep -rn "GoldFilterConfig" src/bioetl/ --include="*.py" | grep -i silver
   to find all locations where GoldFilterConfig appears in silver-related context.
2. In each file, change `SilverFilterConfig | GoldFilterConfig | None` to `SilverFilterConfig | None`.
3. Remove unused GoldFilterConfig imports where they were only used for the silver_filters type.
4. Run: mypy --strict src/bioetl/
5. Run: pytest tests/architecture/ -v
6. Run: pytest tests/unit/ -x --timeout=60

DO NOT change any runtime behavior. This is a type-annotation-only change.
```

### Prompt 1.2: Extract BaseFilterConfig and break SilverFilterConfig inheritance

```
TASK: Refactor domain filtering to use a shared BaseFilterConfig base class
instead of SilverFilterConfig inheriting from GoldFilterConfig.

CONTEXT:
- Currently `SilverFilterConfig(GoldFilterConfig)` in `src/bioetl/domain/filtering/silver_config.py:17`
- This means `isinstance(silver_cfg, GoldFilterConfig)` returns True — BAD for nominal typing.
- Goal: Both GoldFilterConfig and SilverFilterConfig inherit from a private BaseFilterConfig.
  Neither is a subclass of the other.

DESIGN:
1. Create `src/bioetl/domain/filtering/_base_filter_config.py`:
   - Move ALL logic from GoldFilterConfig here: `should_include()`, all `_check_*` methods,
     `_OPERATOR_CHECKERS` dispatch table, `is_empty()`.
   - Class name: `BaseFilterConfig`
   - Same frozen dataclass with same fields.
   - Add `from_base(cls, other: BaseFilterConfig) -> Self` classmethod for cross-type conversion.

2. Modify `src/bioetl/domain/filtering/gold_config.py`:
   - Change `GoldFilterConfig` to inherit from `BaseFilterConfig` instead of defining everything.
   - Keep docstring explaining Gold-layer purpose.
   - Class body should be minimal (just docstring or `pass`).

3. Modify `src/bioetl/domain/filtering/silver_config.py`:
   - Change `SilverFilterConfig` to inherit from `BaseFilterConfig` (NOT GoldFilterConfig).
   - Replace `from_gold_filter_config(config: GoldFilterConfig)` with `from_base(other: BaseFilterConfig)`.
   - Update docstring.

4. Modify `src/bioetl/domain/filtering/__init__.py`:
   - Export `BaseFilterConfig` (but document it as internal — consumers should use Gold/Silver).

5. Update infrastructure:
   - `src/bioetl/infrastructure/schemas/filter_config.py` — if it has `to_silver_domain()`,
     update factory call from `SilverFilterConfig.from_gold_filter_config()` to `SilverFilterConfig.from_base()`.
   - `src/bioetl/infrastructure/config/_base.py` — same update.
   - `src/bioetl/infrastructure/config/filter_config_loader.py` — update return type if needed.

VERIFICATION:
- mypy --strict src/bioetl/
- pytest tests/unit/domain/ -v
- pytest tests/architecture/ -v
- Confirm: `isinstance(SilverFilterConfig(...), GoldFilterConfig)` is False
- Confirm: `isinstance(GoldFilterConfig(...), SilverFilterConfig)` is False
- Confirm: both `should_include()` work identically (same base logic)

CRITICAL: Zero code duplication. All filter logic lives in BaseFilterConfig only.
```

### Prompt 1.3: Narrow TableConfig write mode types (optional)

```
TASK: Remove `| str` from write mode field declarations in TableConfig.

CONTEXT:
- `src/bioetl/domain/config/table.py:31-32` declares:
    silver_write_mode: SilverWriteMode | str = SilverWriteMode.MERGE
    gold_write_mode: GoldWriteMode | str = GoldWriteMode.APPEND
- `__post_init__` (lines 37-50) always converts strings to enums via `convert_write_mode()`.
- At runtime the value is always an enum, but mypy sees `SilverWriteMode | str`.

STEPS:
1. First verify ALL construction sites pass enum values or go through __post_init__:
   grep -rn "silver_write_mode\|gold_write_mode" src/bioetl/ --include="*.py"
   grep -rn "SilverWriteMode\|GoldWriteMode" src/bioetl/ --include="*.py"

2. If safe, change declarations in table.py:
   silver_write_mode: SilverWriteMode = SilverWriteMode.MERGE
   gold_write_mode: GoldWriteMode = GoldWriteMode.APPEND

3. Move any string→enum conversion to infrastructure boundary:
   - src/bioetl/infrastructure/config/_base.py (yaml_config_to_domain or equivalent)
   - Ensure YAML strings are converted BEFORE constructing TableConfig.

4. Update PipelineConfig.write_mode return type (if still present):
   SilverWriteMode | str → SilverWriteMode

5. Remove `| str` from any callers' type hints.

6. Run: mypy --strict src/bioetl/
7. Run: pytest tests/ -x --timeout=120

SKIP this prompt if the grep in step 1 reveals callers passing raw strings
without going through __post_init__. In that case, fix those callers first.
```

---

## Phase 2: Infrastructure Loader Enhancements

### Prompt 2.1: DQ Config Loader — unified field names with alias support

```
TASK: Add alias support to DQConfigLoader so that the unified key `field_validations`
works at ALL hierarchy levels alongside the existing level-specific keys.

CONTEXT:
- File: src/bioetl/infrastructure/config/dq_config_loader.py
- Currently the loader expects:
  - _defaults.yaml: `common_field_validations`, `common_cross_field_validations`, `common_conditional_validations`
  - providers/*.yaml: `provider_field_validations`, etc.
  - entities/*/*.yaml: `entity_field_validations`, etc.
- We want to ALSO accept the universal key `field_validations` at any level,
  automatically treated as if it were the level-specific key.

IMPLEMENTATION:
1. Read the current normalization logic (likely in a `_normalize_*` method).
2. Add a normalization step that runs BEFORE the existing merge:
   ```python
   def _normalize_level_keys(self, data: dict, level: str) -> dict:
       """Map universal 'field_validations' to level-specific key if not already present."""
       prefix_map = {"defaults": "common", "provider": "provider", "entity": "entity"}
       prefix = prefix_map[level]
       for suffix in ("field_validations", "cross_field_validations", "conditional_validations"):
           universal_key = suffix
           level_key = f"{prefix}_{suffix}"
           if universal_key in data and level_key not in data:
               data[level_key] = data.pop(universal_key)
       return data
   ```
3. Call this normalization after loading each YAML file, before merging.
4. Add `dq_overrides` as alias for `dq_rules` in pipeline config loading
   (in pipeline_config_loader.py).

VERIFICATION:
- Existing tests pass unchanged (old format works).
- Write a small test: YAML with `field_validations` at entity level → same domain object
  as YAML with `entity_field_validations`.
- pytest tests/unit/infrastructure/config/ -v
```

### Prompt 2.2: Source Config — dual format support

```
TASK: Update source config loading to accept both old nested format and new flat format.

CONTEXT:
- File: src/bioetl/composition/providers/_config_helpers.py
- Old format: `source.provider_config.base_url`, `source.batch_size`, etc.
- New format: `api.base_url`, `client.timeout_sec`, `batch.api_batch_size`, etc.

IMPLEMENTATION:
1. Read _config_helpers.py to understand current parsing.
2. Add normalization that converts new format to old format internally:
   ```python
   def _normalize_source_config(raw: dict) -> dict:
       """Accept both old (source.provider_config) and new (api/client/batch) formats."""
       if "api" in raw and "source" not in raw:
           # New format → convert to old format for compatibility
           raw["source"] = {
               "provider_config": {
                   "base_url": raw["api"]["base_url"],
                   "auth_type": raw["api"].get("auth_type", "public"),
                   ...
               },
               "batch_size": raw.get("batch", {}).get("api_batch_size", 100),
               ...
           }
       return raw
   ```
3. Apply this normalization in `_get_source_config()` or wherever YAML is loaded.

VERIFICATION:
- Existing source configs load correctly (old format).
- Manually test with one converted source config (new format).
- pytest tests/ -k "source_config or adapter" -v
```

### Prompt 2.3: Filter Config Loader — path alias

```
TASK: Update FilterConfigLoader to search both `configs/filter/` and `configs/filters/` paths.

CONTEXT:
- File: src/bioetl/infrastructure/config/filter_config_loader.py
- Current: hardcoded `configs/filter/` path.
- Goal: Try `configs/filters/` first, fall back to `configs/filter/`.

IMPLEMENTATION:
1. Find where the filter config root path is set (likely in __init__ or a class attribute).
2. Add fallback logic:
   ```python
   filter_root = self._configs_root / "filters"
   if not filter_root.exists():
       filter_root = self._configs_root / "filter"
   ```
3. Same pattern for DQ: try `configs/quality/` then `configs/dq/`.
4. Same for data_schema: try `configs/schemas/` then `configs/data_schema/`.

VERIFICATION:
- Existing paths work (no directory rename yet).
- pytest tests/unit/infrastructure/config/ -v
```

---

## Phase 3: Caller Migration & Property Removal

### Prompt 3.1: Add effective_silver_table / effective_gold_table

```
TASK: Add `effective_silver_table` and `effective_gold_table` properties to PipelineConfig.

CONTEXT:
- File: src/bioetl/domain/config/pipeline.py
- Multiple callers use `config.silver_table or f"{config.provider}.{config.entity_type}"` pattern.
- Centralize this fallback logic.

IMPLEMENTATION:
Add after the existing convenience properties section:

```python
@property
def effective_silver_table(self) -> str:
    """Silver table name with provider.entity fallback."""
    return self.table.silver_table or f"{self.provider}.{self.entity_type}"

@property
def effective_gold_table(self) -> str:
    """Gold table name with provider.entity fallback."""
    return self.table.gold_table or f"{self.provider}.{self.entity_type}"
```

VERIFICATION:
- mypy --strict src/bioetl/
- pytest tests/unit/domain/config/ -v
```

### Prompt 3.2: Migrate all callers from convenience properties to config.table.*

```
TASK: Replace all usage of PipelineConfig convenience properties with canonical
config.table.* access or the new effective_* properties.

CONTEXT:
- PipelineConfig has 7 convenience properties forwarding to config.table.*:
  primary_keys, silver_table, gold_table, write_mode, gold_write_mode, partition_cols, on_schema_mismatch
- These will be removed. All callers must use config.table.* directly.
- For silver_table/gold_table with fallback pattern, use config.effective_silver_table/effective_gold_table.

STEPS:
1. Run exhaustive search:
   grep -rn 'config\.primary_keys\b' src/bioetl/ --include="*.py" | grep -v 'table\.primary_keys' | grep -v '_test\.'
   grep -rn 'config\.silver_table\b' src/bioetl/ --include="*.py" | grep -v 'table\.silver_table' | grep -v 'effective_silver'
   grep -rn 'config\.gold_table\b' src/bioetl/ --include="*.py" | grep -v 'table\.gold_table' | grep -v 'effective_gold'
   grep -rn 'config\.write_mode\b' src/bioetl/ --include="*.py" | grep -v 'table\.'
   grep -rn 'config\.gold_write_mode\b' src/bioetl/ --include="*.py" | grep -v 'table\.'
   grep -rn 'config\.partition_cols\b' src/bioetl/ --include="*.py" | grep -v 'table\.'
   grep -rn 'config\.on_schema_mismatch\b' src/bioetl/ --include="*.py" | grep -v 'table\.'

2. Also check for `source_config.silver_table`, `source_config.primary_keys` etc. in composite code.

3. For each match, apply the migration:
   - config.primary_keys → config.table.primary_keys
   - config.silver_table → config.effective_silver_table (if fallback pattern exists) or config.table.silver_table
   - config.gold_table → config.effective_gold_table (if fallback pattern exists) or config.table.gold_table
   - config.write_mode → config.table.silver_write_mode
   - config.gold_write_mode → config.table.gold_write_mode
   - config.partition_cols → config.table.partition_cols
   - config.on_schema_mismatch → config.table.on_schema_mismatch

4. CRITICAL: Also update test files that reference these properties.

VERIFICATION:
- All grep commands from step 1 return 0 results (except the property definitions themselves).
- mypy --strict src/bioetl/
- pytest tests/ -x --timeout=120
```

### Prompt 3.3: Remove convenience properties from PipelineConfig

```
TASK: Remove the 7 convenience properties from PipelineConfig.

PREREQUISITE: Prompt 3.2 is COMPLETE and verified.

CONTEXT:
- File: src/bioetl/domain/config/pipeline.py
- Lines ~112-145 contain 7 properties: primary_keys, silver_table, gold_table,
  write_mode, gold_write_mode, partition_cols, on_schema_mismatch.

STEPS:
1. Run grep one more time to verify NO callers remain:
   grep -rn 'config\.\(primary_keys\|silver_table\|gold_table\|write_mode\|gold_write_mode\|partition_cols\|on_schema_mismatch\)\b' src/bioetl/ --include="*.py" | grep -v 'self\.table\.' | grep -v 'effective_' | grep -v '_test\.'

2. Remove properties from pipeline.py (lines 107-145 approximately).
   Keep: lock_key, effective_silver_table, effective_gold_table.

3. Update class docstring — remove mention of convenience properties,
   state that config.table.* is the canonical access path.

4. Remove the GoldWriteMode, SilverWriteMode imports if no longer used in this file.

VERIFICATION:
- mypy --strict src/bioetl/
- pytest tests/ -x --timeout=120
- grep -rn "convenience" src/bioetl/domain/config/pipeline.py should return 0.
```

---

## Phase 4: YAML Config Migration

### Prompt 4.1: Fix entity names in source configs

```
TASK: Replace outdated entity names in configs/sources/*.yaml files.

CONTEXT:
- ADR-024 renamed document → publication, but source configs still use old names.
- File: configs/sources/chembl.yaml (and any other source files with "document").

STEPS:
1. grep -rn "document" configs/sources/ to find all occurrences.
2. Replace:
   - document → publication
   - document_similarity → publication_similarity
   - document_term → publication_term
3. Do NOT change descriptive text or comments that discuss the rename itself.

VERIFICATION:
- grep -rn "^\s*- document\b" configs/sources/ returns 0 results.
- Run integration tests if available for config loading.
```

### Prompt 4.2: Simplify pipeline configs to convention-based minimal

```
TASK: Remove duplicated fields from all pipeline config YAML files,
keeping only convention-based minimal style.

CONTEXT:
- ADR-029 established convention-based auto-computation for paths, primary_key propagation, etc.
- Many pipeline configs still have explicit redundant fields.

FOR EACH FILE in configs/pipelines/{provider}/{entity}.yaml:

REMOVE these fields (they are auto-computed by convention):
- source_file
- dq_config_file
- data_schema_file
- filter_config_file
- sink.bronze.path
- sink.silver.path
- sink.gold.path
- sink.silver.primary_key (auto-propagated from top-level primary_keys)
- sink.silver.sort_by (auto-propagated from primary_keys)
- sink.gold.sort_by (auto-propagated from primary_keys)
- sink.silver.csv_export.path (auto-computed from sink path)
- sink.gold.csv_export.path (auto-computed from sink path)

RENAME:
- dq_rules → dq_overrides (to clarify these are overrides, not full rule set)

KEEP:
- pipeline_name, provider, entity_type, version, description
- primary_keys, silver_table, gold_table
- sink.silver.partition_by (entity-specific, not auto-computed)
- sink.silver.write_mode / sink.gold.write_mode (only if non-default)
- dq_overrides content (field_validations, cross_field_validations, conditional_validations)
- Any other entity-specific overrides

PROCESS:
1. Start with chembl/molecule.yaml (most verbose, 117 lines) as template.
2. Apply to all 30 pipeline configs.
3. Skip composite/ configs for now (they have different structure).

VERIFICATION:
- Config loader still produces identical PipelineConfig domain objects.
- Run: pytest tests/ -k "config" -v
```

### Prompt 4.3: Unify DQ field naming in YAML files

```
TASK: Rename DQ validation keys to use unified naming in all YAML files.

CONTEXT:
- Phase 2.1 added alias support in the loader, so both old and new keys work.
- Now migrate all YAML files to use the new unified keys.

RENAMES:
| File Level | Old Key | New Key |
|------------|---------|---------|
| configs/dq/_defaults.yaml | common_field_validations | field_validations |
| configs/dq/_defaults.yaml | common_cross_field_validations | cross_field_validations |
| configs/dq/_defaults.yaml | common_conditional_validations | conditional_validations |
| configs/dq/providers/*.yaml | provider_field_validations | field_validations |
| configs/dq/providers/*.yaml | provider_cross_field_validations | cross_field_validations |
| configs/dq/providers/*.yaml | provider_conditional_validations | conditional_validations |
| configs/dq/entities/*/*.yaml | entity_field_validations | field_validations |
| configs/dq/entities/*/*.yaml | entity_cross_field_validations | cross_field_validations |
| configs/dq/entities/*/*.yaml | entity_conditional_validations | conditional_validations |

STEPS:
1. Count files: find configs/dq/ -name "*.yaml" | wc -l
2. For each file, apply the renames using sed or manual edit.
3. Verify no old keys remain: grep -rn "common_field_validations\|provider_field_validations\|entity_field_validations" configs/dq/

VERIFICATION:
- Loader produces identical DQConfig domain objects (alias support from Phase 2 handles both).
- pytest tests/ -k "dq" -v
```

### Prompt 4.4: Normalize source configs

```
TASK: Restructure all 7 source config YAML files to use the uniform schema.

CONTEXT:
- Phase 2.2 added dual-format support in the loader.
- Now migrate YAML files to the new flat structure.

TARGET SCHEMA for each configs/sources/{provider}.yaml:

```yaml
version: "1.0.0"

api:
  base_url: <from source.provider_config.base_url>
  auth_type: <from source.provider_config.auth_type>
  api_key: <from source.provider_config.api_key, if present>
  api_version: <from source.provider_config.api_version, if present>

client:
  timeout_sec: <from source.provider_config.client.timeout_sec>
  max_retries: <from source.provider_config.client.max_retries>
  retry_base_delay: <if present>
  retry_max_delay: <if present>

batch:
  api_batch_size: <from source.batch_size OR source.provider_config.batch_size>
  page_size: <from source.provider_config.page_size>
  max_url_length: <from source.provider_config.max_url_length, if present>

rate_limit:
  default:
    requests_per_second: <from rate_limit.requests_per_second>
    burst: <from rate_limit.burst>
  authenticated: <from rate_limit.with_api_key, if present — rename>

circuit_breaker:
  failure_threshold: <from circuit_breaker.failure_threshold>
  recovery_timeout: <from circuit_breaker.recovery_timeout>

health_check:
  endpoint: <from health_check.endpoint>
  method: GET
  timeout_sec: <from health_check.timeout — add _sec suffix>
  params: <from health_check.params, if present>
  skip_on_429: <from health_check.skip_on_429, if present>

retry:
  use_retry_after: <from retry.use_retry_after>

entities: <use canonical names per ADR-024>
```

DELETE from source configs:
- `dq_thresholds` (belongs in configs/dq/ hierarchy only)
- `source.type` and `source.load_strategy` (if unused by loaders)
- Duplicate `batch_size` entries

FILES: configs/sources/chembl.yaml, crossref.yaml, openalex.yaml, pubchem.yaml,
pubmed.yaml, semanticscholar.yaml, uniprot.yaml

VERIFICATION:
- All adapter factories create valid adapter instances.
- pytest tests/ -k "adapter or source" -v
```

### Prompt 4.5: Slim down _base.yaml

```
TASK: Reduce configs/pipelines/_base.yaml from ~491 lines to ~150 lines.

CONTEXT:
- ~60% of _base.yaml is documentation/comments that duplicates ADR-029 and RULES.md.
- Keep only: default values with brief inline comments.
- Move detailed documentation to docs/03-guides/CONFIG-GUIDE.md.

STEPS:
1. Read configs/pipelines/_base.yaml fully.
2. Extract documentation content to docs/03-guides/CONFIG-GUIDE.md (new file).
3. In _base.yaml, keep:
   - YAML structure with all default values
   - One-liner inline comments for non-obvious defaults
   - Section headers (# Identity, # Sink, # DQ, etc.)
4. Remove:
   - Multi-line explanations
   - Example usage blocks
   - References to ADRs (these belong in the guide)
   - ASCII art / dividers

VERIFICATION:
- Config loader produces identical defaults from simplified _base.yaml.
- pytest tests/ -k "config" -v
```

---

## Phase 5: Directory Reorganization

### Prompt 5.1: Rename config directories

```
TASK: Rename config directories to their new canonical names.

PREREQUISITE: Phase 2 (loader aliases) is complete and tested.

RENAMES:
1. configs/dq/ → configs/quality/
2. configs/filter/ → configs/filters/
3. configs/data_schema/ → configs/schemas/
4. configs/composite/field_groups/ → configs/schemas/composite/field_groups/
5. configs/pipelines/_schema.json → configs/_schema/pipeline.json
6. configs/pipelines/_composite_schema.json → configs/_schema/composite.json

STEPS:
1. Create new directories: mkdir -p configs/quality configs/filters configs/schemas configs/_schema
2. Copy (not move) all contents:
   cp -r configs/dq/* configs/quality/
   cp -r configs/filter/* configs/filters/
   cp -r configs/data_schema/* configs/schemas/
   mkdir -p configs/schemas/composite/field_groups/
   cp configs/composite/field_groups/* configs/schemas/composite/field_groups/
   cp configs/pipelines/_schema.json configs/_schema/pipeline.json
   cp configs/pipelines/_composite_schema.json configs/_schema/composite.json
3. Run full test suite — loaders should find new paths first (Phase 2 aliases).
4. If tests pass, remove old directories:
   rm -rf configs/dq/ configs/filter/ configs/data_schema/ configs/composite/
   rm configs/pipelines/_schema.json configs/pipelines/_composite_schema.json

VERIFICATION:
- find configs/ -name "*.yaml" | wc -l — same count as before.
- pytest tests/ -x --timeout=120
- No references to old paths in loader code (except fallback logic from Phase 2).
```

---

## Phase 6: Cleanup & Finalization

### Prompt 6.1: Remove backward-compat aliases

```
TASK: Remove old-format alias support from config loaders.

PREREQUISITE: All YAML files are migrated (Phase 4) and directories renamed (Phase 5).

FILES:
- src/bioetl/infrastructure/config/dq_config_loader.py — remove old key aliases
- src/bioetl/infrastructure/config/filter_config_loader.py — remove old path fallback
- src/bioetl/infrastructure/config/pipeline_config_loader.py — remove dq_rules alias
- src/bioetl/composition/providers/_config_helpers.py — remove old source format support

STEPS:
1. Verify no old-format files remain:
   grep -rn "common_field_validations\|provider_field_validations\|entity_field_validations" configs/
   grep -rn "dq_rules:" configs/pipelines/
   ls configs/dq/ 2>/dev/null (should not exist)
   ls configs/filter/ 2>/dev/null (should not exist)
2. Remove alias/fallback code added in Phase 2.
3. Clean up any deprecation warnings.

VERIFICATION:
- mypy --strict src/bioetl/
- pytest tests/ -x --timeout=120
```

### Prompt 6.2: Clean up validation.py

```
TASK: Remove structural noise from domain/config/validation.py while preserving
semantically important documentation.

FILE: src/bioetl/domain/config/validation.py

REMOVE:
- Section divider comments (# ============, # ---- etc.)
- Verbose module-level docstring (keep one-liner)
- Redundant whitespace/formatting

PRESERVE (do NOT remove):
- Attribute docstrings on ValidationConfig (publication year ranges, molecular weight ranges)
- FieldValidation.validation_type Literal explanations (what "required", "not_null", "range" mean)
- CrossFieldValidation.condition Literal inline comments (what "all_present" etc. mean)
- ConditionalValidation attribute descriptions

VERIFICATION:
- mypy --strict src/bioetl/domain/config/validation.py
- pytest tests/unit/domain/config/ -v
```

### Prompt 6.3: Architecture and regression tests

```
TASK: Add tests validating the refactoring results.

NEW TEST FILES:

1. tests/architecture/test_filter_separation.py:
   - SilverFilterConfig is NOT a subclass of GoldFilterConfig
   - GoldFilterConfig is NOT a subclass of SilverFilterConfig
   - Both ARE subclasses of BaseFilterConfig
   - isinstance(SilverFilterConfig(...), GoldFilterConfig) is False
   - No code outside domain/filtering/ imports _base_filter_config directly

2. tests/unit/domain/config/test_effective_tables.py:
   - effective_silver_table returns table.silver_table when set
   - effective_silver_table returns "{provider}.{entity_type}" as fallback
   - effective_gold_table same tests

3. tests/integration/config/test_config_loading.py:
   - Load each pipeline config from YAML → verify PipelineConfig is valid
   - Load DQ config with unified keys → verify same domain object as old keys
   - Load source config with new format → verify adapter creation works

4. tests/unit/domain/filtering/test_base_filter_config.py:
   - Parameterized: both GoldFilterConfig and SilverFilterConfig pass identical
     should_include() test cases (proving shared base logic works)

VERIFICATION:
- pytest tests/ -x --timeout=120
- pytest --cov=src/bioetl --cov-fail-under=85
```

### Prompt 6.4: Update ADR and documentation

```
TASK: Update architecture documentation to reflect config structure changes.

FILES TO UPDATE:
1. docs/02-architecture/decisions/ — find ADR-027, ADR-028, ADR-029:
   - Update all references from configs/dq/ → configs/quality/
   - Update from configs/filter/ → configs/filters/
   - Update from configs/data_schema/ → configs/schemas/
   - Note the unified DQ key naming

2. docs/00-project/RULES.md — if it references config paths, update them.

3. Create docs/03-guides/CONFIG-GUIDE.md (content extracted from _base.yaml in Phase 4.5).

DO NOT create files that already exist. Check first.

VERIFICATION:
- grep -rn "configs/dq/" docs/ returns 0 (or only in historical ADRs marked superseded)
- grep -rn "configs/filter/" docs/ returns 0
- grep -rn "configs/data_schema/" docs/ returns 0
```

---

## Execution Notes

### Parallelization
- **Within Phase 1:** Steps 1.1 and 1.3 are independent. Step 1.2 depends on 1.1.
- **Phase 1 and Phase 2:** Can run in parallel (different layers).
- **Phase 3:** Sequential (3.1 → 3.2 → 3.3). Depends on Phase 1.
- **Phase 4:** Steps 4.1, 4.3, 4.4, 4.5 can be parallelized. Step 4.2 should be last.
  Depends on Phase 2.
- **Phase 5:** Single step, depends on Phase 4.
- **Phase 6:** Steps 6.1-6.4 can be parallelized. Depends on Phase 5.

### Rollback
Each Phase should be a separate git commit (or commit group).
Rollback = `git revert <phase-commit>`.

### Verification Cadence
After EVERY prompt execution:
1. `mypy --strict src/bioetl/` (type safety)
2. `pytest tests/architecture/ -v` (import boundaries)
3. `pytest tests/ -x --timeout=120` (full suite, fail-fast)
