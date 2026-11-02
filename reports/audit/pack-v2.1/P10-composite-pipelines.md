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

### Finding 1
- **finding_id**: `pack-v2.1/P10-COMPOSITE-001`
- **root_cause_id**: `rc-many-to-one-config-missing`
- **owner_prompt**: P10
- **concern**: MANY_TO_ONE cardinality requirements cannot be verified without aggregation configs.
- **severity**: P3
- **confidence**: low
- **status**: NOT_VERIFIABLE
- **expected**: MANY_TO_ONE join requires an explicit aggregation config.
- **actual**: No MANY_TO_ONE cardinality is explicitly visible in the YAML configs scanned, rendering static verification impossible.
- **evidence_ids**: E3, E7
- **attempted_disproof**: Checked `configs/entities/composite/molecule.yaml` and `activity.yaml` for aggregation blocks. None found.
- **exceptions_checked**: Composite operations natively fallback to 1:1 or 1:N explosion.
- **impact**: Cannot guarantee safe MANY_TO_ONE data aggregations.
- **root cause**: Missing explicit cardinality definitions in test configs.
- **recommendation**: Add an explicit MANY_TO_ONE mapping in the configs with aggregation functions to allow static verification.
- **scope / non-goals**: Scope is static configuration.
- **acceptance criteria**: A test config provides a MANY_TO_ONE aggregation example.
- **verification command/test**: `grep -r "MANY_TO_ONE" configs/entities/composite/`
- **dependencies**: None.
- **related_findings**: None.

### Finding 2
- **finding_id**: `pack-v2.1/P10-COMPOSITE-002`
- **root_cause_id**: `rc-normalization-profile-runtime-only`
- **owner_prompt**: P10
- **concern**: Normalization-profile compatibility before merge relies on dynamic runtime verification.
- **severity**: P3
- **confidence**: low
- **status**: NOT_VERIFIABLE
- **expected**: Static profiles can prove normalization compatibility before merge execution.
- **actual**: The structural normalization check executes at runtime inside `MergeService`, not as a static DAG gate.
- **evidence_ids**: E3, E6
- **attempted_disproof**: Looked for static linters validating normalization against composite gold contracts; only runtime data validation is present.
- **exceptions_checked**: This is an accepted dynamic execution boundary.
- **impact**: Missed structural drifts could fail the merge phase instead of failing early.
- **root cause**: Lack of static configuration validation.
- **recommendation**: Include normalization profile hash verification in pre-flight composite DAGs.
- **scope / non-goals**: Affects preflight orchestration.
- **acceptance criteria**: Pre-flight composite validater checks `normalization_profile_hash`.
- **verification command/test**: N/A
- **dependencies**: None.
- **related_findings**: None.

## P10 Specific Output
### Composite FSM
States: NOT_STARTED -> SEED_RUNNING -> SEED_COMPLETED -> DEPENDENCIES_RUNNING -> DEPENDENCIES_COMPLETED -> ENRICHING -> ENRICHMENT_COMPLETED -> MERGING -> COMPLETED.
Terminal: COMPLETED, FAILED.
Source: `src/bioetl/domain/composite/state.py`

### Workflow FSM
Step execution sequences bounded by `run_id` and tracked in `RunManifest`. Sub-steps maintain isolated outcomes mapping to `CompositePipelineState`.

### Identity Map
- Workflow identity: `manifest_id`, `workflow_run_id`
- Composite pipeline identity: `run_id`, `composite_run_identity`, `effective_config_hash`

### Join/Cardinality Matrix
- Dependencies & Enrichers: 1:1 or 1:N implied statically.
- `MANY_TO_ONE`: NOT_VERIFIABLE statically (requires explicit metric configs to trace).
- Inner mappings verified for key presense (keys ⊆ seed outputs).

### Recovery/Equivalence Matrix
- Resume points defined by `is_resumable` (SEED_COMPLETED, DEPENDENCIES_RUNNING, DEPENDENCIES_COMPLETED, ENRICHING, ENRICHMENT_COMPLETED, FAILED).
- Data replay fetches cached partitions based on `cached_bronze_date` indicating BYTE_EQUIVALENT intent.

### Invalid-state/test gaps
- Structural normalization profile checks lack static safety enforcement.
- Missing explicit MANY_TO_ONE cardinality examples in contracts.

