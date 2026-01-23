# CLI Reference

The BioETL command-line interface (CLI) is the primary entry point for interacting with the application. It is built using Python's `argparse` and is accessible via `python -m bioetl.main`.

## Global Flags

These flags can be used with any command.

*   `--log-level <LEVEL>`: Set the logging level.
    *   **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
    *   **Default**: `INFO`
    *   **Environment Variable**: `BIOETL_LOG_LEVEL`

## Commands

### `run`
Executes a data pipeline.

**Usage:**
```bash
python -m bioetl.main run --pipeline <PIPELINE_NAME> [OPTIONS]
```

**Arguments & Flags:**

*   `--pipeline <NAME>` (Required): The name of the pipeline to run. This must correspond to a YAML file in `configs/pipelines/`.
*   `--limit <N>`: Process only the first `N` records from the source. Useful for testing and debugging.
*   `--full-rebuild`: Force a full data load, ignoring any existing watermarks or checkpoints.
*   `--resume`: Resume a pipeline from a saved checkpoint if a previous run was interrupted.
*   `--start-date <YYYY-MM-DD>`: For backfills, specifies the start of the date range to process.
*   `--end-date <YYYY-MM-DD>`: For backfills, specifies the end of the date range to process.
*   `--wait-for-lock <SECONDS>`: When acquiring an exclusive lock, wait for the specified duration instead of failing immediately.

**Examples:**
```bash
# Run the full ChEMBL activity pipeline
python -m bioetl.main run --pipeline chembl_activity

# Test the UniProt pipeline with only 10 records
python -m bioetl.main run --pipeline uniprot_trembl --limit 10

# Rebuild the PubChem compound data from scratch
python -m bioetl.main run --pipeline pubchem_compound --full-rebuild
```

---

### `list`
Lists all available pipelines.

**Usage:**
```bash
python -m bioetl.main list
```

**Description:**
This command scans the `configs/pipelines/` directory and prints a list of all valid pipeline configuration files, which correspond to the names you can pass to the `run` command.

---

### `release-lock`
Manually releases a stale lock for a given pipeline.

**Usage:**
```bash
python -m bioetl.main release-lock --pipeline <PIPELINE_NAME>
```

**Description:**
Use this command with caution. If a pipeline crashes and fails to release its distributed lock, subsequent runs will fail. This command allows a developer to manually clear the lock from Redis.

**Warning**: Only use this if you are certain that no other instance of the pipeline is currently running.

---

### `quarantine-inspect`
(Coming Soon) Dumps a sample of records from the quarantine for a specific pipeline to the console for analysis.

### `quarantine-replay`
(Coming Soon) Re-processes records from the quarantine that match a specific filter.
