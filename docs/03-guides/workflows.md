______________________________________________________________________

Version: 1.0.1
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-16'

______________________________________________________________________

# Workflow Object

## Purpose

This guide describes the canonical BioETL `workflow` object for the active
Workflow Control Plane.

It connects:

- the accepted control-plane boundary in
  [ADR-044](../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md);
- the current declarative workflow code in `src/bioetl/domain/workflow/` and
  `src/bioetl/application/services/workflow_runner_service.py`;
- the shipped workflow control-plane services in
  `src/bioetl/application/services/control_plane/workflow/`.

Use this guide when you need one stable explanation of what a workflow is, what
it is not, and how fields, identities, and workflow control-plane artifacts are
represented in the current codebase.

## Formal Reference Surfaces

Use this guide for operator narrative and end-to-end flow. Use the following
published references for formal semantics:

- [Workflow State Machine](../04-reference/domain/workflow-state-machine.md) —
  canonical workflow/step statuses, transitions, and ambiguity semantics;
- [Workflow Catalog](../04-reference/workflow-catalog.md) — current
  config-backed inventory of `configs/workflows/*.yaml`;
- [Workflow Control-Plane Recovery Runbook](../05-operations/runbooks/workflow-control-plane.md) —
  incident-time recovery and operator procedures.


## Target Control-Plane Model (ADR-047)

The target and shipped workflow control plane is the **manifest + ledger + execution-state** split defined by ADR-047.

### Component roles and responsibility boundaries

- **WorkflowManifest (immutable intent)**: one immutable intent snapshot per workflow run; never mutated after creation.
- **WorkflowLedger (append-only history)**: durable event history for lifecycle and operator intent (`repair`/`force`), but not a mutable status owner.
- **WorkflowExecutionState (mutable owner)**: current workflow/step status, error projection, `repair_required`, and ambiguity markers.
- **Workflow lock (local-only safety)**: one `MemoryLock` key per workflow name under ADR-010 local-only boundary.

### Commands and operator flows

- Start: `bioetl workflow run <name>`
- Safe resume: `bioetl workflow run <name> --resume-last`
- Pinned resume by manifest: `bioetl workflow run <name> --resume-manifest-id <manifest_id>`
- Pinned resume by workflow run: `bioetl workflow run <name> --resume-run-id <workflow_run_id>`
- Ambiguous destructive recovery: `--repair-steps ...` or `--force-steps ...` (explicit operator intent)
- Incremental workflow launch: `bioetl workflow run <name> --incremental`
- Inspection: `bioetl workflow status <name> [--run-id <workflow_run_id>]`

### Ownership boundary (what each seam MUST NOT do)

- Manifest MUST NOT be reused as mutable status.
- Ledger MUST NOT be treated as the sole mutable resume source.
- Execution state MUST NOT silently infer destructive replay without explicit operator flags when ambiguity is present.
- Local lock semantics MUST NOT be replaced with external orchestrators in standard runtime.

### Canonical operation sources

- ADR decision: [ADR-047](../02-architecture/decisions/ADR-047-workflow-control-plane.md)
- Recovery procedure and triage: [Workflow Control-Plane Recovery Runbook](../05-operations/runbooks/workflow-control-plane.md)
- Runtime validation policy linkage: [POST_CHANGE_VALIDATION.md](../00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md)
- Runtime precedence and orchestration policy: repository paths `AGENTS.md` and `.codex/agents/CODEX-RUNTIME.md`

> Deprecated wording: any older docs/text that describe workflow resume as ledger-only or name-only are deprecated. Use ADR-047 + this guide + the workflow runbook as the canonical set.

## Historical Rollout Traceability

The workflow control-plane rollout centered on these historical issue IDs. They
remain useful as traceability anchors, but the current behavior is defined by
the code/config sources cited above and by ADR-047:

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

The guide below intentionally describes the current coherent object model rather
than restating each ticket separately.

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

The workflow model uses three different identity layers.

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

The shipped workflow status vocabulary is defined in
[`workflow-state-machine.md`](../04-reference/domain/workflow-state-machine.md).
Use these names in configs, ledgers, operator output, tests, and docs.

Workflow-level statuses:

- `created`
- `running`
- `success`
- `failed`
- `incomplete`

Step-level statuses:

- `pending`
- `running`
- `commit_pending_confirmation`
- `success`
- `failed`
- `skipped`

Operator-facing fields such as `repair_required` and `ambiguous_step_ids`
describe repair posture and destructive ambiguity; they are not status values.
Older backlog-only aliases are historical planning vocabulary and are not part
of the current shipped status contract.

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

- steps with terminal `success` status should normally be skipped on resume;
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
- workflow config loading from repo-root `configs/workflows`, resolved through
  the canonical config-root seam instead of the current working directory;
- `WorkflowRunnerService` MVP;
- transform-step fingerprinting and skip support;
- workflow-level manifest, ledger, and execution-state persistence;
- workflow CLI with `bioetl workflow run`, `--resume-last`,
  `--resume-manifest-id`, `--resume-run-id`, `--incremental`,
  `--repair-steps`, `--force-steps`, and persisted `workflow status`;
