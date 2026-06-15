______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-15'

______________________________________________________________________

# Workflow State Machine

## Purpose

This page is the formal workflow lifecycle reference for the shipped Workflow
Control Plane.

Use it together with:

- [Workflow Guide](../../03-guides/workflows.md) for operator narrative;
- [Workflow Catalog](../workflow-catalog.md) for the current declarative DAG
  inventory;
- [Workflow Control-Plane Runbook](../../05-operations/runbooks/workflow-control-plane.md)
  for recovery and incident response.

## Artifact Ownership Matrix

| Artifact | Role | Mutable? | Source of truth |
| --- | --- | --- | --- |
| `WorkflowManifest` | Immutable intent snapshot for one workflow run | No | `src/bioetl/domain/ports/control_plane/workflow_manifest.py` |
| `WorkflowLedger` | Append-only history of lifecycle and operator intent | Append-only | `src/bioetl/domain/ports/control_plane/workflow_ledger.py` |
| `WorkflowExecutionState` | Mutable current owner for workflow/step status, error projection, repair state, and ambiguity | Yes | `src/bioetl/domain/control_plane/workflow_execution_state.py` |

Boundary rules:

- manifest MUST NOT be reused as mutable status;
- ledger MUST NOT be treated as the sole mutable resume source;
- execution state MUST NOT infer destructive replay silently when ambiguity is
  present.

## Workflow-Level Statuses

Current owner model: `WorkflowExecutionState.status`

| Status | Meaning | Terminal |
| --- | --- | --- |
| `created` | Execution-state artifact exists but workflow has not started step execution | No |
| `running` | At least one step is in active execution or the workflow is otherwise in progress | No |
| `success` | All selected steps completed successfully | Yes |
| `failed` | Workflow stopped because a step or workflow-level operation failed | Yes |
| `incomplete` | Workflow requires explicit repair/force or further operator action before safe continuation | Yes for automatic resume; operator action required |

## Step-Level Statuses

Current owner model: `WorkflowStepState.status`

| Status | Meaning | Terminal |
| --- | --- | --- |
| `pending` | Step is declared but has not started | No |
| `running` | Step execution is in progress | No |
| `commit_pending_confirmation` | Destructive/mutating step finished work that requires explicit confirmation/recovery semantics | No |
| `success` | Step completed successfully | Yes |
| `failed` | Step failed and recorded error projection | Yes |
| `skipped` | Step was intentionally skipped based on selection or prior state | Yes |

## Transition Model

### Workflow-Level Transitions

| From | Trigger | To |
| --- | --- | --- |
| `created` | `bioetl workflow run <name>` creates and starts a run | `running` |
| `running` | all selected steps succeed | `success` |
| `running` | step failure or workflow-level failure with no ambiguous destructive state | `failed` |
| `running` | ambiguous destructive state, repair requirement, or unresolved commit boundary | `incomplete` |
| `incomplete` | explicit operator recovery via `--repair-steps` or `--force-steps`, then successful continuation | `running` -> `success` or `failed` |

### Step-Level Transitions

| From | Trigger | To |
| --- | --- | --- |
| `pending` | scheduler selects runnable step | `running` |
| `running` | non-destructive successful completion | `success` |
| `running` | destructive completion awaiting explicit confirmation semantics | `commit_pending_confirmation` |
| `running` | failure | `failed` |
| `pending` | step excluded from current selection | `skipped` |
| `commit_pending_confirmation` | explicit operator-approved continuation | `success` or workflow-level recovery path |

## Ambiguity And Repair Semantics

Relevant execution-state fields:

- `repair_required`
- `repair_hint`
- `ambiguous_step_ids`
- `commit_pending_confirmation`

Canonical interpretation:

- `--resume-last` is the safe default continuation path only when the current
  execution-state is unambiguous.
- `repair_required=true` means normal resume is insufficient.
- `ambiguous_step_ids` identifies destructive or uncertain steps that need
  operator intent.
- `--repair-steps ...` declares bounded repair/reconciliation intent.
- `--force-steps ...` declares explicit destructive re-execution intent.

## Operator Command Matrix

| Operator command | Expected use |
| --- | --- |
| `bioetl workflow run <name>` | Start a new workflow run from declarative config. |
| `bioetl workflow run <name> --resume-last` | Safely continue the latest compatible run when no destructive ambiguity remains. |
| `bioetl workflow run <name> --repair-steps <ids>` | Repair or reconcile explicitly identified ambiguous/destructive steps. |
| `bioetl workflow run <name> --force-steps <ids>` | Force explicit re-execution of steps when destructive recovery is intended. |
| `bioetl workflow status <name> [--run-id <workflow_run_id>]` | Inspect current workflow, step state, and control-plane evidence. |

## Related References

- [Workflow Guide](../../03-guides/workflows.md)
- [Workflow Catalog](../workflow-catalog.md)
- [Run Manifest and Run Ledger Contract](../contracts/run-manifest-ledger.md)
- [ADR-046](../../02-architecture/decisions/ADR-046-checkpoint-vs-ledger-resume.md)
- [ADR-047](../../02-architecture/decisions/ADR-047-workflow-control-plane.md)
