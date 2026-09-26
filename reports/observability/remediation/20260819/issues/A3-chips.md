## Problem

Provider Health hides `$pipeline_context` and `$adapter` (`hide=2`). Runtime hides `$provider_hint`. Circuit-breaker / adapter panels still consume `$adapter`, so the operator cannot confirm applied scope.

## Proposed solution

Keep implementation variables hidden (editable clutter is worse). Add **read-only effective-filter chips** on D2–D5 first window (and D3 especially): `stage`, `provider`, `adapter`, `pipeline_context` when they affect a query.

Join to `selector-contracts.yaml` / inventory; do not make a second variable SSOT.

## Scope

Grafana text/HTML chips or Grafana 12 viz; `docs/03-guides/dashboards/contracts/selector-contracts.yaml`; tests for hidden-var → chip text.

## Alternatives considered

Un-hide all variables — rejected; chips only.

## Acceptance criteria

- [ ] Hidden vars that appear in any live target are visible as read-only chips.
- [ ] `adapter=All` / `.*` interpolation is asserted.
- [ ] Operator-readability / HTML copy roles stay green.

Parent: DASH-SCOPE epic. Depends on A1/A2 scope header landing so chips sit in the same strip.
