# Running Pipelines

## Prerequisites

1. Virtual environment activated:
   ```bash
   # Linux/macOS
   source .venv/bin/activate

   # Windows
   .venv\Scripts\activate
   ```

2. Environment configured (`.env` file or environment variables)

3. Infrastructure running (for production):
   ```bash
   make docker-up
   ```

## Basic Usage

### List Available Pipelines

```bash
python -m bioetl.main list
```

### Run a Pipeline

```bash
# Incremental run (default)
python -m bioetl.main run --pipeline chembl_activity

# With logging level
python -m bioetl.main run --pipeline chembl_activity --log-level DEBUG
```

## Run Types

| Type | Flag | Description |
|------|------|-------------|
| **Incremental** | (default) | Process new records since last run |
| **Backfill** | `--start-date`, `--end-date` | Process specific date range |
| **Full Rebuild** | `--full-rebuild` | Reload all data from scratch |

### Incremental Run

```bash
python -m bioetl.main run --pipeline chembl_activity
```

### Backfill

```bash
python -m bioetl.main run --pipeline chembl_activity \
    --start-date 2024-01-01 \
    --end-date 2024-12-31
```

### Full Rebuild

```bash
python -m bioetl.main run --pipeline chembl_activity --full-rebuild
```

## Testing & Development

### Limit Records

For testing, limit the number of records processed:

```bash
python -m bioetl.main run --pipeline chembl_activity --limit 100
```

### Resume Interrupted Run

If a pipeline was interrupted, resume from checkpoint:

```bash
python -m bioetl.main run --pipeline chembl_activity --resume
```

## Lock Management

Pipelines use distributed locks to prevent concurrent writes.

### Wait for Lock

If another instance is running, wait instead of failing:

```bash
python -m bioetl.main run --pipeline chembl_activity --wait-for-lock 300
```

### Release Stale Lock

If a pipeline crashed and left a lock:

```bash
python -m bioetl.main release-lock --pipeline chembl_activity
```

**Warning**: Only use if you're certain no instance is running.

## Monitoring

### Log Levels

Set via flag or environment variable:

```bash
# Via flag
python -m bioetl.main run --pipeline chembl_activity --log-level DEBUG

# Via environment
export BIOETL_LOG_LEVEL=DEBUG
python -m bioetl.main run --pipeline chembl_activity
```

| Level | Use Case |
|-------|----------|
| `DEBUG` | Development, troubleshooting |
| `INFO` | Production (default) |
| `WARNING` | Alerts only |
| `ERROR` | Errors only |

### Pipeline Output

Pipelines write data to:

| Layer | Path Pattern | Format |
|-------|--------------|--------|
| Bronze | `bronze/{version}/{provider}/{entity}/{date}/` | JSONL + zstd |
| Silver | `silver/{provider}/{entity}/` | Delta Lake |
| Gold | `gold/{entity}/` | Delta Lake / Parquet |

## Common Issues

| Issue | Solution |
|-------|----------|
| Lock acquisition failed | Wait or release stale lock |
| Rate limit (429) | Automatic retry with backoff |
| Schema drift detected | Check logs, review new fields |
| Checkpoint not found | Run without `--resume` |

## See Also

- [CLI Reference](../04-reference/cli.md) - Full command documentation
- [Troubleshooting](troubleshooting.md) - Common problems and solutions
- [Pipeline Configuration](../04-reference/pipelines/chembl_activity.md) - YAML config format
