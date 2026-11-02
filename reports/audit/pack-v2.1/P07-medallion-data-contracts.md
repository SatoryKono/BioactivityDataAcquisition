# P07. Medallion, storage semantics и data contracts

## A. Audit Manifest
- **Audit ID:** pack-v2.1/P07
- **Pinned Revision (SHA):** a5243cb4bbed67b267daecdc097b8c48501e140a
- **Date/Time:** 2026-11-02 (simulated); findings re-evaluated 2026-11-02 after Devin/Codex/CodeRabbit review (wrong test path disproof + local recovery matrix + recorded validation commands).
- **Scope:** Bronze/Silver/Gold contracts, writers/readers, validators, schema/contract registry.
- **Environment:** Ubuntu (Sandbox), Python 3.13 / uv.
- **Evidence Mode:** REPO_ONLY / RUNTIME_ALLOWED.
- **Exceptions/Limitations:** No access to external APIs or remote databases; static and local test execution only. Read-only mode for codebase. Write mode authorized for report generation only.

## B. Scope/ownership и exclusions
- **In Scope:** `src/bioetl/domain/medallion.py`, `src/bioetl/application/services/medallion/`, `src/bioetl/domain/control_plane/contract_registry*.py`, `src/bioetl/infrastructure/storage/`, `configs/base/contract_registry.yaml`, `src/bioetl/domain/contracts/gold/`.
- **Exclusions:** Data quality rule evaluation logic (P09 territory), Replay engine inner workings (P11 territory).

## C. Evidence Ledger

| Evidence ID | Class | Freshness | Source/Command |
| :--- | :--- | :--- | :--- |
| E1-MEDALLION-POLICY | STATIC | CURRENT | `src/bioetl/domain/medallion.py` (`WriteMode`, `SilverWriteMode`, `GoldWriteMode`, `WriteModePolicy`) |
| E2-CONTRACT-REGISTRY-YAML | STATIC | CURRENT | `configs/base/contract_registry.yaml` |
| E2-CONTRACT-REGISTRY-CODE | STATIC | CURRENT | `src/bioetl/domain/control_plane/contract_registry.py` and related files |
| E2-CONTRACT-REGISTRY-TESTS | STATIC + LOCAL_TEST | CURRENT | `tests/unit/domain/control_plane/test_contract_registry.py`, `test_contract_registry_invariants.py`, `test_contract_registry_service_additional.py` (present at pinned SHA; executed — see Validation Evidence) |
| E2-STORAGE-WRITERS | STATIC | CURRENT | `src/bioetl/infrastructure/storage/gold_writer.py`, `src/bioetl/infrastructure/storage/silver_writer.py` (import/enforce domain modes; not a runtime write proof) |
| E3-SILVER-FAIL-GOLD-BLOCK | LOCAL_TEST | CURRENT | `tests/unit/application/core/test_batch_processing_support.py::test_write_silver_gold_concurrent_stops_on_silver_failure` (+ `test_write_silver_gold_skips_gold_when_silver_quarantined`) |
| E3-BATCH-RESUME | LOCAL_TEST | CURRENT | `tests/unit/application/core/test_batch_executor_recovery.py::TestBatchExecutorRecoveryInvariants::test_failure_and_resume_preserves_exactly_all_records` (FakeDataSource + in-memory checkpoint + mock storage) |
| E3-SILVER-MERGE-REPLAY | LOCAL_TEST | CURRENT | `tests/integration/infrastructure/storage/test_silver_merge_replay.py` (local Delta temp path; idempotent merge checksum + metadata-rerun business-column stability) |
| E4-CLEANUP-INVENTORY | LOCAL_CMD | CURRENT | `python -m scripts.docs generate-cleanup-inventory --update` / `--check` (see Validation Evidence) |

## D. Findings Register

