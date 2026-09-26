______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Prometheus Metrics Export Guide

**Issue:** #6553
**Related:** [metrics-monitoring.md](metrics-monitoring.md), ADR-017, ADR-032

## Architecture (local-first)

BioETL emits metrics from the application/observability ports. Prometheus is an
**optional** scraper. Local development can validate metric names without a full
monitoring stack.

## Metric classes

| Class | Examples | Notes |
| --- | --- | --- |
| Pipeline | duration, records, status | Label carefully by pipeline |
| DQ | fail rates, quarantine counts | Align with threshold surfaces |
| HTTP | request count/duration/retries/CB | ADR-032 client |
| Runtime | memory/batch decisions | Avoid per-record labels |

## Naming and labels

- Prefer stable `bioetl_` (or project-standard) prefixes already used in code
- Low cardinality labels only (pipeline, provider, stage — not raw IDs)
- Histograms for latency; counters for events

## Scrape configuration (example shape)

```yaml
scrape_configs:
  - job_name: bioetl
    static_configs:
      - targets: ["localhost:8000"]  # health/metrics port when enabled
```

Exact port/path follow the running process config — verify against current
interfaces/health modules before copying into production.

## Alerting

- Rules live with repo Prometheus rule files when present
- Validate with `promtool` (skill: prometheus-rule-testing)
- Map alerts to runbooks under `docs/05-operations/runbooks/`

## Cardinality guardrails

- Never label by free-text error message or full URL
- Bound provider/entity enums
- Review dashboards after new labels

## Related

- [Grafana configuration](grafana-dashboard-configuration.md)
- Observability checklist runbook
