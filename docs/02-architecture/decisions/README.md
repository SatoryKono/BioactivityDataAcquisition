______________________________________________________________________

Version: 1.0.3
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-28'

______________________________________________________________________

# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records documenting significant architectural decisions for the BioETL project.

## ADR Index

| ADR                                                      | Title                                      | Status                                  | Category        | Date       |
| -------------------------------------------------------- | ------------------------------------------ | --------------------------------------- | --------------- | ---------- |
| [ADR-001](ADR-001-delta-lake-vs-parquet.md)              | Delta Lake vs Parquet                      | Accepted                                | Storage         | 2025-05-20 |
| [ADR-002](ADR-002-medallion-architecture.md)             | Medallion Architecture                     | Accepted                                | Architecture    | 2025-05-20 |
| [ADR-003](ADR-003-in-memory-locking-strategy.md)         | In-Memory Locking (MemoryLock)             | Superseded                              | Locking         | 2025-12-23 |
| [ADR-004](ADR-004-pydantic-vs-dataclasses.md)            | Pydantic vs Dataclasses                    | Accepted                                | Data Modeling   | 2025-05-20 |
| [ADR-005](ADR-005-composition-layer-separation.md)       | Composition Layer Separation               | Accepted                                | Architecture    | 2025-12-15 |
| [ADR-006](ADR-006-logger-metrics-ports.md)               | Logger and Metrics Ports                   | Accepted                                | Observability   | 2025-12-18 |
| [ADR-007](ADR-007-circuit-breaker-implementation.md)     | Circuit Breaker Implementation             | Accepted                                | Resilience      | 2025-12-22 |
| [ADR-008](ADR-008-graceful-shutdown-strategy.md)         | Graceful Shutdown Strategy                 | Superseded                              | Lifecycle       | 2025-12-22 |
| [ADR-009](ADR-009-paginated-fetcher-mixin.md)            | PaginatedFetcherMixin Design               | Accepted                                | Data Fetching   | 2025-12-22 |
| [ADR-010](ADR-010-local-only-deployment.md)              | Local-Only Deployment                      | Accepted                                | Deployment      | 2025-12-23 |
| [ADR-011](ADR-011-remove-watermark-mechanism.md)         | Remove Watermark Mechanism                 | Accepted                                | Data Loading    | 2025-12-23 |
| [ADR-012](ADR-012-storage-clear-contract-and-run-id.md)  | Storage Clear Contract and Run ID          | Accepted                                | Storage         | 2025-12-23 |
| [ADR-013](ADR-013-async-storage-cleanup.md)              | Async Storage Cleanup                      | Accepted                                | Storage         | 2025-12-24 |
| [ADR-014](ADR-014-deterministic-writes.md)               | Deterministic Writes and Retries           | Accepted                                | Reproducibility | 2025-12-24 |
| [ADR-015](ADR-015-pipeline-services-lifecycle.md)        | Pipeline Services Lifecycle                | Accepted                                | Lifecycle       | 2025-12-24 |
| [ADR-016](ADR-016-error-handling-strategy.md)            | Error Handling Strategy                    | Accepted                                | Resilience      | 2025-12-26 |
| [ADR-017](ADR-017-observability-architecture.md)         | Observability Architecture                 | Accepted                                | Observability   | 2025-12-26 |
| [ADR-018](ADR-018-gold-strict-validation.md)             | Gold Strict Validation                     | Accepted                                | Data Quality    | 2025-12-26 |
| [ADR-019](ADR-019-observability-port-enforcement.md)     | Observability Port Enforcement             | Accepted                                | Observability   | 2025-12-26 |
| [ADR-020](ADR-020-basepipeline-decomposition.md)         | BasePipeline Decomposition                 | Accepted                                | Architecture    | 2025-12-16 |
| [ADR-021](ADR-021-ddd-aggregates-adoption.md)            | DDD Aggregates Adoption                    | Accepted                                | Domain Model    | 2025-12-29 |
| [ADR-022](ADR-022-tracing-noop.md)                       | NoOp Tracing for Local-Only                | Accepted                                | Observability   | 2025-12-30 |
| [ADR-023](ADR-023-entity-type-patterns.md)               | Entity Type Patterns                       | Accepted                                | Observability   | 2026-01-06 |
| [ADR-024](ADR-024-entity-naming-unification.md)          | Entity Naming Unification                  | Accepted                                | Architecture    | 2026-01-06 |
| [ADR-025](ADR-025-pipeline-config-unification.md)        | Pipeline Config Unification                | Accepted (partial supersede by ADR-039) | Configuration   | 2026-01-19 |
| [ADR-026](ADR-026-composite-pipeline-pattern.md)         | Composite Pipeline Pattern                 | Accepted                                | Architecture    | 2026-01-15 |
| [ADR-027](ADR-027-dq-rules-externalization.md)           | DQ Rules Externalization                   | Accepted                                | Data Quality    | 2026-01-19 |
| [ADR-028](ADR-028-filter-rules-externalization.md)       | Filter Rules Externalization               | Accepted                                | Configuration   | 2026-01-20 |
| [ADR-029](ADR-029-output-metadata-unification.md)        | Output Metadata Unification                | Accepted                                | Data Modeling   | 2026-01-23 |
| [ADR-030](ADR-030-publication-pagination-strategy.md)    | Publication Pagination Strategy            | Accepted                                | Data Fetching   | 2026-01-26 |
| [ADR-031](ADR-031-loading-strategy-formalization.md)     | Loading Strategy Formalization             | Accepted                                | Data Loading    | 2026-01-26 |
| [ADR-032](ADR-032-unified-http-client.md)                | Unified HTTP Client Pattern                | Accepted                                | HTTP/Networking | 2026-01-28 |
| [ADR-033](ADR-033-publication-validation-strategy.md)    | Publication Metadata Validation Strategy   | Accepted                                | Data Quality    | 2026-02-06 |
| [ADR-034](ADR-034-schema-domain-pairs.md)                | Schema↔Domain Configuration Pairs          | Accepted                                | Architecture    | 2026-02-15 |
| [ADR-035](ADR-035-json-field-typing-policy.md)           | JSON Field Typing Policy (Silver↔Gold)     | Accepted                                | Data Modeling   | 2026-02-17 |
| [ADR-036](ADR-036-gold-contract-versioning-policy.md)    | Gold Contract Versioning Policy            | Accepted                                | Data Quality    | 2026-02-18 |
| [ADR-037](ADR-037-canonical-schema-generation.md)        | Canonical Schema Source and Generation     | Accepted                                | Data Contracts  | 2026-02-18 |
| [ADR-038](ADR-038-enum-externalization.md)               | ChEMBL Enum Values Externalization to YAML | Accepted                                | Configuration   | 2026-02-16 |
| [ADR-039](ADR-039-unified-entity-config-format.md)       | Unified Entity Config Format               | Accepted                                | Configuration   | 2026-02-24 |
| [ADR-040](ADR-040-diagram-governance.md)                 | Diagram Governance and Layout Policy       | Accepted                                | Documentation   | 2026-02-25 |
| [ADR-041](ADR-041-naming-policy-skills-agents.md)        | Naming Policy for Skills, Agents, Commands | Accepted                                | Architecture    | 2026-03-04 |
| [ADR-042](ADR-042-testing-strategy-matrix.md)            | Testing Strategy Matrix & Fixture Gov.     | Accepted                                | Testing         | 2026-03-09 |
| [ADR-043](ADR-043-documentation-knowledge-management.md) | Documentation & Knowledge Management       | Accepted                                | Documentation   | 2026-03-09 |
| [ADR-044](ADR-044-run-manifest-ledger-control-plane.md)  | Run Manifest & Ledger Control Plane        | Accepted                                | Reproducibility | 2026-03-24 |
| [ADR-045](ADR-045-dq-contract-system.md)                 | Data Quality Contract System               | Accepted                                | Data Quality    | 2026-03-26 |
| [ADR-046](ADR-046-checkpoint-vs-ledger-resume.md)        | Checkpoint Versus Ledger-Based Resume      | Accepted                                | Reproducibility | 2026-05-06 |
| [ADR-047](ADR-047-workflow-control-plane.md)             | Workflow Control Plane for Declarative Workflows | Accepted                           | Reproducibility | 2026-05-08 |
| [ADR-048](ADR-048-domain-schema-boundary-and-runtime-pandera-compat.md) | Domain Schema Boundary and Runtime Pandera Compatibility | Accepted | Architecture | 2026-05-26 |
| [ADR-049](ADR-049-context-aware-loc-target-policy.md) | Context-Aware LOC Target Policy | Accepted | Architecture | 2026-05-26 |
| [ADR-050](ADR-050-silver-structural-gold-semantic-filter-boundary.md) | Silver Structural and Gold Semantic Filter Boundary | Accepted | Data Quality | 2026-06-15 |
| [ADR-051](ADR-051-quarantine-entry-aggregate-surface.md) | QuarantineEntry Wide Constructor as Intentional Aggregate Surface | Accepted | Architecture | 2026-07-27 |
| [ADR-052](ADR-052-infrastructure-config-package-root-public-api.md) | Infrastructure Config Package Root as Permanent Public API | Accepted | Architecture | 2026-07-28 |

