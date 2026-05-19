---
id: close-4256-4260-runtime-facades
title: Close runtime facade issues 4256-4260
task_id: close-4256-4260-runtime-facades
created_at: '2026-05-19T07:04:29Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Retired stale interfaces.orchestration and domains.run.command surfaces;
  removed globals-based facade caching from public runtime facades; made composition
  run_pipeline use one prepared PipelineRunContext for stable run identity; trimmed
  redundant SilverWriter delegation overrides; refreshed compatibility snapshot and
  scripts inventory after policy/doc updates.
---

# Episodic summary

## Task

- Title: Close runtime facade issues 4256-4260

## Outcome

- Retired stale interfaces.orchestration and domains.run.command surfaces; removed globals-based facade caching from public runtime facades; made composition run_pipeline use one prepared PipelineRunContext for stable run identity; trimmed redundant SilverWriter delegation overrides; refreshed compatibility snapshot and scripts inventory after policy/doc updates.

## Lessons learned

- Replace with durable follow-up if needed
