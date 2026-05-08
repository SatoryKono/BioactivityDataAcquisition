# [dq] Align publication_term derived contract

**Status**: Completed ✅
**Priority**: P0 (Critical)
**Labels**: `dq`, `configs`, `testing`, `governance`
**Epic**: ChEMBL Normalization and DQ Alignment 2026Q2
**Last audited**: 2026-05-08

> Repo-aligned completion (2026-05-08): current repo state already aligns the
> derived `publication_term` contract. DQ uses `^[a-f0-9]{16}$`, runtime emits
> only `MESH_HEADING` / `MESH_QUALIFIER` / `KEYWORD`, the schema/profile use the
> same enum set, and dedicated profile/runtime/policy tests are present.

## Problem

`chembl_publication_term` is internally inconsistent: runtime emits one
`term_type` contract, schema/DQ allow a different set, and DQ expects a
64-char hash while implementation uses a 16-char deterministic hex prefix.

## Evidence

- `configs/entities/chembl/publication_term.yaml`
- `src/bioetl/application/core/publication_term_runtime.py`
- `src/bioetl/application/core/entity_id.py`
- `src/bioetl/application/pipelines/chembl/publication_term_transformer.py`
- `src/bioetl/domain/normalization/profiles/chembl_publication_term.py`
- `src/bioetl/domain/schemas/chembl/publication_term.py`

## Required Outcome

- `term_type` set is identical across runtime, schema, profile, and DQ.
- Canonical active set is `MESH_HEADING`, `MESH_QUALIFIER`, `KEYWORD`.
- DQ `entity_id` regex matches implementation: `^[a-f0-9]{16}$`.
- `term_type` becomes profile-governed.

## Implementation Plan

1. Update `configs/entities/chembl/publication_term.yaml`:
   - change `entity_id` regex to 16 lowercase hex chars
   - align `term_type.allowed`
   - remove unsupported values from this derived pipeline
2. Align enum values in `src/bioetl/domain/schemas/chembl/publication_term.py`.
3. Add `term_type` normalization to
   `src/bioetl/domain/normalization/profiles/chembl_publication_term.py`.
4. Keep the 16-char deterministic ID contract in
   `src/bioetl/application/core/entity_id.py` and document it explicitly.
5. Add parity and normalization tests in config, profile, and runtime suites.

## Done When

- DQ/schema/profile `term_type` sets are identical.
- Runtime extraction tests pass.
- 16-char `entity_id` contract is covered by tests.
- Architecture tests pass.
- Identical Bronze publication input produces the same `entity_id` and
  `content_hash` across replay.

## Dependencies

None.
