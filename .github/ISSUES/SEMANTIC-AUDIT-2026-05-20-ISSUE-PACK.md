# Semantic Audit 2026-05-20 Issue Pack

This pack reconciles the user-provided 2026-05-19 architecture-semantic ETL
audit with the current repository state on `main` and converts only confirmed,
still-actionable gaps into new GitHub issues.

## Decision Summary

| Finding | User audit claim | Current repo actuality | Action |
| --- | --- | --- | --- |
| CF-01 | Composite preflight misses dependencies and resolves schemas by provider only | Not reproduced. Composite preflight now accepts provider+entity source tokens and validates seed, dependencies, and enrichers through the current orchestration path. | Do not create new issue |
| CF-02 | Composite outputs lack normalization profiles | Not reproduced as an active defect. Current semantic audit reports `Normalization DIFFERENT/CONFLICTING = 0` and follow-up semantic hardening wave for profile/schema authority already closed. | Do not create new issue |
| CF-03 | `chembl.activity` active Gold contract but Gold sink disabled | Not reproduced. `configs/entities/chembl/activity.yaml` currently has `pipeline.sink.gold.enabled: true`; earlier registry coverage gap was already closed by `CHEMBL-015`. | Do not create new issue |
| CF-04 | `include_sample_failures: truebc` | Not reproduced on current `main`. Active configs now use valid booleans and the stale typo is already called out as resolved in `TECH-DEBT-AUDIT-2026-05-19-ISSUE-PACK.md`. | Do not create new issue |
| CF-05 | Base `strict_validation=false` weakens Gold strict validation | Not reproduced as a live gap. Current repo already enforces Gold strictness at write/config gate level. | Do not create new issue |
| CF-06 | Occurrence-scoped lineage fields leak into persisted contracts | Not confirmed as a defect under current repo policy. Current semantic audit intentionally classifies `_run_id`, `_source_batch_id`, `_ingestion_ts`, `_index` as shared system/lineage fields. | Do not create new issue |
| CF-07 | Same-name semantic overload needs canonical registry / coalesce policy | Already covered and completed through semantic governance waves `#4219`, `#4220`, `#4222`, `#4272`, `#4273`. | Do not create new issue |
| CF-08 | Composite DQ stubs are underdefined | Confirmed residual gap. `configs/quality/entities/composite/activity.yaml`, `assay.yaml`, `molecule.yaml`, and `target.yaml` are still threshold-only stubs with `required_fields: []`. | Create issue |
| CF-09 | Identifier typing drift int vs float | Not reproduced as a current lossiness defect. Current semantic audit reports `Typing LOSSY/CONFLICTING = 0`; explicit schema-authority follow-up `#4274` is already completed. | Do not create new issue |
| CF-10 | Enum validation externalization is incomplete | Broad theme already covered by existing enum/vocabulary governance work (`CROSS-001`, `NONCHEMBL-004`) and second-wave semantic hardening. | Do not create new issue |

## Publish-Ready Set

1. `SEMANTIC-020-Replace-Threshold-Only-Composite-DQ-Stubs-With-Contract-Derived-Validation-Bundles.md`

## Why Only One Issue

The user-provided audit is directionally useful, but much of its CRITICAL/HIGH
set is stale against the current checkout. The only reproduced gap with clear
current evidence is the underdefined DQ surface for four composite entities:

- `composite_activity`
- `composite_assay`
- `composite_molecule`
- `composite_target`

These files still keep only thresholds and empty `required_fields`, while
`composite_publication` already carries real field-level validations. That is a
real asymmetry and an appropriate follow-up issue.
