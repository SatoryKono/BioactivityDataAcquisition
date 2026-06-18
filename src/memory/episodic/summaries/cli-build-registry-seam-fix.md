---
id: cli-build-registry-seam-fix
title: Restore CLI build_cli_registry patch seam
task_id: cli-build-registry-seam-fix
created_at: '2026-06-18T09:52:03Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/cli/main.py
summary: Restored a local build_cli_registry compatibility seam in cli.main and routed
  _build_main_registry through it so both legacy CLI patch points remain stable.
---

# Episodic summary

## Task

- Title: Restore CLI build_cli_registry patch seam

## Outcome

- Restored a local build_cli_registry compatibility seam in cli.main and routed _build_main_registry through it so both legacy CLI patch points remain stable.

## Lessons learned

- Replace with durable follow-up if needed
