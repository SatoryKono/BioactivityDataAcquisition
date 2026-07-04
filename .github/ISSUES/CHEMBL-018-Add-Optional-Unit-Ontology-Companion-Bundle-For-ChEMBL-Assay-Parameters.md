# [normalization] Add optional unit ontology companion bundle for `chembl_assay_parameters`

**Status**: completed_in_repo
**Priority**: P1 (High)
**Labels**: `provider:chembl`, `governance`, `data-quality`, `schema-evolution`, `config`
**Epic**: ChEMBL Normalization Residuals 2026Q2
**Last audited**: 2026-05-19

## Problem

`chembl_assay_parameters` already shares token-level canonical unit
normalization with `chembl_activity`, but it does not publish the reviewed
UO/QUDT ontology companion bundle that activity surfaces already expose.

That leaves cross-pipeline asymmetry:

- unit tokens are deterministic across both bioactivity-like pipelines;
- ontology-backed meaning, mapping status, and ontology version remain visible
  on `chembl_activity` only;
- the gap is explicitly documented in governance config rather than being an
  accidental omission.

This is a reviewed boundary today, but the 2026-05-19 audit concluded it should
be converted into a focused additive decision instead of remaining an implicit
parity gap.

## Evidence

- `reports/quality/chembl_normalization_audit_2026-05-19.md`
- `configs/vocab/chembl_ontology.yaml`
- `src/bioetl/domain/normalization/profiles/chembl_activity.py`
- `src/bioetl/domain/normalization/profiles/chembl_assay_parameters.py`
- `configs/entities/chembl/assay_parameters.yaml`
- `src/bioetl/domain/schemas/chembl/assay_parameters.py`

## Current Fact Base

- `chembl_activity` publishes reviewed unit ontology companion fields including
  UO/QUDT identifiers, IRIs, mapping status, and ontology version metadata.
- `chembl_assay_parameters` canonicalizes `units` and `standard_units` tokens
  but does not emit ontology companion sidecars.
- `configs/vocab/chembl_ontology.yaml` explicitly documents
  `chembl_assay_parameters` as
  `standard_unit_only_no_ontology_companion_bundle`.
- The audit did not identify a current determinism defect; it identified a
  semantic parity gap between two closely related ChEMBL unit-bearing surfaces.

## Required Outcome

- The repo makes a reviewed additive choice for `chembl_assay_parameters` unit
  ontology semantics.
- If approved, assay parameters gain the same optional UO/QUDT-style companion
  bundle shape as activity-like unit surfaces.
- If rejected, the boundary remains explicit and mechanically enforced as an
  intentional asymmetry.

## Implementation Plan

1. Confirm the desired governance posture for assay-parameter unit ontology
   companions.
2. If the bundle is approved, add profile-owned companion fields and registry
   metadata for unit ontology mapping.
3. Extend schema, DQ, and Gold contract surfaces additively.
4. Refresh matrix and docs so assay-parameter unit semantics no longer require
   manual interpretation.
5. If persisted row shape changes, make contract/version and backfill decisions
   explicit.

## Suggested File Targets

- `src/bioetl/domain/normalization/profiles/chembl_assay_parameters.py`
- `configs/vocab/chembl_ontology.yaml`
- `configs/entities/chembl/assay_parameters.yaml`
- `src/bioetl/domain/schemas/chembl/assay_parameters.py`
- Gold contract exports for `chembl_assay_parameters`
- generated artifacts under `docs/reports/generated/`

## Testing Expectations

- Add ontology-companion regression tests for assay-parameter unit fields.
- Extend DQ/profile parity tests with mapping-status expectations.
- Re-run schema/contract snapshot tests for `chembl_assay_parameters`.
- Re-run normalization matrix generation tests.
- If companion fields become hash-relevant, add explicit hash-transition
  coverage.

## Documentation Updates

- Update ChEMBL assay-parameters provider docs under
  `docs/04-reference/providers/chembl/`.
- Refresh generated normalization matrix artifacts under
  `docs/reports/generated/`.
- Document the final posture in `configs/vocab/chembl_ontology.yaml` comments
  and any corresponding architecture/governance notes.

## Done When

- Assay-parameter unit ontology semantics are no longer a silent parity gap.
- The final reviewed posture is visible in profile, config, schema, and docs.
- Any additive contract or hash impact is versioned and regression-tested.

## Dependencies

- Follow-up residual issue from `reports/quality/chembl_normalization_audit_2026-05-19.md`.
