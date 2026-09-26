## Source

- Epic: #7688
- Wave parent: #7690
- Wave: **A**
- Path cluster: `src/bioetl/application/core/_filtered_data_source_fetch_support.py`
- Severity counts: `{'major': 1}`

## Findings (top)

- **major** `src/bioetl/application/core/_filtered_data_source_fetch_support.py`: In @src/bioetl/application/core/_filtered_data_source_fetch_support.py around lines 125 - 148, Add nominal-path unit tests for fetch_records covering multi-column, single-column, and unfiltered dispatch. Mock the corresponding fetch_multi_column, fetch_single_column, and fetch...

## Acceptance

- [ ] Confirm each finding against current `main` (code wins)
- [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
- [ ] Do **not** grow tech-debt / quality budgets
- [ ] Prefer one root-cause PR

## Notes

Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
De-dupe against open ARCH-CR / prior packs before implementing.

