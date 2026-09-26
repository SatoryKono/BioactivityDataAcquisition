# ChEMBL Target Schema

This reference documents the current persisted-row contract for ChEMBL
target publication. It is scoped to the live Silver/Gold row shape.
Do not treat this page as a second field SSOT: the generated Gold JSON
is canonical.

## Canonical sources

- Gold contract: `docs/04-reference/contracts/gold/chembl_target_v3.0.json`
- Silver snapshot: `tests/contract/silver_schemas/snapshots/chembl_target_schema.json`
- Pipeline reference: `docs/04-reference/providers/chembl/target.md`
- Entity config: `configs/entities/chembl/target.yaml`

## System Fields (Persisted-Row Contract)

| Field          | Type   | Nullable | Purpose                     |
| -------------- | ------ | -------- | --------------------------- |
| `entity_id`    | `str`  | No       | Business key (= `target_id`) |
| `content_hash` | `str`  | No       | SHA256 for SCD Type 2       |
| `_dq_warn`     | `bool` | No       | Soft DQ warning flag        |
| `_dq_error`    | `bool` | No       | Hard DQ error flag          |
| `_index`       | `int`  | No       | Source-batch row ordinal    |

## Business keys and identity

| Field          | Type          | Nullable | Purpose                 |
| -------------- | ------------- | -------- | ----------------------- |
| `target_id`    | `str`         | No       | ChEMBL target identifier |
| `target_type`  | `str \| None` | Yes      | ChEMBL target type      |
| `pref_name`    | `str \| None` | Yes      | Preferred name          |
| `taxonomy_id`  | `number \| None` | Yes   | NCBI taxonomy id        |
| `organism`     | `str \| None` | Yes      | Organism name           |

Remaining organism-class and component columns are defined only in the Gold
JSON above. Occurrence-scoped run anchors are published outside the physical
row contract.

## Validation

The persisted-row contract is validated by `ChEMBLTargetGoldSchema` and the
active ChEMBL target normalization profile.
