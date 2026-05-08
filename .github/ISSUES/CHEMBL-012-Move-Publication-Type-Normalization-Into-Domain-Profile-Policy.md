# [normalization] Move publication_type normalization into domain profile policy

**Status**: Completed ✅
**Priority**: P1 (High)
**Labels**: `architecture`, `dq`, `refactor`, `testing`
**Epic**: ChEMBL Normalization and DQ Alignment 2026Q2
**Last audited**: 2026-05-08

> Repo-aligned completion (2026-05-08): the publication transformer now seeds
> raw provider publication type fields only, while canonical
> `publication_type` normalization is owned by `CHEMBL_PUBLICATION_PROFILE` and
> shared publication taxonomy rules.

## Problem

`chembl_publication.publication_type` canonicalization is transformer-owned
instead of profile-owned, so semantic policy is split between application and
domain normalization.

## Evidence

- `src/bioetl/application/pipelines/chembl/publication_transformer.py`
- `src/bioetl/domain/mapping/publication_type_mapping.py`
- `src/bioetl/domain/normalization/profiles/chembl_publication.py`
- `configs/entities/chembl/publication.yaml`
- `configs/enums/chembl.yaml`

## Required Outcome

- `publication_type` normalization becomes profile-owned.
- Transformer only extracts and maps raw source fields.
- DQ validates normalized output or explicitly documents subset policy.

## Implementation Plan

1. Add `publication_type` normalization rule to
   `src/bioetl/domain/normalization/profiles/chembl_publication.py`.
2. Remove direct semantic normalization calls from the publication transformer.
3. Align DQ `publication_type` validation with normalized output.
4. Add profile tests and transformer tests proving canonicalization is not
   transformer-local.

## Done When

- Profile owns `publication_type` canonicalization.
- Transformer tests prove no transformer-local semantic normalization.
- DQ validates the chosen canonical representation.
- Hash golden tests cover equivalent publication type spellings.

## Dependencies

- Should precede `CHEMBL-013`.
