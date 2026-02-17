# Data Contracts Governance (Gold Layer)

Primary governance document for Gold-layer data contracts in BioETL.

> **Status**: Active source for contracts governance
> **Version**: 1.2.0
> **Last updated**: 2026-02-17
> **Related ADRs**: [ADR-018](../../02-architecture/decisions/ADR-018-gold-strict-validation.md), [ADR-014](../../02-architecture/decisions/ADR-014-deterministic-writes.md), [ADR-002](../../02-architecture/decisions/ADR-002-medallion-architecture.md)

______________________________________________________________________

## Source of truth

Gold contracts are governed from two canonical sources:

1. **Runtime contract definitions**: `src/bioetl/domain/contracts/gold/` (Pandera `DataFrameModel` classes, `strict=True`).
1. **Published contract artifacts**: `docs/04-reference/contracts/gold/*.json` (versioned JSON exports for downstream consumers).

This README defines lifecycle policy, compatibility expectations, and release rules for those sources.

## Export flow

Contract publication flow:

1. Update Pandera models in `src/bioetl/domain/contracts/gold/`.
1. Validate schema and pipeline behavior in tests.
1. Regenerate JSON exports in `docs/04-reference/contracts/gold/`.
1. Review diffs for backward compatibility and version impact.
1. Merge only with corresponding version bump and changelog notes.

**Implementation references**:

- Script: `src/tools/scripts/generate_contracts.py`
- Parity check: `src/tools/verify_schema_parity.py`

## Semantic versioning policy (SemVer)

Contract versions use SemVer: `MAJOR.MINOR.PATCH`.

- **MAJOR**: Breaking changes (consumer updates required).
- **MINOR**: Backward-compatible additions/relaxations.
- **PATCH**: Non-functional fixes (docs/metadata corrections, no schema shape impact).

Version must be reflected consistently in:

- Contract metadata and/or export filename conventions.
- Release notes / changelog entries.
- Consumer communication when a breaking change is introduced.

## Breaking vs non-breaking matrix

| Change type                            | Example                          | Compatibility        | Version bump |
| -------------------------------------- | -------------------------------- | -------------------- | ------------ |
| Add nullable field                     | New optional column              | Backward-compatible  | MINOR        |
| Add non-nullable field without default | Required column added            | Breaking             | MAJOR        |
| Remove field                           | Delete existing column           | Breaking             | MAJOR        |
| Rename field                           | `old_name` → `new_name`          | Breaking             | MAJOR        |
| Tighten validation                     | Wider type/constraint → stricter | Usually breaking     | MAJOR        |
| Relax validation                       | More accepted values/nullability | Usually non-breaking | MINOR        |
| Reorder columns only                   | No logical schema change         | Non-breaking         | PATCH        |
| Description/comment fix                | Docs only                        | Non-breaking         | PATCH        |

When uncertain, treat the change as breaking and bump **MAJOR**.

## Hash stability guarantees

`content_hash` must stay deterministic across reruns for identical business content.

Hash formula:

```python
sha256(provider + canonical_json(record))
```

Normalization rules before hashing:

- NaN/Inf → `null`
- Floats → `round(val, 10)`
- Dates → `YYYY-MM-DD`
- Strings → `strip()`
- Exclude operational metadata fields: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_*`

**Guarantee**: Contract changes that alter canonicalization or excluded fields are treated as compatibility-sensitive and require explicit release notes.

## Related artifacts

- JSON exports: [`gold/`](gold/)
- Legacy details and provider-level examples: [`gold-schemas.md`](gold-schemas.md)
- Pipeline specs index: [`../pipelines/README.md`](../pipelines/README.md)
