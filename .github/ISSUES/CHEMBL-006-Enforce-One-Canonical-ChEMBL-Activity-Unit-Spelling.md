# [normalization] Enforce one canonical ChEMBL activity unit spelling

**Status**: Completed ✅
**Priority**: P0 (Critical)
**Labels**: `dq`, `configs`, `testing`
**Epic**: ChEMBL Normalization and DQ Alignment 2026Q2
**Last audited**: 2026-05-08

> Repo-aligned completion (2026-05-08): activity `standard_units` now use one
> canonical unit policy in domain normalization, DQ validates the same enum, and
> contract tests explicitly cover alias collapse such as `uM -> µM`.

## Problem

`chembl_activity.standard_units` canonicalization conflicts across
profile/helper and DQ/config. Equivalent unit spellings are not governed by one
policy.

## Evidence

- `src/bioetl/domain/normalization/chembl.py`
- `src/bioetl/domain/normalization/profiles/chembl_activity.py`
- `configs/entities/chembl/activity.yaml`
- `configs/composites/activity.yaml`
- `src/bioetl/application/pipelines/chembl/activity_transformer.py`

## Required Outcome

- One canonical spelling policy exists for ChEMBL units.
- DQ validates the same unit spelling emitted by profile.
- Activity and composite configs use canonical units for normalized-layer
  filters.
- Bronze payload remains raw.

## Implementation Plan

1. Keep and document pure canonicalization in
   `src/bioetl/domain/normalization/chembl.py`.
2. Align `configs/enums/chembl.yaml` and
   `configs/entities/chembl/activity.yaml` with canonical profile output.
3. Ensure `configs/composites/activity.yaml` uses canonical normalized units.
4. Add alias-to-canonical unit tests and hash-stability tests for equivalent
   spellings.

## Done When

- Unit normalization tests pass.
- DQ accepts profile output.
- Equivalent unit spellings produce identical hash input.
- Composite activity tests pass.
- Architecture tests pass.

## Dependencies

- Blocks `CHEMBL-004`.
