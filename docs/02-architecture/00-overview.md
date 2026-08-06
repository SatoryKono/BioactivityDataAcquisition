______________________________________________________________________

Version: 1.1.2
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-05'

______________________________________________________________________

# Architecture Overview

*Synced with RULES.md v6.1.7 (2026-08-05)*

## Architecture health scores (do not collapse)

Two different instruments report “architecture health.” They **must not** be
treated as the same number:

| Instrument | Typical use | Example (2026-08-05) |
| --- | --- | ---: |
| **Human maintainability audit** (ARCH-REF / review report) | Density, residual structure, cognitive load, package ownership | **7.82** / 10 |
| **Machine quality scorecard** (`reports/quality/architecture-quality-scorecard.json`) | Layer violations, coverage floors, hotspot budgets, gate pass rates | **9.41** |

Scorecard green means **gates hold**; it does **not** mean residual package
sprawl or mixin graphs are finished. Prefer human audit for prioritization of
structure refactors (ARCH-REF-R2 / #7734). Ports counts come from the generator
`python -m scripts.engineering.qa report-domain-ports-inventory` (not hand-edited).

## Quick Navigation

BioETL follows a **Hexagonal Architecture** (Ports & Adapters) pattern with **Medallion Architecture** for data layers.

For published contracts, CLI surfaces, pipeline/provider specs, and package
reference, use the [Reference Index](../04-reference/index.md). This
architecture section focuses on structure, boundaries, and design rationale.

### Layer Documentation

| Layer              | Document                                                 | Key Contents                                          |
| ------------------ | -------------------------------------------------------- | ----------------------------------------------------- |
| **Domain**         | [01-domain-layer.md](01-domain-layer.md)                 | Ports, Models, Schemas, Pure logic                    |
| **Application**    | [02-application-layer.md](02-application-layer.md)       | Pipelines, Use Cases, Orchestration                   |
| **Infrastructure** | [03-infrastructure-layer.md](03-infrastructure-layer.md) | Adapters, HTTP clients, Storage                       |
| **Interfaces**     | [04-interfaces-layer.md](04-interfaces-layer.md)         | CLI, HTTP health server, orchestration entry surfaces |
| **Composition**    | [05-composition-layer.md](05-composition-layer.md)       | DI wiring, bootstrap, factories, runtime builders     |

### System Views

| Document                                                      | Description                    | C4 Level |
| ------------------------------------------------------------- | ------------------------------ | -------- |
| [current-state-inventory.md](current-state-inventory.md)      | Current code/config/docs inventory and drift findings | - |
| [current-state-diagrams.md](current-state-diagrams.md)        | Current C4, layer, dependency, medallion, lifecycle diagrams | 1-2 |
| [system-context.md](system-context.md)                        | External systems interaction   | Level 1  |
| [container-diagram.md](diagrams/guide/container-reference.md) | Internal containers & services | Level 2  |
| [data-flow.md](diagrams/guide/data-flow-reference.md)         | Medallion data flow            | -        |
| [data-layers.md](data-layers.md)                              | Bronze/Silver/Gold details     | -        |
| [observability-layers.md](observability-layers.md)            | Metrics, Tracing, Logging      | -        |

### Diagrams

- [diagrams/](diagrams/README.md) — Canonical Mermaid source files (`.mmd`)
- [diagram catalog](diagrams/README.md) — Full diagram catalog, bundles, and generated views
- [diagrams/guide/index.md](diagrams/guide/index.md) — Inline diagram collection

### Architecture Decision Records (ADRs)

See [decisions/README.md](decisions/README.md) for full index with categories.

55 ADRs documenting key architectural decisions:

| ADR                                                                | Topic                                     | RULES.md Reference |
| ------------------------------------------------------------------ | ----------------------------------------- | ------------------ |
| [ADR-001](decisions/ADR-001-delta-lake-vs-parquet.md)              | Delta Lake vs Parquet                     | §2.1, §3           |
| [ADR-002](decisions/ADR-002-medallion-architecture.md)             | Medallion Architecture                    | §1                 |
| [ADR-003](decisions/ADR-003-in-memory-locking-strategy.md)         | In-Memory Locking *(Superseded; see ADR-010)* | §6             |
| [ADR-004](decisions/ADR-004-pydantic-vs-dataclasses.md)            | Pydantic vs Dataclasses                   | -                  |
| [ADR-005](decisions/ADR-005-composition-layer-separation.md)       | Composition Layer                         | §1.1               |
| [ADR-006](decisions/ADR-006-logger-metrics-ports.md)               | Logger & Metrics Ports                    | -                  |
| [ADR-007](decisions/ADR-007-circuit-breaker-implementation.md)     | Circuit Breaker                           | §3.1.4             |
| [ADR-008](decisions/ADR-008-graceful-shutdown-strategy.md)         | Graceful Shutdown *(Superseded; see ADR-015)* | §5.3           |
| [ADR-009](decisions/ADR-009-paginated-fetcher-mixin.md)            | Paginated Fetcher                         | -                  |
| [ADR-010](decisions/ADR-010-local-only-deployment.md)              | Local-Only Deployment                     | §5.6               |
| [ADR-011](decisions/ADR-011-remove-watermark-mechanism.md)         | Remove Watermark                          | -                  |
| [ADR-012](decisions/ADR-012-storage-clear-contract-and-run-id.md)  | Storage Clear Contract                    | §2.4               |
| [ADR-013](decisions/ADR-013-async-storage-cleanup.md)              | Async Storage Cleanup                     | -                  |
| [ADR-014](decisions/ADR-014-deterministic-writes.md)               | Deterministic Writes                      | -                  |
| [ADR-015](decisions/ADR-015-pipeline-services-lifecycle.md)        | Pipeline Services Lifecycle               | -                  |
| [ADR-016](decisions/ADR-016-error-handling-strategy.md)            | Error Handling Strategy                   | §3.1               |
| [ADR-017](decisions/ADR-017-observability-architecture.md)         | Observability Architecture                | §3.2               |
| [ADR-018](decisions/ADR-018-gold-strict-validation.md)             | Gold Strict Validation                    | §2.1               |
| [ADR-019](decisions/ADR-019-observability-port-enforcement.md)     | Observability Port Enforcement            | -                  |
| [ADR-020](decisions/ADR-020-basepipeline-decomposition.md)         | BasePipeline Decomposition                | -                  |
| [ADR-021](decisions/ADR-021-ddd-aggregates-adoption.md)            | DDD Aggregates                            | -                  |
| [ADR-022](decisions/ADR-022-tracing-noop.md)                       | Tracing NoOp                              | -                  |
| [ADR-023](decisions/ADR-023-entity-type-patterns.md)               | Entity Type Patterns                      | -                  |
| [ADR-024](decisions/ADR-024-entity-naming-unification.md)          | Entity Naming Unification                 | -                  |
| [ADR-025](decisions/ADR-025-pipeline-config-unification.md)        | Pipeline Config Unification               | -                  |
| [ADR-026](decisions/ADR-026-composite-pipeline-pattern.md)         | Composite Pipeline Pattern                | -                  |
| [ADR-027](decisions/ADR-027-dq-rules-externalization.md)           | DQ Rules Externalization                  | §3.1.2             |
| [ADR-028](decisions/ADR-028-filter-rules-externalization.md)       | Filter Rules Externalization              | App D              |
| [ADR-029](decisions/ADR-029-output-metadata-unification.md)        | Output Metadata Unification               | §2.4               |
| [ADR-030](decisions/ADR-030-publication-pagination-strategy.md)    | Publication Pagination Strategy           | -                  |
| [ADR-031](decisions/ADR-031-loading-strategy-formalization.md)     | Loading Strategy Formalization            | -                  |
| [ADR-032](decisions/ADR-032-unified-http-client.md)                | Unified HTTP Client Pattern               | §3.1               |
| [ADR-033](decisions/ADR-033-publication-validation-strategy.md)    | Publication Metadata Validation Strategy  | -                  |
| [ADR-034](decisions/ADR-034-schema-domain-pairs.md)                | Schema↔Domain Configuration Pairs         | -                  |
| [ADR-035](decisions/ADR-035-json-field-typing-policy.md)           | JSON Field Typing Strategy                | -                  |
| [ADR-036](decisions/ADR-036-gold-contract-versioning-policy.md)    | Gold Contract Versioning                  | §2.1               |
| [ADR-037](decisions/ADR-037-canonical-schema-generation.md)        | Canonical Schema Generation               | -                  |
| [ADR-038](decisions/ADR-038-enum-externalization.md)               | Enum Externalization                      | -                  |
| [ADR-039](decisions/ADR-039-unified-entity-config-format.md)       | Unified Entity Config Format              | App D              |
| [ADR-040](decisions/ADR-040-diagram-governance.md)                 | Diagram Governance                        | -                  |
| [ADR-041](decisions/ADR-041-naming-policy-skills-agents.md)        | Naming Policy for Skills & Agents         | -                  |
| [ADR-042](decisions/ADR-042-testing-strategy-matrix.md)            | Testing Strategy Matrix                   | -                  |
| [ADR-043](decisions/ADR-043-documentation-knowledge-management.md) | Documentation & Knowledge Management      | -                  |
| [ADR-044](decisions/ADR-044-run-manifest-ledger-control-plane.md)  | Run Manifest and Run Ledger Control Plane | -                  |
| [ADR-045](decisions/ADR-045-dq-contract-system.md)                 | Data Quality Contract System              | -                  |
| [ADR-046](decisions/ADR-046-checkpoint-vs-ledger-resume.md)        | Checkpoint Versus Ledger-Based Resume     | -                  |
| [ADR-047](decisions/ADR-047-workflow-control-plane.md)             | Workflow Control Plane for Declarative Workflows | -           |
| [ADR-048](decisions/ADR-048-domain-schema-boundary-and-runtime-pandera-compat.md) | Domain Schema Boundary and Runtime Pandera Compatibility | - |
| [ADR-049](decisions/ADR-049-context-aware-loc-target-policy.md)     | Context-Aware LOC Target Policy           | -                  |
| [ADR-050](decisions/ADR-050-silver-structural-gold-semantic-filter-boundary.md) | Silver Structural and Gold Semantic Filter Boundary | §2.1, App D |
| [ADR-051](decisions/ADR-051-quarantine-entry-aggregate-surface.md) | QuarantineEntry aggregate constructor surface | §2.6 |
| [ADR-052](decisions/ADR-052-infrastructure-config-package-root-public-api.md) | Infrastructure config package root public API | §1, composition |
| [ADR-053](decisions/ADR-053-optional-grafana-scenes-app-shell.md) | Optional Grafana Scenes app shell (presentation adapter) | §3.2, ADR-010 |
| [ADR-054](decisions/ADR-054-passport-documentation-projections.md) | Evidence-backed passport documentation projections | §6, DOC-GOV |
| [ADR-055](decisions/ADR-055-workflow-reconciliation-data-step-ownership.md) | Workflow reconciliation data-step ownership | §2.4, ADR-047 |

______________________________________________________________________

## Architecture Principles

### Import Matrix (Layer Dependencies)

| From ↓ / To →      | domain | application | infrastructure | composition | interfaces |
| ------------------ | ------ | ----------- | -------------- | ----------- | ---------- |
| **domain**         | ✅     | ❌          | ❌             | ❌          | ❌         |
| **application**    | ✅     | ✅          | ❌             | ❌          | ❌         |
| **infrastructure** | ✅     | ❌          | ✅             | ❌          | ❌         |
| **composition**    | ✅     | ✅          | ✅             | ✅          | ❌         |
| **interfaces**     | ✅     | ✅          | ❌             | ✅          | ✅         |

**Violation = PR Blocker.** Enforced by `import-linter` and `tests/architecture/`.
Direct `interfaces -> infrastructure` imports are forbidden; interfaces must
obtain concrete runtime wiring through composition entrypoints.

### Key Patterns

1. **Dependency Injection**: Dependencies injected via constructor
1. **Ports & Adapters**: Interfaces in `domain/ports/`, implementations in `infrastructure/`
1. **Composition Root**: Assembly layer centered on `composition/` with `bootstrap/`, `factories/`, `providers/`, `runtime_builders/`, and service APIs
1. **Medallion Architecture**: Bronze (raw) → Silver (normalized) → Gold (curated)
1. **Composite Pipeline** (ADR-026): Multi-source data enrichment with seed → enrich (fan-out) → merge workflow

### Key Diagrams

| Diagram                 | Description                                    | File                                                                                             |
| ----------------------- | ---------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Five Layer Architecture | Complete system architecture with all 5 layers | [01-high-level.mmd](diagrams/foundation/01-high-level.mmd)                                       |
| Layers Interaction      | How layers communicate                         | [05-layers-interaction.mmd](diagrams/foundation/05-layers-interaction.mmd)                       |
| Composite Pipeline      | ADR-026 workflow: seed → enrich → merge        | [29-composite-pipeline-workflow.mmd](diagrams/foundation/29-composite-pipeline-workflow.mmd)     |
| Provider Adapters       | 7 external API adapters plus the `uniprot_idmapping` provider seam | [05-provider-adapter-hierarchy.mmd](diagrams/architecture/05-provider-adapter-hierarchy.mmd)     |
| Pipeline Hierarchy      | Pipeline/Transformer inheritance               | [17-pipeline-hierarchy.mmd](diagrams/foundation/17-pipeline-hierarchy.mmd)                       |
| Local Deployment        | ADR-010 local-only runtime architecture        | [12-local-deployment-architecture.mmd](diagrams/foundation/12-local-deployment-architecture.mmd) |

______________________________________________________________________

## Related Documents

- [RULES.md](../00-project/RULES.md) — Project rules (source of truth)
- [00-map.md](../00-project/00-map.md) — Full project navigator
- [glossary.md](../00-project/glossary.md) — Ubiquitous language terminology
- [Reference Index](../04-reference/index.md) — Published reference surfaces
