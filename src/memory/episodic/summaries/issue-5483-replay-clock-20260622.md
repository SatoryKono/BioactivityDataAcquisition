---
id: issue-5483-replay-clock-20260622
title: Close issue 5483 replay-safe clock seam
task_id: issue-5483-replay-clock-20260622
created_at: '2026-06-22T15:49:37Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: 'Added PipelineRunContext.create in src/bioetl/domain/context.py, routed
  production callers through the shared context timestamp seam, added fixed-clock
  regression coverage, refreshed module-coverage inventory, and closed GitHub issue
  #5483 after targeted replay/time-seam validation.'
---

# Episodic summary

## Task

- Title: Close issue 5483 replay-safe clock seam

## Outcome

- Added PipelineRunContext.create in src/bioetl/domain/context.py, routed production callers through the shared context timestamp seam, added fixed-clock regression coverage, refreshed module-coverage inventory, and closed GitHub issue #5483 after targeted replay/time-seam validation.

## Lessons learned

- Replace with durable follow-up if needed