## ADRs by Category

### Architecture (Core Patterns)

- [ADR-002](ADR-002-medallion-architecture.md): Medallion Architecture (Bronze/Silver/Gold)
- [ADR-005](ADR-005-composition-layer-separation.md): Composition Layer Separation (DI)
- [ADR-020](ADR-020-basepipeline-decomposition.md): BasePipeline Decomposition (God Object removal)
- [ADR-024](ADR-024-entity-naming-unification.md): Entity Naming Unification
- [ADR-026](ADR-026-composite-pipeline-pattern.md): Composite Pipeline Pattern
- [ADR-034](ADR-034-schema-domain-pairs.md): Schema↔Domain Configuration Pairs — Domain frozen dataclasses vs Infrastructure Pydantic models
- [ADR-040](ADR-040-diagram-governance.md): Diagram Governance and Layout Policy
- [ADR-041](ADR-041-naming-policy-skills-agents.md): Naming Policy for Skills, Agents, and Commands
- [ADR-043](ADR-043-documentation-knowledge-management.md): Documentation and Knowledge Management Strategy
- [ADR-048](ADR-048-domain-schema-boundary-and-runtime-pandera-compat.md): Domain Schema Boundary and Runtime Pandera Compatibility
- [ADR-049](ADR-049-context-aware-loc-target-policy.md): Context-Aware LOC Target Policy
- [ADR-051](ADR-051-quarantine-entry-aggregate-surface.md): QuarantineEntry Wide Constructor as Intentional Aggregate Surface
- [ADR-052](ADR-052-infrastructure-config-package-root-public-api.md): Infrastructure Config Package Root as Permanent Public API

