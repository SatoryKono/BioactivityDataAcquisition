---
id: cli-domain-lazy-export-fix-20260520
title: Fix CLI domain package import cycles
task_id: cli-domain-lazy-export-fix-20260520
created_at: '2026-05-20T06:43:56Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/cli/commands/domains/run_all/__init__.py
summary: Converted CLI domain command packages to lazy __getattr__ exports so retained
  compat import paths no longer trigger circular imports during submodule loading.
---

# Episodic summary

## Task

- Title: Fix CLI domain package import cycles

## Outcome

- Converted CLI domain command packages to lazy __getattr__ exports so retained compat import paths no longer trigger circular imports during submodule loading.

## Lessons learned

- Replace with durable follow-up if needed
