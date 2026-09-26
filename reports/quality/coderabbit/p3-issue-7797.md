## Source

- Epic: #7688
- Wave parent: #7690
- Wave: **A**
- Path cluster: `src/bioetl/application/core/_fetch_forwarding.py`
- Severity counts: `{'major': 1}`

## Findings (top)

- **major** `src/bioetl/application/core/_fetch_forwarding.py`: In @src/bioetl/application/core/_fetch_forwarding.py around lines 9 - 20, Replace the bare object sentinel used by build_forwarded_fetch_kwargs and forward_fetch_records with a distinct single-member Enum sentinel type, and annotate filter_ids and filter_field as their actual ...

## Acceptance

- [ ] Confirm each finding against current `main` (code wins)
- [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
- [ ] Do **not** grow tech-debt / quality budgets
- [ ] Prefer one root-cause PR

## Notes

Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
De-dupe against open ARCH-CR / prior packs before implementing.

