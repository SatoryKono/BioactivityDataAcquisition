---
id: dashboard-id-panels-fill
title: Diagnose and fill BioETL Grafana ID panels
task_id: dashboard-id-panels-fill
created_at: '2026-06-01T15:43:37Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/http/_health_server_control_plane_scope.py
summary: Diagnosed empty Grafana ID panels as Quarantine Explorer backend reachability
  plus slow exact-run identity lookup. Fixed exact run_id ID lookup to use run_manifest
  get_by_run_id instead of list_all, changed ensure_quarantine_explorer readiness
  probe to a fail-fast identity route, switched monitoring compose default datasource
  to quarantine-explorer service DNS, updated docs/tests, started backend on port
  8081, and verified all six shipped ID panels return 9 rows via Grafana datasource
  proxy for run b51986c6-870b-4457-aa70-baedac2710ad.
---

# Episodic summary

## Task

- Title: Diagnose and fill BioETL Grafana ID panels

## Outcome

- Diagnosed empty Grafana ID panels as Quarantine Explorer backend reachability plus slow exact-run identity lookup. Fixed exact run_id ID lookup to use run_manifest get_by_run_id instead of list_all, changed ensure_quarantine_explorer readiness probe to a fail-fast identity route, switched monitoring compose default datasource to quarantine-explorer service DNS, updated docs/tests, started backend on port 8081, and verified all six shipped ID panels return 9 rows via Grafana datasource proxy for run b51986c6-870b-4457-aa70-baedac2710ad.

## Lessons learned

- Replace with durable follow-up if needed
