---
id: dashboard-provider-health-corrections-20260525
title: Implement Provider Health dashboard corrections
task_id: dashboard-provider-health-corrections-20260525
created_at: '2026-05-25T07:32:23Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-provider-health-v2.json
summary: Added Provider Health telemetry freshness marker, normalized __all scope
  handling, and made unknown pipeline HTTP table scopes fail fast with No data/no-manifest
  states. Updated Provider Health dashboard docs and tests; targeted unit, Grafana
  semantic/contract, visual semantics, ruff, and live Prometheus freshness query passed.
  Broad Grafana suite still has unrelated DQ first-screen y-position drift.
---

# Episodic summary

## Task

- Title: Implement Provider Health dashboard corrections

## Outcome

- Added Provider Health telemetry freshness marker, normalized __all scope handling, and made unknown pipeline HTTP table scopes fail fast with No data/no-manifest states. Updated Provider Health dashboard docs and tests; targeted unit, Grafana semantic/contract, visual semantics, ruff, and live Prometheus freshness query passed. Broad Grafana suite still has unrelated DQ first-screen y-position drift.

## Lessons learned

- Replace with durable follow-up if needed
