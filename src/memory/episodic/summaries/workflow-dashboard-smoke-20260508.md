---
id: workflow-dashboard-smoke-20260508
title: Check dashboard filling during workflow run
task_id: workflow-dashboard-smoke-20260508
created_at: '2026-05-08T08:40:25Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Executed workflow run chembl_activity --limit 1000 successfully and verified
  that live Prometheus workflow metrics driving the Workflow dashboard remained absent
  before, during, and after execution; dashboard fill is therefore not correct for
  this path and likely lacks metrics export/flush in workflow run orchestration.
---

# Episodic summary

## Task

- Title: Check dashboard filling during workflow run

## Outcome

- Executed workflow run chembl_activity --limit 1000 successfully and verified that live Prometheus workflow metrics driving the Workflow dashboard remained absent before, during, and after execution; dashboard fill is therefore not correct for this path and likely lacks metrics export/flush in workflow run orchestration.

## Lessons learned

- Replace with durable follow-up if needed