### Finding 1: Incomplete or Missing Domain Contract Registry Tests — DISPROVED
- **finding_id:** P07-CONTRACT-REGISTRY-001
- **root_cause_id:** rc-contract-registry-test-coverage
- **owner_prompt:** P07
- **concern:** Earlier draft claimed contract-registry domain tests were missing because `pytest tests/domain/control_plane/test_contract_registry.py` failed with "No such file or directory".
- **severity:** n/a (retracted)
- **confidence:** high
- **status:** DISPROVED
- **expected:** Dedicated unit tests for `src/bioetl/domain/control_plane/contract_registry*.py` under the canonical domain unit-test tree.
- **actual:** Tests exist at the pinned SHA under `tests/unit/domain/control_plane/`:
  - `test_contract_registry.py` (exports smoke)
  - `test_contract_registry_invariants.py` (deterministic issue ordering, rebind stability, registry hash, gold/run-manifest/run-ledger golden fixtures)
  - `test_contract_registry_service_additional.py` (parse/validation coverage)
- **evidence_ids:** E2-CONTRACT-REGISTRY-CODE, E2-CONTRACT-REGISTRY-TESTS
- **attempted_disproof:** Re-checked paths on pinned revision `a5243cb4bb`. Wrong path `tests/domain/...` does not exist; correct path `tests/unit/domain/control_plane/` contains the three modules above. The earlier "No such file" result was a path error, not missing coverage. Re-ran the correct suite (Validation Evidence V1).
- **exceptions_checked:** No separate proven gap remains for "missing domain registry unit tests" after path correction. Residual coverage depth (breadth of edge cases) was not measured as a new CONFIRMED debt here.
- **impact:** None for the original claim; scorecard/verdict updated accordingly.
- **root_cause:** Auditor used a non-canonical test path (`tests/domain/...` instead of `tests/unit/domain/...`).
- **recommendation:** Do not open an Issue to recreate existing tests. Any future coverage work must cite measured gaps against the existing suite.
- **scope / non-goals:** Retract false debt only. Do not delete or rewrite existing tests in this audit PR.
- **acceptance_criteria:** Finding status remains DISPROVED; no Issue draft for recreating existing files.
- **verification command/test:** see Validation Evidence V1 (exit 0; 10 passed, 0 failed, 0 skipped).
- **dependencies:** None.
- **related_findings:** None.

No other CONFIRMED findings in this re-evaluation.

## E. Quantitative Scorecard
- **Bronze Contract/Semantics:** 4 (Strong domain policy: Bronze limited to append in `WriteModePolicy`). (Evidence: E1-MEDALLION-POLICY)
- **Silver Contract/Semantics:** 4 (Merge/Append enums + policy in domain). (Evidence: E1-MEDALLION-POLICY)
- **Gold Contract/Semantics:** 4 (Append/SCD2/Overwrite enums in domain; schemas + registry config present). (Evidence: E1-MEDALLION-POLICY, E2-CONTRACT-REGISTRY-CODE, E2-CONTRACT-REGISTRY-YAML)
- **Contract Registry:** 4 (Implementation + YAML mapping + dedicated domain unit tests at pinned SHA). (Evidence: E2-CONTRACT-REGISTRY-CODE, E2-CONTRACT-REGISTRY-YAML, E2-CONTRACT-REGISTRY-TESTS)

Scores above reflect **domain policy / registry / unit-test presence**. They do **not** certify that infrastructure writers applied those modes correctly at runtime against real storage.

## F. Cross-cutting/root-cause clusters
- **Cluster 1 (audit process):** Wrong test-path probes can mint false CONFIRMED debt. Prefer `tests/unit/domain/...` for domain control-plane modules.
- **Cluster 2 (evidence boundary):** Layer write-mode enums in `medallion.py` are not equivalent to end-to-end writer/storage proofs.

## G. Prioritized roadmap P0→P3
1. **P3 (optional, not CONFIRMED debt):** If deeper assurance is required, add focused writer/runtime evidence that Silver/Gold writers enforce domain modes on real Delta operations (out of static domain-test scope).

