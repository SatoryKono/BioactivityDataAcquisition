---
id: cli-main-registry-lazy-fix-20260603
title: Fix CLI main registry lazy-build regression
task_id: cli-main-registry-lazy-fix-20260603
created_at: '2026-06-03T05:57:36Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/cli/main.py
summary: Restored CLI main entrypoint to lazy registry behavior by ensuring main()
  invokes cli() without eager obj construction; target CLI helper tests pass; refreshed
  module coverage inventory artifact using scripts.engineering.qa report-module-coverage
  and verified source_tree_sha256 guard.
---

# Episodic summary

## Task

- Title: Fix CLI main registry lazy-build regression

## Outcome

- Restored CLI main entrypoint to lazy registry behavior by ensuring main() invokes cli() without eager obj construction; target CLI helper tests pass; refreshed module coverage inventory artifact using scripts.engineering.qa report-module-coverage and verified source_tree_sha256 guard.

## Lessons learned

- Replace with durable follow-up if needed
