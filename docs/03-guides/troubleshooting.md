# Troubleshooting Guide

This guide provides solutions to common problems encountered during development and pipeline execution.

## Docker & Infrastructure

### Error: `Connection refused` for Redis/MinIO/Postgres
*   **Symptom**: The pipeline fails immediately with a connection error.
*   **Cause**: The Docker containers for the infrastructure are not running or are not accessible.
*   **Solution**:
    1.  Ensure Docker Desktop is running.
    2.  Run `make docker-up` to start the containers.
    3.  Verify the containers are running with `docker ps`.
    4.  Check your `.env` file to ensure the hostnames and ports match the Docker Compose configuration (e.g., `BIOETL_REDIS_URL=redis://localhost:6379/0`).

### Error: `Permission Denied` on `./docker-data`
*   **Symptom**: Docker fails to start containers, complaining about file permissions.
*   **Cause**: The `./docker-data` directory may have incorrect ownership, often after system changes or running Docker with different user accounts.
*   **Solution**:
    1.  Stop all running containers: `make docker-down`.
    2.  Completely reset the Docker volumes: `make docker-reset`. This will delete all local data.
    3.  Restart the containers: `make docker-up`.

## Pipeline Execution

### Error: `PipelineNotFoundError: No pipeline named '...'`
*   **Symptom**: The CLI fails with a "pipeline not found" error.
*   **Cause**: The name provided via `--pipeline` does not match any file in the `configs/pipelines/` directory.
*   **Solution**:
    1.  List all available pipelines: `python -m bioetl.main list`.
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
    2.  Inspect the raw data in the Bronze layer (MinIO) to understand the new structure.
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
