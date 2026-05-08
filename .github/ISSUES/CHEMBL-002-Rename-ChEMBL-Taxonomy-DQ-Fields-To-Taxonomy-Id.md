# [dq] Rename ChEMBL taxonomy DQ fields to taxonomy_id

**Status**: Completed ✅
**Priority**: P0 (Critical)
**Labels**: `dq`, `configs`, `testing`
**Epic**: ChEMBL Normalization and DQ Alignment 2026Q2
**Last audited**: 2026-05-08

> Repo-aligned completion (2026-05-08): target and target_component DQ now
> validate canonical Silver field `taxonomy_id`, while provider extraction
> params correctly keep ChEMBL API syntax such as `tax_id__isnull`.

## Problem

`chembl_target` and `chembl_target_component` DQ rules validate `tax_id`,
while normalized Silver fields are `taxonomy_id`.

## Evidence

- `configs/entities/chembl/target.yaml`
- `configs/entities/chembl/target_component.yaml`
- `src/bioetl/domain/normalization/profiles/chembl_target.py`
- `src/bioetl/domain/normalization/profiles/chembl_target_component.py`
- `src/bioetl/domain/schemas/chembl/target.py`
- `src/bioetl/domain/schemas/chembl/target_component.py`

## Required Outcome

- DQ rules validate `taxonomy_id` for target and target_component.
- Provider API query params may stay `tax_id` where that is ChEMBL syntax.
- Silver schema, profile, and DQ use the same canonical field name.

## Implementation Plan

1. Rename DQ validation fields from `tax_id` to `taxonomy_id` in:
   - `configs/entities/chembl/target.yaml`
   - `configs/entities/chembl/target_component.yaml`
2. Leave provider API filters untouched.
3. Add config tests asserting DQ validation fields exist in Silver schema for
   both pipelines.

## Done When

- DQ validates `taxonomy_id`.
- Config tests fail if a DQ field is absent from Silver schema and not
  explicitly API-only.
- Unit, integration, and architecture tests pass.

## Dependencies

None.
