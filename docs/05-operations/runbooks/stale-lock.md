# Stale Lock Detected (P2)

*Reference: [RULES.md §3.3](../../00-project/RULES.md#33-конкурентность-и-блокировки)*

> Runtime profile: Local-Only single-instance (ADR-010). Lock diagnostics assume local process scope and `MemoryLock`.

This runbook describes how to handle "Stale Lock" alerts.

## Symptoms

- Alert "Lock expired" fires.
- Pipeline refuses to start with `LockAcquisitionError`.
- Logs show "Lock held by owner ... (expired)".

## Causes

1. **Worker Crash**: Worker process was killed (OOM, SIGKILL) without releasing the lock.
1. **Long Running Job**: Job exceeded the 4-hour hard limit.
1. **Forced Termination**: Process was interrupted before graceful shutdown (`aclose()`), leaving stale in-process lock state.

## Diagnosis Steps

1. **Check Active Processes**:
   - Are there any running python processes for this pipeline?
   - If yes, is it stuck? (Check CPU/Memory usage).
1. **Check Lock Status**:
   - Inspect local logs and identify lock owner `run-id`.
   - Remember that `bioetl lock ...` operates on the `MemoryLock` instance in the current CLI process only.

## Recovery Actions

1. **Kill Zombie Processes**:
   - If a worker is stuck, kill it.
1. **Restart Pipeline**:
   ```bash
   bioetl run --pipeline {pipeline-name}
   ```
1. **Same-process diagnostics only**:
   ```bash
   bioetl lock check --pipeline {pipeline-name} --run-id {run-id}
   ```
   Use `bioetl lock release ...` only if you are debugging lock state in the same process that created it; it is not a cross-process stale-lock recovery tool.

## Prevention

- **Heartbeats**: Ensure workers send heartbeats regularly.
- **Timeouts**: Configure appropriate timeouts for HTTP requests and DB queries.
- **Resource Limits**: Ensure workers have enough memory to avoid OOM kills.
