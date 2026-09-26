# ChEMBL Observed Vocabulary Inventory

The tracked Bronze fixture manifest can be exported into a deterministic
observed-value inventory for reviewed ChEMBL vocabulary surfaces.

## Command

```bash
./.venv/bin/python scripts/data_quality/export_chembl_observed_vocab.py
```

## Output

The script writes:

- `docs/reports/generated/chembl_observed_vocab_inventory.csv`
- `docs/reports/generated/chembl_observed_vocab_inventory.json`

## CSV Columns

| Column | Meaning |
| --- | --- |
| `pipeline_name` | Canonical pipeline name such as `chembl_activity` |
| `fixture_key` | Fixture manifest key such as `chembl/activity` |
| `field_name` | Reviewed field observed in tracked Bronze fixtures |
| `layer_hint` | Current layer origin hint; today always `bronze_fixture` |
| `observed_value` | Raw observed value rendered deterministically |
| `count` | Occurrence count in tracked fixtures |
| `normalized_value` | Profile-normalized representation when a normalization rule exists |
| `classification_hint` | High-level governance hint such as `enum`, `ontology`, or `normalized_field` |
| `fixture_path` | Relative path to the tracked fixture file |

## Scope

- scans all tracked `chembl/*` fixture entries from `configs/base/bronze_fixture_manifest.yaml`
- fails fast if a declared fixture path is missing
- sorts rows by `pipeline_name`, `field_name`, `normalized_value`, `observed_value`

This inventory is an audit artifact. It does not replace runtime DQ contracts or
normalization profiles.
