# Troubleshooting Guide

This guide provides solutions to common problems encountered during development and pipeline execution.

## Local-only Deployment & Storage

### Reminder: Redis/MinIO are not used in the current mode
*   **Context**: The project runs in local-only mode by design, without Redis or MinIO.
*   **Reference**: See [ADR-010: Local-Only Deployment](../02-architecture/decisions/ADR-010-local-only-deployment.md).

### Error: `FileNotFoundError` or missing local data paths
*   **Symptom**: The pipeline fails when reading or writing local files.
*   **Cause**: The expected directory layout in `data/` does not exist or is misconfigured.
*   **Solution**:
    1.  Confirm the local storage layout described in [Local Storage Layout](local-storage-layout.md).
    2.  Ensure the expected directories under `data/` exist and are writable.
    3.  Re-run the pipeline to recreate missing folders if needed.

## Pipeline Execution

### Error: `PipelineNotFoundError: No pipeline named '...'`
*   **Symptom**: The CLI fails with a "pipeline not found" error.
*   **Cause**: The name provided via `--pipeline` does not match any file in the `configs/pipelines/` directory.
*   **Solution**:
    1.  List all available pipelines: `bioetl config list-pipelines` or `bioetl run-all --list-only`.
    2.  Verify the spelling of the pipeline name.
    3.  Ensure the corresponding YAML file exists in `configs/pipelines/`.

### Error: `LockNotAcquiredError`
*   **Symptom**: The pipeline fails to start, stating it could not acquire a lock.
*   **Cause**: Another instance of the same pipeline is currently running, or a previous run crashed without releasing the lock.
*   **Solution**:
    1.  Check for other running processes of the same pipeline.
    2.  If you are certain no other process is running, the lock may be stale. Manually release it:
        ```bash
        make release-lock PIPELINE=your_pipeline_name
        ```

### Error: `pydantic.ValidationError`
*   **Symptom**: The pipeline fails during the `transform` or `load` stage with a Pydantic validation error.
*   **Cause**: The data returned by the source API has changed, and it no longer matches the Pydantic model defined in `src/bioetl/domain/`.
*   **Solution**:
    1.  Examine the error message to see which field is causing the validation failure.
    2.  Inspect the raw data in the local Bronze layer under `data/` to understand the new structure (see [Local Storage Layout](local-storage-layout.md)).
    3.  Update the Pydantic model in the `src/bioetl/domain/` directory to accommodate the change (e.g., make a field optional, add a new field). This is a **schema drift** event and should be documented.

## Data Quality

### High number of records in Quarantine
*   **Symptom**: The pipeline run summary shows a high percentage of records sent to the quarantine.
*   **Cause**: A non-critical data quality rule is failing for many records.
*   **Solution**:
    1.  Inspect the quarantined records:
        ```bash
        make quarantine-inspect PIPELINE=your_pipeline_name
        ```
    2.  Analyze the `error_code` and `payload` to identify the root cause (e.g., unexpected `null` values, invalid SMILES strings).
    3.  Adjust the data quality rules or the transformation logic in the corresponding adapter.

## See Also

- [Running Pipelines](running-pipelines.md) - CLI commands and options
- [Getting Started](getting-started.md) - Initial setup guide
- [Project Rules](../RULES.md) - Data quality thresholds and error handling
