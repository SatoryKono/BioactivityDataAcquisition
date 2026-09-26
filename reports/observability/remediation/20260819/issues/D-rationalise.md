## Problem

236 shipped panels. First-window data-bearing count is already capped (`DASH-FIT-006`, `#8980` closed). Remaining cost is **below-fold duplicate tables** and three independent blank empty-states on Provider Health.

## Proposed solution

Progressive deprecation (not delete-first):

- D1: one domain matrix with current/range tab instead of duplicate domain-status tables.
- D2: global shutdown/memory/process → collapsed operations row.
- D3: Fleet Severity / Non-OK / Causes → master-detail + one empty-state contract.
- D4: reject reasons/fields/outcomes → one pivot + drill-down.
- D5: ranked suspects with domain, signal, confidence, freshness, action; EMPTY DOMAIN shows coverage + next action.
- D6: static explanatory text → expandable details next to the table that needs it.

Do **not** reduce first-window below the answer set in `layout-budgets.yaml` `answer_panels`. Do **not** raise `first_screen_max_panels`.

## Scope

`grafana/dashboards/*.json`, panel docs, content-contract rows for merged/retired ids.

## Alternatives considered

Immediate deletion of collapsed rows — rejected until C4 navigation replacement exists.

## Acceptance criteria

- [ ] Documented panel-id map: retired → replacement.
- [ ] D3 has one empty-state for the fleet cluster.
- [ ] First-window answer panels remain root with `y < 18`.
- [ ] Content-contract and inventory `--check` stay green.
- [ ] Operator-readability green.

Parent: DASH-SCOPE epic. Start after A1/A2 and C2 so summaries exist before tables move.
