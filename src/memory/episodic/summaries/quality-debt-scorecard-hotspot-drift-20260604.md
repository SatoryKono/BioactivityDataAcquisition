---
id: quality-debt-scorecard-hotspot-drift-20260604
title: Resolve hotspot family metric drift in debt scorecard
task_id: quality-debt-scorecard-hotspot-drift-20260604
created_at: '2026-06-04T07:58:22Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/engineering/qa/hotspot_family_metrics.py
summary: Stabilized hotspot family governance against dirty-worktree noise by counting
  tracked Python files in the shared collector, added a unit guard for untracked-file
  exclusion, regenerated hotspot family baseline artifacts, and synced application_core
  scorecard metrics down to the current tracked baseline.
---

# Episodic summary

## Task

- Title: Resolve hotspot family metric drift in debt scorecard

## Outcome

- Stabilized hotspot family governance against dirty-worktree noise by counting tracked Python files in the shared collector, added a unit guard for untracked-file exclusion, regenerated hotspot family baseline artifacts, and synced application_core scorecard metrics down to the current tracked baseline.

## Lessons learned

- Replace with durable follow-up if needed
