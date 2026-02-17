# ADR-035: Target Schema Architecture 2026

- **Status**: Accepted
- **Date**: 2026-02-17
- **Related**: ADR-002, ADR-014, ADR-018, ADR-034

## Context

By 2026, BioETL requires a single target-state schema governance model that aligns:

- Medallion contracts (Bronze tolerant, Silver controlled, Gold strict),
- SCD Type 2 historical guarantees,
- deterministic hashing and replay behavior,
- and explicit release gating for schema drift.

Existing controls are distributed across multiple rules and ADRs. This ADR formalizes the target architecture and implementation roadmap.

## Decision

BioETL adopts a **Target Schema Architecture 2026** with:

1. Unified schema lifecycle governance gate (`blocking` vs `warning`).
1. Explicit contract versioning policy (MAJOR/MINOR/PATCH per entity contract).
1. Canonical PK/content-hash separation and partition policy.
1. JSON typing standard used by validation, hashing, and schema diffs.
1. Mandatory SCD2 decision matrix for Gold model evolution.

## Roadmap (3 phases)

### Phase 1 — Foundation (Q1 2026)

- Publish `Schema-Governance.md` as normative architecture reference.
- Add governance gate outputs into CI artifact set.
- Standardize change classification (`blocking`, `warning`) in docs and release checklist.

### Phase 2 — Enforcement (Q2 2026)

- Enforce contract semantic versioning in schema change pipeline.
- Add automated drift classifier with deterministic severity mapping.
- Add mandatory SCD2 decision checks for Gold-breaking changes.

### Phase 3 — Optimization (Q3 2026)

- Add trend monitoring for drift volume and warning debt.
- Tune partition strategy with observed workload patterns.
- Automate migration plan generation for MAJOR version changes.

## Impact Matrix

| Area                 | Positive impact                                                       | Cost / tradeoff                                        |
| -------------------- | --------------------------------------------------------------------- | ------------------------------------------------------ |
| Data Reliability     | Lower risk of silent schema breakages in Gold                         | More pre-release checks and slower approval path       |
| Operability          | Clear `blocking`/`warning` semantics for on-call and release managers | Requires team alignment on severity taxonomy           |
| Performance          | Better partition discipline reduces metadata overhead                 | May require repartition migrations for existing tables |
| Developer Experience | Predictable contract evolution path and fewer ad-hoc reviews          | Additional documentation and versioning duties per PR  |
| Governance           | Traceable and auditable schema decisions                              | More ADR/update overhead for MAJOR changes             |

## Risk Assessment

| Risk                                             | Probability | Impact | Mitigation                                                     |
| ------------------------------------------------ | ----------- | ------ | -------------------------------------------------------------- |
| Over-classification as `blocking` slows delivery | Medium      | Medium | Start with conservative warning defaults and calibrate monthly |
| Inconsistent version bump decisions across teams | Medium      | High   | Provide versioning checklist and CI validation hooks           |
| Drift alert fatigue from additive changes        | High        | Medium | Batch warning alerts and enforce warning debt SLA              |
| Migration complexity for legacy schemas          | Medium      | High   | Phase rollout by provider/entity and keep rollback plans       |
| Documentation drift from implementation          | Medium      | Medium | Add docs sync check in release gate                            |

## Consequences

### Positive

- Target-state schema governance becomes explicit and auditable.
- Gold layer evolution receives uniform SCD2 and contract controls.
- Architecture audit and RULES now share a single schema target narrative.

### Negative

- Governance workflow introduces additional process overhead.
- Initial rollout may require refactoring of historical schema metadata.

## Related ADRs

- [ADR-002](ADR-002-medallion-architecture.md): Medallion architecture baseline.
- [ADR-014](ADR-014-deterministic-writes.md): Deterministic behaviors for replay/hash logic.
- [ADR-018](ADR-018-gold-strict-validation.md): Strict Gold contract enforcement.
- [ADR-034](ADR-034-schema-domain-pairs.md): Schema/domain split and compatibility constraints.
