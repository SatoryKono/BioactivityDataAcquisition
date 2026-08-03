______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-06'

______________________________________________________________________

# Domain Reference

## Purpose

This section is the canonical published reference catalog for the BioETL domain
model.

Use these pages when you need the current semantic catalog of aggregates,
entities, value-object families, domain events, control-plane artifacts, port
families, invariants, and workflow state-machine semantics.

## Boundary

- Use [Domain Layer](../../02-architecture/01-domain-layer.md) for architecture
  rationale, layer boundaries, and DDD positioning.
- Use this reference section for the current published semantic catalog of live
  domain surfaces.
- Use `src/bioetl/domain/README.md` as a code-navigation package map only. It
  is not the canonical published operator/reference surface.
- Use [API Reference](../api/index.md) when you need module-level or
  symbol-level API lookup instead of a semantic catalog.

## Source Of Truth

- Domain code: `src/bioetl/domain/`
- Domain workflow runtime: `src/bioetl/domain/workflow/`
- Control-plane state owners: `src/bioetl/domain/control_plane/`
- Domain ports: `src/bioetl/domain/ports/`
- Aggregate tests and invariants: `tests/unit/domain/**`,
  `tests/architecture/**`

## Catalog

| Surface | Purpose | Entry point |
| --- | --- | --- |
| Aggregates | Aggregate roots, lifecycle boundaries, child objects, and invariants | [aggregates.md](aggregates.md) |
| Entities | Provider DTOs and domain entity record models (non-aggregate) | [entities.md](entities.md) |
| Value Objects | Immutable domain primitives and typed semantic families | [value-objects.md](value-objects.md) |
| Events | Aggregate coordination events and observability event constants | [events.md](events.md) |
| Control Plane | Run manifest, run ledger, workflow control-plane, contract-registry, and reproducibility domain surfaces | [control-plane.md](control-plane.md) |
| Ports | Transport-neutral contracts for runtime, storage, observability, quality, and control plane | [ports.md](ports.md) |
| Contexts | `PipelineContext`, `PipelineRunContext`, and the shared context helper modules | [contexts.md](contexts.md) |
| Invariants | Cross-cutting domain, workflow, replay, and schema-boundary rules | [invariants.md](invariants.md) |
| Aggregate State Machines | Formal lifecycle transitions for `Batch`, `PipelineRun`, and `QuarantineEntry` | [aggregate-state-machines.md](aggregate-state-machines.md) |
| Workflow State Machine | Formal workflow lifecycle and artifact ownership model | [workflow-state-machine.md](workflow-state-machine.md) |
| Symbol Traceability | Public aggregate, value-object, and control-plane symbols mapped to roles, invariants, events, and tests | [symbol-invariant-traceability.md](symbol-invariant-traceability.md) |

## Reading Order

1. Start with [aggregates.md](aggregates.md) for lifecycle owners.
2. Use [entities.md](entities.md) for provider record models and DTO surfaces.
3. Continue with [invariants.md](invariants.md) for rules that must stay true
   across code, contracts, and runbooks.
4. Use [control-plane.md](control-plane.md) for immutable provenance,
   append-only ledger, workflow control-plane, and reproducibility surfaces.
5. Use [aggregate-state-machines.md](aggregate-state-machines.md) for
   transition-level aggregate lifecycle semantics.
6. Use [workflow-state-machine.md](workflow-state-machine.md) for formal
   workflow/control-plane semantics.
7. Use [contexts.md](contexts.md) when tracing runtime context ownership,
   deterministic time seams, or replay/control-plane anchors.
8. Use [ports.md](ports.md) and [events.md](events.md) when wiring or auditing
   adapters, observability, or runtime orchestration.
