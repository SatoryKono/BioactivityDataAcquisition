______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-28'

______________________________________________________________________

# Data Quality Configuration

*Reference: [ADR-027: DQ Rules Externalization](../02-architecture/decisions/ADR-027-dq-rules-externalization.md)*

This guide describes how to configure Data Quality (DQ) rules in BioETL.

## Overview

DQ rules are organized in a hierarchical configuration structure that enables:

- **Reusability**: Share validations across pipelines
- **Override flexibility**: Entity-specific rules without affecting others
- **DRY principle**: Global thresholds defined once

Current implementation details:

- Provider and entity layers are loaded from the unified `quality:` section when present.
- For backward compatibility, `DQConfigLoader` still accepts flat fallback keys when a YAML file has no `quality:` section.
- Inline overrides are resolved from `pipeline.dq_overrides` in the validated pipeline config.

## Threshold layers (config vs runtime default)

Hierarchical YAML and Silver DQ runtime use related but not identical default
thresholds. Operators must treat both as active surfaces.

| Layer | Source | `soft_fail` | `hard_fail` | Notes |
| --- | --- | ---: | ---: | --- |
| Global YAML defaults | `configs/base/quality.yaml` | `0.05` | `0.50` | Merged through provider/entity `quality:` sections (hierarchical SSOT) |
| Silver analyze request fallback | `src/bioetl/domain/ports/quality/silver_dq_request.py` (`SilverDQAnalyzeRequest`) | `0.05` | `0.20` | Used when runtime request does not override thresholds |
| Composite overrides | `configs/composites/*.yaml` | per surface | per surface | Explicit per-composite DQ policy |

Composite pipelines may define additional per-surface overrides. Contract-level
DQ flags in entity contract YAML under `configs/contracts/{provider}/{entity}.yaml`
remain DQ-only and do not control Gold strict validation
([gold-schemas.md](../04-reference/contracts/gold-schemas.md)).

## Hierarchical DQ Config Structure

```
configs/
├── base/quality.yaml                 # Level 1: Global defaults
├── providers/{provider}.yaml         # Level 2: Section "quality"
└── entities/{provider}/{entity}.yaml # Level 3: Section "quality"
```

## Merge Behavior

Configurations are merged in order (later wins):

| Level | File                                            | Scope                    |
| ----- | ----------------------------------------------- | ------------------------ |
| 1     | `base/quality.yaml`                             | All pipelines            |
| 2     | `providers/{provider}.yaml` (`quality`)         | All entities of provider |
| 3     | `entities/{provider}/{entity}.yaml` (`quality`) | Specific entity          |
| 4     | Inline `pipeline.dq_overrides` in pipeline YAML | Override for exceptions  |

**Merge rules**:

- Scalars: Override (later value wins)
- Validation lists (`*-validations`): Concatenate with deduplication by `name`/`field`
- Nested dicts: Recursive merge

## DQ Thresholds

BioETL has **multiple related default surfaces**. Hard-fail depends on which
surface is active; do not assume a single universal value.

| Surface | Source of truth | Default | Notes |
| --- | --- | --- | --- |
| Hierarchical quality config | `configs/base/quality.yaml`, `ThresholdsConfig` (`dq_config.py`) | `soft_fail=0.05`, `hard_fail=0.50` | Provider/entity `quality:` hierarchy and RULES default |
| Contract-backed DQ loader fallback | `src/bioetl/infrastructure/config/dq_contract_config_loader.py` | `soft_fail=0.05`, `hard_fail=0.50` | When contract YAML omits explicit thresholds |
| Inline pipeline DQ override baseline | `src/bioetl/infrastructure/config/pipeline_dq_resolution.py` | `soft_fail=0.05`, `hard_fail=0.20` | Baseline for detecting whether `pipeline.dq_overrides` changed defaults |
| Silver DQ request shape | `src/bioetl/domain/ports/quality/silver_dq_request.py` | `soft_fail=0.05`, `hard_fail=0.20` | Request-shape default for Silver analyze |

