# [normalization] Canonicalize PubChem CID before identity, hashing, and composite boundaries

**Status**: active
**Priority**: P0 (Critical)
**Labels**: `provider:pubchem`, `governance`, `data-quality`, `schema-evolution`, `technical-debt`, `composite`
**Epic**: Non-ChEMBL Normalization Residuals 2026Q2
**Last audited**: 2026-05-19

## Problem

`pubchem_compound.molecule_id` is already treated in repo evidence as a
canonicalizable PubChem CID surface, but the reusable normalization profile
still treats it as generic text.

That creates a governance mismatch:

- fixture evidence already expects `CID:2244` and `2244` to normalize to the
  same canonical value;
- the profile does not define a dedicated PubChem CID canonicalizer;
- composite molecule keeps PubChem-specific normalized anchors explicit, but
  `molecule_id` is not yet a governed identity family.

This is now the clearest remaining non-ChEMBL identifier gap that can affect
identity, `content_hash`, replay explanation, and future composite-boundary
activation decisions.

## Evidence

- `reports/quality/non_chembl_normalization_audit_2026-05-19.md`
- `src/bioetl/domain/normalization/profiles/pubchem_compound.py`
- `tests/fixtures/normalization/non_chembl_observed_values.yaml`
- `configs/entities/pubchem/compound.yaml`
- `src/bioetl/domain/normalization/join_keys.py`
- `configs/composites/molecule.yaml`
- `docs/reports/generated/pipeline_normalization_field_matrix/non_chembl_normalization_field_matrix.md`

## Current Fact Base

- `pubchem_compound` has dedicated profile rules for `canonical_smiles`,
  `isomeric_smiles`, `inchi_key`, and `standardized_inchi_key`, but not for
  `molecule_id`.
- `tests/fixtures/normalization/non_chembl_observed_values.yaml` already
  contains `CID:2244` and `2244` examples with normalized expectation `2244`.
- `configs/entities/pubchem/compound.yaml` requires `molecule_id`, but does not
  constrain it as a canonical PubChem CID format.
- `configs/composites/molecule.yaml` documents active joins on `inchi_key` and
  `canonical_smiles`, while PubChem-only normalized anchors remain retained
  validation surfaces.

## Required Outcome

- PubChem CID becomes a first-class canonical identifier family in the
  non-ChEMBL normalization layer.
- `molecule_id` normalization, DQ, contracts, and fixtures agree on the same
  canonical semantics.
- Any resulting hash drift is explicit, versioned, and migration-ready.

## Implementation Plan

1. Introduce a dedicated PubChem CID canonicalizer in the shared
   reference-identifier seam.
2. Route `pubchem_compound.molecule_id` through that canonicalizer in the
   profile layer.
3. Tighten DQ/config posture for canonical PubChem CID formatting.
4. Refresh matrix/governance artifacts so the new identifier family is visible.
5. Decide whether composite molecule should remain `inchi_key`-centric only, or
   whether CID should be documented as a non-join identity anchor explicitly.
6. If normalization output changes for persisted rows, document and implement
   migration/backfill behavior.

## Suggested File Targets

- `src/bioetl/domain/normalization/reference_ids.py`
- `src/bioetl/domain/normalization/profiles/profile_normalizers.py`
- `src/bioetl/domain/normalization/profiles/pubchem_compound.py`
- `configs/entities/pubchem/compound.yaml`
- `tests/fixtures/normalization/non_chembl_observed_values.yaml`
- `tests/contract/test_non_chembl_cross_layer_contract_matrix.py`
- `configs/composites/molecule.yaml`
- generated artifacts under `docs/reports/generated/`

## Testing Expectations

- Extend `tests/contract/test_non_chembl_cross_layer_contract_matrix.py` to
  assert PubChem CID parity across fixture, profile, config, and matrix rows.
- Add or extend PubChem identifier normalization regression tests under
  `tests/integration/normalization/`.
- Re-run `tests/unit/scripts/test_generate_pipeline_normalization_field_matrix.py`.
- Re-run PubChem contract/E2E slices that persist or compare `molecule_id`.
- If `content_hash` changes, add golden/regression coverage that makes the hash
  transition explicit.

## Documentation Updates

- Update `docs/03-data-model/reference-identifier-families.md` with the PubChem
  CID family.
- Update PubChem provider reference docs under
  `docs/04-reference/providers/pubchem/`.
- Refresh generated matrix/governance artifacts under
  `docs/reports/generated/`.
- If hash semantics change materially, update the relevant normalization or
  replay/change-management docs.

## Done When

- `molecule_id` no longer falls through generic text semantics.
- Fixtures, DQ, and profile output all agree on canonical PubChem CID behavior.
- Any hash-impacting behavior is documented and regression-tested.
- Composite molecule docs explicitly describe the role of PubChem CID relative
  to `inchi_key` and retained validation anchors.

## Dependencies

- Independent P0 issue.
