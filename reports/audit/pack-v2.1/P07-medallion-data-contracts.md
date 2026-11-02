# P07. Medallion, storage semantics и data contracts

## A. Audit Manifest
- **Audit ID:** pack-v2.1/P07
- **Pinned Revision (SHA):** a5243cb4bbed67b267daecdc097b8c48501e140a
- **Date/Time:** 2026-11-02 (simulated)
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
| E1-MEDALLION-POLICY | STATIC | CURRENT | `src/bioetl/domain/medallion.py` |
| E2-CONTRACT-REGISTRY-YAML | STATIC | CURRENT | `configs/base/contract_registry.yaml` |
| E2-CONTRACT-REGISTRY-CODE | STATIC | CURRENT | `src/bioetl/domain/control_plane/contract_registry.py` and related files |
| E2-STORAGE-WRITERS | STATIC | CURRENT | `src/bioetl/infrastructure/storage/gold_writer.py`, `src/bioetl/infrastructure/storage/silver_writer.py` |

## D. Findings Register

### Finding 1: Incomplete or Missing Domain Contract Registry Tests
- **finding_id:** P07-CONTRACT-REGISTRY-001
- **root_cause_id:** rc-contract-registry-test-coverage
- **owner_prompt:** P07
- **concern:** Contract registry and ledger invariants are governance-critical but lack sufficient test coverage. Running `pytest tests/domain/control_plane/test_contract_registry.py` fails with "No such file or directory". This was also highlighted in previous tech debt audits.
- **severity:** P2 (Maintainability/test debt without proven P0/P1 impact).
- **confidence:** high
- **status:** CONFIRMED
- **expected:** Comprehensive unit tests for `src/bioetl/domain/control_plane/contract_registry*.py`.
- **actual:** No dedicated tests found in `tests/domain/control_plane/` for the contract registry.
- **evidence_ids:** E2-CONTRACT-REGISTRY-CODE, E3 (pytest execution result).
- **attempted_disproof:** Searched for `test_contract_registry.py` and related files using `find` and `grep`. Tests exist in `integration/config/` but domain invariant tests are missing.
- **exceptions_checked:** Checked known debt issues; it was flagged before but apparently not fully resolved or regressions occurred.
- **impact:** Risk of silent breaks in governance-critical contract registry logic.
- **root_cause:** Missing test implementations for domain control plane.
- **recommendation:** Implement unit tests covering contract registry parsing, validation, and invariants in `tests/unit/domain/control_plane/`.
- **scope / non-goals:** Add unit tests. Do not refactor the registry implementation itself.
- **acceptance_criteria:** `pytest tests/unit/domain/control_plane/` passes and covers `contract_registry*.py`.
- **verification command/test:** `pytest tests/unit/domain/control_plane/ --cov=src/bioetl/domain/control_plane`
- **dependencies:** None.
- **related_findings:** None.

## E. Quantitative Scorecard
- **Bronze Contract/Semantics:** 4 (Strong implementation, clear append-only policy in `medallion.py`). (Evidence: E1-MEDALLION-POLICY)
- **Silver Contract/Semantics:** 4 (Merge/Append policies enforced, clear lifecycle). (Evidence: E1-MEDALLION-POLICY)
- **Gold Contract/Semantics:** 3 (Policy exists, schemas defined, but domain registry test coverage is lacking). (Evidence: E1-MEDALLION-POLICY, E2-CONTRACT-REGISTRY-CODE, E2-CONTRACT-REGISTRY-YAML)
- **Contract Registry:** 2 (Implementation exists, configuration mapped, but domain test coverage is missing). (Evidence: E2-CONTRACT-REGISTRY-CODE, E2-CONTRACT-REGISTRY-YAML)

## F. Cross-cutting/root-cause clusters
- **Cluster 1:** Control Plane Domain Coverage. The domain logic for the contract registry lacks dedicated unit testing, making it vulnerable to accidental structural changes.

## G. Prioritized roadmap P0→P3
1. **P2:** Implement missing domain unit tests for `contract_registry*.py` and related types.

