---
id: id-panel-parameter-audit-20260516
title: Audit ID panel displayed parameters
task_id: id-panel-parameter-audit-20260516
created_at: '2026-05-16T09:08:52Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards
summary: 'Audited primary Grafana ID panels: dashboards 0..5 share the legacy /ops/control-plane/identity-table
  compact table with 9 rows, while Control Plane alone has /identity-evidence detail
  panels. Recommended moving shared ID display to a compact identity-evidence overview
  with normalized P0 anchors and keeping high-cardinality IDs off Prometheus.'
---

# Episodic summary

## Task

- Title: Audit ID panel displayed parameters

## Outcome

- Audited primary Grafana ID panels: dashboards 0..5 share the legacy /ops/control-plane/identity-table compact table with 9 rows, while Control Plane alone has /identity-evidence detail panels. Recommended moving shared ID display to a compact identity-evidence overview with normalized P0 anchors and keeping high-cardinality IDs off Prometheus.

## Lessons learned

- Replace with durable follow-up if needed
