Parent: #7167

Task ID: `GRA-RT-01`
Priority: `P0`

## Problem

The canonical runtime render shows ellipsized operator-facing values in:

- Data Quality (`bioetl-dq-v2`): reason/name cells;
- Incident Workspace (`bioetl-incident-v1`): reason/signal cells;
- Run Explorer (`bioetl-run-explorer-v1`): identity labels and identifiers.

The pixels prove truncation, but the audit could not establish whether the full
value remains accessible through hover, cell inspection, or copy. Operational
impact is therefore currently `INFERENCE`.

## Evidence

- `reports/observability/grafana/render-audit-20260729/AUDIT.md`
- render group `1440x900-dark`
- corresponding dashboard JSON under `grafana/dashboards/`

Evidence source: `RUNTIME_RENDER`, `DASHBOARD_JSON`

Confidence: `INFERENCE`

## Scope

1. Use Grafana Inspect and browser interaction to record the full and displayed
   values for each affected field.
2. Classify every case as acceptable compression, identification blocker, or
   lost operator context.
3. Where impact is confirmed, apply the smallest dashboard JSON correction:
   tooltip/cell inspection, field-width override, wrapping, column reduction,
   or compact display with reliable full-value copy.
4. Preserve panel IDs and progressive disclosure.

## Acceptance criteria

- [ ] Each affected panel and field has inspect evidence and a factual impact
      classification.
- [ ] Operator-critical reason, signal, and identity values are retrievable in
      full without consulting datasource storage directly.
- [ ] Copy actions return the full value rather than the rendered abbreviation.
- [ ] No page-level horizontal overflow appears at 1366×768.
- [ ] Navigation remains on one line at 1366×768, 1440×900, and 1920×1080.
- [ ] Dark and Light render groups are reviewed after any JSON change.
- [ ] Any intentionally retained ellipsis is documented with its access path.

## Validation

```bash
.venv/bin/python -m pytest -q \
  tests/integration/test_grafana_config.py \
  tests/integration/test_grafana_layout_and_metadata.py

.venv/bin/python -m scripts.ops rerender-grafana
```

## Out of scope

- changing metric semantics;
- adding new datasource requirements;
- widening technical-debt budgets;
- treating explicit `UNKNOWN`, `INCOMPLETE`, or `No data` as render errors.

