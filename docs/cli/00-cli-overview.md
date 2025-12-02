# 00 CLI Overview

The BioETL command-line interface (CLI) is the primary way to run pipelines, validate configurations, and integrate with automation tools such as CI.

This document provides a high-level overview of the CLI design and how it relates to configuration and project rules.

## Entry Points

The CLI is implemented using Typer and exposed through a static registry of commands.

Depending on your installation, you may invoke the CLI via a console script (for example `bioetl`) or by running the module directly (for example `python -m bioetl.cli`).

In the examples below, `bioetl` is used as a placeholder for whatever entry point is configured in your environment.

## Design Principles

- **Explicit commands and flags**: Prefer explicit named options over ambiguous positional arguments
- **Deterministic behavior**: Identical inputs and configuration should lead to byte-identical outputs
- **Idempotent commands**: Running the same command twice with the same inputs should not produce conflicting or inconsistent artifacts
- **Clear exit codes**: Successful commands exit with code `0`. Validation or runtime errors result in non-zero exit codes that can be checked in CI

## Relationship to IDE Commands

In the development environment, convenience commands may be exposed as IDE slash commands (for example `/run-activity-chembl` or `/run-chembl-all`).

These commands are thin wrappers around the same underlying CLI functionality described in this section and should follow the same contracts for flags, determinism, and exit codes.

## Logging and Observability

All CLI commands are expected to:

- Initialize a unified run context (for example `run_id`, `pipeline`, `stage`, `dataset`, `source`)
- Emit structured logs via UnifiedLogger instead of using `print` or raw logging calls

This ensures that pipeline runs are observable and can be audited in production and CI environments.

## Related Components

- **UnifiedLogger**: структурированное логирование (см. `docs/02-pipelines/02-logging-and-configuration.md`)
- **FileConfigResolver**: резолвер конфигурации (см. `docs/02-pipelines/config/28-config-resolver.md`)
