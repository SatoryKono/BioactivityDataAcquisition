# Data Quality Configuration

*Reference: [ADR-027: DQ Rules Externalization](../02-architecture/decisions/ADR-027-dq-rules-externalization.md)*

This guide describes how to configure Data Quality (DQ) rules in BioETL.

## Overview

DQ rules are organized in a hierarchical configuration structure that enables:
- **Reusability**: Share validations across pipelines
- **Override flexibility**: Entity-specific rules without affecting others
- **DRY principle**: Global thresholds defined once

## Hierarchical DQ Config Structure

```
configs/
├── base/quality.yaml                 # Level 1: Global defaults
├── providers/{provider}.yaml         # Level 2: Section "quality"
└── entities/{provider}/{entity}.yaml # Level 3: Section "quality"
```

## Merge Behavior

Configurations are merged in order (later wins):

| Level | File | Scope |
|-------|------|-------|
| 1 | `base/quality.yaml` | All pipelines |
| 2 | `providers/{provider}.yaml` (`quality`) | All entities of provider |
| 3 | `entities/{provider}/{entity}.yaml` (`quality`) | Specific entity |
| 4 | Inline `dq-overrides` in pipeline | Override for exceptions |

**Merge rules**:
- Scalars: Override (later value wins)
- Validation lists (`*-validations`): Concatenate with deduplication by `name`/`field`
- Nested dicts: Recursive merge

## DQ Thresholds

BioETL uses two-level error thresholds (RULES.md §3.1.2):

| Threshold | Default | Behavior |
|-----------|---------|----------|
| `soft-fail` | 0.05 (5%) | Warning emitted, pipeline continues |
| `hard-fail` | 0.20 (20%) | Batch fails, records quarantined |

Configure in `configs/base/quality.yaml`:

```yaml
thresholds:
  soft-fail: 0.05      # >5% errors → Warning
  hard-fail: 0.20      # >20% errors → Fail Batch
```

**Invariant**: `soft-fail` must be strictly less than `hard-fail`.

## Complete `base/quality.yaml` Key Reference

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `version` | string | `"1.0.0"` | Schema version of the DQ config |
| `thresholds.soft-fail` | float | `0.05` | Error rate (>5%) that triggers a warning |
| `thresholds.hard-fail` | float | `0.20` | Error rate (>20%) that fails the batch |
| `strict-validation` | bool | `false` | Feature flag for stricter validation rules |
| `invalid-record-policy` | string | `"quarantine"` | How to handle failed records: `quarantine`, `skip`, or `fail` |
| `report.enabled` | bool | `true` | Enable DQ report generation |
| `report.format` | string | `"json"` | Report format: `json`, `yaml`, or `csv` |
| `report.include-sample-failures` | bool | `true` | Include sample of failed records in report |
| `report.sample-size` | int | `10` | Number of failed records to include in sample |
| `report.output-path` | string | `null` | Custom output path (null = pipeline output dir) |
| `common-field-validations` | list | see below | Field validations applied to ALL entities |
| `common-cross-field-validations` | list | `[]` | Cross-field validations applied to ALL entities |

### Default Common Field Validations

Two validations are applied globally to all entities:

1. **`-content-hash` required** — Content hash must be present after transform (for deduplication)
2. **`-ingestion-ts` pattern** — Ingestion timestamp must match ISO 8601 format (`^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}`)

## Adding DQ Rules for New Entity

### Step 1: Check if provider config exists

```bash
ls configs/providers/{provider}.yaml
```

If it doesn't exist, create it:

```yaml
# configs/providers/{provider}.yaml
version: "1.0.0"
provider: {provider}

quality:
  # Optional: provider-wide field validations
  provider-field-validations: []
```

### Step 2: Create entity config

```yaml
# configs/entities/{provider}/{entity}.yaml
version: "1.0.0"
provider: {provider}
entity: {entity}

quality:
  # Override thresholds for this entity (optional)
  # thresholds:
  #   hard-fail: 0.10

  # Field-level validations
  entity-field-validations:
    - field: primary-id
      type: required
      nullable: false
      error-message: "Primary ID is required"

  # Cross-field validations
  entity-cross-field-validations: []

  # Conditional validations
  entity-conditional-validations: []
```

### Step 3: Add optional inline overrides in `pipeline`

```yaml
# configs/entities/{provider}/{entity}.yaml
pipeline:
  pipeline-name: {provider}-{entity}
  dq-overrides:
    thresholds:
      hard-fail-threshold: 0.25
```

## Validation Types

### Field Validations

| Type | Parameters | Description |
|------|------------|-------------|
| `required` | `nullable` | Field must be present (unless nullable=true) |
| `range` | `min`, `max` | Numeric bounds check |
| `pattern` | `pattern` | Regex match |
| `enum` | `allowed` | Value must be in whitelist |
| `custom` | `validator` | Custom validator function name |

**Examples:**

```yaml
entity-field-validations:
  # Required field
  - field: activity-id
    type: required
    nullable: false
    error-message: "Activity ID is required"

  # Range validation
  - field: standard-value
    type: range
    min: 0
    nullable: true
    error-message: "Standard value must be non-negative"

  # Pattern validation
  - field: smiles
    type: pattern
    pattern: '^[A-Za-z0-9@+\-\[\]\(\)=#%\/\\\.]+$'
    nullable: true
    error-message: "Invalid SMILES format"

  # Enum validation
  - field: standard-type
    type: enum
    allowed:
      - IC50
      - Ki
      - Kd
      - EC50
    nullable: true
    error-message: "Invalid standard-type value"
```

