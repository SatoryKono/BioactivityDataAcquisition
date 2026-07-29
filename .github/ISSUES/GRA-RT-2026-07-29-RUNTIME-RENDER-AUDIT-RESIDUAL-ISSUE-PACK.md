# Grafana runtime-render audit residual issue pack

**Status:** prepared; publication blocked by GitHub authentication
**Date:** 2026-07-29
**Parent:** #7167
**Evidence:** `reports/observability/grafana/render-audit-20260729/AUDIT.md`

## Scope

This pack contains only residual work established by the 2026-07-29 canonical
runtime-render audit. It does not reopen the closed DUX6 redesign wave and does
not duplicate the broad live-render/parity baseline tracked by #7167.

| Code | Priority | Title | Body |
|---|---|---|---|
| GRA-RT-01 | P0 | Inspect and remediate ellipsized operator-critical table values | `_grafana_runtime_render_bodies/GRA-RT-01.md` |
| GRA-RT-02 | P1 | Add terminal-state validation to the standard render matrix | `_grafana_runtime_render_bodies/GRA-RT-02.md` |
| GRA-RT-03 | P2 | Add kiosk profiles and deterministic layout-consistency checks | `_grafana_runtime_render_bodies/GRA-RT-03.md` |
| GRA-RT-04 | P2 | Make Quarantine Explorer applicability explicit in render evidence | `_grafana_runtime_render_bodies/GRA-RT-04.md` |

## Delivery order

1. GRA-RT-01
2. GRA-RT-02
3. GRA-RT-03
4. GRA-RT-04 may proceed independently once runtime applicability is decided.

## Guardrails

- Runtime render is the primary visual evidence.
- Preserve the seven dashboard UIDs and stable panel IDs where possible.
- Do not invent metrics or add `run_id` to Prometheus labels.
- `UNKNOWN`, `INCOMPLETE`, and `No data` are not render failures.
- Grafana remains optional under ADR-010.
- Technical-debt budgets must not increase.
- Do not modify `.env` files without explicit per-task approval.

