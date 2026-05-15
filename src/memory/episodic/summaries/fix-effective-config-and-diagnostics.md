---
id: fix-effective-config-and-diagnostics
title: Fix effective config and diagnostics regressions
task_id: fix-effective-config-and-diagnostics
created_at: '2026-05-15T17:28:42Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/application/services/test_run_manifest_diagnostics.py
summary: Aligned effective-config env override tests with the strict execution_environment
  allowlist, synchronized diagnostics expectations with replay_ready defaults, and
  stabilized supported family ordering for reproducibility golden fixtures.
---

# Episodic summary

## Task

- Title: Fix effective config and diagnostics regressions

## Outcome

- Aligned effective-config env override tests with the strict execution_environment allowlist, synchronized diagnostics expectations with replay_ready defaults, and stabilized supported family ordering for reproducibility golden fixtures.

## Lessons learned

- Replace with durable follow-up if needed
