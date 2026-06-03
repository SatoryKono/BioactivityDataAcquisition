---
id: future-annotations-policy-fix-20260603
title: Add future annotations imports to sanctioned source modules
task_id: future-annotations-policy-fix-20260603
created_at: '2026-06-03T07:50:45Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/pipelines/pubmed/block_definitions.py
- src/bioetl/application/pipelines/uniprot/extractors/_comment_facets.py
- reports/quality/module-coverage-inventory.json
summary: Added from __future__ import annotations to two source modules required by
  architecture policy, refreshed module coverage inventory, and confirmed the policy
  test passes. The source-tree hash guard remained unstable due unrelated concurrent
  src/bioetl drift already present in the worktree.
---

# Episodic summary

## Task

- Title: Add future annotations imports to sanctioned source modules

## Outcome

- Added from __future__ import annotations to two source modules required by architecture policy, refreshed module coverage inventory, and confirmed the policy test passes. The source-tree hash guard remained unstable due unrelated concurrent src/bioetl drift already present in the worktree.

## Lessons learned

- Replace with durable follow-up if needed
