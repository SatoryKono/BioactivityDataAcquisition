# Contract coverage matrix schema v3 (CR-02 / #6694)

**Date:** 2026-07-27  
**Linked issues:** #6694 (version/parity), #6693 (strict predicate)

## Change

Bump published artifact schema from `contract-coverage-matrix-v2` to
`contract-coverage-matrix-v3`.

### Semantics delta

`gold_contract_available` now requires **all** of:

1. contract YAML
2. registry entry
3. gold schema source path/file
4. published artifact (present, not missing)
5. Pandera contract declaration
6. **gold strict validation declaration** (new hard requirement for availability)

Runtime `gold_enabled` remains independent of availability.

## Migration

1. Regenerate with:
   `python -m scripts.engineering.qa report-contract-coverage-matrix`
2. Update consumers that pin `schema_version == contract-coverage-matrix-v2`
   to accept `v3`.
3. Re-evaluate dashboards/scripts that treated “Pandera declared” as “Gold contract available”.

## Rollback

1. Revert generator predicate and `schema_version` string to v2.
2. Restore prior `reports/quality/contract-coverage-matrix.{json,md}` from git.
3. Re-run architecture integrity tests for the matrix.

## ADR linkage

Follows project public-contract change policy (version bump + migration +
rollback). No new architectural boundary change; reporting semantics only.
