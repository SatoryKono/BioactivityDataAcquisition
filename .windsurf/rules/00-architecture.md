---
trigger: glob
description: "BioETL Architecture — Layers, Ports & Adapters, Import Matrix"
globs:
  - "src/**/*.py"
  - "tests/**/*.py"
---

# Layer Architecture (Clean / Ports & Adapters)

**Canonical references:** `AGENTS.md`, `docs/00-project/RULES.md`, `docs/01-requirements/REQUIREMENTS.md`, `docs/02-architecture/decisions/`.

**Philosophy**: "Pragmatic engineering" — avoid over-engineering, accelerate time-to-market.

**Layers** (`src/bioetl/`):
- **domain/**: Pure business logic, Protocols (typing.Protocol), NO I/O
- **application/**: Orchestration, use cases
- **infrastructure/**: Adapters, concrete implementations
- **composition/**: DI wiring — ONLY place knowing ALL layers
- **interfaces/**: CLI; routes concrete wiring through `composition/`, not `infrastructure/`

## Import Matrix (MUST follow)

| From ↓ / To → | domain | app | infra | comp | iface |
|---------------|--------|-----|-------|--------|-------|
| domain        | ✅ | ❌ | ❌ | ❌ | ❌ |
| application   | ✅ | ✅ | ❌ | ❌ | ❌ |
| infrastructure| ✅ | ❌ | ✅ | ❌ | ❌ |
| composition   | ✅ | ✅ | ✅ | ✅ | ❌ |
| interfaces    | ✅ | ✅ | ❌ | ✅ | ✅ |

## Ports & Protocols

- Define external dependency abstractions as `typing.Protocol` in `bioetl.domain.ports`
- Import port interfaces **only** via facade: `from bioetl.domain.ports import ...` (never `bioetl.domain.ports.*` submodules)
- `*Port` suffix = cross-layer contract in `domain/ports/`
- `*Protocol` suffix = layer-internal structural typing (allowed)
- Domain/application code MUST depend on `*Port` Protocols, not concrete SDK/client classes
- Critical ports MUST be `@runtime_checkable`: DataSourcePort, FilterableDataSourcePort, HealthCheckPort, StoragePort

## Domain Layer Purity (NO I/O)

Domain modules MUST NOT:
- Import I/O libraries: `httpx`, `requests`, `aiohttp`, DB clients/ORMs, message brokers, `structlog`, `logging`
- Import from `infrastructure/`, `adapters/`, or other infra packages
- Call `open()`, network APIs, DB sessions, or logging directly

Allowed: pure stdlib (`math`, `dataclasses`, `typing`, `datetime` arithmetic) and `*Port` abstractions.

## Composition Wiring

- All DI wiring, factories, and environment-specific service assembly MUST live in `src/bioetl/composition/`
- Feature modules receive dependencies via constructor/parameters, not direct instantiation
- Composition modules contain wiring only — no business logic
- Violation: modules outside `composition/` constructing collaborating components or performing env-specific wiring

## Import-Time Side Effects

Domain and application modules MUST NOT perform side effects at import time:
- No I/O, logging, env reads that trigger actions, or global state mutation
- Bootstrap logic belongs in composition/CLI entry points only

## Structured Logging

- Application logging MUST go through `LoggerPort` (keyword arguments for context)
- Forbidden in domain/application: `print()`, `logging.getLogger()`, `structlog.get_logger()`

## Required Methods

**Health Check** (ALL adapters):
```python
async def health_check(self) -> HealthStatus:
    # Returns: HEALTHY, DEGRADED, or UNHEALTHY
    # MUST be async, MUST NOT raise exceptions
```

**Resource Cleanup** (ALL services/adapters):
```python
async def aclose(self) -> None:
    # Idempotent, MUST NOT raise, SHOULD: self._client = None
```

## Architecture Verification

```bash
uv run python -m scripts.engineering.qa check-exemptions
uv run python -m pytest tests/architecture/test_quality_debt_scorecard.py -q
uv run python -m pytest tests/architecture/test_regression_metrics.py -q
```
