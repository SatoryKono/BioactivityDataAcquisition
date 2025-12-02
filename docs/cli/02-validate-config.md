# 02 Validate Config

Before running pipelines, configuration files should be validated to catch schema and value errors early.

The BioETL CLI provides a dedicated command for validating configuration files without executing a full pipeline run.

## Purpose

- Ensure that configuration files conform to the expected schema
- Validate that profiles, paths, and important parameters are well-formed
- Fail fast in CI when configuration is invalid

## Typical Usage

A conceptual example:

```bash
bioetl validate-config \
  --config configs/pipelines/activity/example.yaml
```

In this example:

- `validate-config` is the subcommand that performs validation only
- `--config` points to the YAML configuration file to validate

Implementations may support additional options such as selecting profiles or printing normalized configuration.

## Exit Codes

The expected behavior is:

- Exit code `0` when the configuration is valid
- A non-zero exit code when validation fails

This contract allows CI jobs to treat configuration validation as a strict gate.

## Integration with Profiles and Precedence

Configuration validation should respect the same precedence rules as runtime execution:

1. Environment variables
2. CLI overrides (such as `--set`)
3. Pipeline configuration files
4. Profiles

This ensures that the configuration being validated matches what will be used during an actual pipeline run.

## Related Components

- **FileConfigResolver**: резолвер конфигурации (см. `docs/02-pipelines/config/00-config-resolver.md`)
- **ConfigValidationError**: исключение валидации (см. `docs/02-pipelines/chembl/common/13-config-validation-error.md`)

