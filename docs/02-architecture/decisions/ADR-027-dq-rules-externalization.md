______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-027: DQ Rules Externalization

**Date:** 2026-01-19
**Status:** Accepted
**Decision makers:** @BioETL-Team

## Context

Data Quality (DQ) rules were embedded directly in pipeline YAML configuration files (`configs/entities/{provider}/{entity}.yaml`). This caused several problems:

1. **Duplication**: Same thresholds and validation rules repeated across pipelines
1. **Maintenance burden**: Changing global DQ policies required editing multiple files
1. **No reusability**: Impossible to share validation rules across providers/entities
1. **SRP violation**: Pipeline config mixed orchestration and DQ policy concerns

Example of duplication:

```yaml
# configs/entities/chembl/activity.yaml
dq_overrides:
  soft-fail-threshold: 0.05
  hard-fail-threshold: 0.20

# configs/entities/chembl/molecule.yaml
dq_overrides:
  soft-fail-threshold: 0.05  # Duplicated
  hard-fail-threshold: 0.20  # Duplicated
```

## Decision

Extract DQ rules into a hierarchical configuration structure:

```
configs/
├── base/quality.yaml            # Global defaults (Level 1)
├── providers/{provider}.yaml    # Section quality (Level 2)
└── entities/{provider}/{entity}.yaml  # Section quality (Level 3)
```

**Merge priority** (later wins for scalars, concatenate for validations):

1. `configs/base/quality.yaml`
1. `configs/providers/{provider}.yaml#quality`
1. `configs/entities/{provider}/{entity}.yaml#quality`
1. Inline `dq_overrides` in pipeline config (for exceptional cases)

Pipeline configs reference DQ config via `dq-config-file`:

```yaml
pipeline_name: chembl_activity
dq-config-file: ../../entities/chembl/activity.yaml
```

> **`dq-config-file` semantics (convention-based):**
> This field is **auto-computed** by the pipeline config loader from `provider` and
> `entity_type` as `../../entities/{provider}/{entity_type}.yaml`. Pipeline
> YAML files **SHOULD NOT** explicitly set this field — it is resolved automatically
> via convention (ADR-029). If explicitly set, the value acts as an **override path**
> that replaces the convention-based resolution. The `DQConfigLoader` always loads
> the full 3-level hierarchy (`-defaults → provider → entity`) regardless of whether
> `dq-config-file` is explicit or computed.
>
> Inline `dq_overrides` in pipeline YAML are applied as Level 4 on top of the
> resolved hierarchy. They are the recommended way to add entity-specific exceptions.

### Implementation Components

1. **Pydantic schemas**: `src/bioetl/infrastructure/schemas/dq_config.py`

   - `ThresholdsConfig`: Validates soft-fail < hard-fail invariant
   - `DQConfigFile`: Complete schema with hierarchical validation support

1. **Configuration loader**: `src/bioetl/infrastructure/config/dq_config_loader.py`

   - `DQConfigLoader.load(provider, entity, inline-overrides)`: Merges configs
   - Thread-safe caching for performance
   - Deep merge with validation list concatenation

1. **Config files**: unified hierarchy in `configs/base|providers|entities`

   - `base/quality.yaml`: Global thresholds (0.05/0.20), common validations
   - `providers/{provider}.yaml#quality`: Provider-specific settings
   - `entities/{provider}/{entity}.yaml#quality`: Entity-specific rules

## Consequences

### Positive

- **DRY**: Global thresholds defined once in `configs/base/quality.yaml`
- **Separation of Concerns**: Pipeline config focuses on orchestration
- **Reusability**: Provider-level validations shared across entities
- **Flexibility**: Entity-specific rules without affecting others
- **Backward compatible**: Inline `dq_overrides` still supported as Level 4 override
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

| Data Type                          | Behavior               | Example                                                   |
| ---------------------------------- | ---------------------- | --------------------------------------------------------- |
| Scalars                            | Override (later wins)  | `soft-fail: 0.10` replaces `0.05`                         |
| Validation lists (`*-validations`) | Concatenate with dedup | Entity validations added to provider                      |
| Nested dicts                       | Recursive merge        | `thresholds.soft-fail` merged with `thresholds.hard-fail` |
| Other lists                        | Override (later wins)  | `allowed: [A, B]` replaces `[X, Y]`                       |

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

One global `dq-config.yaml` with all rules. Rejected because:

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

| Requirement                   | Status | Implementation                                 |
| ----------------------------- | ------ | ---------------------------------------------- |
| RULES.md §3.1.2 DQ Thresholds | PASS   | `ThresholdsConfig` enforces 0.05/0.20 defaults |
| soft-fail < hard-fail         | PASS   | `ThresholdsConfig.validate_order()`            |
| Hierarchical merge            | PASS   | `DQConfigLoader._deep_merge()`                 |
| Backward compatibility        | PASS   | Inline `dq_overrides` supported as override    |

## References

- RULES.md §3.1.2: DQ Thresholds
- Domain config: `src/bioetl/domain/config.py`
- Schema: `src/bioetl/infrastructure/schemas/dq_config.py`
- Loader: `src/bioetl/infrastructure/config/dq_config_loader.py`
- Config files: `configs/base/quality.yaml`, `configs/providers/*.yaml#quality`, `configs/entities/*/*#quality`

## Changelog

| Date       | Author      | Change          |
| ---------- | ----------- | --------------- |
| 2026-01-19 | Claude Code | Initial version |

## Rollout

- Rollout steps MUST be sequenced before broad adoption.
- Documentation, configuration, and test surfaces SHOULD be updated in the same change set when the decision is implemented.
- Breaking or migration-sensitive adoption SHOULD include an explicit transition window.

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [ ] The decision is documented with current status, date, and owner metadata.
- [ ] The implementation path or adoption boundary is testable and linked from the ADR.
- [ ] Supersession or migration impact is documented when the decision changes an earlier posture.
- [ ] Related docs, contracts, and operational guidance are aligned with this ADR.
