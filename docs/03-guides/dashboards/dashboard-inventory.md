______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-15'

______________________________________________________________________

# Dashboard Inventory And Versioning Policy

## Purpose

This page is the canonical human-readable inventory for shipped Grafana
dashboards.

Current sources of truth:

- dashboard JSON: `grafana/dashboards/*.json`
- machine-readable mapping:
  `docs/03-guides/dashboards/contracts/dashboard-inventory.yaml`

Use this page when you need one authoritative mapping between dashboard JSON,
published docs, primary panel references, data sources, and naming/versioning
policy.

## Shipped Dashboard Mapping

| Dashboard | JSON file | Family | Primary docs | Panel docs | Datasources | Versioning form |
| --- | --- | --- | --- | --- | --- | --- |
| `0. Control Plane` | `grafana/dashboards/bioetl-control-plane-v1.json` | primary | [dashboard-v2-usage.md](dashboard-v2-usage.md), [Monitoring Guide](../../05-operations/01-monitoring-guide.md) | [bioetl-control-plane-v1-panels.md](panels/bioetl-control-plane-v1-panels.md) | Prometheus, HTTP control-plane backend | versioned (`v1`) |
| `1. Overview` | `grafana/dashboards/bioetl-overview-v2.json` | primary | [dashboard-v2-usage.md](dashboard-v2-usage.md), [monitoring-index.md](monitoring-index.md) | [bioetl-overview-v2-panels.md](panels/bioetl-overview-v2-panels.md) | Prometheus, HTTP control-plane backend | versioned (`v2`) |
| `2. Runtime` | `grafana/dashboards/bioetl-runtime.json` | primary | [dashboard-v2-usage.md](dashboard-v2-usage.md), [Monitoring Guide](../../05-operations/01-monitoring-guide.md) | [bioetl-runtime-panels.md](panels/bioetl-runtime-panels.md) | Prometheus | stable unversioned |
| `3. Provider Health` | `grafana/dashboards/bioetl-provider-health-v2.json` | primary | [dashboard-v2-usage.md](dashboard-v2-usage.md), [monitoring-index.md](monitoring-index.md) | [bioetl-provider-health-v2-panels.md](panels/bioetl-provider-health-v2-panels.md) | Prometheus | versioned (`v2`) |
| `4. Data Quality` | `grafana/dashboards/bioetl-dq-v2.json` | primary | [dashboard-v2-usage.md](dashboard-v2-usage.md), [Monitoring Guide](../../05-operations/01-monitoring-guide.md) | [bioetl-dq-v2-panels.md](panels/bioetl-dq-v2-panels.md) | Prometheus | versioned (`v2`) |
| `5. Workflow` | `grafana/dashboards/bioetl-workflow-overview.json` | primary | [dashboard-v2-usage.md](dashboard-v2-usage.md), [monitoring-index.md](monitoring-index.md) | [bioetl-workflow-overview-panels.md](panels/bioetl-workflow-overview-panels.md) | Prometheus | stable unversioned |
| `Silver Reject Explorer` | `grafana/dashboards/bioetl-silver-reject-explorer.json` | explorer | [monitoring-index.md](monitoring-index.md), [dashboard-v2-usage.md](dashboard-v2-usage.md) | [bioetl-silver-reject-explorer-panels.md](panels/bioetl-silver-reject-explorer-panels.md) | HTTP quarantine backend | stable unversioned |
| `6. Alerts & SLO` | `grafana/dashboards/bioetl-alerts-slo.json` | alert triage | [Monitoring Guide](../../05-operations/01-monitoring-guide.md), [monitoring-index.md](monitoring-index.md) | [bioetl-alerts-slo-panels.md](panels/bioetl-alerts-slo-panels.md) | Prometheus | stable unversioned |

## Versioning And Naming Policy

### Versioned dashboards

Use an explicit version suffix such as `-v1` or `-v2` when a dashboard
represents a maintained major revision line of an existing conceptual family.

Current examples:

- `bioetl-control-plane-v1`
- `bioetl-overview-v2`
- `bioetl-provider-health-v2`
- `bioetl-dq-v2`

### Stable unversioned dashboards

Use a stable unversioned name when the dashboard is an adjunct, explorer, or
currently single-line operational surface without parallel major revisions.

Current examples:

- `bioetl-runtime`
- `bioetl-workflow-overview`
- `bioetl-silver-reject-explorer`
- `bioetl-alerts-slo`

### Governance rule

- If a future dashboard replaces an existing conceptual family while the old
  family still matters for traceability or operator cognition, the new shipped
  JSON SHOULD use an explicit version suffix.
- Do not introduce mixed aliases where docs, JSON, and panel guides use
  different family names for the same shipped surface.

## Datasource Boundary

Current shipped datasource families:

- Prometheus
- HTTP control-plane backend
- HTTP quarantine backend

Loki and Tempo are part of the wider observability stack and Explore handoff
workflow, but they are not the primary datasource owners for every shipped
dashboard panel. Use the panel docs and monitoring guide when validating
Explore-side behavior.

## Validation

Preferred validation surfaces:

```bash
python -m scripts.ops check-grafana-audit-preflight
python -m scripts.ops audit-live-grafana
python -m scripts.ops rerender-grafana
python -m pytest tests/integration/ci/test_dashboard_docs_yaml_consistency.py -q
python -m pytest tests/integration/ci/test_dashboard_active_docs_sync.py -q
```

## Related References

- [Dashboards Docs Index](README.md)
- [Monitoring Docs Index](monitoring-index.md)
- [Dashboard Guide](../dashboard-guide.md)
- `docs/03-guides/dashboards/contracts/dashboard-inventory.yaml`
