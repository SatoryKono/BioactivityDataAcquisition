______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P1
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-08-27'

______________________________________________________________________

# Game Day (DR restore drill)

## Trigger

- Run this procedure at least annually (RULES §5.5 Game Days) or after a
  material change to backup layout, Delta paths, or control-plane artifacts.
- Use it as a **rehearsal**, not as a substitute for a live incident. Live
  restore steps stay in [Data Recovery](data-recovery.md).

## Impact

- Priority: P1.
- Skipping the drill leaves RTO/RPO unproven. Success criteria: restored data
  match the backup point; elapsed time is **less than RTO 4 hours**.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010). Do **not** start
  `docker-compose.monitoring.yml` for this drill unless an operator explicitly
  set `MONITORING=true`.
- A current backup of the local data root exists (see
  [Data Recovery](data-recovery.md) backup cadence / RPO 24h).
- Exclusive access: no concurrent `bioetl run` against the same data root.
- There is **no** `bioetl rollback` command; rollback is restore + rebuild.

## Procedure

### 1. Tabletop (required)

1. Pick one RULES §5.5.1 scenario: Silver/Gold corruption, lost checkpoint, or
   lost host/volume.
1. Name the backup source, restore destination, and the exact
   `bioetl run --pipeline <name> --run-type rebuild --yes` command you would
   run after restore.
1. Record the expected RPO (24h) and RTO (4h) in the drill log.

### 2. Restore rehearsal (required at least annually)

1. Copy or snapshot the backup into an **isolated** data root (never overwrite
   the only copy of production-like local data).
1. Follow [Data Recovery](data-recovery.md) for the chosen scenario.
1. Start the timer at first restore command; stop when Silver/Gold are readable
   and `bioetl run-manifest show <run-id>` (or the rebuilt run) is inspectable.
1. Pass if elapsed time < 4h and row counts / content hashes match the backup
   point for a sampled table.

### 3. Commands that exist

```bash
bioetl run --pipeline <pipeline-name> --run-type rebuild --yes
bioetl run-manifest show <run-id|manifest-id>
```

Do not invent `bioetl rollback`. Do not use Spark `RESTORE TABLE`.

## Compliance

- Execute within the Local-Only profile declared in the header.
- Preserve drill date, scenario, elapsed time, and pass/fail in Post-incident.

## Verification

- Drill log contains RPO/RTO numbers from RULES §5.5.
- Restored sample matches backup (counts and/or `content_hash`).

## Rollback

- Discard the isolated restore root. Do not promote a failed rehearsal over
  the last known-good data root.

## Post-incident

- Record Game Day date, scenario, elapsed minutes, owner, and gaps to fix in
  `data-recovery.md` or this page.