## H. Verification Matrix

| Component | Contract/Invariant | Verified | Evidence / boundary |
| :--- | :--- | :--- | :--- |
| Bronze | Append-only mode declared in domain policy | Yes (domain enum/policy only) | E1-MEDALLION-POLICY — proves `WriteModePolicy` allows Bronze=`append` only; does **not** prove Bronze writers/storage apply it |
| Silver | Merge/Append modes declared | Yes (domain enum/policy only) | E1-MEDALLION-POLICY — proves `SilverWriteMode` / policy; does **not** prove `SilverWriter` runtime application |
| Gold | Append/SCD2/Overwrite modes declared | Yes (domain enum only) | E1-MEDALLION-POLICY — proves `GoldWriteMode`; does **not** prove `GoldWriter` runtime application |
| Silver/Gold writers | Modes imported / policy hooks present | Partial (static) | E2-STORAGE-WRITERS — static import/`_enforce_write_policy` style signals only; no live Delta write proof in this audit |
| Gold | Schema Registry Alignment | Yes (config + domain tests) | E2-CONTRACT-REGISTRY-YAML, E2-CONTRACT-REGISTRY-CODE, E2-CONTRACT-REGISTRY-TESTS |

## I. NOT_VERIFIABLE и missing evidence
- E2E Replay exactness beyond Silver merge replay local proofs (broader P11 scope, deferred).
- Physical Delta schema drift on actual production storage (requires external access).
- Runtime proof that real writers/storage honor medallion write modes on **production** tables (local unit/integration ≠ prod).
- Prod/network partial-failure matrices that need live pipeline metadata or remote storage — **not** the same as the local recovery cases already covered by E3-*.

## J. Self-check
- Findings re-checked against correct test paths and evidence boundaries.
- No CONFIRMED finding remains for the false missing-tests claim.
- Severity/status match the disproof.
- No product-code changes in this audit PR beyond the report (and inventory rebind if required).
- Validation commands below are recorded with exit codes; no inferred passes.

## K. Verdict
The Medallion layer policies are well-defined in the domain (`bioetl.domain.medallion`): write-mode enums and `WriteModePolicy` categorize Bronze/Silver/Gold modes. **Verified: Yes** in the matrix for those rows means the modes are declared and constrained in `medallion.py`, not that infrastructure writers were runtime-proven against storage. The Contract Registry domain implementation has dedicated unit tests under `tests/unit/domain/control_plane/` at the pinned SHA; the earlier CONFIRMED P2 “missing domain tests” claim is **DISPROVED** (wrong path `tests/domain/...`). No replacement CONFIRMED debt is asserted without a separately measured gap.

---
## Issue drafts

**None.** The previous draft `[TDX-AUDIT-009] Add domain contract registry and ledger invariant tests` is **withdrawn**: the target files already exist at the pinned revision under `tests/unit/domain/control_plane/`. Do not recreate them from this audit.

## Validation Evidence (executed 2026-11-02, tip workspace at remediation)

| ID | Command | Exit | passed | failed | skipped |
| :--- | :--- | ---: | ---: | ---: | ---: |
| V1 | `uv run --frozen --no-build pytest -q tests/unit/domain/control_plane/test_contract_registry.py tests/unit/domain/control_plane/test_contract_registry_invariants.py tests/unit/domain/control_plane/test_contract_registry_service_additional.py --tb=no` | 0 | 10 | 0 | 0 |
| V2 | `uv run --frozen --no-build pytest -q tests/unit/application/core/test_batch_processing_support.py::test_write_silver_gold_concurrent_stops_on_silver_failure tests/unit/application/core/test_batch_processing_support.py::test_write_silver_gold_skips_gold_when_silver_quarantined --tb=no` | 0 | 2 | 0 | 0 |
| V3 | `uv run --frozen --no-build pytest -q tests/unit/application/core/test_batch_executor_recovery.py::TestBatchExecutorRecoveryInvariants::test_failure_and_resume_preserves_exactly_all_records --tb=no` | 0 | 1 | 0 | 0 |
| V4 | `uv run --frozen --no-build pytest -q tests/integration/infrastructure/storage/test_silver_merge_replay.py --tb=line` | 0 | 2 | 0 | 0 |
| V5 | `.venv/bin/python -m scripts.docs generate-cleanup-inventory --update` | 0 | n/a | n/a | n/a |
| V6 | `.venv/bin/python -m scripts.docs.checks.documentation_cleanup_inventory --check` | 0 | n/a | n/a | n/a |

