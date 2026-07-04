______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-001: Why Delta Lake over Raw Parquet?

**Date:** 2025-05-20
**Status:** Accepted
**Last updated:** 2026-01-02
**Decision makers:** @BioETL-Team

## Context

The project requires a reliable, high-performance storage format for the Silver (normalized) and Gold (aggregated) layers of the data warehouse. The primary candidates were raw Apache Parquet and Delta Lake.

## Decision

We have chosen **Delta Lake** as the mandatory format for the Silver and Gold layers. Raw Parquet **MUST NOT** be used for these layers.

This decision is codified in Section 2.1 of `RULES.md`.

## Justification

While Parquet is an excellent columnar storage format, it lacks critical features for building a robust data warehouse. Delta Lake is a storage layer built on top of Parquet that provides these missing features:

1. **ACID Transactions**: Delta Lake brings atomicity, consistency, isolation, and durability to data lake operations. This is crucial for `MERGE` (upsert) operations, which are the primary mechanism for loading data into the Silver layer. With raw Parquet, handling updates and deletes is complex and prone to race conditions.

1. **Schema Enforcement & Evolution**:

   - **Enforcement**: Delta Lake prevents data with incorrect schemas from being written, which protects the data warehouse from corruption.
   - **Evolution**: It provides clear mechanisms for evolving the schema over time (e.g., adding new columns), which is essential for a long-running project.

1. **Time Travel (Data Versioning)**: The ability to query data "as of" a specific timestamp or version is an invaluable tool for:

   - **Auditing**: Understanding how data has changed.
   - **Debugging**: Pinpointing when bad data was introduced.
   - **Rollbacks**: Quickly reverting the state of a table in case of a faulty data load.

1. **Unified Batch and Streaming**: Delta Lake is designed to be a single source of truth for both batch and streaming workloads, which provides future-proofing for the architecture.

1. **Performance Optimizations**: Features like `OPTIMIZE` (file compaction), `Z-ORDER` (data skipping), and caching significantly improve query performance compared to a raw collection of Parquet files, which can suffer from the "small files problem".

## Consequences

- **Increased Dependency**: The project now has a hard dependency on the `delta-rs` library.
- **Operational Overhead**: The database requires regular maintenance (`VACUUM`, `OPTIMIZE`). This is enforced as a weekly job in `RULES.md`.
- **Vendor Lock-in**: While Delta Lake is an open format, it is most heavily supported by Databricks. However, the growing ecosystem and open-source Rust core (`delta-rs`) mitigate this risk.

## References

- [ADR-002](ADR-002-medallion-architecture.md): Medallion Architecture — uses Delta Lake for Silver and Gold layers (Updated: 2025-05-20)
- [ADR-012](ADR-012-storage-clear-contract-and-run-id.md): Storage Clear Contract — defines clear/cleanup operations for Delta tables (Updated: 2025-12-25)
- [ADR-018](ADR-018-gold-strict-validation.md): Gold Strict Validation — schema validation for Gold layer Delta tables (Updated: 2025-12-26)

## Compliance

| Control      | Requirement                                                                | Status | Evidence                             |
| ------------ | -------------------------------------------------------------------------- | ------ | ------------------------------------ |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-001-delta-lake-vs-parquet.md`   |
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
