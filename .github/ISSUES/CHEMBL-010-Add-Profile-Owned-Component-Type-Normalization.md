# [normalization] Add profile-owned component_type normalization

**Status**: completed_in_repo
**Priority**: P0 (Critical)
**Labels**: `dq`, `configs`, `testing`
**Epic**: ChEMBL Normalization and DQ Alignment 2026Q2
**Last audited**: 2026-05-08

> Repo-aligned completion (2026-05-08): `component_type` is profile-governed in
> `CHEMBL_TARGET_COMPONENT_PROFILE`, sourced from SSOT enum config, aligned with
> DQ, and covered by enum parity tests.

## Problem

`chembl_target_component.component_type` is validated in DQ but not normalized
through the target-component profile or enum SSOT.

## Evidence

- `configs/entities/chembl/target_component.yaml`
- `src/bioetl/domain/normalization/profiles/chembl_target_component.py`
- `src/bioetl/domain/schemas/chembl/target_component.py`
- `configs/enums/chembl.yaml`

## Required Outcome

- `component_type` is governed by the target-component profile.
- Allowed values are defined in `configs/enums/chembl.yaml`.
- DQ/profile/schema use the same canonical set.

## Implementation Plan

1. Add `target_component.component_types` to `configs/enums/chembl.yaml`.
2. Export schema-facing constants if needed.
3. Add `component_type` to the target-component profile.
4. Align DQ allowed values in `configs/entities/chembl/target_component.yaml`.
5. Add profile normalization tests and parity tests.

## Done When

- `component_type` profile tests pass.
- DQ/profile/SSOT parity tests pass.
- Casing variants normalize deterministically.
- Unit, integration, and architecture tests pass.

## Dependencies

- Related to `CHEMBL-013`.
