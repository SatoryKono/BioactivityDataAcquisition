# Interactive Pipeline Debugging Guide

## Overview

BioETL provides an interactive debugger for step-by-step pipeline execution. This allows you to:

- **Pause execution** at specific pipeline stages (preflight, bronze, silver, gold, DQ)
- **Inspect state** including record counts, data quality issues, and sample records
- **Step through** pipeline execution one stage at a time
- **Capture snapshots** of intermediate state for analysis

## Quick Start

```bash
# Run pipeline in interactive debug mode
python -m bioetl debug chembl_molecule \
  --mode interactive \
  --limit 100 \
  --breakpoints after_preflight,after_bronze,after_silver

# Or use logging mode for non-interactive debugging
python -m bioetl debug chembl_molecule \
  --mode log \
  --limit 100
```

## Debug Modes

### Interactive Mode

Interactive mode pauses execution at each enabled breakpoint and prompts for action:

```bash
python -m bioetl debug chembl_molecule \
  --mode interactive \
  --limit 100 \
  --breakpoints after_preflight,after_dq
```

When a breakpoint is hit, you'll see:

```
============================================================
  BREAKPOINT: after_preflight
  Infrastructure validation complete
============================================================
  Stage:        preflight_complete
  Fetched:      0
  Bronze:       0
  Silver:       0
  Gold:         0
  Quarantined:  0

Action [continue/skip_stage/inspect/abort/dump_state] (continue):
```

#### Available Actions

- **`continue`** (default): Continue to next breakpoint
- **`skip_stage`**: Skip the current stage (not yet implemented)
- **`inspect`**: View detailed state (not yet implemented)
- **`abort`**: Abort pipeline execution immediately
- **`dump_state`**: Export current state to file (not yet implemented)

### Logging Mode

Logging mode captures snapshots but never pauses execution. Useful for:

- CI/CD pipelines
- Production debugging
- Automated testing

```bash
python -m bioetl debug chembl_molecule \
  --mode log \
  --limit 1000 \
  --log-level DEBUG
```

All breakpoints are logged to structured logs:

```json
{
  "event": "debug_breakpoint",
  "breakpoint": "after_bronze",
  "stage": "bronze_complete",
  "records_fetched": 1000,
  "records_bronze": 950,
  "records_quarantined": 50
}
```

## Breakpoint Stages

### Available Breakpoints

| Breakpoint          | Triggered After...                      |
|---------------------|-----------------------------------------|
| `after_preflight`   | Infrastructure health validation        |
| `after_bronze`      | Bronze layer writes (raw API data)      |
| `after_silver`      | Silver layer writes (transformed data)  |
| `after_gold`        | Gold layer writes (curated data)        |
| `after_dq`          | Data quality checks complete            |
| `on_error`          | Any error during execution              |
| `on_quarantine`     | Records quarantined due to DQ issues    |

**Note:** Only `after_preflight` and `after_dq` are currently implemented in PipelineRunner. Medallion-level breakpoints (`after_bronze`, `after_silver`, `after_gold`) require BatchExecutor integration (planned).

### Selecting Breakpoints

```bash
# Enable specific breakpoints
python -m bioetl debug chembl_molecule \
  --breakpoints after_preflight,after_dq

# Enable all breakpoints (default in interactive mode)
python -m bioetl debug chembl_molecule \
  --mode interactive
```

## Snapshot Data

Each breakpoint captures a snapshot containing:

```python
PipelineSnapshot(
    stage="after_bronze",              # Stage name
    records_fetched=1000,              # Total records from API
    records_bronze=950,                # Records written to Bronze
    records_silver=900,                # Records in Silver
    records_gold=880,                  # Records in Gold
    records_quarantined=50,            # Records quarantined
    dq_issues={                        # DQ issue breakdown
        "missing_required_field": 30,
        "invalid_format": 20
    },
    sample_records=[                   # Sample records (first 3)
        {"chembl_id": "CHEMBL1", ...},
        {"chembl_id": "CHEMBL2", ...}
    ],
    metadata={                         # Stage-specific metadata
        "provider": "chembl",
        "batch_id": "batch-123"
    }
)
```

## Common Use Cases

### 1. Debug Failing Pipeline

```bash
# Run with debug to see exactly where it fails
python -m bioetl debug problematic_pipeline \
  --mode interactive \
  --limit 10 \
  --breakpoints after_preflight,after_bronze,after_silver,after_dq
```

### 2. Inspect Data Quality Issues

```bash
# Run with DQ breakpoint to see quarantined records
python -m bioetl debug chembl_activity \
  --mode interactive \
  --breakpoints after_dq,on_quarantine \
  --limit 1000
```

When `after_dq` breakpoint is hit, you'll see DQ issue counts:

```
DQ Issues:    {'missing_field': 42, 'invalid_format': 8}
Sample (3 records):
  {"chembl_id": "CHEMBL123", "issue": "missing_field"}
```

### 3. Performance Analysis

```bash
# Use logging mode to capture snapshots without pausing
python -m bioetl debug slow_pipeline \
  --mode log \
  --limit 10000 \
  --log-level INFO
```

Review logs to see record counts at each stage and identify bottlenecks.

