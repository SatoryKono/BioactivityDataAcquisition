# P10. Composite pipelines и workflow semantics

## A. Audit Manifest
- **Repo**: SatoryKono/BioactivityDataAcquisition
- **Branch**: main
- **Pinned Revision (HEAD SHA)**: a5243cb4bbed67b267daecdc097b8c48501e140a
- **Clean/Dirty Worktree**: Clean (except for this generated report)
- **Environment**: Python/uv, pytest, bash on Linux
- **Mode**: READ_ONLY (Issue creation allowed if needed)
- **Evidence Mode**: REPO_ONLY

## B. Scope/Ownership и exclusions
- **Scope**: `domain/application/composition/configs/control-plane` для composite и workflow.
- **Exclusions**: DQ-семантика cross-validation (относится к P09). Observability/lineage closure передается P14/P11.

## C. Evidence Ledger
- `E1`: `E1 NORMATIVE` | `CURRENT` | `ADR-026-composite-pipeline-pattern.md` (Composite Architecture)
- `E2`: `E1 NORMATIVE` | `CURRENT` | `ADR-047-workflow-control-plane.md` (Workflow Semantics)
- `E3`: `E2 STATIC` | `CURRENT` | `configs/entities/composite/*.yaml` (Composite Pipeline Configs)
- `E4`: `E2 STATIC` | `CURRENT` | `configs/workflows/*.yaml` (Workflow definitions)
- `E5`: `E2 STATIC` | `CURRENT` | `configs/composites/field_groups/shared_policy.yaml` (Conflict resolution rules)
- `E6`: `E2 STATIC` | `CURRENT` | `src/bioetl/application/composite/merger_orchestration.py` (Merge Semantics)
- `E7`: `E2 STATIC` | `CURRENT` | `src/bioetl/application/composite/dependency_join_execution.py` (Join Semantics)
- `E8`: `E2 STATIC` | `CURRENT` | `src/bioetl/application/workflow/transforms/reconcile_foreign_keys.py` (Workflow transforms)
- `E9`: `E2 STATIC` | `CURRENT` | `src/bioetl/application/composite/checkpoint/state.py` (Failure/recovery matrix)
- `E10`: `E2 STATIC` | `CURRENT` | `src/bioetl/domain/composite/state.py` (Composite FSM)
- `E11`: `E2 STATIC` | `CURRENT` | `src/bioetl/application/composite/conflict_resolver.py` (Conflict resolver logic)
- `E12`: `E2 STATIC` | `CURRENT` | `src/bioetl/composition/bootstrap/runtime/composite_control_plane_builder.py` (Control Plane run manifests)

## D. Findings Register

No confirmed P10 defect was found in these two areas. The original candidate findings are withdrawn because existing runtime validation and tests already enforce the stated constraints; this audit does not create issue drafts for them.

## P10 Specific Output
### Composite FSM
States: NOT_STARTED -> SEED_RUNNING -> SEED_COMPLETED -> DEPENDENCIES_RUNNING -> DEPENDENCIES_COMPLETED -> ENRICHING -> ENRICHMENT_COMPLETED -> MERGING -> COMPLETED.
Terminal: COMPLETED, FAILED.
Source: `src/bioetl/domain/composite/state.py`

### Workflow FSM
Workflow lifecycle is owned by `WorkflowExecutionState` (`created`, `running`, `success`, `failed`, `incomplete`) and step lifecycle by `WorkflowStepState`; `WorkflowManifest` records immutable intent. Recovery that requires operator action is explicit (`--repair-steps` / `--force-steps`). This is separate from the composite pipeline FSM in `src/bioetl/domain/composite/state.py`. See `docs/04-reference/domain/workflow-state-machine.md`.

### Identity Map
- Workflow identity: `manifest_id`, `workflow_run_id`
- Composite pipeline identity: `run_id`, `composite_run_identity`, `effective_config_hash`

### Join/Cardinality Matrix
- `EnricherConfig` rejects `MANY_TO_ONE` when aggregation is absent (`src/bioetl/domain/composite/config_models.py::_validate`).
- Unit tests cover both rejection without aggregation and acceptance with aggregation (`tests/unit/domain/composite/test_composite_config.py::test_enricher_config_many_to_one_requires_aggregation`, `::test_enricher_config_many_to_one_with_aggregation`).
- Inner mappings verified for key presense (keys ⊆ seed outputs).

### Recovery/Equivalence Matrix
- Resume points defined by `is_resumable` (SEED_COMPLETED, DEPENDENCIES_RUNNING, DEPENDENCIES_COMPLETED, ENRICHING, ENRICHMENT_COMPLETED, FAILED).
- Data replay fetches cached partitions based on `cached_bronze_date` indicating BYTE_EQUIVALENT intent.

### Invalid-state/test gaps
- No gap is claimed for the reviewed normalization mismatch or `MANY_TO_ONE` aggregation requirements; see the tests listed in the Verification Matrix.

## E. Quantitative Scorecard
- 4/5: Strong implementation, mostly covered by configuration-as-code and FSMs. Some semantic checks remain NOT_VERIFIABLE without runtime. (Evidence: E1-E12)

## F. Cross-cutting/root-cause clusters
- No confirmed cross-cutting defect remains from the two withdrawn candidate findings.

## G. Prioritized roadmap P0→P3
- No remediation item is proposed for these already-enforced validation rules.

## H. Verification Matrix
- `tests/unit/domain/composite/test_composite_config.py::test_enricher_config_many_to_one_requires_aggregation`: rejects `MANY_TO_ONE` without aggregation.
- `tests/unit/domain/composite/test_composite_config.py::test_enricher_config_many_to_one_with_aggregation`: accepts the valid aggregation config.
- `tests/unit/repo_backed/application/composite/test_preflight_validator.py::test_validate_fails_on_field_level_normalization_mismatch_without_override`: preflight rejects a field-level normalization mismatch.
- Workflow status ownership and transitions: `src/bioetl/domain/control_plane/workflow_execution_state.py`, `docs/04-reference/domain/workflow-state-machine.md`.
- FSM Isolation: E10, E12
- Merge Sequence: E6
- Keys ⊆ Seed: E7
- Explicit Rules Conflict: E5, E11
- State Recovery: E9, E10

## I. `NOT_VERIFIABLE` и missing evidence
- None for the two withdrawn candidates. This report does not claim that composite and workflow FSMs are one state machine.

## J. Self-check
- Verified candidate claims against the domain guard and focused unit tests. Workflow-level state is documented separately from composite pipeline state. Evidence ledger strictly follows `Evidence ID | class | freshness | source` schema. Output contains required P10 section.

## K. Verdict
- The reviewed configuration guard and preflight validation reject the cited invalid cases. Workflow execution and composite pipeline state have separate owners. No issue drafts are warranted for the withdrawn candidates.

## Issue Drafts
None. The candidates above duplicate existing validation controls and were withdrawn before P20.
