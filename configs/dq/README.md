# DQ Configuration

Data Quality configuration hierarchy for BioETL pipelines.

*Reference: [ADR-027: DQ Rules Externalization](../../docs/02-architecture/decisions/ADR-027-dq-rules-externalization.md)*

## Structure

```
dq/
├── _defaults.yaml       # Global defaults (REQUIRED)
├── providers/           # Provider-level overrides
│   └── {provider}.yaml
└── entities/            # Entity-specific rules
    └── {provider}/
        └── {entity}.yaml
```

## Merge Priority

1. `_defaults.yaml` (lowest)
2. `providers/{provider}.yaml`
3. `entities/{provider}/{entity}.yaml`
4. Inline `dq_rules` in pipeline config (highest)

## Quick Start

### Add validation for new entity

1. Create entity config:
   ```yaml
   # entities/{provider}/{entity}.yaml
   version: "1.0.0"
   provider: {provider}
   entity: {entity}

   entity_field_validations:
     - field: id
       type: required
       nullable: false
   ```

2. Reference in pipeline:
   ```yaml
   # pipelines/{provider}/{entity}.yaml
   dq_config_file: ../../dq/entities/{provider}/{entity}.yaml
   ```

### Override threshold for specific pipeline

```yaml
# pipelines/{provider}/{entity}.yaml
dq_config_file: ../../dq/entities/{provider}/{entity}.yaml
dq_rules:
  thresholds:
    hard_fail: 0.30  # Temporary override
```

## Thresholds

Default thresholds from RULES.md:

| Threshold | Value | Behavior |
|-----------|-------|----------|
| `soft_fail` | 0.05 | Warning (>5% errors) |
| `hard_fail` | 0.20 | Batch fails (>20% errors) |

## Validation Types

| Type | Parameters | Description |
|------|------------|-------------|
| `required` | `nullable` | Field must be present |
| `range` | `min`, `max` | Numeric bounds |
| `pattern` | `pattern` | Regex match |
| `enum` | `allowed` | Value whitelist |
| `custom` | `validator` | Custom validator function |

## Cross-Field Conditions

| Condition | Description |
|-----------|-------------|
| `all_present` | All fields must have values |
| `any_present` | At least one field must have value |
| `mutually_exclusive` | Only one field can have value |
| `conditional_required` | Field required when trigger present |
| `custom` | Custom validator |

## Validation

```bash
# Validate all configs
python -c "
from pathlib import Path
import yaml
from bioetl.infrastructure.schemas.dq_config import DQConfigFile

for f in Path('configs/dq').rglob('*.yaml'):
    if f.name == 'README.md':
        continue
    with open(f) as fp:
        data = yaml.safe_load(fp)
        if data:
            DQConfigFile.model_validate(data)
    print(f'OK {f}')
"
```

## Files

| File | Purpose |
|------|---------|
| `_defaults.yaml` | Global thresholds, common validations |
| `providers/chembl.yaml` | ChEMBL-specific overrides |
| `providers/pubchem.yaml` | PubChem-specific overrides |
| `providers/uniprot.yaml` | UniProt-specific overrides |
| `entities/chembl/activity.yaml` | Activity-specific rules |
| `entities/chembl/assay.yaml` | Assay-specific rules |
| `entities/chembl/molecule.yaml` | Molecule-specific rules |
| `entities/chembl/target.yaml` | Target-specific rules |
| `entities/pubchem/compound.yaml` | Compound-specific rules |
| `entities/uniprot/target.yaml` | UniProt target-specific rules |

## Reference

- [ADR-027: DQ Rules Externalization](../../docs/02-architecture/decisions/ADR-027-dq-rules-externalization.md)
- [DQ Configuration Guide](../../docs/03-guides/dq-configuration.md)
- RULES.md Section 3.1.2: DQ Thresholds
- Schema: `src/bioetl/infrastructure/schemas/dq_config.py`
- Loader: `src/bioetl/infrastructure/config/dq_config_loader.py`
