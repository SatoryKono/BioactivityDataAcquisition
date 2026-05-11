---
id: audit-explore-links
title: Check Explore Logs and Explore Traces
task_id: audit-explore-links
created_at: '2026-05-11T13:36:07Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/scripts/bootstrap-datasources.sh
summary: Confirmed Explore links are configured in shipped dashboards, but live Grafana
  lacks Loki and Tempo datasources because bootstrap auto-detect likely pruned them;
  direct Loki API works and Tempo is reachable but empty.
---

# Episodic summary

## Task

- Title: Check Explore Logs and Explore Traces

## Outcome

- Confirmed Explore links are configured in shipped dashboards, but live Grafana lacks Loki and Tempo datasources because bootstrap auto-detect likely pruned them; direct Loki API works and Tempo is reachable but empty.

## Lessons learned

- Replace with durable follow-up if needed
