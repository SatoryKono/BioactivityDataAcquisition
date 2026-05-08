______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-08'

______________________________________________________________________

# Workflow Object

## Purpose

This guide describes the canonical BioETL `workflow` object for the active
Workflow Control Plane backlog.

It connects:

- the accepted control-plane boundary in
  [ADR-044](../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md);
- the current declarative workflow code in `src/bioetl/domain/workflow/` and
  `src/bioetl/application/services/workflow_runner_service.py`;
- the open implementation backlog `WF-02` through `WF-15`.

Use this guide when you need one stable explanation of what a workflow is, what
it is not, and which fields/identities are already shipped versus still planned.

## Backlog Scope

The workflow control-plane rollout centered on these issues:

- `WF-02` [#2691](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/2691): `WorkflowRunnerService` MVP
- `WF-03` [#2692](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/2692): workflow CLI
- `WF-04` [#2693](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/2693): example workflow config + smoke dry-run
- `WF-05` [#2694](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/2694): workflow manifest/ledger control plane
- `WF-06` [#2695](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/2695): resume/retry projection
- `WF-07` [#2696](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/2696): workflow inspection CLI aligned with control-plane taxonomy
- `WF-08` [#2697](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/2697): local single-runtime workflow locking
- `WF-10` [#2699](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/2699): built-in destructive transform `reconcile_foreign_keys`
- `WF-11` [#2700](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/2700): destructive ambiguity recovery with explicit repair/force events
- `WF-15` [#2704](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/2704): docs, runbooks, and ADR

The guide below intentionally describes one coherent object model across those
issues instead of restating each ticket separately.

## Canonical Definition

A BioETL `workflow` is a declarative orchestration object that describes one
named DAG of steps executed as one operator-level unit.

At minimum a workflow owns:

- a stable workflow name;
- a versioned declarative config payload;
- workflow-level default run options;
- one or more ordered steps with explicit dependency edges;
- a runtime execution result at step granularity;
- its own workflow-level control-plane artifacts.

In the current codebase the canonical configuration root is
`WorkflowConfig` from `src/bioetl/domain/workflow/config.py`.

## Object Boundary

The workflow object is deliberately not the same thing as any of the following:

- not a pipeline config:
  pipeline execution remains a child operation invoked by workflow steps;
- not a transform implementation:
  transform logic is referenced by name and parameters, not embedded into the
  workflow object itself;
- not a runtime execution context:
  by analogy with ADR-044, workflow config and workflow provenance must stay
  separate;
- not a universal god-object:
  the same object must not simultaneously be config root, in-flight mutable
  execution state, durable event log, and operator diagnostics payload.

This separation is the workflow-level extension of ADR-044's rule that runtime
execution context and provenance context evolve at different seams.

## Structural Model

### 1. Workflow Config Root

The currently shipped root fields are:

- `name`
- `steps`
- `defaults`
- `version`

Source:
- `WorkflowConfig` in `src/bioetl/domain/workflow/config.py`
- `WorkflowConfigSchema` in `src/bioetl/infrastructure/schemas/workflow_config.py`
- `WorkflowConfigFileSchema` in `src/bioetl/infrastructure/schemas/workflow_config.py`

Semantic interpretation:

- `name` is the operator-facing identity of the workflow definition;
- `version` versions the declarative workflow contract;
- `defaults` contains workflow-level run-option overrides that cascade into
  pipeline steps;
- `steps` is the complete DAG specification.

### 2. Step Types

The workflow DAG currently supports two step families:

- `WorkflowStepConfig` for `pipeline` steps
- `TransformStepConfig` for `transform` steps

Pipeline step fields:

- `step_id`
- `pipeline_name`
- `depends_on`
- `run_options`

Transform step fields:

- `step_id`
- `transform_name`
- `depends_on`
- `config`

This means the workflow object is polymorphic at the step layer: one DAG can
mix pipeline execution and post-pipeline transforms while preserving a shared
dependency model.

### 3. DAG Invariants

Workflow DAG validity is currently enforced by
`src/bioetl/domain/workflow/dag.py`.

The canonical invariants are:

- a workflow must define at least one step;
- `step_id` values must be unique;
- every dependency in `depends_on` must reference a declared step;
- the dependency graph must be acyclic;
- execution order is derived topologically, not by file order alone.

The workflow object is therefore a validated DAG object, not just an arbitrary
ordered list.

## Identity Model

The workflow backlog implies three different identity layers.

### 1. Definition Identity

Definition identity answers: "Which workflow did the operator ask to run?"

Current anchors:

- `workflow.name`
- `workflow.version`
- the YAML file under `configs/workflows/<name>.yaml`

This identity is human-meaningful but is not sufficient for safe resume by
itself.

### 2. Step Identity

Step identity answers: "Which logical child operation inside the workflow is
this?"

Current anchors:

- `step_id`
- step kind: `pipeline` or `transform`
- step-local payload (`pipeline_name` or `transform_name`)

Step identity is stable inside one workflow definition and is the base key for
status, blocking, skipping, and resume projection.

### 3. Execution Identity

Execution identity answers: "Is this rerun semantically the same workflow
execution intent as a previous run?"

This layer is now shipped as a first-class workflow control-plane concern:

- `WF-05` requires a workflow manifest with canonical `sha256` fingerprint
  semantics;
- `WF-06` proposes `--resume-last` against the safest identity, namely the
  latest run with the same execution fingerprint rather than only the same
  workflow name;
- `WF-11` requires auditable repair/force semantics for destructive transforms.

Canonical implication:

- `workflow.name` alone is not a safe resume key;
- the workflow control plane publishes a workflow-level execution fingerprint
  derived from resolved workflow intent;
- child pipeline `run_id` values remain occurrence-level evidence, not the
  semantic identity of the parent workflow.

### 4. Transform Fingerprint Identity

Transform steps already have a shipped deterministic identity primitive via
`WorkflowTransformSpec` in `src/bioetl/domain/workflow/transform_spec.py`.

Its fingerprint is a canonical `sha256` over:

- `step_id`
- `transform_name`
- `depends_on`
- normalized `config`

That fingerprint already powers skip/reuse semantics for transform steps and is
the first concrete example of workflow-level execution identity in the current
implementation.

## Runtime Model

The currently shipped runtime projection is
`WorkflowRunExecutionResult` from
`src/bioetl/application/services/workflow_runner_service.py`.

Current runtime result fields:

- `workflow_name`
- `status`
- `steps`

Each step result currently exposes:

- `step_id`
- `step_kind`
- `status`
- `payload`
- `error_type`
- `error_message`

This runtime object is intentionally a normalized execution result, not the
workflow definition itself.

## Status Model

The backlog defines the target workflow step status vocabulary in `WF-02`:

- `pending`
- `running`
- `succeeded`
- `failed`
- `skipped`
- `blocked`

`WF-06` adds one more derived operational state:

- `incomplete`

Current code-state note:

- the shipped workflow runner still emits compact terminal step outcomes such
  as `success`, `failed`, and `skipped`;
- durable workflow control-plane state now persists workflow-level statuses such
  as `created`, `running`, `success`, `failed`, and `incomplete`;
- operator surfaces also publish `repair_required` and `ambiguous_step_ids`
  instead of silently replaying destructive ambiguity.

## Relationship To Pipelines

The workflow object orchestrates pipelines; it does not replace pipeline
execution.

The expected parent/child boundary is:

- workflow run = parent orchestration unit;
- pipeline step = child pipeline invocation through `PipelineRunnerService`;
- transform step = child transform invocation through `WorkflowTransformService`.

Implications:

- existing `bioetl run` pipeline behavior remains a separate surface;
- workflow orchestration must stay additive to pipeline execution;
- workflow-level control-plane artifacts must not collapse child pipeline run
  provenance into one opaque blob.

## Relationship To The Control Plane

`WF-05` extends ADR-044 from run-level provenance to workflow-level provenance.

The shipped workflow control-plane split is:

- `WorkflowManifest` is immutable and captures intended workflow execution;
- `WorkflowLedger` is append-only and captures lifecycle events;
- inspection services and CLI resolve workflow state from those artifacts plus
  the dedicated workflow execution-state owner;
- resume/retry projections do not rely on ledger as the mutable owner.

By analogy with ADR-044, the workflow object should split into these seams:

1. `WorkflowConfig`
Definition object. Declarative and versioned.

2. Workflow runtime result / execution context
Ephemeral execution-local state used while one workflow is running.

3. `WorkflowManifest`
Immutable provenance artifact for one workflow execution intent.

4. `WorkflowLedger`
Append-only event stream for what actually happened.

That separation is the most important architectural boundary in the whole
Workflow Control Plane program.

## Durable Artifact Model

The workflow object now ships with these first-class durable projections:

| Projection | Role | Mutability |
| ---------- | ---- | ---------- |
| `WorkflowConfig` | Declares intended DAG and defaults | immutable input |
| `WorkflowManifest` | Captures one resolved workflow execution intent | immutable after persist |
| `WorkflowLedger` | Records workflow lifecycle and operator intent | append-only |
| `WorkflowExecutionState` | Owns last-known mutable state for resume/status | mutable owner |

Current storage shape:

- `data/output/control/workflow_manifest/*`
- `data/output/control/workflow_ledger/*`
- `data/output/control/workflow_state/*`

Current operator surface:

- `bioetl workflow run ...`
- `bioetl workflow status ...`

## Resume And Retry Semantics

The linked issues now define the shipped object behavior on rerun:

- succeeded steps should normally be skipped on resume;
- failed steps should be retried;
- `started` without terminal event should be treated as incomplete and retriable;
- destructive transforms must not silently replay after ambiguous crash points;
- explicit `force` and `repair` actions must be visible in ledger history.

This means the workflow object is not just a DAG definition. It is also the
anchor for operator intent across repeated occurrences of the same logical job.

## What Is Already Shipped

Present in the current tree:

- immutable workflow config models;
- strict workflow YAML schema;
- DAG validation and topological ordering;
- workflow config loading from `configs/workflows`;
- `WorkflowRunnerService` MVP;
- transform-step fingerprinting and skip support;
- workflow-level manifest, ledger, and execution-state persistence;
- workflow CLI with `bioetl workflow run`, `--resume-last`,
  `--repair-steps`, `--force-steps`, and persisted `workflow status`;
- workflow inspection by workflow name or explicit `--run-id`;
- local single-runtime workflow locking through `MemoryLock`;
- canonical example workflow config in `configs/workflows/chembl_core.yaml`;
- baseline built-in transform `summarize_upstream_outputs` for local workflow
  transform-step coverage;
- built-in `reconcile_foreign_keys` for idempotent ChEMBL orphan cleanup;
- destructive ambiguity detection with explicit repair / force intent surfaces;
- workflow observability metrics for run and step outcomes.

Not yet fully shipped from the open backlog:

- multi-runtime or distributed workflow coordination;
- separate workflow-manifest diff/show namespace beyond the published
  `workflow status` / `workflow run` surface;
- richer live step taxonomy such as `blocked` on every runner result.

## Canonical Summary

The most accurate short definition today is:

> A BioETL workflow is a named, versioned, declarative DAG that orchestrates
> pipeline and transform steps as one operator-level unit, with step-local
> identity and dependency semantics already shipped, and with a workflow-level
> manifest, append-only ledger, mutable execution-state owner, local-only
> locking, and explicit destructive recovery semantics as a separate
> control-plane layer.

## Related Sources

- [ADR-044: Run Manifest and Run Ledger Control Plane](../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
- [Run Manifest and Run Ledger Contract](../04-reference/contracts/run-manifest-ledger.md)
- `WorkflowConfig` domain model in `src/bioetl/domain/workflow/config.py`
- Workflow DAG validation in `src/bioetl/domain/workflow/dag.py`
- `WorkflowTransformSpec` fingerprinting in `src/bioetl/domain/workflow/transform_spec.py`
- Workflow runner MVP in `src/bioetl/application/services/workflow_runner_service.py`
- [ADR-047: Workflow Control Plane for Declarative Workflows](../02-architecture/decisions/ADR-047-workflow-control-plane.md)
- [Workflow Control-Plane Recovery](../05-operations/runbooks/workflow-control-plane.md)
