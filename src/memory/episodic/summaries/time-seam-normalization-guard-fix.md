---
id: time-seam-normalization-guard-fix
title: Fix time seam normalization architecture guard
task_id: time-seam-normalization-guard-fix
created_at: '2026-06-22T17:31:43Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_time_seam_normalization.py
summary: 'Updated the architecture guard to follow the normalized time-seam split:
  context.py now delegates through resolve_context_started_at, while clock.now() lives
  in context_time.py.'
---

# Episodic summary

## Task

- Title: Fix time seam normalization architecture guard

## Outcome

- Updated the architecture guard to follow the normalized time-seam split: context.py now delegates through resolve_context_started_at, while clock.now() lives in context_time.py.

## Lessons learned

- Replace with durable follow-up if needed
