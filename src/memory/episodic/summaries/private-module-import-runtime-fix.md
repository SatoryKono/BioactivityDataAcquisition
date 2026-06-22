---
id: private-module-import-runtime-fix
title: Fix private module import in composition bootstrap runtime facade
task_id: private-module-import-runtime-fix
created_at: '2026-06-22T17:17:59Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_private_module_imports.py
summary: Replaced the cross-owner private bootstrap export helper with a public runtime_public_exports
  module, removed the stale private duplicate, and resynced the committed module coverage
  hash and architecture scorecard.
---

# Episodic summary

## Task

- Title: Fix private module import in composition bootstrap runtime facade

## Outcome

- Replaced the cross-owner private bootstrap export helper with a public runtime_public_exports module, removed the stale private duplicate, and resynced the committed module coverage hash and architecture scorecard.

## Lessons learned

- Replace with durable follow-up if needed
