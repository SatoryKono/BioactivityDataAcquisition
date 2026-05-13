______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P1
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-05-08'

______________________________________________________________________

# Workflow Control-Plane Recovery

## Trigger

- Use this runbook when a declarative workflow run must be inspected, resumed,
  repaired, or force-recovered.
- Use it when `bioetl workflow status` exposes persisted workflow state,
  `repair_required`, or ambiguous destructive-step recovery.

## Impact

- Priority: P1.
- Delayed handling increases recovery risk and can hide explicit operator intent
  around destructive workflow transforms.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem
  storage, MemoryLock.
- Required access: repository checkout, local shell, workflow YAML, and
  `data/output/control/workflow_*` artifacts.

## Procedure

### 1. Inspect the latest workflow state

```bash
bioetl workflow status <workflow-name>
bioetl workflow status <workflow-name> --format json
```

Read these fields first:

- `status`
- `workflow_run_id`
- `manifest_id`
- `execution_fingerprint`
- `repair_required`
- `repair_hint`
- `ambiguous_step_ids`
- `last_error_type`
- `last_error_message`

### 2. Inspect one specific run

```bash
bioetl workflow status <workflow-name> --run-id <workflow-run-id>
```

Use `--run-id` when the latest workflow state is not enough or when multiple
recent occurrences exist for the same workflow definition.

### 3. Ordinary resume

If `repair_required=false` and the latest state is `failed` or `incomplete`:

```bash
bioetl workflow run <workflow-name> --resume-last
```

Interpretation:

- successful steps are skipped;
- failed or incomplete steps are retried;
- semantic workflow identity is checked by execution fingerprint.

### 4. Destructive ambiguity recovery

If `repair_required=true`, do not use plain `--resume-last`.

Choose one explicit recovery path:

```bash
bioetl workflow run <workflow-name> \
  --resume-last \
  --repair-steps <step-id>
```

```bash
bioetl workflow run <workflow-name> \
  --resume-last \
  --force-steps <step-id>
```

Use `--repair-steps` when the operator is intentionally acknowledging an
ambiguity and re-entering a safe repair path. Use `--force-steps` only when the
operator intentionally overrides ordinary resume posture.

### 5. Built-in destructive transform baseline

The first shipped destructive built-in transform is:

- `reconcile_foreign_keys`

Current supported action:

- `delete_orphans`

Canonical example:

- `source_table=chembl_assay`
- `reference_table=chembl_target`
- `source_key=target_id`
- `reference_key=target_id`

Repeated execution is idempotent, but ambiguity after commit still requires
explicit operator intent.

### 6. Local lock check

Workflow execution uses one local lock key per workflow name. If a workflow
claims to already be running:

- confirm whether another local runtime is still active;
- use the stale-lock runbook if the process died unexpectedly;
- do not introduce external coordination as a workaround.

## Direct Artifact Checks

Canonical workflow control-plane paths:

```text
data/output/control/workflow_manifest/{manifest_id}.json
data/output/control/workflow_manifest/_by_run_id/{workflow_run_id}.txt
data/output/control/workflow_ledger/{manifest_id}.jsonl
data/output/control/workflow_ledger/_by_run_id/{workflow_run_id}.txt
data/output/control/workflow_state/{workflow_run_id}.json
```

Useful checks:

```bash
cat data/output/control/workflow_manifest/_by_run_id/<workflow_run_id>.txt
cat data/output/control/workflow_manifest/<manifest_id>.json
tail -n 20 data/output/control/workflow_ledger/<manifest_id>.jsonl
cat data/output/control/workflow_state/<workflow_run_id>.json
```

Look for:

- `workflow_step_commit_pending_confirmation`
- `workflow_repair_requested`
- `workflow_force_requested`

## Verification

- Confirm `workflow status` no longer reports `repair_required=true` after the chosen recovery path succeeds.
- Confirm the expected step statuses are present in persisted state.
- Confirm the workflow lock was released after completion or failure.

## Rollback/Recovery

- If resume or repair selected the wrong workflow run, stop before executing
  additional destructive steps and inspect the specific `workflow_run_id`.
- Restore tracked workflow YAML from git if the workflow definition was edited
  during diagnosis.
- Do not hand-edit retained manifests, ledgers, state files, or checkpoint
  anchors. Use the workflow CLI or open a separate recovery issue when persisted
  control-plane artifacts are inconsistent.
- For ambiguous destructive-step recovery, prefer `--repair-steps` over
  `--force-steps` unless the operator explicitly accepts the replay impact.

## Post-incident

- Record the workflow name, `workflow_run_id`, `manifest_id`, chosen recovery
  path, and verification commands in the incident issue or PR.
- File a follow-up if `repair_required=true` recurs for the same workflow step.
- Update workflow examples or ADR-linked docs if the incident exposes a missing
  recovery path.

## Compliance

- ADR-010 local-only posture remains in force; do not introduce external
  orchestration or distributed locks to recover one local workflow.
- ADR-046 and ADR-047 control checkpoint, ledger, resume, and repair semantics.
  Recovery must preserve explicit operator intent for destructive steps.

## Related Sources

- [CLI Reference](../../04-reference/cli.md)
- [Workflow Object Guide](../../03-guides/workflows.md)
- [ADR-046](../../02-architecture/decisions/ADR-046-checkpoint-vs-ledger-resume.md)
- [ADR-047](../../02-architecture/decisions/ADR-047-workflow-control-plane.md)
- [Stale Lock](stale-lock.md)
