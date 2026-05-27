---
id: e2e-dq-timeout-fix
title: Debug E2E timeout in silver DQ distribution profiling
task_id: e2e-dq-timeout-fix
created_at: '2026-05-26T10:01:11Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/factories/dq/_context_resolver_support.py
summary: Moved relaxed-DQ trimming to the extracted Silver DQ report config seam so
  runner/postrun receives a value_distribution-free config when relaxed_dq is enabled.
---

# Episodic summary

## Task

- Title: Debug E2E timeout in silver DQ distribution profiling

## Outcome

- Moved relaxed-DQ trimming to the extracted Silver DQ report config seam so runner/postrun receives a value_distribution-free config when relaxed_dq is enabled.

## Lessons learned

- Replace with durable follow-up if needed