### Storage

- [ADR-001](ADR-001-delta-lake-vs-parquet.md): Delta Lake vs Parquet
- [ADR-012](ADR-012-storage-clear-contract-and-run-id.md): Storage Clear Contract and Run ID
- [ADR-013](ADR-013-async-storage-cleanup.md): Async Storage Cleanup

### Resilience & Error Handling

- [ADR-007](ADR-007-circuit-breaker-implementation.md): Circuit Breaker Implementation
- [ADR-016](ADR-016-error-handling-strategy.md): Error Handling Strategy
- [ADR-032](ADR-032-unified-http-client.md): Unified HTTP Client Pattern — Centralized HTTP with rate limiting and retry

### Observability

- [ADR-006](ADR-006-logger-metrics-ports.md): Logger and Metrics Ports
- [ADR-017](ADR-017-observability-architecture.md): Observability Architecture
- [ADR-019](ADR-019-observability-port-enforcement.md): Observability Port Enforcement
- [ADR-022](ADR-022-tracing-noop.md): NoOp Tracing for Local-Only
- [ADR-023](ADR-023-entity-type-patterns.md): Entity Type Patterns (transformer entity_type)

### Lifecycle Management

- [ADR-008](ADR-008-graceful-shutdown-strategy.md): Graceful Shutdown Strategy — superseded historical context; see ADR-015
- [ADR-015](ADR-015-pipeline-services-lifecycle.md): Pipeline Services Lifecycle

