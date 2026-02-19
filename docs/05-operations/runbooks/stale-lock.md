# Stale Lock Detected (P2)

*Reference: [RULES.md §3.3](../../00-project/RULES.md#33-%D0%BA%D0%BE%D0%BD%D0%BA%D1%83%D1%80%D0%B5%D0%BD%D1%82%D0%BD%D0%BE%D1%81%D1%82%D1%8C-%D0%B8-%D0%B1%D0%BB%D0%BE%D0%BA%D0%B8%D1%80%D0%BE%D0%B2%D0%BA%D0%B8)*

This runbook describes how to handle "Stale Lock" alerts.

## Symptoms

- Alert "Lock expired" fires.
- Pipeline refuses to start with `LockAcquisitionError`.
- Logs show "Lock held by owner ... (expired)".

## Causes

1. **Worker Crash**: Worker process was killed (OOM, SIGKILL) without releasing the lock.
1. **Long Running Job**: Job exceeded the 4-hour hard limit.
1. **Network Partition**: Worker lost connectivity to Lock Manager (Redis/Memory).

## Diagnosis Steps

1. **Check Active Processes**:
   - Are there any running python processes for this pipeline?
   - If yes, is it stuck? (Check CPU/Memory usage).
1. **Check Lock Status**:
   - Inspect lock key in Redis (if applicable) or logs.

## Recovery Actions

1. **Kill Zombie Processes**:
   - If a worker is stuck, kill it.
1. **Release Lock Manually**:
   ```bash
   make release-lock PIPELINE={pipeline-name}
   ```
   *Note: Ensure no other worker is actually writing to avoid data corruption.*
1. **Restart Pipeline**:
   ```bash
   bioetl run --pipeline {pipeline-name}
   ```

## Prevention

- **Heartbeats**: Ensure workers send heartbeats regularly.
- **Timeouts**: Configure appropriate timeouts for HTTP requests and DB queries.
- **Resource Limits**: Ensure workers have enough memory to avoid OOM kills.
