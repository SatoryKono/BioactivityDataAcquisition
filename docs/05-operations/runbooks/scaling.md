# Scaling and Performance Tuning

This document provides guidance on scaling the BioETL platform to handle larger data volumes and improve performance.

## Horizontal Scaling: Adding More Workers

The BioETL system is designed to be stateless, allowing for horizontal scaling by simply adding more worker nodes (e.g., Docker containers, Kubernetes pods).

*   **Strategy**: Deploy multiple instances of the BioETL application.
*   **Concurrency**: The distributed locking mechanism (`lock:{provider}_{entity}`) ensures that only one worker can process a specific pipeline at any given time, preventing race conditions.
*   **Benefit**: Allows multiple different pipelines to run in parallel across the worker pool (e.g., `worker-1` runs `chembl_activity` while `worker-2` runs `pubchem_compound`).

## Vertical Scaling: Increasing Resources

If a single pipeline run is slow, consider increasing the resources available to the worker.

*   **CPU**: More cores can help with CPU-bound tasks like data transformation and validation (e.g., using Polars).
*   **Memory**: Larger memory is crucial for handling large dataframes. Insufficient memory can lead to out-of-memory (OOM) errors or slow disk swapping.

## Performance Tuning

### 1. Adjusting Batch Sizes

*   **Symptom**: High memory usage or slow processing of individual batches.
*   **Tuning**: The batch size is often controlled by the source adapter (e.g., how many records are fetched per API call).
*   **Action**:
    *   Reduce the batch size in the pipeline's configuration or adapter code. This will lower memory pressure but may increase the total number of I/O operations.

### 2. Tuning Delta Lake

*   **Symptom**: Slow `merge` operations on large Delta tables.
*   **Tuning**: Delta Lake performance depends heavily on file sizes and table maintenance.
*   **Actions**:
    *   **`OPTIMIZE`**: Periodically run `OPTIMIZE` to compact small files into larger ones. This significantly speeds up read performance.
        ```sql
        OPTIMIZE schema.table_name;
        ```
    *   **`Z-ORDER`**: For frequently filtered columns, use `Z-ORDER` to co-locate related data.
        ```sql
        OPTIMIZE schema.table_name ZORDER BY (filter_column);
        ```
    *   **`VACUUM`**: Regularly run `VACUUM` to remove old, unreferenced data files and reduce storage costs. This is a mandatory weekly operation as per `RULES.md`.

### 3. Partitioning Strategy

*   **Symptom**: Queries on the data warehouse are slow.
*   **Tuning**: Review the partitioning strategy for your Silver and Gold tables.
*   **Action**:
    *   Ensure you are partitioning on low-cardinality fields that are frequently used in `WHERE` clauses (e.g., `year`, `month`, `entity_type`).
    *   **Avoid over-partitioning**: Do not partition on high-cardinality fields like UUIDs or hashes. This creates a "small files" problem and slows down the metadata log. Refer to the partitioning limits in `RULES.md`.
