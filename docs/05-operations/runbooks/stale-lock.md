______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P1
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-04-03'

______________________________________________________________________

# Stale Lock Detected (P1)

## Trigger

- Run this procedure when MemoryLock or filesystem lock artifacts block progress after interrupted execution.
- Escalate according to the priority declared in metadata when operator ownership is unclear.

## Impact

- Priority: P1.
- Delayed handling can extend service disruption, data correctness risk, or operator response time.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
- Required access: repository checkout, local shell, logs, configuration, and relevant data/control-plane artifacts.

## Procedure

### Symptoms

- Alert "Lock expired" fires.
- Pipeline refuses to start with `LockAcquisitionError`.
- Logs show "Lock held by owner ... (expired)".

### Causes

1. **Worker Crash**: Worker process was killed (OOM, SIGKILL) without releasing the lock.
1. **Long Running Job**: Job exceeded the 4-hour hard limit.
1. **Forced Termination**: Process was interrupted before graceful shutdown (`aclose()`), leaving stale in-process lock state.

### Diagnosis Steps

1. **Check Active Processes**:
   - Are there any running python processes for this pipeline?
   - If yes, is it stuck? (Check CPU/Memory usage).
1. **Check Lock Status**:
   - Inspect local logs and identify lock owner `run-id`.
   - Remember that `bioetl lock ...` operates on the `MemoryLock` instance in the current CLI process only.

### Recovery Actions

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

- Use `bioetl lock release ...` only if you are debugging lock state in the same process that created it; it is not a cross-process stale-lock recovery tool.

### Prevention

- **Heartbeats**: Ensure workers send heartbeats regularly.
- **Timeouts**: Configure appropriate timeouts for HTTP requests and DB queries.
- **Resource Limits**: Ensure workers have enough memory to avoid OOM kills.

## Compliance

- This runbook MUST be executed within the priority and runtime profile declared in the YAML header.
- Operators SHOULD preserve evidence, commands, and follow-up actions in the Verification and Post-incident sections.

## Verification

- Confirm the triggering condition is cleared or understood with evidence.
- Verify logs, manifests, datasets, or alerts reflect the expected post-procedure state.

## Rollback

- Revert partial changes made during mitigation, including config overrides, restored checkpoints, or rewritten data, if they worsen the situation.
- Return to the last known good state before attempting an alternate recovery path.

## Post-incident

- Record timeline, commands executed, evidence reviewed, and follow-up owners.
- Update related alerts, dashboards, or runbooks when operator gaps or ambiguous steps are discovered.
