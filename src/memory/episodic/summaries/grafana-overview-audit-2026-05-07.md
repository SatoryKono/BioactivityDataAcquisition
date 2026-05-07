---
id: grafana-overview-audit-2026-05-07
title: Audit BioETL 1. Overview dashboard
task_id: grafana-overview-audit-2026-05-07
created_at: '2026-05-07T13:18:56Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: Completed static and live audit of grafana/dashboards/bioetl-overview-v2.json.
  Verified JSON, dashboard inventory, rule syntax, targeted tests, Prometheus/Grafana
  health, live metric/rule presence, and identified critical Overview issues around
  sparse status series, missing actionable dataLinks, provider projection drift in
  L0 Inputs, unlabeled zero-series leakage from recording rules, trend gap masking,
  and monitoring docs drift.
---

# Episodic summary

## Task

- Title: Audit BioETL 1. Overview dashboard

## Outcome

- Completed static and live audit of grafana/dashboards/bioetl-overview-v2.json. Verified JSON, dashboard inventory, rule syntax, targeted tests, Prometheus/Grafana health, live metric/rule presence, and identified critical Overview issues around sparse status series, missing actionable dataLinks, provider projection drift in L0 Inputs, unlabeled zero-series leakage from recording rules, trend gap masking, and monitoring docs drift.

## Lessons learned

- Replace with durable follow-up if needed