## H. Verification Matrix
| Component | Contract/Invariant | Verified | Evidence |
| :--- | :--- | :--- | :--- |
| Bronze | Append-only mode | Yes | E1-MEDALLION-POLICY |
| Silver | Merge/Append modes | Yes | E1-MEDALLION-POLICY |
| Gold | Append/SCD2/Overwrite modes | Yes | E1-MEDALLION-POLICY |
| Gold | Schema Registry Alignment | Partial | Registry config exists, but domain logic untested. |

## I. NOT_VERIFIABLE и missing evidence
- E2E Replay exactness (P11 scope, deferred).
- Physical Delta schema drift on actual production storage (requires external access).

## J. Self-check
- Findings are grounded in static and executable evidence.
- Severity matches impact definition.
- No changes made to repository code.

## K. Verdict
The Medallion layer policies are well-defined in the domain (`bioetl.domain.medallion`). Write modes are strictly categorized. However, the domain implementation of the Contract Registry (`bioetl.domain.control_plane.contract_registry*.py`) suffers from a lack of dedicated unit tests, representing a P2 debt that needs addressing to ensure governance stability.

---
## Issue drafts

**Title:** [TDX-AUDIT-009] Add domain contract registry and ledger invariant tests
**Body:**
### Provenance
- **Audit ID:** pack-v2.1/P07
- **Audited SHA:** a5243cb4bbed67b267daecdc097b8c48501e140a
- **Root Cause ID:** rc-contract-registry-test-coverage
- **Source Finding IDs:** P07-CONTRACT-REGISTRY-001
- **Severity:** P2
- **Confidence:** high
- **Status:** CONFIRMED

### Problem
Contract registry and ledger invariants are governance-critical but lack sufficient test coverage in the domain layer.

### Evidence
- File: `src/bioetl/domain/control_plane/contract_registry*.py`
- Test failure: `pytest tests/unit/domain/control_plane/test_contract_registry.py` reports "No such file or directory".

### Expected vs Actual
**Expected:** Comprehensive unit tests for `contract_registry*.py` ensuring domain invariants.
**Actual:** Missing test files in the domain test suite.

### Impact
Risk of silent breaks in governance-critical contract registry logic, affecting downstream pipeline validation.

### Scope / Non-goals
Add unit tests. Do not refactor the registry implementation itself.

### Architecture Constraints
Must follow existing testing patterns, isolated from I/O (pure domain tests).

### Implementation outline
1. Create `tests/unit/domain/control_plane/test_contract_registry.py` and `test_contract_registry_helpers.py`.
2. Write tests covering initialization, validation, and policy checks using standard `pytest` assertions.

### Acceptance Criteria
- Domain tests added for contract registry components.
- Tests pass locally and in CI.
- Coverage for `src/bioetl/domain/control_plane/contract_registry*.py` increases.

### Verification Commands
`uv run pytest tests/unit/domain/control_plane/`
`uv run pytest --cov=src/bioetl/domain/control_plane tests/unit/domain/control_plane/`

### Dependencies
None.

### Rollback/Risk
Low risk, test-only addition.

## P07 Local Output

### Field-Level Drift Matrix
**Status:** NOT_VERIFIABLE
**Reason:** Physical schema checks on actual persisted Bronze/Silver tables require environment access to Delta tables, which is not available in static repo-only mode.

### Registry Completeness
**Status:** Partial (Configured, but domain verified untested).
**Details:** `configs/base/contract_registry.yaml` contains 27 valid entries, primarily covering `chembl` and some generic datasets. Ownership matrices indicate it covers pipeline paths. Domain-level tests for `contract_registry*.py` are missing (see P07-CONTRACT-REGISTRY-001).

### Version-Transition Matrix
**Status:** NOT_VERIFIABLE
**Reason:** Historical schema migrations and fixtures required to track old version -> new version paths are not locally executable without external databases or specific archived `fixtures/` sets not surfaced during this run.

### Layer Commit/Recovery Matrix (Partial-Failure Matrix)
**Status:** NOT_VERIFIABLE
**Reason:** Assessing Bronze commit -> Silver failure -> recovery requires live pipeline run metadata or execution of integration tests with forced failures (`tests/integration/` network access).

### Migration / Replay Risks
- Replay impact assessment is bounded by P11.
- Migration testing on local data lacks the external schema drift inputs to verify data loss or type coercion during upgrades.
