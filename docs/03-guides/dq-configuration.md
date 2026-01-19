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
configs/dq/
├── _defaults.yaml           # Level 1: Global defaults
├── providers/
│   └── {provider}.yaml      # Level 2: Provider overrides
└── entities/
    └── {provider}/
        └── {entity}.yaml    # Level 3: Entity-specific rules
```

## Merge Behavior

Configurations are merged in order (later wins):

| Level | File | Scope |
|-------|------|-------|
| 1 | `_defaults.yaml` | All pipelines |
| 2 | `providers/{provider}.yaml` | All entities of provider |
| 3 | `entities/{provider}/{entity}.yaml` | Specific entity |
| 4 | Inline `dq_rules` in pipeline | Override for exceptions |

**Merge rules**:
- Scalars: Override (later value wins)
- Validation lists (`*_validations`): Concatenate with deduplication by `name`/`field`
- Nested dicts: Recursive merge

## DQ Thresholds

BioETL uses two-level error thresholds (RULES.md §3.1.2):

| Threshold | Default | Behavior |
|-----------|---------|----------|
| `soft_fail` | 0.05 (5%) | Warning emitted, pipeline continues |
| `hard_fail` | 0.20 (20%) | Batch fails, records quarantined |

Configure in `_defaults.yaml`:

```yaml
thresholds:
  soft_fail: 0.05      # >5% errors → Warning
  hard_fail: 0.20      # >20% errors → Fail Batch
```

**Invariant**: `soft_fail` must be strictly less than `hard_fail`.

## Adding DQ Rules for New Entity

### Step 1: Check if provider config exists

```bash
ls configs/dq/providers/{provider}.yaml
```

If it doesn't exist, create it:

```yaml
# configs/dq/providers/{provider}.yaml
version: "1.0.0"
provider: {provider}

# Optional: provider-wide field validations
provider_field_validations: []
```

### Step 2: Create entity config

```yaml
# configs/dq/entities/{provider}/{entity}.yaml
version: "1.0.0"
provider: {provider}
entity: {entity}

# Override thresholds for this entity (optional)
# thresholds:
#   hard_fail: 0.10

# Field-level validations
entity_field_validations:
  - field: primary_id
    type: required
    nullable: false
    error_message: "Primary ID is required"

# Cross-field validations
entity_cross_field_validations: []

# Conditional validations
entity_conditional_validations: []
```

### Step 3: Reference in pipeline config

```yaml
# configs/pipelines/{provider}/{entity}.yaml
pipeline_name: {provider}_{entity}
dq_config_file: ../../dq/entities/{provider}/{entity}.yaml
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
entity_field_validations:
  # Required field
  - field: activity_id
    type: required
    nullable: false
    error_message: "Activity ID is required"

  # Range validation
  - field: standard_value
    type: range
    min: 0
    nullable: true
    error_message: "Standard value must be non-negative"

  # Pattern validation
  - field: smiles
    type: pattern
    pattern: '^[A-Za-z0-9@+\-\[\]\(\)=#%\/\\\.]+$'
    nullable: true
    error_message: "Invalid SMILES format"

  # Enum validation
  - field: standard_type
    type: enum
    allowed:
      - IC50
      - Ki
      - Kd
      - EC50
    nullable: true
    error_message: "Invalid standard_type value"
```

### Cross-Field Validations

| Condition | Description |
|-----------|-------------|
| `all_present` | All specified fields must have values |
| `any_present` | At least one field must have value |
| `mutually_exclusive` | Only one field can have value |
| `conditional_required` | `required_field` needed when `trigger_field` present |
| `custom` | Custom validator function |

**Examples:**

```yaml
entity_cross_field_validations:
  # If value present, units should be present
  - name: value_requires_units
    fields:
      - standard_value
      - standard_units
    condition: conditional_required
    trigger_field: standard_value
    required_field: standard_units
    error_message: "Units required when value is present"

  # At least one identifier must be present
  - name: need_identifier
    fields:
      - chembl_id
      - inchi_key
      - smiles
    condition: any_present
    error_message: "At least one identifier required"
