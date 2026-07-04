______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P1
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-04-03'

______________________________________________________________________

# Pipeline Failure Recovery Runbook

## Trigger

- Run this procedure when a pipeline must be stabilized and resumed, rebuilt, or
  rolled back to a known-good local state.
- Escalate according to the priority declared in metadata when operator
  ownership is unclear.

## Impact

- Priority: P1.
- Delayed handling can extend service disruption, data correctness risk, or
  operator response time.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem
  storage, MemoryLock.
- Required access: repository checkout, local shell, logs, configuration, and
  relevant data/control-plane artifacts.

## Procedure

### 1. Route to the right symptom runbook first

- If the failure is clearly critical or integrity-threatening, start with
  [Pipeline Failure - Critical](pipeline-failure-critical.md).
- If the failure is driven by DQ policy or invalid records, start with
  [Pipeline Failure - DQ](pipeline-failure-dq.md).
- Use this page as the shared recovery decision layer after the initial triage.

### 2. Capture recovery evidence

Collect the minimum state you need before changing anything:

```bash
# Recent errors
grep -r "error\|ERROR\|exception" logs/ | tail -50

# Checkpoint owner and progress
cat data/output/checkpoints/{pipeline}.json

# Control-plane state
bioetl run-manifest show <run-id|manifest-id> --format json
```

Focus on:

- exit code
- `run_id`
- latest checkpoint owner/progress
- whether the run failed before or after any Silver/Gold writes

### 3. Choose the recovery mode

| Situation                                    | Action              |
| -------------------------------------------- | ------------------- |
| Interrupted run with valid checkpoint        | Resume              |
| Recoverable failure after transient issue    | Resume              |
| Checkpoint missing/corrupted/incompatible    | Rebuild             |
| Silver/Gold output is suspected inconsistent | Backup then rebuild |
| `loading_strategy: full_scan_only`           | Rebuild, not resume |

### 4. Resume when checkpoint is still trustworthy

For recoverable failures or interrupted runs:

```bash
bioetl run --pipeline <pipeline-name> --resume
```

If operators must resume one explicit historical checkpoint occurrence instead
of trusting the mutable latest pointer:

```bash
bioetl run --pipeline <pipeline-name> --resume-run-id <run-id>
bioetl run --pipeline <pipeline-name> --resume-manifest-id <manifest-id>
```

Use resume only when:

- checkpoint belongs to the expected pipeline/run family
- storage layout is still intact
- there is no evidence of schema or write-side corruption
- operators only need checkpoint continuation rather than strict exact replay

Prefer the occurrence-pinned selectors for forensic/debug workflows where the
run family is known and the latest pointer is not trustworthy enough.

Do not interpret `--resume` as exact replay proof. It is a recovery path for the
current execution family and relies on checkpoint compatibility policy.

### 5. Rebuild when state is not trustworthy

If the checkpoint is corrupted, incompatible, or the pipeline cannot safely
resume:

```bash
bioetl run --pipeline <pipeline-name> --run-type rebuild
```

Use rebuild when:

- checkpoint compatibility blocks resume
- critical schema/write invariants were violated
- output needs to be recomputed from source of truth

Do not interpret `--run-type rebuild` as replay evidence. Rebuild is a fresh
recomputation path, not checkpoint continuation and not strict exact replay.

### 6. Backup and rebuild affected Delta outputs when needed

If Silver/Gold data is suspected inconsistent, preserve the last broken state
before rebuilding:

```bash
# Example path; adjust provider/entity
mv data/output/silver/<provider>/<entity> data/output/silver/<provider>/<entity>.bak
rm data/output/checkpoints/<pipeline>.json
bioetl run --pipeline <pipeline-name> --run-type rebuild
```

After validation succeeds, remove the backup intentionally.

### 7. Post-recovery validation

Confirm the recovery path actually restored a sane runtime:

```bash
# Smoke validation with limited scope when supported
bioetl run --pipeline <pipeline-name> --limit 10
```

Also verify:

- logs no longer emit the triggering failure
- expected Silver/Gold outputs are readable
- checkpoint/control-plane artifacts reflect the new run state

### 8. Escalate when recovery loops

Escalate to development/architecture ownership when:

- the same failure repeats after 3 recovery attempts
- rebuild also fails with the same invariant break
- control-plane inspection shows contradictory lifecycle state

## Compliance

- This runbook MUST be executed within the priority and runtime profile
  declared in the YAML header.
- Operators SHOULD preserve evidence, commands, and follow-up actions in the
  Verification and Post-incident sections.

## Verification

- Confirm the selected recovery mode matched the observed failure type.
- Verify logs, manifests, datasets, or alerts reflect the expected
  post-recovery state.

## Rollback

- Revert partial mitigation changes if they worsen the situation.
- Restore backups before attempting an alternate rebuild path.

## Post-incident

- Record timeline, commands executed, evidence reviewed, and follow-up owners.
- Update linked symptom-specific runbooks when repeated recovery decisions show
  missing operator guidance.
