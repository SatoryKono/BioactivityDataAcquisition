---
id: fix-cross-layer-group-edge-budget
title: Fix cross-layer group edge budget regression
task_id: fix-cross-layer-group-edge-budget
created_at: '2026-06-04T15:01:31Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Fixed cross-layer group edge budget regression without increasing budgets
  by removing the unique application.composite -> domain.constants edge from CompositeRuntimeConfig.
  Replaced the domain constants import with an application-local composite default
  preserving lock_ttl_seconds=3600. Updated generated architecture dependency map
  artifacts and module coverage inventory. Validated ruff, unit runtime/heartbeat
  tests, failing architecture budget test with extended timeout, dependency-map check,
  module coverage check, and source-tree hash guard.
---

# Episodic summary

## Task

- Title: Fix cross-layer group edge budget regression

## Outcome

- Fixed cross-layer group edge budget regression without increasing budgets by removing the unique application.composite -> domain.constants edge from CompositeRuntimeConfig. Replaced the domain constants import with an application-local composite default preserving lock_ttl_seconds=3600. Updated generated architecture dependency map artifacts and module coverage inventory. Validated ruff, unit runtime/heartbeat tests, failing architecture budget test with extended timeout, dependency-map check, module coverage check, and source-tree hash guard.

## Lessons learned

- Replace with durable follow-up if needed
