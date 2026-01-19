# ADR-027: DQ Rules Externalization

**Status**: Accepted
**Date**: 2026-01-19
**Authors**: Claude Code
**Reviewers**: -

## Context

Data Quality (DQ) rules were embedded directly in pipeline YAML configuration files (`configs/pipelines/{provider}/{entity}.yaml`). This caused several problems:

1. **Duplication**: Same thresholds and validation rules repeated across pipelines
2. **Maintenance burden**: Changing global DQ policies required editing multiple files
3. **No reusability**: Impossible to share validation rules across providers/entities
4. **SRP violation**: Pipeline config mixed orchestration and DQ policy concerns

Example of duplication:
```yaml
# configs/pipelines/chembl/activity.yaml
dq_rules:
  soft_fail_threshold: 0.05
  hard_fail_threshold: 0.20

# configs/pipelines/chembl/molecule.yaml
dq_rules:
  soft_fail_threshold: 0.05  # Duplicated
  hard_fail_threshold: 0.20  # Duplicated
```

## Decision

Extract DQ rules into a hierarchical configuration structure:

```
configs/dq/
├── _defaults.yaml           # Global defaults (Level 1)
├── providers/
│   └── {provider}.yaml      # Provider overrides (Level 2)
└── entities/
    └── {provider}/
        └── {entity}.yaml    # Entity-specific rules (Level 3)
```

**Merge priority** (later wins for scalars, concatenate for validations):
1. `_defaults.yaml`
2. `providers/{provider}.yaml`
3. `entities/{provider}/{entity}.yaml`
4. Inline `dq_rules` in pipeline config (for exceptional cases)

Pipeline configs reference DQ config via `dq_config_file`:
```yaml
pipeline_name: chembl_activity
dq_config_file: ../../dq/entities/chembl/activity.yaml
```

### Implementation Components

1. **Pydantic schemas**: `src/bioetl/infrastructure/schemas/dq_config.py`
   - `ThresholdsConfig`: Validates soft_fail < hard_fail invariant
   - `DQConfigFile`: Complete schema with hierarchical validation support

2. **Configuration loader**: `src/bioetl/infrastructure/config/dq_config_loader.py`
   - `DQConfigLoader.load(provider, entity, inline_overrides)`: Merges configs
   - Thread-safe caching for performance
   - Deep merge with validation list concatenation

3. **Config files**: `configs/dq/`
   - `_defaults.yaml`: Global thresholds (0.05/0.20), common validations
   - `providers/{provider}.yaml`: Provider-specific settings
   - `entities/{provider}/{entity}.yaml`: Entity-specific rules

## Consequences

### Positive

- **DRY**: Global thresholds defined once in `_defaults.yaml`
- **Separation of Concerns**: Pipeline config focuses on orchestration
- **Reusability**: Provider-level validations shared across entities
- **Flexibility**: Entity-specific rules without affecting others
- **Backward compatible**: Inline `dq_rules` still supported as Level 4 override
- **Type safety**: Pydantic validation catches config errors early
- **Performance**: Caching prevents repeated file reads

### Negative

- **More files**: Additional config files to manage (mitigated by clear structure)
- **Indirection**: Must look at multiple files to understand full config
- **Merge complexity**: Need to understand merge behavior

### Neutral

- Migration effort: Existing pipelines work without changes
- Tooling: Config validation scripts provided

## Merge Rules

| Data Type | Behavior | Example |
|-----------|----------|---------|
| Scalars | Override (later wins) | `soft_fail: 0.10` replaces `0.05` |
| Validation lists (`*_validations`) | Concatenate with dedup | Entity validations added to provider |
| Nested dicts | Recursive merge | `thresholds.soft_fail` merged with `thresholds.hard_fail` |
| Other lists | Override (later wins) | `allowed: [A, B]` replaces `[X, Y]` |

**Deduplication key** for validation lists:
- Field validations: `field` attribute
- Cross-field validations: `name` attribute
- Conditional validations: `name` attribute

## Alternatives Considered

### 1. YAML Anchors
Using YAML anchors for reuse within a single file. Rejected because:
- Doesn't work across files
- Complex syntax for users
- No tool support for validation

### 2. Single DQ Config File
One global `dq_config.yaml` with all rules. Rejected because:
- Becomes large and hard to navigate
- No provider/entity separation
- Cannot override specific entity without affecting others

### 3. DQ Rules in Code
Define validation rules in Python. Rejected because:
- Requires code changes for config updates
- Violates configuration-driven principle
- Less accessible to non-developers

### 4. Database-stored Rules
Store DQ rules in a database. Rejected because:
- Adds infrastructure dependency
- Overkill for local-only deployment (ADR-010)
- Harder to version control

## Compliance

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| RULES.md §3.1.2 DQ Thresholds | PASS | `ThresholdsConfig` enforces 0.05/0.20 defaults |
| soft_fail < hard_fail | PASS | `ThresholdsConfig.validate_order()` |
| Hierarchical merge | PASS | `DQConfigLoader._deep_merge()` |
| Backward compatibility | PASS | Inline `dq_rules` supported as override |

## References

- RULES.md §3.1.2: DQ Thresholds
- Domain config: `src/bioetl/domain/config.py`
- Schema: `src/bioetl/infrastructure/schemas/dq_config.py`
- Loader: `src/bioetl/infrastructure/config/dq_config_loader.py`
- Config files: `configs/dq/`

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-01-19 | Claude Code | Initial version |
