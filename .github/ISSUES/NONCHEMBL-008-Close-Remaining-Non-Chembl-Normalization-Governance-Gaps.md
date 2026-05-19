# [normalization] Close remaining non-ChEMBL normalization governance gaps

**Status**: Draft
**Priority**: P0/P1
**Labels**: `normalization`, `dq`, `contracts`, `testing`, `governance`
**Epic**: Non-ChEMBL Normalization Governance 2026Q2
**Last audited**: 2026-05-19

> This umbrella issue consolidates the confirmed non-ChEMBL normalization
> governance gaps from the current `main` audit. The underlying architecture is
> already largely deterministic and profile-owned; the remaining work is to
> close governance, replay, and composite-boundary gaps.

## Problem

The current non-ChEMBL stack is not missing a normalization framework. The
remaining work is narrower and more structural:

- UniProt semantic payload raw-sidecar coverage is incomplete;
- DQ does not fully mirror already-governed OA and identifier-array semantics;
- composite pipelines depend on normalized non-ChEMBL fields without enough
  explicit drift guards;
- vocabulary externalization maturity differs by provider family;
- structured-field Gold posture does not always distinguish canonical
  analytical payload from replay/debug evidence;
- observed-value inventory coverage remains partial.

## Evidence

- `configs/composites/publication.yaml`
- `configs/composites/molecule.yaml`
- `configs/composites/target.yaml`
- `configs/vocab/publication_controlled.yaml`
- `configs/vocab/publication_nested.yaml`
- `configs/vocab/uniprot_semantic_payloads.yaml`
- `src/bioetl/domain/normalization/structured_payload_policies.py`
- `src/bioetl/domain/normalization/hash_identity.py`
- `src/bioetl/domain/normalization/open_access.py`
- `src/bioetl/domain/normalization/profiles/openalex_publication.py`
- `src/bioetl/domain/normalization/profiles/semanticscholar_publication.py`
- `src/bioetl/domain/normalization/profiles/pubchem_compound.py`
- `src/bioetl/domain/normalization/profiles/uniprot_protein.py`
- `src/bioetl/domain/normalization/profiles/uniprot_idmapping.py`

## Required Outcome

- Non-ChEMBL normalization governance is consistent across publication,
  PubChem, UniProt, and composite boundaries.
- Replay/debug posture for structured semantic payloads is explicit.
- DQ, contracts, and profile policy agree on governed surfaces.
- Composite-critical normalized boundaries are regression-tested.

## Publish Order

### P0

1. `NONCHEMBL-001`
2. `NONCHEMBL-002`
3. `NONCHEMBL-003`

### P1

4. `NONCHEMBL-004`
5. `NONCHEMBL-005`
6. `NONCHEMBL-006`

### P2

7. `NONCHEMBL-007`

## Testing Expectations

- The umbrella is not complete until the targeted issue-level suites have been
  updated and the following shared governance tests are green:
  - `tests/contract/test_non_chembl_cross_layer_contract_matrix.py`
  - `tests/architecture/test_non_chembl_json_field_typing_policy.py`
  - `tests/integration/config/test_non_chembl_identifier_dq_parity.py`
  - `tests/integration/config/test_uniprot_semantic_payload_vocabulary_inventory.py`
  - `tests/unit/config/test_non_chembl_composite_boundary_policy.py`
  - `tests/unit/application/core/test_non_chembl_normalization_hash_golden.py`
  - `tests/unit/scripts/test_generate_pipeline_normalization_field_matrix.py`
- Provider-specific contract/E2E suites touched by the sub-issues must also be
  green before closeout.

## Documentation Updates

- Umbrella closeout must include refresh of the non-ChEMBL governance docs most
  directly affected by the sub-issues:
  - `docs/03-data-model/json-field-typing-inventory.md`
  - `docs/03-data-model/reference-identifier-families.md`
  - `docs/04-reference/pipelines/uniprot/01-protein-spec.md`
  - `docs/04-reference/pipelines/uniprot/protein-xwalk.csv`
  - publication provider reference docs under `docs/04-reference/providers/`
  - `docs/05-operations/verification/vcr-test-tasks.md`
  - generated artifacts under `docs/reports/generated/`
- If registry posture changes materially, include the corresponding ADR-038 or
  normalization-plan follow-up updates.

## Done When

- The P0 issues are complete and composite-critical non-ChEMBL normalized
  surfaces are protected against silent drift.
- Vocabulary and contract governance no longer differ arbitrarily by provider
  family.
- The repo can explain content-hash and structured-payload behavior from
  persisted artifacts and contracts.
- The shared non-ChEMBL docs and generated governance artifacts have been
  refreshed together with the code/config changes.

## Dependencies

- Follows the 2026-05-19 non-ChEMBL normalization audit.