### Cross-Field Validations

| Condition | Description |
|-----------|-------------|
| `all-present` | All specified fields must have values |
| `any-present` | At least one field must have value |
| `mutually-exclusive` | Only one field can have value |
| `conditional-required` | `required-field` needed when `trigger-field` present |
| `custom` | Custom validator function |

**Examples:**

```yaml
entity-cross-field-validations:
  # If value present, units should be present
  - name: value-requires-units
    fields:
      - standard-value
      - standard-units
    condition: conditional-required
    trigger-field: standard-value
    required-field: standard-units
    error-message: "Units required when value is present"

  # At least one identifier must be present
  - name: need-identifier
    fields:
      - chembl-id
      - inchi-key
      - smiles
    condition: any-present
    error-message: "At least one identifier required"
```

### Conditional Validations

Apply validations only when a condition is met.

| Parameter | Description |
|-----------|-------------|
| `condition-field` | Field to check for condition |
| `condition-value` | Value(s) that trigger the validation |
| `condition-operator` | Comparison operator: `eq`, `ne`, `in`, `not-in`, `gt`, `lt`, `ge`, `le` |
| `then-validations` | List of validations to apply when condition is true |

**Example:**

```yaml
entity-conditional-validations:
  # When assay-type is 'B' (Binding), target must be present
  - name: binding-requires-target
    condition-field: assay-type
    condition-value: B
    condition-operator: eq
    then-validations:
      - field: target-chembl-id
        type: required
        nullable: false
        error-message: "Binding assays must have a target"

  # When activity-type is in [IC50, Ki], standard-value required
  - name: potency-needs-value
    condition-field: activity-type
    condition-value: [IC50, Ki, Kd, EC50]
    condition-operator: in
    then-validations:
      - field: standard-value
        type: required
        nullable: false
        error-message: "Potency measures require a value"
```

## Complete Entity DQ Config Example

```yaml
# configs/entities/chembl/activity.yaml
version: "1.0.0"
provider: chembl
entity: activity

quality:
  # Override provider thresholds (optional)
  # thresholds:
  #   hard-fail: 0.10

  entity-field-validations:
    - field: activity-id
      type: required
      nullable: false
      error-message: "Activity ID is required"

    - field: standard-value
      type: range
      min: 0
      nullable: true
      error-message: "Standard value must be non-negative"

    - field: pchembl-value
      type: range
      min: 0
      max: 15
      nullable: true
      error-message: "pChEMBL value must be between 0 and 15"

    - field: standard-type
      type: enum
      allowed: [IC50, Ki, Kd, EC50, AC50, GI50, Potency, Activity, Inhibition]
      nullable: true
      error-message: "Invalid standard-type value"

  entity-cross-field-validations:
    - name: value-requires-units
      fields: [standard-value, standard-units]
      condition: conditional-required
      trigger-field: standard-value
      required-field: standard-units
      error-message: "standard-units required when standard-value is present"

  entity-conditional-validations:
    - name: binding-requires-target
      condition-field: assay-type
      condition-value: B
      condition-operator: eq
      then-validations:
        - field: target-chembl-id
          type: required
          nullable: false
          error-message: "Binding assays must have a target"
```

## Inline Overrides (Level 4)

For exceptional cases, override DQ rules directly in pipeline config:

```yaml
# configs/entities/chembl/activity.yaml
pipeline:
  pipeline-name: chembl-activity

  # Temporary override for migration period
  dq-overrides:
    hard-fail-threshold: 0.30  # Higher tolerance during migration
    field-validations:
      - field: legacy-id
        type: required
        nullable: false
```

**Note**: Inline overrides should be temporary. Prefer updating entity config for permanent changes.

## Programmatic Access

```python
from pathlib import Path
from bioetl.infrastructure.config.dq-config-loader import DQConfigLoader

# Load merged config
loader = DQConfigLoader(Path("configs"))
dq-config = loader.load(
    provider="chembl",
    entity="activity",
    inline-overrides=None,  # Optional Level 4 overrides
)

# Access domain objects
print(f"Soft threshold: {dq-config.soft-fail-threshold}")
print(f"Hard threshold: {dq-config.hard-fail-threshold}")
print(f"Field validations: {len(dq-config.field-validations)}")
```

## Validation

Validate all DQ configs:

```bash
python src/tools/scripts/validate-unified-configs.py
```

## Troubleshooting

### Error: soft-fail >= hard-fail

```
ValueError: soft-fail (0.25) must be < hard-fail (0.20)
```

**Fix**: Ensure `soft-fail` is strictly less than `hard-fail` in your config.

### Error: Required field not found

```
FileNotFoundError: Required DQ defaults file not found: configs/base/quality.yaml
```

**Fix**: Create `configs/base/quality.yaml` with global settings.

### Validation not applied

**Check**:
1. Is `quality` section present in `configs/entities/{provider}/{entity}.yaml`?
2. Is field name spelled correctly in validation?
3. Is validation type correct for the field data type?

## References

- [ADR-027: DQ Rules Externalization](../02-architecture/decisions/ADR-027-dq-rules-externalization.md)
- RULES.md §3.1.2: DQ Thresholds
- Schema: `src/bioetl/infrastructure/schemas/dq-config.py`
- Loader: `src/bioetl/infrastructure/config/dq-config-loader.py`
