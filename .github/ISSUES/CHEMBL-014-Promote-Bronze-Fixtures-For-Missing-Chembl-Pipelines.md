# [testing] Promote Bronze fixtures for missing chembl pipelines

**Status**: Completed ✅
**Priority**: P2 (Medium)
**Labels**: `testing`, `governance`, `configs`
**Epic**: ChEMBL Normalization and DQ Alignment 2026Q2
**Last audited**: 2026-05-08

> Repo-aligned completion (2026-05-08): the ChEMBL Bronze fixture manifest now
> covers all active `chembl_*` pipelines with tracked CI samples, and the gap
> registry is expected to stay empty under integration coverage.

## Problem

Most `chembl_*` pipelines still lack tracked Bronze fixture samples, which
blocks complete observed-value inventory and enum validation from repository
data.

## Evidence

- `configs/base/bronze_fixture_manifest.yaml`
- `configs/base/bronze_fixture_gaps.yaml`
- `tests/fixtures/bronze/chembl/activity/`
- `tests/fixtures/bronze/chembl/molecule/`
- `tests/fixtures/vcr/`

## Required Outcome

- Every active `chembl_*` pipeline has a bounded tracked Bronze fixture or
  explicit waiver.
- Fixture manifest and gaps registry are aligned.
- Fixture-derived observed-value inventory can run offline in CI.

## Implementation Plan

1. Promote raw Bronze fixtures for uncovered active ChEMBL pipelines.
2. Register all promoted fixtures in
   `configs/base/bronze_fixture_manifest.yaml`.
3. Resolve or explicitly waive active ChEMBL gaps in
   `configs/base/bronze_fixture_gaps.yaml`.
4. Add a test ensuring every active ChEMBL config has a fixture or waiver.

## Done When

- Manifest contains a tracked fixture or waiver for every active ChEMBL
  pipeline.
- Gap file has no unresolved active ChEMBL gaps.
- CI can run fixture-based normalization tests without network.
- Bronze fixtures remain raw JSONL.

## Dependencies

- Should follow the P0 normalization fixes.
