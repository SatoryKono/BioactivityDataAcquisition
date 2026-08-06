## Source

- Epic: #7688
- Wave parent: #7690
- Wave: **A**
- Path cluster: `src/bioetl/application/core/_record_processor_span_support.py`
- Severity counts: `{'major': 1}`

## Findings (top)

- **major** `src/bioetl/application/core/_record_processor_span_support.py`: In @src/bioetl/application/core/_record_processor_span_support.py around lines 48 - 58, Update the span execution methods, including execute_transform_with_span and the shown coroutine method, to close the span in a finally block so success, processing errors, cancellation, an...

## Acceptance

- [ ] Confirm each finding against current `main` (code wins)
- [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
- [ ] Do **not** grow tech-debt / quality budgets
- [ ] Prefer one root-cause PR

## Notes

Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
De-dupe against open ARCH-CR / prior packs before implementing.

