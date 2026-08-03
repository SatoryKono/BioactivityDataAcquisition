______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Grafana Dashboard Configuration Guide

**Issue:** #6552
**Boundary:** Monitoring/Grafana is **optional** (ADR-010). Default BioETL is Local-Only.

## Source of truth

| Artifact | Role |
| --- | --- |
| `grafana/dashboards/*.json` | Shipped dashboards (edit carefully) |
| `docs/03-guides/dashboards/**` | Human inventory, panels, checklists |
| Skills `grafana-dashboard-extension` / `render` | Agent workflows |

## Setup (when enabled)

1. Provision Grafana with a Prometheus datasource matching label conventions.
2. Import/load shipped JSON dashboards — prefer repo files over ad-hoc exports.
3. Verify variables (`pipeline`, `provider`, …) resolve.
4. Confirm panels that require recording rules have rules deployed.

## BioETL dashboard families

- Workflow / pipeline overview
- Runtime / resource
- DQ / Silver reject explorer
- Alerts / SLO (when rules present)
- Incident views

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

## Related

- [metrics-monitoring.md](metrics-monitoring.md)
- [monitoring-alerts tutorial](tutorials/monitoring-alerts-setup.md)
