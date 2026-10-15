## Summary

Rename Processed Records field **`percintage`** → **`percentage`** across HTTP contract and Grafana transforms.

## Scope

- `processed_records_table.py` payload key
- All dashboard JSON organize/rename/index for Processed Records
- Unit + metric-semantics tests
- grafana/README if it documents the field

## Acceptance

- API key is `percentage`
- Grafana column header shows percentage (not typo)
- No remaining `percintage` in shipped dashboard JSON for this contract
