---
id: control-plane-dashboard-audit
title: Implement Control Plane dashboard audit fixes
task_id: control-plane-dashboard-audit
created_at: '2026-05-05T17:28:45Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-control-plane-v1.json
summary: 'Implemented Control Plane dashboard audit fixes: preserved UNKNOWN for trust-row
  missing telemetry, added Control-Plane Telemetry Missing and Terminal Run Events
  first-screen panels, removed unsafe zero fallback from trust/blocker/lag cards,
  projected manifest/ledger failure ratios into canonical 0/1/2 severity while preserving
  >10% CRIT logic, expanded known missing replay-safety signals, updated Grafana docs
  and regression tests. Targeted Control Plane tests passed; visual semantics gate
  no longer reports Control Plane issues but still fails on out-of-scope DQ/Overview/Provider
  dashboard debt.'
---

# Episodic summary

## Task

- Title: Implement Control Plane dashboard audit fixes

## Outcome

- Implemented Control Plane dashboard audit fixes: preserved UNKNOWN for trust-row missing telemetry, added Control-Plane Telemetry Missing and Terminal Run Events first-screen panels, removed unsafe zero fallback from trust/blocker/lag cards, projected manifest/ledger failure ratios into canonical 0/1/2 severity while preserving >10% CRIT logic, expanded known missing replay-safety signals, updated Grafana docs and regression tests. Targeted Control Plane tests passed; visual semantics gate no longer reports Control Plane issues but still fails on out-of-scope DQ/Overview/Provider dashboard debt.

## Lessons learned

- Replace with durable follow-up if needed
