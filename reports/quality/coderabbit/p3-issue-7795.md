## Source

- Epic: #7688
- Wave parent: #7690
- Wave: **A**
- Path cluster: `src/bioetl/application/core/_base_transformer_structural_support.py`
- Severity counts: `{'major': 1}`

## Findings (top)

- **major** `src/bioetl/application/core/_base_transformer_structural_support.py`: In @src/bioetl/application/core/_base_transformer_structural_support.py around lines 149 - 152, Update the structural-policy flow around apply_structural_policy and evaluate_semantic_shadow_decision so a non-quarantined record’s Silver filter is evaluated only once before appl...

## Acceptance

- [ ] Confirm each finding against current `main` (code wins)
- [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
- [ ] Do **not** grow tech-debt / quality budgets
- [ ] Prefer one root-cause PR

## Notes

Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
De-dupe against open ARCH-CR / prior packs before implementing.

