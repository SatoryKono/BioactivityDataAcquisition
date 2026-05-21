---
id: registry-validation-function-length-20260521
title: Refactor registry manifest validator under function length limit
task_id: registry-validation-function-length-20260521
created_at: '2026-05-21T09:13:10Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Split validate_registry_manifest into entry-level and entity-config helper
  validators so the composition registry validation module stays under the 100-line
  function cap without changing diagnostics.
---

# Episodic summary

## Task

- Title: Refactor registry manifest validator under function length limit

## Outcome

- Split validate_registry_manifest into entry-level and entity-config helper validators so the composition registry validation module stays under the 100-line function cap without changing diagnostics.

## Lessons learned

- Replace with durable follow-up if needed
