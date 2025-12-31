# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records documenting significant architectural decisions for the BioETL project.

## ADR Index

| ADR | Title | Status | Category | Date |
|-----|-------|--------|----------|------|
| [ADR-001](ADR-001-delta-lake-vs-parquet.md) | Delta Lake vs Parquet | Accepted | Storage | 2025-05-20 |
| [ADR-002](ADR-002-medallion-architecture.md) | Medallion Architecture | Accepted | Architecture | 2025-05-20 |
| [ADR-003](ADR-003-redis-for-distributed-locking.md) | Redis for Distributed Locking | **Superseded** | Locking | 2025-05-20 |
| [ADR-004](ADR-004-pydantic-vs-dataclasses.md) | Pydantic vs Dataclasses | Accepted | Data Modeling | 2025-05-20 |
| [ADR-005](ADR-005-composition-layer-separation.md) | Composition Layer Separation | Accepted | Architecture | 2025-12-15 |
| [ADR-006](ADR-006-logger-metrics-ports.md) | Logger and Metrics Ports | Accepted | Observability | 2025-12-18 |
| [ADR-007](ADR-007-circuit-breaker-implementation.md) | Circuit Breaker Implementation | Accepted | Resilience | 2025-12-22 |
| [ADR-008](ADR-008-graceful-shutdown-strategy.md) | Graceful Shutdown Strategy | Accepted | Lifecycle | 2025-12-22 |
| [ADR-009](ADR-009-paginated-fetcher-mixin.md) | PaginatedFetcherMixin Design | Accepted | Data Fetching | 2025-12-22 |
| [ADR-010](ADR-010-local-only-deployment.md) | Local-Only Deployment | Accepted | Deployment | 2025-12-23 |
| [ADR-011](ADR-011-remove-watermark-mechanism.md) | Remove Watermark Mechanism | Accepted | Data Loading | 2025-12-23 |
| [ADR-012](ADR-012-storage-clear-contract-and-run-id.md) | Storage Clear Contract and Run ID | Accepted | Storage | 2025-12-23 |
| [ADR-013](ADR-013-async-storage-cleanup.md) | Async Storage Cleanup | Accepted | Storage | 2025-12-24 |
| [ADR-014](ADR-014-deterministic-writes.md) | Deterministic Writes and Retries | Accepted | Reproducibility | 2025-12-24 |
| [ADR-015](ADR-015-pipeline-services-lifecycle.md) | Pipeline Services Lifecycle | Accepted | Lifecycle | 2025-12-24 |
| [ADR-016](ADR-016-error-handling-strategy.md) | Error Handling Strategy | Accepted | Resilience | 2025-12-26 |
| [ADR-017](ADR-017-observability-architecture.md) | Observability Architecture | Accepted | Observability | 2025-12-26 |
| [ADR-018](ADR-018-gold-strict-validation.md) | Gold Strict Validation | Accepted | Data Quality | 2025-12-26 |
| [ADR-019](ADR-019-observability-port-enforcement.md) | Observability Port Enforcement | Accepted | Observability | 2025-12-26 |
| [ADR-020](ADR-020-basepipeline-decomposition.md) | BasePipeline Decomposition | Accepted | Architecture | 2025-12-16 |
| [ADR-021](ADR-021-ddd-aggregates-adoption.md) | DDD Aggregates Adoption | Accepted | Domain Model | 2025-12-29 |
| [ADR-022](ADR-022-tracing-noop.md) | NoOp Tracing for Local-Only | Accepted | Observability | 2025-12-30 |

## ADRs by Category

### Architecture (Core Patterns)
- [ADR-002](ADR-002-medallion-architecture.md): Medallion Architecture (Bronze/Silver/Gold)
- [ADR-005](ADR-005-composition-layer-separation.md): Composition Layer Separation (DI)
- [ADR-020](ADR-020-basepipeline-decomposition.md): BasePipeline Decomposition (God Object removal)

### Storage
- [ADR-001](ADR-001-delta-lake-vs-parquet.md): Delta Lake vs Parquet
- [ADR-012](ADR-012-storage-clear-contract-and-run-id.md): Storage Clear Contract and Run ID
- [ADR-013](ADR-013-async-storage-cleanup.md): Async Storage Cleanup

### Resilience & Error Handling
- [ADR-007](ADR-007-circuit-breaker-implementation.md): Circuit Breaker Implementation
- [ADR-016](ADR-016-error-handling-strategy.md): Error Handling Strategy

### Observability
- [ADR-006](ADR-006-logger-metrics-ports.md): Logger and Metrics Ports
- [ADR-017](ADR-017-observability-architecture.md): Observability Architecture
- [ADR-019](ADR-019-observability-port-enforcement.md): Observability Port Enforcement
- [ADR-022](ADR-022-tracing-noop.md): NoOp Tracing for Local-Only

