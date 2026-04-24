# ADR Registry

*Generated: 2026-04-24 | Last Updated: 2026-04-24 | Total ADRs: 45*

## Status Summary

- **Accepted**: 40 ADRs
- **Superseded**: 1 ADR (ADR-008)
- **Partially Superseded**: 1 ADR (ADR-025)
- **Implemented**: 2 ADRs (ADR-020, ADR-021)
- **Revised**: 1 ADR (ADR-003)

## Complete ADR Registry

| ADR ID | Status | Date |
|--------|--------|------|
| ADR-001-delta-lake-vs-parquet | Accepted | 2025-05-20 |
| ADR-002-medallion-architecture | Accepted | 2025-05-20 |
| ADR-003-in-memory-locking-strategy | Accepted (Revised 2025-12-23, see also ADR-010) | 2025-05-20 |
| ADR-004-pydantic-vs-dataclasses | Accepted | 2025-05-20 |
| ADR-005-composition-layer-separation | Accepted | 2025-12-18 |
| ADR-006-logger-metrics-ports | Accepted | 2025-12-18 |
| ADR-007-circuit-breaker-implementation | Accepted | 2025-12-22 |
| ADR-008-graceful-shutdown-strategy | Superseded (signal handlers removed; shutdown handled in canonical CLI domain command modules and application/core/lifecycle/shutdown.py) | 2025-12-22 |
| ADR-009-paginated-fetcher-mixin | Accepted | 2025-12-22 |
| ADR-010-local-only-deployment | Accepted | 2025-12-23 |
| ADR-011-remove-watermark-mechanism | Accepted | 2025-12-23 |
| ADR-012-storage-clear-contract-and-run-id | Accepted | 2025-12-23 |
| ADR-013-async-storage-cleanup | Accepted | 2025-12-24 |
| ADR-014-deterministic-writes | Accepted | 2025-12-24 |
| ADR-015-pipeline-services-lifecycle | Accepted | 2025-12-24 |
| ADR-016-error-handling-strategy | Accepted | 2025-12-26 |
| ADR-017-observability-architecture | Accepted | 2025-12-26 |
| ADR-018-gold-strict-validation | Accepted | 2025-12-26 |
| ADR-019-observability-port-enforcement | Accepted | 2025-12-26 |
| ADR-020-basepipeline-decomposition | Accepted (Implemented 2025-12-16) | 2025-12-16 |
| ADR-021-ddd-aggregates-adoption | Accepted (Implemented 2025-12-29) | 2025-12-29 |
| ADR-022-tracing-noop | Accepted | 2025-12-30 |
| ADR-023-entity-type-patterns | Accepted | 2026-01-06 |
| ADR-024-entity-naming-unification | Accepted | 2026-01-06 |
| ADR-025-pipeline-config-unification | Accepted (partially superseded by ADR-039) | 2026-01-19 |
| ADR-026-composite-pipeline-pattern | Accepted | 2026-01-15 |
| ADR-027-dq-rules-externalization | Accepted | 2026-01-19 |
| ADR-028-filter-rules-externalization | Accepted | 2026-02-09 |
| ADR-029-output-metadata-unification | Accepted | 2026-01-23 |
| ADR-030-publication-pagination-strategy | Accepted | 2026-01-26 |
| ADR-031-loading-strategy-formalization | Accepted | 2026-01-26 |
| ADR-032-unified-http-client | Accepted | 2026-01-28 |
| ADR-033-publication-validation-strategy | Accepted | 2026-02-01 |
| ADR-034-schema-domain-pairs | Accepted | 2026-02-15 |
| ADR-035-json-field-typing-policy | Accepted | 2026-02-17 |
| ADR-036-gold-contract-versioning-policy | Accepted | 2026-02-18 |
| ADR-037-canonical-schema-generation | Accepted | 2026-02-18 |
| ADR-038-enum-externalization | Accepted | 2026-02-16 |
| ADR-039-unified-entity-config-format | Accepted | 2026-02-24 |
| ADR-040-diagram-governance | Accepted | 2026-02-25 |
| ADR-041-naming-policy-skills-agents | Accepted | 2026-03-04 |
| ADR-042-testing-strategy-matrix | Accepted | 2026-03-09 |
| ADR-043-documentation-knowledge-management | Accepted | 2026-03-09 |
| ADR-044-run-manifest-ledger-control-plane | Accepted | 2026-03-24 |
| ADR-045-dq-contract-system | Accepted | 2026-03-26 |

## Status Legend

- **Accepted**: Decision is active and implemented
- **Superseded**: Decision has been replaced by a newer ADR
- **Partially Superseded**: Decision is mostly replaced but some aspects remain
- **Implemented**: Decision has been fully implemented with specific date
- **Revised**: Decision has been updated with references to newer ADRs

## Navigation

- [Return to Project Navigator](../00-project/00-map.md)
- [View Architecture Overview](../02-architecture/00-overview.md)
- [Browse All ADRs](./decisions/)

## Metadata

- **Generated**: 2026-04-24
- **Last Verified**: 2026-04-24
- **ADR Count**: 45
- **Status**: Active
- **Owner**: BioETL Team