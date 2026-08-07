______________________________________________________________________

Title: Reproducibility Scoring Rubric
Status: Active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: "2026-04-22"

______________________________________________________________________

# Reproducibility Scoring Rubric

This rubric makes reproducibility audit scores repeatable. Each category has
five criteria. Each criterion is scored:

| Score | Meaning                                                              |
| ----: | -------------------------------------------------------------------- |
|     0 | Absent, unsafe, fail-open, or not evidenced                          |
|     1 | Partial support, degraded support, or documented but not test-backed |
|     2 | Implemented, documented, and test-backed                             |

Category score is the sum of its five criteria, so each category scores from
0 to 10. Reviewers MUST cite evidence for every non-zero score. Missing
evidence MUST be recorded explicitly instead of inferred.

Canonical score labels used by drift checks:
| 0 | Absent, unsafe, fail-open, or not evidenced |
| 2 | Implemented, documented, and test-backed |

## Criteria

### Determinism

| ID    | Criterion               | 0                                                     | 1                                                           | 2                                                                                |
| ----- | ----------------------- | ----------------------------------------------------- | ----------------------------------------------------------- | -------------------------------------------------------------------------------- |
| DET-1 | Canonical serialization | Ad hoc serialization                                  | Canonical path exists but has uncovered bypasses            | Canonical JSON/normalization contracts cover persisted identity payloads         |
| DET-2 | Stable timestamps       | Wall-clock timestamps enter semantic hashes           | Occurrence timestamps are separated in some surfaces        | Semantic identity excludes occurrence timestamps across governed surfaces        |
| DET-3 | Stable ordering         | Output order depends on input/runtime iteration       | Sorting is local to selected writers                        | Ordering-sensitive writes and comparisons are explicitly normalized              |
| DET-4 | Randomness control      | Random or nondeterministic IDs affect replay identity | Runtime IDs are separated but some identities are ambiguous | Reproducibility anchors use deterministic hashes or explicit run identity fields |
| DET-5 | Drift guards            | No tests prevent deterministic contract drift         | Unit tests cover selected helpers                           | Architecture/contract tests guard deterministic semantics across layers          |

### Idempotency

| ID    | Criterion            | 0                                                    | 1                                             | 2                                                                                           |
| ----- | -------------------- | ---------------------------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------- |
| IDE-1 | Write idempotency    | Re-runs duplicate persisted rows                     | Merge/upsert exists for some layers           | Layer write contracts preserve idempotent merge/upsert behavior                             |
| IDE-2 | Checkpoint safety    | Resume can mutate state without compatibility checks | Compatibility checks are observe-only         | Resume policy can fail closed on identity mismatch                                          |
| IDE-3 | Control-plane writes | Control-plane artifacts overwrite semantic history   | Some artifacts are immutable                  | Manifest, ledger, effective-config, and lineage writes preserve immutable/auditable history |
| IDE-4 | Cleanup safety       | Cleanup can remove referenced artifacts              | Dry-run exists without dependency protection  | Cleanup planner protects retained references before apply                                   |
| IDE-5 | Retry behavior       | Retry/fallback behavior changes identity             | Retry behavior is bounded but under-evidenced | Retry/fallback semantics are deterministic or isolated from identity anchors                |

### Run Identity

| ID    | Criterion             | 0                                     | 1                                               | 2                                                                              |
| ----- | --------------------- | ------------------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------ |
| RID-1 | Manifest identity     | No durable manifest identity          | Manifest exists but lacks complete anchors      | Manifest carries run, config, source, artifact, and replay anchors             |
| RID-2 | Execution fingerprint | Fingerprint absent or path/time-bound | Fingerprint present but partial                 | Fingerprint is canonical and drift-tested                                      |
| RID-3 | Config identity       | Config hash includes locator noise    | Config hashes are stable for selected sources   | Effective config artifacts separate semantic identity from occurrence metadata |
| RID-4 | Source identity       | Source inputs are implicit            | Sources are listed without immutable input refs | Source refs include content-addressed input snapshot identity                  |
| RID-5 | Replay parentage      | Replay lineage is not represented     | Parentage exists but is optional/ambiguous      | Replay run/manifest parentage is explicit and inspected                        |

### Checkpoint Safety

| ID    | Criterion             | 0                                                 | 1                                                            | 2                                                                        |
| ----- | --------------------- | ------------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------ |
| CPS-1 | Identity continuity   | Checkpoint resume ignores identity changes        | Compatibility emits warnings only                            | Hard-fail policy blocks unsafe resume                                    |
| CPS-2 | Anchor completeness   | Checkpoints store only run IDs                    | Checkpoints store partial anchors                            | Checkpoints persist config, contract, manifest, and execution anchors    |
| CPS-3 | Composite checkpoints | Composite state lacks resume boundary             | Composite state captures anchors but has partial enforcement | Composite checkpoints are bounded to resume/rebuild semantics and tested |
| CPS-4 | Lifecycle protection  | Cleanup can delete active checkpoint dependencies | Checkpoints are retained but do not protect references       | Active checkpoints protect run/manifest/effective-config dependencies    |
| CPS-5 | Operator visibility   | No checkpoint diagnostics                         | CLI lists checkpoints only                                   | Diagnostics correlate checkpoints with manifest/control-plane evidence   |