### Lifecycle Management
- [ADR-008](ADR-008-graceful-shutdown-strategy.md): Graceful Shutdown Strategy
- [ADR-015](ADR-015-pipeline-services-lifecycle.md): Pipeline Services Lifecycle

### Data Quality
- [ADR-018](ADR-018-gold-strict-validation.md): Gold Strict Validation

### Domain Model
- [ADR-004](ADR-004-pydantic-vs-dataclasses.md): Pydantic vs Dataclasses
- [ADR-021](ADR-021-ddd-aggregates-adoption.md): DDD Aggregates Adoption

### Data Fetching
- [ADR-009](ADR-009-paginated-fetcher-mixin.md): PaginatedFetcherMixin Design
- [ADR-011](ADR-011-remove-watermark-mechanism.md): Remove Watermark Mechanism

### Deployment
- [ADR-010](ADR-010-local-only-deployment.md): Local-Only Deployment

### Locking (Superseded)
- [ADR-003](ADR-003-redis-for-distributed-locking.md): Redis for Distributed Locking — **Superseded by ADR-010**

### Reproducibility
- [ADR-014](ADR-014-deterministic-writes.md): Deterministic Writes and Retries

## ADR Relationships Graph

```
                    ┌─────────────────────────────────────────┐
                    │            Core Architecture            │
                    └─────────────────────────────────────────┘
                                        │
         ┌──────────────────────────────┼──────────────────────────────┐
         ▼                              ▼                              ▼
   ┌───────────┐                 ┌───────────┐                  ┌───────────┐
   │  ADR-001  │                 │  ADR-002  │                  │  ADR-005  │
   │ Delta Lake│ ◄───────────────┤ Medallion │──────────────────► Composition│
   └───────────┘                 └───────────┘                  └───────────┘
         │                              │                              │
         │                              │                              │
         ▼                              ▼                              ▼
   ┌───────────┐                 ┌───────────┐                  ┌───────────┐
   │  ADR-012  │                 │  ADR-018  │                  │  ADR-020  │
   │Storage Clr│────────────────►│Gold Valid │                  │ BasePipe  │
   └───────────┘                 └───────────┘                  └───────────┘
         │                                                             │
         ▼                                                             ▼
   ┌───────────┐                                                ┌───────────┐
   │  ADR-013  │                                                │  ADR-015  │
   │Async Clean│◄───────────────────────────────────────────────┤ Services  │
   └───────────┘                                                └───────────┘
                                                                       │
         ┌─────────────────────────────────────────────────────────────┤
         ▼                              ▼                              ▼
   ┌───────────┐                 ┌───────────┐                  ┌───────────┐
   │  ADR-006  │                 │  ADR-008  │                  │  ADR-021  │
   │Logger/Metr│                 │ Shutdown  │                  │DDD Aggreg │
   └───────────┘                 └───────────┘                  └───────────┘
         │                              │
         ▼                              ▼
   ┌───────────┐                 ┌───────────┐
   │  ADR-017  │                 │  ADR-007  │
   │Observabil.│                 │Circuit Brk│
   └───────────┘                 └───────────┘
         │                              │
         ├──────────────────────────────┤
         ▼                              ▼
   ┌───────────┐                 ┌───────────┐
   │  ADR-019  │                 │  ADR-016  │
   │Port Enforc│                 │Error Handl│
   └───────────┘                 └───────────┘
         │
         ▼
   ┌───────────┐
   │  ADR-022  │
   │ NoOp Trac │◄───────────────────────┐
   └───────────┘                        │
                                        │
                                 ┌───────────┐
                                 │  ADR-010  │
                                 │Local-Only │──────► ADR-003 (Superseded)
                                 └───────────┘
                                        │
                                        ▼
                                 ┌───────────┐
                                 │  ADR-011  │
                                 │Rm Watermark│
                                 └───────────┘
```

## Writing New ADRs

### Template

```markdown
# ADR-XXX: [Title]

*   **Status**: Proposed | Accepted | Superseded | Deprecated
*   **Date**: YYYY-MM-DD
*   **Supersedes**: ADR-NNN (if applicable)
*   **Related**: ADR-NNN, ADR-NNN (brief context)

## Context

[Describe the issue and why a decision is needed]

## The Decision

[Describe the chosen solution]

## Justification

[Explain why this decision was made]

## Consequences

### Positive
- [benefit]

### Negative
- [tradeoff]

## Related ADRs

- [ADR-NNN](ADR-NNN-title.md): Description — how it relates
```

### Naming Convention

ADR files follow the pattern: `ADR-NNN-kebab-case-title.md`

- Numbers are sequential (001, 002, 003...)
- Titles use kebab-case
- Status should be in the header metadata

## References

- [RULES.md](../../RULES.md) — Project rules referencing these ADRs
- [CLAUDE.md](../../../CLAUDE.md) — Developer guide with ADR context
- [Michael Nygard's ADR format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
