## Problem

Operators still mix **CURRENT Prometheus** with **SELECTED RUN** HTTP evidence: a successful historical UUID (outside `now-12h`) is read as the live fleet/provider verdict; Provider Health can show UNKNOWN/NaN with blank cause tables; hidden `$adapter` / `$pipeline_context` are applied but not visible.

This is not a run-report arithmetic bug. Exact-run accounting is already correct via Ops HTTP.

## Proposed solution

Execute the actualized plan:

`reports/observability/remediation/20260819/plan_dashboard_scope_refactor.md`

Pin: `origin/main` `592bf60b74`. Surface is **seven** UIDs (0. Trust … 6. Run Explorer), **236** panels — not the audit-era “six boards / 148 panels”.

Workstreams:

- **A** scope/time coverage (per-panel `scope_class`, Set range to run, effective chips/refresh)
- **B** provider status without NaN + reason/freshness
- **C** compact selected-run projection + D6 drill-down
- **D** below-fold duplicate table reduction (do **not** raise or fight `first_screen_max_panels=8`)
- **E** reuse `#8984` `#8985` `#8986` — do not fork a second test pack

## Scope

Grafana JSON, Prom recording rules for provider current-status, Ops HTTP run-report projection, dashboard contract tests.

## Alternatives considered

- Silent auto-rewrite of Grafana `$__from/$__to` when a run is selected — rejected; warning + explicit CTA only.
- Storing `run_id` as a Prometheus label — forbidden (`DASH-DATA-002`).
- Reopening closed scope-banner issues `#8543`–`#8552` / `#8923` — those banners already shipped; this epic is per-panel class + coverage CTA.

## Constraints

- ADR-010: Grafana remains optional; no new local Docker requirement.
- No tech-debt budget / viewport / `first_screen_max_panels` increases.
- No `or vector(0)` on verdicts.
- Do not duplicate `#8984` `#8985` `#8986`.

## Children (created with this pack)

See linked issues in the epic comment after create.
