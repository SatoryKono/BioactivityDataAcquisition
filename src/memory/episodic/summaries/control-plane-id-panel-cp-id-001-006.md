---
id: control-plane-id-panel-cp-id-001-006
title: Implement Control Plane ID identity evidence refactor
task_id: control-plane-id-panel-cp-id-001-006
created_at: '2026-05-15T17:47:11Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/http/_health_server_identity_evidence.py
summary: Implemented dedicated /ops/control-plane/identity-evidence endpoint, preserved
  identity-table contract, added Control Plane Grafana identity evidence panels, updated
  dashboard docs, and added targeted HTTP/Grafana regression tests. Validation passed
  for HTTP identity tests, Grafana config/metric/link slices, ruff, JSON parse, and
  dashboard visual semantics.
---

# Episodic summary

## Task

- Title: Implement Control Plane ID identity evidence refactor

## Outcome

- Implemented dedicated /ops/control-plane/identity-evidence endpoint, preserved identity-table contract, added Control Plane Grafana identity evidence panels, updated dashboard docs, and added targeted HTTP/Grafana regression tests. Validation passed for HTTP identity tests, Grafana config/metric/link slices, ruff, JSON parse, and dashboard visual semantics.

## Lessons learned

- Replace with durable follow-up if needed