### Data Quality

- [ADR-018](ADR-018-gold-strict-validation.md): Gold Strict Validation
- [ADR-027](ADR-027-dq-rules-externalization.md): DQ Rules Externalization — Hierarchical DQ config
- [ADR-033](ADR-033-publication-validation-strategy.md): Publication Metadata Validation Strategy — 5-level validation for publication data
- [ADR-036](ADR-036-gold-contract-versioning-policy.md): Gold Contract Versioning Policy — Semver for Gold contracts with breaking window policy
- [ADR-045](ADR-045-dq-contract-system.md): Data Quality Contract System
- [ADR-050](ADR-050-silver-structural-gold-semantic-filter-boundary.md): Silver structural and Gold semantic filter boundary

### Domain Model

- [ADR-004](ADR-004-pydantic-vs-dataclasses.md): Pydantic vs Dataclasses
- [ADR-021](ADR-021-ddd-aggregates-adoption.md): DDD Aggregates Adoption
- [ADR-029](ADR-029-output-metadata-unification.md): Output Metadata Unification — Unified output metadata contracts
- [ADR-035](ADR-035-json-field-typing-policy.md): JSON Field Typing Policy (Silver↔Gold)
- [ADR-037](ADR-037-canonical-schema-generation.md): Canonical schema source + generated artifact gates

### Data Fetching

- [ADR-009](ADR-009-paginated-fetcher-mixin.md): PaginatedFetcherMixin Design
- [ADR-011](ADR-011-remove-watermark-mechanism.md): Remove Watermark Mechanism
- [ADR-030](ADR-030-publication-pagination-strategy.md): Publication Pagination Strategy
- [ADR-031](ADR-031-loading-strategy-formalization.md): Loading Strategy Formalization

### Deployment

- [ADR-010](ADR-010-local-only-deployment.md): Local-Only Deployment

### Locking

- [ADR-003](ADR-003-in-memory-locking-strategy.md): In-Memory Locking (MemoryLock) — historical locking decision now superseded by ADR-010

### Testing

- [ADR-042](ADR-042-testing-strategy-matrix.md): Testing Strategy Matrix and Fixture Governance

### Reproducibility

- [ADR-014](ADR-014-deterministic-writes.md): Deterministic Writes and Retries
- [ADR-044](ADR-044-run-manifest-ledger-control-plane.md): Run Manifest and Run Ledger Control Plane
- [ADR-046](ADR-046-checkpoint-vs-ledger-resume.md): Checkpoint Versus Ledger-Based Resume (Accepted)
- [ADR-047](ADR-047-workflow-control-plane.md): Workflow Control Plane for Declarative Workflows

### Configuration

- [ADR-025](ADR-025-pipeline-config-unification.md): Pipeline Config Unification
- [ADR-028](ADR-028-filter-rules-externalization.md): Filter Rules Externalization — Hierarchical filter config
- [ADR-038](ADR-038-enum-externalization.md): ChEMBL Enum Values Externalization to YAML
- [ADR-039](ADR-039-unified-entity-config-format.md): Unified Entity Config Format
- [ADR-050](ADR-050-silver-structural-gold-semantic-filter-boundary.md): Silver structural and Gold semantic filter boundary

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
         ├─────────────────────┐
         ▼                     ▼
   ┌───────────┐         ┌───────────┐
   │  ADR-022  │         │  ADR-023  │
   │ NoOp Trac │◄────────┤Entity Type│
   └───────────┘         └───────────┘
         │
         │◄────────────────────────────┐
                                       │
                                ┌───────────┐
                                │  ADR-010  │
                                │Local-Only │──────► ADR-003 (historical Redis→MemoryLock transition)
                                └───────────┘
                                       │
                                       ▼
                                ┌───────────┐
                                │  ADR-011  │
                                │Rm Watermark│
                                └───────────┘
