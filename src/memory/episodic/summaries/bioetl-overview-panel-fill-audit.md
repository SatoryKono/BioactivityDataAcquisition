---
id: bioetl-overview-panel-fill-audit
title: Audit BioETL Overview panel fill chain
task_id: bioetl-overview-panel-fill-audit
created_at: '2026-05-05T06:10:25Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-overview-v2.json
summary: Verified overview panels against shipped JSON, recording rules, live Prometheus
  queries, and Prometheus container mounts; current No data is primarily caused by
  missing /etc/prometheus/rules mount and the bioetl scrape endpoint being down.
---

# Episodic summary

## Task

- Title: Audit BioETL Overview panel fill chain

## Outcome

- Verified overview panels against shipped JSON, recording rules, live Prometheus queries, and Prometheus container mounts; current No data is primarily caused by missing /etc/prometheus/rules mount and the bioetl scrape endpoint being down.

## Lessons learned

- Replace with durable follow-up if needed