Hierarchical / RULES / contract-loader default hard-fail is **0.50 (50%)**.
The **0.20** value is the Silver request / pipeline-override baseline only.

### Hierarchical `quality:` default

Configured in `configs/base/quality.yaml`:

```yaml
thresholds:
  soft_fail: 0.05      # >5% errors -> Warning
  hard_fail: 0.50      # >50% errors -> Fail Batch (hierarchical default)
```

### Silver / pipeline-override baseline

When Silver DQ request fields or inline `pipeline.dq_overrides` normalization
use code defaults without an explicit hard-fail, the baseline is:

```text
soft_fail = 0.05
hard_fail = 0.20
```

Anchors:

- `src/bioetl/infrastructure/config/pipeline_dq_resolution.py`
- `src/bioetl/domain/ports/quality/silver_dq_request.py`

Contract-backed loader omitted thresholds resolve to **0.50** via
`dq_contract_config_loader.py` (`hard_fail` resolve default).

**Invariant**: `soft_fail` must be strictly less than `hard_fail` on every
surface.

## Complete `base/quality.yaml` Key Reference

| Key                              | Type   | Default        | Description                                                    |
| -------------------------------- | ------ | -------------- | -------------------------------------------------------------- |
| `version`                        | string | `"1.0.0"`      | Schema version of the DQ config                                |
| `thresholds.soft_fail`           | float  | `0.05`         | Error rate (>5%) that triggers a warning in the hierarchical `quality:` defaults |
| `thresholds.hard_fail`           | float  | `0.50`         | Error rate (>50%) that fails the batch in the hierarchical `quality:` defaults |
| `strict_validation`              | bool   | `false`        | Runtime flag for stricter validation/error-handling paths      |
| `invalid_record_policy`          | string | `"quarantine"` | How to handle invalid records: `quarantine`, `skip`, or `fail` |
| `report.enabled`                 | bool   | `true`         | Enable DQ report generation                                    |
| `report.format`                  | string | `"json"`       | Report format: `json`, `yaml`, or `csv`                        |
| `report.include_sample_failures` | bool   | `true`         | Include sample of failed records in report                     |
| `report.sample_size`             | int    | `10`           | Number of failed records to include in sample                  |
| `report.output_path`             | string | `null`         | Custom output path (null = pipeline output dir)                |
| `common_field_validations`       | list   | see below      | Field validations applied to ALL entities                      |
| `common_cross_field_validations` | list   | `[]`           | Cross-field validations applied to ALL entities                |

## Current Traceability Surface

The current implementation exposes DQ provenance in three places:

- DQ reports generated by the postrun DQ report service.
- Silver metadata sidecars can include `dq_summary.rule_provenance` when application code supplies `dq_rule_provenance`.
- Gold metadata sidecars always keep `dq_report_path` and schema contract metadata (`contract_path`, `version`, `validation`).

Threshold provenance today is **not** a single global constant:

- hierarchical config defaults come from `configs/base/quality.yaml` (`hard_fail=0.50`);
- contract-backed loader omitted thresholds also resolve to `hard_fail=0.50`;
- Silver request / pipeline-override baselines use `hard_fail=0.20`;
- provider/entity/composite configs may override both.

What is **not** implemented yet as a unified platform contract:

- a global `contract_version` field across all DQ reports and sidecars;
- a global `rule_bundle_version`;
- one canonical `disposition` object shared by Bronze/Silver/Gold/composite DQ paths.

Those items should be documented as planned control-plane/governance work, not as current behavior.

### Default Common Field Validations

Two validations are applied globally to all entities:

1. **`_content_hash` required** — Content hash must be present after transform (for deduplication)
1. **`_ingestion_ts` pattern** — Ingestion timestamp must match ISO 8601 format (`^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}`)

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
  provider_field_validations: []
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

### Step 3: Add optional inline overrides in `pipeline`

