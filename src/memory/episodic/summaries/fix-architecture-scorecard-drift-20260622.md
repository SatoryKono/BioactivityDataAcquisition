---
id: fix-architecture-scorecard-drift-20260622
title: Fix architecture scorecard drift
task_id: fix-architecture-scorecard-drift-20260622
created_at: '2026-06-22T16:02:10Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_architecture_quality_scorecard.py
summary: 'Investigated architecture-quality-scorecard failures after duplication first-wave
  work. Root cause was generated artifact drift: committed scorecard/module coverage
  inventory needed the current live compatibility census twin_pair_count=1 and current
  module coverage source_tree_sha256. On the current checkout the staged artifacts
  already contain the synchronized values, and tests/architecture/test_architecture_quality_scorecard.py
  passes. Module coverage source-tree hash guard is skipped on WSL by repo policy.
  Full git status was stopped due shared-drive latency; path-scoped status/diff confirmed
  the relevant staged generated artifacts.'
---

# Episodic summary

## Task

- Title: Fix architecture scorecard drift

## Outcome

- Investigated architecture-quality-scorecard failures after duplication first-wave work. Root cause was generated artifact drift: committed scorecard/module coverage inventory needed the current live compatibility census twin_pair_count=1 and current module coverage source_tree_sha256. On the current checkout the staged artifacts already contain the synchronized values, and tests/architecture/test_architecture_quality_scorecard.py passes. Module coverage source-tree hash guard is skipped on WSL by repo policy. Full git status was stopped due shared-drive latency; path-scoped status/diff confirmed the relevant staged generated artifacts.

## Lessons learned

- Replace with durable follow-up if needed
