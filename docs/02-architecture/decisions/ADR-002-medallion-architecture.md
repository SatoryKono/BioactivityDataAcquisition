______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-002: Why Medallion Architecture?

**Date:** 2025-05-20
**Status:** Accepted
**Last updated:** 2026-01-02
**Decision makers:** @BioETL-Team

## Context

The project needs a structured and scalable approach to manage data pipelines, from raw ingestion to analysis-ready aggregates.

## Decision

We have adopted the **Medallion Architecture**, which organizes data into three distinct quality layers: **Bronze**, **Silver**, and **Gold**.

This decision is codified in Section 2.1 of `RULES.md`.

## Justification

The Medallion Architecture provides a clear and logical separation of concerns, which directly addresses several key project requirements:

1. **Traceability and Replayability**:

   - The **Bronze** layer serves as an immutable, append-only archive of raw source data. This allows us to re-run any pipeline from scratch (`--full-rebuild`) in case of bugs or changes in business logic, without having to re-fetch data from source APIs. This is critical for disaster recovery and auditing.

1. **Improved Data Quality**:

   - Each layer represents a progressive improvement in data quality.
   - **Bronze**: Raw, as-is data.
   - **Silver**: Normalized, cleaned, and enriched data (e.g., standardized units, validated schemas).
   - **Gold**: Business-level aggregates and views, optimized for specific use cases (e.g., analytics, machine learning).
   - This structure isolates data quality issues. A problem in a Gold table can be fixed by reprocessing from the Silver layer, which is much faster than going back to the source.

1. **Decoupling of Concerns**:

   - **Ingestion vs. Transformation**: Ingestion pipelines are only responsible for landing data in Bronze. Transformation pipelines work from Bronze to Silver. This decoupling means a change in a Gold table's business logic does not impact the ingestion process.
   - **Multiple Use Cases**: The Silver layer can serve as a source for many different Gold tables, preventing the duplication of cleaning and normalization logic.

1. **Security and Governance**:

   - The layered approach allows for different access controls. For example, a wider audience can be granted access to the public-safe Gold layer, while access to the potentially sensitive Bronze and Silver layers can be more restricted.

## Consequences

- **Increased Storage Costs**: Storing data in three different forms consumes more storage space. This is mitigated by using efficient storage formats (zstd-compressed JSONL, Delta Lake) and a local archive policy for old Bronze data.
- **Higher Latency**: The multi-hop process (Bronze -> Silver -> Gold) introduces latency compared to a single, monolithic ETL job. This is an acceptable trade-off for the gains in reliability and maintainability.
- **Development Overhead**: Requires developers to think in terms of layers and manage pipelines between them. However, this structure also simplifies individual pipeline logic.

## References

- [ADR-001](ADR-001-delta-lake-vs-parquet.md): Delta Lake vs Parquet — storage format choice for Silver/Gold layers (Updated: 2025-05-20)
- [ADR-010](ADR-010-local-only-deployment.md): Local-Only Deployment — simplifies deployment while preserving Medallion architecture (Updated: 2025-12-23)
- [ADR-011](ADR-011-remove-watermark-mechanism.md): Remove Watermark — simplifies load strategy within Medallion (Updated: 2025-12-23)
- [ADR-012](ADR-012-storage-clear-contract-and-run-id.md): Storage Clear Contract — Medallion invariants for destructive operations (Updated: 2025-12-25)
- [ADR-018](ADR-018-gold-strict-validation.md): Gold Strict Validation — quality guarantees for Gold layer (Updated: 2025-12-26)

## Compliance

| Control      | Requirement                                                                | Status | Evidence                             |
| ------------ | -------------------------------------------------------------------------- | ------ | ------------------------------------ |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-002-medallion-architecture.md`  |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                           |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                     |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria` |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                         |

## Rollout

- Rollout steps MUST be sequenced before broad adoption.
- Documentation, configuration, and test surfaces SHOULD be updated in the same change set when the decision is implemented.
- Breaking or migration-sensitive adoption SHOULD include an explicit transition window.

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [ ] The decision is documented with current status, date, and owner metadata.
- [ ] The implementation path or adoption boundary is testable and linked from the ADR.
- [ ] Supersession or migration impact is documented when the decision changes an earlier posture.
- [ ] Related docs, contracts, and operational guidance are aligned with this ADR.
