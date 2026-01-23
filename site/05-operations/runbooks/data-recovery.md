# Data Recovery Runbook

This runbook provides procedures for recovering data in case of corruption, accidental deletion, or other disaster scenarios.

**RPO (Recovery Point Objective):** 24 hours
**RTO (Recovery Time Objective):** 4 hours

## Scenario 1: Silver/Gold Data Corruption

*   **Symptom**: Data in Silver or Gold layers is found to be incorrect, incomplete, or corrupted. The Bronze layer is intact.
*   **Cause**: A bug in a transformation, incorrect business logic, or a failed merge operation.
*   **Recovery Steps**:
    1.  **Stop Pipelines**: Halt all pipelines that write to the affected tables to prevent further corruption.
    2.  **Identify Blast Radius**: Determine which tables and partitions are affected.
    3.  **Use Time Travel (Delta Lake)**: If the issue was recent (within 7 days), use Delta Lake's time travel to revert the table to a previous version or timestamp.
        ```sql
        -- Example: Revert a table to a specific version
        RESTORE TABLE schema.table_name TO VERSION AS OF <version_number>;

        -- Example: Revert to a timestamp
        RESTORE TABLE schema.table_name TO TIMESTAMP AS OF 'YYYY-MM-DD HH:MI:SS';
        ```
    4.  **Full Rebuild from Bronze**: If time travel is not an option, the most reliable method is to rebuild from the Bronze layer.
        *   Delete the corrupted data from the Silver/Gold tables.
        *   Run the pipeline with the `--full-rebuild` flag. This will re-process all data from Bronze.
        ```bash
        python -m bioetl.main run --pipeline <pipeline_name> --full-rebuild
        ```

## Scenario 2: Bronze Data Loss or Corruption

*   **Symptom**: Files in the Bronze layer (S3/MinIO) are deleted or corrupted.
*   **Cause**: Accidental deletion, S3 bucket misconfiguration, or infrastructure failure.
*   **Recovery Steps**:
    1.  **Stop All Pipelines**: Immediately halt all data ingestion.
    2.  **Restore S3 Bucket**:
        *   Use your cloud provider's Point-in-Time Restore (PITR) feature for the S3 bucket.
        *   Restore the bucket to a state just before the incident occurred.
    3.  **Rebuild Silver/Gold**: Once the Bronze layer is restored, follow the steps in **Scenario 1** to rebuild the downstream layers. A full rebuild is mandatory.

## Scenario 3: Lost Checkpoint

*   **Symptom**: A pipeline was interrupted, but the checkpoint file was lost or corrupted. The pipeline warns about a "Stale checkpoint" on restart.
*   **Cause**: S3 write failure, race condition, or manual error.
*   **Recovery Steps**:
    1.  **Option A (Safest)**: Ignore the checkpoint and re-process a slightly larger window of data.
        ```bash
        python -m bioetl.main run --pipeline <pipeline_name> --ignore-checkpoint
        ```
        *   **Impact**: This may create duplicate records in the Bronze layer, but the merge/upsert logic in the Silver layer will handle deduplication, ensuring correctness.
    2.  **Option B (Advanced)**: Manually determine the last successfully processed record ID or timestamp from the Silver table and create a new checkpoint file. This is faster but more error-prone.