```yaml
# configs/entities/{provider}/{entity}.yaml
pipeline:
  pipeline_name: {provider}-{entity}
  dq_overrides:
    hard_fail_threshold: 0.50
```

## Validation Types

### Field Validations

| Type       | Parameters   | Description                                  |
| ---------- | ------------ | -------------------------------------------- |
| `required` | `nullable`   | Field must be present (unless nullable=true) |
| `range`    | `min`, `max` | Numeric bounds check                         |
| `pattern`  | `pattern`    | Regex match                                  |
| `enum`     | `allowed`    | Value must be in whitelist                   |
| `custom`   | `validator`  | Custom validator function name               |

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

| Condition              | Description                                          |
| ---------------------- | ---------------------------------------------------- |
| `all_present`          | All specified fields must have values                |
| `any_present`          | At least one field must have value                   |
| `mutually_exclusive`   | Only one field can have value                        |
| `conditional_required` | `required_field` needed when `trigger_field` present |
| `custom`               | Custom validator function                            |

**Examples:**

```yaml
entity_cross_field_validations:
  # If value present, units should be present
  - name: value-requires-units
    fields:
      - standard_value
      - standard_units
    condition: conditional_required
    trigger_field: standard_value
    required_field: standard_units
    error_message: "Units required when value is present"

  # At least one identifier must be present
  - name: need-identifier
    fields:
      - chembl_id
      - inchi_key
      - smiles
    condition: any_present
    error_message: "At least one identifier required"
```

### Conditional Validations

Apply validations only when a condition is met.

| Parameter            | Description                                                             |
| -------------------- | ----------------------------------------------------------------------- |
| `condition_field`    | Field to check for condition                                            |
| `condition_value`    | Value(s) that trigger the validation                                    |
| `condition_operator` | Comparison operator: `eq`, `ne`, `in`, `not_in` |
| `then_validations`   | List of validations to apply when condition is true                     |

**Example:**

```yaml
entity_conditional_validations:
  # When assay_type is 'B' (Binding), target must be present
  - name: binding-requires-target
    condition_field: assay_type
    condition_value: B
    condition_operator: eq
    then_validations:
      - field: target_chembl_id
        type: required
        nullable: false
        error_message: "Binding assays must have a target"

  # When activity_type is in [IC50, Ki], standard_value required
  - name: potency-needs-value
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
# configs/entities/chembl/activity.yaml
version: "1.0.0"
provider: chembl
entity: activity

quality:
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
    - name: value-requires-units
      fields: [standard_value, standard_units]
      condition: conditional_required
      trigger_field: standard_value
      required_field: standard_units
      error_message: "standard_units required when standard_value is present"

  entity_conditional_validations:
    - name: binding-requires-target
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
# configs/entities/chembl/activity.yaml
pipeline:
  pipeline_name: chembl_activity

  # Temporary override for migration period
  dq_overrides:
    hard_fail_threshold: 0.30  # Higher tolerance during migration
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
uv run python -m scripts.schema validate-configs
```

## Troubleshooting

### Error: soft_fail >= hard_fail

```
ValueError: soft_fail_threshold must be strictly less than hard_fail_threshold
```

**Fix**: Ensure `soft_fail` is strictly less than `hard_fail` in your config.

### Error: Required field not found

```
FileNotFoundError: Required DQ defaults file not found: configs/base/quality.yaml
```

**Fix**: Create `configs/base/quality.yaml` with global settings.

### Validation not applied

**Check**:

1. Is `quality` section present in `configs/entities/{provider}/{entity}.yaml`?
1. Is field name spelled correctly in validation?
1. Is validation type correct for the field data type?

## References

- [ADR-027: DQ Rules Externalization](../02-architecture/decisions/ADR-027-dq-rules-externalization.md)
- RULES.md §3.1.2: DQ Thresholds
- Schema: `src/bioetl/infrastructure/schemas/dq_config.py`
- Loader: `src/bioetl/infrastructure/config/dq_config_loader.py`
