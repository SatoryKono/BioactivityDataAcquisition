---
id: acceptance-baseline-context-anchor-fix
title: Fix acceptance baseline code anchor for domain context
task_id: acceptance-baseline-context-anchor-fix
created_at: '2026-06-22T16:49:45Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_architecture_acceptance_baseline.py
summary: Updated architecture acceptance baseline and execution-context guards to
  follow the PipelineRunContext split into src/bioetl/domain/context_run.py while
  keeping PipelineContext in src/bioetl/domain/context.py.
---

# Episodic summary

## Task

- Title: Fix acceptance baseline code anchor for domain context

## Outcome

- Updated architecture acceptance baseline and execution-context guards to follow the PipelineRunContext split into src/bioetl/domain/context_run.py while keeping PipelineContext in src/bioetl/domain/context.py.

## Lessons learned

- Replace with durable follow-up if needed
