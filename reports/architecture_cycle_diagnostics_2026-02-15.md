# Architecture Audit Report

Date: 2026-02-15
Scope: Python import graph for `bioetl` package (`src/bioetl/**`)

## Executive Summary

- Total findings (cycles): 4
- Critical (MUST): 1
- Moderate (SHOULD): 3
- import-linter contracts: 5/5 kept

## Context

- Installed tooling: `import-linter`, `grimp`.
- Ran layer contracts from `.importlinter`: all passed.
- Built import graph with `grimp.build_graph("bioetl")` and analyzed strongly connected components (SCC).

## Findings

## [CRITICAL] Domain cycle in core contracts/context

**Location**:

- `bioetl.domain.ports`
- `bioetl.domain.ports.runner`
- `bioetl.domain.context`

**Rule Violated**: Circular imports inside domain contracts/context (architectural anti-pattern: circular imports between layers/components).

**Evidence**:

```text
bioetl.domain.ports -> bioetl.domain.ports.runner
bioetl.domain.ports.runner -> bioetl.domain.context
bioetl.domain.context -> bioetl.domain.ports
```

**Impact**: Tight coupling in the domain core can create fragile initialization order, hinder refactoring, and obscure ownership of abstractions.

**Recommendation**:

- Split shared types into a dedicated dependency-neutral module (e.g., `bioetl.domain.types` or `bioetl.domain.contracts.shared`).
- Keep `ports` definitions acyclic by moving runtime/context references behind `typing.TYPE_CHECKING` or protocol boundaries.

**Severity rationale**: Domain is the most stability-critical layer; cycles here should be treated as release-blocking architectural debt.

______________________________________________________________________

## [MODERATE] Infrastructure config/schema cycle cluster

**Location**:

- `bioetl.infrastructure.config`
- `bioetl.infrastructure.config._base`
- `bioetl.infrastructure.config.dq_config_loader`
- `bioetl.infrastructure.config.pipeline_config_loader`
- `bioetl.infrastructure.config_loader`
- `bioetl.infrastructure.schemas.dq_config`
- `bioetl.infrastructure.schemas.pipeline_config`

**Rule Violated**: Circular imports in configuration subsystem.

**Evidence (example cycle)**:

```text
bioetl.infrastructure.config._base -> bioetl.infrastructure.schemas.pipeline_config
bioetl.infrastructure.schemas.pipeline_config -> bioetl.infrastructure.config
bioetl.infrastructure.config -> bioetl.infrastructure.config._base
```

**Impact**: Raises risk of partial module initialization and increases complexity for config/schema evolution.

**Recommendation**:

- Separate schema declarations from loader orchestration (one-way dependency: loaders -> schemas).
- Introduce thin DTO-only module for schema primitives with no loader imports.

______________________________________________________________________

## [MODERATE] Composition bootstrap/runner cycle cluster

**Location**:

- `bioetl.composition._pipeline_execution`
- `bioetl.composition._resource_management`
- `bioetl.composition._services`
- `bioetl.composition.bootstrap`
- `bioetl.composition.bootstrap.runtime`
- `bioetl.composition.bootstrap.runtime.composite`
- `bioetl.composition.bootstrap.runtime.runner`
- `bioetl.composition.entrypoints`
- `bioetl.composition.factories.runner_factory`

**Rule Violated**: Circular imports in composition root internals.

**Evidence (example cycle)**:

```text
bioetl.composition.factories.runner_factory -> bioetl.composition.bootstrap
bioetl.composition.bootstrap -> bioetl.composition.bootstrap.runtime
bioetl.composition.bootstrap.runtime -> bioetl.composition.bootstrap.runtime.runner
bioetl.composition.bootstrap.runtime.runner -> bioetl.composition.factories.runner_factory
```

**Impact**: Composition is allowed broad visibility, but cycles increase bootstrap fragility and complicate dependency injection evolution.

**Recommendation**:

- Enforce a single direction: `entrypoints -> bootstrap -> runtime -> factories`.
- Extract factory interfaces into a leaf module imported by runtime, avoiding runtime-to-factory back edges.

______________________________________________________________________

## [MODERATE] Composition providers/factories cycle cluster

**Location**:

- `bioetl.composition.factories.data_source_factory`
- `bioetl.composition.factories.http_client_factory`
- `bioetl.composition.providers`
- `bioetl.composition.providers._config_helpers`
- `bioetl.composition.providers.loader`
- `bioetl.composition.providers.registration`

**Rule Violated**: Circular imports in provider registration and factory wiring.

**Evidence (example cycle)**:

```text
bioetl.composition.factories.http_client_factory -> bioetl.composition.providers
bioetl.composition.providers -> bioetl.composition.providers.registration
bioetl.composition.providers.registration -> bioetl.composition.providers._config_helpers
bioetl.composition.providers._config_helpers -> bioetl.composition.factories.http_client_factory
```

**Impact**: Impedes clear separation between provider metadata, registration, and concrete factory creation.

**Recommendation**:

- Move provider registry constants/types into standalone module with no factory imports.
- Keep factories consuming registry data, but prevent registry/helpers from importing factories.

## Import-Linter Contract Status

All configured contracts are currently kept:

1. `domain-independence`
1. `application-independence`
1. `infrastructure-independence`
1. `composition-no-interfaces`
1. `no-direct-instantiation-in-application`

## Verification Log

Commands executed:

1. `python -m pip install import-linter grimp`
1. `PYTHONPATH=src lint-imports --config .importlinter`
1. `PYTHONPATH=src python - <<'PY' ... build_graph('bioetl') ... Tarjan SCC analysis ... PY`
1. `PYTHONPATH=src python - <<'PY' ... build_graph('bioetl') ... example cycle extraction ... PY`
