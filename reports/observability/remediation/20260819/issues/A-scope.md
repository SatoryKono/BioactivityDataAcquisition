## Problem

First-window copy already distinguishes CURRENT / SELECTED RUN / TIME RANGE (`#8923` closed). Query panels still lack a machine-readable **per-panel** `scope_class`, and a selected UUID that finished outside the Grafana window has **no coverage offset and no Set range to run CTA**. Operators keep reading CURRENT Prometheus as the historical run verdict.

## Proposed solution

**A1.** Every query panel on the seven shipped UIDs declares `scope_class` in `panel-content-contract.yaml` (`current` / `time_range` / `selected_run` / `global`) and shows a compact badge. Join to existing `scope`; do not fork a second UID/title SSOT.

**A2.** Shared coverage chip: `covers selected run: yes | outside by <duration>`. Button **Set range to run** sets absolute range `started_at-5m` … `completed_at+5m`. Do **not** change range silently.

Applies to D0–D6. Trust keeps its evidence banner; it still needs coverage vs selected run.

## Scope

`grafana/dashboards/*.json`, `docs/03-guides/dashboards/contracts/panel-content-contract.yaml`, operator copy, tests in `tests/integration/test_dashboard_*`.

## Alternatives considered

Auto-changing the dashboard time range when `$run_id` is set — rejected.

## Acceptance criteria

- [ ] 100% query panels have `scope`/`scope_class` in the content contract and a visible badge or equivalent first-window marker.
- [ ] UUID outside the window shows a warning with hour offset.
- [ ] Set range to run opens an absolute range covering the run ±5 min.
- [ ] No PromQL `run_id=` label.
- [ ] `test_dashboard_first_window_containment` and operator-readability stay green.
- [ ] No first-window panel-count budget increase.

Parent: DASH-SCOPE epic.
