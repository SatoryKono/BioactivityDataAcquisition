# [governance] Register missing ChEMBL Gold contracts

**Status**: deferred_by_priority
**Priority**: P2 (Medium)
**Labels**: `governance`, `configs`, `testing`
**Epic**: ChEMBL Normalization and DQ Alignment 2026Q2
**Last audited**: 2026-05-08

> Repo-aligned completion (2026-05-08): the contract registry now covers the
> full active ChEMBL Gold surface with published artifacts and dedicated
> integration tests for registry/path/DQ identity consistency.

## Problem

The contract registry activates only part of the ChEMBL Gold contract surface.
Gold contract modules exist in code, but registry coverage is incomplete for
family-wide governance.

## Evidence

- `configs/base/contract_registry.yaml`
- `src/bioetl/domain/contracts/gold/chembl.py`
- `src/bioetl/domain/contracts/gold/_chembl_*`
- `docs/04-reference/contracts/gold/`

## Required Outcome

- Every active ChEMBL Gold-producing entity has a registry entry or explicit
  documented exclusion.
- Registry entries include owner, source path, artifact path, version, schema
  hash, and policy references.
- Published contract docs exist for registered entries.

## Implementation Plan

1. Expand `configs/base/contract_registry.yaml` for uncovered active ChEMBL
   Gold entities.
2. Add missing published contract artifacts under
   `docs/04-reference/contracts/gold/`.
3. Ensure `src/bioetl/domain/contracts/gold/chembl.py` exports the registered
   schema classes through the canonical facade.
4. Add registry coverage and published-path tests.

## Done When

- Registry coverage tests pass.
- All registry source paths exist.
- All published artifacts exist.
- Gold strict validation remains enabled.

## Dependencies

- Should follow the P0/P1 contract-affecting fixes so unstable semantics are
  not published as canonical truth.