V5 output: `[documentation-cleanup-inventory] inventory already synchronized` (no tree change).
V6 output: `[documentation-cleanup-inventory] inventory is synchronized`.

**declared_status tracking:** `_extract_declared_status` in `scripts/docs/checks/documentation_cleanup_inventory.py` reads only header-like lines starting with `Status:` / `status:` / `*Status:` in the first 1500 chars. Local body markers like `**Status:** NOT_VERIFIABLE` in P07 Local Output are **not** tracked as `declared_status`. Inventory entry for this report: `declared_status: null`, lifecycle `working_report`, status `Working`.

## P07 Local Output

### Field-Level Drift Matrix
**Status:** NOT_VERIFIABLE
**Reason:** Physical schema checks on actual persisted Bronze/Silver tables require environment access to Delta tables, which is not available in static repo-only mode.

### Registry Completeness
**Status:** Configured and domain-tested (static + V1).
**Details:** `configs/base/contract_registry.yaml` contains 27 valid entries, primarily covering `chembl` and some generic datasets. Ownership matrices indicate it covers pipeline paths. Domain-level unit tests for `contract_registry*.py` are present at `tests/unit/domain/control_plane/` (see DISPROVED P07-CONTRACT-REGISTRY-001; V1 exit 0).

### Version-Transition Matrix
**Status:** NOT_VERIFIABLE
**Reason:** Historical schema migrations and fixtures required to track old version -> new version paths are not locally executable without external databases or specific archived `fixtures/` sets not surfaced during this run.

### Layer Commit/Recovery Matrix (Partial-Failure Matrix)
**Status:** Partial (local unit/integration evidence; prod/network cases separated below).

| Scenario | Result | Evidence | Boundary |
| :--- | :--- | :--- | :--- |
| Silver write failure blocks Gold | Verified (V2 exit 0; 2 passed / 0 failed / 0 skipped) | E3-SILVER-FAIL-GOLD-BLOCK | Mock writer; proves orchestration does not await Gold after Silver raise / quarantine |
| Mid-batch failure + resume preserves all records (no dupes) | Verified (V3 exit 0; 1 passed / 0 failed / 0 skipped) | E3-BATCH-RESUME | FakeDataSource fail-at, in-memory checkpoint, mock storage — not live remote I/O |
| Silver merge replay idempotent by table checksum | Verified (V4 exit 0; 2 passed / 0 failed / 0 skipped for module) | E3-SILVER-MERGE-REPLAY | Local temp Delta path via `SilverWriter`; proves merge replay checksum stability |
| Metadata-only Silver rerun preserves business columns | Verified (same V4 run) | E3-SILVER-MERGE-REPLAY | Same local Delta harness |
| Bronze→Silver→Gold recovery against production / networked stores | NOT_VERIFIABLE here | — | Needs live pipeline metadata or remote Delta; do **not** collapse into the local rows above |

**Note:** Earlier draft marked this whole matrix NOT_VERIFIABLE due to “network access”. That was over-broad: the local tests above run without external network and already cover silver-fail/gold-block, batch resume, and silver merge replay.

### Migration / Replay Risks
- Broader replay impact assessment remains bounded by P11 beyond the local Silver merge replay proofs (E3-SILVER-MERGE-REPLAY).
- Migration testing on local data lacks the external schema drift inputs to verify data loss or type coercion during upgrades.
