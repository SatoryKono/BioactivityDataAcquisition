______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-08'

______________________________________________________________________

# ADR-047: Workflow Control Plane for Declarative Workflows

**Date:** 2026-05-08
**Status:** Accepted
**Decision makers:** @BioETL-Team
**Related:** ADR-010, ADR-014, ADR-015, ADR-044, ADR-046

## Context

Declarative workflow DAGs had already shipped config loading and sequential
execution, but safe operator recovery still needed explicit workflow-level
control-plane seams:

- immutable workflow execution intent;
- append-only workflow lifecycle history;
- a mutable owner for resume/status that is not the ledger;
- local single-runtime safety;
- explicit ambiguity handling for destructive workflow transforms.

ADR-044 already accepted manifest + ledger separation for pipeline runs.
ADR-046 already accepted that ledger history must not become the mutable owner
for resume state. Declarative workflows need the same boundary at workflow
scope.

## Decision

BioETL introduces four workflow-level control-plane seams.

### 1. `WorkflowManifest` is immutable

Each workflow execution persists one immutable manifest before execution starts.
The manifest captures workflow identity, selected steps, defaults, launch
context, and a canonical execution fingerprint.

### 2. `WorkflowLedger` is append-only provenance

Workflow lifecycle, operator intent, and destructive-ambiguity markers are
recorded as immutable ledger events. Published baseline events include:

- manifest created
- workflow started / resumed
- workflow step started
- workflow step completed
- destructive step commit pending confirmation
- workflow finished / failed
- repair requested
- force requested

### 3. `WorkflowExecutionState` owns mutable resume/status state

Workflow resume and status do not derive mutability from ledger alone.
BioETL persists a separate execution-state owner carrying:

- workflow status
- step states
- completed transform fingerprints
- last error
- repair-required flag
- ambiguous destructive step IDs

This is the workflow-scope application of ADR-046.

### 4. Workflow safety is local-only and single-runtime

Workflow execution uses one local workflow lock per workflow name through
`MemoryLock`. This is intentional:

- no Redis;
- no external orchestration;
- no distributed coordinator;
- one local runtime boundary by default.

This is an ADR-010 consequence, not a gap.

### 5. Parent/child correlation is reciprocal and durable

Every pipeline child launched from a workflow receives an optional typed
correlation envelope containing `workflow_run_id`, `workflow_name`, and the
stable DAG `workflow_step_id`. These fields are persisted in the child
`RunManifest`; standalone and historical manifests may omit them.

When the child returns a terminal result, the parent workflow step ledger
details persist `child_run_id` and `child_manifest_id` for both successful and
failed results. The parent-to-child and child-to-parent anchors allow repeated
or concurrent executions of the same workflow to be reconstructed without
timestamp inference. Occurrence IDs remain control-plane fields: they do not
participate in semantic execution fingerprints and must not be introduced as
Prometheus labels.

## Resume and Recovery

### Semantic resume identity

`--resume-last` targets the latest persisted execution state with the same
semantic execution fingerprint. Recovery controls such as:

- `resume_last`
- `force_steps`
- `repair_steps`

do not participate in the fingerprint because they change operator recovery
intent, not execution identity.

### Default resume behavior

On resume:

- successful steps are skipped by default;
- failed steps are retried;
- `running` without terminal confirmation is normalized to `incomplete`.

### Destructive ambiguity

Built-in destructive transforms must not silently replay after a crash point
where mutation may have committed but terminal state was not yet persisted.

When a destructive transform commits its mutation, runtime records a
`commit_pending_confirmation` marker in workflow execution state and appends a
matching ledger event before terminal step completion is persisted.

If the process crashes after commit and before confirmation:

- ambiguity is detectable;
- plain `--resume-last` is blocked;
- operators must choose explicit `--repair-steps` or `--force-steps`;
- operator intent is visible in workflow ledger history.

## First Built-in Destructive Transform

The first shipped destructive workflow transform is:

- `reconcile_foreign_keys`

Current supported action:

- `delete_orphans`

It is storage-backed, config-driven, and idempotent under repeated execution.

## Consequences

### Positive

1. Workflow executions now have immutable intent, append-only history, and a dedicated mutable resume-state owner.
1. `bioetl workflow status` can expose real persisted workflow state.
1. Destructive transform recovery is explicit and auditable.
1. Workflow locking stays inside the local-only runtime contract.
1. Parent and child control-plane records can be joined in both directions.

### Negative

1. Workflow execution writes additional control-plane artifacts.
1. Destructive recovery is stricter and requires explicit operator action.
1. Workflow control-plane implementation spans more seams than the initial runner MVP.

## Storage Shape

The initial workflow control-plane store is filesystem-backed:

- `data/output/control/workflow_manifest/{manifest_id}.json`
- `data/output/control/workflow_manifest/_by_run_id/{workflow_run_id}.txt`
- `data/output/control/workflow_ledger/{manifest_id}.jsonl`
- `data/output/control/workflow_ledger/_by_run_id/{workflow_run_id}.txt`
- `data/output/control/workflow_state/{workflow_run_id}.json`

## Operator Surface

Published workflow control-plane commands:

- `bioetl workflow run <name>`
- `bioetl workflow run <name> --resume-last`
- `bioetl workflow run <name> --repair-steps ...`
- `bioetl workflow run <name> --force-steps ...`
- `bioetl workflow status <name>`
- `bioetl workflow status <name> --run-id <workflow_run_id>`

## Compliance

- ADR-010: local-only coordination.
- ADR-014: deterministic execution identity.
- ADR-015: workflows orchestrate pipelines; they do not replace pipeline lifecycle.
- ADR-044: manifest + ledger separation.
- ADR-046: mutable resume/state owner stays separate from ledger history.
