# [contracts] Promote structured-field contract typing and hash governance

**Status**: active
**Priority**: P1 (High)
**Labels**: `contracts`, `normalization`, `hashing`, `governance`
**Epic**: Non-ChEMBL Normalization Governance 2026Q2
**Last audited**: 2026-05-19

## Problem

Many non-ChEMBL structured fields are governed and canonically serialized, but
their Gold contracts still expose them only as `Series[str]` without a more
explicit governance distinction between:

- raw JSON payload
- canonical JSON payload
- semantic projection field

This is contract-safe syntactically, but it weakens auditability of which
representation is hash-relevant and which is replay/debug evidence only.

## Evidence

- `src/bioetl/domain/contracts/gold/publications_openalex.py`
- `src/bioetl/domain/contracts/gold/publications_semanticscholar.py`
- `src/bioetl/domain/contracts/gold/publications_crossref.py`
- `src/bioetl/domain/contracts/gold/uniprot.py`
- `src/bioetl/domain/normalization/structured_payload_policies.py`
- `src/bioetl/domain/normalization/hash_identity.py`

## Current Fact Base

- The hash layer already supports canonical JSON deterministically.
- Several profiles already exclude raw-sidecar fields from hash identity.
- Contract typing does not yet make hash-relevant vs evidence-only payloads
  consistently obvious.

## Required Outcome

- Structured non-ChEMBL fields have explicit contract posture.
- Hash-excluded raw-sidecar fields are documented and test-backed.
- Gold surfaces make it clear which payload form is authoritative for analytics
  and which is retained for forensics.

## Implementation Plan

1. Inventory structured non-ChEMBL fields with raw/canonical/evidence roles.
2. Add contract-level documentation and, where needed, field companions that
   reflect those roles explicitly.
3. Publish or generate a per-entity hash-exclusion inventory.
4. Add regression tests proving raw evidence changes do not perturb
   content-hash when policy says they should not.
5. Reconcile generated contract and normalization artifacts so typed/evidence
   posture is visible outside source code.

## Suggested File Targets

- `src/bioetl/domain/contracts/gold/publications_openalex.py`
- `src/bioetl/domain/contracts/gold/publications_semanticscholar.py`
- `src/bioetl/domain/contracts/gold/publications_crossref.py`
- `src/bioetl/domain/contracts/gold/uniprot.py`
- `src/bioetl/domain/normalization/hash_identity.py`
- `src/bioetl/domain/normalization/profiles/`
- generated docs under `docs/reports/generated/`

## Testing Expectations

- Extend `tests/contract/test_non_chembl_cross_layer_contract_matrix.py` so
  structured-field posture is asserted as one of:
  - canonical-only
  - raw+canonical dual-field
  - semantic projection
- Extend `tests/architecture/test_non_chembl_json_field_typing_policy.py` to
  reflect the updated contract posture.
- Extend `tests/unit/application/core/test_non_chembl_normalization_hash_golden.py`
  so hash-excluded evidence fields are verified explicitly.
- Re-run provider contract suites for every changed Gold surface:
  - `tests/contract/test_crossref_contract.py`
  - `tests/contract/test_openalex_contract.py`
  - `tests/contract/test_pubmed_contract.py`
  - `tests/contract/test_semanticscholar_contract.py`
  - `tests/contract/test_uniprot_contract.py`
- Re-run `tests/unit/scripts/test_generate_pipeline_normalization_field_matrix.py`
  because the matrix already reports structured-field and hash-governance
  semantics.

## Documentation Updates

- Update `docs/03-data-model/json-field-typing-inventory.md` to reflect the
  final raw/canonical/evidence contract posture.
- Update the affected contract JSON references under
  `docs/04-reference/contracts/gold/`.
- Refresh generated governance artifacts under:
  - `docs/reports/generated/pipeline_normalization_field_matrix/`
  - `docs/reports/generated/pipeline_normalization_validation_table/`
- If hash-exclusion policy becomes part of contributor guidance, update the
  relevant normalization plan entry in
  `docs/05-engineering/normalization_plan_P0_P6.md`.

## Done When

- Structured-field contract posture is explicit across the audited
  non-ChEMBL families.
- Hash-relevant and hash-excluded payload fields are documented and testable.
- Replay/debug evidence fields are distinguishable from canonical analytical
  fields in Gold surfaces.
- Generated docs and contract exports expose the same distinction.

## Dependencies

- Depends on `NONCHEMBL-001`.