```

### Conditional Validations

Apply validations only when a condition is met.

| Parameter | Description |
|-----------|-------------|
| `condition_field` | Field to check for condition |
| `condition_value` | Value(s) that trigger the validation |
| `condition_operator` | Comparison operator: `eq`, `ne`, `in`, `not_in`, `gt`, `lt`, `ge`, `le` |
| `then_validations` | List of validations to apply when condition is true |

**Example:**

```yaml
entity_conditional_validations:
  # When assay_type is 'B' (Binding), target must be present
  - name: binding_requires_target
    condition_field: assay_type
    condition_value: B
    condition_operator: eq
    then_validations:
      - field: target_chembl_id
        type: required
        nullable: false
        error_message: "Binding assays must have a target"

  # When activity_type is in [IC50, Ki], standard_value required
  - name: potency_needs_value
    condition_field: activity_type
    condition_value: [IC50, Ki, Kd, EC50]
    condition_operator: in
    then_validations:
      - field: standard_value
        type: required
        nullable: false
        error_message: "Potency measures require a value"
```

## Complete Entity DQ Config Example

```yaml
# configs/dq/entities/chembl/activity.yaml
version: "1.0.0"
provider: chembl
entity: activity

# Override provider thresholds (optional)
# thresholds:
#   hard_fail: 0.10

entity_field_validations:
  - field: activity_id
    type: required
    nullable: false
    error_message: "Activity ID is required"

  - field: standard_value
    type: range
    min: 0
    nullable: true
    error_message: "Standard value must be non-negative"

  - field: pchembl_value
    type: range
    min: 0
    max: 15
    nullable: true
    error_message: "pChEMBL value must be between 0 and 15"

  - field: standard_type
    type: enum
    allowed: [IC50, Ki, Kd, EC50, AC50, GI50, Potency, Activity, Inhibition]
    nullable: true
    error_message: "Invalid standard_type value"

entity_cross_field_validations:
  - name: value_requires_units
    fields: [standard_value, standard_units]
    condition: conditional_required
    trigger_field: standard_value
    required_field: standard_units
    error_message: "standard_units required when standard_value is present"

entity_conditional_validations:
  - name: binding_requires_target
    condition_field: assay_type
    condition_value: B
    condition_operator: eq
    then_validations:
      - field: target_chembl_id
        type: required
        nullable: false
        error_message: "Binding assays must have a target"
```

## Inline Overrides (Level 4)

For exceptional cases, override DQ rules directly in pipeline config:

```yaml
# configs/pipelines/chembl/activity.yaml
pipeline_name: chembl_activity
dq_config_file: ../../dq/entities/chembl/activity.yaml

# Temporary override for migration period
dq_rules:
  thresholds:
    hard_fail: 0.30  # Higher tolerance during migration
  field_validations:
    - field: legacy_id
      type: required
      nullable: false
```

**Note**: Inline overrides should be temporary. Prefer updating entity config for permanent changes.

## Programmatic Access

```python
from pathlib import Path
from bioetl.infrastructure.config.dq_config_loader import DQConfigLoader

# Load merged config
loader = DQConfigLoader(Path("configs"))
dq_config = loader.load(
    provider="chembl",
    entity="activity",
    inline_overrides=None,  # Optional Level 4 overrides
)

# Access domain objects
print(f"Soft threshold: {dq_config.soft_fail_threshold}")
print(f"Hard threshold: {dq_config.hard_fail_threshold}")
print(f"Field validations: {len(dq_config.field_validations)}")
```

## Validation

Validate all DQ configs:

```bash
# Validate via Python
python -c "
from pathlib import Path
import yaml
from bioetl.infrastructure.schemas.dq_config import DQConfigFile

for f in Path('configs/dq').rglob('*.yaml'):
    if f.name == 'README.md':
        continue
    with open(f) as fp:
        data = yaml.safe_load(fp)
        if data:  # Skip empty files
            DQConfigFile.model_validate(data)
    print(f'OK {f}')
print('All configs valid!')
"
```

## Troubleshooting

### Error: soft_fail >= hard_fail

```
ValueError: soft_fail (0.25) must be < hard_fail (0.20)
```

**Fix**: Ensure `soft_fail` is strictly less than `hard_fail` in your config.

### Error: Required field not found

```
FileNotFoundError: Required DQ defaults file not found: configs/dq/_defaults.yaml
```

**Fix**: Create `configs/dq/_defaults.yaml` with global settings.

### Validation not applied

**Check**:
1. Is `dq_config_file` path correct in pipeline config?
2. Is field name spelled correctly in validation?
3. Is validation type correct for the field data type?

## References

- [ADR-027: DQ Rules Externalization](../02-architecture/decisions/ADR-027-dq-rules-externalization.md)
- RULES.md §3.1.2: DQ Thresholds
- Schema: `src/bioetl/infrastructure/schemas/dq_config.py`
- Loader: `src/bioetl/infrastructure/config/dq_config_loader.py`
