---
id: cli-main-calls-cli-lazy-fix-20260603
title: Fix CLI main_calls_cli lazy registry regression
task_id: cli-main-calls-cli-lazy-fix-20260603
created_at: '2026-06-03T06:08:32Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/interfaces/cli/test_cli_helpers.py
summary: Investigated reported TestMainEntryPoint.test_main_calls_cli failure. Current
  source main() invokes cli() without eager registry construction; targeted and full
  CLI helper tests pass in WSL and Windows .venv-win. No source change was required
  in this turn; staged local changes remain limited to test import placement and module
  coverage inventory artifact.
---

# Episodic summary

## Task

- Title: Fix CLI main_calls_cli lazy registry regression

## Outcome

- Investigated reported TestMainEntryPoint.test_main_calls_cli failure. Current source main() invokes cli() without eager registry construction; targeted and full CLI helper tests pass in WSL and Windows .venv-win. No source change was required in this turn; staged local changes remain limited to test import placement and module coverage inventory artifact.

## Lessons learned

- Replace with durable follow-up if needed
