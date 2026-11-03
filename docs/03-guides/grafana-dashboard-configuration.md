______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-11-03'

______________________________________________________________________

# Grafana Dashboard Configuration Guide

**Issue:** #6552
**Boundary:** Monitoring/Grafana is **optional** (ADR-010). Default BioETL is Local-Only.

## Source of truth

| Artifact | Role |
| --- | --- |
| `grafana/dashboards/*.json` | Shipped dashboards (edit carefully) |
| `docs/03-guides/dashboards/**` | Human inventory, panels, checklists |
| Skill `observability-dashboard` | Agent edit, render, and debug workflow |

## Setup (when enabled)

1. Provision Grafana with a Prometheus datasource matching label conventions.
2. Import/load shipped JSON dashboards — prefer repo files over ad-hoc exports.
3. Verify variables (`pipeline`, `provider`, …) resolve.
4. Confirm panels that require recording rules have rules deployed.

## Shipped dashboard set (five JSON)

Provisioned under `grafana/dashboards/` (no `*-preview.json`, no retired
boards 3/4):

| File | UID | Title |
| --- | --- | --- |
| `bioetl-control-plane-v1.json` | `bioetl-control-plane-v1` | Replay Readiness |
| `bioetl-overview-v2.json` | `bioetl-overview-v2` | Run Overview |
| `bioetl-dq-v2.json` | `bioetl-dq-v2` | Data Quality |
| `bioetl-incident-v1.json` | `bioetl-incident-v1` | Incident Workspace |
| `bioetl-run-explorer-v1.json` | `bioetl-run-explorer-v1` | Run Explorer |

Each board carries navigation panel `id=1000` (`Navigate Dashboards`): five
chips at 19.5% width; the current board is a `<span class="bioetl-nav-current">`,
not a link. Runtime / Provider Health JSON were retired; their evidence lives on
Overview / Incident.

See [dashboard-guide.md](dashboard-guide.md) and `dashboards/README.md`.

## Customization rules

1. Prefer extending existing panels over cloning entire dashboards.
2. Keep PromQL aligned with real metric names (use metric discovery skill).
3. Update panel markdown docs in the same change as JSON.
4. Avoid high-cardinality label explosions.

## Verification

- Dashboard JSON validates in Grafana UI
- Render preflight/skill when screenshots required
- No dependency on removed Loki/Tempo/Quarantine Explorer UI surfaces

## Reproducible acceptance captures

For regression acceptance, use a fresh output directory and one explicit
occurrence ID with fixed UTC Unix-millisecond boundaries:

```bash
python -m scripts.ops.observability.grafana.rerender_grafana_screenshots \
  --fallback playwright --width 1366 --height 768 \
  --capture-surface viewport --no-expand-collapsed-rows \
  --range-from 1788782400000 --range-to 1788804000000 \
  --occurrence-id acceptance-20260907-1366-dark \
  --output-dir reports/observability/grafana/acceptance-20260907-1366-dark
```

Supply credentials through the existing repository environment. Both fixed
boundaries are required, and the end must follow the start. Omit them to retain
the interactive `--range-hours` behavior. Repeat full expanded captures in a
different directory; their image height does not prove first-viewport fit.

Explicit occurrences refuse existing PNG/manifest output before capture. Use
the named `render-manifest--…--<capture_id>.json` in reviewer bundles; the
mutable `render-manifest.json` is a navigation pointer. Preserve the whole
capture directory. Preflight compares source digests to the selected checkout,
so validating older evidence requires its matching source checkout.

Failed captures retain available screenshots and measurements and keep a
nonzero exit status. A partial manifest is evidence of the failure, never a
passing render. DOM text contrast measurements include computed foreground,
composited background, font classification, and unrounded ratio; gradients,
filters, canvas graphics, hidden/virtualized content, and unobserved states
need separate evidence. The collector does not certify overall accessibility.

## Related

- [metrics-monitoring.md](metrics-monitoring.md)
- [monitoring-alerts tutorial](tutorials/monitoring-alerts-setup.md)