- `bioetl workflow run --tracing` when operator trace drilldowns are expected;
- best-effort workflow metrics publication at the CLI command boundary so
  shipped workflow dashboards can observe completed workflow runs;
- workflow metrics are published with per-run grouping identity so selected-range
  dashboard evidence survives short-lived CLI process exit;
- workflow inspection by workflow name or explicit `--run-id`;
- local single-runtime workflow locking through `MemoryLock`;
- canonical baseline workflow config in `configs/workflows/chembl_baseline.yaml`;
- richer multi-step example workflow config in `configs/workflows/chembl_core.yaml`;
- baseline built-in transform `summarize_upstream_outputs` for local workflow
  transform-step coverage;
- built-in `reconcile_foreign_keys` for idempotent ChEMBL orphan cleanup;
- destructive ambiguity detection with explicit repair / force intent surfaces;
- workflow observability metrics for run and step outcomes.

## Shipped Workflow Inventory

Current shipped workflow configs under `configs/workflows/` now fall into three
operator-facing families:

1. single-pipeline workflow wrappers for every non-composite pipeline;
2. optional provider-pack workflows that bundle multiple related pipelines;
3. canonical baseline workflow `chembl_baseline` that runs the core ChEMBL
   assay/target/publication pipelines before sequential orphan reconciliation;
4. richer multi-step examples such as `chembl_core` that mix pipeline and
   transform steps.

### 1. Single-Pipeline Workflow Wrappers

Every non-composite pipeline in `configs/entities/**` now has a matching
single-step workflow wrapper named `configs/workflows/<pipeline_name>.yaml`.

| Provider | Workflow wrappers |
| --- | --- |
| `chembl` | `chembl_activity`, `chembl_assay`, `chembl_assay_parameters`, `chembl_cell_line`, `chembl_compound_record`, `chembl_molecule`, `chembl_protein_class`, `chembl_publication`, `chembl_publication_similarity`, `chembl_publication_term`, `chembl_subcellular_fraction`, `chembl_target`, `chembl_target_component`, `chembl_target_protein_classification`, `chembl_tissue` |
| `crossref` | `crossref_publication` |
| `openalex` | `openalex_publication` |
| `pubchem` | `pubchem_compound` |
| `pubmed` | `pubmed_publication` |
| `semanticscholar` | `semanticscholar_publication` |
| `uniprot` | `uniprot_idmapping`, `uniprot_protein` |

Canonical wrapper shape:

- `workflow.name == pipeline_name`
- one pipeline step only
- `step_id == run_<pipeline_name>`
- no transform logic bundled by default

This is the minimum durable workflow coverage layer. Operators can now use the
workflow control plane for ordinary pipeline executions without first authoring
a custom multi-step DAG.

### 2. Optional Provider-Pack Workflows

The repo also ships additive provider-pack workflows that group related
pipelines without replacing the single-pipeline wrappers:

- `chembl_reference_pack`
- `publication_provider_pack`
- `uniprot_support_pack`

These packs are:

- optional orchestration bundles;
- still declarative workflow configs under `configs/workflows/`;
- intentionally separate from composite pipelines and composite configs;
- allowed to express light dependency edges where the pack wants a stable
  operator order, but they do not become the only supported entrypoint for the
  child pipelines.

#### Operator run pattern for pack workflows

Pack workflows use the same operator surface as any other workflow:

```bash
bioetl workflow run <pack-name> [workflow options]
```

The current CLI surface that matters most for packs is:

- `--use-cached-bronze` and optional `--cached-bronze-path` /
  `--cached-bronze-date` when the child pipelines require immutable cached
  Bronze inputs;
- `--resume-last`, `--resume-manifest-id`, or `--resume-run-id` for safe
  control-plane recovery;
- `--incremental` for ordinary offset-driven launches that should advance from
  the latest successful execution rather than replay an old occurrence;
- `--only-steps` when an operator needs one bounded subset of the pack DAG;
- optional `--ensure-observability-backend` and `--observability-backend-port`
  (default **8000**) when the operator wants Grafana ID/detail panels backed by
  a detached **BioETL Ops HTTP** / `bioetl health server` (default ensure is off).

#### `chembl_reference_pack`

`configs/workflows/chembl_reference_pack.yaml` bundles ten ChEMBL
reference-data pipelines with six declared dependency edges so target-related
dimensions land in a stable operator order.

Use it when the goal is to refresh ChEMBL reference/supporting dimensions as
one unit instead of running each child wrapper independently.

Canonical examples:

```bash
bioetl workflow run chembl_reference_pack --dry-run
bioetl workflow run chembl_reference_pack --use-cached-bronze --cached-bronze-date 2026-06-29
bioetl workflow run chembl_reference_pack --resume-last
bioetl workflow run chembl_reference_pack --only-steps run_chembl_target,run_chembl_target_component
```

Operator notes:

- prefer cached Bronze when one or more child steps require a
  `replay_ready` persistence floor;
- use `--only-steps` for bounded target/classification refreshes, but remember
  the workflow engine still pulls required dependencies into the execution set;
