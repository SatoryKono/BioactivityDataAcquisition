# [dq] Align tissue ontology DQ patterns with canonical IDs

**Status**: Completed ✅
**Priority**: P0 (Critical)
**Labels**: `dq`, `configs`, `testing`
**Epic**: ChEMBL Normalization and DQ Alignment 2026Q2
**Last audited**: 2026-05-08

> Repo-aligned completion (2026-05-08): tissue DQ patterns now validate
> canonical normalized ontology IDs (`BTO_`, `EFO_`, `UBERON_`), the tissue
> profile owns ontology companion normalization, and cross-layer tests cover the
> canonical form.

## Problem

`chembl_tissue` profile canonicalizes ontology IDs, but DQ validates a
different representation. Normalized Silver values and DQ regexes disagree.

## Evidence

- `configs/entities/chembl/tissue.yaml`
- `src/bioetl/domain/normalization/profiles/chembl_tissue.py`
- `src/bioetl/domain/normalization/identifiers.py`
- `src/bioetl/domain/schemas/chembl/tissue.py`
- `configs/composites/assay.yaml`

## Required Outcome

- DQ patterns accept the canonical ID representation emitted by the profile.
- Tissue ontology fields are consistent across profile, schema, DQ, and
  composite assay output.
- Bronze remains raw.

## Implementation Plan

1. Update `bto_id`, `efo_id`, and `uberon_id` regex patterns in
   `configs/entities/chembl/tissue.yaml` to match profile output.
2. Keep normalization pure in `chembl_tissue.py`.
3. Add profile tests for colon-to-canonical conversions.
4. Add config tests proving DQ regex accepts profile output and rejects
   non-canonical post-normalization forms.
5. Add or update composite assay tests confirming canonical tissue ontology IDs.

## Done When

- Tissue profile tests pass.
- Tissue DQ accepts canonical profile output.
- Composite assay tests pass.
- Architecture tests pass.
- Identical Bronze tissue input produces stable normalized IDs and hash.

## Dependencies

None.
