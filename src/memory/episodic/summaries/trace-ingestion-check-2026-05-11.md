---
id: trace-ingestion-check-2026-05-11
title: Check trace ingestion path
task_id: trace-ingestion-check-2026-05-11
created_at: '2026-05-11T15:42:37Z'
ttl_days: 14
confidence: episodic
source_refs:
- docs/05-operations/01-monitoring-guide.md
summary: Verified Tempo is reachable but empty; Prometheus scrapes BioETL metrics
  from port 8000 exposed by bioetl quarantine serve; observability runtime status
  reports tracing mode=noop for all pipelines, so Explore Traces returns no data.
  Also found a secondary UX risk where dashboard Explore Traces links use  with includeAll=true/allValue=null,
  which can produce an empty regex in some click paths.
---

# Episodic summary

## Task

- Title: Check trace ingestion path

## Outcome

- Verified Tempo is reachable but empty; Prometheus scrapes BioETL metrics from port 8000 exposed by bioetl quarantine serve; observability runtime status reports tracing mode=noop for all pipelines, so Explore Traces returns no data. Also found a secondary UX risk where dashboard Explore Traces links use  with includeAll=true/allValue=null, which can produce an empty regex in some click paths.

## Lessons learned

- Replace with durable follow-up if needed
