______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-17'

______________________________________________________________________

# Gold contract 1.1 migration

Gold contract 1.1 is a deliberate breaking correction:

- Gold output metadata accepts only `format: delta`;
- metadata datetime fields require timezone-aware effective UTC;
- legacy Gold Parquet remains readable as a migration source, but is not a
  valid target for new Gold writes.

The supported migration is local-only, dry-run by default, and preserves the
source. It writes a separate Delta target, verifies row parity, normalizes
reviewed metadata fields, and records a content-bound migration manifest.

## 1. Inventory without writing

Choose one legacy table and a new target path. The paths must differ.

```bash
python scripts/ops/migrations/active/migrate_gold_parquet_to_delta.py \
  --source data/output/gold/legacy/provider_entity \
  --target data/output/gold/delta/provider_entity
```

The JSON result has `status: planned` plus file count, byte count, row count,
schema, and a source SHA-256 fingerprint. No target is created.

If the legacy dataset is partitioned, repeat `--partition-by` for every Delta
partition column during both planning and apply review.

## 2. Decide how to handle naive legacy timestamps

The migration fails closed on naive metadata timestamps. Verify from the
producer/run evidence that they represented UTC before opting in to:

```text
--assume-naive-utc
```

Aware non-UTC offsets are converted to the same instant in UTC. Naive values
are never guessed without the explicit flag.

## 3. Apply to an isolated target

```bash
python scripts/ops/migrations/active/migrate_gold_parquet_to_delta.py \
  --source data/output/gold/legacy/provider_entity \
  --target data/output/gold/delta/provider_entity \
  --partition-by provider \
  --assume-naive-utc \
  --apply
```

Apply writes a sibling staging directory, validates Delta row count against
the source inventory, then atomically renames the staging directory to the
target. It never edits, renames, or removes the source. Repeating the same
command returns `status: already_applied` only when the source fingerprint and
row counts still match.

The target contains `_gold_contract_v1_1_migration.json`. Retain this manifest
with migration evidence.

## 4. Validate and cut over

Before changing consumers:

1. Compare source and target row counts from the migration result.
1. Run `python scripts/ops/data/check_delta_integrity.py <target-path>`.
1. Validate a representative domain query and the normalized metadata sidecar.
1. Change the consumer/table pointer in a separately reviewed configuration
   change.

Rollback is pointer-only: restore the consumer to the untouched legacy source.
Do not delete legacy Parquet until the normal retention and backup policy has
expired and the owner has approved removal.

## Failure recovery

- An existing non-matching target causes a hard failure; choose a new target or
  investigate it rather than overwriting it.
- An existing staging directory causes a hard failure. Inspect it, capture any
  evidence needed, and remove it only through the normal operator cleanup
  workflow before retrying.
- A row-count mismatch leaves the source untouched and does not promote the
  staging table.

## Related contracts

- [ADR-001: Delta Lake vs Parquet](../02-architecture/decisions/ADR-001-delta-lake-vs-parquet.md)
- [Local storage layout](local-storage-layout.md)
- [Migrations inventory](../../scripts/ops/migrations/README.md)
