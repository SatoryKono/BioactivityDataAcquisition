# [dq] Align activity standard_type with ChEMBL enum SSOT

**Status**: completed_in_repo
**Priority**: P0 (Critical)
**Labels**: `dq`, `configs`, `testing`, `governance`
**Epic**: ChEMBL Normalization and DQ Alignment 2026Q2
**Last audited**: 2026-05-08

> Repo-aligned completion (2026-05-08): `activity.standard_type` is already
> aligned across enum SSOT, schema constants, profile governance, DQ config, and
> integration/contract parity tests.

## Problem

`chembl_activity.standard_type` is normalized as enum-like, but DQ allowed
values drift from the ChEMBL enum SSOT and schema/profile contract.

## Evidence

- `configs/entities/chembl/activity.yaml`
- `configs/enums/chembl.yaml`
- `src/bioetl/domain/normalization/profiles/chembl_activity.py`
- `src/bioetl/domain/schemas/constants.py`
- `src/bioetl/domain/schemas/chembl/activity.py`

## Required Outcome

- `standard_type` DQ allowed set is exact SSOT match or explicit subset.
- Profile, schema constants, and DQ use the same canonical values.
- Existing normalization remains deterministic.

## Implementation Plan

1. Replace or document `standard_type.allowed` in
   `configs/entities/chembl/activity.yaml`.
2. Confirm canonical activity standard type set in `configs/enums/chembl.yaml`.
3. Align schema constants and profile enum usage.
4. Add DQ/profile/schema/SSOT parity tests and accepted/rejected profile cases.

## Done When

- DQ/profile/schema/SSOT parity tests pass.
- Activity profile tests pass.
- Composite activity tests pass.
- Unit, integration, and architecture tests pass.

## Dependencies

- `CHEMBL-013` should enforce this class of drift after the concrete fix lands.
