# Backfill and Rebuild Operations

*Reference: [RULES.md §2.4](../../RULES.md#24-политика-backfill--replay)*

This runbook describes how to perform Backfill (historical load) and Rebuild (full reload) operations.

## Definitions
- **Backfill**: Loading historical data for a specific period.
- **Rebuild**: Completely clearing Silver/Gold tables and reloading from source/Bronze.

## Prerequisites
- **Exclusive Lock**: These operations require an exclusive lock (`lock:{provider}_{entity}:exclusive`).
- **Downtime**: Incremental pipelines must be stopped or will be blocked.

## Procedure: Full Rebuild

1. **Stop Incremental Pipelines**:
   Ensure no incremental runs are scheduled.

2. **Run Rebuild**:
   ```bash
   make run-pipeline PIPELINE={pipeline_name} ARGS="--full-rebuild"
   ```
   *Note: This will automatically clear Silver and Gold tables for this entity.*

3. **Verify Data**:
   - Check record counts in Silver/Gold.
   - Validate DQ metrics.

4. **Resume Incremental**:
   Enable scheduled incremental runs.

## Procedure: Backfill (Time Range)

1. **Determine Range**:
   Identify start and end dates for backfill.

2. **Run Backfill**:
   ```bash
   # Example: Backfill for Jan 2024
   make run-pipeline PIPELINE={pipeline_name} ARGS="--backfill --start-date 2024-01-01 --end-date 2024-01-31"
   ```

3. **Monitor Progress**:
   Watch logs for progress. Backfills can be long-running.

## Troubleshooting
- **LockAcquisitionError**: Another process holds the lock. Wait or investigate.
- **Memory Issues**: Backfills process large volumes. Watch for OOM. Reduce batch size if needed.