### Lineage Completeness

| ID    | Criterion          | 0                                      | 1                                         | 2                                                                              |
| ----- | ------------------ | -------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------ |
| LIN-1 | Fragment identity  | Lineage fragments are path-only        | Fragment IDs exist without closure rules  | Stored and semantic fragment IDs are persisted and indexed                     |
| LIN-2 | Run correlation    | Lineage cannot resolve run context     | Some fragments include run IDs            | Lineage resolves run/manifest context for supported families                   |
| LIN-3 | Sidecar anchors    | Sidecars omit control-plane anchors    | Selected sidecars include partial anchors | Sidecars include manifest, ledger, config, and lineage anchors where supported |
| LIN-4 | Supported boundary | All families imply same evidence level | Boundary is documented but not enforced   | Unsupported families cap forensic-grade scoring                                |
| LIN-5 | Drift tests        | No lineage contract drift tests        | Unit tests cover stores                   | Contract tests cover supported lineage closure behavior                        |

### Replay Readiness

| ID    | Criterion               | 0                                                  | 1                                                                | 2                                                                           |
| ----- | ----------------------- | -------------------------------------------------- | ---------------------------------------------------------------- | --------------------------------------------------------------------------- |
| REP-1 | Immutable input refs    | Replay depends on live data                        | Cached inputs exist without strict manifest refs                 | Exact replay requires persisted immutable input snapshots                   |
| REP-2 | Snapshot portability    | Snapshot identity uses local path/mtime            | Content hash exists but identity still includes locator metadata | Snapshot identity is content-addressed and locator metadata is supplemental |
| REP-3 | Effective config replay | Replay uses current config implicitly              | Config artifact exists but is optional                           | Replay-ready manifests anchor effective-config semantic artifacts           |
| REP-4 | Replay classification   | Composite/source replay capabilities are conflated | Replay boundary is documented                                    | Run manifests classify exact, resume-only, and rebuild-only capability      |
| REP-5 | Fail-closed behavior    | Missing replay evidence falls back to live sources | Missing evidence emits warning                                   | Missing required evidence blocks exact replay                               |

### Layer Consistency

| ID    | Criterion                | 0                                      | 1                                      | 2                                                                               |
| ----- | ------------------------ | -------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------------- |
| LAY-1 | Domain/application split | Runtime logic owns persistence details | Some seams are layered                 | Domain DTOs, application services, and infrastructure adapters remain separated |
| LAY-2 | Composition wiring       | CLI/runtime constructs stores ad hoc   | Composition exists but bypasses remain | CLI/runtime use composition/bootstrap seams for control-plane collaborators     |
| LAY-3 | Storage layout           | Storage paths are undocumented         | Paths documented without tests         | Storage layout is documented and guarded by contract tests                      |
| LAY-4 | Operational docs         | Operators rely on code reading         | Partial CLI docs exist                 | Runbooks describe dry-run/apply, recovery, and safety constraints               |
| LAY-5 | Governance checks        | Audit scores are free-form             | Rubric exists without freshness tests  | Rubric and evidence surfaces are guarded by doc/architecture checks             |

## Evidence Matrix

| Criterion range | Evidence type     | Current evidence                                                                                                                                                                   |
| --------------- | ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DET-1..DET-5    | Code/tests        | `src/bioetl/domain/normalization/`, `tests/architecture/test_reproducibility_docs_contract_drift.py`, `tests/integration/ci/test_reproducibility_contract_suite.py`                |
| IDE-1..IDE-5    | Code/tests/docs   | Medallion writer suites, lifecycle planner tests, `docs/05-operations/control-plane-lifecycle.md`                                                                                  |
| RID-1..RID-5    | Code/tests/docs   | `src/bioetl/domain/control_plane/run_manifest.py`, `tests/unit/infrastructure/control_plane/test_file_run_manifest_store.py`, `docs/04-reference/contracts/run-manifest-ledger.md` |
| CPS-1..CPS-5    | Code/tests/docs   | checkpoint compatibility service tests, lifecycle checkpoint protection tests, CLI checkpoint docs                                                                                 |
| LIN-1..LIN-5    | Code/tests/docs   | `FileLineageStore`, reproducibility contract suite, run-manifest contract lineage section                                                                                          |
| REP-1..REP-5    | Code/tests/docs   | cached Bronze snapshot tests, exact replay integration test, snapshot identity contract docs                                                                                       |
| LAY-1..LAY-5    | Architecture/docs | architecture tests, CLI docs, lifecycle runbook, this rubric                                                                                                                       |

## Criterion Evidence Index

