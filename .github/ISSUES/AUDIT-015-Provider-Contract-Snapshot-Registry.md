# AUDIT-015: Ratchet provider contract snapshot registry without duplicating drift layer

## 1. Title
[testing] Ratchet provider contract snapshot registry without duplicating drift layer

## 2. Problem
The provider contract drift surface already exists and is marked as enforced in the fixture governance ledger, but governance documentation suggests it may need ratcheting against the matrix-declared provider baseline. The next work must ratchet the existing registry and tests, not create a parallel drift mechanism.

## 3. Evidence
- `configs/quality/fixture_governance_ledger.yaml`
  - `contract_snapshots.status: enforced` (line 57)
  - Evidence paths include all provider contract tests and fixtures
- `configs/quality/test_matrix.yaml`
- `tests/contract/_provider_contract_drift.py`
- `tests/contract/_provider_contract_replay.py`
- `tests/contract/test_provider_contract_snapshot_registry.py`
- `tests/contract/test_provider_contract_drift_replay.py`
- Provider-specific tests: `test_chembl_contract.py`, `test_crossref_contract.py`, `test_openalex_contract.py`, `test_pubchem_contract.py`, `test_pubmed_contract.py`, `test_semanticscholar_contract.py`, `test_uniprot_contract.py`
- `tests/fixtures/contracts/{provider}/v1.json`
- `.github/workflows/contract-tests.yml`
- `.github/workflows/provider-contract-drift.yml`

## 4. Root Cause
Provider contract drift governance is implemented and marked enforced, but may need verification that it fully covers the matrix-declared provider baseline with readable drift diagnostics.

## 5. Architectural Impact
- Reproducibility: provider snapshot baselines may drift without clear diagnostics
- Testing: current registry is active and enforced
- Governance: risk of duplicate drift systems if the existing surface is ignored
- Observability: drift reporting can become noisy or unreadable if not bounded

## 6. Required Outcome
The existing provider contract snapshot registry must be the single canonical drift surface. It must cover every provider in the enforced live-contract baseline and provide readable drift diagnostics without default live network requirements.

## 7. File-level Implementation Plan
### Changes
- `configs/quality/test_matrix.yaml`
  - Verify declared provider contract baseline matches active provider tests
  - Do not add providers without fixture and test evidence

- `configs/quality/fixture_governance_ledger.yaml`
  - Update contract_snapshots status only after registry coverage is proven
  - Preserve bounded_live_provider_baseline scope

- `tests/contract/test_provider_contract_snapshot_registry.py`
  - Assert every matrix-declared provider has:
    - fixture contract snapshot
    - provider-specific contract test module
    - required probe declarations
    - documented update path

- `tests/contract/_provider_contract_drift.py`
  - Improve diff readability if current diagnostics are not actionable
  - Keep comparisons bounded to stable envelopes/fields
  - Do not treat optional nullable fields as noisy failures unless policy says so

- `tests/contract/_provider_contract_replay.py`
  - Ensure replay mode runs without live network
  - Keep live-smoke path opt-in

- `tests/fixtures/contracts/README.md`
  - Document snapshot update workflow:
    - when to update
    - how to review diff
    - required env var
    - network opt-in policy

- `.github/workflows/provider-contract-drift.yml`
  - Ensure replay gate runs in CI without live network
  - Do not duplicate monthly live contract workflow

- `.github/workflows/contract-tests.yml`
  - Keep scheduled/manual live API workflow separate and opt-in

### Refactoring actions
- Consolidate around existing contract drift helpers
- Remove duplicate registry attempts if found
- Do not move provider drift checks into runtime orchestration

### Contracts impact
- Provider contract fixture governance changes
- No runtime data contract change
- No domain port change
- No DQ rule change

### Migration
- No production migration. Snapshot updates may be needed if current fixtures are stale

## 8. Constraints
Forbidden:
- runtime network probes in default tests
- provider drift checks inside domain
- duplicate snapshot registries
- noisy checks on optional provider fields
- high-cardinality metric labels
- weakening Gold strict validation
- changing Quarantine payload
- cyclic dependencies

## 9. Acceptance Criteria
- Every matrix-declared provider has a snapshot, test module, and required probe metadata
- Provider contract replay works without network
- Live contract tests remain scheduled/manual and opt-in
- Drift diffs are readable and scoped
- contract_snapshots ledger status is updated only with passing evidence
- Contract tests pass
- Architecture tests pass
- No duplicate drift layer is introduced

## 10. Priority
P1. Provider drift can break ingestion silently; the existing drift layer must be ratcheted instead of cloned.

## 11. Size
M. Mostly tests, config governance, and docs.

## 12. Labels
testing, governance, technical-debt

## 13. Dependencies
Depends on Issue 14 only if VCR metadata is required for contract replay diagnostics in the same release.
