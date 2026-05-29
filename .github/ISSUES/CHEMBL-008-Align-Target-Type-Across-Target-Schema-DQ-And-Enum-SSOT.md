# [dq] Align target_type across target schema, DQ and enum SSOT

**Status**: active
**Priority**: P0 (Critical)
**Labels**: `dq`, `configs`, `testing`, `governance`
**Epic**: ChEMBL Normalization and DQ Alignment 2026Q2
**Last audited**: 2026-05-08

> Repo-aligned completion (2026-05-08): `target_type` now uses one governed set
> across `configs/enums/chembl.yaml`, schema constants, target profile, DQ, and
> parity tests.

## Problem

`chembl_target.target_type` differs across DQ, enum SSOT/schema constants, and
profile governance.

## Evidence

- `configs/entities/chembl/target.yaml`
- `configs/enums/chembl.yaml`
- `src/bioetl/domain/normalization/profiles/chembl_target.py`
- `src/bioetl/domain/schemas/constants.py`
- `src/bioetl/domain/schemas/chembl/target.py`

## Required Outcome

- `target_type` values are identical across SSOT, schema constants, profile,
  and DQ, or DQ is explicitly declared as a subset.
- Invalid values are quarantined or rejected according to DQ policy.

## Implementation Plan

1. Confirm canonical target type set in `configs/enums/chembl.yaml`.
2. Align `target_type.allowed` in `configs/entities/chembl/target.yaml`.
3. Align schema constants and profile enum usage.
4. Add accepted/rejected profile cases and parity tests.

## Done When

- `target_type` parity tests pass.
- Target DQ validates profile-normalized values.
- Unit, integration, and architecture tests pass.

## Dependencies

- `CHEMBL-013` should enforce this class of drift after the concrete fix lands.