| Criterion | Code path                                                                  | Test/doc/issue evidence                                                         | Missing evidence note                              |
| --------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | -------------------------------------------------- |
| DET-1     | `src/bioetl/domain/normalization/`                                         | `tests/architecture/test_normalization_surface_coverage_ratchet.py`             | None                                               |
| DET-2     | `src/bioetl/domain/control_plane/run_manifest.py`                          | `tests/integration/ci/test_reproducibility_contract_suite.py`                   | None                                               |
| DET-3     | storage writer ordering helpers                                            | `tests/integration/ci/test_reproducibility_contract_suite.py`                   | None                                               |
| DET-4     | `src/bioetl/domain/control_plane/run_manifest.py`                          | `docs/04-reference/contracts/run-manifest-ledger.md`                            | None                                               |
| DET-5     | architecture contract tests                                                | `tests/architecture/test_reproducibility_docs_contract_drift.py`                | None                                               |
| IDE-1     | Medallion writer merge/upsert paths                                        | storage writer unit suites                                                      | None                                               |
| IDE-2     | `src/bioetl/application/services/checkpoint/checkpoint_compatibility_service.py` | checkpoint compatibility unit suites                                       | None                                               |
| IDE-3     | `src/bioetl/infrastructure/control_plane/`                                 | run manifest, ledger, lineage, and effective-config store tests                 | None                                               |
| IDE-4     | `src/bioetl/infrastructure/control_plane/file_artifact_lifecycle_store.py` | `tests/unit/infrastructure/control_plane/test_file_artifact_lifecycle_store.py` | None                                               |
| IDE-5     | resilience/retry helpers                                                   | resilience and adapter tests                                                    | Missing: one consolidated retry identity audit row |
| RID-1     | `src/bioetl/domain/control_plane/run_manifest.py`                          | `tests/unit/infrastructure/control_plane/test_file_run_manifest_store.py`       | None                                               |
| RID-2     | run manifest fingerprint builders                                          | run manifest service tests                                                      | None                                               |
| RID-3     | effective-config artifact services                                         | effective-config artifact store tests                                           | None                                               |
| RID-4     | cached Bronze snapshot ref builders                                        | cached Bronze snapshot tests                                                    | None                                               |
| RID-5     | run manifest replay parent fields                                          | run manifest inspection/diff tests                                              | None                                               |
| CPS-1     | checkpoint compatibility service                                           | checkpoint compatibility service tests                                          | None                                               |
| CPS-2     | checkpoint state and context helpers                                       | checkpoint facade and service tests                                             | None                                               |
| CPS-3     | composite checkpoint state                                                 | composite checkpoint unit suites                                                | None                                               |
| CPS-4     | lifecycle store checkpoint protection                                      | lifecycle store tests and control-plane lifecycle runbook                       | None                                               |
| CPS-5     | checkpoint CLI and diagnostics services                                    | CLI checkpoint and diagnostics tests                                            | None                                               |
| LIN-1     | `FileLineageStore`                                                         | lineage store and reproducibility contract tests                                | None                                               |
| LIN-2     | run manifest inspection lineage helpers                                    | reproducibility contract suite                                                  | None                                               |
| LIN-3     | lineage metadata assemblers and sidecars                                   | sidecar/linkage contract tests                                                  | None                                               |
| LIN-4     | reproducibility profile resolver                                           | replay profile diagnostics tests                                                | None                                               |
| LIN-5     | lineage closure contract tests                                             | `tests/integration/ci/test_reproducibility_contract_suite.py`                   | None                                               |
| REP-1     | cached Bronze exact replay bootstrap                                       | exact replay integration tests                                                  | None                                               |
| REP-2     | `RunInputSnapshotRef` and cached Bronze snapshot builders                  | cached Bronze snapshot identity tests                                           | None                                               |
| REP-3     | effective-config artifact anchors                                          | effective-config artifact store and manifest tests                              | None                                               |
| REP-4     | `ReplayCapability` and reproducibility profiles                            | run manifest diagnostics tests                                                  | None                                               |
| REP-5     | exact replay fail-closed checks                                            | exact replay integration and CLI tests                                          | None                                               |
| LAY-1     | domain/application/infrastructure packages                                 | architecture layer tests                                                        | None                                               |
| LAY-2     | composition/bootstrap CLI/runtime modules                                  | CLI and composition tests                                                       | None                                               |
| LAY-3     | storage layout docs and store adapters                                     | run-manifest ledger contract drift test                                         | None                                               |
| LAY-4     | operations runbooks and CLI docs                                           | control-plane lifecycle runbook and CLI docs                                    | None                                               |
| LAY-5     | rubric governance checks                                                   | `tests/architecture/test_reproducibility_docs_contract_drift.py`                | None                                               |

## Score Update Rules

- Recalculate scores after any P0/P1 reproducibility remediation changes.
- A criterion cannot score `2` unless code, tests, and docs all support it.
- A criterion with failing or skipped required tests scores at most `1`.
- Unsupported replay families can score at most `8/10` for Replay Readiness and
  at most `7/10` for Lineage Completeness.
- Audit reports MUST cite criterion IDs instead of free-form point awards.
