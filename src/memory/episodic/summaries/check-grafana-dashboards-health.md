---
id: check-grafana-dashboards-health
title: Check Grafana dashboards health
task_id: check-grafana-dashboards-health
created_at: '2026-05-22T14:55:29Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Audited shipped Grafana dashboards in repo mode using the dashboard extension
  workflow. Dashboard inventory renders coherently across seven shipped surfaces,
  but the canonical visual-semantics QA script fails on grafana/dashboards/bioetl-runtime.json
  because the trust-marker panel Runtime Telemetry Gap is no longer above fold, so
  the dashboards cannot currently be considered fully healthy. Live Grafana rendering
  was not checked because no running Grafana target was provided; verdict is based
  on repo contracts and QA tooling only.
---

# Episodic summary

## Task

- Title: Check Grafana dashboards health

## Outcome

- Audited shipped Grafana dashboards in repo mode using the dashboard extension workflow. Dashboard inventory renders coherently across seven shipped surfaces, but the canonical visual-semantics QA script fails on grafana/dashboards/bioetl-runtime.json because the trust-marker panel Runtime Telemetry Gap is no longer above fold, so the dashboards cannot currently be considered fully healthy. Live Grafana rendering was not checked because no running Grafana target was provided; verdict is based on repo contracts and QA tooling only.

## Lessons learned

- Replace with durable follow-up if needed
