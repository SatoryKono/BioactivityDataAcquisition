# ChEMBL Molecule Schema

This reference documents the current persisted-row contract for ChEMBL molecule
publication. It is intentionally scoped to the live Silver/Gold row shape and
the guardrails around that shape; historical migration-only details remain in
the archive copy.

## System Fields (Persisted-Row Contract)

| Field          | Type   | Nullable | Purpose                      | Included in Content Hash |
| -------------- | ------ | -------- | ---------------------------- | ------------------------ |
| `entity_id`    | `str`  | No       | Business key (= molecule_id) | Yes                      |
| `content_hash` | `str`  | No       | SHA256 for SCD Type 2        | No                       |
| `_dq_warn`     | `bool` | No       | DQ warning flag              | No                       |
| `_index`       | `int`  | No       | Source-batch row ordinal     | No                       |

Occurrence-scoped provenance (`_run_id`, `_run_type`, `_source_batch_id`,
`_ingestion_ts`) is not part of the physical Silver/Gold row contract for
current ChEMBL molecule publication. These anchors are emitted through
sidecar/control-plane metadata, lineage fragments, run manifest, run ledger,
and related audit artifacts.

## Transformation Notes

- `molecule_id` remains the business key carried into `entity_id`.
- Structure payloads are flattened into canonical molecule fields for the
  persisted contract.
- Historical migration-only field renames are archive concerns, not part of the
  current operational publication contract.

## Validation Notes

- The persisted-row contract is validated by the active domain schema and
  normalization profile for ChEMBL molecule publication.
- DQ warnings are recorded through `_dq_warn`; occurrence-level reproducibility
  anchors are published outside the row contract.
