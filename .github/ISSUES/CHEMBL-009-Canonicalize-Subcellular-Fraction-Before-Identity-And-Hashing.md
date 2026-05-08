# [normalization] Canonicalize subcellular_fraction before identity and hashing

**Status**: Completed ✅
**Priority**: P0 (Critical)
**Labels**: `dq`, `technical-debt`, `testing`
**Epic**: ChEMBL Normalization and DQ Alignment 2026Q2
**Last audited**: 2026-05-08

> Repo-aligned completion (2026-05-08): subcellular-fraction extraction now
> normalizes the label before record creation and entity-id generation, and
> contract tests cover hash/id stability for equivalent casing and ontology-like
> variants.

## Problem

`chembl_subcellular_fraction` computes identity from a canonicalized label but
stores and hashes a different label representation. Case-only variants can
share `entity_id` but diverge in `content_hash`.

## Evidence

- `src/bioetl/application/core/_subcellular_fraction_support.py`
- `src/bioetl/application/pipelines/chembl/subcellular_fraction_transformer.py`
- `src/bioetl/domain/normalization/profiles/chembl_subcellular_fraction.py`
- `configs/entities/chembl/subcellular_fraction.yaml`

## Required Outcome

- Canonical label is used before both ID generation and content hash.
- Case-only variants do not create false versions.
- Raw value is retained only if an explicit schema migration is approved.

## Implementation Plan

1. Add a pure canonical label helper in
   `src/bioetl/application/core/_subcellular_fraction_support.py`.
2. Use the canonical label in both `compute_entity_id` and
   `create_fraction_record`.
3. Ensure profile output matches helper output.
4. Add equivalence and hash golden tests for case and whitespace variants.

## Done When

- Casing variants produce the same `entity_id`.
- Casing variants produce the same hash input.
- No false SCD2 versions are created for case-only differences.
- Unit, integration, and architecture tests pass.

## Dependencies

None.
