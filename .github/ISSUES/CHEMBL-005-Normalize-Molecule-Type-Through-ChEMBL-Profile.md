# [normalization] Normalize molecule_type through ChEMBL profile

**Status**: active
**Priority**: P0 (Critical)
**Labels**: `dq`, `configs`, `testing`
**Epic**: ChEMBL Normalization and DQ Alignment 2026Q2
**Last audited**: 2026-05-08

> Repo-aligned completion (2026-05-08): `molecule_type` is profile-governed in
> `CHEMBL_MOLECULE_PROFILE`, backed by SSOT schema constants and parity tests
> against `configs/enums/chembl.yaml` and DQ config.

## Problem

`chembl_molecule.molecule_type` is constrained by schema/DQ but not normalized
through the molecule profile.

## Evidence

- `configs/entities/chembl/molecule.yaml`
- `src/bioetl/domain/normalization/profiles/chembl_molecule.py`
- `src/bioetl/domain/schemas/chembl/molecule.py`
- `src/bioetl/domain/schemas/constants.py`
- `configs/enums/chembl.yaml`

## Required Outcome

- `molecule_type` is profile-governed.
- DQ allowed values match ChEMBL enum SSOT or an explicit declared subset.
- Hash input uses canonical `molecule_type`.

## Implementation Plan

1. Confirm canonical molecule type set in `configs/enums/chembl.yaml`.
2. Align schema-facing constants if needed.
3. Add `molecule_type` to
   `src/bioetl/domain/normalization/profiles/chembl_molecule.py`.
4. Align DQ allowed values in `configs/entities/chembl/molecule.yaml`.
5. Add profile and parity tests for molecule type normalization.

## Done When

- `molecule_type` is profile-governed.
- DQ/profile/SSOT parity test passes.
- Hash tests cover casing and spelling normalization.
- Unit, integration, and architecture tests pass.

## Dependencies

- Related to `CHEMBL-013`, but can be implemented before it.
