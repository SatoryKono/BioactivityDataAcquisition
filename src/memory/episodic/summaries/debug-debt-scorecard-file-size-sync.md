---
id: debug-debt-scorecard-file-size-sync
title: Fix debt scorecard file_size_limits sync
task_id: debug-debt-scorecard-file-size-sync
created_at: '2026-06-22T16:41:18Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/quality/architecture_metric_exemptions.yaml
summary: Removed stale file_size_limits exemptions from the active architecture metric
  registry by restoring file_size_limits to an empty mapping. Verified debt scorecard
  baseline remains zero, live total exemptions is zero, quality exemptions gate passes,
  deterministic debt task generation reports zero tasks, and the full debt scorecard
  architecture test file passes.
---

# Episodic summary

## Task

- Title: Fix debt scorecard file_size_limits sync

## Outcome

- Removed stale file_size_limits exemptions from the active architecture metric registry by restoring file_size_limits to an empty mapping. Verified debt scorecard baseline remains zero, live total exemptions is zero, quality exemptions gate passes, deterministic debt task generation reports zero tasks, and the full debt scorecard architecture test file passes.

## Lessons learned

- Replace with durable follow-up if needed
