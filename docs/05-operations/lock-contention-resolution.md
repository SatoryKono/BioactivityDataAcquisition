______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Lock Contention Resolution

**Issue:** #6550
**SSOT:** ADR-010 Local-Only + MemoryLock; runbook [stale-lock.md](runbooks/stale-lock.md)
**State diagram:** `docs/02-architecture/diagrams/state-machines/02-lock-acquisition-state-machine.mmd`

## Model

BioETL default runtime is **single-instance Local-Only**. Locking is in-process
/ local filesystem oriented (MemoryLock). Distributed Redis-style locking from
superseded ADR-003 is **not** the active model.

## Symptoms

- Second run blocked waiting on same pipeline lock
- “Lock held” / timeout errors in logs
- Orphan lock after crash without cleanup
- Long critical section (large batch) increasing wait time

## Detection

1. Identify pipeline id + run_id from logs.
2. Check lock holder metadata (path/process) per stale-lock runbook.
3. Confirm whether holder process is alive.
4. Correlate with checkpoint/shutdown state machines.

## Immediate resolution

1. If holder is dead → follow **stale lock** removal procedure in runbook.
2. If holder is alive → do **not** force-steal; stop duplicate schedule or wait.
3. After release, re-run with same resume/checkpoint policy as designed.
4. Capture evidence (logs, lock file contents) before deletion.

## Configuration / process fixes

- Avoid concurrent schedulers on the same pipeline name
- Reduce lock hold time (smaller batches, faster extract)
- Ensure shutdown/cleanup always releases lock (ADR-015 lifecycle)
- Align CI/local jobs so they do not share the same lock directory unexpectedly

## Prevention

- One active writer per pipeline lock key
- Heartbeat / cleanup on SIGTERM paths
- Operator docs: never run two long pipelines that share lock identity without intent

## Related

- [pipeline-failure-recovery](runbooks/pipeline-failure-recovery.md)
- State machines index: [diagrams/state-machines/README.md](../02-architecture/diagrams/state-machines/README.md)
