# Documentation Parity Gate

*Status: Active | Version: 1.0.0 | Last Updated: 2026-04-24*

## Overview

The Documentation Parity Gate ensures that all active entity configurations have corresponding pipeline specification documents and vice versa. This gate helps maintain documentation consistency and completeness.

## CI/CD Integration

The active repository gate runs in [`.github/workflows/docs.yml`](../../.github/workflows/docs.yml)
via the docs job step `Run docs-config parity gate`.

### GitHub Actions Example

```yaml
name: Documentation Parity Check

on:
  push:
    branches: [ main, dev ]
  pull_request:
    branches: [ main, dev ]

jobs:
  docs-parity-check:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
      
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pyyaml
        
    - name: Run documentation parity check
      run: bash scripts/ci_check_docs_parity.sh
```

### GitLab CI Example

```yaml
stages:
  - test
  
docs_parity_check:
  stage: test
  image: python:3.12
  
  script:
    - pip install pyyaml
    - bash scripts/ci_check_docs_parity.sh
  
  artifacts:
    when: always
    paths:
      - parity_report.txt
```

## Manual Execution

To run the parity check manually:

```bash
# Run the active config-to-spec parity gate
uv run python scripts/check_entity_config_parity.py

# Generate the broader parity report JSON used by governance tooling
python3 scripts/docs_parity_check.py
```

## Parity Check Script

The active config/spec gate is located at `scripts/check_entity_config_parity.py`. It performs the following checks:

1. **Config-to-Spec Parity**: Ensures all active entity configs have corresponding pipeline specs
2. **Spec-to-Config Parity**: Ensures all pipeline specs have corresponding entity configs
3. **Status Markers**: Identifies specs with historical/legacy markers (informational only)

### Script Features

- **Automatic Naming Mapping**: Handles common naming differences between configs and specs
- **Parity Scoring**: Calculates a parity score (0-100%) based on coverage
- **Detailed Reporting**: Provides clear output with specific issues found
- **Exit Codes**: Returns appropriate exit codes for CI/CD integration

The broader governance report path is implemented by `scripts/docs_parity_check.py`,
which writes `docs/reports/docs-parity-report.json` for local or CI consumption.

### Exit Codes

- `0`: All checks passed
- `1`: Critical parity issues found
- `2`: Error during execution

## Entity Configuration Requirements

Entity configurations should be placed in `configs/entities/{provider}/{entity}.yaml` and follow this structure:

```yaml
version: 1.0.0
provider: chembl
entity: activity
status: active  # or disabled

# Configuration details...
```

## Pipeline Specification Requirements

Pipeline specifications should be placed in `docs/04-reference/pipelines/{provider}/{entity}-spec.md` and include:

- Clear identification of the pipeline
- Current runtime behavior
- Field specifications
- Quality and validation rules
- Contract references

## Troubleshooting

### Missing Pipeline Specs

If the check reports missing pipeline specs:

1. **Create the missing spec**: Use existing specs as templates
2. **Update naming**: Ensure the spec filename matches the entity name
3. **Add historical markers**: If the spec contains legacy information, add appropriate notices

### Missing Entity Configs

If the check reports missing entity configs:

1. **Create the config**: Use existing configs as templates
2. **Set proper status**: Use `active` or `disabled` as appropriate
3. **Place in correct location**: `configs/entities/{provider}/{entity}.yaml`

### Naming Mismatches

The script handles common naming differences automatically:

| Spec Name | Config Name |
|-----------|-------------|
| `class` | `protein_class` |
| `line` | `cell_line` |
| `parameters` | `assay_parameters` |
| `record` | `compound_record` |
| `component` | `target_component` |
| `term` | `publication_term` |
| `similarity` | `publication_similarity` |
| `fraction` | `subcellular_fraction` |

## Maintenance

### Adding New Entities

When adding new entities:

1. **Create entity config** in `configs/entities/{provider}/{entity}.yaml`
2. **Create pipeline spec** in `docs/04-reference/pipelines/{provider}/{entity}-spec.md`
3. **Run parity check** to verify coverage
4. **Update documentation** in the appropriate sections

### Updating Existing Entities

When updating existing entities:

1. **Update both config and spec** to maintain parity
2. **Add version information** to track changes
3. **Add historical markers** if introducing legacy references
4. **Run parity check** to ensure no regressions

## Related Documentation

- [Pipeline Configuration](pipeline-configuration.md)
- [Pipeline Specification Template](../04-reference/templates/pipeline-spec-template.md)
- [Documentation Governance Policy](../00-project/governance/01-documentation-governance-style-guide.md)

## Support

For issues with the parity gate:

- Check the script output for specific errors
- Review the parity report for detailed information
- Consult the documentation governance policy for guidelines
- Open an issue if you encounter unexpected behavior
