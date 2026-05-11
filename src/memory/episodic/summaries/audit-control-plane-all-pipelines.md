---
id: audit-control-plane-all-pipelines
title: Audit Control Plane dashboard across pipelines
task_id: audit-control-plane-all-pipelines
created_at: '2026-05-11T11:17:25Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-control-plane-v1.json
summary: Checked live 0. Control Plane dashboard fill across all currently selectable
  pipeline selectors. Verified 8 live selectors from control-plane universe telemetry,
  quantified per-selector panel fill in the default now-12h window, confirmed global
  UNKNOWN top-row status signals, expected empty audit/drift surfaces, and identified
  workflow alias gaps in multiple lower panels using direct pipeline regex selectors.
---

# Episodic summary

## Task

- Title: Audit Control Plane dashboard across pipelines

## Outcome

- Checked live 0. Control Plane dashboard fill across all currently selectable pipeline selectors. Verified 8 live selectors from control-plane universe telemetry, quantified per-selector panel fill in the default now-12h window, confirmed global UNKNOWN top-row status signals, expected empty audit/drift surfaces, and identified workflow alias gaps in multiple lower panels using direct pipeline regex selectors.

## Lessons learned

- Replace with durable follow-up if needed
