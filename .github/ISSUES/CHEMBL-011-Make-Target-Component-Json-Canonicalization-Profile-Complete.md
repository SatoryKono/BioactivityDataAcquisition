# [dq] Make target_component JSON canonicalization profile-complete

**Status**: Completed ✅
**Priority**: P1 (High)
**Labels**: `dq`, `testing`, `technical-debt`
**Epic**: ChEMBL Normalization and DQ Alignment 2026Q2
**Last audited**: 2026-05-08

> Repo-aligned completion (2026-05-08): target-component JSON-like fields are
> governed through strict profile JSON policy and ADR-035-aligned tests; the
> schema stays string-based for business JSON surfaces and normalization contract
> coverage is in place.

## Problem

`chembl_target_component` transformer serializes JSON-like fields that are not
all declared as JSON fields in the normalization profile. ADR-035 compliance is
therefore incomplete and hash stability is at risk.

## Evidence

- `src/bioetl/application/pipelines/chembl/target_component_transformer.py`
- `src/bioetl/domain/normalization/profiles/chembl_target_component.py`
- `src/bioetl/domain/schemas/chembl/target_component.py`
- `configs/entities/chembl/target_component.yaml`
- `docs/02-architecture/decisions/ADR-035-json-field-typing-policy.md`

## Required Outcome

- Every JSON-like target_component field is declared in the profile.
- Canonical JSON serialization is applied before hashing.
- No native list or dict reaches Silver/Gold business fields.

## Implementation Plan

1. Add missing JSON string fields to the target-component profile.
2. Remove duplicate ad-hoc canonicalization in the transformer if profile owns
   it fully.
3. Confirm schema types remain nullable strings for JSON-like business fields.
4. Add stable-key-order and equivalent-structure tests.

## Done When

- JSON profile completeness tests pass.
- Transformer does not emit native list/dict into Silver business data.
- Equivalent JSON structures hash identically.
- ADR-035 tests pass.

## Dependencies

- Can follow `CHEMBL-010`.
