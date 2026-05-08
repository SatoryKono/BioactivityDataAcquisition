---
id: grafana-missing-data-conformance-followup-20260508
title: Finish missing-data semantics conformance for dashboards
task_id: grafana-missing-data-conformance-followup-20260508
created_at: '2026-05-08T09:12:53Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Closed the remaining missing-data semantics ambiguity by documenting and
  testing two intentional exceptions: workflow selected-range counters keep zero-valid
  noValue=0, and Silver Reject Explorer keeps datasource-specific noValue copy for
  HTTP forensic states. Fast QA and direct metric-semantic contract checks remain
  green.'
---

# Episodic summary

## Task

- Title: Finish missing-data semantics conformance for dashboards

## Outcome

- Closed the remaining missing-data semantics ambiguity by documenting and testing two intentional exceptions: workflow selected-range counters keep zero-valid noValue=0, and Silver Reject Explorer keeps datasource-specific noValue copy for HTTP forensic states. Fast QA and direct metric-semantic contract checks remain green.

## Lessons learned

- Replace with durable follow-up if needed
