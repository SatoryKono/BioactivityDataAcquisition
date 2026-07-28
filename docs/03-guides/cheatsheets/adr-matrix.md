______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# ADR Decision Matrix

Quick index of accepted architecture decisions and their operational impact.

**Issue:** #6538 · **Full texts:** [docs/02-architecture/decisions/](../../02-architecture/decisions/) · **Registry:** [adr-registry](../../02-architecture/adr-registry.md)

## Table of contents

- [By domain](#by-domain)
- [Quick reference table](#quick-reference-table)
- [Impact dimensions](#impact-dimensions)
- [Interdependencies](#interdependencies)

## By domain

| Domain | ADRs |
| --- | --- |
| Deployment & operations | ADR-010 Local-Only, ADR-003 In-memory locking, ADR-008 Graceful shutdown, ADR-013 Async storage cleanup |
| Data / medallion | ADR-001 Delta vs Parquet, ADR-002 Medallion, ADR-014 Deterministic writes, ADR-018 Gold strict validation, ADR-012 Clear contract |
| Pipeline architecture | ADR-015 Services lifecycle, ADR-020 BasePipeline decomposition, ADR-026 Composite, ADR-031 Loading strategy, ADR-047 Workflow control plane |
| Configuration | ADR-025 Pipeline config unification, ADR-027 DQ externalization, ADR-028 Filter externalization, ADR-039 Entity config format, ADR-029 Output metadata unification |
| Schema & contracts | ADR-034 Schema pairs, ADR-036 Gold contract versioning, ADR-037 Canonical schema generation, ADR-038 Enums, ADR-045 DQ contracts, ADR-048 Schema boundary, ADR-050 Filter boundary |
| Observability | ADR-006 Logger/metrics ports, ADR-017 Observability architecture, ADR-019 Port enforcement, ADR-022 Tracing noop |
| HTTP & providers | ADR-007 Circuit breaker, ADR-009 Paginated fetcher, ADR-032 Unified HTTP client, ADR-030/033 Publication |
| Control plane / replay | ADR-044 Run manifest & ledger, ADR-046 Checkpoint vs ledger resume, ADR-051 Quarantine aggregate |
| Quality & governance | ADR-040 Diagram governance, ADR-042 Testing matrix, ADR-043 Docs knowledge, ADR-049 LOC policy |
| Domain / composition | ADR-005 Composition separation, ADR-021 DDD aggregates, ADR-052 Infrastructure config public API |

## Quick reference table

| ADR | Topic | Status | Key constraint | Migration / action |
| --- | --- | --- | --- | --- |
| [ADR-001](../../02-architecture/decisions/ADR-001-delta-lake-vs-parquet.md) | Delta Lake vs Parquet | Accepted | Silver/Gold Delta only | Prefer Delta writers |
| [ADR-002](../../02-architecture/decisions/ADR-002-medallion-architecture.md) | Medallion | Accepted | Bronze→Silver→Gold | Layer ops via medallion services |
| [ADR-005](../../02-architecture/decisions/ADR-005-composition-layer-separation.md) | Composition DI | Accepted | DI only in composition | No factories in application |
| [ADR-010](../../02-architecture/decisions/ADR-010-local-only-deployment.md) | Local-only | Accepted | No Docker/Redis required for core | Optional monitoring only |
| [ADR-014](../../02-architecture/decisions/ADR-014-deterministic-writes.md) | Deterministic writes | Accepted | Stable Silver order/keys | Add sort/keys to sinks |
| [ADR-017](../../02-architecture/decisions/ADR-017-observability-architecture.md) | Observability | Accepted | Ports for logs/metrics/traces | Wire via composition |
| [ADR-018](../../02-architecture/decisions/ADR-018-gold-strict-validation.md) | Gold strict | Accepted | Fail-closed Gold | Do not swallow SchemaError |
| [ADR-025](../../02-architecture/decisions/ADR-025-pipeline-config-unification.md) | Config unification | Accepted | Unified entity identity fields | Migrate legacy configs |
| [ADR-026](../../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md) | Composite | Accepted | seed/enrichers/merge | Use `configs/composites/` |
| [ADR-027](../../02-architecture/decisions/ADR-027-dq-rules-externalization.md) | DQ YAML | Accepted | Rules in hierarchy | No hardcoded DQ |
| [ADR-028](../../02-architecture/decisions/ADR-028-filter-rules-externalization.md) | Filters YAML | Accepted | Externalized filters | See ADR-050 boundary |
| [ADR-032](../../02-architecture/decisions/ADR-032-unified-http-client.md) | Unified HTTP | Accepted | Shared client/resilience | Adapters use unified client |
| [ADR-037](../../02-architecture/decisions/ADR-037-canonical-schema-generation.md) | Schema generation | Accepted | Generated artifacts from SSOT | Refresh generated schemas |
| [ADR-038](../../02-architecture/decisions/ADR-038-enum-externalization.md) | Enums in YAML | Accepted | Controlled vocab external | Update YAML enums |
| [ADR-040](../../02-architecture/decisions/ADR-040-diagram-governance.md) | Diagrams | Accepted | Mermaid + lint gates | `python -m scripts.diagrams lint` |
| [ADR-044](../../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md) | Control plane | Accepted | Manifest + ledger SSOT | Use run-manifest CLI |
| [ADR-045](../../02-architecture/decisions/ADR-045-dq-contract-system.md) | DQ contracts | Accepted | Contract registry | Keep contracts in sync |
| [ADR-046](../../02-architecture/decisions/ADR-046-checkpoint-vs-ledger-resume.md) | Resume model | Accepted | Checkpoint ≠ ledger | Choose correct resume path |
| [ADR-051](../../02-architecture/decisions/ADR-051-quarantine-entry-aggregate-surface.md) | Quarantine aggregate | Accepted | Wide constructor intentional | Use bag/waiver, don’t flatten |
| [ADR-052](../../02-architecture/decisions/ADR-052-infrastructure-config-package-root-public-api.md) | Config package root | Accepted | Public API root permanent | Prefer public package imports |

Statuses: treat listed ADRs as **Accepted** unless the individual ADR file marks otherwise. Supersession examples (e.g. historical ADR-008 notes) live in the ADR body.

## Impact dimensions

When applying an ADR change, check:

| Dimension | Questions |
| --- | --- |
| **Scope** | Code layers, configs, CLI, dashboards affected? |
| **Constraints** | What is now forbidden or mandatory? |
| **Migration** | Config/schema/code steps for existing pipelines? |
| **Testing** | Architecture tests, contract tests, VCR, DQ? |
| **Monitoring** | Metrics, alerts, control-plane claims? |

## Interdependencies

```text
ADR-002 Medallion
  ├─ ADR-001 Delta storage
  ├─ ADR-014 Deterministic Silver/Gold writes
  └─ ADR-018 Gold strict validation

ADR-025 Config unification
  ├─ ADR-027 DQ YAML
  ├─ ADR-028 Filters YAML
  └─ ADR-039 Entity format

ADR-026 Composite
  └─ depends on entity pipelines (ADR-025) + merge policy domain

ADR-044/046/047 Control plane
  └─ observability ports ADR-006/017; resume semantics ADR-046

ADR-040 Diagrams
  └─ documents architecture constrained by ADR-005/010/002/...
```

**Conflicts:** resolve via ADR text + [NORMATIVE_SOURCES.md](../../00-project/NORMATIVE_SOURCES.md); docs guides MUST NOT invent policy.

## See also

- [decisions/README.md](../../02-architecture/decisions/README.md)
- [Pipeline Config Cheatsheet](pipeline-config.md)
- [Architecture diagrams (ADR-040 map)](../../02-architecture/diagrams/adr-040-compliance-map.md)