- use `workflow status` after partial or repaired runs because the pack can have
  multiple in-flight step outcomes at once.

#### `publication_provider_pack`

`configs/workflows/publication_provider_pack.yaml` groups the four independent
publication-provider ingestion workflows: Crossref, OpenAlex, PubMed, and
Semantic Scholar.

Use it when publication coverage should advance as one operator action without
implying cross-provider data dependencies.

Canonical examples:

```bash
bioetl workflow run publication_provider_pack --dry-run
bioetl workflow run publication_provider_pack --incremental
bioetl workflow run publication_provider_pack --resume-run-id 00000000-0000-0000-0000-000000000111
```

Operator notes:

- the pack has zero declared dependency edges, so failures are usually isolated
  to one provider step rather than the full pack topology;
- pinned resume is useful when several recent pack runs exist and the operator
  must recover one exact occurrence.

#### `uniprot_support_pack`

`configs/workflows/uniprot_support_pack.yaml` bundles the two UniProt support
pipelines used for support/reference enrichment.

Use it when the operator wants the UniProt support pair refreshed together
without promoting it into a composite-pipeline entrypoint.

Canonical examples:

```bash
bioetl workflow run uniprot_support_pack --dry-run
bioetl workflow run uniprot_support_pack --incremental --ensure-observability-backend
bioetl workflow run uniprot_support_pack --resume-manifest-id wf-manifest-2026-06-30-001
```

Operator notes:

- the small DAG makes it a good bounded smoke target for workflow control-plane
  validation;
- prefer a long-lived `bioetl health server --port 8000` for Grafana Ops HTTP;
  use `--ensure-observability-backend` only as a short-lived opt-in helper.

### 3. Canonical ChemblBaseline Workflow

`configs/workflows/chembl_baseline.yaml` is the canonical baseline example for a
workflow that runs:

- `run_chembl_assay`
- `run_chembl_target`
- `run_chembl_publication`
- `reconcile_assay_target_orphans`
- `reconcile_assay_publication_orphans`
- `reconcile_target_assay_orphans`
- `reconcile_publication_assay_orphans`

It keeps the destructive reconciliation phase after the core pipeline phase and
uses logical table names only.

The shipped dependency edges are intentionally minimal and reflect actual
transform inputs rather than incidental linear ordering:

- `reconcile_assay_target_orphans` depends on `run_chembl_assay` and
  `run_chembl_target`;
- `reconcile_assay_publication_orphans` depends on
  `reconcile_assay_target_orphans` and `run_chembl_publication`.
- `reconcile_target_assay_orphans` depends on
  `reconcile_assay_publication_orphans`;
- `reconcile_publication_assay_orphans` depends on
  `reconcile_target_assay_orphans`.

This means the workflow no longer encodes a false dependency from target orphan
cleanup to publication ingestion. In execution terms,
`reconcile_assay_target_orphans` may run as soon as assay and target inputs are
ready, before `run_chembl_publication`, because publication data is not part of
that transform's input contract. The inverse target/publication cleanup runs
after assay cleanup so unused Gold target/publication rows are expired only
against the final current `chembl.assay` reference set.

Each executed `reconcile_foreign_keys` transform publishes a compact normal-mode
result artifact under
`data/output/control/workflow_transform_results/<workflow_run_id>/<step_id>/result.json`.
For `chembl_baseline`, this applies to all four `reconcile_*_orphans` steps
listed above. When debug export is enabled, row-level reconcile evidence is also
written under
`artifacts/debug_exports/<workflow_name>/workflow_transforms/<workflow_run_id>/<step_id>/`.
Pipeline `gold_full.csv` files remain pipeline-stage debug exports and are not
the source of truth for post-reconcile current Gold state.

Workflow-level `--dry-run` now applies to both step families:

- pipeline steps inherit dry-run through workflow defaults and CLI overrides;
- destructive transform steps switch to preview/no-op semantics and report when
  a mutation would have happened.

For the built-in `reconcile_foreign_keys` transform this means dry-run shows the
orphan count and `would_mutate=true` without clearing or rewriting the Silver
table.

The built-in reconciliation transform accepts either single keys or composite
key tuples through `source_keys` / `reference_keys`. Null handling is explicit
via `nulls_equal`; the default remains `false`, so null-key rows are treated as
non-matching unless the workflow config states otherwise.

### 4. Richer Multi-Step Example

`configs/workflows/chembl_core.yaml` remains the canonical richer example for a
workflow that mixes:

- multiple pipeline steps;
- built-in transform steps;
- explicit dependency edges;
- destructive repair semantics through the workflow control plane.

If a future workflow needs composite reconciliation keys, keep the paired
`source_keys` / `reference_keys` lists aligned and prefer logical table names
only.

## Future Work Outside The Active Contract

The items below remain useful roadmap context, but they are not part of the
current shipped workflow contract:

- multi-runtime or distributed workflow coordination;
- separate workflow-manifest diff/show namespace beyond the published
  `workflow status` / `workflow run` surface;
- richer live step repair classification beyond the shipped status contract.

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
