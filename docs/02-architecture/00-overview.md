# Architecture Overview

*Synced with RULES.md v5.10 (2026-01-05)*

## Quick Navigation

BioETL follows a **Hexagonal Architecture** (Ports & Adapters) pattern with **Medallion Architecture** for data layers.

### Layer Documentation

| Layer | Document | Key Contents |
|-------|----------|--------------|
| **Domain** | [01-domain-layer.md](01-domain-layer.md) | Ports, Models, Schemas, Pure logic |
| **Application** | [02-application-layer.md](02-application-layer.md) | Pipelines, Use Cases, Orchestration |
| **Infrastructure** | [03-infrastructure-layer.md](03-infrastructure-layer.md) | Adapters, HTTP clients, Storage |
| **Interfaces** | [04-interfaces-layer.md](04-interfaces-layer.md) | CLI, API endpoints |
| **Composition** | [05-composition-layer.md](05-composition-layer.md) | DI container, Bootstrap, Factories |

### System Views

| Document | Description | C4 Level |
|----------|-------------|----------|
| [system-context.md](system-context.md) | External systems interaction | Level 1 |
| [container-diagram.md](container-diagram.md) | Internal containers & services | Level 2 |
| [data-flow.md](data-flow.md) | Medallion data flow | - |
| [data-layers.md](data-layers.md) | Bronze/Silver/Gold details | - |
| [observability-layers.md](observability-layers.md) | Metrics, Tracing, Logging | - |

### Diagrams

- [diagrams/](diagrams/) — 34 Mermaid diagram files
- [diagrams/diagrams-index.md](diagrams/diagrams-index.md) — Full diagram index
- [diagrams.md](diagrams.md) — Inline diagram collection

### Architecture Decision Records (ADRs)

22 ADRs documenting key architectural decisions:

| ADR | Topic | RULES.md Reference |
|-----|-------|-------------------|
| [ADR-001](decisions/ADR-001-delta-lake-vs-parquet.md) | Delta Lake vs Parquet | §2.1, §3 |
| [ADR-002](decisions/ADR-002-medallion-architecture.md) | Medallion Architecture | §1 |
| [ADR-003](decisions/ADR-003-in-memory-locking-strategy.md) | In-Memory Locking | §6 |
| [ADR-004](decisions/ADR-004-pydantic-vs-dataclasses.md) | Pydantic vs Dataclasses | - |
| [ADR-005](decisions/ADR-005-composition-layer-separation.md) | Composition Layer | §1.1 |
| [ADR-006](decisions/ADR-006-logger-metrics-ports.md) | Logger & Metrics Ports | - |
| [ADR-007](decisions/ADR-007-circuit-breaker-implementation.md) | Circuit Breaker | §3.1.4 |
| [ADR-008](decisions/ADR-008-graceful-shutdown-strategy.md) | Graceful Shutdown | §5.3 |
| [ADR-009](decisions/ADR-009-paginated-fetcher-mixin.md) | Paginated Fetcher | - |
| [ADR-010](decisions/ADR-010-local-only-deployment.md) | Local-Only Deployment | §5.6 |
| [ADR-011](decisions/ADR-011-remove-watermark-mechanism.md) | Remove Watermark | - |
| [ADR-012](decisions/ADR-012-storage-clear-contract-and-run-id.md) | Storage Clear Contract | §2.4 |
| [ADR-013](decisions/ADR-013-async-storage-cleanup.md) | Async Storage Cleanup | - |
| [ADR-014](decisions/ADR-014-deterministic-writes.md) | Deterministic Writes | - |
| [ADR-015](decisions/ADR-015-pipeline-services-lifecycle.md) | Pipeline Services Lifecycle | - |
| [ADR-016](decisions/ADR-016-error-handling-strategy.md) | Error Handling Strategy | §3.1 |
| [ADR-017](decisions/ADR-017-observability-architecture.md) | Observability Architecture | §3.2 |
| [ADR-018](decisions/ADR-018-gold-strict-validation.md) | Gold Strict Validation | §2.1 |
| [ADR-019](decisions/ADR-019-observability-port-enforcement.md) | Observability Port Enforcement | - |
| [ADR-020](decisions/ADR-020-basepipeline-decomposition.md) | BasePipeline Decomposition | - |
| [ADR-021](decisions/ADR-021-ddd-aggregates-adoption.md) | DDD Aggregates | - |
| [ADR-022](decisions/ADR-022-tracing-noop.md) | Tracing NoOp | - |

---

## Architecture Principles

### Import Matrix (Layer Dependencies)

| From ↓ / To → | domain | application | composition | infrastructure | interfaces |
|---------------|--------|-------------|-------------|----------------|------------|
| **domain** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **application** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **composition** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **infrastructure** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **interfaces** | ✅ | ✅ | ✅ | ✅ | ✅ |

**Violation = PR Blocker.** Enforced by `import-linter` and `tests/architecture/`.

### Key Patterns

1. **Dependency Injection**: Dependencies injected via constructor
2. **Ports & Adapters**: Interfaces in `domain/ports/`, implementations in `infrastructure/`
3. **Composition Root**: Single assembly point in `composition/bootstrap.py`
4. **Medallion Architecture**: Bronze (raw) → Silver (normalized) → Gold (curated)

---

## Related Documents

- [RULES.md](../RULES.md) — Project rules (source of truth)
- [00-map.md](../00-map.md) — Full project navigator
- [glossary.md](../glossary.md) — Ubiquitous language terminology
