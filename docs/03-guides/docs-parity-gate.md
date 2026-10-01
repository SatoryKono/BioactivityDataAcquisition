# Documentation Parity Gate

*Status: Active | Version: 1.1.0 | Last Updated: 2026-10-01*

## Overview

The Documentation Parity Gate ensures that all active entity configurations have corresponding pipeline specification documents and vice versa. It also fails when an active pipeline spec still labels itself as a historical or legacy stub instead of a canonical published summary.

## CI/CD Integration

The active repository gate runs in [`.github/workflows/docs.yml`](../../.github/workflows/docs.yml)
via the docs job step `Run docs-config parity gate`.

### GitHub Actions Example (фактический docs.yml step)

```yaml
      - name: Run docs-config parity gate
        run: >-
          uv run --frozen --no-build python -m scripts.data_quality
          check-entity-config-parity
```

Legacy-примеры (`bash scripts/ci_check_docs_parity.sh`, отдельный GitLab-job)
удалены: скрипты `scripts/ci_check_docs_parity.sh` и `scripts/docs_parity_check.py`
помечены retired/non-CI (см. ниже) и не вызываются из CI.

## Manual Execution

To run the parity check manually:

```bash
# Run the active config-to-spec parity gate
uv run --frozen --no-build python -m scripts.data_quality check-entity-config-parity
```

Retired local-only report (non-CI, не gate): `python3 scripts/docs_parity_check.py`
пишет `docs/reports/docs-parity-report.json` для локального разбора. В CI не
используется.

## Parity Check Script

The active config/spec gate is located at
`scripts/data_quality/check_entity_config_parity.py` and is invoked through the
`scripts.data_quality` package CLI. It performs the following checks:

1. **Config-to-Spec Parity**: Ensures all active entity configs have corresponding pipeline specs
1. **Spec-to-Config Parity**: Ensures all pipeline specs have corresponding entity configs
1. **Page-Role Enforcement**: Fails when active specs still self-identify as historical or legacy summaries

### Script Features

- **Automatic Naming Mapping**: Handles common naming differences between configs and specs
- **Parity Scoring**: Calculates a parity score (0-100%) based on coverage
- **Detailed Reporting**: Provides clear output with specific issues found
- **Exit Codes**: Returns appropriate exit codes for CI/CD integration

The broader governance report path is implemented by the retired
`scripts/docs_parity_check.py` (non-CI, local use only), which writes
`docs/reports/docs-parity-report.json` for local consumption.

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
1. **Update naming**: Ensure the spec filename matches the entity name
1. **Convert the page to a canonical compact summary**: keep historical field notes only where they explain runtime compatibility, but remove any page-level historical/legacy stub labeling

### Missing Entity Configs

If the check reports missing entity configs:

1. **Create the config**: Use existing configs as templates
1. **Set proper status**: Use `active` or `disabled` as appropriate
1. **Place in correct location**: `configs/entities/{provider}/{entity}.yaml`

### Naming Mismatches

The script handles common naming differences automatically:

| Spec Name    | Config Name              |
| ------------ | ------------------------ |
| `class`      | `protein_class`          |
| `line`       | `cell_line`              |
| `parameters` | `assay_parameters`       |
| `record`     | `compound_record`        |
| `component`  | `target_component`       |
| `term`       | `publication_term`       |
| `similarity` | `publication_similarity` |
| `fraction`   | `subcellular_fraction`   |

## Maintenance

### Adding New Entities

When adding new entities:

1. **Create entity config** in `configs/entities/{provider}/{entity}.yaml`
1. **Create pipeline spec** in `docs/04-reference/pipelines/{provider}/{entity}-spec.md`
1. **Run parity check** to verify coverage
1. **Update documentation** in the appropriate sections

### Updating Existing Entities

When updating existing entities:

1. **Update both config and spec** to maintain parity
1. **Add version information** to track changes
1. **Keep the page canonical** even when you preserve compatibility notes for older field names or API aliases
1. **Run parity check** to ensure no regressions

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
