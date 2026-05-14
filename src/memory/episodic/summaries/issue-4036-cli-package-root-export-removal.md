---
id: issue-4036-cli-package-root-export-removal
title: Issue 4036 CLI package-root export removal
task_id: issue-4036-cli-package-root-export-removal
created_at: '2026-05-13T17:31:15Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Removed create_pipeline_runner from bioetl.interfaces.cli package-root, updated
  wrapper-family tests to enforce its absence, and passed targeted pytest; refresh
  still requires skip-refresh because generated memory surfaces can lag compatibility-removal
  waves.
---

# Episodic summary

## Task

- Title: Issue 4036 CLI package-root export removal

## Outcome

- Removed create_pipeline_runner from bioetl.interfaces.cli package-root, updated wrapper-family tests to enforce its absence, and passed targeted pytest; refresh still requires skip-refresh because generated memory surfaces can lag compatibility-removal waves.

## Lessons learned

- Replace with durable follow-up if needed
