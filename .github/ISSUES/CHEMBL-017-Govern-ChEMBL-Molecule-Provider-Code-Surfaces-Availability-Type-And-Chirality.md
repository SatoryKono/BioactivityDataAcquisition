# [normalization] Govern ChEMBL molecule provider-code surfaces `availability_type` and `chirality`

**Status**: Draft
**Priority**: P1 (High)
**Labels**: `provider:chembl`, `governance`, `data-quality`, `config`, `technical-debt`
**Epic**: ChEMBL Normalization Residuals 2026Q2
**Last audited**: 2026-05-19

## Problem

`chembl_molecule.availability_type` and `chembl_molecule.chirality` are already
observed in repo evidence as provider-code surfaces, but the shipped profile
still treats them as generic numeric fields.

That leaves a governance gap:

- Bronze observed-value inventory already tracks these fields explicitly;
- the profile applies numeric coercion only, with no reviewed code-universe or
  explicit "intentionally open numeric" declaration;
- DQ/config layers do not express the same posture, so the fields sit outside
  the normal enum-aware ChEMBL SSOT flow.

This is the clearest remaining ChEMBL provider-code seam that can still affect
semantic stability and future `content_hash` migrations if late canonicalization
is introduced ad hoc.

## Evidence

- `reports/quality/chembl_normalization_audit_2026-05-19.md`
- `tests/fixtures/normalization/chembl_bronze_observed_value_inventory_snapshot.json`
- `src/bioetl/domain/normalization/profiles/chembl_molecule.py`
- `configs/entities/chembl/molecule.yaml`
- `src/bioetl/domain/schemas/chembl/molecule.py`
- `docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md`

## Current Fact Base

- Bronze observed-value snapshot tracks `availability_type` values `-1` and
  `2`, and `chirality` values `1` and `2`.
- `chembl_molecule` profile treats `availability_type` as float-like and
  `chirality` as int-like, with no special provider-code governance.
- Current entity config exposes both fields in business data, but no explicit
  reviewed-code DQ policy was found for them.
- The 2026-05-19 audit did not conclude that they must become strict enums; it
  concluded that the repo needs an explicit reviewed posture instead of silent
  numeric pass-through.

## Required Outcome

- `availability_type` and `chirality` become first-class reviewed provider-code
  surfaces in the ChEMBL normalization layer.
- The repo explicitly chooses one posture per field:
  - governed reviewed code universe; or
  - intentionally non-governed open numeric provider code.
- Profile, DQ, fixtures, and generated matrix all surface the same decision.

## Implementation Plan

1. Review observed repo values and current ChEMBL schema references for both
   fields.
2. Introduce a reviewed provider-code registry entry or explicit waiver posture.
3. Route both fields through profile-owned reviewed semantics instead of generic
   numeric fallthrough.
4. Align DQ/config posture with the chosen governance model.
5. Refresh generated matrix/governance artifacts so the field classification is
   explicit.
6. If canonical output changes, document the resulting hash/migration impact.

## Suggested File Targets

- `src/bioetl/domain/normalization/profiles/chembl_molecule.py`
- `configs/enums/chembl.yaml`
- `configs/vocab/chembl_controlled.yaml`
- `configs/entities/chembl/molecule.yaml`
- `tests/fixtures/normalization/chembl_observed_values.yaml`
- `tests/integration/config/test_chembl_enum_parity.py`
- generated artifacts under `docs/reports/generated/`

## Testing Expectations

- Extend ChEMBL enum/policy parity coverage with explicit assertions for
  `availability_type` and `chirality`.
- Add observed-value regression cases covering provider numeric/string variants.
- Re-run cross-layer normalization contract coverage for `chembl_molecule`.
- If canonical output changes, add hash-regression coverage that makes the
  migration explicit.

## Documentation Updates

- Update ChEMBL molecule provider reference docs under
  `docs/04-reference/providers/chembl/`.
- Refresh generated normalization matrix artifacts under
  `docs/reports/generated/`.
- If a reviewed "open numeric" posture is chosen, document that explicitly in
  the corresponding governance doc/config comments.

## Done When

- Both fields no longer rely on silent generic numeric semantics.
- Repo artifacts make the reviewed governance posture explicit.
- DQ/profile/matrix/fixture parity exists for the chosen posture.
- Any hash-affecting behavior is documented and regression-tested.

## Dependencies

- Follow-up residual issue from `reports/quality/chembl_normalization_audit_2026-05-19.md`.
