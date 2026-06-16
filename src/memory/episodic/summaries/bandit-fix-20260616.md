---
id: bandit-fix-20260616
title: Fix Bandit findings surfaced by pre-push hook
task_id: bandit-fix-20260616
created_at: '2026-06-16T08:33:59Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/cli/commands/domains/health/observability_backend_runtime.py
summary: Removed unsafe urlopen usage and hardcoded tmp path, resolved subprocess
  path handling for detached observability health helpers, replaced Bandit-flagged
  subprocess type imports with Protocols, updated targeted tests, and refreshed reports/quality/module-coverage-inventory.json
  source_tree_sha256.
---

# Episodic summary

## Task

- Title: Fix Bandit findings surfaced by pre-push hook

## Outcome

- Removed unsafe urlopen usage and hardcoded tmp path, resolved subprocess path handling for detached observability health helpers, replaced Bandit-flagged subprocess type imports with Protocols, updated targeted tests, and refreshed reports/quality/module-coverage-inventory.json source_tree_sha256.

## Lessons learned

- Replace with durable follow-up if needed
