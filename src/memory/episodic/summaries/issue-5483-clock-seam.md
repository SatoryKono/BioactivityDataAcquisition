---
id: issue-5483-clock-seam
title: Fix replay-safe context timestamps
task_id: issue-5483-clock-seam
created_at: '2026-06-22T06:32:08Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/context.py
summary: Routed PipelineContext timestamp resolution through ClockPort-aware constructor
  support and added replay-safe regression coverage.
---

# Episodic summary

## Task

- Title: Fix replay-safe context timestamps

## Outcome

- Routed PipelineContext timestamp resolution through ClockPort-aware constructor support and added replay-safe regression coverage.

## Lessons learned

- Replace with durable follow-up if needed
