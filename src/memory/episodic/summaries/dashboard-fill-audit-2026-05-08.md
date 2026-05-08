---
id: dashboard-fill-audit-2026-05-08
title: Run chembl_assay and audit dashboard panel fill correctness
task_id: dashboard-fill-audit-2026-05-08
created_at: '2026-05-08T15:13:30Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Ran chembl_assay workflow with limit 1000 and audited Grafana dashboards
  by querying Prometheus and Loki. Confirmed successful workflow run 03783fed-566e-409c-bb7e-ae7b7ac80dc3
  with Prometheus metrics present. Identified control-plane rule empties, runtime
  blocker inconsistency, and a Loki ingestion gap causing empty log panels and Explore
  Logs. Classified audit, tracing, DQ-duration, failure, and several provider-health
  empties as expected due to disabled subsystems or healthy successful run.
---

# Episodic summary

## Task

- Title: Run chembl_assay and audit dashboard panel fill correctness

## Outcome

- Ran chembl_assay workflow with limit 1000 and audited Grafana dashboards by querying Prometheus and Loki. Confirmed successful workflow run 03783fed-566e-409c-bb7e-ae7b7ac80dc3 with Prometheus metrics present. Identified control-plane rule empties, runtime blocker inconsistency, and a Loki ingestion gap causing empty log panels and Explore Logs. Classified audit, tracing, DQ-duration, failure, and several provider-health empties as expected due to disabled subsystems or healthy successful run.

## Lessons learned

- Replace with durable follow-up if needed
