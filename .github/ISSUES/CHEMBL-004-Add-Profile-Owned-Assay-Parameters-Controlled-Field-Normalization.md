# [normalization] Add profile-owned assay_parameters controlled-field normalization

**Status**: active
**Priority**: P0 (Critical)
**Labels**: `dq`, `configs`, `refactor`, `testing`
**Epic**: ChEMBL Normalization and DQ Alignment 2026Q2
**Last audited**: 2026-05-08

> Repo-aligned completion (2026-05-08): `chembl_assay_parameters` now keeps
> controlled-field ownership in the domain profile for `type`,
> `standard_type`, `standard_relation`, and `standard_units`; DQ aligns to the
> same governed sets and the transformer no longer owns semantic vocabulary
> normalization.

## Problem

`chembl_assay_parameters` has controlled fields that are not normalized through
its domain profile. Semantic canonicalization is partly transformer-local and
partly missing.

## Evidence

- `src/bioetl/application/pipelines/chembl/assay_parameters_transformer.py`
- `src/bioetl/domain/normalization/profiles/chembl_assay_parameters.py`
- `configs/entities/chembl/assay_parameters.yaml`
- `src/bioetl/domain/schemas/chembl/assay_parameters.py`
- `configs/enums/chembl.yaml`

## Required Outcome

- `type` normalization is profile-owned.
- `relation` / `standard_relation` use shared operator normalization.
- `units` / `standard_units` use shared ChEMBL unit normalization.
- `standard_type` aligns with ChEMBL enum SSOT.
- Transformer no longer owns semantic canonicalization.

## Implementation Plan

1. Extend `configs/enums/chembl.yaml` with assay-parameter controlled sets.
2. Add controlled fields to
   `src/bioetl/domain/normalization/profiles/chembl_assay_parameters.py`.
3. Remove semantic ownership from
   `src/bioetl/application/pipelines/chembl/assay_parameters_transformer.py`.
4. Expand DQ validation in `configs/entities/chembl/assay_parameters.yaml`.
5. Add profile and transformer tests for type/operator/unit normalization and
   canonical JSON comments handling.

## Done When

- Profile tests cover controlled fields above.
- Transformer tests prove semantic normalization is not transformer-local.
- DQ validates canonical values.
- Hash golden tests prove replay stability.
- Unit, integration, and architecture tests pass.

## Dependencies

- Depends on `CHEMBL-006` for canonical unit spelling.
