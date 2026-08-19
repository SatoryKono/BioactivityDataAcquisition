# ChEMBL Assay Schema

This reference documents the current persisted-row contract for ChEMBL
assay publication. It is scoped to the live Silver/Gold row shape.
Do not treat this page as a second field SSOT: the generated Gold JSON
is canonical.

## Canonical sources

- Gold contract: `docs/04-reference/contracts/gold/chembl_assay_v1.0.json`
- Silver snapshot: `tests/contract/silver_schemas/snapshots/chembl_assay_schema.json`
- Pipeline reference: `docs/04-reference/providers/chembl/assay.md`
- Entity config: `configs/entities/chembl/assay.yaml`

## System Fields (Persisted-Row Contract)

| Field          | Type   | Nullable | Purpose                    |
| -------------- | ------ | -------- | -------------------------- |
| `entity_id`    | `str`  | No       | Business key (= `assay_id`) |
| `content_hash` | `str`  | No       | SHA256 for SCD Type 2      |
| `_dq_warn`     | `bool` | No       | Soft DQ warning flag       |
| `_dq_error`    | `bool` | No       | Hard DQ error flag         |
| `_index`       | `int`  | No       | Source-batch row ordinal   |

## Business keys and joins

| Field            | Type          | Nullable | Purpose                |
| ---------------- | ------------- | -------- | ---------------------- |
| `assay_id`       | `str`         | No       | ChEMBL assay identifier |
| `target_id`      | `str \| None` | Yes      | Assay target           |
| `publication_id` | `str \| None` | Yes      | Source publication     |
| `cell_id`        | `str \| None` | Yes      | Cell line, when present |
| `tissue_id`      | `str \| None` | Yes      | Tissue, when present   |

Remaining assay-type, description, and source columns are defined only in the
Gold JSON above. Occurrence-scoped run anchors are published outside the
physical row contract.

## Validation

The persisted-row contract is validated by `ChEMBLAssayGoldSchema` and the
active ChEMBL assay normalization profile.
