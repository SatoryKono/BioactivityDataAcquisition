---
id: fix-advanced-scenarios-coroutine-compare
title: Fix advanced scenarios e2e coroutine comparison regression
task_id: fix-advanced-scenarios-coroutine-compare
created_at: '2026-06-19T08:49:47Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/e2e/test_advanced_scenarios_e2e.py
summary: Awaited advanced-scenarios async silver assertion helpers consistently in
  shared helper paths and affected e2e call sites, eliminating coroutine-vs-int comparisons
  in ChEMBL orchestration scenarios.
---

# Episodic summary

## Task

- Title: Fix advanced scenarios e2e coroutine comparison regression

## Outcome

- Awaited advanced-scenarios async silver assertion helpers consistently in shared helper paths and affected e2e call sites, eliminating coroutine-vs-int comparisons in ChEMBL orchestration scenarios.

## Lessons learned

- Replace with durable follow-up if needed
