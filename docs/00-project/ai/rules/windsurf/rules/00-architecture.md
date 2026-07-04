---
trigger: glob
description: "BioETL Architecture — Layers, Ports & Adapters, Import Matrix"
globs:
  - "src/**/*.py"
  - "tests/**/*.py"
---

# Layer Architecture (Clean / Ports & Adapters)

**Canonical references:** `AGENTS.md`, `docs/00-project/NORMATIVE_SOURCES.md`, `docs/00-project/RULES.md`, `docs/01-requirements/REQUIREMENTS.md`, `docs/02-architecture/decisions/`.

**Patterns:** Hexagonal Architecture, DDD, Medallion Architecture, Composite Pipeline Pattern.

**Layers** (`src/bioetl/`):
- **domain/**: Value Objects, aggregates, events, enums, errors, ports, immutable configs, data contracts — NO I/O
- **application/**: Use cases, lifecycle, BatchWriter, RecordProcessor, DQ orchestration via ports
- **infrastructure/**: HTTP/storage/Delta/quarantine/observability adapters — NO business rules
- **composition/**: **Only** Composition Root — DI, factories, bootstrap, pipeline assembly
- **interfaces/**: CLI, health/metrics surfaces, request validation — NO business logic; NO direct `infrastructure/` import

## Import Matrix (MUST follow)

| From ↓ / To → | domain | app | infra | comp | iface |
|---------------|--------|-----|-------|--------|-------|
| domain        | ✅ | ❌ | ❌ | ❌ | ❌ |
| application   | ✅ | ✅ | ❌ | ❌ | ❌ |
| infrastructure| ✅ | ❌ | ✅ | ❌ | ❌ |
| composition   | ✅ | ✅ | ✅ | ✅ | ❌ |
| interfaces    | ✅ | ✅ | ❌ | ✅ | ✅ |

**Forbidden:** cyclic dependencies, service locator, hidden global mutable state, module-import side effects, concrete adapters in domain/application signatures.

## Ports & Protocols

- Cross-layer ports: `typing.Protocol` in `bioetl.domain.ports`; import **only** via facade: `from bioetl.domain.ports import ...`
- `*Port` = cross-layer contract; local `*Protocol` = layer-internal structural typing (not a cross-layer port)
- Primary enforcement: `mypy --strict`; `@runtime_checkable` on composition boundary for critical ports per ADR
- Critical ports SHOULD be `@runtime_checkable`: DataSourcePort, FilterableDataSourcePort, HealthCheckPort, StoragePort

## Domain Layer

**MUST NOT:** I/O libraries (`httpx`, `requests`, DB clients, `structlog`, `logging`), infra imports, `open()`, network/DB calls, concrete logging.

**ADR-048 exception:** Pandera/Pandas allowed **only** as schema-contract representation in:
- `src/bioetl/domain/schemas/`
- `src/bioetl/domain/contracts/`

Runtime DataFrame processing, compatibility bootstrap, and infrastructure mapping in domain **MUST NOT**.

**Value Objects / immutable configs:** frozen dataclasses unless approved alternative.

Runtime Pandera compat: **only** via `bioetl.composition.bootstrap.runtime.pipeline.apply_runtime_compatibility_patches` → `infrastructure.compat.pandera_compat`. Import-time `__init__` patching **MUST NOT**.

## Application Layer

- Orchestrates via ports; **MUST NOT** know URLs, paths, storage drivers, HTTP libs, or concrete `*Impl`
- **MUST NOT** create writers, clients, locks, clocks, metrics/loggers internally

## Composition & Interfaces

- All concrete creation, constructor DI, provider registration, bootstrap live in `composition/`
- Reuse existing port/DTO/Value Object; parallel abstraction of same meaning requires ADR
- `interfaces/` delegates to application/composition only

## Domain Aggregates (invariants)

**Batch:** OPEN → SEALED → WRITING → COMMITTED | FAILED. Records only in OPEN; indices sequential; content hash after seal excludes occurrence/meta fields.

**PipelineRun:** PENDING → RUNNING → COMPLETED | FAILED | SHUTDOWN. First mandatory stage failure → FAILED; terminal state immutable.

**QuarantineEntry:** entry_id, payload, hash, Bronze linkage immutable after creation; resolution creates new Silver candidate, not mutation.

## Pipeline Lifecycle (ordinary)

preflight → adapter health → lock → extract → Bronze → transform → DQ/schema → Silver → Gold prep → Gold strict validation → Gold write → checkpoint/postrun → terminal event → cleanup (idempotent finally).

- Checkpoint **only after** durable commit
- Mandatory stage failure stops subsequent business stages; cleanup/lock release in finally
- `PipelineService` is async context manager; all adapters/services: idempotent `async def aclose()` (no exceptions)

## Adapter Health Contract (ALL adapters)

```python
async def health_check(self) -> HealthStatus:
    # Lightweight probe, bounded timeout, MUST NOT raise — return UNHEALTHY on error
```

Provider probes: ChEMBL `/status.json`, PubChem lightweight compound query, others dedicated endpoint or generic 5s timeout.

## Structured Logging

Application logging via `LoggerPort` (keyword context). Forbidden in domain/application/interfaces: `print()`, `logging.getLogger()`, `structlog.get_logger()`.

## Architecture Verification

```bash
uv run lint-imports --config .importlinter
uv run python -m pytest tests/architecture/ -m "not slow and not benchmark and not memory" -q
uv run python -m scripts.engineering.qa check-exemptions
```
