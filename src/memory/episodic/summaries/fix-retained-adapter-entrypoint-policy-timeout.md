---
id: fix-retained-adapter-entrypoint-policy-timeout
title: Fix retained adapter entrypoint policy timeout
task_id: fix_retained_adapter_entrypoint_policy_timeout
created_at: '2026-06-16T04:43:21Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Reworked retained-adapter-entrypoint architecture guards to use ripgrep-backed
  mention scans with a Python fallback, eliminating slow full-file pathlib reads across
  ~1900 test modules on Windows while preserving the same policy checks and allowlists.
---

# Episodic summary

## Task

- Title: Fix retained adapter entrypoint policy timeout

## Outcome

- Reworked retained-adapter-entrypoint architecture guards to use ripgrep-backed mention scans with a Python fallback, eliminating slow full-file pathlib reads across ~1900 test modules on Windows while preserving the same policy checks and allowlists.

## Lessons learned

- Replace with durable follow-up if needed
