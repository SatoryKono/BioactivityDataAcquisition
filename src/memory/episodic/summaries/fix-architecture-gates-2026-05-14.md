---
id: fix-architecture-gates-2026-05-14
title: Fix architecture gate failures from reported Windows run
task_id: fix-architecture-gates-2026-05-14
created_at: '2026-05-14T13:47:42Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_architecture_acceptance_baseline.py
summary: Fixed reported architecture gate failures by syncing run-ledger acceptance
  anchors with split runtime modules, removing the orphan CLI inspection output helper,
  updating VCR inventory, splitting pipeline registry export metadata under hotspot
  budgets, keeping bronze_writer under its LOC ratchet, and regenerating dependency-map
  artifacts with zero layer violations. Memory refresh remains blocked by stale RAG
  references to the removed CLI helper.
---

# Episodic summary

## Task

- Title: Fix architecture gate failures from reported Windows run

## Outcome

- Fixed reported architecture gate failures by syncing run-ledger acceptance anchors with split runtime modules, removing the orphan CLI inspection output helper, updating VCR inventory, splitting pipeline registry export metadata under hotspot budgets, keeping bronze_writer under its LOC ratchet, and regenerating dependency-map artifacts with zero layer violations. Memory refresh remains blocked by stale RAG references to the removed CLI helper.

## Lessons learned

- Replace with durable follow-up if needed
