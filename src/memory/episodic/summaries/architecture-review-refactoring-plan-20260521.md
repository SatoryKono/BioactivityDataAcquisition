---
id: architecture-review-refactoring-plan-20260521
title: Architecture review, quality scoring, and prioritized refactoring plan
task_id: architecture-review-refactoring-plan-20260521
created_at: '2026-05-21T11:32:36Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Completed read-only architecture review with parallel fact gathering across
  layer boundaries, composition/DI/config, test strategy, docs/governance, and hotspots.
  Key results: no current forbidden layer imports or runtime SCCs found in dependency-map
  evidence; current blockers are C901 in registry_validation and naming alias ManifestClock;
  major refactoring risks are config-root propagation, run-all registry ambient dependency,
  mixed script dispatch, stale singleton docs, docs/governance drift, and hotspot
  duplication/fan-in budgets. No implementation edits were made.'
---

# Episodic summary

## Task

- Title: Architecture review, quality scoring, and prioritized refactoring plan

## Outcome

- Completed read-only architecture review with parallel fact gathering across layer boundaries, composition/DI/config, test strategy, docs/governance, and hotspots. Key results: no current forbidden layer imports or runtime SCCs found in dependency-map evidence; current blockers are C901 in registry_validation and naming alias ManifestClock; major refactoring risks are config-root propagation, run-all registry ambient dependency, mixed script dispatch, stale singleton docs, docs/governance drift, and hotspot duplication/fan-in budgets. No implementation edits were made.

## Lessons learned

- Replace with durable follow-up if needed
