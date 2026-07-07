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

### 7. ChemblBaseline workflow check

The shipped `chembl_baseline` example lives in
`configs/workflows/chembl_baseline.yaml` and runs the core ChEMBL entity
pipelines before the reconciliation phase:

- `run_chembl_assay`
- `run_chembl_target`
- `run_chembl_publication`
- `reconcile_assay_target_orphans`
- `reconcile_assay_publication_orphans`
- `reconcile_target_assay_orphans`
- `reconcile_publication_assay_orphans`

Its reconciliation edges are intentionally input-driven:

- `reconcile_assay_target_orphans` depends on `run_chembl_assay` and
  `run_chembl_target`;
- `reconcile_assay_publication_orphans` depends on
  `reconcile_assay_target_orphans` and `run_chembl_publication`.
- `reconcile_target_assay_orphans` depends on
  `reconcile_assay_publication_orphans`, because it prunes unused Gold target
  rows only after the assay source has been cleaned against target and
  publication references.
- `reconcile_publication_assay_orphans` depends on
  `reconcile_target_assay_orphans`, giving the inverse cleanup phase a stable
  operator-facing order.

This removes a false dependency from target orphan cleanup to publication
ingestion. In practice `reconcile_assay_target_orphans` can run as soon as
assay and target inputs are complete, because publication data is not part of
that transform's input contract. The inverse target/publication cleanup remains
after `reconcile_assay_publication_orphans`, because its reference side is the
final current `chembl.assay` Gold table.

When reviewing this workflow, keep the reconciliation config on logical table
names only:

- `source_table=chembl.assay`
- `reference_table=chembl.target`
- `source_key=target_id`
- `reference_key=target_id`
- `source_table=chembl.assay`
- `reference_table=chembl.publication`
- `source_key=publication_id`
- `reference_key=publication_id`
- `source_table=chembl.target`
- `reference_table=chembl.assay`
- `source_key=target_id`
- `reference_key=target_id`
- `source_table=chembl.publication`
- `reference_table=chembl.assay`
- `source_key=publication_id`
- `reference_key=publication_id`

The reconciliation transform also accepts composite keys via paired
`source_keys` / `reference_keys` lists. Keep both lists aligned and set
`nulls_equal` explicitly when a workflow should treat null-key rows as valid
matches rather than orphans.

### 8. Workflow dry-run for destructive transforms

Use workflow dry-run when an operator wants preview evidence without allowing
destructive mutation:

```bash
bioetl workflow run chembl_baseline --dry-run --only-steps reconcile_assay_target_orphans
```

Under this mode:

- pipeline steps still receive normal dry-run semantics;
- destructive transforms such as `reconcile_foreign_keys` switch to preview/no-op mode;
- CLI output explicitly marks blocked destructive mutation when the transform
  would have deleted orphan rows.

If a dry-run preview shows a needed mutation, rerun without `--dry-run` only
after the operator has confirmed the intended recovery path.

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
- [POST_CHANGE_VALIDATION policy](../../00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md)
- [Stale Lock](stale-lock.md)
