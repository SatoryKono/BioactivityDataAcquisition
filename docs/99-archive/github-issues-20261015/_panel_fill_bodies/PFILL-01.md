## Summary

**Processed Records** HTTP payload embeds parameter name into value cells via `display_token()`.

## Bug

```json
{"parameter":"01 bronze_records","value":"01 bronze_records|45","percintage":"01 bronze_records|100%"}
```

Operator sees duplicated labels in Grafana table columns.

## Root cause

`display_token(parameter, display_text) -> f"{parameter}|{display_text}"` in `_processed_records_table_support.py` while Grafana already has separate `parameter` / `value` / percentage columns.

## Fix

- Return plain `display_text` from `display_token` (or stop using it for multi-column table)
- Update unit tests that assert pipe-prefixed tokens
- Keep padded/right-aligned count formatting

## Acceptance

- API returns `"value":"45"` (or padded count) without parameter prefix
- Percentage field without parameter prefix
- Grafana Processed Records readable on all 6 boards
