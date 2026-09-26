## Source

- Epic: #7688
- Wave parent: #7690
- Wave: **A**
- Path cluster: `src/bioetl/application/core/publication_term_filtering_mixin.py`
- Severity counts: `{'major': 1}`

## Findings (top)

- **major** `src/bioetl/application/core/publication_term_filtering_mixin.py`: In @src/bioetl/application/core/publication_term_filtering_mixin.py around lines 44 - 60, The publication fetch limit calculations in the surrounding filtering flow and _resolve_target_fallback_upstream_limit currently treat zero as absent. Change both conditional expressions ...

## Acceptance

- [ ] Confirm each finding against current `main` (code wins)
- [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
- [ ] Do **not** grow tech-debt / quality budgets
- [ ] Prefer one root-cause PR

## Notes

Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
De-dupe against open ARCH-CR / prior packs before implementing.

