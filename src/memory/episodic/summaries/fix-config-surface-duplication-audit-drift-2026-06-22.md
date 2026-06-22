---
id: fix-config-surface-duplication-audit-drift-2026-06-22
title: Fix config surface duplication audit drift
task_id: fix-config-surface-duplication-audit-drift-2026-06-22
created_at: '2026-06-22T13:27:10Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Made config-surface duplication audit deterministic by scanning tracked configs
  via git ls-files with a filesystem fallback, reran the backlog generator, and verified
  the targeted architecture test passes with committed and live files_scanned both
  at 186.
---

# Episodic summary

## Task

- Title: Fix config surface duplication audit drift

## Outcome

- Made config-surface duplication audit deterministic by scanning tracked configs via git ls-files with a filesystem fallback, reran the backlog generator, and verified the targeted architecture test passes with committed and live files_scanned both at 186.

## Lessons learned

- Replace with durable follow-up if needed
