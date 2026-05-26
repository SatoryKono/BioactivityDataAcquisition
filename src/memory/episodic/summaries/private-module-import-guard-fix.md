---
id: private-module-import-guard-fix
title: Fix owner-aware private module imports
task_id: private-module-import-guard-fix
created_at: '2026-05-26T12:00:33Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Replaced cross-owner private-module imports in control-plane ownership packages
  by introducing public owner modules and retargeting subpackage imports; switched
  file_run_ledger_store to settings_api.get_settings; verified with ruff and AST-equivalent
  private-import scan (0 violations).
---

# Episodic summary

## Task

- Title: Fix owner-aware private module imports

## Outcome

- Replaced cross-owner private-module imports in control-plane ownership packages by introducing public owner modules and retargeting subpackage imports; switched file_run_ledger_store to settings_api.get_settings; verified with ruff and AST-equivalent private-import scan (0 violations).

## Lessons learned

- Replace with durable follow-up if needed