```

### ADR-024..045 Relationships

```
                    ┌─────────────────────────────────────────┐
                    │        Configuration & Schemas          │
                    └─────────────────────────────────────────┘
                                        │
         ┌──────────────────────────────┼──────────────────────────────┐
         ▼                              ▼                              ▼
   ┌───────────┐                 ┌───────────┐                  ┌───────────┐
   │  ADR-025  │─ superseded by ─►  ADR-039  │                  │  ADR-027  │
   │Config Unif│                 │Entity Cfg │                  │DQ Extern  │
   └───────────┘                 └───────────┘                  └───────────┘
                                       │                              │
                                       ▼                              ▼
                                ┌───────────┐                  ┌───────────┐
                                │  ADR-038  │                  │  ADR-028  │
                                │Enum Extern│                  │Filter Ext │
                                └───────────┘                  └───────────┘
                                                                      │
                                                                      ▼
                                                               ┌───────────┐
                                                               │  ADR-045  │
                                                               │DQ Contract│
                                                               └───────────┘

         ┌─────────────────────────────────────────────────────────────┐
         │                  Schema & Contracts                         │
         └─────────────────────────────────────────────────────────────┘
                                        │
         ┌──────────────────────────────┼──────────────────────────────┐
         ▼                              ▼                              ▼
   ┌───────────┐                 ┌───────────┐                  ┌───────────┐
   │  ADR-034  │◄───────────────┤  ADR-037  │                  │  ADR-035  │
   │Schema↔Dom │                │Canon Schema│                  │JSON Fields│
   └───────────┘                └───────────┘                  └───────────┘
         │                                                             │
         ▼                                                             ▼
   ┌───────────┐                                                ┌───────────┐
   │  ADR-036  │                                                │  ADR-033  │
   │Gold Versn │                                                │Pub Valid  │
   └───────────┘                                                └───────────┘

         ┌─────────────────────────────────────────────────────────────┐
         │                Pipeline & Infrastructure                    │
         └─────────────────────────────────────────────────────────────┘
                                        │
         ┌──────────────────────────────┼──────────────────────────────┐
         ▼                              ▼                              ▼
   ┌───────────┐                 ┌───────────┐                  ┌───────────┐
   │  ADR-026  │                 │  ADR-030  │                  │  ADR-032  │
   │Composite  │                 │Pub Paging │                  │Unified HTTP│
   └───────────┘                └───────────┘                  └───────────┘
         │
         ▼
   ┌───────────┐                 ┌───────────┐                  ┌───────────┐
   │  ADR-024  │                 │  ADR-029  │                  │  ADR-031  │
   │Entity Name│                 │Meta Unif  │                  │Load Strat │
   └───────────┘                └───────────┘                  └───────────┘

         ┌─────────────────────────────────────────────────────────────┐
         │                   Governance & Process                      │
         └─────────────────────────────────────────────────────────────┘
                                        │
         ┌──────────────────────────────┼──────────────────────────────┐
         ▼                              ▼                              ▼
   ┌───────────┐                 ┌───────────┐                  ┌───────────┐
   │  ADR-040  │                 │  ADR-041  │                  │  ADR-042  │
   │Diagram Gov│                 │Name Policy│                  │Test Strat │
   └───────────┘                └───────────┘                  └───────────┘
                                                                       │
                                                                       ▼
                                                                ┌───────────┐
                                                                │  ADR-043  │
                                                                │Doc & KM   │
                                                                └───────────┘
```

ADR-044 extends the lifecycle and metadata line by introducing a dedicated
control-plane layer for immutable run manifests and append-only run ledgers.
ADR-045 formalizes the Data Quality Contract System, building upon the
externalization patterns defined in ADR-027 and ADR-028.

## Writing New ADRs

### Template

```markdown
# ADR-XXX: [Title]

*   **Status**: Added | Accepted | Superseded | Deprecated
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

- [ADR-001](ADR-001-delta-lake-vs-parquet.md): Description — how it relates
```

### Naming Convention

ADR files follow the pattern: `ADR-NNN-kebab-case-title.md`

- Numbers are sequential (001, 002, 003...)
- Titles use kebab-case
- Status should be in the header metadata

## References

- [RULES.md](../../00-project/RULES.md) — Project rules referencing these ADRs
- [CLAUDE.md](../../00-project/ai/agents/guides/CLAUDE.md) — Developer guide with ADR context
- [Michael Nygard's ADR format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
