# 0003 Provider Registry Via Config

## Status
Accepted

## Context
Providers and pipelines are already enumerated through declarative YAML files under `configs/`, and canonical provider identifiers are used across domain contracts. The application relies on this registry to route extraction, transformation, and writing to the correct adapters.

## Decision
We will keep the provider registry driven by configuration files, using canonical snake_case IDs validated at load time. The container reads these configs to register provider-specific adapters, schemas, and pipeline definitions without embedding provider metadata in code.

## Consequences
- Adding a provider is primarily a configuration change accompanied by new adapters; orchestration code remains unchanged.
- Registry validation prevents drift between configs and available implementations.
- Documentation remains the source of truth for provider IDs, keeping naming consistent across pipelines and schemas.
