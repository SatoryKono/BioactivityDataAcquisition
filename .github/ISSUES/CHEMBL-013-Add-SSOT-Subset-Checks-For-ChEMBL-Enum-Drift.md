# [governance] Add SSOT subset checks for ChEMBL enum drift

**Status**: Completed ✅
**Priority**: P1 (High)
**Labels**: `governance`, `configs`, `testing`, `technical-debt`
**Epic**: ChEMBL Normalization and DQ Alignment 2026Q2
**Last audited**: 2026-05-08

> Repo-aligned completion (2026-05-08): enum SSOT/subset governance is already
> enforced by shipped integration and contract tests, including
> `test_chembl_enum_parity.py`, `test_chembl_policy_surface_parity.py`, and
> `test_chembl_enum_normalization_policy.py`.

## Problem

ChEMBL enum values are externalized, but DQ configs, schema constants, and
normalization profiles are not mechanically checked for exact or subset parity.

## Evidence

- `configs/enums/chembl.yaml`
- `src/bioetl/domain/schemas/constants.py`
- `src/bioetl/domain/normalization/profiles/chembl_*`
- `configs/entities/chembl/*.yaml`
- `docs/02-architecture/decisions/ADR-038-enum-externalization.md`

## Required Outcome

- CI fails when DQ enum values do not match SSOT or declared subset.
- CI fails when profile enum fields lack SSOT mapping or explicit waiver.
- Waivers are field-scoped and machine-readable.

## Implementation Plan

1. Add an architecture/governance parity test loading SSOT, entity configs,
   schema constants, and profile enum metadata.
2. Add subset metadata where a real subset policy is intended.
3. Expose profile enum metadata in a pure, introspectable way if current
   profile objects do not surface it clearly.
4. Update ADR-038 with CI enforcement notes.

## Done When

- New parity test fails on artificial enum drift fixtures.
- Test passes after concrete enum fixes land.
- Every governed DQ enum list has SSOT mapping or explicit waiver.
- CI includes the new check.

## Dependencies

- Depends on `CHEMBL-001`, `CHEMBL-005`, `CHEMBL-007`, `CHEMBL-008`,
  `CHEMBL-010`, and `CHEMBL-012`.
