---
id: exhaustive-grafana-dashboard-audit
title: Exhaustive Grafana dashboard audit
task_id: exhaustive-grafana-dashboard-audit
created_at: '2026-05-24T15:28:02Z'
ttl_days: 14
confidence: episodic
source_refs:
- docs/03-guides/dashboards/contracts/selector-contracts.yaml
summary: 'Audited shipped Grafana dashboards: confirmed primary run_id is HTTP-backed
  and isolated from Prometheus labels; confirmed ID and Processed Records panels use
  expected endpoints on six primary dashboards; found one drift in bioetl-provider-health-v2
  workflow selector includeAll=false despite shared-shell All handoff/docs; pytest
  stdout was unreliable so used repo-local static assertion scripts for validation.'
---

# Episodic summary

## Task

- Title: Exhaustive Grafana dashboard audit

## Outcome

- Audited shipped Grafana dashboards: confirmed primary run_id is HTTP-backed and isolated from Prometheus labels; confirmed ID and Processed Records panels use expected endpoints on six primary dashboards; found one drift in bioetl-provider-health-v2 workflow selector includeAll=false despite shared-shell All handoff/docs; pytest stdout was unreliable so used repo-local static assertion scripts for validation.

## Lessons learned

- Replace with durable follow-up if needed
