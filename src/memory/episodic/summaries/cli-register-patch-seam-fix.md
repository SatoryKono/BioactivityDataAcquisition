---
id: cli-register-patch-seam-fix
title: Restore CLI register_all_pipelines patch seam
task_id: cli-register-patch-seam-fix
created_at: '2026-06-18T09:49:31Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/cli/main.py
summary: Restored the CLI main module's register_all_pipelines patch seam by wiring
  the explicit main-entry registry bootstrap through create_registry plus register_all_pipelines
  again.
---

# Episodic summary

## Task

- Title: Restore CLI register_all_pipelines patch seam

## Outcome

- Restored the CLI main module's register_all_pipelines patch seam by wiring the explicit main-entry registry bootstrap through create_registry plus register_all_pipelines again.

## Lessons learned

- Replace with durable follow-up if needed
