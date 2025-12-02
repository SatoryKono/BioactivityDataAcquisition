# 03 Config Precedence and Profiles

BioETL supports layered configuration so that defaults can be shared across pipelines while still allowing precise overrides.

This document explains how different configuration sources interact and how to use profiles effectively.

## Precedence Rules

Configuration sources are applied in the following order, from highest priority to lowest:

1. Environment variables
2. CLI overrides (for example `--set key=value`)
3. Pipeline configuration files
4. Profiles

Later items in the list provide defaults that can be overridden by higher-priority sources.

## Profiles

Profiles are reusable named configuration fragments that capture common settings, such as network defaults or determinism options.

Examples include:

- A base profile with general defaults
- A determinism profile that enforces strict sorting and golden-comparison behavior
- Environment-specific profiles such as `dev` or `prod`

Profiles are typically selected via a dedicated CLI flag or field in the configuration file.

## CLI Overrides with --set

For fine-grained overrides, the CLI may support a `--set` option that allows setting individual keys without editing the underlying configuration file.

A conceptual example:

```bash
bioetl run activity_chembl \
  --config configs/pipelines/activity/example.yaml \
  --set pipeline.run_id=example-run-001
```

In this example, the `pipeline.run_id` field is overridden at runtime without changing the YAML file on disk.

## Recommendations

- Keep most defaults in profiles and shared configuration files
- Use environment variables and `--set` for truly environment-specific or ephemeral overrides (such as run identifiers)
- Avoid scattering important defaults across multiple layers; document them in configuration files and profiles so they remain discoverable

## Related Components

- **FileConfigResolver**: резолвер конфигурации (см. `docs/02-pipelines/config/28-config-resolver.md`)
- **EnvSecretProvider**: провайдер секретов (см. `docs/02-pipelines/config/29-secret-provider.md`)

