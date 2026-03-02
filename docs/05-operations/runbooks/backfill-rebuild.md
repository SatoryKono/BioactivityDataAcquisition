# Backfill and Rebuild Operations

*Reference: [RULES.md §2.4](../../00-project/RULES.md#24-политика-backfill--replay)*

> Runtime profile: Local-Only single-instance (ADR-010). Steps assume local filesystem storage and `MemoryLock` (no Redis/distributed coordinator).

This runbook describes how to perform Backfill (historical load) and Rebuild (full reload) operations.

## Definitions

- **Backfill**: Loading historical data for a specific period.
- **Rebuild**: Completely clearing Silver/Gold tables and reloading from source/Bronze.

## Prerequisites

- **Exclusive Lock**: These operations require an exclusive lock in local `MemoryLock` scope.
- **Downtime**: Incremental pipelines must be stopped or will be blocked.

## Procedure: Full Rebuild

1. **Stop Incremental Pipelines**:
   Ensure no incremental runs are scheduled.

1. **Run Rebuild**:

   ```bash
   bioetl run --pipeline {name} --run-type rebuild
   ```

   *Note: This will automatically clear Silver and Gold tables for this entity.*

1. **Verify Data**:

   - Check record counts in Silver/Gold.
   - Validate DQ metrics.

1. **Resume Incremental**:
   Enable scheduled incremental runs.

## Procedure: Backfill (Time Range)

1. **Determine Range**:
   Identify start and end dates for backfill.

1. **Run Backfill**:

   ```bash
   # Example: Backfill for Jan 2024
   bioetl run --pipeline {name} --run-type backfill
   ```

1. **Monitor Progress**:
   Watch logs for progress. Backfills can be long-running.

## Troubleshooting

- **LockAcquisitionError**: Another process holds the lock. Wait or investigate.
- **Memory Issues**: Backfills process large volumes. Watch for OOM. Reduce batch size if needed.
