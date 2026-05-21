---
id: fix-contract-registry-loader-boundary
title: Fix contract registry loader boundary regressions
task_id: fix-contract-registry-loader-boundary
created_at: '2026-05-21T09:44:53Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/infrastructure/config/contract_registry_loader.py
summary: Replaced direct contract-registry YAML path/parsing in effective-config graph
  support and memory graph sync with the canonical contract_registry_loader constant
  and loader seam, restoring architecture guardrail compliance.
---

# Episodic summary

## Task

- Title: Fix contract registry loader boundary regressions

## Outcome

- Replaced direct contract-registry YAML path/parsing in effective-config graph support and memory graph sync with the canonical contract_registry_loader constant and loader seam, restoring architecture guardrail compliance.

## Lessons learned

- Replace with durable follow-up if needed
