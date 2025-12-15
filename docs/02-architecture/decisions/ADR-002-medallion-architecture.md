# ADR-002: Why Medallion Architecture?

*   **Status**: Accepted
*   **Date**: 2025-05-20 (Implicitly from RULES.md v2.0)
*   **Context**: The project needs a structured and scalable approach to manage data pipelines, from raw ingestion to analysis-ready aggregates.

## The Decision

We have adopted the **Medallion Architecture**, which organizes data into three distinct quality layers: **Bronze**, **Silver**, and **Gold**.

This decision is codified in Section 2.1 of `RULES.md`.

## Justification

The Medallion Architecture provides a clear and logical separation of concerns, which directly addresses several key project requirements:

1.  **Traceability and Replayability**:
    *   The **Bronze** layer serves as an immutable, append-only archive of raw source data. This allows us to re-run any pipeline from scratch (`--full-rebuild`) in case of bugs or changes in business logic, without having to re-fetch data from source APIs. This is critical for disaster recovery and auditing.

2.  **Improved Data Quality**:
    *   Each layer represents a progressive improvement in data quality.
    *   **Bronze**: Raw, as-is data.
    *   **Silver**: Normalized, cleaned, and enriched data (e.g., standardized units, validated schemas).
    *   **Gold**: Business-level aggregates and views, optimized for specific use cases (e.g., analytics, machine learning).
    *   This structure isolates data quality issues. A problem in a Gold table can be fixed by reprocessing from the Silver layer, which is much faster than going back to the source.

3.  **Decoupling of Concerns**:
    *   **Ingestion vs. Transformation**: Ingestion pipelines are only responsible for landing data in Bronze. Transformation pipelines work from Bronze to Silver. This decoupling means a change in a Gold table's business logic does not impact the ingestion process.
    *   **Multiple Use Cases**: The Silver layer can serve as a source for many different Gold tables, preventing the duplication of cleaning and normalization logic.

4.  **Security and Governance**:
    *   The layered approach allows for different access controls. For example, a wider audience can be granted access to the public-safe Gold layer, while access to the potentially sensitive Bronze and Silver layers can be more restricted.

## Consequences

*   **Increased Storage Costs**: Storing data in three different forms consumes more storage space. This is mitigated by using efficient storage formats (zstd-compressed JSONL, Delta Lake) and S3 lifecycle policies to archive old Bronze data.
*   **Higher Latency**: The multi-hop process (Bronze -> Silver -> Gold) introduces latency compared to a single, monolithic ETL job. This is an acceptable trade-off for the gains in reliability and maintainability.
*   **Development Overhead**: Requires developers to think in terms of layers and manage pipelines between them. However, this structure also simplifies individual pipeline logic.
