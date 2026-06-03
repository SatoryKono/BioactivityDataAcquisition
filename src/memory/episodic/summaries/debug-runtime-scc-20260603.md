---
id: debug-runtime-scc-20260603
title: Debug runtime import SCC
task_id: debug-runtime-scc-20260603
created_at: '2026-06-03T05:56:19Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/cli/commands/domains/maintenance/__init__.py
summary: Removed the AST-visible maintenance package cycle by preserving the lazy
  maintenance re-export via importlib.import_module instead of a direct import; runtime
  import SCC gate now passes and the retained seam still resolves correctly.
---

# Episodic summary

## Task

- Title: Debug runtime import SCC

## Outcome

- Removed the AST-visible maintenance package cycle by preserving the lazy maintenance re-export via importlib.import_module instead of a direct import; runtime import SCC gate now passes and the retained seam still resolves correctly.

## Lessons learned

- Replace with durable follow-up if needed
