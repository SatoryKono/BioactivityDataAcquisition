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
1. Name the backup source, isolated restore destination, and exact command
   for the chosen scenario. For Bronze recovery, identify the verified
   provider/entity snapshot directory and date (or full date range) and use
   the cached-input rebuild command below. For a lost checkpoint, follow
   Data Recovery Scenario 3, Option A: reset the checkpoint and rebuild
   using the live provider, not the cached-input command below.
1. Record the expected RPO (24h) and RTO (4h) in the drill log.

### 2. Restore rehearsal (required at least annually)

1. Copy or snapshot the backup into an **isolated** data root (never overwrite
   the only copy of production-like local data).
1. Set `BIOETL_DATA_DIR` in the rehearsal process to the absolute isolated
   data root and verify resolved output paths before running any rebuild;
   keep the snapshot source and original data outside those destinations.
1. For Bronze recovery, verify the selected snapshot is intact and covers the
   intended pipeline and recovery point; keep it separate from rebuild
   destinations. For checkpoint reset, use the live-provider procedure.
1. Follow [Data Recovery](data-recovery.md) for the chosen scenario.
1. Start the timer at first restore command; stop when Silver/Gold are readable
   and `bioetl run-manifest show <run-id>` (or the rebuilt run) is inspectable.
1. Pass if elapsed time < 4h and row counts / content hashes match the backup
   point for a sampled table.

### 3. Bronze recovery commands

After setting `BIOETL_DATA_DIR` to the isolated data root as above:

```bash
bioetl run --pipeline <pipeline-name> --run-type rebuild --yes --use-cached-bronze --cached-bronze-path <bronze-snapshot-path> --cached-bronze-date <YYYY-MM-DD>
bioetl run-manifest show <run-id|manifest-id>
```

The snapshot path must be the provider/entity directory directly containing
dated batch directories, not the common Bronze root. The date filters input
to one day; omit it only when the verified snapshot
contains the intended multi-day input. Without `--use-cached-bronze`, rebuild
uses the live provider, not the saved snapshot. Cached recomputation is not
strict exact replay.

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