### 4. Integration Testing

```python
# Use debug service programmatically in tests
from bioetl.application.services.pipeline_debug_service import PipelineDebugService
from bioetl.infrastructure.observability.debug_adapters import LoggingDebugAdapter

debug_port = LoggingDebugAdapter(logger=logger)
debug_service = PipelineDebugService(debug_port=debug_port, logger=logger)

# Run pipeline with debug service attached
# ...

# Assert snapshots were captured
assert len(debug_service.snapshots) >= 2
assert debug_service.snapshots[0].stage == "preflight_complete"
```

## Architecture

### Debug Flow

```
CLI Command
   ↓
RunOptions (debug_port field)
   ↓
PipelineRunContext (debug_port field)
   ↓
PipelineRunner.__init__(debug_service)
   ↓
PipelineRunner.run() → Breakpoint Calls
   ↓
PipelineDebugService.check_breakpoint()
   ↓
PipelineDebugPort (InteractiveDebugAdapter or LoggingDebugAdapter)
```

### Components

- **`PipelineDebugPort`** (Protocol): Defines debug adapter contract
  - `is_breakpoint_enabled(breakpoint)` → bool
  - `on_breakpoint(hit)` → DebugAction
  - `on_snapshot(snapshot)` → None

- **`InteractiveDebugAdapter`**: CLI-interactive mode with `click.prompt`
- **`LoggingDebugAdapter`**: Non-interactive mode with structured logging
- **`NoOpDebug`**: Production null-object (zero overhead)

- **`PipelineDebugService`**: Application service
  - Captures snapshots at each stage
  - Checks breakpoints and delegates to debug port
  - Maintains snapshot history for post-mortem analysis

## Limitations

### Current Implementation

✅ **Implemented:**
- Interactive and logging debug modes
- CLI command with `--mode`, `--breakpoints`, `--limit`
- `after_preflight` and `after_dq` breakpoints in PipelineRunner
- Snapshot capture with executor state
- Debug service creation and injection

⏳ **Planned (Future):**
- Medallion-level breakpoints (`after_bronze`, `after_silver`, `after_gold`)
  - Requires BatchExecutor integration
- Error and quarantine breakpoints (`on_error`, `on_quarantine`)
- Advanced actions (`skip_stage`, `inspect`, `dump_state`)
- Time-travel debugging (replay from snapshot)
- Hot-reload (modify code without restart)
- Data diff visualization (compare snapshots)
- Remote debugging (attach to running pipeline)

### Performance

- **NoOpDebug (production):** <1% overhead
- **Attached debugger (no paused breakpoints):** <5% overhead
- **Interactive breakpoints:** Pauses execution until user continues

## Troubleshooting

### Debug Mode Not Working

**Problem:** Debug command runs but no breakpoints are hit.

**Solution:** Ensure you're using `debug` command, not `run`:

```bash
# Wrong - uses regular run command
python -m bioetl run chembl_molecule --limit 100

# Correct - uses debug command with debug mode
python -m bioetl debug chembl_molecule --mode interactive --limit 100
```

### No Snapshots in Logging Mode

**Problem:** Logging mode doesn't show debug snapshots.

**Solution:** Set log level to DEBUG to see debug events:

```bash
python -m bioetl debug chembl_molecule \
  --mode log \
  --log-level DEBUG
```

### Breakpoint Not Triggering

**Problem:** Specific breakpoint never triggers.

**Possible causes:**
1. Breakpoint not enabled: Use `--breakpoints` to specify
2. Stage not reached: Pipeline failed before reaching breakpoint
3. Breakpoint not implemented: Check "Breakpoint Stages" section above

## Example Session

```bash
$ python -m bioetl debug chembl_molecule --mode interactive --limit 100 --breakpoints after_preflight,after_dq

============================================================
  BREAKPOINT: after_preflight
  Infrastructure validation complete
============================================================
  Stage:        preflight_complete
  Fetched:      0
  Bronze:       0
  Silver:       0
  Gold:         0
  Quarantined:  0

Action [continue/skip_stage/inspect/abort/dump_state] (continue): continue

[Pipeline executes: fetch 100 records, transform, write to Bronze/Silver/Gold]

============================================================
  BREAKPOINT: after_dq
  Data quality checks complete
============================================================
  Stage:        dq_complete
  Fetched:      100
  Bronze:       95
  Silver:       92
  Gold:         90
  Quarantined:  5
  DQ Issues:    {'missing_field': 3, 'invalid_format': 2}
  Sample (3 records):
    {"chembl_id": "CHEMBL1", ...}
    {"chembl_id": "CHEMBL2", ...}
    {"chembl_id": "CHEMBL3", ...}

Action [continue/skip_stage/inspect/abort/dump_state] (continue): continue

[Pipeline completes]
✓ Pipeline completed successfully
```

## See Also

- [Running Pipelines](running-pipelines.md) - Standard pipeline execution
- [Troubleshooting](troubleshooting.md) - Common pipeline issues
- [Pipeline Lifecycle](pipeline-lifecycle.md) - Understanding pipeline stages
- [DQ Configuration](dq-configuration.md) - Data quality checks
