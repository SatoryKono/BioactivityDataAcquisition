# P11. Reproducibility, replay, manifests, ledgers и lineage

## A. Audit Manifest
- **Audit ID:** pack-v2.1/P11
- **Target Repository:** https://github.com/SatoryKono/BioactivityDataAcquisition
- **Branch:** main
- **Pinned Revision:** 20bc18f2c1f5ff23b23d732d4c9aa703fddeb8b7
- **Environment:** Ubuntu Linux, Python 3.13 (uv), sandboxed environment.
- **Execution Mode:** READ_ONLY (Issue creation NOT authorized during exploration).
- **Scope:** run/workflow control plane, checkpoints, manifests, ledgers, lineage, hashing, replay.
- **Exclusions:** Data pipelines content (focus is on control plane and exact replay capabilities).
- **Worktree State:** Clean

## B. Scope/ownership и exclusions
- **Scope:** The mechanisms ensuring execution identity, code/config provenance, hashing, manifest/ledger immutability, checkpointing, exact replay eligibility, and lineage construction.
- **Ownership:** PRIMARY owner of exact-replay eligibility, deterministic identity, provenance closure, replay equivalence, and canonical equivalence taxonomy.
- **Exclusions:** Semantic validation (P09), versioned schema transitions (P07), lifecycle event wiring (P04, P06), effective config identity parsing logic (P08 uses it, P11 consumes it).

## C. Evidence Ledger

| Evidence ID | Class | Freshness | Source/Location | Description |
|---|---|---|---|---|
| E2.1 | E2 STATIC | CURRENT | `src/bioetl/domain/aggregates/pipeline_run.py` | Implementation of PipelineRun lifecycle. |
| E2.2 | E2 STATIC | CURRENT | `src/bioetl/domain/control_plane/run_manifest.py` | RunManifest data class representing the control plane. |
| E2.3 | E2 STATIC | CURRENT | `src/bioetl/composition/runtime_builders/run_manifest_builder.py` | Builder logic for assembling RunManifest. |
| E2.4 | E2 STATIC | CURRENT | `src/bioetl/composition/bootstrap/runtime/runner_bootstrap_wiring.py` | Wiring of runner and manifest generation. |
| E2.5 | E2 STATIC | CURRENT | `src/bioetl/domain/aggregates/pipeline_run_stage_result.py` | Stage tracking and `PipelineRunState`. |

## D. Findings Register

### NOT_VERIFIABLE (Runtime constraints)

- **finding_id**: `pack-v2.1/P11-RUN-001`
- **root_cause_id**: `no-production-runtime-logs`
- **owner_prompt**: P11
- **concern**: Exact-replay eligibility gate requires verification of retained immutable inputs, pinned code/deps, effective config, and complete anchors against a real execution manifest. Without historical production artifacts, complete replay equivalence cannot be empirically confirmed.
- **severity**: P2
- **confidence**: low
- **status**: NOT_VERIFIABLE
- **expected**: Presence of historical run manifests and complete replay anchors in the repository or accessible artifact storage to verify the exact-replay eligibility gate.
- **actual**: The sandboxed repository contains the structural code for creating manifests (e.g., `RunManifest`), but no populated historical ledgers or run manifests are available for empirical validation.
- **evidence_ids**: E2.2, E2.3
- **attempted_disproof**: N/A (Missing data).
- **exceptions_checked**: N/A
- **impact**: Cannot definitively prove the system perfectly executes exact replays in production, only that the *code* supports the required anchors.
- **root cause**: Missing production/test data volumes in the audit environment.
- **recommendation**: Provide sample execution manifests and input snapshots for offline verification, or run a controlled integration test that dumps a full lineage trace.
- **scope / non-goals**: Verification of exact replay using production data.
- **acceptance criteria**: N/A (Not an actionable defect, but a missing evidence claim).
- **verification command/test**: N/A
- **dependencies**: N/A
- **related_findings**: None

## E. Quantitative Scorecard

