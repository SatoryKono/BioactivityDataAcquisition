---
id: fix-dashboard-id-processed-records-empty
title: Fix empty ID and Processed Records panels
task_id: fix-dashboard-id-processed-records-empty
created_at: '2026-05-31T16:10:32Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-control-plane-v1.json
summary: Fixed empty Grafana ID and Processed Records panels by splitting health/quarantine
  listener bootstrap from heavy provider/pipeline runtime imports, adding lightweight
  health-server control-plane dependencies, lazy control-plane adapter exports, a
  read-only quarantine service for health server, and removing blocking checkpoint
  lookup from identity-table. Validated targeted tests, ruff, and in-process HTTP
  smoke for identity/processed rows.
---

# Episodic summary

## Task

- Title: Fix empty ID and Processed Records panels

## Outcome

- Fixed empty Grafana ID and Processed Records panels by splitting health/quarantine listener bootstrap from heavy provider/pipeline runtime imports, adding lightweight health-server control-plane dependencies, lazy control-plane adapter exports, a read-only quarantine service for health server, and removing blocking checkpoint lookup from identity-table. Validated targeted tests, ruff, and in-process HTTP smoke for identity/processed rows.

## Lessons learned

- Replace with durable follow-up if needed
