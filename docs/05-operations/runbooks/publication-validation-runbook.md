______________________________________________________________________

Version: 2.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P1
  Runtime profile: Local-Only single-instance (ADR-010)
  Last verified: '2026-07-23'

______________________________________________________________________

# Operational Runbook: Publication Validation

## Trigger

Use this procedure when a publication pipeline fails validation or its
release evidence must be reviewed. Preserve the failed run, manifest, ledger,
checkpoint, DQ report, and quarantine evidence before attempting recovery.

## Runtime contract

The supported validation surface is the configured pipeline runtime:

- entity configs: `configs/entities/{provider}/publication.yaml`;
- composite config: `configs/composites/publication.yaml`;
- Gold contracts: `configs/contracts/{provider}/publication.yaml`;
- Pandera schemas: `src/bioetl/domain/contracts/gold/`;
- RunManifest, RunLedger, checkpoint, DQ report, and quarantine artifacts.

ADR-033's current implementation status is authoritative:

- Level 1 schema validation is active;
- former Level 2 standalone structural validation is retired;
- Level 4 logical/cross-field validation is active through config and
  contracts;
- Levels 3 and 5 are not standalone production validators.

There are no supported CLI switches that bypass external or semantic
validation. Do not invent recovery flags from the historical five-level
design.

## Read-only diagnosis

1. Capture the exact pipeline and run:

   ```bash
   bioetl diagnostics run --run-id <run-id>
   bioetl diagnostics checkpoint --pipeline <pipeline>
   ```

1. Inspect the effective entity and contract configuration:

   ```bash
   bioetl config show --pipeline <pipeline>
   bioetl config validate --pipeline <pipeline>
   ```

1. Inspect bounded quarantine evidence without modifying payloads:

   ```bash
   bioetl quarantine inspect \
     --pipeline <pipeline> \
     --run-id <run-id> \
     --limit 200
   ```

1. When table-level inspection is required, use the Delta reader against a
   copied or read-only path:

   ```python
   from deltalake import DeltaTable

   table = DeltaTable("<silver-or-gold-delta-path>")
   evidence = table.to_pyarrow_table()
   ```

   Silver and Gold are Delta tables. Raw Parquet reads and in-place dataframe
   appends are not supported publication recovery operations.

## Failure classification

| Evidence | Classification | Owner |
| --- | --- | --- |
| Pandera/schema error in Gold | contract violation | Gold contract and transformer owner |
| configured cross-field rule failure | logical DQ failure | entity config/DQ owner |
| Silver structural reject | structural normalization/filtering failure | transformer owner |
| quarantine payload present | immutable rejected-input evidence | source/transform owner |
| missing or incompatible checkpoint | control-plane recovery failure | checkpoint/runtime owner |
| provider timeout/rate limit | provider availability failure | adapter owner |

## Recovery

1. Correct the source defect, transformer, config, or contract through normal
   review. Do not mutate the failed Silver/Gold table to manufacture passing
   evidence.
1. Do not weaken DQ thresholds as incident mitigation. Follow
   [pipeline-failure-dq.md](pipeline-failure-dq.md) for a separately reviewed
   policy change when evidence proves the policy itself is wrong.
1. Re-run from the captured checkpoint or replay input only after compatibility
   checks pass:

   ```bash
   bioetl run --pipeline <pipeline> --resume
   ```

1. Compare the replay manifest, effective-config hashes, input snapshot refs,
   row counts, DQ results, and output hashes with the original run.

## Determinism and quarantine invariants

- Replay uses persisted inputs and effective configuration; it must not depend
  on the current wall clock or a fresh provider response.
- Quarantine payload and payload hash are immutable. Resolution metadata may
  change only through the supported quarantine command surface.
- A successful replay creates new run evidence; it does not overwrite the
  failed run's manifest or ledger history.
- Gold remains strict: unexpected or invalid fields fail contract validation.

## Verification

Closure evidence must contain:

- exact `pipeline` and `run_id`;
- manifest and ledger status;
- checkpoint compatibility result;
- DQ report and bounded quarantine summary;
- effective-config and contract versions/hashes;
- replay command and resulting run identity;
- deterministic output comparison.

Escalate when replay inputs are unavailable, checkpoint compatibility is
blocked, the same persisted inputs produce different outputs, or strict Gold
validation still fails after the owning defect is corrected.