| Area | Score (0-5) | Evidence IDs | Justification |
|---|---|---|---|
| Execution identity | 4 | E2.1, E2.2 | `PipelineRun` and `RunManifest` capture `run_id`, `execution_fingerprint`, and stage tracking. Missing empirical validation of uniqueness across parallel runs. |
| Config/code provenance | 3 | E2.2, E2.3 | `RunManifest` contains anchors for config hash and code revision. |
| Inputs & Anchors | 3 | E2.2 | Anchors exist structurally, but missing actual artifacts to confirm immutability in practice. |
| Manifest/ledger | 4 | E2.1, E2.5 | State machine and append-only stage tracking implemented in `PipelineRun`. |
| Lineage/artifacts | 3 | E2.3, E2.4 | Builders assemble context, but full end-to-end lineage closure requires runtime validation. |
| Equivalence Classes | 2 | E2.2 | Taxonomy (`BYTE_EQUIVALENT`, `SEMANTIC_EQUIVALENT`, etc.) is implied by structure but lacks explicit formal enforcement in the domain models inspected. |

## F. Cross-cutting/root-cause clusters
- **Missing Empirical Evidence:** The primary limitation of this audit is the lack of runtime manifests, ledgers, and input snapshots, preventing end-to-end validation of exact replay capabilities (Root Cause: `no-production-runtime-logs`).

## G. Prioritized roadmap P0→P3
No actionable P0-P3 code defects found based on static analysis. The primary need is for test data/artifacts to validate the existing control plane infrastructure.

## H. Verification Matrix
| Requirement | Status |
|---|---|
| Exact-replay eligibility | Partially Supported (Code exists, lack of runtime data) |
| Deterministic identity | Supported |
| Provenance closure | Partially Supported (Requires runtime validation) |
| Replay equivalence | Not Verifiable |

## I. NOT_VERIFIABLE и missing evidence
- Missing historical run manifests and complete replay anchors.
- Missing explicit taxonomic definitions for equivalence classes in domain models.

## J. Self-check
- Unsupported claims: The claim of exact-replay capability is unsupported due to missing runtime evidence.
- Stale evidence: None.
- Exception handling: None required.
- Score/severity consistency: Consistent. Scores reflect the presence of code structures but lack of empirical runtime proof.

## K. Verdict
The repository contains robust structural support for reproducibility and replay via `PipelineRun`, `RunManifest`, and related builder classes. The control plane architecture is well-defined. However, empirical validation of the exact-replay eligibility gate is NOT_VERIFIABLE due to the absence of execution ledgers and historical input snapshots in the audit environment. The codebase demonstrates strong adherence to the expected patterns, but true end-to-end replay equivalence remains an untested hypothesis without live or synthetic production data.

## Eligibility Matrix
| Feature | Eligibility |
|---|---|
| Deterministic execution | Supported by pure transforms |
| Code pinning | Supported via commit SHA in manifest |
| Input immutability | Structural support only (NOT_VERIFIABLE in prod) |
| Complete anchors | Partially verified |

## Replay Dossier
- Replay target: PipelineRunner
- Dependencies: Input snapshot resolution
- Constraints: Requires identical environment and runtime config hash

## Equivalence Verdicts
- `BYTE_EQUIVALENT`: Applicable to raw provider payload data.
- `SEMANTIC_EQUIVALENT`: Used when sorting or non-functional structural changes occur.
- `OCCURRENCE_ONLY_DIFFERENT`: Timing metadata, UUIDs generated per-run, log paths.
- `NOT_EQUIVALENT`: Drift in data schema or business logic mutations.

## A/B Reconciliation
- Pass A found no runtime evidence.
- Pass B confirmed missing runtime ledgers. No discrepancies between passes.

## Unsupported Exact-Replay Claims
- "End-to-end byte-identical outputs across infrastructure changes": Cannot be verified without historical execution data.

## Lineage Gaps
- Gap 1: Missing runtime observability artifacts for historical pipelines.
- Gap 2: Input snapshots are not persisted in the codebase directly.
