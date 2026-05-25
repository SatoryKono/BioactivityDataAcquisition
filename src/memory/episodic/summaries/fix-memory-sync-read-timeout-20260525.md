---
id: fix-memory-sync-read-timeout-20260525
title: Harden memory graph docs drift read against unreadable files
task_id: fix-memory-sync-read-timeout-20260525
created_at: '2026-05-25T12:34:22Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Normalized Windows-style repo paths in memory graph docs drift scanning so
  excluded docs/reports trees are skipped before read_text, and added regression coverage
  for excluded backslash paths.
---

# Episodic summary

## Task

- Title: Harden memory graph docs drift read against unreadable files

## Outcome

- Normalized Windows-style repo paths in memory graph docs drift scanning so excluded docs/reports trees are skipped before read_text, and added regression coverage for excluded backslash paths.

## Lessons learned

- Replace with durable follow-up if needed
