# ChEMBL Activity Schema

This reference documents the current persisted-row contract for ChEMBL
activity publication. It is scoped to the live Silver/Gold row shape.
Do not treat this page as a second field SSOT: the generated Gold JSON
is canonical.

## Canonical sources

- Gold contract: `docs/04-reference/contracts/gold/chembl_activity_v1.0.json`
- Silver snapshot: `tests/contract/silver_schemas/snapshots/chembl_activity_schema.json`
- Pipeline reference: `docs/04-reference/providers/chembl/activity.md`
- Entity config: `configs/entities/chembl/activity.yaml`

## System Fields (Persisted-Row Contract)

| Field          | Type   | Nullable | Purpose                      |
| -------------- | ------ | -------- | ---------------------------- |
| `entity_id`    | `str`  | No       | Business key (= `activity_id`) |
| `content_hash` | `str`  | No       | SHA256 for SCD Type 2        |
| `_dq_warn`     | `bool` | No       | Soft DQ warning flag         |
| `_dq_error`    | `bool` | No       | Hard DQ error flag           |
| `_index`       | `int`  | No       | Source-batch row ordinal     |

## Business keys and joins

| Field            | Type          | Nullable | Purpose                          |
| ---------------- | ------------- | -------- | -------------------------------- |
| `activity_id`    | `str`         | No       | ChEMBL activity identifier       |
| `molecule_id`    | `str`         | No       | Parent molecule                  |
| `target_id`      | `str \| None` | Yes      | Measured target                  |
| `assay_id`       | `str \| None` | Yes      | Assay that produced the activity |
| `publication_id` | `str \| None` | Yes      | Source publication               |

Remaining measurement, unit, and provenance columns are defined only in the
Gold JSON above. Occurrence-scoped run anchors (`_run_id`, `_ingestion_ts`)
are published outside the physical row contract.

## Validation

The persisted-row contract is validated by `ChEMBLActivityGoldSchema` and the
active ChEMBL activity normalization profile.
