## Source

- Epic: #7688
- Wave parent: #7690
- Wave: **A**
- Path cluster: `src/bioetl/application/core/_filtered_data_source_support.py`
- Severity counts: `{'major': 1}`

## Findings (top)

- **major** `src/bioetl/application/core/_filtered_data_source_support.py`: In @src/bioetl/application/core/_filtered_data_source_support.py around lines 108 - 122, Update load_csv_filter_ids to explicitly reject or normalize a one-entry columns configuration when column_name is absent, ensuring it cannot continue to fetch_without_internal_filters wit...

## Acceptance

- [ ] Confirm each finding against current `main` (code wins)
- [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
- [ ] Do **not** grow tech-debt / quality budgets
- [ ] Prefer one root-cause PR

## Notes

Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
De-dupe against open ARCH-CR / prior packs before implementing.

