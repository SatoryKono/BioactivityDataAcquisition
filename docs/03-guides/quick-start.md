# How to Run Pipelines

This guide covers the common ways to execute data pipelines using the BioETL CLI.

## Basic Execution

The primary command for running a pipeline is `bioetl.main run`. You must specify which pipeline to run using the `--pipeline` flag.

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the ChEMBL activity pipeline
python -m bioetl.main run --pipeline chembl_activity
```

This will run the pipeline defined in `configs/pipelines/chembl_activity.yaml`.

## Common Flags

*   `--limit <N>`: Process only the first `N` records. Ideal for testing.
    ```bash
    python -m bioetl.main run --pipeline chembl_activity --limit 500
    ```

*   `--full-rebuild`: Force a full load, ignoring any saved watermarks or checkpoints.
    ```bash
    python -m bioetl.main run --pipeline chembl_activity --full-rebuild
    ```

*   `--resume`: Resume from a previously saved checkpoint (see Graceful Shutdown in `RULES.md`).
    ```bash
    python -m bioetl.main run --pipeline chembl_activity --resume
    ```

## Load Strategies

The pipeline's behavior depends on the `load_strategy` defined in its YAML configuration.

### Incremental Load
This is the default for most pipelines. The pipeline fetches only new or updated records since the last successful run. The `watermark_field` (e.g., `updated_at`) is used to track progress.

### Full Load
The pipeline fetches all available data from the source. This is useful for initial data loading or periodic consistency checks. You can force a full load with `--full-rebuild`.

## Backfill and Replay

To process data for a specific historical period, you can use flags to override the default behavior.

```bash
# Example: Backfill ChEMBL data for a specific date range
python -m bioetl.main run --pipeline chembl_activity \
    --start-date 2023-01-01 \
    --end-date 2023-01-31
```

**Note**: Backfill operations use an exclusive lock to prevent conflicts with regular incremental runs.

## Viewing Available Pipelines

To see a list of all configured pipelines, you can use the `list` command:

```bash
python -m bioetl.main list
```
This will output a list of pipeline names found in the `configs/pipelines/` directory.