## E. Quantitative Scorecard
- 4/5: Strong implementation, mostly covered by configuration-as-code and FSMs. Some semantic checks remain NOT_VERIFIABLE without runtime. (Evidence: E1-E12)

## F. Cross-cutting/root-cause clusters
- Both unverified findings relate to runtime vs static definitions of complex join behaviors (cardinality, profile alignment).

## G. Prioritized roadmap P0→P3
1. [P3] Add dummy configs for MANY_TO_ONE to enable testing/verification.

## H. Verification Matrix
- FSM Isolation: E10, E12
- Merge Sequence: E6
- Keys ⊆ Seed: E7
- Explicit Rules Conflict: E5, E11
- State Recovery: E9, E10

## I. `NOT_VERIFIABLE` и missing evidence
- `pack-v2.1/P10-COMPOSITE-001` - missing aggregation configuration evidence.
- `pack-v2.1/P10-COMPOSITE-002` - missing static profile verification evidence.

## J. Self-check
- Attempted to disprove missing pieces by looking for them in tests and configs. Remaining unverified items properly documented and status set to NOT_VERIFIABLE. Strict finding schema followed. Evidence ledger strictly follows `Evidence ID | class | freshness | source` schema. Output contains required P10 section.

## K. Verdict
- Composite merge order and pipeline vs workflow separation conform strongly to architectural standards at this pinned revision. No manual code or config changes needed at this point. No issues created.

## Issue Drafts
### Draft Issue for `pack-v2.1/P10-COMPOSITE-001`
- **audit_id**: `pack-v2.1/P10`
- **audited SHA**: `a5243cb4bbed67b267daecdc097b8c48501e140a`
- **root_cause_id**: `rc-many-to-one-config-missing`
- **source finding IDs**: `pack-v2.1/P10-COMPOSITE-001`
- **severity**: P3
- **confidence**: low
- **status**: NOT_VERIFIABLE
- **Problem**: MANY_TO_ONE cardinality requirements cannot be verified without explicit aggregation configs.
- **Evidence**: `configs/entities/composite/molecule.yaml`, `src/bioetl/application/composite/dependency_join_execution.py`
- **Expected vs actual**: Expected MANY_TO_ONE join to require an explicit aggregation config. Actually, no MANY_TO_ONE cardinality is explicitly visible in the YAML configs scanned, rendering static verification impossible.
- **Impact**: Cannot guarantee safe MANY_TO_ONE data aggregations.
- **Scope / non-goals**: Scope is static configuration.
- **Architecture constraints**: Hexagonal architecture and configuration mappings.
- **Implementation outline**: Define a configuration example in a test config showcasing `MANY_TO_ONE`.
- **Acceptance criteria**: A test config provides a MANY_TO_ONE aggregation example.
- **Verification commands/tests**: `grep -r "MANY_TO_ONE" configs/entities/composite/`
- **Dependencies**: None.
- **Rollback/risk**: Very low.

### Draft Issue for `pack-v2.1/P10-COMPOSITE-002`
- **audit_id**: `pack-v2.1/P10`
- **audited SHA**: `a5243cb4bbed67b267daecdc097b8c48501e140a`
- **root_cause_id**: `rc-normalization-profile-runtime-only`
- **source finding IDs**: `pack-v2.1/P10-COMPOSITE-002`
- **severity**: P3
- **confidence**: low
- **status**: NOT_VERIFIABLE
- **Problem**: Normalization-profile compatibility before merge relies on dynamic runtime verification.
- **Evidence**: `configs/entities/composite/*.yaml`, `src/bioetl/application/composite/merger_orchestration.py`
- **Expected vs actual**: Expected static profiles to be able to prove normalization compatibility before merge execution. Actually, the structural normalization check executes at runtime inside `MergeService`, not as a static DAG gate.
- **Impact**: Missed structural drifts could fail the merge phase instead of failing early.
- **Scope / non-goals**: Affects preflight orchestration.
- **Architecture constraints**: Hexagonal architecture and configuration mappings.
- **Implementation outline**: Add `normalization_profile_hash` verification checks in pre-flight composite tools.
- **Acceptance criteria**: Pre-flight composite validater checks `normalization_profile_hash`.
- **Verification commands/tests**: New pre-flight integration tests passing.
- **Dependencies**: None.
- **Rollback/risk**: Low.
