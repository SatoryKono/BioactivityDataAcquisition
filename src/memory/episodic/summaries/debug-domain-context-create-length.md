---
id: debug-domain-context-create-length
title: Reduce domain context create function length
task_id: debug-domain-context-create-length
created_at: '2026-06-22T16:34:11Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/context.py
summary: Reduced PipelineRunContext.create() below the 100-line architecture metric
  by moving optional default resolution for vacuum, input filter, and cached Bronze
  contexts into small module-level helpers. Verified WSL and Windows code metrics
  tests, PipelineRunContext behavior tests, ruff, module coverage artifact check,
  and architecture scorecard consistency.
---

# Episodic summary

## Task

- Title: Reduce domain context create function length

## Outcome

- Reduced PipelineRunContext.create() below the 100-line architecture metric by moving optional default resolution for vacuum, input filter, and cached Bronze contexts into small module-level helpers. Verified WSL and Windows code metrics tests, PipelineRunContext behavior tests, ruff, module coverage artifact check, and architecture scorecard consistency.

## Lessons learned

- Replace with durable follow-up if needed
