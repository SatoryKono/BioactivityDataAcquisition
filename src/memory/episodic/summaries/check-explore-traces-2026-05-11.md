---
id: check-explore-traces-2026-05-11
title: Check Explore Traces behavior
task_id: check-explore-traces-2026-05-11
created_at: '2026-05-11T14:26:19Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards
summary: 'Verified Explore Traces live. Found Grafana app and Tempo datasource present,
  Tempo backend empty with no traces/tags, and Grafana Explore Traces issuing invalid
  Tempo metrics query with groupBy=undefined causing HTTP 400. Proposed fixes: ensure
  traced runs exist, avoid invalid default breakdown state, add live smoke for Explore
  Traces.'
---

# Episodic summary

## Task

- Title: Check Explore Traces behavior

## Outcome

- Verified Explore Traces live. Found Grafana app and Tempo datasource present, Tempo backend empty with no traces/tags, and Grafana Explore Traces issuing invalid Tempo metrics query with groupBy=undefined causing HTTP 400. Proposed fixes: ensure traced runs exist, avoid invalid default breakdown state, add live smoke for Explore Traces.

## Lessons learned

- Replace with durable follow-up if needed
